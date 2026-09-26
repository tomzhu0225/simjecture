"""Small, source-bound methods checkpoint for instrument-backed minimal studies."""

from __future__ import annotations

import json
import time

from pydantic import BaseModel, ConfigDict, Field

from .mvp_skills import MVPCapabilityRegistry


class StudyRequirements(BaseModel):
    """Operator-owned requirements; a reviewer has no authority to weaken these."""

    model_config = ConfigDict(extra="forbid")
    require_method_review: bool = True
    required_capability_prefixes: list[str] = Field(default_factory=list)


class MethodService:
    def freeze_requirements(self, requirements):
        from .research_service import put

        value = StudyRequirements.model_validate(requirements).model_dump()
        if any(not p.strip() for p in value["required_capability_prefixes"]):
            raise ValueError("Capability prefixes cannot be empty")
        with self.lock():
            manifest = json.loads((self.root / "research.json").read_text())
            if "requirements" in manifest:
                if manifest["requirements"] != value:
                    raise ValueError("Study requirements are immutable")
            else:
                if self._all("experiments") or self._all("methods"):
                    raise ValueError("Cannot add requirements after research begins")
                manifest["requirements"] = value
                manifest["methods_required"] = value["require_method_review"]
                put(self.root / "research.json", manifest)
            self.manifest = manifest

    def capability_hashes(self):
        return self.manifest["capability_hashes"] | {
            r["name"]: r["runtime_sha256"] for r in self._all("capability_additions")
        }

    def register_capability(self, name):
        """Append a newly built runtime without changing any existing capability identity."""
        from .research_service import fingerprint, put

        if not self.manifest.get("capabilities"):
            raise ValueError("Study has no operator-configured capability directory")
        registry = MVPCapabilityRegistry.discover(self.manifest["capabilities"])
        runtime = registry.get(name).contract_hash
        with self.lock():
            prior = self.capability_hashes().get(name)
            if prior is not None and prior != runtime:
                raise ValueError("Existing capability identity is immutable; use a new name")
            if prior is not None:
                return dict(name=name, runtime_sha256=prior)
            if time.time() >= self.manifest["deadline"]:
                raise ValueError("Study deadline exhausted")
            body = dict(name=name, runtime_sha256=runtime, created_at=time.time())
            directory = self.root / "capability_additions"
            directory.mkdir(exist_ok=True)
            put(directory / (fingerprint(name) + ".json"), body)
        return body

    @staticmethod
    def method_binding(binding):
        return {k: binding[k] for k in ("source", "inputs", "capability", "runtime_sha256")}

    def check_method(self, binding, method, stage):
        requirements = self.manifest.get("requirements", {})
        if stage == "evidence":
            prefixes = requirements.get("required_capability_prefixes", [])
            if prefixes and not any((binding["capability"] or "").startswith(p) for p in prefixes):
                raise ValueError(
                    "Evidence instrument violates the operator's required capabilities"
                )
        if method:
            record = self._read("methods", method)
            if record["binding"] != self.method_binding(binding):
                raise ValueError("Method source/runtime changed; submit the revised method")
            if stage == "evidence" and record.get("scope", "production") != "production":
                raise ValueError("Instrument readiness does not authorize hypothesis evidence")
            if stage == "evidence" and (
                record.get("verdict", {}).get("decision") != "continue"
                or record.get("verdict", {}).get("prerequisites")
            ):
                raise ValueError("Method needs independent review; end this turn for the host")
        elif stage == "evidence" and self.manifest.get("methods_required", False):
            raise ValueError(
                "Submit lab.method with source, model, geometry, observable, validation and "
                "rationale; end this turn. Use stage='exploration' for commissioning."
            )

    def method(
        self,
        *,
        source,
        model,
        geometry,
        observable,
        validation,
        rationale,
        inputs=(),
        capability=None,
        validation_experiments=(),
        blockers=(),
        scope="production",
    ):
        """Freeze the method and actual commissioning evidence for host-triggered review."""
        from .research_service import fingerprint, put

        if scope not in {"instrument", "production"}:
            raise ValueError("Method scope must be instrument or production")
        fields = dict(
            scope=scope,
            model=model,
            geometry=geometry,
            observable=observable,
            validation=validation,
            rationale=rationale,
        )
        if any(not isinstance(v, str) or not v.strip() for v in fields.values()):
            raise ValueError("Describe every method field")
        binding = self.method_binding(self._binding(source, (), inputs, capability))
        # Even a model reviewer cannot waive an explicit instrument requirement.
        prefixes = self.manifest.get("requirements", {}).get("required_capability_prefixes", [])
        if prefixes and not any((capability or "").startswith(p) for p in prefixes):
            raise ValueError("Proposed method violates required capabilities")
        sources = {}
        for name in binding["inputs"]:
            path = self._source(name)
            if path.stat().st_size > 131072:
                if name == source or path.suffix.lower() in {".py", ".f90", ".h", ".sh"}:
                    raise ValueError("Method source exceeds 128 KiB; provide a compact interface")
                continue
            if name == source or path.suffix.lower() in {
                ".py",
                ".f90",
                ".h",
                ".par",
                ".txt",
                ".json",
                ".md",
                ".sh",
            }:
                sources[name] = path.read_text()
        evidence = []
        from .research_audit import review_documents
        from .research_service import sha

        for identifier in dict.fromkeys([*validation_experiments, *blockers]):
            r = self._read("experiments", identifier)
            if r["status"] in {"queued", "running"}:
                raise ValueError("Wait for the commissioning/blocker experiment to finish")
            w = self.root / "experiments" / identifier / "workspace"
            for name, meta in r.get("artifacts", {}).items():
                if sha(w / name) != meta["sha256"]:
                    raise ValueError("Commissioning artifact changed")
            docs, raw, findings = review_documents(w, r, require_document=False)
            validation_sources = {
                name: (w / name).read_text()
                for name in r["binding"]["inputs"]
                if (name == r["binding"]["source"] or name.endswith((".py", ".F90", ".f90")))
                and (w / name).stat().st_size <= 131072
            }
            evidence.append(
                dict(
                    record=r,
                    documents=docs,
                    sources=validation_sources,
                    raw_artifacts=raw,
                    output_findings=findings,
                )
            )
        if scope == "instrument":
            validated = [
                e["record"]
                for e in evidence
                if e["record"]["id"] in validation_experiments
                and e["record"]["status"] == "succeeded"
            ]
            if not validated:
                raise ValueError(
                    "Instrument readiness requires a successful recorded validation first"
                )
            if not any(self.method_binding(r["binding"]) == binding for r in validated):
                raise ValueError(
                    "Instrument readiness requires validation of the current source/runtime"
                )
        body = dict(
            binding=binding,
            sources=sources,
            **fields,
            evidence=evidence,
            validation_experiments=list(validation_experiments),
            blockers=list(blockers),
        )
        if len(json.dumps(body).encode()) > 700_000:
            raise ValueError("Method packet exceeds 700 KiB")
        identifier = "method_" + fingerprint(body)[:24]
        with self.lock():
            directory = self.root / "methods"
            directory.mkdir(exist_ok=True)
            path = directory / (identifier + ".json")
            if not path.exists():
                put(path, dict(id=identifier, status="queued", created_at=time.time(), **body))
        return self._read("methods", identifier)
