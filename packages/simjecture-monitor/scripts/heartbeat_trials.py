"""Experimental bounded time observations while a scientific worker is parked."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import parked_trials as parked
from simjecture_monitor.events import digest


class ParkingClock:
    """Coarse elapsed-time evidence; no incident oracle or action recommendation."""

    def __init__(self, interval=15):
        if interval <= 0:
            raise ValueError("A positive interval is required")
        self.interval = interval
        self.started = self.last = None
        self.sequence = 0

    def observe(self, *, is_parked, now):
        if not is_parked:
            self.started = self.last = None
            return None
        if self.started is None:
            self.started = self.last = now
            return None
        if now - self.last < self.interval:
            return None
        self.last = now
        self.sequence += 1
        return dict(sequence=self.sequence, parked_seconds=round(now - self.started, 2))


class HeartbeatSupervisor(parked.ParkedSupervisor):
    def monitor_tick(self, directory):
        path = Path(directory) / "response.json"
        if str(path) not in self.monitor_streams:
            self.monitor_streams[str(path)] = parked.CompletionStream(
                path,
                subject=Path(directory).name,
                maximum=8,
                work=self.service.work,
                parked=lambda: getattr(self, "worker_parked", False),
            )
        if not hasattr(self, "parking_clock"):
            self.parking_clock = ParkingClock()
        now = time.time()
        observation = self.parking_clock.observe(
            is_parked=getattr(self, "worker_parked", False), now=now
        )
        if observation is not None and self.authority_future is None:
            body = dict(
                type="command_execution",
                command="Host timed asynchronous state observation",
                exit_code=None,
                provenance="host public clock and process/adapter probe",
                aggregated_output=json.dumps(
                    dict(
                        **observation,
                        completion=parked.statuses(self.service.work),
                        worker_parked=True,
                    )
                ),
            )
            self.monitor_streams[str(path)].inject(
                dict(
                    id="parking-clock:" + str(observation["sequence"]),
                    observed_at=now,
                    subject="worker",
                    body=body,
                    source_sha256=digest(body),
                )
            )
        super().monitor_tick(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--case", choices=["healthy", "adapter"], required=True)
    parser.add_argument("--policy", choices=["model"], required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    args = parser.parse_args()
    parked.ParkedSupervisor = HeartbeatSupervisor
    parked.run(args.root, args.case, args.policy, args.socket, args.wrapper)


if __name__ == "__main__":
    main()
