"""Recorded operating settings; never changes scientific or operator budgets."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class OperatingLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    worker_action_limit: int | None = Field(default=None, gt=0)
    worker_checkpoint_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    review_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)


def operating_limits(root):
    path = Path(root) / "operating_limits.json"
    body = json.loads(path.read_text()) if path.exists() else {}
    return OperatingLimits.model_validate(body.get("limits", {})).model_dump()


def configure_limits(root, values, *, actor="operator", reason):
    from .research_service import ResearchService, fingerprint, put

    if not isinstance(values, dict) or not values:
        raise ValueError("Supply operating settings to change")
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 2400:
        raise ValueError("Give a concrete reason of at most 2400 characters")
    service = ResearchService(root)
    with service.lock():
        before = operating_limits(service.root)
        after = OperatingLimits.model_validate(before | values).model_dump()
        if before == after:
            return dict(limits=after, changed=False)
        record = dict(
            before=before,
            limits=after,
            actor=actor,
            reason=reason.strip(),
            created_at=time.time(),
            authority="Operating settings only; budgets unchanged",
        )
        directory = service.root / "operating_limit_changes"
        directory.mkdir(exist_ok=True)
        put(directory / (fingerprint(record) + ".json"), record)
        put(service.root / "operating_limits.json", record)
    return dict(limits=after, changed=True)
