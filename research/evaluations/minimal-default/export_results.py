"""Export completed follow-up measurements without private transcripts."""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = REPO / ".private/minimal-default/simple"
spec = importlib.util.spec_from_file_location(
    "usage", HERE.parent / "frontier-workflow/token_usage.py"
)
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)
manifest = json.loads((BASE / "launch.json").read_text())
scores = json.loads((BASE / "scores.json").read_text())
index = usage.session_index(Path.home() / ".codex/sessions")
rows = []
for score in scores:
    directory = BASE / score["run"]
    campaign = directory / "campaign"
    prompts = sorted((campaign / "supervisor").glob("turn-*/task.txt"))
    accounting = usage.collect_run(directory, index)
    reviews = [json.loads(p.read_text()) for p in (campaign / "reviews").glob("*.json")]
    rows.append(
        dict(
            task=score["task"],
            wall_seconds=score["wall_seconds"],
            independent_assessment=score["review"],
            internal_status=json.loads((campaign / "supervisor/state.json").read_text())["status"],
            usage=accounting["combined_reported_usage"],
            categories=accounting["categories"],
            worker_prompt_bytes=[p.stat().st_size for p in prompts],
            reviews=[
                {k: r.get(k) for k in ["claim", "disposition", "challenge", "verdict"]}
                for r in reviews
            ],
        )
    )
threads = {}
for path in BASE.glob("external-grading/*/response.json"):
    records = list(usage.records(path))
    for record in records:
        if record.get("type") == "thread.started":
            tid = record["thread_id"]
            files = index.get(tid, [])
            fallback = [r.get("usage") for r in records if r.get("type") == "turn.completed"]
            threads[tid] = (
                usage.cumulative_usage(files[0])["usage"]
                if len(files) == 1
                else fallback[-1]
                if fallback
                else None
            )
result = dict(
    model="glm-5.3",
    runs=rows,
    frozen_source_sha256=manifest["source_hashes"],
    external_grading_usage=usage.add_usage(threads.values()),
    external_threads_without_usage=sum(v is None for v in threads.values()),
    limitations=[
        "One trial per task; no causal attribution to individual changes.",
        "Counters count cumulative usage once per thread, not billing.",
        "Cached input is a subset of input; reasoning output a subset of output.",
        "Interrupted requests without counters and implementation-assistant usage excluded.",
    ],
)
(HERE / "measurements.json").write_text(json.dumps(result, indent=2) + "\n")
for row in rows:
    print(row["task"], round(row["wall_seconds"]), row["usage"], row["worker_prompt_bytes"])
