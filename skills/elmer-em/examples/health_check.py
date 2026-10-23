"""Run the independent cylinder control through the installed driver."""

import importlib.util
import json
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location("elmer_em", os.environ["SIMJECTURE_ELMER_DRIVER"])
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
try:
    result = driver.wire_demo(Path("wire-control"))
    report = {
        "checks": {
            "current_energy": result["numerical_checks_pass"],
            "analytic_wire": result["analytic_field_pass"],
        },
        "control": result,
    }
except Exception as exc:
    Path("elmer_health.json").write_text(json.dumps({"error": str(exc)}))
    raise
Path("elmer_health.json").write_text(json.dumps(report, indent=2) + "\n")
