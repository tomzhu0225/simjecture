"""Prospective attention-contract trials using native workers and a remote solver.

Reuse the retained worker lifecycle without altering historical trial sources.
The selected policy sees only public observations. Host admission and actual
dispatch are recorded separately. Knowledge support needs a separate workflow
with declared questions; these plasma trials do not test retrieval utility.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from pathlib import Path

import live_trials as live
from simjecture_monitor import attention_support as protocol
from simjecture_monitor.action_distribution import DISTRIBUTIONS, INDEPENDENT
from simjecture_monitor.attention_server import request
from simjecture_monitor.events import digest, put
from simjecture_monitor.sampling_trace import SamplingTrace
from simjecture_monitor.workflow_attention import ScientificConsistencyRules, observation


def supervisor_type(
    legacy,
    *,
    model_policy=None,
    sampling_seed=None,
    sampling_split="train",
    decision_distribution=INDEPENDENT,
):
    class ScientificSupervisor(legacy.RawSupervisor):
        def initialize(self, arm):
            super().initialize("observe")
            self.attention_arm = arm
            self.attention_model_policy = model_policy or arm
            self.attention_gate = protocol.AdmissionGate()
            self.attention_rules = ScientificConsistencyRules()
            self.attention_clock = uuid.uuid4().hex
            self.attention_seen = 0
            self.attention_next_poll = 0
            self.attention_future = None
            self.attention_packets = {}
            self.attention_count = 0
            self.attention_revision = 0
            self.attention_revision_digest = None
            self.sampling_trace = (
                SamplingTrace(
                    self.monitor_dir,
                    seed=sampling_seed,
                    split=sampling_split,
                    decision_distribution=decision_distribution,
                )
                if sampling_seed is not None
                else None
            )

        def canonical(self, raw, now):
            public = raw["state"]["host_state"]["public_artifacts"]
            # Revision binds diagnostic/configuration identity, not heartbeat timestamps.
            revision = digest(
                dict(
                    analysis_options=public.get("analysis_options"),
                    diagnostic_rows=public.get("diagnostic_rows"),
                    phase=public.get("progress", {}).get("phase"),
                    run_started=public.get("execution_plan", {}).get("started_at"),
                )
            )
            if revision != self.attention_revision_digest:
                self.attention_revision += 1
                self.attention_revision_digest = revision
            return observation(
                raw,
                subject_id="main-worker",
                operation_id="plasma-bundle",
                incident_id="diagnostic-episode",
                clock_id=self.attention_clock,
                captured_ms=round(time.monotonic() * 1000),
                sequence=self.public_sequence,
                state_revision=self.attention_revision,
                wall_time=now,
            )

        def receive(self, raw, submitted, result, directory):
            if (
                self.attention_arm in {"base", "adapted"}
                and result.get("policy") != self.attention_model_policy
            ):
                raise ValueError("Response model policy differs from the requested policy")
            now = time.time()
            current_raw = self.snapshot(directory, now)
            current = self.canonical(current_raw, now)
            view = protocol.PackedView.model_validate(result["view"])
            decision = protocol.Decision.model_validate(result["decision"])
            admission = self.attention_gate.evaluate(
                submitted, view, decision, current, now_ms=current.captured_ms
            )
            self.attention_count += 1
            path = self.monitor_dir / f"attention-{self.attention_count:05d}.json"
            record = dict(
                submitted=submitted.model_dump(),
                current=current.model_dump(),
                result=result,
                admission=admission,
                received_at=now,
            )
            put(path, record)
            if self.sampling_trace is not None:
                self.sampling_trace.record(submitted, result, decision_path=path)
            if admission["disposition"] != "admitted":
                return
            if decision.support_kind != "none":
                raise ValueError("This task declares no retrievable question")
            self.attention_packets[raw["packet_sha256"]] = submitted
            self._record_decision(
                raw,
                dict(
                    choice=decision.action,
                    packet_sha256=raw["packet_sha256"],
                    policy="scientific-attention-" + self.attention_arm,
                    evidence=decision.evidence_ids,
                    canonical_receipt=str(path.relative_to(self.root)),
                ),
                received_at=now,
            )
            self.route_monitor_alerts()

        def route_monitor_alerts(self):
            before = list(self.monitor_pending)
            super().route_monitor_alerts()
            remaining = {a["packet_sha256"] for a in self.monitor_pending}
            for alert in before:
                key = alert["packet_sha256"]
                packet = getattr(self, "attention_packets", {}).get(key)
                if packet is None or key in remaining:
                    continue
                actual = bool(
                    alert.get("help_request")
                    or self.authority_future is not None
                    or getattr(self, "_director_pending", None) is not None
                )
                if actual:
                    self.attention_gate.record_dispatch(packet)
                with (self.monitor_dir / "attention-dispatches.jsonl").open("a") as stream:
                    stream.write(
                        json.dumps(dict(packet_id=packet.packet_id, dispatched=actual, alert=alert))
                        + "\n"
                    )

        def monitor_tick(self, directory):
            # Retain explicit help/repair processing and the fixed wait fallback.
            super().monitor_tick(directory)
            if self.attention_future is not None and self.attention_future[0].done():
                future, raw, packet = self.attention_future
                self.attention_future = None
                try:
                    self.receive(raw, packet, future.result(), directory)
                except Exception as error:
                    with (self.monitor_dir / "attention-errors.jsonl").open("a") as stream:
                        stream.write(
                            json.dumps(dict(packet_id=packet.packet_id, error=str(error))) + "\n"
                        )
            now = time.monotonic()
            if now < self.attention_next_poll or self.monitor_latest is None:
                return
            self.attention_next_poll = now + 5
            self.attention_seen = self.public_sequence
            raw = self.monitor_latest
            host = raw["state"]["host_state"]
            if (
                self.attention_future is not None
                or not self.worker_parked
                or self.discretionary_used
                or host["telemetry"]["workflow_complete"]
                or any(
                    host[k]
                    for k in [
                        "authority_active",
                        "director_active",
                        "pending_explicit_help",
                        "active_helpers",
                    ]
                )
            ):
                return
            packet = self.canonical(raw, time.time())
            if self.attention_arm in {"base", "adapted"}:
                payload = dict(
                    observation=packet.model_dump(),
                    policy=self.attention_model_policy,
                    distribution=decision_distribution,
                )
                if self.sampling_trace is not None:
                    payload.update(
                        self.sampling_trace.request(packet, policy=self.attention_model_policy)
                    )
                if os.environ.get("SIMJECTURE_ATTENTION_TOKEN_FILE"):
                    payload["auth_token"] = (
                        Path(os.environ["SIMJECTURE_ATTENTION_TOKEN_FILE"]).read_text().strip()
                    )
                self.attention_future = (
                    self.monitor_executor.submit(
                        request,
                        self.monitor_socket,
                        payload,
                        timeout=25,
                    ),
                    raw,
                    packet,
                )
            else:
                view = protocol.pack(
                    packet, len, token_counter_id="reference:characters", budget_tokens=100000
                )
                choice = (
                    self.attention_rules.predict(packet, view)
                    if self.attention_arm == "rules"
                    else protocol.Choice(
                        action="observe",
                        support_kind="none",
                        question_ref=None,
                        basis="unspecified",
                        evidence=[],
                    )
                )
                decision = protocol.bind_choice(packet, view, choice, policy_id=self.attention_arm)
                self.receive(
                    raw,
                    packet,
                    dict(view=view.model_dump(), decision=decision.model_dump()),
                    directory,
                )

        def close_monitor(self):
            if self.attention_future is not None:
                future, _, _ = self.attention_future
                future.cancel()
                # A completed trial cannot admit delayed expert requests.
                self.attention_future = None
            super().close_monitor()
            if self.sampling_trace is not None:
                self.sampling_trace.close()

    return ScientificSupervisor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--arm", choices=["observe", "rules", "base", "adapted"], required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--plasma-assets", type=Path, required=True)
    parser.add_argument("--model-policy", help="Explicit named adapter for a model arm")
    parser.add_argument(
        "--sampling-seed", type=int, help="Log categorical decisions for a training episode"
    )
    parser.add_argument("--sampling-split", choices=["train", "commissioning"], default="train")
    parser.add_argument("--decision-distribution", choices=DISTRIBUTIONS, default=INDEPENDENT)
    args = parser.parse_args()
    if args.model_policy and args.arm not in {"base", "adapted"}:
        parser.error("--model-policy requires a model arm")
    if args.sampling_seed is not None and args.arm not in {"base", "adapted"}:
        parser.error("--sampling-seed requires a model arm")
    live.PYTHON = args.python
    live.SCRIPTS = live.SOLVER = args.plasma_assets
    # Task text captures paths at import time, after configuring this new backend.
    import generalization_trials as legacy

    legacy.RawSupervisor = supervisor_type(
        legacy,
        model_policy=args.model_policy,
        sampling_seed=args.sampling_seed,
        decision_distribution=args.decision_distribution,
        sampling_split=args.sampling_split,
    )
    legacy.run(args.root, args.family, args.arm, args.seed, args.socket, args.wrapper)


if __name__ == "__main__":
    main()
