"""Receipt-backed advisory targets and empirical cost estimates.

Metric definitions, units, baselines and targets are researcher declarations.
Artifact identity and values are checked by the host. None of this approves a
scientific claim, changes a deadline, or prescribes an experiment schedule.
"""

from __future__ import annotations

import math
import time

from pydantic import BaseModel, ConfigDict, Field


class ProgressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    experiment: str = Field(pattern=r"^exp_[a-z0-9_-]+$")
    output: str = Field(min_length=1)
    path: str = Field(min_length=1)
    quantity: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=80)
    target: float = Field(allow_inf_nan=False)
    baseline: float = Field(default=0, allow_inf_nan=False)
    estimate_rate: bool = False
    series: str = Field(default="", max_length=160)
    limitations: list[str] = Field(default_factory=list, max_length=16)


class ProgressService:
    def progress(self, **kwargs):
        """Record a target observation from a successful, hash-verified JSON output."""
        from .research_service import fingerprint, put

        body = ProgressRequest.model_validate(kwargs).model_dump(mode="json")
        if any(not x or len(x) > 1200 for x in body["limitations"]):
            raise ValueError("Progress limitations must be nonempty and ≤1200 characters")
        record = self._read("experiments", body["experiment"])
        cell = self.compare([body["experiment"]], {"value": [body["output"], body["path"]]})[
            "rows"
        ][0]["metrics"]["value"]
        value = cell["value"]
        if cell["status"] != "available" or type(value) not in {int, float}:
            raise ValueError("Progress requires a finite numeric value from a recorded JSON output")
        body.update(
            value=value,
            artifact_sha256=cell["sha256"],
            measured_wall_seconds=record.get("execution", {}).get("wall_seconds"),
            machine=record.get("machine", "local"),
            capability=record["binding"].get("capability"),
            authority="Verified receipt value; scientific meaning and target are unreviewed",
        )
        if body["estimate_rate"] and body["target"] <= body["baseline"]:
            raise ValueError("A throughput target must be greater than its declared baseline")
        identifier = "progress_" + fingerprint(body)[:24]
        with self.lock():
            directory = self.root / "progress"
            directory.mkdir(exist_ok=True)
            p = directory / (identifier + ".json")
            if not p.exists():
                put(p, dict(id=identifier, created_at=time.time(), **body))
        return self._read("progress", identifier)

    def progress_summary(self, remaining_seconds):
        """Latest observation per explicitly named series; no cross-series pooling."""
        latest = {}
        for record in sorted(self._all("progress"), key=lambda r: (r["created_at"], r["id"])):
            key = (record["series"] or record["quantity"], record["unit"], record["target"])
            latest[key] = record
        rows = []
        for r in latest.values():
            try:
                cell = self.compare([r["experiment"]], {"value": [r["output"], r["path"]]})["rows"][
                    0
                ]["metrics"]["value"]
            except (ValueError, FileNotFoundError) as error:
                cell = {"reason": str(error)}
            valid = cell.get("sha256") == r["artifact_sha256"] and cell.get("value") == r["value"]
            wall = r.get("measured_wall_seconds")
            span = r["value"] - r["baseline"]
            gap = max(0, r["target"] - r["value"])
            estimate = None
            if (
                valid
                and r["estimate_rate"]
                and span > 0
                and type(wall) in {int, float}
                and wall > 0
            ):
                proposed = wall * gap / span
                if math.isfinite(proposed):
                    estimate = proposed
            rows.append(
                dict(
                    **r,
                    integrity="verified" if valid else "invalid",
                    integrity_error=None if valid else cell.get("reason", "Recorded value changed"),
                    target_reached=valid and r["value"] >= r["target"],
                    estimated_additional_seconds=estimate,
                    exceeds_remaining_budget=estimate is not None and estimate > remaining_seconds,
                    estimate_note="Linear extrapolation from this experiment only, "
                    "assuming similar throughput; excludes analysis/review and may fail "
                    "as physics or resolution changes.",
                )
            )
        return rows[-32:]
