"""Export measurements without raw model transcripts or private session paths."""

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "usage", HERE.parent / "frontier-workflow/token_usage.py"
)
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)
base = REPO / ".private/lean-benchmark"
index = usage.session_index(Path.home() / ".codex/sessions")
rows = []
for group in ("simple", "plasma", "simple-current", "plasma-current", "simple-scoped"):
    for score in json.loads((base / group / "scores.json").read_text()):
        row = {
            k: score.get(k)
            for k in (
                "run",
                "task",
                "workflow",
                "wall_seconds",
                "returncode",
                "scientific_completion",
                "recognized_numerical_limitation",
                "reason",
            )
        }
        row["revision_group"] = group
        row["included_in_comparison"] = score.get("included_in_comparison", True)
        row["usage"] = score["token_accounting"]["combined_reported_usage"]
        row["usage_categories"] = score["token_accounting"]["categories"]
        rows.append(row)


def account(paths):
    threads = {}
    for path in paths:
        events = list(usage.records(path))
        fallback = [e.get("usage") for e in events if e.get("type") == "turn.completed"]
        for event in events:
            if event.get("type") != "thread.started":
                continue
            tid = event["thread_id"]
            sessions = index.get(tid, [])
            threads[tid] = (
                usage.cumulative_usage(sessions[0])["usage"]
                if len(sessions) == 1
                else (fallback[-1] if fallback else None)
            )
    return {
        "unique_threads": len(threads),
        "threads_without_usage": sum(v is None for v in threads.values()),
        "reported_usage": usage.add_usage(threads.values()),
    }


extras = {}
for name, paths in {
    "external_grading_current": [p for p in base.glob("*/external-grading/**/response.json")],
    "external_grading_superseded": [p for p in base.glob("*/external-grading-*/**/response.json")],
    "scoped_review_diagnostic": list((base / "scoped-review-audit").rglob("response.json")),
    "invalidated_affinity_attempt": list(
        (base / "plasma-affinity-invalidated").rglob("response.json")
    ),
}.items():
    extras[name] = account(paths)
provenance = {}
for name in (
    "implementation",
    "implementation-hard",
    "implementation-current",
    "implementation-scoped",
):
    root = base / name
    provenance[name] = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
result = {
    "requested_model": "glm-5.3",
    "runs": rows,
    "separate_usage": extras,
    "frozen_implementation_sha256": provenance,
    "accounting": (
        "Last cumulative usage once per unique native thread. "
        "Cached input is a subset of input; reasoning output is a subset of output. "
        "Missing counters are not zero. Interrupted requests may be unmeasured. "
        "Root implementation assistant usage and subscription billing are unavailable."
    ),
}
(HERE / "measurements.json").write_text(json.dumps(result, indent=2) + "\n")
for key, value in extras.items():
    print(key, value)
