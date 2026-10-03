"""Receipt-aware execution control and explicitly non-evidentiary live telemetry."""

from __future__ import annotations

import json
import math
import os
import re
import signal
import time
from contextlib import suppress
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExperimentMonitor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str = Field(min_length=1)
    format: Literal["json", "flash"] = "json"
    value_key: str = "value"
    quantity: str = Field(default="Physical time", min_length=1, max_length=160)
    unit: str = Field(default="ns", min_length=1, max_length=40)
    target: float = Field(gt=0, allow_inf_nan=False)
    baseline: float = Field(default=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid(self):
        p = Path(self.path)
        if p.is_absolute() or ".." in p.parts or "\0" in self.path:
            raise ValueError("Monitor path must be workspace-relative and contained")
        if self.target <= self.baseline:
            raise ValueError("Monitor target must exceed its starting baseline")
        if self.format == "flash" and self.unit not in {"s", "us", "ns", "ps"}:
            raise ValueError("FLASH monitor units must be s, us, ns or ps")
        return self


def read_monitor(view, specification, elapsed):
    """Bounded mutable observations for planning; never scientific evidence."""
    m = ExperimentMonitor.model_validate(specification)
    result = dict(
        **m.model_dump(),
        observed_at=time.time(),
        elapsed_seconds=elapsed,
        authority="Mutable operational telemetry; not scientific evidence",
        available=False,
    )
    try:
        root = Path(view).resolve()
        p = (root / m.path).resolve(strict=True)
        if not p.is_relative_to(root) or not p.is_file():
            raise ValueError("Monitor file escapes its workspace")
        if m.format == "json":
            if p.stat().st_size > 65536:
                raise ValueError("Monitor JSON exceeds 64 KiB")
            data = json.loads(p.read_text())
            value = data[m.value_key]
            if type(value) not in {int, float}:
                raise ValueError("Monitor value must be numeric")
        else:
            with p.open("rb") as f:
                f.seek(max(0, p.stat().st_size - 262144))
                tail = f.read(262144).decode(errors="replace")
            number = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?"
            matches = re.findall(
                r"(?m)^\s*(\d+)\s+(" + number + r")\s+(" + number + r")\s+\(", tail
            )
            if not matches:
                raise ValueError("No FLASH step/time line in monitor tail")
            step, physical, dt = matches[-1]
            scale = {"s": 1, "us": 1e6, "ns": 1e9, "ps": 1e12}[m.unit]
            value = float(physical.replace("D", "E")) * scale
            result.update(step=int(step), timestep=float(dt.replace("D", "E")) * scale)
        if not math.isfinite(value) or value < m.baseline:
            raise ValueError("Invalid physical progress value")
        span = value - m.baseline
        estimate = elapsed * max(0, m.target - value) / span if span > 0 else None
        result.update(
            available=True,
            value=value,
            estimated_additional_seconds=estimate
            if estimate is None or math.isfinite(estimate)
            else None,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        result["error"] = str(error)[:500]
    return result


class ControlService:
    def cancel(self, experiment, *, reason):
        """Request a stop for this study's receipt; keep partial data and claim state."""
        from .execution_pool import cancel_remote
        from .mvp_launch import ProcessIdentity, process_identity_matches
        from .research_service import put

        if not isinstance(reason, str) or not 8 <= len(reason.strip()) <= 2400:
            raise ValueError("Give a concise reason for stopping this experiment")
        with self.lock():
            record = self._read("experiments", experiment)
            if record["status"] not in {"queued", "running"}:
                return record
            record.update(
                cancel_requested=True, stop_reason=reason.strip(), stop_requested_at=time.time()
            )
            put(self.root / "experiments" / (experiment + ".json"), record)
        if record.get("machine"):
            return cancel_remote(self, record)
        identity = record.get("worker_identity")
        if identity and process_identity_matches(ProcessIdentity.model_validate(identity)):
            with suppress(ProcessLookupError):
                os.killpg(identity["pid"], signal.SIGTERM)
        return self._read("experiments", experiment)

    def pending_director_replan(self):
        """A continue review cannot silently discharge a required worker response."""
        replans = [r for r in self._all("director") if r["decision"] == "replan"]
        if not replans:
            return None
        latest = max(replans, key=lambda r: r["created_at"])
        if (self.root / "director-acks" / (latest["id"] + ".json")).exists():
            return None
        return latest

    def director_status(self):
        decisions = sorted(self._all("director"), key=lambda r: r["created_at"], reverse=True)
        pending = self.pending_director_replan()
        decisions = decisions[:8]
        if pending and all(r["id"] != pending["id"] for r in decisions):
            decisions = decisions[:7] + [pending]
        for r in decisions:
            p = self.root / "director-acks" / (r["id"] + ".json")
            if p.exists():
                r["acknowledgement"] = json.loads(p.read_text())
            for action in r.get("control_actions", []):
                current = self._read("experiments", action["experiment"])
                action.update(
                    status=current["status"],
                    cancellation_confirmed=current.get("cancellation_confirmed", False),
                )
        return decisions

    def director_ack(self, decision, *, response, reason, plan=None):
        """A replan needs a recorded next-test plan or an explicit reasoned challenge."""
        from .research_service import put

        if (
            response not in {"plan", "challenge"}
            or not isinstance(reason, str)
            or not 16 <= len(reason.strip()) <= 2400
        ):
            raise ValueError("Use response='plan' or 'challenge' and a substantive reason")
        directive = self._read("director", decision)
        if directive["decision"] != "replan":
            raise ValueError("Only a replan directive needs acknowledgement")
        if response == "plan":
            if not plan:
                raise ValueError(
                    "Record lab.note(kind='next_test', ...) and pass its note_ID as plan"
                )
            note = self._read("notebook", plan)
            if note["kind"] != "next_test" or note["created_at"] < directive["created_at"]:
                raise ValueError("Plan must be a new next_test note after this director decision")
        body = dict(
            id=decision,
            response=response,
            reason=reason.strip(),
            plan=plan,
            created_at=time.time(),
            authority="Worker response; not scientific approval",
        )
        with self.lock():
            p = self.root / "director-acks" / (decision + ".json")
            p.parent.mkdir(exist_ok=True)
            if p.exists():
                return json.loads(p.read_text())
            put(p, body)
        return body

    def check_director(self, stage, purpose, timeout):
        if not self.pending_director_replan():
            return
        if stage == "exploration" and purpose == "diagnostic" and timeout <= 120:
            return
        raise ValueError(
            "Director requested a replan. Read lab.director_status(); record a "
            "next_test note and call lab.director_ack, or give a reasoned challenge."
        )
