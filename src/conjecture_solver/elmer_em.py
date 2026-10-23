"""Experimental single-process Elmer A-v workflow with auditable stage boundaries.

Mesh construction accepts a user-authored Gmsh geometry or an existing MSH2 mesh.
Only linear, nonmagnetic, fixed conductors and backward Euler are supported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import shutil
import signal
import subprocess
import time
from pathlib import Path

import numpy as np

MU0 = 4 * np.pi * 1e-7
FAILURES = (
    "iteration halted due to problem in algorithm",
    "rnrm^2 is negative",
    "kappal^2 is non-positive",
    "kappa0^2 is non-positive",
    "error::",
    "fatal",
    "not converged",
    "failed to converge",
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value, name, *, zero=False):
    require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and (value >= 0 if zero else value > 0),
        f"{name} must be finite and {'nonnegative' if zero else 'positive'}",
    )


def vector(value, name):
    arr = np.asarray(value, dtype=float)
    require(arr.shape == (3,) and np.isfinite(arr).all(), f"{name}: expected finite xyz")
    return arr


def validate(config):
    require(
        config.get("schema_version") == "0.1" and config.get("units") == "SI",
        "Expected schema_version=0.1 and units=SI",
    )
    positive(config["dt_s"], "dt_s")
    require(type(config["steps"]) is int and config["steps"] > 0, "steps must be positive integer")
    positive(config["linear_tolerance"], "linear_tolerance")
    require(config["linear_tolerance"] < 1, "linear_tolerance must be < 1")
    require(type(config.get("save_state", False)) is bool, "save_state must be boolean")
    materials = config["materials"]
    require(len(materials) >= 2, "At least one conductor and one air material required")
    tags = [m["tag"] for m in materials]
    require(
        len(tags) == len(set(tags)) and all(type(t) is int and t > 0 for t in tags),
        "Material tags must be distinct positive integers",
    )
    for m in materials:
        positive(m["conductivity_S_m"], "conductivity_S_m", zero=True)
    conducting = {m["tag"] for m in materials if m["conductivity_S_m"] > 0}
    require(conducting and len(conducting) < len(materials), "Need conductor and air")
    boundaries = []
    for role in ("input", "ground", "outer"):
        values = config["boundaries"][role]
        require(values and all(type(v) is int and v > 0 for v in values), "Invalid boundaries")
        boundaries.extend(values)
    require(len(set(boundaries)) == len(boundaries), "Boundary roles must be disjoint")
    driver = config["driver"]
    require(bool(driver.get("provenance", "").strip()), "Record driver provenance/assumptions")
    if driver["kind"] == "rlc":
        positive(driver["R_ohm"], "R_ohm", zero=True)
        for key in ("L_H", "C_F", "V0_V"):
            positive(driver[key], key)
    elif driver["kind"] in ("constant", "sine"):
        positive(driver["current_A"], "current_A")
        if driver["kind"] == "sine":
            positive(driver["peak_time_s"], "peak_time_s")
    else:
        raise ValueError("driver.kind must be constant, sine or rlc")
    probes = config["probes"]
    require(probes and len({p["name"] for p in probes}) == len(probes), "Unique probes required")
    for p in probes:
        vector(p["position_m"], "probe position")
    regions = config["current_regions"]
    require(
        regions and len({r["name"] for r in regions}) == len(regions), "Unique regions required"
    )
    for r in regions:
        require(r["tags"] and set(r["tags"]) <= conducting, "Current region must be conducting")
        require(
            np.isclose(np.linalg.norm(vector(r["direction"], "direction")), 1),
            "Current region direction must be a unit vector",
        )
        positive(r["length_m"], "length_m")
    names = {r["name"] for r in regions}
    require(config["current_balances"], "At least one independent current balance required")
    for terms in config["current_balances"]:
        require(
            terms and set(terms) <= names and len(set(terms)) == len(terms),
            "Each balance sums distinct named region currents and compares with the port",
        )
    for name in ("current_relative", "energy_relative", "circuit_relative"):
        positive(config["limits"][name], name)
        require(config["limits"][name] < 1, "Relative limits must be < 1")
    return config


def runtime():
    home = Path(os.environ["SIMJECTURE_ELMER_HOME"]).resolve()
    solver = home / "bin/ElmerSolver"
    if not solver.is_file():
        solver = home / "bin/ElmerSolver_mpi"
    grid = home / "bin/ElmerGrid"
    require(solver.is_file() and grid.is_file(), "ElmerSolver and ElmerGrid are required")
    env = os.environ | {
        "ELMER_HOME": str(home),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    }
    library_dirs = [home / "lib/elmersolver", home / "lib", home / "deps"]
    env["LD_LIBRARY_PATH"] = ":".join(map(str, library_dirs))
    # Every run binds the actual installed core, modules and dependency bundle.
    identity = {
        str(p.relative_to(home)): digest(p)
        for p in sorted(home.rglob("*"))
        if p.is_file() and (".so" in p.name or p in (solver, grid) or p.name == "elements.def")
    }
    record = home.parent / "share/build-record.json"
    if record.is_file():
        require(identity == read(record)["elmer_identity"], "Installed Elmer files changed")
    return solver, grid, env, identity


def run_process(command, directory, stem, *, timeout, memory_gib, env):
    positive(timeout, "timeout")
    positive(memory_gib, "memory_gib")
    directory = Path(directory)
    require(not (directory / f"{stem}.json").exists(), "Preserve previous trials; use a fresh case")

    def limits():
        size = int(memory_gib * 1024**3)
        resource.setrlimit(resource.RLIMIT_AS, (size, size))

    start = time.monotonic()
    peak_rss = 0
    timed_out = False
    logpath = directory / f"{stem}.log"
    with logpath.open("x") as log:
        child = subprocess.Popen(
            command,
            cwd=directory,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=limits,
        )
        try:
            while child.poll() is None:
                try:
                    status = Path(f"/proc/{child.pid}/status").read_text()
                    values = re.findall(r"^VmHWM:\s+(\d+)", status, re.M)
                    if values:
                        peak_rss = max(peak_rss, int(values[0]))
                except (FileNotFoundError, ProcessLookupError):
                    pass
                if time.monotonic() - start >= timeout:
                    timed_out = True
                    break
                time.sleep(0.2)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        code = child.wait()
    logtext = logpath.read_text(errors="replace")
    failures = [marker for marker in FAILURES if marker in logtext.lower()]
    accepted = code == 0 and not timed_out and not failures
    if stem == "run":
        accepted = accepted and "ELMER SOLVER FINISHED" in logtext
    record = {
        "command": list(map(str, command)),
        "returncode": code,
        "timed_out": timed_out,
        "execution_pass": accepted,
        "failure_markers": failures,
        "elapsed_s": time.monotonic() - start,
        "peak_process_RSS_KiB": peak_rss,
        "address_space_limit_GiB": memory_gib,
        "timeout_s": timeout,
        "log_sha256": digest(logpath),
    }
    save(directory / f"{stem}.json", record)
    return record


def mesh_case(case, config_path, mesh_path, *, timeout, memory_gib):
    import meshio

    config = validate(read(config_path))
    case = Path(case).resolve()
    case.mkdir(parents=True, exist_ok=False)
    save(case / "case.json", config)
    source = Path(mesh_path).resolve()
    require(source.suffix == ".msh", "mesh stage accepts an MSH2 mesh; generate with gmsh first")
    with source.open("rb") as stream:
        require(
            stream.readline().strip() == b"$MeshFormat" and stream.readline().split()[0] == b"2.2",
            "Expected Gmsh MSH 2.2 format",
        )
    shutil.copy2(source, case / "input.msh")
    mesh = meshio.read(case / "input.msh")
    require(
        set(mesh.cells_dict) <= {"vertex", "line", "triangle", "tetra"},
        "Only first-order tetrahedral meshes supported",
    )
    xyz = mesh.points
    require(np.isfinite(xyz).all(), "Mesh coordinates must be finite SI meters")
    tet = mesh.cells_dict["tetra"]
    tags = mesh.cell_data_dict["gmsh:physical"]["tetra"]
    p = xyz[tet]
    signed_volume = np.linalg.det(p[:, 1:] - p[:, :1]) / 6
    require(np.all(signed_volume > 0), "Mesh contains inverted or zero-volume tetrahedra")
    require(set(tags) == {m["tag"] for m in config["materials"]}, "Material tags mismatch")
    surfaces = set(mesh.cell_data_dict["gmsh:physical"]["triangle"])
    require(
        surfaces == {x for values in config["boundaries"].values() for x in values},
        "Boundary physical groups must exactly match the configured terminal/outer tags",
    )
    # A massive component must form one connected conductor; vertex connectivity
    # is insufficient because two bodies may touch at an edge without an electrical face.
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    conductors = {m["tag"] for m in config["materials"] if m["conductivity_S_m"] > 0}
    ct = tet[np.isin(tags, list(conductors))]
    faces = np.concatenate([ct[:, face] for face in ([0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3])])
    owners = np.tile(np.arange(len(ct)), 4)
    faces.sort(axis=1)
    order = np.lexsort(faces.T)
    pairs = np.all(faces[order][1:] == faces[order][:-1], axis=1)
    a, b = owners[order[:-1][pairs]], owners[order[1:][pairs]]
    graph = coo_matrix((np.ones(len(a)), (a, b)), shape=(len(ct), len(ct)))
    components = connected_components(graph, directed=False, return_labels=False)
    require(components == 1, f"Expected one face-connected conductor; found {components}")
    _, elmergrid, env, identity = runtime()
    result = run_process(
        [str(elmergrid), "14", "2", "input.msh", "-out", "mesh"],
        case,
        "mesh-convert",
        timeout=timeout,
        memory_gib=memory_gib,
        env=env,
    )
    require(result["execution_pass"], "ElmerGrid failed; inspect mesh-convert.log")
    for name in ("mesh.nodes", "mesh.elements", "mesh.boundary", "mesh.header"):
        require((case / "mesh" / name).is_file(), f"Missing ElmerGrid output {name}")
    generate_case(case, config)
    hashes = input_hashes(case)
    save(
        case / "mesh.json",
        {
            "tetrahedra": len(tet),
            "nodes": len(xyz),
            "conductor_components": int(components),
            "minimum_volume_m3": float(min(signed_volume)),
            "input_hashes": hashes,
            "runtime_identity": identity,
        },
    )


def generate_case(case, config):
    template = Path(__file__).with_name("elmer_em_case.sif").read_text()
    if not config.get("save_state", False):
        template = template.replace("  Output File = state.result\n  Save All = Logical True\n", "")
    materials = sorted(config["materials"], key=lambda m: m["conductivity_S_m"] == 0)
    n = sum(m["conductivity_S_m"] > 0 for m in materials)
    replacements = {
        "DT": config["dt_s"],
        "STEPS": config["steps"],
        "TOLERANCE": config["linear_tolerance"],
        "COMPONENT": f"""Component 1
  Name = String ConductorNetwork
  Master Bodies({n}) = Integer {" ".join(str(i) for i in range(1, n + 1))}
  Coil Type = String Massive
  Circuit Equation Voltage Factor = Real 1.0
End""",
    }
    for role, values in config["boundaries"].items():
        replacements[role.upper()] = " ".join(map(str, values))
        replacements["N" + role.upper()] = len(values)
    driver = config["driver"]
    if driver["kind"] == "rlc":
        replacements["DRIVER"] = f"Body Force 1\n  Vbank0 = Real {driver['V0_V']:.16g}\nEnd"
        circuit = f"""$ Circuits = 1
$ C.1.variables = 3
$ C.1.perm = zeros(3)
$ C.1.perm(0) = 0
$ C.1.perm(1) = 1
$ C.1.perm(2) = 2
$ C.1.A = zeros(3,3)
$ C.1.B = zeros(3,3)
$ C.1.name.1 = "i_component(1)"
$ C.1.name.2 = "v_component(1)"
$ C.1.name.3 = "v_cap_drop"
$ C.1.A(0,0) = {driver["L_H"]:.16g}
$ C.1.B(0,0) = {driver["R_ohm"]:.16g}
$ C.1.B(0,1) = 1
$ C.1.B(0,2) = 1
$ C.1.source.1 = "Vbank0"
$ C.1.A(2,2) = {driver["C_F"]:.16g}
$ C.1.B(2,0) = -1
"""
    else:
        expression = f"{driver['current_A']:.16g}"
        if driver["kind"] == "sine":
            expression += f"*sin(pi*tx/(2*{driver['peak_time_s']:.16g}))"
        replacements["DRIVER"] = (
            f'Body Force 1\n  S1 = Variable Time\n    Real MATC "{expression}"\nEnd'
        )
        circuit = """$ Circuits = 1
$ C.1.perm = zeros(4)
$ C.1.perm(3) = 0
$ C.1.perm(2) = 1
$ C.1.perm(0) = 2
$ C.1.perm(1) = 3
$ C.1.variables = 4
$ C.1.A = zeros(4,4)
$ C.1.B = zeros(4,4)
$ C.1.name.1 = "i_component(1)"
$ C.1.name.2 = "v_component(1)"
$ C.1.name.3 = "i_S1"
$ C.1.name.4 = "v_S1"
$ C.1.B(0,2) = 1
$ C.1.source.1 = "S1"
$ C.1.B(2,3) = 1
$ C.1.B(2,1) = 1
$ C.1.B(3,2) = 1
$ C.1.B(3,0) = -1
"""
    for key, value in replacements.items():
        template = template.replace(f"@{key}@", str(value))
    require(not re.search(r"@[A-Z]+@", template), "Unresolved SIF template parameter")
    for i, m in enumerate(materials, 1):
        equation = 1 if m["conductivity_S_m"] > 0 else 2
        force = "  Body Force = 1\n" if equation == 1 else ""
        template += f"""Material {i}
  Electric Conductivity = {m["conductivity_S_m"]:.16g}
  Relative Permeability = 1
  Relative Permittivity = 1
End
Body {i}
  Target Bodies(1) = {m["tag"]}
  Equation = {equation}
  Material = {i}
  Initial Condition = 1
{force}End
"""
    (case / "case.sif").write_text(template)
    (case / "circuit.definitions").write_text(circuit)
    save(case / "body-map.json", {str(m["tag"]): i for i, m in enumerate(materials, 1)})


def input_hashes(case):
    files = [
        case / name for name in ("case.json", "case.sif", "circuit.definitions", "body-map.json")
    ]
    files += [
        case / "mesh" / name
        for name in ("mesh.nodes", "mesh.elements", "mesh.boundary", "mesh.header")
    ]
    return {str(p.relative_to(case)): digest(p) for p in files}


def solve(case, *, timeout, memory_gib):
    case = Path(case).resolve()
    validate(read(case / "case.json"))
    mesh = read(case / "mesh.json")
    hashes = input_hashes(case)
    require(hashes == mesh["input_hashes"], "Case inputs changed after mesh preparation")
    solver, _, env, identity = runtime()
    require(identity == mesh["runtime_identity"], "Runtime changed after mesh preparation")
    require(not list((case / "mesh").glob("fields*")), "Existing fields: use a fresh case")
    record = run_process(
        [str(solver), "case.sif"], case, "run", timeout=timeout, memory_gib=memory_gib, env=env
    )
    record.update(
        input_hashes=hashes,
        runtime_identity=identity,
        driver_sha256=digest(__file__),
        scientific_validation="Not established by execution",
    )
    save(case / "run.json", record)
    return record["execution_pass"]


def table(case):
    names = (case / "circuits.dat.names").read_text()
    columns = {
        s.strip(): int(n) - 1 for n, s in re.findall(r"^\s*(\d+):\s*res:\s*(.+)$", names, re.M)
    }
    data = np.loadtxt(case / "circuits.dat", ndmin=2)
    require(np.isfinite(data).all(), "Non-finite circuit data")
    return {name: data[:, index] for name, index in columns.items()}


def circuit_audit(driver, t, current, voltage, drop):
    dt = np.diff(np.r_[0, t])
    di = np.diff(np.r_[0, current])
    du = np.diff(np.r_[0, drop])
    r, inductance, c, v0 = (driver[k] for k in ("R_ohm", "L_H", "C_F", "V0_V"))
    initial = 0.5 * c * v0**2
    stored = 0.5 * c * (v0 - drop) ** 2 + 0.5 * inductance * current**2
    resistor = np.cumsum(dt * r * current**2)
    port = np.cumsum(dt * current * voltage)
    loss = np.cumsum(0.5 * inductance * di**2 + 0.5 * c * du**2)
    return {
        "kvl_relative": float(
            max(abs(inductance * di / dt + r * current + voltage + drop - v0)) / v0
        ),
        "charge_relative": float(max(abs(c * du / dt - current)) / max(max(abs(current)), 1)),
        "energy_relative": float(max(abs(stored + resistor + port + loss - initial)) / initial),
        "backward_Euler_dissipation_J": float(loss[-1]),
        "initial_energy_J": initial,
    }


def audit(case):
    import pyvista as pv

    case = Path(case).resolve()
    config = validate(read(case / "case.json"))
    run = read(case / "run.json")
    require(input_hashes(case) == run["input_hashes"], "Case inputs changed after solve")
    require(digest(case / "run.log") == run["log_sha256"], "Solver log changed after solve")
    body_map = read(case / "body-map.json")
    values = table(case)
    t = values["time"]
    require(
        len(t) == config["steps"]
        and np.allclose(
            t, np.arange(1, len(t) + 1) * config["dt_s"], rtol=1e-9, atol=config["dt_s"] * 1e-9
        ),
        "Missing, duplicate or unexpected time steps",
    )
    files = sorted((case / "mesh").glob("fields_t*.vtu"))
    require(len(files) == len(t), "VTU fields required at every time step")
    drive, voltage = values["i_component(1)"], values["v_component(1)"]
    dt = np.diff(np.r_[0, t])
    rows, previous_b, mesh_signature = [], None, None
    numerical_loss = 0.0
    losses = 0.0
    input_work = 0.0
    previous_energy = 0.0
    max_step_closure = 0.0
    max_energy_mismatch = 0.0
    output_hashes = {
        str(p.relative_to(case)): digest(p)
        for p in [case / "circuits.dat", case / "circuits.dat.names", *files]
    }
    for k, file in enumerate(files):
        grid = pv.read(file)
        grid = grid.extract_cells(grid.celltypes == pv.CellType.TETRA)
        require(grid.n_cells > 0, "No tetrahedra in fields")
        signature = hashlib.sha256(grid.points.tobytes() + grid.cells.tobytes()).hexdigest()
        require(mesh_signature in (None, signature), "Mesh changed between steps")
        mesh_signature = signature
        volume = np.asarray(grid.compute_cell_sizes(length=False, area=False).cell_data["Volume"])
        ids = np.asarray(grid.cell_data["GeometryIds"])
        j = np.asarray(grid.cell_data["current density e"])
        b = np.asarray(grid.cell_data["magnetic flux density e"])
        require(
            np.all(volume > 0) and np.isfinite(j).all() and np.isfinite(b).all(),
            "Non-finite fields or nonpositive volumes",
        )
        currents = {}
        for region in config["current_regions"]:
            mask = np.isin(ids, [body_map[str(tag)] for tag in region["tags"]])
            require(mask.any(), "Missing current integration region")
            currents[region["name"]] = float(
                np.sum((j[mask] @ region["direction"]) * volume[mask]) / region["length_m"]
            )
        balances = [
            abs(sum(currents[n] for n in terms) - drive[k]) / max(abs(drive[k]), 1)
            for terms in config["current_balances"]
        ]
        sampled = pv.PolyData([p["position_m"] for p in config["probes"]]).sample(grid)
        require(np.all(sampled["vtkValidPointMask"] == 1), "Probe outside mesh")
        probes = np.asarray(sampled["magnetic flux density"])
        require(np.isfinite(probes).all(), "Non-finite probe fields")
        if previous_b is None:
            previous_b = np.zeros_like(b)
        be = float(np.sum(volume * np.sum((b - previous_b) ** 2, axis=1)) / (2 * MU0))
        energy = float(np.sum(volume * np.sum(b**2, axis=1)) / (2 * MU0))
        reported = values["electromagnetic field energy"][k]
        max_energy_mismatch = max(max_energy_mismatch, abs(energy - reported) / max(energy, 1e-30))
        work = dt[k] * drive[k] * voltage[k]
        ohmic = dt[k] * values["eddy current power"][k]
        step_closure = energy - previous_energy + ohmic + be - work
        max_step_closure = max(max_step_closure, abs(step_closure))
        numerical_loss += be
        losses += ohmic
        input_work += work
        rows.append(
            {
                "time_s": float(t[k]),
                "drive_current_A": float(drive[k]),
                "voltage_V": float(voltage[k]),
                "currents_A": currents,
                "current_balance_relative": max(balances),
                "field_energy_J": energy,
                "probes_B_T": {
                    p["name"]: v.tolist() for p, v in zip(config["probes"], probes, strict=True)
                },
            }
        )
        previous_b, previous_energy = b.copy(), energy
    scale = max(float(np.sum(abs(dt * drive * voltage))), 1e-30)
    energy_error = abs(previous_energy + losses + numerical_loss - input_work) / scale
    max_current_error = max(r["current_balance_relative"] for r in rows)
    circuit = None
    if config["driver"]["kind"] == "rlc":
        circuit = circuit_audit(config["driver"], t, drive, voltage, values["v_cap_drop"])
    circuit_ok = (
        circuit is None
        or max(circuit[n] for n in ("kvl_relative", "charge_relative", "energy_relative"))
        < config["limits"]["circuit_relative"]
    )
    checks = {
        "execution": run["execution_pass"],
        "current": max_current_error < config["limits"]["current_relative"],
        "field_energy": max(energy_error, max_energy_mismatch, max_step_closure / scale)
        < config["limits"]["energy_relative"],
        "circuit": circuit_ok,
    }
    report = {
        "checks": {k: bool(v) for k, v in checks.items()},
        "numerical_checks_pass": all(checks.values()),
        "qualification": (
            "Conservation checks only; mesh/time/domain convergence "
            "and source calibration remain separate."
        ),
        "steps": rows,
        "max_current_balance_relative": max_current_error,
        "FEM_energy": {
            "input_J": float(input_work),
            "ohmic_J": float(losses),
            "backward_Euler_dissipation_J": numerical_loss,
            "final_field_J": previous_energy,
            "closure_relative": energy_error,
            "max_step_closure_relative": max_step_closure / scale,
            "element_vs_reported_energy_relative": max_energy_mismatch,
        },
        "circuit": circuit,
        "output_hashes": output_hashes,
        "run_sha256": digest(case / "run.json"),
    }
    save(case / "audit.json", report)
    return report


def plot(case):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    case = Path(case).resolve()
    report = read(case / "audit.json")
    require(report["numerical_checks_pass"], "Rejected case: plot stage requires passing audit")
    require(digest(case / "run.json") == report["run_sha256"], "Run record changed after audit")
    require(
        input_hashes(case) == read(case / "run.json")["input_hashes"], "Inputs changed after audit"
    )
    for name, checksum in report["output_hashes"].items():
        require(digest(case / name) == checksum, "Outputs changed after audit")
    rows = report["steps"]
    t = np.array([r["time_s"] for r in rows]) * 1e9
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].plot(t, [r["drive_current_A"] / 1e3 for r in rows], label="Port")
    for name in rows[0]["currents_A"]:
        axes[0].plot(t, [r["currents_A"][name] / 1e3 for r in rows], label=name)
    for name in rows[0]["probes_B_T"]:
        axes[1].plot(t, [np.linalg.norm(r["probes_B_T"][name]) for r in rows], label=name)
    for ax, ylabel in zip(axes, ("Current [kA]", "|B| [T]"), strict=True):
        ax.set(xlabel="Time [ns]", ylabel=ylabel)
        ax.legend()
        ax.grid(alpha=0.2)
    fig.suptitle("Experimental Elmer A-v model — conservation checks pass")
    fig.text(
        0.5,
        0.015,
        "Mesh/time/domain convergence and source calibration require separate evidence.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(case / "results.png", dpi=180)
    fig.savefig(case / "results.pdf")
    plt.close(fig)
    import pyvista as pv

    config = read(case / "case.json")
    grid = pv.read(sorted((case / "mesh").glob("fields_t*.vtu"))[-1])
    point = config["probes"][0]["position_m"]
    x = np.linspace(grid.bounds[0], grid.bounds[1], 241)
    y = np.linspace(grid.bounds[2], grid.bounds[3], 241)
    xx, yy = np.meshgrid(x, y)
    sampled = pv.PolyData(
        np.column_stack([xx.ravel(), yy.ravel(), np.full(xx.size, point[2])])
    ).sample(grid)
    b = np.linalg.norm(sampled["magnetic flux density"], axis=1)
    b[sampled["vtkValidPointMask"] != 1] = np.nan
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    image = ax.pcolormesh(xx * 1e3, yy * 1e3, b.reshape(xx.shape), shading="auto", cmap="magma")
    ax.plot(point[0] * 1e3, point[1] * 1e3, "+", color="cyan")
    ax.set(
        xlabel="x [mm]",
        ylabel="y [mm]",
        aspect="equal",
        title=f"Final |B|, z = {point[2] * 1e3:g} mm; checks pass",
    )
    fig.colorbar(image, ax=ax, label="|B| [T]")
    fig.tight_layout()
    fig.savefig(case / "field-slice.png", dpi=180)
    plt.close(fig)
    return str(case / "results.png")


def wire_demo(directory, *, rlc=False):
    """Independent straight-cylinder control. No private CAD or machine parameters."""
    import gmsh

    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.NumThreads", 1)
        gmsh.option.setNumber("General.Terminal", 0)
        occ = gmsh.model.occ
        conductor = occ.addCylinder(0, 0, -0.01, 0, 0, 0.02, 0.001)
        air = occ.addCylinder(0, 0, -0.01, 0, 0, 0.02, 0.01)
        parts, mapping = occ.fragment([(3, conductor)], [(3, air)])
        occ.synchronize()
        wire = [tag for dim, tag in mapping[0] if dim == 3]
        air = [tag for dim, tag in parts if dim == 3 and tag not in wire]
        gmsh.model.addPhysicalGroup(3, wire, 100)
        gmsh.model.addPhysicalGroup(3, air, 101)
        terminals = {300: [], 301: []}
        for dim, tag in gmsh.model.getBoundary([(3, v) for v in wire], False, False):
            box = occ.getBoundingBox(dim, tag)
            for physical, z in ((300, 0.01), (301, -0.01)):
                if abs(box[2] - z) < 1e-6 and abs(box[5] - z) < 1e-6:
                    terminals[physical].append(tag)
        outer = [tag for dim, tag in gmsh.model.getBoundary(parts, True, False) if dim == 2]
        for physical, surfaces in terminals.items():
            gmsh.model.addPhysicalGroup(2, surfaces, physical)
        gmsh.model.addPhysicalGroup(
            2, [tag for tag in outer if tag not in terminals[300] + terminals[301]], 200
        )
        field = gmsh.model.mesh.field
        local = field.add("Cylinder")
        for name, value in dict(
            XCenter=0,
            YCenter=0,
            ZCenter=0,
            XAxis=0,
            YAxis=0,
            ZAxis=0.022,
            Radius=0.002 if rlc else 0.003,
            VIn=0.0002,
            VOut=0.002,
        ).items():
            field.setNumber(local, name, value)
        field.setAsBackgroundMesh(local)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(directory / "wire.msh"))
    finally:
        gmsh.finalize()
    driver = {"kind": "constant", "current_A": 1000.0, "provenance": "Analytic cylinder control"}
    if rlc:
        driver = {
            "kind": "rlc",
            "R_ohm": 10.0,
            "L_H": 0.001,
            "C_F": 1e-6,
            "V0_V": 1000.0,
            "provenance": "Synthetic RLC control; no experimental machine fit",
        }
    config = {
        "schema_version": "0.1",
        "units": "SI",
        "dt_s": 2e-6 if rlc else 0.001,
        "steps": 30 if rlc else 1,
        "linear_tolerance": 1e-10,
        "materials": [{"tag": 100, "conductivity_S_m": 5.8e7}, {"tag": 101, "conductivity_S_m": 0}],
        "boundaries": {"outer": [200], "input": [300], "ground": [301]},
        "driver": driver,
        "probes": [
            {
                "name": f"p{k}",
                "position_m": [0.002 * np.cos(k * np.pi / 4), 0.002 * np.sin(k * np.pi / 4), 0.0],
            }
            for k in range(8)
        ],
        "current_regions": [
            {"name": "wire", "tags": [100], "direction": [0, 0, -1], "length_m": 0.02}
        ],
        "current_balances": [["wire"]],
        "limits": {"current_relative": 1e-4, "energy_relative": 1e-3, "circuit_relative": 1e-6},
    }
    save(directory / "input.json", config)
    case = directory / "case"
    mesh_case(case, directory / "input.json", directory / "wire.msh", timeout=60, memory_gib=3)
    require(solve(case, timeout=600 if rlc else 90, memory_gib=3), "Wire solve failed")
    result = audit(case)
    require(result["numerical_checks_pass"], "Wire conservation checks failed")
    last = result["steps"][-1]
    errors = []
    for probe in config["probes"]:
        x, y, _ = probe["position_m"]
        analytic = (
            MU0 * last["drive_current_A"] / (2 * np.pi * (x * x + y * y)) * np.array([y, -x, 0])
        )
        actual = np.array(last["probes_B_T"][probe["name"]])
        errors.append(float(np.linalg.norm(actual - analytic) / np.linalg.norm(analytic)))
    control = {
        "numerical_checks_pass": True,
        "max_field_vector_error": max(errors),
        "analytic_field_pass": max(errors) < 0.08,
        "scope": "Finite meshed cylinder compared with infinite-cylinder field; control only.",
    }
    if rlc:
        previous, currents = np.zeros(2), []
        inductance, r, c, h, v = 0.001, 10.0, 1e-6, 2e-6, 1000.0
        for _ in result["steps"]:
            previous = np.linalg.solve(
                [[inductance / h + r, 1], [-h / c, 1]],
                [inductance / h * previous[0] + v, previous[1]],
            )
            currents.append(previous[0])
        error = max(
            abs(np.array(currents) - [s["drive_current_A"] for s in result["steps"]])
        ) / max(currents)
        control.update(rlc_reference_error=float(error), rlc_reference_pass=bool(error < 1e-3))
    save(directory / "control.json", control)
    require(
        control["analytic_field_pass"] and control.get("rlc_reference_pass", True),
        "Independent analytic control failed",
    )
    plot(case)
    return control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True)
    demo = commands.add_parser("wire-demo")
    demo.add_argument("case", type=Path)
    demo.add_argument("--rlc", action="store_true")
    for stage in ("mesh", "solve", "audit", "plot"):
        p = commands.add_parser(stage)
        p.add_argument("case", type=Path)
        if stage in ("mesh", "solve"):
            p.add_argument("--timeout", type=float, default=900)
            p.add_argument("--memory-gib", type=float, default=8)
        if stage == "mesh":
            p.add_argument("--config", type=Path, required=True)
            p.add_argument("--msh", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.stage == "wire-demo":
            print(json.dumps(wire_demo(args.case, rlc=args.rlc)))
        elif args.stage == "mesh":
            mesh_case(
                args.case, args.config, args.msh, timeout=args.timeout, memory_gib=args.memory_gib
            )
        elif args.stage == "solve":
            return 0 if solve(args.case, timeout=args.timeout, memory_gib=args.memory_gib) else 2
        elif args.stage == "audit":
            result = audit(args.case)
            print(
                json.dumps({k: v for k, v in result.items() if k not in ("steps", "output_hashes")})
            )
            return 0 if result["numerical_checks_pass"] else 2
        else:
            print(plot(args.case))
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"{args.stage} failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
