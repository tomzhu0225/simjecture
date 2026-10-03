"""Commission a declared native WarpX executable without requiring PICMI bindings."""

import json
import os
import re
import subprocess
from pathlib import Path

executable = Path(os.environ["WARPX_EXECUTABLE"])
template = Path(os.environ["WARPX_PREFLIGHT_INPUT"])
text = template.read_text()
Path("inputs").write_text(text)
match = re.search(r"^diagnostics.diags_names\s*=\s*(.*)$", text, re.MULTILINE)
names = match[1].split() if match else ["diag1"]
overrides = [
    "max_step=2",
    "warpx.do_device_synchronize=0",
    "tiny_profiler.device_synchronize_around_region=0",
]
for name in names:
    overrides.extend(
        [name + ".intervals=1", name + ".file_prefix=diags/" + name, name + ".format=plotfile"]
    )
with Path("native-warpX.log").open("w") as log:
    result = subprocess.run(
        [str(executable), "inputs", *overrides], stdout=log, stderr=subprocess.STDOUT, timeout=90
    )
data = sorted(Path("diags").rglob("Header"))
checks = {
    "executable_present": executable.is_file(),
    "process_completed": result.returncode == 0,
    "native_output_created": bool(data),
}
if data:
    import numpy as np
    import yt

    ds = yt.load(str(data[-1].parent))
    fields = ds.field_list
    checks["evolved_state_readable"] = float(ds.current_time) > 0
    grid = ds.covering_grid(0, ds.domain_left_edge, ds.domain_dimensions)
    candidates = [f for f in fields if f[0] == "boxlib"]
    checks["native_output_readable"] = bool(candidates) and all(
        np.isfinite(np.asarray(grid[f])).all() for f in candidates[:3]
    )
else:
    checks["native_output_readable"] = False
checks["completed"] = all(checks.values())
Path("warpx_native_cli_smoke.json").write_text(
    json.dumps({"checks": checks, "scope": "Execution only"}, indent=2) + "\n"
)
if not checks["completed"]:
    raise SystemExit("Native WarpX preflight failed; inspect native-warpX.log")
