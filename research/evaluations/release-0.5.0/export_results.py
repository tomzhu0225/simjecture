"""Export release validation metrics; retain native transcripts and fields privately."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIVATE = REPO / ".private/release-validation"
BASE = PRIVATE / "plasma"
spec = importlib.util.spec_from_file_location(
    "accounting", HERE.parent / "frontier-workflow/token_usage.py"
)
accounting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accounting)
manifest = json.loads((BASE / "launch.json").read_text())
entry = manifest["runs"][0]
if "finished_at" not in entry:
    raise SystemExit("Release study is still running")
directory = Path(entry["path"])
index = accounting.session_index(Path.home() / ".codex/sessions")
usage = accounting.collect_run(directory, index)
scores = json.loads((BASE / "scores.json").read_text())
checks = json.loads((BASE / "plasma-independent-checks.json").read_text())[directory.name]
report = json.loads((directory / "campaign/research_report.json").read_text())
public_checks = {k: v for k, v in checks.items() if k != "raw_field_cases"}
# Reported-integral checks carry only relative artifact paths and numerical errors.
comparison = json.loads((PRIVATE / "source-comparison.json").read_text())
for row in comparison:
    candidate = (
        PRIVATE / "venv/lib/python3.12/site-packages/conjecture_solver" / row["module"]
    ).read_bytes()
    final = (REPO / "src/conjecture_solver" / row["module"]).read_bytes()
    row.update(
        candidate_sha256=hashlib.sha256(candidate).hexdigest(),
        final_sha256=hashlib.sha256(final).hexdigest(),
        same_ast=ast.dump(ast.parse(candidate)) == ast.dump(ast.parse(final)),
    )
result = dict(
    package="0.5.0",
    requested_model="glm-5.3",
    candidate_wheel_sha256=manifest["wheel_sha256"],
    elapsed_seconds=entry["finished_at"] - entry["launched_at"],
    returncode=entry["returncode"],
    internal_status=report["status"],
    scientific_completion=report["completed"],
    experiments=[
        dict(
            id=e["id"],
            status=e["status"],
            timeout=e["timeout"],
            returncode=e.get("execution", {}).get("returncode"),
            timed_out=e.get("execution", {}).get("timed_out"),
        )
        for e in report["experiments"]
    ],
    usage=usage["combined_reported_usage"],
    usage_categories=usage["categories"],
    independent_checks=public_checks,
    external_assessment=scores[0].get("review"),
    source_comparison=comparison,
    accounting="Last cumulative native usage once per thread; cached input is part of input. "
    "Reasoning output is part of output. Missing counters are not zero. "
    "No billing or implementation-assistant usage is inferred.",
)
# External grading remains a separate cost, not part of the worker's wall budget.
extra = []
for response in BASE.glob("external-grading/*/response.json"):
    events = list(accounting.records(response))
    ids = {e["thread_id"] for e in events if e.get("type") == "thread.started"}
    for tid in ids:
        paths = index.get(tid, [])
        fallback = [e.get("usage") for e in events if e.get("type") == "turn.completed"]
        extra.append(
            accounting.cumulative_usage(paths[0])["usage"]
            if len(paths) == 1
            else fallback[-1]
            if fallback
            else None
        )
result["external_grading_usage"] = accounting.add_usage(extra)
(HERE / "measurements.json").write_text(json.dumps(result, indent=2) + "\n")
print(result["internal_status"], result["usage"])
