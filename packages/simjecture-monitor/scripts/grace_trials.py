"""Mechanism check: defer coprocessor repair alerts during a ten-second grace."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import parked_trials as parked
from heartbeat_trials import HeartbeatSupervisor
from simjecture_monitor.events import put


class GraceMixin:
    def route_monitor_alerts(self):
        age = time.time() - getattr(self, "first_mismatch_at", float("-inf"))
        if getattr(self, "worker_parked", False) and age < 10:
            while (
                self.monitor_pending and self.monitor_pending[0]["action"] == "request_repair_judge"
            ):
                alert = self.monitor_pending.pop(0)
                alert["routing"] = "Host prescribed defer during ten-second contradiction grace"
                if not hasattr(self, "grace_deferrals"):
                    self.grace_deferrals = []
                self.grace_deferrals.append(
                    dict(
                        packet_sha256=alert["packet_sha256"],
                        observed_at=time.time(),
                        contradiction_age_seconds=age,
                        scope="Host action eligibility override; raw model choice remains recorded",
                    )
                )
                put(self.root / "GRACE_DEFERRALS.json", self.grace_deferrals)
            put(self.monitor_dir / "alerts.json", self.monitor_alerts)
        super().route_monitor_alerts()


class GraceEventSupervisor(GraceMixin, parked.ParkedSupervisor):
    pass


class GraceHeartbeatSupervisor(GraceMixin, HeartbeatSupervisor):
    pass


def main(*, timer=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--case", choices=["adapter"], required=True)
    parser.add_argument("--policy", choices=["model"], required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    args = parser.parse_args()
    parked.ParkedSupervisor = GraceHeartbeatSupervisor if timer else GraceEventSupervisor
    parked.run(args.root, args.case, args.policy, args.socket, args.wrapper)


if __name__ == "__main__":
    main()
