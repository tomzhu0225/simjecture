"""Small scripted curriculum for protocol bootstrap, never a utility oracle.

All variants of a base context share a split. Labels use only public packet
content. Generator metadata and labels are stored outside the model input.
"""

from __future__ import annotations

import hashlib
import json
import random

from . import attention_contract as core
from . import attention_support as protocol

SCENARIOS = (
    "quiet_active",
    "quiet_just_ended",
    "persistent_silence",
    "missing_telemetry",
    "lookup_needed",
    "lookup_active",
    "lookup_recent_no_match",
    "lookup_recent_matches",
    "lookup_stale",
    "lookup_context_changed",
    "lookup_failed_cooldown",
    "literature_active",
    "literature_recent",
    "question_resolved",
    "measurement_disagreement",
    "receipt_disagreement",
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def identifier(seed, role):
    return digest([seed, role])[:24]


def evidence(seed, role, kind, content, *, origin="host", measurements=None):
    values = measurements or []
    raw = dict(content=content, measurements=[m.model_dump() for m in values])
    return core.Evidence(
        id=identifier(seed, role),
        source=identifier(seed, role + ":source"),
        source_role=role,
        source_sha256=digest(raw),
        kind=kind,
        age_ms=100,
        origin=origin,
        content=content,
        measurements=values,
    )


def make_observation(seed, scenario):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown development scenario")
    rng = random.Random(seed)
    domain, quantity, unit = rng.choice(
        [
            ("plasma control", "field_peak", "V/m"),
            ("thermal simulation", "temperature", "K"),
            ("spectral analysis", "frequency", "Hz"),
        ]
    )
    value = rng.uniform(10, 1000)
    measurements = [
        core.Measurement(name="stored_" + quantity, value=value, unit=unit, validity="measured"),
        core.Measurement(
            name="reported_" + quantity,
            value=value * (100 if scenario == "measurement_disagreement" else 1),
            unit=unit,
            validity="measured",
        ),
    ]
    data = evidence(
        seed,
        "current_diagnostics",
        "measurement",
        "Stored and reported values for the current run.",
        origin="instrument",
        measurements=measurements,
    )
    events = [data]
    questions = []
    history = []
    needs_knowledge = scenario.startswith(("lookup_", "literature_", "question_"))
    if needs_knowledge:
        text = (
            "Which approved reference procedure defines convergence "
            f"for this {domain} configuration?"
        )
        query = evidence(seed, "worker_question", "expectation", text, origin="worker")
        events.append(query)
        context = digest([domain, quantity, unit, value])
        question = protocol.Question(
            id=identifier(seed, "question"),
            text=text,
            context_sha256=context,
            resolution="resolved" if scenario == "question_resolved" else "open",
            evidence_ids=[query.id],
        )
        questions.append(question)
        if scenario not in {"lookup_needed", "question_resolved"}:
            active = scenario in {"lookup_active", "literature_active"}
            literature = scenario.startswith("literature_")
            failed = scenario == "lookup_failed_cooldown"
            receipt = evidence(
                seed,
                "knowledge_result",
                "receipt",
                "A reference procedure for a neighbouring configuration was returned; "
                "its applicability to this configuration needs assessment."
                if scenario == "lookup_recent_matches"
                else "Scoped search returned no matching records; relevant work may still exist."
                if not literature
                else "A scoped review returned evidence for the worker to assess.",
            )
            if not active and not failed:
                events.append(receipt)
            history.append(
                protocol.Retrieval(
                    id=identifier(seed, "retrieval"),
                    question_id=question.id,
                    context_sha256=digest([context, "older setup"])
                    if scenario == "lookup_context_changed"
                    else context,
                    support_kind="literature_review" if literature else "knowledge_lookup",
                    action="request_worker_help" if literature else "recheck",
                    status="active" if active else "failed" if failed else "completed",
                    outcome="unavailable"
                    if active or failed
                    else "matches"
                    if literature or scenario == "lookup_recent_matches"
                    else "no_matches",
                    age_ms=90000 if scenario == "lookup_stale" else rng.randint(100, 5000),
                    reusable_for_ms=60000,
                    cooldown_remaining_ms=10000 if failed else 0,
                    evidence_ids=[] if active or failed else [receipt.id],
                )
            )
        if scenario == "question_resolved":
            events.append(
                evidence(
                    seed,
                    "prior_answer",
                    "assistance",
                    "The worker recorded the applicable procedure "
                    "and marked this question resolved.",
                    origin="worker",
                )
            )
    if scenario == "receipt_disagreement":
        events.append(
            evidence(
                seed,
                "protected_adapter_receipt",
                "receipt",
                "The protected adapter and independent process receipt report different liveness.",
                measurements=[
                    core.Measurement(
                        name="process_alive", value=0.0, unit="1", validity="measured"
                    ),
                    core.Measurement(
                        name="adapter_reported_alive", value=1.0, unit="1", validity="measured"
                    ),
                ],
            )
        )
    quiet = (
        "active"
        if scenario == "quiet_active"
        else "expired"
        if scenario == "quiet_just_ended"
        else "none"
    )
    timing = core.Timing(
        phase_elapsed_ms=rng.randint(90000, 120000),
        progress_age_ms=rng.randint(60000, 80000)
        if scenario in {"persistent_silence", "quiet_active", "quiet_just_ended"}
        else rng.randint(500, 2000),
        heartbeat_age_ms=100,
        quiet_state=quiet,
        quiet_remaining_ms=40000 if quiet == "active" else 0 if quiet == "expired" else None,
        since_quiet_end_ms=rng.randint(1, 2000) if quiet == "expired" else None,
        retries_remaining=0,
        budget_remaining_ms=rng.randint(300000, 600000),
    )
    return protocol.Observation(
        schema_version=protocol.VERSION,
        packet_id=identifier(seed, "packet:" + scenario),
        subject_id=identifier(seed, "subject"),
        operation_id=identifier(seed, "operation"),
        incident_id=identifier(seed, "incident"),
        clock_id=identifier(seed, "clock"),
        captured_ms=200000,
        sequence=1,
        state_revision=1,
        task=f"Check this {domain} and report the actual diagnostic quantities.",
        phase="diagnostic_review",
        scientific_contract=[
            f"Stored and reported {quantity} must use the declared unit {unit}.",
            "A valid negative result remains valid science; preserve original criteria.",
            "Protected adapter repairs require an independent authority decision.",
        ],
        worker_state="parked",
        workflow_state="running",
        assistance="none",
        timing=timing,
        evidence=events,
        missing_channels=["current_progress"] if scenario == "missing_telemetry" else [],
        questions=questions,
        retrieval_history=history,
        retrieval_history_complete=True,
    )


def scripted_preference(packet, view):
    """A transparent procedural teacher, not measured scientific intervention value."""
    aliases = {value: key for key, value in view.aliases.items()}
    question_aliases = {value: key for key, value in view.question_aliases.items()}

    def choice(action="observe", support="none", question=None, basis="unspecified", refs=()):
        return protocol.Choice(
            action=action,
            support_kind=support,
            question_ref=question,
            basis=basis,
            evidence=[aliases[r] for r in refs],
        )

    if packet.missing_channels:
        return choice("recheck", basis="missing", refs=[packet.evidence[0].id])
    values = {m.name: (m.value, e.id) for e in packet.evidence for m in e.measurements}
    if {"process_alive", "adapter_reported_alive"} <= values.keys() and values["process_alive"][
        0
    ] != values["adapter_reported_alive"][0]:
        return choice("request_repair_judge", basis="source", refs=[values["process_alive"][1]])
    for name, (value, ref) in values.items():
        if (
            name.startswith("stored_")
            and values.get(name.replace("stored_", "reported_", 1), (value, None))[0] != value
        ):
            return choice("wake_director", basis="measurement", refs=[ref])
    for q in packet.questions:
        if q.resolution == "resolved":
            continue
        if not packet.retrieval_history_complete or q.resolution == "unknown":
            return choice("recheck", basis="missing", refs=q.evidence_ids)
        matching = [
            r
            for r in packet.retrieval_history
            if r.question_id == q.id and r.context_sha256 == q.context_sha256
        ]
        if any(r.status in {"active", "pending"} or r.cooldown_remaining_ms > 0 for r in matching):
            return choice()
        fresh = [r for r in matching if r.status == "completed" and r.age_ms <= r.reusable_for_ms]
        if any(r.support_kind == "literature_review" for r in fresh):
            return choice()
        kb = [r for r in fresh if r.support_kind == "knowledge_lookup"]
        if not kb:
            return choice(
                "recheck", "knowledge_lookup", question_aliases[q.id], "missing", q.evidence_ids
            )
        return choice(
            "request_worker_help",
            "knowledge_lookup" if kb[-1].outcome == "matches" else "literature_review",
            question_aliases[q.id],
            "missing",
            q.evidence_ids + kb[-1].evidence_ids,
        )
    silence = packet.timing.unexplained_silence_ms()
    if silence is not None and silence >= 30000:
        return choice("request_worker_help", basis="silence", refs=[packet.evidence[0].id])
    return choice()


def split_for_group(group_id):
    bucket = int(digest(group_id)[:8], 16) % 10
    return "validation" if bucket == 0 else "synthetic_audit" if bucket == 1 else "train"


def generate(groups, *, seed=20261025):
    if groups < 1:
        raise ValueError("At least one context group is required")
    for group in range(groups):
        episode_seed = seed + group
        group_id = identifier(episode_seed, "context_group")
        for scenario in SCENARIOS:
            packet = make_observation(episode_seed, scenario)
            # A character counter is used solely to assemble the FULL view. It is
            # not exported as a model-token count or used to truncate these records.
            view = protocol.pack(
                packet,
                len,
                token_counter_id="assembly:characters-not-model-tokens",
                budget_tokens=1_000_000,
            )
            target = scripted_preference(packet, view)
            protocol.bind_choice(packet, view, target, policy_id="scripted-bootstrap-v1")
            yield dict(
                schema_version="scientific-attention-training/0.1-draft",
                id=identifier(episode_seed, "record:" + scenario),
                group_id=group_id,
                split=split_for_group(group_id),
                observation=packet.model_dump(),
                input_text=view.text,
                input_sha256=view.sha256,
                target=target.model_dump(),
                provenance=dict(
                    origin="synthetic",
                    generator="scripted-context-variants-v1",
                    mechanism=scenario,
                    seed=episode_seed,
                ),
                supervision=dict(
                    label_source="scripted_preference_from_visible_state",
                    permitted_use="protocol_bootstrap_sft",
                    utility_label=None,
                    rollout_validated=False,
                    behavior_probability=None,
                    note="Not an optimal-action label, real outcome, or on-policy RL sample.",
                ),
            )
