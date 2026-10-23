"""Supervisor integration for asynchronous temporary workers."""

from __future__ import annotations

import os
import signal
import time
from contextlib import suppress
from pathlib import Path

from .research_helper_runtime import owned_alive, stop_native
from .research_helpers import ACTIVE
from .research_limits import operating_limits


class HelperSupervision:
    def process_helpers(self, *, dispatch=True):
        if not (self.root / "help_requests").is_dir():
            return
        now = time.time()
        if dispatch and now < getattr(self, "_next_helper_poll", 0):
            return
        self._next_helper_poll = now + 2
        options = {
            "backend": getattr(self.args, "backend", "codex"),
            "model": self.args.model,
            "parent_control": str(self.directory / "control.json"),
        }
        for name in ("executable", "provider_config", "reasoning_effort"):
            value = getattr(self.args, name, None)
            if value is not None:
                options[name] = str(value) if isinstance(value, Path) else value
        if dispatch:
            self.service.dispatch_helpers(
                options, maximum=operating_limits(self.root)["helper_workers"] or 2
            )
        snapshot = self.service.help_status()
        collected = set(self.state.get("helper_usage_collected", []))
        changed = False
        for task in snapshot["tasks"]:
            if task["status"] in ACTIVE or task["id"] in collected:
                continue
            usage = task.get("usage", {})
            for thread, counts in usage.get("usage_by_thread", {}).items():
                key = task["id"] + ":" + thread
                self.state.setdefault("usage_by_thread", {})[key] = counts
                self.state.setdefault("usage_roles_by_thread", {})[key] = "helper"
            for thread in usage.get("usage_unreported_threads", {}):
                self.state.setdefault("usage_unreported_threads", {})[task["id"] + ":" + thread] = (
                    "helper"
                )
            self.state["usage_unidentified_calls"] = self.state.get(
                "usage_unidentified_calls", 0
            ) + usage.get("usage_unidentified_calls", 0)
            self.state["usage_incomplete_turns"] = self.state.get(
                "usage_incomplete_turns", 0
            ) + usage.get("usage_incomplete_turns", 0)
            collected.add(task["id"])
            changed = True
            self.event("helper_finished", task=task["id"], status=task["status"])
        notified = set(self.state.get("helper_feedback_notified", []))
        for request in snapshot["requests"]:
            if request["status"] == "resolved" and request["id"] not in notified:
                self.state.pop("waiting_for", None)
                self.service.wake_worker("Help response ready: " + request["id"])
                pending = self.state.setdefault("helper_feedback_pending", [])
                if request["id"] not in pending:
                    pending.append(request["id"])
                notified.add(request["id"])
                changed = True
        if changed:
            self.state.update(
                helper_usage_collected=sorted(collected),
                helper_feedback_notified=sorted(notified),
                usage_updated_at=time.time(),
            )
            self.save()

    def helper_feedback(self):
        requests = sorted(self.service._all("help_requests"), key=lambda r: r["created_at"])
        pending = set(self.state.get("helper_feedback_pending", []))
        resolved = [r for r in requests if r["status"] not in ACTIVE]
        recent = {r["id"] for r in resolved[-4:]}
        selected = [r for r in requests if r["status"] in ACTIVE or r["id"] in pending | recent]
        return [self.service.help_status(r["id"]) for r in selected]

    def stop_helpers(self):
        """Finish bounded cleanup and usage collection before the final parent save."""
        self.service.cancel_helpers("Research supervisor stopped")
        until = time.monotonic() + 8
        while time.monotonic() < until:
            snapshot = self.service.help_status()
            if not any(task["status"] in ACTIVE for task in snapshot["tasks"]):
                break
            time.sleep(0.05)
        for task in self.service._all("helper_tasks"):
            if task["status"] not in ACTIVE:
                continue
            identity = task.get("process_identity")
            if owned_alive(identity):
                with suppress(ProcessLookupError):
                    os.kill(identity["pid"], signal.SIGKILL)
            stop_native(self.root / "helpers" / task["id"])
        until = time.monotonic() + 2
        while time.monotonic() < until:
            self.service.reconcile_helpers()
            if not any(task["status"] in ACTIVE for task in self.service._all("helper_tasks")):
                break
            time.sleep(0.05)
        self.process_helpers(dispatch=False)
