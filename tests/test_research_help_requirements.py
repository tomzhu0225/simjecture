"""Pre-dispatch feedback declarations retain old identities and cannot be relabeled."""

import json

import pytest

from conjecture_solver.research_service import fingerprint, put
from tests.test_research_director import supervisor
from tests.test_research_helpers import request


def test_legacy_request_keeps_its_original_body_and_identity(tmp_path):
    service = supervisor(tmp_path).service
    row = request(service)
    body = {key: row[key] for key in ["question", "success_criteria", "context", "files"]}
    assert "feedback_requirement" not in row
    assert row["request_sha256"] == fingerprint(body)
    assert row["id"] == "help_" + fingerprint(body)[:24]
    assert request(service)["id"] == row["id"]


@pytest.mark.parametrize("mode", ["required", "advisory"])
def test_declaration_is_in_frozen_context_before_any_helper_runs(tmp_path, mode):
    service = supervisor(tmp_path).service
    row = request(service, feedback_requirement=mode, key="one-request")
    context = json.loads((service.root / row["context_file"]).read_text())
    assert row["feedback_requirement"] == context["feedback_requirement"] == mode
    assert row["status"] == "queued" and row["tasks"] == []
    assert service.help_status(row["id"])["feedback_requirement"] == mode
    assert request(service, feedback_requirement=mode, key="one-request")["id"] == row["id"]
    with pytest.raises(ValueError, match="different context"):
        request(
            service,
            feedback_requirement="advisory" if mode == "required" else "required",
            key="one-request",
        )


@pytest.mark.parametrize("mode", ["sometimes", False, [], {}])
def test_invalid_need_declaration_is_rejected_without_queueing(tmp_path, mode):
    service = supervisor(tmp_path).service
    with pytest.raises(ValueError, match="feedback_requirement"):
        request(service, feedback_requirement=mode)
    assert service._all("help_requests") == []


def test_operator_can_require_explicit_declarations_for_a_new_study(tmp_path):
    sup = supervisor(tmp_path)
    service = sup.service
    manifest = service.manifest
    manifest["helper_policy"] = {"require_feedback_requirement": True}
    put(service.root / "research.json", manifest)
    with pytest.raises(ValueError, match="Declare feedback_requirement"):
        request(service)
    row = request(service, feedback_requirement="required")
    assert row["feedback_requirement"] == "required"
    assert "feedback_requirement='required'" in sup.prompt()
