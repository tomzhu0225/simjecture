"""Operator-only registry templates for native public examples.

Qualification is separate: this script writes installed but unqualified entries.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path("/opt/simjecture-public/tools")
WARPX = Path("/opt/simote/radiation-production-features-20260930/warpx")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    templates = ROOT / "templates"
    templates.mkdir(exist_ok=True)
    entries = []
    for dim, ndim in (("1d", 1), ("2d", 2), ("rz", 2), ("3d", 3)):
        name = "inputs_test_1d_langmuir_multi" if dim == "1d" else "inputs_base_" + dim
        original = WARPX / "Examples/Tests/langmuir" / name
        text = original.read_text().split("# Diagnostics")[0]
        lines = []
        for line in text.splitlines():
            if line.startswith("max_step ="):
                line = "max_step = {{steps}}"
            elif line.startswith("amr.n_cell ="):
                line = "amr.n_cell = " + " ".join(["{{cells}}"] * ndim)
            elif line.startswith("my_constants.epsilon ="):
                line = "my_constants.epsilon = {{amplitude}}"
            lines.append(line)
        text = (
            "\n".join(lines)
            + "\n"
            + """
diagnostics.diags_names = diag1
diag1.diag_type = Full
diag1.intervals = {{steps}}
diag1.file_prefix = native-plot
warpx.reduced_diags_names = field particle
field.type = FieldEnergy
field.intervals = 1
field.path = reduced/
particle.type = ParticleEnergy
particle.intervals = 1
particle.path = reduced/
"""
        )
        template = templates / ("warpx-" + dim + ".txt")
        template.write_text(text)
        binary = ROOT / ("warpx-" + dim + "-cuda")
        entries.append(
            {
                "id": binary.name,
                "family": "warpx",
                "binary": str(binary),
                "binary_sha256": digest(binary),
                "template": str(template),
                "template_sha256": digest(template),
                "geometry": "RZ" if dim == "rz" else dim,
                "name": "WarpX " + dim.upper() + " · CUDA Langmuir wave",
                "scope": "Upstream Langmuir-wave kinetic PIC example. "
                + (
                    "Electrons/ions, absorbing radial boundary, axisymmetric RZ."
                    if dim == "rz"
                    else "Electron/positron pair plasma, periodic Cartesian domain."
                )
                + " No radiation or reconnection model in this example.",
                "parameters": {
                    "cells": {
                        "default": 16 if dim == "3d" else 64,
                        "choices": [16, 32] if dim == "3d" else [32, 64, 128],
                        "integer": True,
                    },
                    "steps": {"default": 80, "min": 10, "max": 200, "integer": True},
                    "amplitude": {"default": 0.01, "min": 0.001, "max": 0.05},
                },
                "units": {"time": "s", "length": "m", "energy": "J"},
                "upstream_input": str(original),
                "upstream_input_sha256": digest(original),
                "timeout": 120,
                "qualified": False,
                "qualification": "Pending native execution",
            }
        )

    common = """
restart = .false.
basenm = "native_"
log_file = "native-flash.log"
iProcs = 1
iGridSize = {{cells}}
cfl = 0.6
dtinit = 1.e-5
dtmin = 1.e-12
dtmax = 1.
tmax = {{end_time}}
nend = 100000
dr_shortenLastStepBeforeTMax = .true.
checkpointFileIntervalTime = 0.
checkpointFileIntervalStep = 0
plotfileIntervalTime = {{end_time}}
plotfileIntervalStep = 0
plot_var_1 = "dens"
plot_var_2 = "pres"
plot_var_3 = "velx"
plot_var_4 = "vely"
"""
    settings = {
        "1d": """
gamma = 1.4
xmin = 0.
xmax = 1.
xl_boundary_type = "outflow"
xr_boundary_type = "outflow"
sim_rhoLeft = 1.
sim_rhoRight = 0.125
sim_pLeft = 1.
sim_pRight = 0.1
sim_uLeft = 0.
sim_uRight = 0.
sim_xangle = 0.
sim_yangle = 90.
sim_posn = 0.5
""",
        "2d": """
gamma = 1.6666666666666667
xmin = 0.
xmax = 1.
ymin = 0.
ymax = 1.
xl_boundary_type = "periodic"
xr_boundary_type = "periodic"
yl_boundary_type = "periodic"
yr_boundary_type = "periodic"
jProcs = 1
jGridSize = {{cells}}
order = 2
RiemannSolver = "HLLD"
plot_var_5 = "magx"
plot_var_6 = "magy"
""",
        "rz": """
gamma = 1.4
xmin = 0.
xmax = 1.
ymin = -1.
ymax = 1.
xl_boundary_type = "reflecting"
xr_boundary_type = "outflow"
yl_boundary_type = "outflow"
yr_boundary_type = "outflow"
jProcs = 1
jGridSize = {{cells}}
sim_pAmbient = 1.e-5
sim_rhoAmbient = 1.
sim_expEnergy = 1.
sim_rInit = 0.1
sim_xctr = 0.
sim_yctr = 0.
sim_profFileName = "/dev/null"
""",
    }
    for dim, description in (
        ("1d", "Sod shock tube"),
        ("2d", "Orszag–Tang MHD vortex"),
        ("rz", "Sedov blast wave"),
    ):
        binary = ROOT / ("flash-" + dim)
        if not binary.exists():
            continue
        template = templates / ("flash-" + dim + ".txt")
        template.write_text(common + settings[dim])
        entries.append(
            {
                "id": binary.name,
                "family": "flash",
                "binary": str(binary),
                "binary_sha256": digest(binary),
                "template": str(template),
                "template_sha256": digest(template),
                "geometry": "RZ" if dim == "rz" else dim,
                "name": "FLASH " + dim.upper() + " · " + description,
                "scope": description + "; ideal-gas EOS, adaptive CFL timestep. "
                "Application-specific build; this example does not include radiation.",
                "parameters": {
                    "cells": {"default": 64, "choices": [32, 64, 128, 256], "integer": True},
                    "end_time": {
                        "default": 0.01 if dim == "rz" else 0.1,
                        "min": 0.001,
                        "max": 0.02 if dim == "rz" else 0.2,
                    },
                },
                "units": {"time": "code time", "length": "code length", "density": "code density"},
                "timeout": 120,
                "qualified": False,
                "qualification": "Pending native execution",
            }
        )

    python = ROOT / "iter-pack/bin/python"
    demo = Path("/opt/simjecture-public/tool-sources/skills/iter-pack/examples/diagnostics_demo.py")
    if python.exists() and (ROOT / "iter-pack/share/build-record.json").exists():
        template = templates / "iter.txt"
        template.write_text("Synthetic analytic diagnostics and IMAS round-trip; no user code.\n")
        entries.append(
            {
                "id": "iter-diagnostics",
                "name": "CHERAB / Raysect / IMAS diagnostics",
                "family": "iter",
                "binary": str(python),
                "binary_sha256": digest(python),
                "template": str(template),
                "template_sha256": digest(template),
                "demo_source": str(demo),
                "demo_source_sha256": digest(demo),
                "scope": "Analytic ray tracing, free-free density scaling, synthetic bolometers "
                "and IMAS netCDF I/O. Not a tokamak-discharge simulation.",
                "parameters": {},
                "timeout": 120,
                "qualified": False,
                "qualification": "Pending native execution",
            }
        )
    (ROOT / "registry.json").write_text(json.dumps({"tools": entries}, indent=2) + "\n")
    print("Prepared", len(entries), "native example templates")


if __name__ == "__main__":
    main()
