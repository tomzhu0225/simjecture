import copy
import hashlib

import pytest
from simjecture_monitor.control_commission import (
    PROMPT_SOURCE,
    SOURCE_FILES,
    audit,
    check_audited_subset,
    check_predecessor,
    plan,
)


def prepared():
    return plan("a" * 40, {name: "b" * 64 for name in SOURCE_FILES})


def completed(parent_turn_limit=4):
    assignment = plan(
        "a" * 40, {name: "b" * 64 for name in SOURCE_FILES}, parent_turn_limit=parent_turn_limit
    )
    records, evidence = [], {}
    for block in assignment["blocks"]:
        for trial in block["trials"]:
            records.append(
                dict(
                    **trial,
                    whole_workflow_verified=1,
                    automatic_alerts=int(trial["arm"] == "routine_help"),
                    monitor_error_count=0,
                    required_feedback_misses=0,
                )
            )
            task = (
                "Preserve original numerical checks; only a judge may authorize protected repairs."
            )
            evidence[trial["id"]] = dict(
                task_protocol=task,
                prompt_receipt=dict(
                    mode="task_protocol",
                    task_sha256=hashlib.sha256(task.encode()).hexdigest(),
                    renderer_sha256=assignment["source_files_sha256"][PROMPT_SOURCE],
                ),
                feedback=[
                    dict(
                        id="help_one",
                        result={"summary": "Returned diagnostic advice"},
                        acknowledgment={"reason": "Checked returned advice"},
                    )
                ],
                authority_results=[
                    dict(
                        stage="completed",
                        verdict={"decision": "grant"},
                        deployment={"status": "applied"},
                    )
                ]
                if trial["family"] == "source_binding"
                else [],
                parent_turn_limit=parent_turn_limit,
                parent_turn_count=4,
            )
    return assignment, records, evidence


def test_commission_plan_covers_both_controls_and_all_three_paths():
    value = prepared()
    trials = [trial for block in value["blocks"] for trial in block["trials"]]
    assert value == prepared()
    assert len({trial["id"] for trial in trials}) == value["workflows"] == 6
    assert {(trial["family"], trial["arm"]) for trial in trials} == {
        (family, arm)
        for family in ["progressing_work", "unit_conversion", "source_binding"]
        for arm in ["observe", "routine_help"]
    }
    assert {trial["worker_prompt"] for trial in trials} == {"task_protocol"}
    assert value["decision_model_calls"] == value["optimizer_updates"] == 0
    assert 6 * value["resource_bounds"]["starts_per_workflow"] + 1 == 73


def test_terminal_partial_cohort_or_live_resource_cannot_admit_followup():
    summary = dict(
        primary_all_attempts=dict(
            complete_design=True, planned=64, started=64, unstarted=[], audit_violations=[]
        )
    )
    check_predecessor(summary, {"stage": "released"}, {"starts": [{"ended_at": 1}]})
    for change in [
        {"complete_design": False},
        {"started": 63},
        {"unstarted": ["original_id"]},
        {"audit_violations": [["trial", "unclosed_actor"]]},
    ]:
        changed = copy.deepcopy(summary)
        changed["primary_all_attempts"].update(change)
        with pytest.raises(ValueError, match="incomplete|violations"):
            check_predecessor(changed, {"stage": "released"}, {"starts": []})
    with pytest.raises(ValueError, match="not released"):
        check_predecessor(summary, {"stage": "watching"}, {"starts": []})
    with pytest.raises(ValueError, match="active"):
        check_predecessor(summary, {"stage": "released"}, {"starts": [{}]})


def test_successful_integration_is_not_an_effectiveness_or_training_claim():
    value, records, evidence = completed()
    result = audit(value, records, evidence, audit_violations=[])
    assert result["commissioned"]
    assert not result["eligible_for_optimizer"]
    assert "model benefit unmeasured" in result["interpretation"]


def test_extended_resumptions_do_not_increase_shared_resources_or_reuse_trial_ids():
    original = prepared()
    extended = plan("a" * 40, {name: "b" * 64 for name in SOURCE_FILES}, parent_turn_limit=12)
    assert original["resource_bounds"] == extended["resource_bounds"]
    old_ids = {t["id"] for b in original["blocks"] for t in b["trials"]}
    new_ids = {t["id"] for b in extended["blocks"] for t in b["trials"]}
    assert not old_ids & new_ids
    for invalid in [0, 13, True]:
        with pytest.raises(ValueError, match="Parent-turn limit"):
            plan("a" * 40, {name: "b" * 64 for name in SOURCE_FILES}, parent_turn_limit=invalid)


def test_extended_commission_requires_an_actual_fifth_resumption_and_matching_limit():
    value, records, evidence = completed(parent_turn_limit=12)
    result = audit(value, records, evidence, audit_violations=[])
    assert not result["commissioned"]
    assert not result["exercised"]["resumption_after_four_turns"]
    identity = records[0]["id"]
    evidence[identity]["parent_turn_count"] = 5
    assert audit(value, records, evidence, audit_violations=[])["commissioned"]
    evidence[identity]["parent_turn_limit"] = 4
    result = audit(value, records, evidence, audit_violations=[])
    assert not result["commissioned"]
    assert [identity, "parent_turn_limit_not_verified"] in result["violations"]


def test_interrupted_commission_uses_only_original_attempted_subset():
    value, records, _ = completed()
    selected = value | dict(blocks=[value["blocks"][0]], workflows=2)
    rows = records[:2]
    check_audited_subset(value, selected, rows)
    with pytest.raises(ValueError, match="coverage"):
        check_audited_subset(value, selected, records)
    with pytest.raises(ValueError, match="protocol"):
        check_audited_subset(value, selected | dict(source_revision="c" * 40), rows)
    changed = copy.deepcopy(selected)
    changed["blocks"][0]["trials"][0]["worker_prompt"] = "inherited"
    with pytest.raises(ValueError, match="assignment"):
        check_audited_subset(value, changed, rows)


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "inherited"},
        {"renderer_sha256": "c" * 64},
        {"task_sha256": "d" * 64},
    ],
)
def test_numerical_success_cannot_hide_wrong_worker_instructions(change):
    value, records, evidence = completed()
    evidence[records[0]["id"]]["prompt_receipt"].update(change)
    result = audit(value, records, evidence, audit_violations=[])
    assert not result["commissioned"]
    assert [records[0]["id"], "prompt_control_not_verified"] in result["violations"]


def test_missing_actual_dispatch_and_authority_are_not_filled_from_proposals():
    value, records, evidence = completed()
    for row in records:
        row["automatic_alerts"] = 0
        row["proposed_actions"] = {"request_worker_help": 20}
    for files in evidence.values():
        files["authority_results"] = [dict(stage="completed", verdict={"decision": "grant"})]
        files["feedback"] = [dict(id="help_one", acknowledgment=None)]
    result = audit(value, records, evidence, audit_violations=[])
    assert not result["commissioned"]
    assert not any(result["exercised"].values())


def test_partial_attempts_duplicates_and_wrong_assignments_remain_visible():
    value, records, evidence = completed()
    missing = records.pop()
    evidence.pop(missing["id"])
    result = audit(value, records, evidence, audit_violations=[])
    assert not result["commissioned"] and result["unstarted"] == [missing["id"]]
    with pytest.raises(ValueError, match="Duplicate"):
        audit(value, records + [records[0]], evidence, audit_violations=[])
    records[0]["family"] = "different_problem"
    result = audit(value, records, evidence, audit_violations=[])
    assert [records[0]["id"], "assignment_mismatch"] in result["violations"]


@pytest.mark.parametrize(
    "change,issue",
    [
        ({"whole_workflow_verified": 0}, "workflow_not_verified"),
        ({"automatic_alerts": 2}, "automatic_dispatch_allowance_not_verified"),
        ({"required_feedback_misses": None}, "required_feedback_not_reconciled"),
        ({"monitor_error_count": 1}, "monitor_errors_or_missing_error_accounting"),
    ],
)
def test_failed_science_or_unreconciled_feedback_prevents_commission(change, issue):
    value, records, evidence = completed()
    records[0].update(change)
    result = audit(value, records, evidence, audit_violations=[])
    assert not result["commissioned"]
    assert [records[0]["id"], issue] in result["violations"]
