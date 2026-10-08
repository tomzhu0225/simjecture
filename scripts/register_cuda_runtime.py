"""Materialize the CUDA capability for this host after successful build/probe."""

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
runtime = root / ".runtime/warpx-cuda-openpmd"
config = json.loads((root / "capabilities/warpx-cuda-openpmd-26.07.json").read_text())
config["runtime_root"] = str(runtime)
package = runtime / "lib/python3.12/site-packages/pywarpx"
# Source-built wheels can place the active binding and pyAMReX under a nested
# site-packages directory. Include those native libraries in the frozen identity.
solver_libraries = sorted(package.rglob("*.so"))
if not solver_libraries:
    raise SystemExit("The compiled WarpX Python library is missing")
config["identity_files"] = sorted(
    set(config.get("identity_files", []))
    | {str(path.relative_to(runtime)) for path in solver_libraries}
)
if (runtime / "conda-meta/history").is_file():
    config["identity_files"].append("conda-meta/history")
config["read_only_mounts"] = {
    "/opt/acs-dependencies/cuda": str(root / ".runtime/cuda-toolkit-12.4"),
    "/opt/acs-dependencies/io": str(root / ".runtime/warpx-cuda-openpmd-deps"),
}
if Path("/dev/dxg").exists():
    config["device_paths"] = ["/dev/dxg"]
    config["read_only_mounts"]["/opt/acs-dependencies/wsl-lib"] = "/usr/lib/wsl/lib"
else:
    config["device_paths"] = [
        str(p)
        for p in map(
            Path, ("/dev/nvidia0", "/dev/nvidiactl", "/dev/nvidia-uvm", "/dev/nvidia-uvm-tools")
        )
        if p.exists()
    ]
    config["environment"]["LD_LIBRARY_PATH"] = ":".join(
        p for p in config["environment"]["LD_LIBRARY_PATH"].split(":") if "wsl-lib" not in p
    )
if not config["device_paths"]:
    raise SystemExit("No GPU devices are available for capability registration")
output = runtime / "capabilities"
output.mkdir(exist_ok=True)
path = output / "warpx-cuda-openpmd-26.07.json"
path.write_text(json.dumps(config, indent=2) + "\n")
print(f"Host CUDA capability: {path}")
