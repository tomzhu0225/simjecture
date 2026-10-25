import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def measure(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "audit_generalization", scripts / "audit_generalization.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.completion_measurement


@pytest.mark.parametrize("required_misses", [0, 1])
def test_teardown_wakeup_does_not_hide_a_premature_stop(measure, required_misses):
    out = dict(
        ended_at=104,
        verified_complete=True,
        turns=[dict(returncode=0, ended_at=50), dict(returncode=124, ended_at=100)],
        parking=[dict(started_at=50, ended_at=90)],
    )
    # Advisory help is also binding when the worker explicitly waits for it.
    wait = dict(status="woken", created_at=99, woken_at=102)
    result = measure(out, wait, dict(required_feedback_misses=required_misses))
    assert result["completion_censored"]
    assert result["worker_waiting_at_last_return"]
    assert not result["whole_workflow_verified"]


def test_wait_resolved_before_a_normal_final_return_is_complete(measure):
    out = dict(
        ended_at=104,
        verified_complete=True,
        turns=[dict(returncode=0, ended_at=100)],
        parking=[],
    )
    result = measure(out, dict(created_at=50, woken_at=90), dict(required_feedback_misses=0))
    assert not result["completion_censored"]
    assert result["whole_workflow_verified"]


@pytest.mark.parametrize("new_collector", [False, True])
def test_actor_hitting_wait_boundary_remains_failure_not_excluded(measure, new_collector):
    out = dict(
        ended_at=120,
        verified_complete=False,
        turns=[dict(returncode=124, ended_at=100)],
        parking=[dict(started_at=100, ended_at=120)],
    )
    if new_collector:
        out.update(
            completion_checks=[dict(allowed=False)], finish_reason="boundary_or_parent_turn_limit"
        )
    result = measure(out, dict(status="waiting", created_at=99), dict(required_feedback_misses=1))
    assert not result["completion_censored"]
    assert not result["whole_workflow_verified"]


def test_missing_required_feedback_alone_does_not_relabel_an_actor_failure(measure):
    out = dict(
        ended_at=104,
        verified_complete=True,
        turns=[dict(returncode=0, ended_at=100)],
        parking=[],
    )
    result = measure(out, {}, dict(required_feedback_misses=1))
    assert not result["completion_censored"]
    assert not result["whole_workflow_verified"]


def test_unknown_feedback_need_is_not_complete_and_remains_in_the_cohort(measure):
    out = dict(
        ended_at=104,
        verified_complete=True,
        turns=[dict(returncode=0, ended_at=100)],
        parking=[],
    )
    result = measure(out, {}, dict(required_feedback_misses=None))
    assert not result["completion_censored"]
    assert not result["whole_workflow_verified"]


def test_new_collector_boundary_cannot_be_overridden_by_correct_numeric_files(measure):
    out = dict(
        ended_at=120,
        verified_complete=True,
        turns=[dict(returncode=0, ended_at=100)],
        parking=[dict(started_at=100, ended_at=120)],
        completion_checks=[dict(allowed=False, pending_required_help=1)],
        finish_reason="boundary_or_parent_turn_limit",
    )
    result = measure(out, {}, dict(required_feedback_misses=0))
    assert not result["completion_censored"]
    assert not result["whole_workflow_verified"]
