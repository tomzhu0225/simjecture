"""Version 0.2 draft: scoped knowledge support, preserving the frozen 0.1 contract."""

from __future__ import annotations

import hashlib
from typing import Annotated, Literal

from pydantic import Field, model_validator

from . import attention_contract as core
from .attention_admission import AdmissionGate as CoreGate

VERSION = "scientific-attention/0.2-draft"
Support = Literal["none", "knowledge_lookup", "literature_review"]
SUPPORT_ACTIONS = {
    "knowledge_lookup": {"recheck", "request_worker_help", "wake_director"},
    "literature_review": {"request_worker_help", "wake_director"},
}


class Question(core.Record):
    id: core.Identifier
    text: Annotated[str, Field(min_length=1, max_length=480)]
    context_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    resolution: Literal["open", "resolved", "unknown"]
    evidence_ids: Annotated[list[core.Identifier], Field(min_length=1, max_length=8)]


class Retrieval(core.Record):
    id: core.Identifier
    question_id: core.Identifier
    context_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    support_kind: Literal["knowledge_lookup", "literature_review"]
    action: core.Action
    status: Literal["pending", "active", "completed", "failed"]
    outcome: Literal["matches", "no_matches", "inconclusive", "unavailable"]
    age_ms: core.Nonnegative
    reusable_for_ms: core.Nonnegative
    cooldown_remaining_ms: core.Nonnegative = 0
    evidence_ids: list[core.Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def result_contract(self):
        if self.action not in SUPPORT_ACTIONS[self.support_kind]:
            raise ValueError("Unsupported support/action combination")
        if self.status == "completed":
            if self.outcome == "unavailable" or not self.evidence_ids:
                raise ValueError(
                    "Completed retrieval needs a result receipt, including no-match searches"
                )
        elif self.outcome != "unavailable":
            raise ValueError("Unfinished/failed work does not have a completed result")
        return self


class Observation(core.Observation):
    schema_version: Literal["scientific-attention/0.2-draft"]
    questions: Annotated[list[Question], Field(max_length=16)]
    retrieval_history: Annotated[list[Retrieval], Field(max_length=32)]
    retrieval_history_complete: bool

    @model_validator(mode="after")
    def knowledge_references(self):
        ids = {q.id for q in self.questions}
        evidence = {e.id for e in self.evidence}
        if len(ids) != len(self.questions) or len({r.id for r in self.retrieval_history}) != len(
            self.retrieval_history
        ):
            raise ValueError("Question and retrieval IDs must be unique")
        for row in [*self.questions, *self.retrieval_history]:
            if not set(row.evidence_ids) <= evidence:
                raise ValueError("Question/retrieval evidence must exist in the observation")
        if any(r.question_id not in ids for r in self.retrieval_history):
            raise ValueError("Retrieval must reference a question in this observation")
        return self


class Decision(core.Decision):
    schema_version: Literal["scientific-attention/0.2-draft"]
    support_kind: Support
    question_ref: core.Identifier | None

    @model_validator(mode="after")
    def support_contract(self):
        if self.support_kind == "none":
            if self.question_ref is not None:
                raise ValueError("No support request must have question_ref=null")
        elif self.question_ref is None or self.action not in SUPPORT_ACTIONS[self.support_kind]:
            raise ValueError("Support needs a specific question and a compatible action")
        return self


class PackedView(core.PackedView):
    schema_version: Literal["scientific-attention/0.2-draft"]
    question_aliases: dict[str, str]


def semantic_view(packet, selected, omitted_count):
    view = core.semantic_view(packet, selected, omitted_count)
    view["version"] = VERSION
    evidence = {e.id: f"e{i}" for i, e in enumerate(selected)}
    questions = {q.id: f"q{i}" for i, q in enumerate(packet.questions)}
    by_id = {q.id: q for q in packet.questions}
    view["knowledge"] = dict(
        history_complete=packet.retrieval_history_complete,
        questions=[
            dict(
                id=questions[q.id],
                text=q.text,
                resolution=q.resolution,
                evidence=[evidence[e] for e in q.evidence_ids],
            )
            for q in packet.questions
        ],
        retrievals=[
            dict(
                question=questions[r.question_id],
                same_context=r.context_sha256 == by_id[r.question_id].context_sha256,
                support_kind=r.support_kind,
                action=r.action,
                status=r.status,
                outcome=r.outcome,
                age_ms=r.age_ms,
                reusable_for_ms=r.reusable_for_ms,
                cooldown_remaining_ms=r.cooldown_remaining_ms,
                evidence=[evidence[e] for e in r.evidence_ids],
            )
            for r in packet.retrieval_history
        ],
    )
    return view


def render(view, *, compact=False):
    text = core.render(view, compact=compact)
    instruction = (
        "\nSUPPORT\nnone: no knowledge request; question=null. "
        "knowledge_lookup: bounded retrieval with recheck, or helper/director interpretation. "
        "literature_review: a scoped helper/director review. Select a visible question alias. "
        "Use retrieval history to avoid repeating active or reusable work. Matches are not proof "
        "of applicability; no matches are not proof that relevant literature does not exist. "
        "Return action, support_kind, question_ref (alias or null), basis and evidence aliases."
    )
    return text.replace("\nDATA\n", instruction + "\nDATA\n", 1)


def pack(packet, count_tokens, *, token_counter_id, budget_tokens=2048, compact=False):
    if budget_tokens <= 0:
        raise ValueError("A positive full-input budget is required")
    # Retrieval evidence is mandatory even if its producer marked it optional.
    referenced = {
        ref for row in [*packet.questions, *packet.retrieval_history] for ref in row.evidence_ids
    }
    selected = [e for e in packet.evidence if e.required or e.id in referenced]
    optional = sorted(
        (e for e in packet.evidence if e not in selected), key=lambda e: (e.age_ms, e.id)
    )

    def encode(items):
        text = render(
            semantic_view(packet, items, len(packet.evidence) - len(items)), compact=compact
        )
        count = count_tokens(text)
        if type(count) is not int or count < 0:
            raise ValueError("Token counter must return a nonnegative integer")
        return text, count

    text, tokens = encode(selected)
    if tokens <= budget_tokens:
        for item in optional:
            candidate, count = encode(selected + [item])
            if count <= budget_tokens:
                selected.append(item)
                text, tokens = candidate, count
    included = [e.id for e in selected]
    return PackedView(
        schema_version=VERSION,
        packet_id=packet.packet_id,
        format="column-json" if compact else "named-json",
        token_counter_id=token_counter_id,
        text=text,
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        input_tokens=tokens,
        budget_tokens=budget_tokens,
        included_ids=included,
        omitted_ids=[e.id for e in packet.evidence if e.id not in included],
        aliases={f"e{i}": e.id for i, e in enumerate(selected)},
        question_aliases={f"q{i}": q.id for i, q in enumerate(packet.questions)},
        status="ready" if tokens <= budget_tokens else "insufficient_budget",
    )


class AdmissionGate:
    """Reference support admission. Retrieval execution and durable state are external."""

    def __init__(self, profile=None):
        self.profile = profile
        self.gates = {}
        self.dispatched = set()

    def evaluate(self, submitted, view, decision, current, *, now_ms):
        route = decision.policy_id, decision.support_kind, decision.question_ref
        gate = self.gates.setdefault(route, CoreGate(self.profile))
        gate.dispatched = self.dispatched
        result = gate.evaluate(submitted, view, decision, current, now_ms=now_ms)
        result.update(support_kind=decision.support_kind, question_ref=decision.question_ref)
        if result["reason"] in {
            "policy_choice",
            "awaiting_persistence",
            "fresh_grounded_persistent_request",
        }:
            # A different current choice interrupts persistence. An older response
            # must never erase a confirmation begun on a newer observation.
            for other_route, other_gate in self.gates.items():
                if other_route == route or other_route[0] != decision.policy_id:
                    continue
                pending = other_gate.pending.get(submitted.scope())
                if (
                    pending
                    and pending["clock_id"] == submitted.clock_id
                    and pending["sequence"] <= submitted.sequence
                ):
                    other_gate.pending.pop(submitted.scope(), None)
        if decision.support_kind == "none" or result["disposition"] in {"rejected", "suppressed"}:
            return result
        if result["reason"] not in {
            "policy_choice",
            "awaiting_persistence",
            "no_new_observation",
            "fresh_grounded_persistent_request",
        }:
            return result

        def blocked(disposition, reason):
            pending = gate.pending.get(submitted.scope())
            if (
                pending
                and pending["sequence"] <= submitted.sequence
                and pending["clock_id"] == submitted.clock_id
            ):
                gate.pending.pop(submitted.scope(), None)
            return result | dict(disposition=disposition, reason=reason)

        visible = set(view.question_aliases.values())
        previous = {q.id: q for q in submitted.questions}
        questions = {q.id: q for q in current.questions}
        qid = decision.question_ref
        if qid not in visible or qid not in previous or qid not in questions:
            return blocked("rejected", "question_not_visible")
        question = questions[qid]
        if current.workflow_state == "complete":
            return blocked("suppressed", "workflow_closed")
        if (
            current.workflow_state == "unknown"
            or current.assistance == "unknown"
            or current.missing_channels
        ):
            return blocked("recheck", "required_state_unknown")
        if question.context_sha256 != previous[qid].context_sha256:
            return blocked("recheck", "question_context_changed")
        if not current.retrieval_history_complete or question.resolution == "unknown":
            return blocked("recheck", "retrieval_context_unknown")
        if question.resolution == "resolved":
            return blocked("suppressed", "question_already_resolved")
        if current.assistance in {"pending", "active", "returned_required"}:
            return blocked("suppressed", "same_incident_already_served")
        matching = [
            r
            for r in current.retrieval_history
            if r.question_id == qid and r.context_sha256 == question.context_sha256
        ]
        if any(r.status in {"pending", "active"} for r in matching):
            return blocked("suppressed", "question_investigation_active")
        relevant = [r for r in matching if r.support_kind == decision.support_kind]
        if any(r.cooldown_remaining_ms > 0 for r in relevant):
            return blocked("pending", "retrieval_retry_cooldown")
        for row in relevant:
            same_work = (
                decision.support_kind == "literature_review" or row.action == decision.action
            )
            if same_work and row.status == "completed" and row.age_ms <= row.reusable_for_ms:
                return blocked("suppressed", "recent_support_result_available")
        return result

    def record_dispatch(self, packet):
        """Record an actual EXPERT dispatch; cheap lookups update retrieval_history instead."""
        self.dispatched.add(packet.scope())
        for gate in self.gates.values():
            gate.pending.pop(packet.scope(), None)


class Choice(core.Record):
    """Trainable payload: identifiers and receipts are supplied by the host."""

    action: core.Action
    support_kind: Support
    question_ref: str | None
    basis: Literal["unspecified", "silence", "repetition", "measurement", "source", "missing"]
    evidence: list[str]


def bind_choice(packet, view, choice: Choice, *, policy_id):
    if view.packet_id != packet.packet_id or view.status != "ready":
        raise ValueError("A ready view of the same packet is required")
    if any(e not in view.aliases for e in choice.evidence):
        raise ValueError("Unknown model evidence alias")
    if choice.question_ref is not None and choice.question_ref not in view.question_aliases:
        raise ValueError("Unknown model question alias")
    return Decision(
        schema_version=VERSION,
        packet_id=packet.packet_id,
        model_view_sha256=view.sha256,
        policy_id=policy_id,
        status="ok",
        action=choice.action,
        support_kind=choice.support_kind,
        question_ref=view.question_aliases.get(choice.question_ref),
        basis=choice.basis,
        evidence_basis="selected" if choice.evidence else "whole_view",
        evidence_ids=[view.aliases[e] for e in choice.evidence],
    )


def schemas():
    return {
        name: cls.model_json_schema()
        | {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:simjecture:scientific-attention:0.2-draft:" + name,
        }
        for name, cls in {
            "Observation": Observation,
            "Decision": Decision,
            "PackedView": PackedView,
            "Choice": Choice,
        }.items()
    }
