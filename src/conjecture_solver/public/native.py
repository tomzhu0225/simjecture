"""Host-owned, parameterized native examples; never executes user/model code.

This module is frozen into each experiment so the diagnostic implementation is
reviewable. The operator registry pins binaries and templates by SHA-256.
"""

import hashlib
import json
import math
import os
import re
import subprocess
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

OUTPUTS = ("result.json", "evolution.png", "raw-output.zip", "provenance.json")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def registry(root):
    settings = root / "settings.json"
    config = json.loads(settings.read_text()) if settings.exists() else {}
    path = config.get("tools_registry")
    if not path:
        return []
    value = json.loads(Path(path).read_text())
    return [entry for entry in value["tools"] if entry.get("qualified") is True]


def validate(entry, parameters):
    """A small numerical schema, no paths, expressions, arguments or commands."""
    if not isinstance(parameters, dict) or set(parameters) - set(entry["parameters"]):
        raise ValueError("Use only the documented numerical parameters")
    result = {}
    for name, rule in entry["parameters"].items():
        value = parameters.get(name, rule["default"])
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or (rule.get("integer") and not isinstance(value, int))
            or ("choices" in rule and value not in rule["choices"])
            or value < rule.get("min", -math.inf)
            or value > rule.get("max", math.inf)
        ):
            raise ValueError(f"{name} is outside the commissioned range")
        result[name] = value
    return result


def materialize(entry, parameters, destination):
    values = validate(entry, parameters)
    binary, template = Path(entry["binary"]), Path(entry["template"])
    if digest(binary) != entry["binary_sha256"] or digest(template) != entry["template_sha256"]:
        raise ValueError("The qualified runtime changed; operator requalification is required")
    text = template.read_text()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    if "{{" in text:
        raise ValueError("Unresolved operator template parameter")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "native-input.txt").write_text(text)
    case = {
        "tool": entry["id"],
        "name": entry["name"],
        "family": entry["family"],
        "binary": str(binary),
        "binary_sha256": entry["binary_sha256"],
        "template_sha256": entry["template_sha256"],
        "parameters": values,
        "scope": entry["scope"],
        "geometry": entry.get("geometry"),
        "units": entry.get("units", {}),
        "qualification": entry["qualification"],
        "timeout": entry.get("timeout", 120),
    }
    (destination / "native-case.json").write_text(json.dumps(case, indent=2) + "\n")
    return case


def reduced_table(path, total_label):
    """Select the realized total by name; never double-count component totals."""
    import numpy as np

    header = path.open().readline().strip()
    labels = re.findall(r"\[\d+\]([^\s]+)", header)
    if labels[:2] != ["step()", "time(s)"] or total_label not in labels:
        raise ValueError("Unknown reduced energy schema: " + header)
    table = np.atleast_2d(np.loadtxt(path))
    if table.shape[1] != len(labels) or not np.all(np.isfinite(table)):
        raise ValueError("Incomplete or non-finite reduced diagnostics")
    return table[:, 0], table[:, 1], table[:, labels.index(total_label)], header


def analyze_warpx(case):
    import numpy as np
    from matplotlib import pyplot as plt

    step, time_axis, field, field_header = reduced_table(Path("reduced/field.txt"), "total_lev0(J)")
    particle_step, particle_time, kinetic, particle_header = reduced_table(
        Path("reduced/particle.txt"), "total(J)"
    )
    if not np.array_equal(step, particle_step) or not np.array_equal(time_axis, particle_time):
        raise ValueError("Field and particle diagnostic coordinates do not agree")
    if len(step) < 2 or int(step[-1]) != case["parameters"]["steps"]:
        raise ValueError("The requested simulation interval is incomplete")
    total = field + kinetic
    if total[0] <= 0:
        raise ValueError("No positive initial energy for a relative energy estimate")
    drift = (total - total[0]) / total[0]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    axes[0].plot(time_axis, field, label="Grid field")
    axes[0].plot(time_axis, kinetic, label="Particle kinetic")
    axes[0].plot(time_axis, total, "--", label="Sum of recorded channels")
    axes[0].set(xlabel="Time (s)", ylabel="Energy (J)", title=case["name"])
    axes[0].legend()
    axes[1].plot(time_axis, drift)
    axes[1].set(xlabel="Time (s)", ylabel="Relative energy change")
    for axis in axes:
        axis.grid(alpha=0.2)
    fig.savefig("evolution.png", dpi=150)
    plt.close(fig)
    return {
        "completed_steps": int(step[-1]),
        "final_time_s": float(time_axis[-1]),
        "field_energy_J": float(field[-1]),
        "particle_kinetic_energy_J": float(kinetic[-1]),
        "initial_recorded_energy_J": float(total[0]),
        "maximum_field_fraction_of_initial_recorded_energy": float(np.max(field) / total[0]),
        "relative_recorded_energy_change": float(drift[-1]),
        "maximum_absolute_relative_recorded_energy_change": float(np.max(np.abs(drift))),
        "diagnostic_headers": {"field": field_header, "particle": particle_header},
        "energy_budget_scope": (
            "Closed periodic Cartesian plasma: field plus particle kinetic energy."
            if case["geometry"] != "RZ"
            else "RZ has an absorbing radial particle boundary: field plus retained particle "
            "energy excludes escaped energy and is not a closed total-energy balance."
        ),
    }


def analyze_flash(case):
    import h5py
    import numpy as np
    from matplotlib import pyplot as plt

    outputs = []
    for path in Path(".").glob("*hdf5_plt_cnt_*"):
        with h5py.File(path, "r") as data:
            scalars = {row[0].decode().strip(): float(row[1]) for row in data["real scalars"]}
        if not math.isfinite(scalars["time"]):
            raise ValueError("FLASH snapshot time is non-finite")
        outputs.append((scalars["time"], path))
    outputs.sort(key=lambda row: (row[0], str(row[1])))
    if len(outputs) < 2 or outputs[0][0] == outputs[-1][0]:
        raise ValueError("Initial and final FLASH plotfiles are required")
    with h5py.File(outputs[-1][1], "r") as data:
        scalars = {row[0].decode().strip(): float(row[1]) for row in data["real scalars"]}
        if abs(scalars["time"] - case["parameters"]["end_time"]) > max(
            1e-10, 1e-7 * case["parameters"]["end_time"]
        ):
            raise ValueError("FLASH did not reach the requested physical time")
        density = np.asarray(data["dens"])[0, 0]
        if not np.all(np.isfinite(density)) or np.any(density <= 0):
            raise ValueError("FLASH density is non-finite or non-positive")
        bounds = np.asarray(data["bounding box"])[0]
        fig, axis = plt.subplots(figsize=(7, 5), layout="constrained")
        if density.shape[0] == 1:
            x = np.linspace(bounds[0, 0], bounds[0, 1], density.shape[1], endpoint=False)
            x += (bounds[0, 1] - bounds[0, 0]) / (2 * density.shape[1])
            axis.plot(x, density[0])
            axis.set(xlabel="x (code length)", ylabel="Density (code units)")
        else:
            image = axis.imshow(
                density, origin="lower", aspect="equal", extent=[*bounds[0], *bounds[1]]
            )
            axis.set(
                xlabel="R" if case["geometry"] == "RZ" else "x",
                ylabel="Z" if case["geometry"] == "RZ" else "y",
            )
            fig.colorbar(image, ax=axis, label="Density (code units)")
        axis.set_title(case["name"] + f" · t = {scalars['time']:.4g}")
        fig.savefig("evolution.png", dpi=150)
        plt.close(fig)
    return {
        "final_time_code_units": scalars["time"],
        "minimum_density": float(density.min()),
        "maximum_density": float(density.max()),
        "density_shape": list(density.shape),
        "checks": {"finite_positive_density": True, "requested_time_reached": True},
        "diagnostic_scope": "Execution and field-output checks; no automatic conservation "
        "or physical claim approval. Raw plotfiles retain native CGS/code-unit definitions.",
    }


@contextmanager
def gpu_lease(case):
    if case["family"] == "warpx":
        import fcntl

        with open("/srv/simjecture-public/gpu.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield
    else:
        yield


def execute_case():
    """The installed host module is copied as public_native.py into the receipt."""
    import matplotlib

    matplotlib.use("Agg")
    case = json.loads(Path("native-case.json").read_text())
    if digest(case["binary"]) != case["binary_sha256"]:
        raise ValueError("Native executable changed after qualification")
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    # Child runtimes use their own environment, not the launcher's injected
    # site-packages. Otherwise CHERAB's NumPy 1.x extensions load public NumPy 2.x.
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    # Separate hosted jobs serialize GPU examples through a host-owned lock.
    # The wait is inside the experiment timeout and cancellation process group.
    if case["family"] == "warpx":
        environment["CUDA_VISIBLE_DEVICES"] = "0"
        command = [case["binary"], "native-input.txt"]
    elif case["family"] == "flash":
        Path("flash.par").write_bytes(Path("native-input.txt").read_bytes())
        command = [case["binary"]]
    elif case["family"] == "iter":
        command = [case["binary"], "iter-demo.py"]
    else:
        raise ValueError("Unknown host-owned runtime family")
    started = time.time()
    with gpu_lease(case), Path("native.log").open("w") as log:
        subprocess.run(
            command,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=case["timeout"],
            check=True,
        )
    if case["family"] == "warpx":
        metrics = analyze_warpx(case)
    elif case["family"] == "flash":
        metrics = analyze_flash(case)
    else:
        import shutil

        payload = json.loads(Path("iter_pack_demo.json").read_text())
        if not payload["checks"]["completed"]:
            raise ValueError("ITER diagnostics readiness checks failed")
        shutil.copyfile("iter_pack_demo.png", "evolution.png")
        metrics = payload
    result = {
        "tool": case["tool"],
        "name": case["name"],
        "parameters": case["parameters"],
        "scope": case["scope"],
        "units": case["units"],
        "metrics": metrics,
        "execution_seconds": time.time() - started,
        "qualification": case["qualification"],
    }
    Path("result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    Path("provenance.json").write_text(
        json.dumps(
            {
                **case,
                "realized_input_sha256": digest("native-input.txt"),
                "diagnostic_source_sha256": digest("public_native.py"),
            },
            indent=2,
        )
        + "\n"
    )
    preserve_raw_output()
    print(json.dumps(result, allow_nan=False))


def preserve_raw_output():
    """Retain application output names, not just the example template's prefix."""
    with zipfile.ZipFile("raw-output.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(Path(".").rglob("*")):
            if (
                path.is_file()
                and not path.is_symlink()
                and (
                    path.parts[0] == "reduced"
                    or path.parts[0].startswith("native-plot")
                    or "hdf5_plt_cnt_" in path.name
                    or "hdf5_chk_" in path.name
                    or path.name
                    in {
                        "native.log",
                        "flash.par",
                        "native-input.txt",
                        "spectra.csv",
                        "profiles.nc",
                        "iter_pack_demo.json",
                    }
                )
            ):
                archive.write(path, str(path))


if __name__ == "__main__":
    execute_case()
