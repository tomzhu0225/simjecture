"""Operator budget changes and agent requests; neither grants scientific acceptance."""

from __future__ import annotations

import json
import math
import time
import uuid
from datetime import UTC, datetime
from getpass import getuser
from pathlib import Path

TERMINAL = {"completed", "cancelled", "budget_exhausted"}


def _read(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {}


def _hours(value):
    if type(value) not in {int, float} or not 0 < value < 1e100 or not math.isfinite(value):
        raise ValueError("Additional hours must be a positive finite number")
    return value * 3600


def _text(value, name, limit, *, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError(f"Provide {name} as text of at most {limit} characters")
    return value.strip()


def budget_status(root, *, manifest=None, experiments=None):
    """A fresh clock for operator interfaces and external watchdogs."""
    from .study_status import supervisor_directory

    root = Path(root)
    manifest = manifest if manifest is not None else _read(root / "research.json")
    state = _read(supervisor_directory(root) / "state.json")
    deadline = manifest.get("deadline")
    now = time.time()
    events = manifest.get("budget_extensions", [])
    requests = sorted(
        (_read(p) for p in (root / "budget_requests").glob("*.json")),
        key=lambda r: r["created_at"],
    )
    granted = {e.get("request_id") for e in events if e.get("request_id")}
    for request in requests:
        request["status"] = "granted" if request["id"] in granted else "pending"
    if experiments is None:
        experiments = [_read(p) for p in (root / "experiments").glob("*.json")]
    return dict(
        supported=bool(manifest),
        can_extend=bool(
            deadline and deadline > now and state.get("status") not in TERMINAL
            and not manifest.get("hosted_runtime_policy", {}).get("unbounded")
        ),
        deadline=deadline,
        compute_deadline=manifest.get("finalization_policy", {}).get("compute_deadline", deadline),
        remaining_seconds=max(0, deadline - now) if deadline is not None else 0,
        total_seconds=deadline - manifest.get("created_at", deadline) if deadline else 0,
        original_deadline=manifest.get("original_deadline", events[0].get("previous_deadline")
                                       if events else deadline),
        revision=len(events),
        extensions=events,
        requests=requests[-8:],
        experiment_limits=[
            {k: e.get(k) for k in ("id", "timeout", "execution_deadline", "started_at")}
            for e in experiments if e.get("status") in {"queued", "running"}
        ],
        scope="Extra campaign time does not change individual experiment limits or evidence rules.",
    )


def extend_budget(
    root, *, hours, key, reason="", request_id=None, actor=None, expected_deadline=None
):
    """Explicit operator operation. Not exposed on the worker's Lab API."""
    from .research_service import ResearchService, put
    from .study_status import supervisor_directory

    seconds = _hours(hours)
    key = _text(key, "a request key", 120, required=True)
    reason = _text(reason, "a reason", 2400)
    actor = _text(
        "operator:" + getuser() if actor is None else actor,
        "the operator identity", 160, required=True,
    )
    if request_id is not None:
        request_id = _text(request_id, "a time-request ID", 120, required=True)
    if not (Path(root) / "research.json").is_file():
        raise ValueError("Live budget extensions require an existing minimal study")
    service = ResearchService(root)
    with service.lock():
        manifest = service.manifest
        events = manifest.get("budget_extensions", [])
        for event in events:
            if event.get("request_key") == key:
                if (event["additional_seconds"] != seconds or event.get("reason", "") != reason
                        or event.get("request_id") != request_id):
                    raise ValueError("Request key already used for a different budget extension")
                return event
        now = time.time()
        state = _read(supervisor_directory(service.root) / "state.json")
        if manifest["deadline"] <= now or state.get("status") in TERMINAL:
            raise ValueError("This study has ended; use Continue investigation with a new budget")
        if expected_deadline is not None and expected_deadline != manifest["deadline"]:
            raise ValueError(
                "The budget changed. Reopen Extend time to review the current deadline"
            )
        if manifest.get("hosted_runtime_policy", {}).get("unbounded"):
            raise ValueError("This study already has unlimited hosted time")
        deadline = manifest["deadline"] + seconds
        if deadline <= manifest["deadline"]:
            raise ValueError("Additional hours are too small to change the deadline")
        try:
            datetime.fromtimestamp(deadline, UTC)
        except (ValueError, OverflowError, OSError) as error:
            raise ValueError("The resulting deadline is outside the supported calendar") from error
        if request_id is not None:
            requests = {r["id"]: r for r in service._all("budget_requests")}
            if request_id not in requests:
                raise ValueError("Choose an existing time request")
            if any(e.get("request_id") == request_id for e in events):
                raise ValueError("This time request has already been granted")
        previous = manifest["deadline"]
        reserve = previous - manifest.get("finalization_policy", {}).get(
            "compute_deadline", previous
        )
        event = dict(
            id="extension_" + uuid.uuid4().hex, request_key=key, created_at=now,
            actor=actor, reason=reason, additional_seconds=seconds,
            previous_deadline=previous, new_deadline=deadline,
            request_id=request_id,
            scope="Operator budget authorization only; existing experiment limits are unchanged.",
        )
        manifest.setdefault("original_deadline", previous)
        manifest["deadline"] = deadline
        if "finalization_policy" in manifest:
            manifest["finalization_policy"]["compute_deadline"] = deadline - reserve
        manifest["budget_extensions"] = [*events, event]
        put(service.root / "research.json", manifest)
    return event


class BudgetRequests:
    def request_time(self, *, hours, reason, key=None, requested_by="worker"):
        """Ask the operator for time; never changes or renews the deadline."""
        from .research_service import put

        _hours(hours)
        reason = _text(reason, "a reason", 2400, required=True)
        if key is not None:
            key = _text(key, "a request key", 120, required=True)
        if requested_by not in {"worker", "director"}:
            raise ValueError("Unknown time-request role")
        with self.lock():
            if not budget_status(self.root, manifest=self.manifest)["can_extend"]:
                raise ValueError("This study has ended; prepare a continuation")
            for request in self._all("budget_requests"):
                if key and request.get("request_key") == key:
                    if request["hours"] != hours or request["reason"] != reason:
                        raise ValueError("Request key already used for a different time request")
                    return request
            record = dict(
                id="time_" + uuid.uuid4().hex, created_at=time.time(), hours=hours,
                reason=reason, requested_by=requested_by, request_key=key,
                authority="Request only; the operator must authorize any additional budget.",
            )
            (self.root / "budget_requests").mkdir(exist_ok=True)
            put(self.root / "budget_requests" / (record["id"] + ".json"), record)
        return record
