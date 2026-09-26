"""Optional evidence-linked memory and bounded recovery context for minimal studies.

Worker notes are not adjudications. Host receipts and immutable claim requirements
remain authoritative; the notebook records interpretation without promoting it to fact.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .evidence_paths import evidence_value
from .research_audit import strict_json


class ResearchNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1, max_length=2400)
    kind: Literal["observation", "interpretation", "question", "next_test", "implementation"]
    experiments: list[str] = Field(default_factory=list, max_length=32)
    sources: list[str] = Field(default_factory=list, max_length=8)
    claim: str = "root"
    supersedes: str | None = None
    alternatives: dict[str, str] = Field(default_factory=dict, max_length=8)
    estimated_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)


def shorten(value, length=400):
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= length else text[:length] + "… [abridged]"


class NotebookService:
    def note(self, statement, *, kind="observation", **kwargs):
        """Append a research note; corrections supersede rather than erase history."""
        from .research_service import fingerprint, put

        body = ResearchNote(statement=statement, kind=kind, **kwargs).model_dump(mode="json")
        if not statement.strip():
            raise ValueError("Note statement cannot be blank")
        if any(len(x) > 2000 for x in body["sources"]):
            raise ValueError("Source references must be compact citations or URLs")
        if any(
            not k.strip() or not v.strip() or len(k) > 200 or len(v) > 1200
            for k, v in body["alternatives"].items()
        ):
            raise ValueError("Alternatives require compact labels and predicted outcomes")
        if body["alternatives"] and kind != "next_test":
            raise ValueError("Discriminating predictions belong to a next_test note")
        if body["claim"] != "root":
            self._read("commitments", body["claim"])
        # Bind references to actual receipt identities, not invented experiment names.
        body["evidence_bindings"] = {}
        for identifier in dict.fromkeys(body["experiments"]):
            experiment = self._read("experiments", identifier)
            body["evidence_bindings"][identifier] = fingerprint(experiment["binding"])
        if body["supersedes"]:
            prior = self._read("notebook", body["supersedes"])
            if prior["claim"] != body["claim"]:
                raise ValueError("A correction cannot silently change its target claim")
        identifier = "note_" + fingerprint(body)[:24]
        with self.lock():
            directory = self.root / "notebook"
            directory.mkdir(exist_ok=True)
            path = directory / (identifier + ".json")
            if not path.exists():
                put(
                    path,
                    dict(id=identifier, created_at=time.time(), authority="worker_note", **body),
                )
        return self._read("notebook", identifier)

    def notes(self, *, limit=20, offset=0, kind=None):
        if (
            not isinstance(limit, int)
            or not 1 <= limit <= 100
            or not isinstance(offset, int)
            or offset < 0
        ):
            raise ValueError("Use limit 1..100 and a nonnegative offset")
        all_notes = sorted(
            self._all("notebook"), key=lambda n: (n["created_at"], n["id"]), reverse=True
        )
        replaced = {n["supersedes"] for n in all_notes if n.get("supersedes")}
        selected = [n for n in all_notes if kind is None or n["kind"] == kind]
        return dict(
            total=len(selected),
            offset=offset,
            notes=[
                dict(n, superseded=n["id"] in replaced) for n in selected[offset : offset + limit]
            ],
        )

    def validate_experiment_context(self, parent_experiment, purpose, plan):
        if purpose not in {
            None,
            "baseline",
            "diagnostic",
            "debug",
            "comparison",
            "validation",
            "timing",
            "parity",
        }:
            raise ValueError("Unknown experiment purpose")
        if parent_experiment:
            self._read("experiments", parent_experiment)
        if plan and self._read("notebook", plan)["kind"] != "next_test":
            raise ValueError("Experiment plan must name a prior next_test note")

    def compare(self, experiments, metrics):
        """Read scalar metrics from verified recorded JSON; never rank scientific truth."""
        from .research_service import sha

        if not 1 <= len(experiments) <= 32 or len(set(experiments)) != len(experiments):
            raise ValueError("Compare 1..32 distinct experiments")
        if not isinstance(metrics, dict) or not 1 <= len(metrics) <= 12:
            raise ValueError("Provide 1..12 metric names mapped to [output, JSON path]")
        for name, spec in metrics.items():
            if not isinstance(name, str) or not isinstance(spec, (list, tuple)) or len(spec) != 2:
                raise ValueError("Each metric must name [output, JSON path]")
            if not all(isinstance(x, str) for x in spec):
                raise ValueError("Output and JSON path must be strings")
        rows = []
        for identifier in experiments:
            r = self._read("experiments", identifier)
            w = self.root / "experiments" / identifier / "workspace"
            values = {}
            documents = {}
            for name, (output, path) in metrics.items():
                cell = dict(value=None, status="unavailable", output=output, path=path)
                if r["status"] != "succeeded":
                    cell["reason"] = f"Experiment execution is {r['status']}"
                elif output not in r["outputs"] or output not in r.get("artifacts", {}):
                    cell["reason"] = "Not a recorded declared output"
                else:
                    artifact = w / output
                    meta = r["artifacts"][output]
                    if (
                        not artifact.is_file()
                        or artifact.is_symlink()
                        or sha(artifact) != meta["sha256"]
                    ):
                        raise ValueError("Recorded artifact changed; comparison rejected")
                    cell["sha256"] = meta["sha256"]
                    if artifact.suffix != ".json" or artifact.stat().st_size > 262144:
                        cell["reason"] = "Record a compact JSON analysis of this artifact first"
                    else:
                        try:
                            if output not in documents:
                                documents[output] = strict_json(artifact.read_text())
                            value = evidence_value(documents[output], path)
                            if isinstance(value, float) and not math.isfinite(value):
                                raise ValueError("Non-finite metric")
                            if value is not None and not isinstance(value, (bool, int, float, str)):
                                raise ValueError("Metric is not a scalar")
                            if isinstance(value, str) and len(value) > 1000:
                                raise ValueError("Metric text exceeds 1000 characters")
                            cell.update(
                                value=value, status="null" if value is None else "available"
                            )
                            if value is None:
                                cell["reason"] = (
                                    "Recorded null; do not treat as zero or falsification"
                                )
                        except (ValueError, KeyError, IndexError, TypeError, UnicodeError) as error:
                            cell["reason"] = str(error)
                values[name] = cell
            rows.append(
                dict(
                    id=identifier,
                    execution=r["status"],
                    stage=r.get("stage", "evidence"),
                    parent_experiment=r.get("parent_experiment"),
                    purpose=r.get("purpose"),
                    source_hash=r["binding"]["inputs"][r["binding"]["source"]],
                    runtime_hash=r["binding"].get("runtime_sha256"),
                    metrics=values,
                )
            )
        return dict(rows=rows, authority="Recorded values; not a scientific adjudication")

    def brief(self, *, max_bytes=16000):
        """Bounded recovery context without code/log duplication or invented summaries."""
        if not isinstance(max_bytes, int) or not 2048 <= max_bytes <= 64000:
            raise ValueError("Brief budget must be 2048..64000 bytes")
        from .research_journal import journal_entries

        snapshot = self.status(compact=True)
        journal = journal_entries(self)
        summaries = sorted(
            (json.loads(p.read_text()) for p in (self.root / "journal/summaries").glob("*.json")),
            key=lambda s: s["created_at"],
            reverse=True,
        )
        experiments = sorted(snapshot["experiments"], key=lambda e: e["created_at"], reverse=True)
        notebook = sorted(
            self._all("notebook"), key=lambda n: (n["created_at"], n["id"]), reverse=True
        )
        replaced = {n["supersedes"] for n in notebook if n.get("supersedes")}
        active = [n for n in notebook if n["id"] not in replaced]
        tested_plans = {e.get("plan") for e in experiments}
        # Preserve unanswered questions and unattempted plans even in a long notebook.
        notes = sorted(
            active,
            key=lambda n: (
                0
                if n["kind"] == "next_test" and n["id"] not in tested_plans
                else 1
                if n["kind"] == "question"
                else 2
            ),
        )
        reviews = sorted(snapshot["reviews"], key=lambda r: r.get("created_at", 0), reverse=True)
        methods = sorted(snapshot["methods"], key=lambda m: m.get("created_at", 0), reverse=True)
        brief = dict(
            hypothesis=shorten(self.manifest["hypothesis"], min(900, max_bytes // 16)),
            authority="Worker notes are unreviewed; only independent verdicts accept claims.",
            remaining_seconds=snapshot["remaining_seconds"],
            completed=snapshot["completed"],
            counts=dict(
                experiments=len(experiments),
                notes=len(notebook),
                execution=dict(Counter(e["status"] for e in experiments)),
            ),
            retrieval=dict(
                guide="RESEARCH_GUIDE.md",
                full_ledger="../research_report.json",
                receipts="../experiments/ID.json",
                notebook="lab.notes(limit=20, offset=0)",
            ),
            budget_warning=snapshot["audit"].get("budget_warning"),
            automatic_journal=[
                {
                    k: e.get(k)
                    for k in (
                        "id",
                        "execution",
                        "source",
                        "args",
                        "implementation",
                        "preceding_attempt_same_entrypoint",
                        "implementation_changed",
                        "explicit_parent",
                        "results",
                        "error",
                        "execution_details",
                        "input_mutations",
                    )
                }
                for e in journal[:8]
            ],
            controller_summaries=[
                dict(authority=s["authority"], notes=s["notes"], packet_sha256=s["packet_sha256"])
                for s in summaries[:2]
            ],
            accepted_claims=[
                dict(id=r["id"], claim=r["claim"], disposition=r["verdict"]["disposition"])
                for r in snapshot["reviews"]
                if (r.get("verdict") or {}).get("decision") == "approved"
            ][:12],
            recent_reviews=[
                dict(
                    id=r["id"],
                    claim=r["claim"],
                    status=r["status"],
                    next_test=shorten((r.get("verdict") or {}).get("next_test"), 500),
                )
                for r in reviews[:8]
            ],
            methods=[{k: m.get(k) for k in ("id", "status", "verdict")} for m in methods[:6]],
            missing_cases=[
                dict(commitment=c["commitment"], missing=c["missing"], planned=c["planned"])
                for c in snapshot["audit"]["coverage"][-12:]
            ],
            notes=[
                {
                    k: n.get(k)
                    for k in (
                        "id",
                        "kind",
                        "statement",
                        "claim",
                        "sources",
                        "experiments",
                        "alternatives",
                        "estimated_seconds",
                    )
                }
                for n in notes[:12]
            ],
            active_experiments=[
                {k: e.get(k) for k in ("id", "status", "stage", "purpose", "parent_experiment")}
                for e in experiments
                if e["status"] in {"queued", "running"}
            ][:12],
            recent_experiments=[
                {
                    k: e.get(k)
                    for k in (
                        "id",
                        "status",
                        "stage",
                        "purpose",
                        "parent_experiment",
                        "plan",
                        "scientific_status",
                        "output_findings",
                    )
                }
                for e in experiments[:12]
            ],
            omitted={},
        )
        for note in brief["notes"]:
            if note["kind"] == "next_test":
                note["attempted_by"] = [
                    e["id"] for e in experiments if e.get("plan") == note["id"]
                ][:8]
                estimate = note.get("estimated_seconds")
                note["estimated_to_fit"] = (
                    estimate + snapshot["audit"]["recommended_review_reserve_seconds"]
                    <= snapshot["remaining_seconds"]
                    if estimate is not None
                    else None
                )
        for key in ("methods",):
            for row in brief[key]:
                if row.get("verdict"):
                    row["verdict"] = {
                        k: shorten(v, 350)
                        for k, v in row["verdict"].items()
                        if k in {"decision", "next_action", "rationale"}
                    }
        # Drop whole entries, never silently truncate a JSON document or overwrite records.
        priority = (
            "recent_experiments",
            "methods",
            "automatic_journal",
            "controller_summaries",
            "notes",
            "recent_reviews",
            "missing_cases",
            "accepted_claims",
            "active_experiments",
        )
        while len(json.dumps(brief, ensure_ascii=False).encode()) > max_bytes:
            removable = next((key for key in priority if brief[key]), None)
            if removable is None:
                raise ValueError("Brief header exceeds requested budget")
            brief[removable].pop()
        totals = dict(
            automatic_journal=len(journal),
            controller_summaries=len(summaries),
            recent_experiments=len(experiments),
            methods=len(snapshot["methods"]),
            recent_reviews=len(snapshot["reviews"]),
            notes=len(notebook),
            missing_cases=len(snapshot["audit"]["coverage"]),
            accepted_claims=sum(
                (r.get("verdict") or {}).get("decision") == "approved" for r in snapshot["reviews"]
            ),
            active_experiments=sum(e["status"] in {"queued", "running"} for e in experiments),
        )
        brief["omitted"] = {key: total - len(brief[key]) for key, total in totals.items()}
        # Reserve space for omission counts too.
        while len(json.dumps(brief, ensure_ascii=False).encode()) > max_bytes:
            key = next((k for k in priority if brief[k]), None)
            if key is None:
                raise ValueError("Brief header exceeds requested budget")
            brief[key].pop()
            brief["omitted"][key] += 1
        return brief

    def write_brief(self):
        from .research_service import put

        body = self.brief()
        put(self.root / "research_brief.json", body)
        temp = self.work / ".RESEARCH_BRIEF.tmp"
        temp.write_text(
            "# Current research brief\n\n"
            "Host-generated from receipts and unreviewed worker notes.\n\n```json\n"
            + json.dumps(body, ensure_ascii=False)
            + "\n```\n"
        )
        temp.replace(self.work / "RESEARCH_BRIEF.md")
        return body
