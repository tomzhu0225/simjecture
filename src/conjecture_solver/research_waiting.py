"""Durable worker waits; the campaign clock and host supervision keep running."""

from __future__ import annotations

import json
import time


class WaitingService:
    def _operator_ids(self):
        return sorted(p.stem for p in (self.root / "operator_steering/messages").glob("*.json"))

    def wait(
        self,
        reason,
        *,
        experiments=(),
        reviews=(),
        methods=(),
        reports=(),
        help_requests=(),
        helpers=(),
        for_operator=False,
    ):
        from .research_service import put

        if not isinstance(reason, str) or not 8 <= len(reason.strip()) <= 2400:
            raise ValueError("Waiting requires a concrete reason of 8 to 2400 characters")
        if type(for_operator) is not bool:
            raise ValueError("for_operator must be a boolean")
        subjects = {}
        for kind, values in (
            ("experiments", experiments),
            ("reviews", reviews),
            ("methods", methods),
            ("report_requests", reports),
            ("help_requests", help_requests),
            ("helper_tasks", helpers),
        ):
            if not isinstance(values, (list, tuple)) or len(values) > 64:
                raise ValueError("Wait subjects must be lists of at most 64 receipt IDs")
            if any(not isinstance(identifier, str) for identifier in values):
                raise ValueError("Wait subjects must contain receipt IDs, not objects or numbers")
            identifiers = list(dict.fromkeys(values))
            for identifier in identifiers:
                self._read(kind, identifier)
            if identifiers:
                subjects[kind] = identifiers
        if not subjects and not for_operator:
            raise ValueError(
                "Choose a pending receipt or for_operator=True; do not poll unchanged status"
            )
        if self.manifest["deadline"] <= time.time():
            raise ValueError("Campaign deadline reached")
        with self.lock():
            delivery = self.root / "operator_steering/delivery.json"
            delivered = json.loads(delivery.read_text()) if delivery.exists() else {}
            put(
                self.root / "worker_wait.json",
                dict(
                    status="waiting",
                    reason=reason.strip(),
                    subjects=subjects,
                    for_operator=for_operator,
                    operator_ids=sorted(delivered),
                    created_at=time.time(),
                    deadline=self.manifest["deadline"],
                    authority="Worker scheduling only; no scientific approval or deadline change",
                ),
            )
        return self.waiting_status()

    def waiting_status(self):
        from .research_service import put

        path = self.root / "worker_wait.json"
        if not path.exists():
            return dict(status="active")
        value = json.loads(path.read_text())
        if value["status"] != "waiting":
            return value
        changes = []
        for kind, identifiers in value["subjects"].items():
            for identifier in identifiers:
                record = self._read(kind, identifier)
                if record["status"] not in {"queued", "running"}:
                    changes.append(dict(kind=kind, id=identifier, status=record["status"]))
        # New steering always wakes a parked worker, irrespective of wait subjects.
        if set(self._operator_ids()) - set(value["operator_ids"]):
            changes.append(dict(kind="operator_steering", status="new_guidance"))
        if changes:
            value.update(status="woken", wake_events=changes, woken_at=time.time())
            put(path, value)
        return value

    def wake_worker(self, reason):
        from .research_service import put

        path = self.root / "worker_wait.json"
        if path.exists():
            value = json.loads(path.read_text())
            value.update(status="woken", wake_reason=reason, woken_at=time.time())
            put(path, value)
