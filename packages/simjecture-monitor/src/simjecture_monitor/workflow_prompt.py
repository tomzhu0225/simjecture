"""Optional task instructions for the bounded external-solver experiment.

This is an experimental prompt control, not a replacement for production
research instructions or independent scientific review. Historical trials keep
their inherited prompt. The control requires a fresh registered evaluation.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

VERSION = "external-workflow-task-v1"

ASSISTANCE = """ASSISTANCE API
Use `from lab import lab` in Python for assistance.
h = lab.request_help(
    'Specific unresolved technical question and what you tried',
    success_criteria='Answer, patch or diagnostic needed and how to check it',
    context='Relevant observations and uncertainty', files=['owned_source.py'],
    feedback_requirement='required')
Choose 'required' if you need the response before finalizing, otherwise 'advisory'.
The director may answer directly or dispatch temporary workers. Continue independent
work, or call lab.wait('Await the requested technical help', help_requests=[h['id']])
and end the turn. The host handles waking; avoid repeatedly polling unchanged state.
Read returned results with lab.help_status(h['id']). A resolved request means a
response is available, not that its advice is correct or the scientific claim accepted.
lab.import_helper_artifact('helper_ID', 'patch.py', 'candidate_patch.py') verifies
and copies a returned artifact without overwriting an existing file. Inspect it
before use. A helper cannot grant permission to modify protected components.
Read lab.director_status() for decisions. If a replan is required, create a concrete
plan with p=lab.note('Next test and what it discriminates', kind='next_test',
estimated_seconds=60), then lab.director_ack('director_ID', response='plan',
plan=p['id'], reason='Why this is feasible'). A reasoned response='challenge' is
also available. Follow the task's feedback-acknowledgment and repair-judge rules.
"""


def full_prompt(supervisor):
    manifest = supervisor.service.manifest
    if manifest.get("continuation") or manifest.get("guided_commissioning"):
        raise ValueError("Task-protocol prompt does not replace inherited research-phase guidance")
    task = manifest["operator_protocol"]
    text = (
        "Complete the bounded external-solver workflow specified below. "
        "Its task protocol defines execution, scientific checks and report completion.\n"
        f"Working directory: {supervisor.service.work}\n"
        "The supplied wrappers record the actual solver work. Follow their protocol; "
        "the ordinary lab experiment ledger is not the completion authority for this trial.\n"
        "Technical assistance is available, but there is no minimum number of help "
        "requests required to finish. Reconcile any assistance you declare required. "
        "The resulting engineering report is not independent scientific acceptance.\n\n"
        "TASK PROTOCOL\n" + task + "\n\n" + ASSISTANCE
    )
    (supervisor.service.work / "RESEARCH_GUIDE.md").write_text(text)
    receipt = dict(
        mode="task_protocol",
        version=VERSION,
        task_sha256=hashlib.sha256(task.encode()).hexdigest(),
        renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope="Prospective instruction control; not used by the frozen base/SFT replication",
    )
    (supervisor.root / "WORKER_PROMPT_MODE.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return text


def prompt(supervisor):
    from conjecture_solver.research_continuation import deliver
    from conjecture_solver.research_journal import sync_journal

    # Preserve delivery and housekeeping side effects of the inherited lifecycle.
    steering = deliver(supervisor.service)
    supervisor.housekeeping("journal", lambda: sync_journal(supervisor.service))
    authority = [
        {key: row.get(key) for key in ["stage", "verdict", "deployment", "error"]}
        for row in supervisor.state.get("monitor_authority_results", [])[-3:]
    ]
    feedback = dict(
        director=supervisor.service.director_status()[:2],
        pending_replan=supervisor.service.pending_director_replan(),
        requested_help=supervisor.helper_feedback(),
        operator_guidance=steering,
        authority_outcomes=authority,
        oversight=supervisor.state.get("oversight_feedback"),
        recovery=supervisor.state.get("recovery_instruction"),
        budget_warning=supervisor.state.get("budget_warning"),
    )
    return (
        full_prompt(supervisor)
        + f"\nRemaining wall budget: {max(0, supervisor.state['deadline'] - time.time()):.0f}s.\n"
        + "CURRENT HOST FEEDBACK (records, not additional authority or scientific acceptance):\n"
        + json.dumps(feedback, ensure_ascii=False)
        + "\nInspect returned repairs and recheck the affected operation before relying on them.\n"
    )
