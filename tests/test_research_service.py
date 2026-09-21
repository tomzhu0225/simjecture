import time

import pytest

from conjecture_solver.research_service import ResearchService, fingerprint


def service(tmp_path, *, modern=False):
    s = ResearchService.create(tmp_path / "study", "Every tested result is 4.", wall_seconds=120)
    if not modern:
        from conjecture_solver.research_service import put

        s.manifest["schema_version"] = 1
        put(s.root / "research.json", s.manifest)
    (s.work / "calc.py").write_text(
        "import json\nfrom pathlib import Path\n"
        'Path("result.json").write_text(json.dumps({"value":2+2}))\n'
    )
    return s


def completed(s, **kwargs):
    receipt = s.run("calc.py", outputs=["result.json"], **kwargs)
    stop = time.time() + 20
    while time.time() < stop:
        record = s._read("experiments", receipt["id"])
        if record["status"] not in ["queued", "running"]:
            assert record["status"] == "succeeded", record
            return record
        time.sleep(0.05)
    pytest.fail("Real sandbox experiment did not finish")


def approve(s, request, disposition="supported"):
    body = s.review_body(request)
    return s.record_verdict(
        request["id"],
        dict(
            claim_id=request["claim"],
            decision="approved",
            disposition=disposition,
            rationale="The arithmetic source and recorded result establish the finite claim.",
            evidence_gaps=[],
            next_test=None,
        ),
        packet_sha256=fingerprint(s.packet(body)),
    )


def test_real_execution_and_durable_review(tmp_path, monkeypatch):
    s = service(tmp_path)
    r = completed(s)
    # A native process can exit and retry without repeating an experiment.
    assert s.run("calc.py", outputs=["result.json"])["id"] == r["id"]
    monkeypatch.chdir(tmp_path)
    request = s.review([r["id"]], "The full finite arithmetic result is four.")
    assert request["status"] == "queued"
    reopened = ResearchService(s.root)
    assert reopened.review_status(request["id"]) == request
    assert not reopened.status()["completed"]
    assert approve(reopened, request)["completed"]


def test_mutated_evidence_is_rejected(tmp_path):
    s = service(tmp_path)
    r = completed(s)
    p = s.root / "experiments" / r["id"] / "workspace/result.json"
    p.write_text('{"value":5}')
    with pytest.raises(ValueError, match="changed"):
        s.review([r["id"]], "This cannot be accepted after modifying the result.")


def test_repair_requires_prior_exact_commitment(tmp_path):
    s = service(tmp_path)
    old = completed(s)
    c = s.commit(
        "A repaired bounded assertion.",
        source="calc.py",
        cases=[[]],
        acceptance="value equals four",
    )
    with pytest.raises(ValueError, match="prior commitment"):
        s.review([old["id"]], "Retrospective relabelling is not a prospective test.", claim=c["id"])
    (s.work / "calc.py").write_text("print(5)")
    with pytest.raises(ValueError, match="differs"):
        s.run("calc.py", outputs=["result.json"], commitment=c["id"])


def test_falsification_alone_does_not_complete(tmp_path):
    s = service(tmp_path)
    r = completed(s)
    request = s.review(
        [r["id"]],
        "A hypothetical falsification record for transition testing.",
        disposition="falsified",
    )
    assert not approve(s, request, "falsified")["completed"]
    c = s.commit(
        "The finite repaired claim produces four.",
        source="calc.py",
        cases=[[]],
        acceptance="value equals four",
    )
    fresh = completed(s, commitment=c["id"])
    req = s.review(
        [fresh["id"]], "Fresh evidence matches the committed finite repair.", claim=c["id"]
    )
    assert approve(s, req)["completed"]


def test_missing_output_is_execution_failure(tmp_path):
    s = service(tmp_path)
    r = s.run("calc.py", outputs=["absent.json"])
    stop = time.time() + 20
    while time.time() < stop:
        final = s._read("experiments", r["id"])
        if final["status"] == "failed":
            break
        time.sleep(0.05)
    assert final["status"] == "failed"
    with pytest.raises(ValueError, match="not a successful"):
        s.review([r["id"]], "An absent result cannot establish the claim.")


def test_deadline_survives_reopen_and_source_paths_are_scoped(tmp_path):
    s = service(tmp_path)
    deadline = s.manifest["deadline"]
    assert (
        ResearchService.create(s.root, s.manifest["hypothesis"], wall_seconds=99999).manifest[
            "deadline"
        ]
        == deadline
    )
    with pytest.raises(ValueError):
        s.run("../outside.py", outputs=["result.json"])
    with pytest.raises(ValueError):
        ResearchService.create(s.root, "Changed claim")


def test_review_includes_entry_source_without_py_extension(tmp_path):
    s = service(tmp_path)
    (s.work / "calc.code").write_text((s.work / "calc.py").read_text())
    receipt = s.run("calc.code", outputs=["result.json"])
    deadline = time.time() + 20
    while time.time() < deadline:
        record = s._read("experiments", receipt["id"])
        if record["status"] == "succeeded":
            break
        time.sleep(0.05)
    body = dict(
        experiments=[receipt["id"]],
        conclusion="The recorded result equals four.",
        claim="root",
        disposition="supported",
    )
    assert "calc.code" in s.packet(body)["experiments"][0]["sources"]


def test_oversized_input_rejected_before_copy_or_launch(tmp_path):
    s = service(tmp_path)
    # Sparse file exercises the limit without consuming the corresponding disk space.
    with (s.work / "large.bin").open("wb") as f:
        f.truncate(513 * 1024**2)
    with pytest.raises(ValueError, match="storage limits"):
        s.run("calc.py", inputs=["large.bin"], outputs=["result.json"])
    assert not list((s.root / "experiments").iterdir())


def test_original_protocol_is_frozen_and_visible_to_reviewer(tmp_path):
    s = service(tmp_path)
    protocol = "The finite decision requires a numerical control and all prescribed cases."
    s.freeze_protocol(protocol)
    r = completed(s)
    packet = s.packet(
        dict(
            experiments=[r["id"]],
            conclusion="A finite numerical argument.",
            claim="root",
            disposition="supported",
        )
    )
    assert packet["operator_protocol"] == protocol
    assert packet["protocol_sha256"]
    reopened = ResearchService(s.root)
    reopened.freeze_protocol(protocol)
    with pytest.raises(ValueError, match="immutable"):
        reopened.freeze_protocol("Drop the control requirement.")


def test_protocol_cannot_be_added_after_observing_experiment(tmp_path):
    s = service(tmp_path)
    completed(s)
    with pytest.raises(ValueError, match="retrospectively"):
        s.freeze_protocol("A decision rule chosen after seeing the data.")


def test_parallel_storage_reservations_fit_study_budget(tmp_path):
    s = service(tmp_path)
    (s.work / "calc.py").write_text(
        "import time\nfrom pathlib import Path\ntime.sleep(.4)\n"
        'Path("result.json").write_text("{}")\n'
    )
    first = s.run("calc.py", outputs=["result.json"], key="first")
    second = s.run("calc.py", outputs=["result.json"], key="second")
    assert (
        first["workspace_limit_bytes"] + second["workspace_limit_bytes"]
        <= s.manifest["max_total_bytes"]
    )
    assert second["workspace_limit_bytes"] > 3 * 1024**3
    deadline = time.time() + 20
    while time.time() < deadline:
        if all(s._read("experiments", r["id"])["status"] == "succeeded" for r in [first, second]):
            break
        time.sleep(0.05)
    assert all(s._read("experiments", r["id"])["status"] == "succeeded" for r in [first, second])


def test_supervisor_waits_for_experiment_before_relaunching_model(tmp_path, monkeypatch):
    import argparse

    from conjecture_solver.research_supervisor import ResearchSupervisor

    s = service(tmp_path)
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Check the finite arithmetic claim.")
    (s.work / "calc.py").write_text(
        "import time\nfrom pathlib import Path\ntime.sleep(.4)\n"
        'Path("result.json").write_text("{}")\n'
    )
    args = argparse.Namespace(
        campaign=s.root,
        state_dir=s.root / "supervisor",
        instructions_file=instructions,
        wall_seconds=120,
        turn_seconds=10,
        backend="codex-glm",
        executable="unused",
        model="unused",
        judge_model="unused",
    )
    supervisor = ResearchSupervisor(args)
    calls = []

    def launch(directory, prompt, judge=False):
        calls.append(1)
        if len(calls) == 1:
            s.run("calc.py", outputs=["result.json"])
        else:
            assert all(r["status"] == "succeeded" for r in s.status()["experiments"])
            (supervisor.directory / "control.json").write_text('{"command":"pause"}')
        return 0

    monkeypatch.setattr(supervisor, "launch", launch)
    assert supervisor.run() == 0
    assert len(calls) == 2


def test_repair_review_targets_repair_and_rejects_other_claim_id(tmp_path):
    from conjecture_solver.research_supervisor import research_review_prompt

    s = service(tmp_path)
    c = s.commit(
        "The repaired finite result is four.",
        source="calc.py",
        cases=[[]],
        acceptance="The computed value equals four.",
    )
    r = completed(s, commitment=c["id"])
    request = s.review([r["id"]], "Fresh evidence establishes this finite repair.", claim=c["id"])
    body = s.review_body(request)
    packet = s.packet(body)
    assert packet["target_claim"]["statement"] == c["statement"]
    prompt = research_review_prompt(packet)
    assert "not the final study-completion check" in prompt
    assert "repair can be supported while the original hypothesis is falsified" in prompt
    with pytest.raises(ValueError, match="different claim"):
        s.record_verdict(
            request["id"],
            dict(
                claim_id="root",
                decision="approved",
                disposition="falsified",
                rationale="This verdict discusses the original, wrong target.",
                evidence_gaps=[],
                next_test=None,
            ),
            packet_sha256=fingerprint(packet),
        )


def challenge(record):
    return dict(
        strategy="Exhaustively test the finite singleton domain.",
        experiments=[record["id"]],
        outcome="The exact result is four.",
    )


def test_support_requires_actual_challenge_receipts(tmp_path):
    s = service(tmp_path, modern=True)
    r = completed(s)
    with pytest.raises(ValueError, match="Support requires challenge"):
        s.review([r["id"]], "I claim that I searched for counterexamples.")
    invalid = challenge(r) | dict(experiments=["exp_not_submitted"])
    with pytest.raises(ValueError, match="Support requires challenge"):
        s.review([r["id"]], "A challenge cites missing evidence.", challenge=invalid)
    req = s.review([r["id"]], "All finite possibilities were tested.", challenge=challenge(r))
    assert approve(s, req)["completed"]


def test_nested_repairs_keep_counterexamples_and_require_ancestor_failures(tmp_path):
    s = service(tmp_path, modern=True)
    root = completed(s)
    fail = s.review(
        [root["id"]], "Synthetic root failure for transition test.", disposition="falsified"
    )
    approve(s, fail, "falsified")
    with pytest.raises(ValueError, match="smallest justified"):
        s.commit("A new statement", source="calc.py", cases=[[]], acceptance="Equals four")
    first = s.commit(
        "A first repair",
        source="calc.py",
        cases=[[]],
        acceptance="Equals four",
        rationale="Change only the failed numerical bound.",
    )
    second = s.commit(
        "A second repair",
        source="calc.py",
        cases=[[]],
        acceptance="Equals four",
        parent=first["id"],
        rationale="Add only the missing boundary condition.",
    )
    fresh = completed(s, commitment=second["id"])
    req = s.review(
        [fresh["id"]], "The second repair passes.", claim=second["id"], challenge=challenge(fresh)
    )
    with pytest.raises(ValueError, match="ancestor falsifications"):
        approve(s, req)
    bad = completed(s, commitment=first["id"])
    failure = s.review(
        [bad["id"]],
        "Synthetic first repair failure for transition test.",
        claim=first["id"],
        disposition="falsified",
    )
    approve(s, failure, "falsified")
    packet = s.packet(s.review_body(req))
    assert [a["id"] for a in packet["ancestry"]] == ["root", first["id"]]
    assert {c["review"]["claim"] for c in packet["counterexamples"]} == {"root", first["id"]}
    assert all(c["evidence"][0]["documents"] for c in packet["counterexamples"])
    assert approve(s, req)["completed"]
    root_path = s.root / "experiments" / root["id"] / "workspace/result.json"
    root_path.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        s.packet(s.review_body(req))


def test_compact_status_keeps_receipts_and_full_details_available(tmp_path):
    s = service(tmp_path, modern=True)
    r = completed(s)
    brief, full = s.status(compact=True), s.status()
    assert brief["experiments"][0]["id"] == r["id"]
    assert "artifacts" not in brief["experiments"][0]
    assert full["experiments"][0]["artifacts"]
    assert brief["remaining_seconds"] > 0
    assert __import__("pathlib").Path(brief["experiments"][0]["receipt"]).is_file()


def test_create_cannot_convert_existing_campaign(tmp_path):
    root = tmp_path / "existing"
    root.mkdir()
    (root / "mvp_manifest.json").write_text("{}")
    with pytest.raises(ValueError, match="never convert"):
        ResearchService.create(root, "A new hypothesis")


def test_reviewer_cannot_bypass_challenge_by_changing_disposition(tmp_path):
    s = service(tmp_path, modern=True)
    r = completed(s)
    req = s.review(
        [r["id"]],
        "Proposed falsification with malformed challenge.",
        disposition="falsified",
        challenge={"strategy": "Assertion only"},
    )
    with pytest.raises(ValueError, match="Support requires challenge"):
        approve(s, req, "supported")
    assert not s.status()["completed"]


def test_resumed_agent_has_durable_guide_and_short_prompt(tmp_path):
    import argparse

    from conjecture_solver.research_supervisor import ResearchSupervisor

    s = service(tmp_path, modern=True)
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Test every point of the finite domain.")
    args = argparse.Namespace(
        campaign=s.root,
        state_dir=s.root / "supervisor",
        instructions_file=instructions,
        wall_seconds=120,
        turn_seconds=10,
        backend="codex-glm",
        executable="unused",
        model="unused",
        judge_model="unused",
    )
    supervisor = ResearchSupervisor(args)
    full = supervisor.prompt()
    supervisor.state["worker_cursor"] = "existing-thread"
    supervisor.save()
    (s.work / "RESEARCH_GUIDE.md").unlink()
    reopened = ResearchSupervisor(args)
    assert (s.work / "RESEARCH_GUIDE.md").read_text() == full
    assert len(reopened.prompt()) < len(full) / 4
    assert "RESEARCH_GUIDE.md" in reopened.prompt()
