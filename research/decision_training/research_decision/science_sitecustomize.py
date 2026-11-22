"""Case-local SDK instrumentation inside the existing filesystem sandbox only."""

from pathlib import Path

case = Path.cwd().resolve()
while case.parent != case and not (case / "study-run.json").exists():
    case = case.parent
if (case / "study-run.json").exists():
    import conjecture_solver.research_service as service

    from research_decision.simjecture_bridge import DecisionLab

    DecisionLab._native_class = service.Lab
    service.Lab = DecisionLab
