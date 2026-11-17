"""Opt-in Lab facade with provenance for normal Simjecture research entry points."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from .contracts import DECISION_COMPONENTS, decision_audit, fingerprint, reject_private_fields
from .journal import Journal


class DecisionLab:
    _native_class = None

    def __init__(self, root, *, arm=None, advice_endpoint=None):
        import os

        from conjecture_solver.research_service import Lab

        if os.environ.get("SCIENCE_TRANSPORT_SOCKET"):
            from .lab_rpc import NativeLabProxy

            self.native = NativeLabProxy(root)
        else:
            self.native = (self._native_class or Lab)(root)
        self.root = Path(root).resolve()
        from .storage import read_json

        run = read_json(self.root / "study-run.json", {})
        self.sampling_seed = run.get("policy_sampling_seed", int(fingerprint(self.root.name)[:8], 16))
        self.arm = arm or run["arm"]
        self.host_model = run.get("decision_host_model", "gpt-6.1-sol")
        self.endpoint = advice_endpoint or run.get("advice_endpoint")
        self.journal = Journal(self.root / "decision-audit" / "events.sqlite")
        self.advice_records = {}

    def state(self, *, receipt_ids=None, evidence_ids=None):
        from .case import public_state

        return public_state(self.root, native=self.native, receipt_ids=receipt_ids, evidence_ids=evidence_ids)

    def simulation_seed(self, signature):
        from .storage import read_json

        task = read_json(self.root / "task.json")
        return int(fingerprint(dict(seed=task.get("perturbation_seed"), signature=signature))[:8], 16)

    def __getattr__(self, name):
        return getattr(self.native, name)

    def analyze(self, source, args=(), **kwargs):
        if "stage" in kwargs or "purpose" in kwargs or kwargs.get("commitment"):
            raise ValueError("Analysis uses exploration/diagnostic semantics; use run for evidence")
        return self.run(source, args, stage="exploration", purpose="diagnostic", **kwargs)

    def record_teacher_decision(self, state, advice):
        if self.arm != "teacher":
            raise ValueError("Public teacher decisions belong to the SFT collection arm")
        reject_private_fields(state)
        reject_private_fields(advice)
        reply = dict(advice=advice, teacher_model="gpt-6.1-sol")
        identifier = "advice-" + uuid.uuid4().hex
        self.journal.append(
            study_id=self.root.name,
            event_id=identifier,
            kind="raw_advice",
            payload=dict(observation=state, raw_reply=reply, received_at=time.time()),
        )
        self.advice_records[identifier] = dict(state=state, reply=reply)
        return identifier

    def advise(self, state=None, *, seed=0, request_id=None):
        state = state if state is not None else self.state()
        if self.arm == "simjecture":
            raise ValueError("The baseline arm uses the independent host decision")
        if not self.endpoint:
            raise ValueError("An assisted study needs its pinned policy endpoint")
        reject_private_fields(state)
        request_id = request_id or uuid.uuid4().hex
        sample_seed = int(
            fingerprint(dict(base=self.sampling_seed, request_id=request_id, requested_seed=seed))[:8], 16
        )
        body = dict(observation=state, seed=sample_seed, expected_arm=self.arm, request_id=request_id)

        remaining = state["remaining_wall_seconds"]
        if remaining <= 0:
            raise TimeoutError("The research wall budget has expired")
        if self.endpoint.startswith("gateway:"):
            from .transport import request as gateway_request

            reply = gateway_request(
                "/policy", dict(slot=int(self.endpoint.split(":")[1]), body=body), timeout=remaining
            )
        else:
            request = Request(
                self.endpoint,
                data=json.dumps(body, allow_nan=False).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=remaining) as response:
                reply = json.load(response)
        identifier = "advice-" + body["request_id"]
        existing = next((e for e in self.journal.export(self.root.name) if e["event_id"] == identifier), None)
        received_at = existing["payload"]["received_at"] if existing else time.time()
        self.journal.append(
            study_id=self.root.name,
            event_id=identifier,
            kind="raw_advice",
            payload=dict(observation=state, raw_reply=reply, received_at=received_at),
        )
        self.advice_records[identifier] = dict(state=state, reply=reply)
        # Sampling token IDs/probabilities remain in the immutable replay log;
        # they are not scientific advice and must not flood the host context.
        public = {
            key: reply[key]
            for key in ("advice", "validation_error", "inference_wall_seconds")
            if key in reply
        }
        if reply.get("validation_error"):
            public["raw_output_excerpt"] = reply.get("raw_output", "")[:1600]
            public["full_raw_reply_record"] = "decision-audit/events.sqlite"
        return dict(advice_id=identifier, **public)

    def run(
        self,
        source,
        args=(),
        *,
        advice_id=None,
        executed_plan=None,
        component_sources=None,
        override_reasons=None,
        takeover_reason=None,
        timeout=None,
        **kwargs,
    ):
        if not advice_id and self.arm == "teacher":
            raise ValueError(
                "First record a public structured teacher decision with record_teacher_decision(lab.state(), advice); bind its advice_id to this run."
            )
        if (
            not advice_id
            and not takeover_reason
            and self.arm in {"simjecture_raw9b", "simjecture_sft9b", "simjecture_sftrl9b"}
        ):
            reply = self.advise()
            from .storage import write_json

            write_json(self.root / "decision-audit/latest-advice.json", reply)
            raise ValueError(
                "A student suggestion is available in decision-audit/latest-advice.json. Review it, then call run with advice_id, final executed_plan, all five component_sources and concrete override_reasons. Full host takeover remains allowed with every component marked host."
            )
        remaining = self.native.status()["remaining_seconds"]
        if remaining <= 0:
            raise TimeoutError("The research wall budget has expired")
        source_path = (self.root / "research" / source).resolve()
        if not source_path.is_relative_to(self.root / "research"):
            raise ValueError("Executed source must be in the research workspace")
        with source_path.open("rb") as stream:
            source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        # Native Simjecture has a 600 s default. Passing the current remaining
        # study budget explicitly removes that default for every comparison arm.
        effective_timeout = remaining if timeout is None else min(remaining, timeout)
        binding = dict(
            source=str(source),
            source_sha256=source_hash,
            args=list(args),
            timeout=effective_timeout,
            resources=kwargs.get("resources"),
            inputs=list(kwargs.get("inputs", ())),
            outputs=list(kwargs.get("outputs", ())),
        )
        plan = dict(executed_plan or {}, execution_binding=binding)
        identifier = "decision-" + fingerprint(dict(plan=plan, advice_id=advice_id))[:24]
        if advice_id:
            recorded = self.advice_records.get(advice_id)
            if recorded is None:
                events = self.journal.export(self.root.name)
                event = next(
                    (e for e in events if e["event_id"] == advice_id and e["kind"] == "raw_advice"), None
                )
                if event is None:
                    raise ValueError("Advice provenance was not found")
                recorded = dict(state=event["payload"]["observation"], reply=event["payload"]["raw_reply"])
            audit = decision_audit(
                study_id=self.root.name,
                decision_id=identifier,
                state=recorded["state"],
                original_advice=recorded["reply"]["advice"],
                executed_plan=plan,
                component_sources=component_sources or {},
                override_reasons=override_reasons or {},
                host_model=self.host_model,
            )
        else:
            reason = (
                "Independent baseline decision"
                if self.arm == "simjecture"
                else (takeover_reason or "Host takeover without an advice-bound plan")
            )
            audit = dict(
                study_id=self.root.name,
                decision_id=identifier,
                executed_plan=plan,
                original_advice=None,
                component_sources={key: "host" for key in DECISION_COMPONENTS},
                override_reasons={key: reason for key in DECISION_COMPONENTS},
                observation_sha256=fingerprint(
                    dict(remaining_wall_seconds=remaining, execution_binding=binding)
                ),
                host_model=self.host_model,
                scale_default="prefer_student_subject_to_capacity_and_physical_consistency",
                student_positive_credit_eligible=False,
                retained_student_components=[],
            )
        self.journal.append(
            study_id=self.root.name, event_id=identifier, kind="decision_audit", payload=audit
        )
        self.journal.append(
            study_id=self.root.name,
            event_id=identifier + "-advice-link",
            kind="advice_execution_link",
            payload=dict(decision_id=identifier, advice_id=advice_id),
        )
        try:
            receipt = self.native.run(source, args, timeout=effective_timeout, **kwargs)
        except Exception as error:
            self.journal.append(
                study_id=self.root.name,
                event_id=identifier + "-submission-failed",
                kind="execution_submission_failure",
                payload=dict(decision_id=identifier, error=str(error)),
            )
            raise
        self.journal.append(
            study_id=self.root.name,
            event_id="execution-" + receipt["id"],
            kind="execution_submission",
            payload=dict(decision_id=identifier, receipt=receipt),
        )
        return receipt
