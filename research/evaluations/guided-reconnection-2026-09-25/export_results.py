"""Export public receipts and reported usage; never inspect private reasoning."""

import argparse
import importlib.util
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def read(p):
    return json.loads(p.read_text()) if p.exists() else {}


def collect(root):
    helper_path = Path(__file__).resolve().parent.parent / "frontier-workflow/token_usage.py"
    spec = importlib.util.spec_from_file_location("usage", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    index = helper.session_index(Path.home() / ".codex/sessions")
    rows = []
    for arm in ["minimal-fixed", "structured-fixed", "minimal", "structured-v2"]:
        base = root / arm
        state = read(base / "supervisor/state.json")
        accounting = helper.collect_run(base, index)
        totals = accounting["combined_reported_usage"]
        experiments = [read(p) for p in sorted((base / "experiments").glob("*.json"))]
        successes = [e["finished_at"] for e in experiments if e.get("status") == "succeeded"]
        for path in (base / "jobs").rglob("result.json"):
            job = read(path)
            if job.get("status") == "succeeded":
                successes.append(datetime.fromisoformat(job["finished_at"]).timestamp())
        first_success = (min(successes) - state["started_at"]) if successes else None
        ledger = read(base / "hypothesis_ledger.json")
        claims = ledger.get("claims", [])
        if isinstance(claims, dict):
            claims = list(claims.values())
        rows.append(
            dict(
                arm=arm,
                status=state.get("status"),
                rounds=state.get("round"),
                seconds_to_first_success=first_success,
                reported_usage=totals,
                usage_categories=accounting["categories"],
                included_in_comparison=arm.endswith("-fixed"),
                usage_incomplete_turns=state.get("usage_incomplete_turns", 0),
                experiment_status=dict(Counter(e.get("status") for e in experiments)),
                claims=[{k: c.get(k) for k in ["id", "status", "statement"]} for c in claims],
                kernel_jobs=[
                    {k: read(p).get(k) for k in ["job_id", "status", "returncode"]}
                    for p in sorted((base / "jobs").rglob("result.json"))
                ],
                methods=[
                    {k: read(p).get(k) for k in ["id", "scope", "status", "verdict"]}
                    for p in sorted((base / "methods").glob("*.json"))
                ],
            )
        )
    return dict(
        arms=rows,
        accounting="Latest reported cumulative receipt per unique native thread; "
        "workers and reviewers included when emitted. Interrupted/unreported usage can be missing. "
        "Cached input is a subset of input. These are tokens, not billed cost.",
        limitations=read(root / "pilot-fixed-manifest.json").get("limitations", []),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("private_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(collect(args.private_root), indent=2) + "\n")
