"""Bounded research strategy decisions with host-executed experiment stops."""

from __future__ import annotations

import json
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_supervisor import parse_judge_stream
from .research_service import fingerprint, put


class DirectorVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["continue", "replan"]
    rationale: str = Field(min_length=16, max_length=3000)
    scientific_feasibility: Literal["adequate", "limited", "unknown"]
    budget_feasibility: Literal["feasible", "at_risk", "infeasible", "unknown"]
    stop_experiments: list[str] = Field(default_factory=list, max_length=8)
    next_action: str = Field(min_length=16, max_length=2400)

    @model_validator(mode="after")
    def coherent(self):
        if self.decision == "continue" and self.stop_experiments:
            raise ValueError("Stopping an experiment requires decision=replan")
        if len(set(self.stop_experiments)) != len(self.stop_experiments):
            raise ValueError("Stop IDs must be distinct")
        return self


class ResearchDirector:
    def director_packet(self):
        from .research_continuation import steering

        snapshot = self.service.status(compact=True)
        active = []
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
                    )
                )
        return dict(
            original_hypothesis=self.service.manifest["hypothesis"],
            operator_protocol=self.service.manifest.get("operator_protocol"),
            operator_steering=steering(self.service.root),
            remaining_seconds=snapshot["remaining_seconds"],
            snapshot=self.service.brief(max_bytes=8000),
            active_experiments=active,
            previous_decisions=self.service.director_status()[:2],
            authority="Execution strategy only; cannot change hypothesis or approve claims",
        )

    def director_prompt(self, packet):
        return (
            """You are the research director responsible for useful science within the remaining
wall budget. You can request host-executed stops of named experiments and require a replan.
The worker owns implementation and can respond with a recorded plan or reasoned challenge.
Respect new operator steering within the original scientific contract.
You do not accept scientific claims or change the original hypothesis, operator constraints,
deadline or evidence rules. Independent scientific review remains a separate fresh context.
Read-only source/data/documentation inspection is available. Do not modify files, send
control commands yourself or run simulations. Return a structured decision for the host.

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
Do not prescribe fixed phases or hourly schedules. Give a concrete useful next action.
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
SCHEMA:
"""
            + json.dumps(DirectorVerdict.model_json_schema())
            + "\nPACKET:\n"
            + json.dumps(packet)
        )

    def run_director(self, *, force=False):
        policy = self.service.manifest.get("director_policy", {})
        if not policy.get("enabled") or self.boundary():
            return False
        now = time.time()
        last = self.state.get("last_director_at", self.state.get("started_at", now))
        if not force and now - last < policy.get("interval_seconds", 300):
            return False
        if not self.service._all("experiments") and self.state.get("round", 0) < 2:
            return False
        if now < self.state.get("director_retry_after", 0) or self.state["deadline"] - now < 60:
            return False
        packet = self.director_packet()
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
            if rc:
                raise ValueError(f"Director exited with {rc}")
            verdict = DirectorVerdict.model_validate(
                parse_judge_stream(d / "response.json", self.args.backend)
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
                control_actions=[],
                authority="Execution strategy; not scientific approval",
                **verdict,
            )
            put(folder / (identifier + ".json"), record)
            for experiment in verdict["stop_experiments"]:
                stopped = self.service.cancel(
                    experiment, reason=f"{identifier}: {verdict['rationale']}"[:2400]
                )
                record["control_actions"].append(
                    dict(
                        experiment=experiment,
                        status=stopped["status"],
                        cancellation_confirmed=stopped.get("cancellation_confirmed", False),
                    )
                )
                put(folder / (identifier + ".json"), record)
            put(d / "verdict.json", record)
            self.state.update(
                last_director_at=time.time(), director_feedback=record, director_retry_after=0
            )
            if verdict["decision"] == "replan":
                self.state["director_wake_worker"] = True
            self.event("research_director", decision=identifier, verdict=verdict)
            self.save()
            return verdict["decision"] == "replan"
        except (ValueError, KeyError) as error:
            self.state.update(
                last_director_error=str(error)[:500], director_retry_after=time.time() + 120
            )
            self.event("director_invalid", error=str(error))
            self.save()
            return False
