"""Bounded research strategy decisions with host-executed experiment stops."""

from __future__ import annotations

import json
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_supervisor import parse_judge_stream
from .research_development import development_guidance
from .research_registration import RegistrationTuning
from .research_resources import StorageIncrease
from .research_service import fingerprint, put


class TimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: float = Field(gt=0, allow_inf_nan=False)
    reason: str = Field(min_length=16, max_length=2400)


class DirectorVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["continue", "replan"]
    rationale: str = Field(min_length=16, max_length=3000)
    scientific_feasibility: Literal["adequate", "limited", "unknown"]
    budget_feasibility: Literal["feasible", "at_risk", "infeasible", "unknown"]
    stop_experiments: list[str] = Field(default_factory=list, max_length=8)
    wake_worker: bool = Field(
        default=False,
        description=(
            "Resume an idle worker for concrete work that can proceed while experiments run, "
            "without stopping those experiments or requiring a strategy change."
        ),
    )
    park_worker: bool = Field(
        default=False,
        description="Wait without inference until work, review or operator feedback arrives.",
    )
    report_assessment: str | None = Field(
        default=None,
        max_length=512,
        description="Report path for independent assessment now; never approves a claim.",
    )
    next_action: str = Field(min_length=16, max_length=2400)
    storage_increase: StorageIncrease | None = Field(
        default=None,
        description="Request larger storage allowances when operator authority permits.",
    )
    registration_tuning: RegistrationTuning | None = Field(
        default=None,
        description="Tune remote registration probe timeout and retries when delegated.",
    )
    time_request: TimeRequest | None = Field(
        default=None, description="Ask the operator for additional hours; never grants time."
    )

    @model_validator(mode="after")
    def coherent(self):
        if self.decision == "continue" and self.stop_experiments:
            raise ValueError("Stopping an experiment requires decision=replan")
        if len(set(self.stop_experiments)) != len(self.stop_experiments):
            raise ValueError("Stop IDs must be distinct")
        if self.park_worker and (self.wake_worker or self.decision == "replan"):
            raise ValueError("Parking cannot also wake the worker or require a replan response")
        return self


class ResearchDirector:
    def director_packet(self):
        from .research_continuation import steering

        snapshot = self.service.status(compact=True)
        active = []
        records = {
            kind: {r["id"]: r.get("status") for r in self.service._all(kind)}
            for kind in (
                "experiments",
                "notebook",
                "methods",
                "reviews",
                "progress",
                "report_requests",
            )
        }
        previous = self.state.get("director_seen_records", {})
        now = time.time()
        for r in snapshot["experiments"]:
            if r["status"] in {"queued", "running"}:
                t = r.get("telemetry")
                active.append(
                    dict(
                        id=r["id"],
                        status=r["status"],
                        purpose=r.get("purpose"),
                        timeout=r.get("timeout"),
                        monitor=r.get("monitor"),
                        telemetry=t,
                        elapsed_seconds=max(0, now - (r.get("started_at") or r["created_at"])),
                        telemetry_age_seconds=now - t["observed_at"] if t else None,
                        estimated_additional_seconds=t.get("estimated_additional_seconds")
                        if t
                        else None,
                        cancel_requested=r.get("cancel_requested", False),
                        transport_status=r.get("transport_status")
                        or ("connected" if r.get("machine", "local") == "local" else "unknown"),
                    )
                )
        return dict(
            original_hypothesis=self.service.manifest["hypothesis"],
            operator_protocol=self.service.manifest.get("operator_protocol"),
            operator_steering=steering(self.service.root),
            remaining_seconds=snapshot["remaining_seconds"],
            budget=snapshot["budget"],
            finalization=snapshot.get("finalization", {}),
            snapshot=self.context_brief(max_bytes=8000),
            active_experiments=active,
            worker_waiting_for=list(self.state.get("waiting_for", [])),
            worker_wait=snapshot.get("worker_wait", {}),
            report_assessments=snapshot.get("report_assessments", []),
            previous_decisions=self.service.director_status()[:2],
            pending_replan=self.service.pending_director_replan(),
            resource_limits=snapshot["resource_limits"],
            resource_policy=snapshot["resource_policy"],
            registration=snapshot["registration"],
            solver_development=snapshot["solver_development"],
            first_strategy_review=not bool(previous),
            evidence_changes={
                kind: [
                    dict(id=identifier, status=status)
                    for identifier, status in index.items()
                    if identifier not in previous.get(kind, {})
                    or previous[kind][identifier] != status
                ]
                for kind, index in records.items()
            },
            record_index=records,
            authority=(
                "Execution strategy, delegated storage increases and registration tuning; "
                "cannot change hypothesis or approve claims"
            ),
        )

    def director_prompt(self, packet):
        return (
            """You are the research director responsible for useful science within the remaining
wall budget. You can request host-executed stops of named experiments and require a replan.
The worker owns implementation and can respond with a recorded plan or reasoned challenge.
Respect new operator steering within the original scientific contract.
You do not accept scientific claims or change the original hypothesis, operator constraints,
deadline or evidence rules. Independent scientific review remains a separate fresh context.
You may ask the operator for additional hours using time_request (hours and a concrete reason).
This is a request only: plan against the current authoritative budget until it is granted.
budget.extensions records operator-authorized changes; update forecasts when it changes.
Read-only source/data/documentation inspection is available. Do not modify files, send
control commands yourself or run simulations. Return a structured decision for the host.
When resource_policy.director_can_increase is true, you may set storage_increase to larger
max_experiment_bytes and max_total_bytes with a concrete reason. These are adjustable
allowances, not scientific constraints. Use actual build/output sizes and expected retention.
The host records before/after allowances and applies them to new experiments only. A larger
experiment allowance also raises its per-file ceiling. There is no additional fixed 512 MiB
ceiling. Existing jobs retain their recorded reservations. Disk space and shared host capacity
remain finite: do not grant unjustified storage or assume the allowance creates physical space.
Without this delegated authority, report the blocker to the operator; do not request a grant.

When registration.policy.director_can_tune is true, you may request registration_tuning
with timeout_seconds, max_attempts and a reason based on registration.recent_attempts.
A full worker probe reads and fingerprints all installed instruments; a slow probe does
not establish a missing instrument or scientific failure. Increase the deadline when
measured latency warrants it, or reduce retries when they waste time. Only transport
failures are retried. Worker rejections and immutable-identity checks cannot be bypassed.
The host records the change, wakes the worker and bounds every probe and retry by the
compute deadline, preserving the report reserve. Registration tuning applies to future
requests; it neither changes active jobs nor grants an unreviewed method approval.
Do not repeat an unchanged timed-out registration without a concrete recovery action.

Use an MVP research strategy: establish an affordable end-to-end trajectory through the
scientifically relevant window before spending the campaign polishing early-time diagnostics.
Fix blockers to valid completion first. Then refine features that affect the conclusion.
Commissioned cases are starting examples. Mesh, adaptive timestep, rank count, output cadence
and restart strategy can change with documented qualification; they are not the hypothesis.
Do not force completion with invalid physics or unstable steps. Coarse results are exploratory.
Physical assumptions and domain changes need explicit scope, not silent substitution.

Evaluate SCIENTIFIC usefulness and BUDGET feasibility separately. New files, correct local
diagnostics, or a successful startup do not establish a path to the original observable.
Consider actual costs and numerical limits. Test adaptive timestepping/accuracy, mesh and
rank scaling, or justified patches/restarts before continuing an unaffordable configuration.
Respect the host finalization.compute_deadline when present: numerical work must fit
before that cutoff, leaving the protected report reserve. Otherwise do not prescribe
fixed phases or hourly schedules. Give a concrete useful next action.
This is execution strategy review, not a fresh methods or claim audit. Reuse the
recorded limitations of unchanged cases. Inspect new artifacts only when they bear
on the current decision; request a separate methods review for extensive qualification.
Start with evidence_changes and the previous decision. Retrieve selected fields or
bounded excerpts when possible; avoid printing entire large JSON, CSV or trace files.
Reopen unchanged sources when a concrete uncertainty affects the execution decision.
An intentional timing/diagnostic pilot need not reach the full scientific window; evaluate
whether it has collected enough information and whether its remaining cost is worthwhile.

Active telemetry is MUTABLE operational information, not scientific evidence. It can be
missing/stale, has researcher-declared targets, and its linear forecast can change as physics
evolves. Do not falsely assert reconnection, convergence, or falsification from it.
For stop_experiments choose only IDs from active_experiments. Stop expensive or unproductive
individual experiments when a better strategy is justified; keep the investigation running.
Use decision=replan to stop or redirect; use continue only when the current strategy is
defensible. Explain uncertainty rather than inventing missing measurements. Acknowledge
worker challenges and assess their recorded plan. Stops preserve partial data and history.
A continue review does not waive the pending_replan worker response. A later replan
replaces the earlier response requirement; the worker must acknowledge that latest replan.
When worker_waiting_for is nonempty, the worker is parked until an experiment finishes
unless you explicitly wake it. A continue decision with next_action alone does not
deliver immediate parallel work. Set wake_worker=true when a concrete useful task can
proceed now, such as submitting completed qualification for review or analyzing existing
outputs while a simulation continues. Keep useful experiments running. Do not wake the
worker merely to poll, restate limitations or wait again. A replan always wakes it and
retains its acknowledgement requirement; a continue wake-up adds no new approval gate.
For an honest inconclusive report ready for assessment, set report_assessment to its
research-relative path, usually RESULTS.md. The host queues a fresh independent report
review now; it does not approve the hypothesis or change exploratory evidence stages.
Do not merely ask for host routing in next_action prose. Set park_worker=true with a
concrete waiting reason when no useful worker action can proceed before feedback.
The campaign clock, active experiments and supervision continue. A replan, explicit
wake-up or new operator guidance resumes the worker. Parking cannot accompany a replan
or a wake-up. Validate a claimed API blocker against the actual error and allowed values;
claim review accepts unresolved, while exploratory reports use report assessment.
"""
            + development_guidance(packet["solver_development"]["policy"])
            + "\nSCHEMA:\n"
            + json.dumps(DirectorVerdict.model_json_schema())
            + "\nPACKET:\n"
            + json.dumps({k: v for k, v in packet.items() if k != "record_index"})
        )

    def director_strategy_signature(self, packet):
        """Exclude changing clocks/telemetry; retain changes to work and steering."""
        return fingerprint(
            dict(
                active=[
                    {
                        k: r.get(k)
                        for k in (
                            "id",
                            "status",
                            "purpose",
                            "timeout",
                            "monitor",
                            "cancel_requested",
                        )
                    }
                    for r in packet["active_experiments"]
                ],
                records=packet["record_index"],
                operator_steering=packet["operator_steering"],
                pending_replan=packet["pending_replan"],
                context_warning=packet["snapshot"].get("context_warning"),
                resource_limits=packet.get("resource_limits"),
                resource_policy=packet.get("resource_policy"),
                registration=packet.get("registration"),
                worker_wait=packet.get("worker_wait"),
                budget_revision=packet.get("budget", {}).get("revision", 0),
            )
        )

    def defer_unchanged_director(self, packet, signature, now, last):
        policy = self.service.manifest["director_policy"]
        interval = policy.get("interval_seconds", 300)
        # Pre-existing studies retain their recorded cadence.
        maximum = policy.get("unchanged_review_seconds", interval)
        previous = self.state.get("director_feedback", {})
        parked_idle = (
            not packet["active_experiments"]
            and packet.get("worker_wait", {}).get("status") == "waiting"
        )
        if (
            now - last >= maximum
            or self.state.get("director_strategy_signature") != signature
            or previous.get("decision") != "continue"
            or (previous.get("budget_feasibility") != "feasible" and not parked_idle)
            or packet["pending_replan"]
            or packet["remaining_seconds"] <= maximum
            or (
                not packet["active_experiments"]
                and packet.get("worker_wait", {}).get("status") != "waiting"
            )
        ):
            return False
        for r in packet["active_experiments"]:
            t = r.get("telemetry") or {}
            estimate = r.get("estimated_additional_seconds")
            elapsed = r.get("elapsed_seconds", 0)
            timeout = r.get("timeout")
            if (
                r["status"] != "running"
                or r.get("cancel_requested")
                or r.get("transport_status") != "connected"
                or not t.get("available")
                or (r.get("telemetry_age_seconds") or 0) > 60
                or estimate is None
                or estimate > packet["remaining_seconds"]
                or timeout is None
                or elapsed + estimate > 0.85 * timeout
            ):
                return False
        return True

    def run_director(self, *, force=False):
        policy = self.service.manifest.get("director_policy", {})
        if not policy.get("enabled") or self.boundary():
            return False
        now = time.time()
        last = self.state.get("last_director_at", self.state.get("started_at", now))
        if not force and now - last < policy.get("interval_seconds", 300):
            return False
        if (
            not self.service._all("experiments")
            and self.state.get("round", 0) < 2
            and not self.service._all("registration_attempts")
            and not (self.service.work / "RESULTS.md").is_file()
        ):
            return False
        if now < self.state.get("director_retry_after", 0) or self.state["deadline"] - now < 60:
            return False
        if not force and now < self.state.get("director_next_check_at", 0):
            return False
        packet = self.director_packet()
        signature = self.director_strategy_signature(packet)
        if not force and self.defer_unchanged_director(packet, signature, now, last):
            self.state["director_deferred_count"] = self.state.get("director_deferred_count", 0) + 1
            self.state["director_next_review_at"] = last + policy["unchanged_review_seconds"]
            self.state["director_next_check_at"] = min(
                now + 60, self.state["director_next_review_at"]
            )
            self.save()
            return False
        self.state.pop("director_next_review_at", None)
        self.state.pop("director_next_check_at", None)
        self.state["director_count"] = self.state.get("director_count", 0) + 1
        d = self.directory / f"director-{self.state['director_count']:05d}"
        d.mkdir(exist_ok=True)
        put(d / "packet.json", packet)
        self.save()
        try:
            original_allowance = getattr(self.args, "turn_seconds", None)
            self.args.turn_seconds = min(
                original_allowance or 120, policy.get("review_seconds", 120)
            )
            try:
                rc = self.launch(d, self.director_prompt(packet), judge=True)
            finally:
                if original_allowance is None:
                    del self.args.turn_seconds
                else:
                    self.args.turn_seconds = original_allowance
            if self.boundary():
                return False
            if packet.get("budget", {}).get("revision", 0) != len(
                self.service.manifest.get("budget_extensions", [])
            ):
                self.event("director_budget_changed", action="Replan using the new operator budget")
                return False
            if rc:
                raise ValueError(f"Director exited with {rc}")
            verdict = DirectorVerdict.model_validate(
                parse_judge_stream(
                    d / "response.json", self.args.backend, allow_readonly_tools=True
                )
            ).model_dump()
            known = {r["id"] for r in packet["active_experiments"]}
            if any(i not in known for i in verdict["stop_experiments"]):
                raise ValueError(
                    "Director stop list must contain this packet's active experiment IDs"
                )
            identifier = (
                "director_" + fingerprint(dict(packet=fingerprint(packet), verdict=verdict))[:24]
            )
            folder = self.service.root / "director"
            folder.mkdir(exist_ok=True)
            record = dict(
                id=identifier,
                created_at=time.time(),
                packet_sha256=fingerprint(packet),
                control_actions=[
                    dict(experiment=experiment, status="stop_pending", cancellation_confirmed=False)
                    for experiment in verdict["stop_experiments"]
                ],
                authority="Execution strategy; not scientific approval",
                **verdict,
            )
            put(folder / (identifier + ".json"), record)
            if verdict["time_request"]:
                record["time_request_action"] = self.service.request_time(
                    **verdict["time_request"], requested_by="director",
                    key="director-" + str(packet["budget"]["revision"]) + "-"
                    + fingerprint(verdict["time_request"])[:40],
                )
                put(folder / (identifier + ".json"), record)
            if verdict["report_assessment"]:
                try:
                    request = self.service.assess_report(
                        verdict["report_assessment"], reason=verdict["rationale"][:2400]
                    )
                    record["report_assessment_action"] = dict(status="queued", request=request)
                except (OSError, ValueError) as error:
                    record["report_assessment_action"] = dict(
                        status="rejected", error=str(error)[:500]
                    )
                    self.state["director_wake_worker"] = True
                put(folder / (identifier + ".json"), record)
            if verdict["storage_increase"]:
                try:
                    adjustment = self.service.increase_storage(
                        verdict["storage_increase"], director_decision=identifier
                    )
                    record["storage_action"] = dict(status="granted", adjustment=adjustment)
                except (OSError, ValueError) as error:
                    record["storage_action"] = dict(status="rejected", error=str(error)[:500])
                put(folder / (identifier + ".json"), record)
            if verdict["registration_tuning"]:
                try:
                    adjustment = self.service.tune_registration(
                        verdict["registration_tuning"], director_decision=identifier
                    )
                    record["registration_action"] = dict(status="granted", adjustment=adjustment)
                except (OSError, ValueError) as error:
                    record["registration_action"] = dict(status="rejected", error=str(error)[:500])
                put(folder / (identifier + ".json"), record)
            for action in record["control_actions"]:
                try:
                    stopped = self.service.cancel(
                        action["experiment"], reason=f"{identifier}: {verdict['rationale']}"[:2400]
                    )
                    action.update(
                        status=stopped["status"],
                        cancellation_confirmed=stopped.get("cancellation_confirmed", False),
                    )
                except (OSError, RuntimeError, ValueError, KeyError) as error:
                    action.update(status="stop_failed", error=str(error)[:500])
                    self.event(
                        "director_control_failed",
                        decision=identifier,
                        experiment=action["experiment"],
                        error=action["error"],
                    )
                put(folder / (identifier + ".json"), record)
            put(d / "verdict.json", record)
            self.state.update(
                last_director_at=time.time(),
                director_feedback=record,
                director_retry_after=0,
                last_director_error=None,
                director_strategy_signature=signature,
                director_seen_records=packet["record_index"],
            )
            wake_worker = (
                verdict["decision"] == "replan"
                or verdict["wake_worker"]
                or record.get("storage_action", {}).get("status") == "granted"
                or record.get("registration_action", {}).get("status") == "granted"
            )
            if wake_worker:
                self.state["director_wake_worker"] = True
            if verdict["park_worker"]:
                try:
                    if self.service.pending_director_replan() or wake_worker:
                        raise ValueError(
                            "Resolve the pending replan or granted recovery before parking"
                        )
                    wait = self.service.wait(
                        verdict["next_action"],
                        experiments=[r["id"] for r in packet["active_experiments"]],
                        reports=[
                            r["id"]
                            for r in self.service._all("report_requests")
                            if r["status"] in {"queued", "running"}
                        ],
                        reviews=[
                            r["id"] for r in self.service._all("reviews") if r["status"] == "queued"
                        ],
                        methods=[
                            r["id"] for r in self.service._all("methods") if r["status"] == "queued"
                        ],
                        for_operator=True,
                    )
                    record["worker_wait_action"] = dict(status="parked", wait=wait)
                except (OSError, ValueError) as error:
                    record["worker_wait_action"] = dict(status="rejected", error=str(error)[:500])
                put(folder / (identifier + ".json"), record)
                put(d / "verdict.json", record)
            self.event("research_director", decision=identifier, verdict=verdict)
            self.save()
            return wake_worker
        except (ValueError, KeyError, OSError) as error:
            self.state.update(
                last_director_error=str(error)[:500], director_retry_after=time.time() + 120
            )
            self.event("director_invalid", error=str(error))
            self.save()
            return False
