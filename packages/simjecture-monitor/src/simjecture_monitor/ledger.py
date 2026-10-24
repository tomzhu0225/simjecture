"""Host-owned incident and feedback receipts for bounded continuation studies.

This ledger records operational facts. A dispatched helper or an acknowledgment
does not establish that an intervention was scientifically useful.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from .events import digest, put


class IncidentLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.data = (
            json.loads(self.path.read_text())
            if self.path.exists()
            else dict(schema=1, incidents={}, dispatches=[], feedback=[])
        )

    def save(self):
        put(self.path, self.data)

    def observe(self, component, mechanism, evidence, *, now=None):
        """Stable identity across text/path changes; explicit resolution is needed."""
        now = time.time() if now is None else now
        key = digest(dict(component=component, mechanism=mechanism))
        rows = self.data["incidents"]
        row = rows.get(key)
        if row is None:
            row = rows[key] = dict(
                id=key,
                component=component,
                mechanism=mechanism,
                generation=1,
                status="active",
                opened_at=now,
                history=[],
                evidence=[],
            )
        elif row["status"] == "resolved":
            row["generation"] += 1
            row.update(status="active", opened_at=now)
            row["history"].append(dict(kind="reopened", at=now))
        evidence_hash = digest(evidence)
        if evidence_hash not in row["evidence"]:
            row["evidence"].append(evidence_hash)
        row["last_observed_at"] = now
        self.save()
        return row

    def resolve(self, incident, receipt, *, now=None):
        row = self.data["incidents"][incident]
        row.update(
            status="resolved",
            resolution_sha256=digest(receipt),
            resolved_at=time.time() if now is None else now,
        )
        row["history"].append(dict(kind="resolved", at=time.time() if now is None else now))
        self.save()

    def dispatch(self, incident, action, *, execution_receipt, redundant=False):
        """Call only after actual native execution is identified, never for a proposal."""
        row = self.data["incidents"][incident]
        if not execution_receipt:
            raise ValueError("Executed dispatch requires an execution receipt")
        receipt_hash = digest(execution_receipt)
        for prior in self.data["dispatches"]:
            if prior["execution_sha256"] == receipt_hash:
                return prior
        dispatch = dict(
            id="dispatch-" + uuid.uuid4().hex,
            incident=incident,
            generation=row["generation"],
            action=action,
            execution_sha256=receipt_hash,
            redundant=bool(redundant),
            at=time.time(),
        )
        self.data["dispatches"].append(dispatch)
        self.save()
        return dispatch

    def feedback(self, identifier, result, *, required, reason):
        """Availability is separate from delivery and acknowledgment."""
        result_hash = digest(result)
        for row in self.data["feedback"]:
            if row["id"] == identifier:
                if row["result_sha256"] != result_hash:
                    raise ValueError("Feedback identity cannot change content")
                return row
        row = dict(
            id=identifier,
            result_sha256=result_hash,
            result=result,
            required=bool(required),
            requirement_reason=reason,
            available_at=time.time(),
            delivered_at=None,
            acknowledgment=None,
        )
        self.data["feedback"].append(row)
        self.save()
        return row

    def deliver(self, work):
        rows = self.data["feedback"]
        if not rows:
            return
        put(Path(work) / "FEEDBACK.json", dict(items=rows))
        for row in rows:
            if row["delivered_at"] is None:
                row["delivered_at"] = time.time()
        self.save()

    def acknowledge(self, path):
        if not Path(path).is_file():
            return []
        acknowledgments = json.loads(Path(path).read_text())
        if not isinstance(acknowledgments, list):
            raise ValueError("Feedback acknowledgment must be a list")
        known = {r["id"]: r for r in self.data["feedback"]}
        accepted = []
        for ack in acknowledgments:
            row = known.get(ack.get("id"))
            if (
                row is None
                or row["delivered_at"] is None
                or ack.get("result_sha256") != row["result_sha256"]
                or ack.get("disposition") not in {"used", "no_change", "challenged"}
                or len(str(ack.get("explanation", "")).strip()) < 16
            ):
                continue
            row["acknowledgment"] = dict(**ack, observed_at=time.time())
            accepted.append(row["id"])
        self.save()
        return accepted

    def measurements(self):
        return dict(
            required_feedback_misses=sum(
                r["required"] and r["acknowledgment"] is None for r in self.data["feedback"]
            ),
            duplicate_wakeups=sum(r["redundant"] for r in self.data["dispatches"]),
            available_feedback=len(self.data["feedback"]),
            acknowledged_feedback=sum(
                r["acknowledgment"] is not None for r in self.data["feedback"]
            ),
        )
