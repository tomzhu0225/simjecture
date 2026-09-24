import argparse
import json
import time
from pathlib import Path

from conjecture_solver.research_journal import journal_entries
from conjecture_solver.research_service import ResearchService
from conjecture_solver.research_supervisor import ResearchSupervisor

root = Path("/srv/simjecture/studies/automatic-journal-check-20260924")
s = ResearchService.create(
    root,
    "For n from 0 to 12, the inclusive sum equals n*(n+1)//2.",
    wall_seconds=1800,
    execution_backend="proot-cooperative",
)
protocol = (
    "Inspect exact finite arithmetic. Implementation bugs and failed e"
    "xecutions are not counterexamples to the mathematical claim. Pres"
    "erve uncertainty until independent review."
)
s.freeze_protocol(protocol)
instructions = root / "operator.txt"
instructions.write_text(protocol)
source = (
    "import json\nfrom pathlib import Path\nrows=[{'n':n,'value':sum(ran"
    "ge(nOFFSET)),'expected':n*(n+1)//2} for n in range(13)]\nPath('res"
    "ult.json').write_text(json.dumps({'mismatch_count':sum(r['value']"
    "!=r['expected'] for r in rows),'rows':rows}))\n"
)
records = []
for key, code in [
    ("baseline", source.replace("nOFFSET", "n")),
    ("crash", 'raise RuntimeError("deliberate execution-failure control")\n'),
    ("corrected", source.replace("nOFFSET", "n+1")),
]:
    (s.work / "calc.py").write_text(code)
    receipt = s.run("calc.py", outputs=["result.json"], stage="exploration", key=key)
    while s._read("experiments", receipt["id"])["status"] in ["queued", "running"]:
        time.sleep(0.1)
    records.append(s._read("experiments", receipt["id"]))
args = argparse.Namespace(
    campaign=root,
    state_dir=root / "supervisor",
    instructions_file=instructions,
    wall_seconds=1800,
    turn_seconds=60,
    backend="codex",
    executable="/usr/local/bin/codex-mimo",
    model="mimo-v2.6-pro",
    judge_model="mimo-v2.6-pro",
)
sup = ResearchSupervisor(args)
sup.maintain_journal()
result = {
    "attempts": [
        {k: r.get(k) for k in ["id", "key", "status", "purpose", "parent_experiment", "plan"]}
        for r in records
    ],
    "worker_notes": len(s.notes()["notes"]),
    "automatic_entries": len(journal_entries(s)),
    "summary_files": len(list((root / "journal/summaries").glob("*.json"))),
    "summary_seconds": sup.state.get("journal_summary_seconds"),
    "summary_error": sup.state.get("journal_summary_error"),
    "usage_by_thread": sup.state.get("usage_by_thread"),
    "completed": s.status()["completed"],
}
(root / "validation.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
