"""Bounded runtime/output check; does not establish cylinder-flow accuracy."""

import importlib.util
import json
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location("lbm_driver", os.environ["SIMJECTURE_LBM_DRIVER"])
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
args = driver.parser().parse_args(
    [
        "--nd",
        "8",
        "--height",
        "8",
        "--length",
        "12",
        "--inlet",
        "4",
        "--steps",
        "64",
        "--out",
        "health",
        "--no-plot",
    ]
)
summary = driver.simulate(args)
Path("lbm_health.json").write_text(
    json.dumps(
        {
            "checks": summary["checks"],
            "device": summary["device"],
            "scope": "Runtime and output smoke check only.",
        },
        indent=2,
    )
    + "\n"
)
