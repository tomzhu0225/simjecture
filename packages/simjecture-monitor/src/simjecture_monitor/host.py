"Experimental stream-to-director integration using the production helper workflow."

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from conjecture_solver.research_service import put as service_put
from conjecture_solver.research_supervisor import ResearchSupervisor

from .events import DiagnosticStream, PublicStream, digest, put
from .policy import AlertGate, PeriodicPolicy, RulesPolicy
from .server import request


class MonitorSupervisor(ResearchSupervisor):
    def __init__(self, args, *, policy, task, model_socket=None, cadence=60):
        super().__init__(args)
        self.repair_authority = None
        self.authority_executor = ThreadPoolExecutor(max_workers=1)
        self.authority_future = None
        self.monitor_policy = policy
        self.monitor_task = task
        self.monitor_socket = model_socket
        self.monitor_streams = {}
        self.diagnostic_streams = {}
        self.monitor_gate = AlertGate(cooldown=cadence)
        self.monitor_executor = ThreadPoolExecutor(max_workers=1)
        self.monitor_future = None
        self.monitor_latest = None
        self.monitor_submitted = set()
        self.monitor_alerts = []
        self.explicit_repairs = set()
        self.monitor_pending = []
        self.monitor_sequence = 0
        self.monitor_baseline = PeriodicPolicy(cadence) if policy == "periodic" else RulesPolicy()
        self.monitor_dir = self.root / "monitor"
        self.monitor_dir.mkdir()
        self.monitor_cadence = cadence
        self._monitor_tick = 0

    def prompt(self):
        text = super().prompt()
        outcomes = self.state.get("monitor_authority_results", [])
        if outcomes:
            summaries = [
                {
                    "stage": r["stage"],
                    "verdict": r.get("verdict"),
                    "deployment": r.get("deployment"),
                    "error": r.get("error"),
                }
                for r in outcomes[-3:]
            ]
            text += (
                "\nIndependent harness authority outcomes. Inspect returned repairs "
                "and rerun the affected operation before updating your report:\n"
                + json.dumps(summaries)
            )
        return text

    def director_packet(self):
        packet = super().director_packet()
        packet["monitor_alerts"] = self.monitor_alerts[-4:]
        return packet

    def director_prompt(self, packet):
        text = super().director_prompt(packet)
        if packet.get("monitor_alerts"):
            text += (
                "\nAn experimental monitor raised these unreviewed observation"
                "s. Inspect the evidence; an alert may be unnecessary or mist"
                "aken. You may continue without intervention. For assistance "
                "requests, use the normal helper workflow. Suspected harness "
                "defects require a separate authority judge; this alert gives"
                " you no code-modification permission.\n"
            ) + json.dumps(packet["monitor_alerts"])
        return text

    def _record_decision(self, packet, decision, *, received_at, error=None):
        self.monitor_sequence += 1
        record = dict(packet=packet, decision=decision, received_at=received_at, error=error)
        if decision:
            alert = self.monitor_gate.accept(packet, decision, now=received_at)
            if alert:
                alert["recent_events"] = packet["state"]["events"][-6:]
                self.monitor_alerts.append(alert)
                self.monitor_pending.append(alert)
                record["alert"] = alert
        put(self.monitor_dir / f"decision-{self.monitor_sequence:05d}.json", record)

    def monitor_tick(self, directory):
        now = time.time()
        if now < self._monitor_tick:
            return
        self._monitor_tick = now + 1
        path = Path(directory) / "response.json"
        stream = self.monitor_streams.setdefault(
            str(path), PublicStream(path, subject=Path(directory).name, maximum=8)
        )
        new = stream.poll(now=now)
        for output in sorted(self.service.work.glob("runs/*/run.log")):
            reader = self.diagnostic_streams.setdefault(
                str(output),
                DiagnosticStream(output, subject=str(output.relative_to(self.service.work))),
            )
            observations = reader.poll(now=now)
            new.extend(observations)
            stream.events.extend(observations)
        if new:
            with (self.monitor_dir / "events.jsonl").open("a") as log:
                for event in new:
                    log.write(json.dumps(event) + "\n")
        if not stream.events:
            return
        state = dict(
            worker_wait=self.service.waiting_status().get("status"),
            pending_explicit_help=len(self.service.pending_help()),
            active_helpers=sum(
                t["status"] in {"queued", "running"} for t in self.service._all("helper_tasks")
            ),
            remaining_seconds=max(0, self.state["deadline"] - now),
        )
        packet = stream.packet(self.monitor_task, host_state=state)
        # Elapsed time is context, not a reason to infer repeatedly on unchanged events.
        signature = digest([r["source_sha256"] for r in packet["state"]["events"]])
        self.monitor_latest = packet
        explicit = self.service.work / "REPAIR_REQUEST.json"
        if explicit.is_file() and self.repair_authority is not None:
            try:
                evidence = json.loads(explicit.read_text())
                signature_repair = digest(evidence)
                if signature_repair not in self.explicit_repairs and self.authority_future is None:
                    from .repair_roles import adjudicate

                    alert = dict(
                        origin="worker",
                        request=evidence,
                        packet_sha256=signature_repair,
                        recent_events=packet["state"]["events"][-6:],
                    )
                    directory = self.root / "monitor_authority" / signature_repair
                    self.authority_future = self.authority_executor.submit(
                        adjudicate, self.args, self.repair_authority, alert, directory
                    )
                    self.explicit_repairs.add(signature_repair)
            except (ValueError, OSError):
                pass  # Wait for a complete worker-written request.
        if self.authority_future is not None and self.authority_future.done():
            outcome = self.authority_future.result()
            self.state.setdefault("monitor_authority_results", []).append(outcome)
            self.service.wake_worker("Independent harness diagnosis returned")
            self.authority_future = None
        if self.monitor_future is not None and self.monitor_future[0].done():
            future, submitted, sent_at = self.monitor_future
            self.monitor_future = None
            try:
                decision = future.result()
                if now - sent_at > 30:
                    raise ValueError("Monitor response exceeded the freshness allowance")
                # Bind the response to its exact observed packet; later events remain queued.
                self._record_decision(submitted, decision, received_at=now)
            except Exception as error:
                self._record_decision(submitted, None, received_at=now, error=str(error))
        if self.monitor_policy == "model":
            if self.monitor_future is None and signature not in self.monitor_submitted:
                self.monitor_submitted.add(signature)
                self.monitor_future = (
                    self.monitor_executor.submit(request, self.monitor_socket, packet),
                    packet,
                    now,
                )
        elif new or self.monitor_policy == "periodic":
            self._record_decision(packet, self.monitor_baseline.predict(packet), received_at=now)
        self.route_monitor_alerts()

    def route_monitor_alerts(self):
        if not self.monitor_pending or self.boundary():
            return
        alert = self.monitor_pending[0]
        if alert["action"] == "request_worker_help":
            if not any(
                r["status"] in {"queued", "running"} for r in self.service._all("help_requests")
            ):
                evidence_path = "monitor_context/" + alert["packet_sha256"] + ".json"
                put(self.service.work / evidence_path, alert)
                request_record = self.service.request_help(
                    (
                        "A monitoring coprocessor observed a possible unreported bloc"
                        "ker. Verify whether assistance would help and arrange a boun"
                        "ded helper task if warranted."
                    ),
                    success_criteria=(
                        "Inspect the recent attempts, identify any actual blocker and"
                        " return tested help or explain why no intervention is needed"
                        "."
                    ),
                    context=(
                        "Automatically inferred assistance request; the worker did no"
                        "t necessarily request it. The attached observations are unre"
                        "viewed."
                    ),
                    files=[evidence_path],
                    key="monitor-" + alert["packet_sha256"],
                )
                with self.service.lock():
                    request_record.update(
                        origin="coprocessor", monitor_packet_sha256=alert["packet_sha256"]
                    )
                    service_put(
                        self.root / "help_requests" / (request_record["id"] + ".json"),
                        request_record,
                    )
                alert["help_request"] = request_record["id"]
            else:
                alert["routing"] = "existing assistance already active"
        elif alert["action"] == "request_repair_judge":
            if self.repair_authority is not None and self.authority_future is None:
                from .repair_roles import adjudicate

                directory = self.root / "monitor_authority" / alert["packet_sha256"]
                self.authority_future = self.authority_executor.submit(
                    adjudicate, self.args, self.repair_authority, alert, directory
                )
                alert["routing"] = "independent repair-authority judge dispatched"
            else:
                put(
                    self.monitor_dir / ("authority-request-" + alert["packet_sha256"] + ".json"),
                    alert,
                )
                alert["routing"] = "authority request retained; no extra repair grant issued"
            self.monitor_pending.pop(0)
            put(self.monitor_dir / "alerts.json", self.monitor_alerts)
            return
        if getattr(self, "_director_pending", None) is None:
            self.run_director(force=True, background=True)
            if getattr(self, "_director_pending", None) is None:
                return  # Provider backoff: preserve this alert for retry.
        self.monitor_pending.pop(0)
        put(self.monitor_dir / "alerts.json", self.monitor_alerts)

    def supervise_worker(self, directory):
        super().supervise_worker(directory)
        self.monitor_tick(directory)

    def close_monitor(self):
        if self.monitor_future is not None:
            future, packet, _ = self.monitor_future
            try:
                self._record_decision(packet, future.result(timeout=35), received_at=time.time())
            except Exception as error:
                self._record_decision(packet, None, received_at=time.time(), error=str(error))
            self.monitor_future = None
        self.monitor_executor.shutdown(wait=True, cancel_futures=True)
        if self.authority_future is not None:
            self.state.setdefault("monitor_authority_results", []).append(
                self.authority_future.result(timeout=310)
            )
        self.authority_executor.shutdown(wait=True, cancel_futures=True)
