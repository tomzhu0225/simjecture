"""Availability/version smoke; scientific commissioning is separate."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

bindir = Path(os.environ.get("QE_BIN", Path(sys.executable).parent))
checks = {
    "completed": False,
    "executables_present": False,
    "version_matches": False,
    "expected_no_input_diagnostic": False,
}
report = {"checks": checks, "scope": "deployment availability, not numerical validity"}
try:
    checks["executables_present"] = all(
        (bindir / n).is_file() for n in ("pw.x", "dos.x", "bands.x", "projwfc.x")
    )
    result = subprocess.run(
        [str(bindir / "pw.x")], input="", capture_output=True, text=True, timeout=30, check=False
    )
    report["startup_stdout"] = result.stdout
    report["startup_stderr"] = result.stderr
    report["startup_returncode"] = result.returncode
    text = result.stdout + result.stderr
    checks["expected_no_input_diagnostic"] = (
        result.returncode == 1
        and "Error in routine  read_namelists" in text
        and "could not find namelist &control" in text
    )
    checks["version_matches"] = re.search(r"\bPWSCF\s+v\.7\.4(?=\s|$)", result.stdout) is not None
    checks["completed"] = True
except (OSError, subprocess.SubprocessError) as error:
    report["error"] = str(error)
Path("qe_runtime_smoke.json").write_text(json.dumps(report, indent=2) + "\n")
raise SystemExit(0 if all(checks.values()) else 1)
