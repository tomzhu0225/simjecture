import time

import pytest
from simjecture_monitor.repair import RepairAuthority

BAD = 'def classify(alive, code):\n    return "running"\n'
GOOD = (
    'def classify(alive, code):\n    return "running" if alive els'
    'e "completed" if code == 0 else "failed"\n'
)
VERIFY = (
    'from bridge import classify\nassert classify(True,None)=="run'
    'ning"\nassert classify(False,0)=="completed"\nassert classify('
    'False,1)=="failed"\nprint("all component invariants passed")\n'
)


def authority(tmp_path):
    component = tmp_path / "component"
    component.mkdir()
    (component / "bridge.py").write_text(BAD)
    return RepairAuthority(
        component, tmp_path / "records", allowed_files=["bridge.py"], test_source=VERIFY
    )


def grant(manager, files=None):
    return manager.issue(
        {"observed": "finished process remains reported running"},
        dict(
            decision="grant",
            rationale="The adapter contradicts the finished process receipt.",
            evidence=["process receipt"],
            files=files or ["bridge.py"],
        ),
        judge_receipt={"role": "independent judge fixture"},
    )


def proposal(item, code=GOOD):
    return dict(
        grant_id=item["id"],
        explanation="Restore correct completed and failed terminal states.",
        replacements={"bridge.py": code},
    )


def test_scoped_repair_passes_real_isolated_checks_and_is_single_use(tmp_path):
    manager = authority(tmp_path)
    item = grant(manager)
    result = manager.apply(proposal(item))
    assert result["status"] == "applied"
    assert result["verification"]["returncode"] == 0
    assert (manager.component / "bridge.py").read_text() == GOOD
    with pytest.raises(ValueError, match="consumed"):
        manager.apply(proposal(item))


@pytest.mark.parametrize("violation", ["path", "expired", "changed", "forged"])
def test_repair_rejects_ungranted_or_stale_authority_before_writing(tmp_path, violation):
    manager = authority(tmp_path)
    item = grant(manager)
    patch = proposal(item)
    if violation == "path":
        patch["replacements"] = {"../outside.py": GOOD}
    elif violation == "expired":
        manager.grants[item["id"]]["expires_at"] = time.time() - 1
    elif violation == "changed":
        (manager.component / "bridge.py").write_text(BAD + "# new edit\n")
    else:
        patch["grant_id"] = "unissued_grant"
    before = (manager.component / "bridge.py").read_bytes()
    with pytest.raises(ValueError):
        manager.apply(patch)
    assert (manager.component / "bridge.py").read_bytes() == before


def test_judge_cannot_expand_operator_policy(tmp_path):
    manager = authority(tmp_path)
    with pytest.raises(ValueError, match="outside operator policy"):
        grant(manager, ["permissions.py"])


def test_failed_repair_leaves_original_intact(tmp_path):
    manager = authority(tmp_path)
    item = grant(manager)
    with pytest.raises(ValueError, match="verification rejected"):
        manager.apply(proposal(item, BAD))
    assert (manager.component / "bridge.py").read_text() == BAD
    assert manager.grants[item["id"]]["status"] == "rejected"


def test_candidate_cannot_read_host_files_or_change_verifier(tmp_path):
    manager = authority(tmp_path)
    item = grant(manager)
    secret = tmp_path / "host_secret"
    secret.write_text("host private fixture")
    malicious = f"from pathlib import Path\nPath({str(secret)!r}).read_text()\n" + GOOD
    with pytest.raises(ValueError, match="verification rejected"):
        manager.apply(proposal(item, malicious))
    assert (manager.component / "bridge.py").read_text() == BAD
    second = grant(manager)
    with pytest.raises(ValueError, match="verification rejected"):
        manager.apply(
            proposal(second, 'open("verify_component.py","w").write("print(1)")\n' + GOOD)
        )


def test_rollback_restores_original_and_rejects_later_worker_edits(tmp_path):
    manager = authority(tmp_path)
    item = grant(manager)
    manager.apply(proposal(item))
    assert manager.rollback(item["id"])["status"] == "rolled_back"
    assert (manager.component / "bridge.py").read_text() == BAD
    second = grant(manager)
    manager.apply(proposal(second))
    (manager.component / "bridge.py").write_text(GOOD + "# independent edit\n")
    with pytest.raises(ValueError, match="changed after repair"):
        manager.rollback(second["id"])
