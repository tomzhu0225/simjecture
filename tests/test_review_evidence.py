import json

import pytest

from conjecture_solver.review_evidence import fetch_evidence
from tests.test_research_notebook import receipt, service
from tests.test_research_oversight import make, transcript


def test_retrieval_preserves_hash_and_scope_and_rejects_mutation(tmp_path):
    s = service(tmp_path)
    r = receipt(s, payload={"ledger": {"residual": 0.13}})
    request = {"experiment": r["id"], "output": "result.json", "path": "ledger.residual"}
    result = fetch_evidence(s, [request])[0]
    assert result["value"] == 0.13 and result["sha256"] == r["artifacts"]["result.json"]["sha256"]
    assert result["stage"] == "exploration"
    file = s.root / "experiments" / r["id"] / "workspace/result.json"
    file.write_text('{"ledger":{"residual":0}}')
    assert "changed" in fetch_evidence(s, [request])[0]["error"]
    assert "value" not in fetch_evidence(s, [request])[0]
    request["output"] = "../../research.json"
    assert "declared output" in fetch_evidence(s, [request])[0]["error"]


def test_large_excerpt_requests_narrower_path_without_dumping_it(tmp_path):
    s = service(tmp_path)
    r = receipt(s, payload={"big": "x" * 15000, "scalar": 4})
    request = {"experiment": r["id"], "output": "result.json"}
    result = fetch_evidence(s, [request])[0]
    assert "narrower" in result["error"] and "value" not in result
    assert fetch_evidence(s, [request | {"path": "scalar"}])[0]["value"] == 4


def test_oversight_fetches_missing_result_before_issuing_verdict(tmp_path, monkeypatch):
    s, sup = make(tmp_path)
    r = receipt(s, payload={"residual": 0.13})
    sup.state["last_oversight_at"] = 0
    packets = []

    def launch(directory, prompt, judge=False):
        packet = json.loads((directory / "packet.json").read_text())
        packets.append(packet)
        if len(packets) == 1:
            requests = [{"experiment": r["id"], "output": "result.json", "path": "residual"}]
        else:
            assert packet["requested_evidence"][0]["value"] == 0.13
            requests = []
        transcript(
            directory / "response.json",
            text=json.dumps(
                dict(
                    decision="revise",
                    rationale="Measured residual requires further validation.",
                    findings=[],
                    next_action="Check the boundary accounting.",
                    prerequisites=["Boundary energy closure"],
                    evidence_requests=requests,
                )
            ),
        )
        with (directory / "response.json").open("a") as stream:
            stream.write('\n{"type":"turn.completed","usage":{}}\n')
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.run_oversight()
    assert len(packets) == 2
    assert sup.state["oversight_feedback"]["decision"] == "revise"
    assert not s.status()["completed"]
    assert (sup.directory / "oversight-00001/final-packet.json").exists()


def test_pending_evidence_cannot_open_method_gate(tmp_path):
    from conjecture_solver.research_oversight import OversightVerdict

    with pytest.raises(ValueError, match="prerequisites"):
        OversightVerdict(
            decision="continue",
            rationale="Approve after fetching the missing result.",
            findings=[],
            next_action="Continue study.",
            prerequisites=[],
            evidence_requests=[{"experiment": "exp_test"}],
        )
