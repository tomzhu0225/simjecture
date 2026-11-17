"""Read-only pilot telemetry; never call a model or modify a scientific record."""

import json
import sqlite3
import sys
from pathlib import Path

from research_decision.storage import read_json

root = Path(__file__).resolve().parents[1]
cfg = read_json(root / "config/pipeline.local.json")
print(json.dumps(dict(status=read_json(root / "pilot/status.json"))))
for case in sorted((Path(cfg["case_store"]) / "runs").glob("*pilot-*")):
    if "--autonomous" in sys.argv and "-auto-" not in case.name:
        continue
    result = dict(case=case.name, executions={}, suggestions=[], decisions=[])
    for path in (case / "experiments").glob("*.json"):
        row = read_json(path)
        status = row["status"]
        result["executions"][status] = result["executions"].get(status, 0) + 1
    database = case / "decision-audit/events.sqlite"
    if database.exists():
        connection = sqlite3.connect("file:" + str(database) + "?mode=ro", uri=True)
        for kind, payload in connection.execute("select kind,payload from events order by sequence"):
            value = json.loads(payload)
            if kind == "raw_advice":
                reply = value["raw_reply"]
                result["suggestions"].append(
                    dict(
                        input_tokens=len(reply.get("input_ids", [])),
                        output_tokens=len(reply.get("response_ids", [])),
                        invalid=bool(reply.get("validation_error")),
                        inference_seconds=reply.get("inference_wall_seconds"),
                    )
                )
            if kind == "decision_audit":
                result["decisions"].append(
                    dict(
                        components=value["component_sources"],
                        student_credit_eligible=value["student_positive_credit_eligible"],
                    )
                )
        connection.close()
    print(json.dumps(result))
