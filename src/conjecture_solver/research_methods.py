"""Small, source-bound methods checkpoint for instrument-backed minimal studies."""

from __future__ import annotations

import json
import re
import time

from pydantic import BaseModel, ConfigDict, Field

from .mvp_skills import MVPCapabilityRegistry
from .research_registration import RegistrationService


def experiment_ids(values, field):
    """Validate receipt references before reading source or hashing a runtime."""
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{field} must be a list of experiment receipt IDs, e.g. ['exp_ID']")
    for index, value in enumerate(values):
        if not isinstance(value, str) or not re.fullmatch(r"exp_[a-z0-9_-]+", value):
            raise ValueError(
                f"{field}[{index}] must be an experiment receipt ID (exp_...), "
                "not descriptive text. Put scientific limitations in limitations=[...]."
            )
    return list(dict.fromkeys(values))


class StudyRequirements(BaseModel):
    """Operator-owned requirements; a reviewer has no authority to weaken these."""

    model_config = ConfigDict(extra="forbid")
    require_method_review: bool = True
    required_capability_prefixes: list[str] = Field(
        default_factory=list,
        description="Alternative families: ONE matching prefix satisfies the requirement.",
    )


def instrument_requirement(manifest, *, capability=None, available=()):
    """Evaluate the existing any-of contract; availability is not qualification."""
    prefixes = manifest.get("requirements", {}).get("required_capability_prefixes", [])
    candidates = [capability] if capability is not None else list(available)
    matching = [c for c in candidates if any(c.startswith(p) for p in prefixes)]
    return dict(
        id="instrument_family",
        operator="any_of",
        prefixes=prefixes,
        scope="selected_method" if capability is not None else "available_instruments",
        matching_capabilities=matching,
        satisfied=not prefixes or bool(matching),
        interpretation=(
            "One matching instrument family is sufficient; other listed families are alternatives. "
            "This checks instrument identity only, not scientific suitability or method approval."
        ),
    )


class MethodService(RegistrationService):
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

    def execution_pool(self):
        """Frozen workers plus append-only instrument registrations."""
        pool = self.manifest.get("execution_pool")
        if not pool:
            return None
        capabilities = dict(pool["capabilities"])
        for record in self._all("capability_additions"):
            if remote := record.get("remote_capability"):
                if record["name"] in capabilities and capabilities[record["name"]] != remote:
                    raise ValueError("Existing capability identity is immutable")
                capabilities[record["name"]] = remote
        return pool | {"capabilities": capabilities}

    def _remote_registration(self, name, machine):
        from .execution_pool import MachineRegistry

        pool = self.execution_pool()
        if not pool or machine not in pool["workers"]:
            raise ValueError("Choose a frozen execution machine for capability registration")
        worker = pool["workers"][machine]
        return self.probe_registration(
            MachineRegistry(pool["registry"]).transport(machine, frozen=worker),
            name=name,
            machine=machine,
            validate=lambda probe: self._validate_remote_registration(name, machine, pool, probe),
        )

    def _validate_remote_registration(self, name, machine, pool, probe):
        from .worker_protocol import PROTOCOL

        worker = pool["workers"][machine]
        if probe.get("protocol") != PROTOCOL or abs(probe["clock"] - time.time()) > 30:
            raise ValueError("Worker protocol or clock differs from the frozen study")
        for key in ("worker_id", "worker_code_sha256", "config_sha256"):
            if probe.get(key) != worker["probe"].get(key):
                raise ValueError("Worker identity or configuration changed since study preparation")
        if probe["capacity"] != worker["profile"]["config"] or not probe["execution"]["available"]:
            raise ValueError("Worker capacity or exact experiment launcher is unavailable")
        for entry in pool["capabilities"].values():
            if (
                entry["machine"] == machine
                and probe["capabilities"].get(entry["worker_capability"], {}).get("contract_sha256")
                != entry["runtime_sha256"]
            ):
                raise ValueError(
                    "Existing capability identity is immutable; restore it and use a new name"
                )
        descriptor = probe["capabilities"].get(name)
        if not descriptor or not re.fullmatch(
            r"[a-f0-9]{64}", descriptor.get("contract_sha256", "")
        ):
            raise ValueError(
                "New instrument is not available in the worker's configured capability directory"
            )
        return f"{name}--at-{machine}", dict(
            machine=machine,
            worker_capability=name,
            runtime_sha256=descriptor["contract_sha256"],
            descriptor=descriptor,
        )

    def register_capability(self, name, *, machine=None, development=None):
        """Append a newly built runtime without changing any existing capability identity."""
        from .research_service import fingerprint, put

        development = self.validate_development(development) if development is not None else None
        remote = None
        if machine is not None or not self.manifest.get("capabilities"):
            pool = self.execution_pool()
            if machine is None:
                if not pool:
                    raise ValueError("Study has no operator-configured capability directory")
                if len(pool["workers"]) != 1:
                    raise ValueError("Specify machine for remote capability registration")
                machine = next(iter(pool["workers"]))
            name, remote = self._remote_registration(name, machine)
            runtime = remote["runtime_sha256"]
        else:
            registry = MVPCapabilityRegistry.discover(self.manifest["capabilities"], names=(name,))
            runtime = registry.get(name).contract_hash
        with self.lock():
            prior = self.capability_hashes().get(name)
            if prior is not None and prior != runtime:
                raise ValueError("Existing capability identity is immutable; use a new name")
            if prior is not None:
                if development is not None:
                    previous = next(
                        (r for r in self._all("capability_additions") if r["name"] == name), {}
                    )
                    if previous.get("development") != development:
                        raise ValueError("Registered development provenance is immutable")
                return dict(name=name, runtime_sha256=prior)
            if self.solver_development_policy()["allowed"] is False:
                raise ValueError(
                    "Solver development is disabled: use the supplied instrument implementations"
                )
            if time.time() >= self.registration_deadline():
                raise ValueError("Registration compute budget exhausted")
            body = dict(name=name, runtime_sha256=runtime, created_at=time.time())
            if remote:
                body["remote_capability"] = remote
            if development is not None:
                body["development"] = development
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
                or record.get("verdict", {}).get("evidence_requests")
            ):
                raise ValueError("Method needs independent review; end this turn for the host")
        elif stage == "evidence" and (
            (
                self.manifest.get("methods_required", False)
                and (
                    self.manifest.get("method_review_scope", "study") == "study"
                    or binding["capability"]
                    or requirements.get("require_method_review", False)
                )
            )
            or any(r["name"] == binding["capability"] for r in self._all("capability_additions"))
        ):
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
        blocker_experiments=(),
        limitations=(),
        scope="production",
    ):
        """Freeze the method and actual commissioning evidence for host-triggered review."""
        from .research_service import fingerprint, put

        blockers = experiment_ids(blockers, "blockers")
        blocker_experiments = experiment_ids(blocker_experiments, "blocker_experiments")
        if blockers and blocker_experiments:
            raise ValueError("Use blocker_experiments or its legacy alias blockers, not both")
        validation_experiments = experiment_ids(validation_experiments, "validation_experiments")
        blockers = blocker_experiments or blockers
        if (
            not isinstance(limitations, (list, tuple))
            or any(not isinstance(v, str) or not v.strip() or len(v) > 2400 for v in limitations)
            or len(limitations) > 32
        ):
            raise ValueError(
                "limitations must be at most 32 nonempty descriptions, each ≤2400 chars"
            )
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
        from .review_assets import source_views

        sources, source_references = source_views(
            self.root,
            self.work,
            binding["inputs"],
            [
                n
                for n in binding["inputs"]
                if n == source
                or self._source(n).suffix.lower()
                in {".py", ".f90", ".h", ".par", ".txt", ".json", ".md", ".sh"}
            ],
        )
        evidence = []
        from .research_audit import review_documents
        from .research_service import sha

        for identifier in dict.fromkeys([*validation_experiments, *blockers]):
            try:
                r = self._read("experiments", identifier)
            except FileNotFoundError as error:
                raise ValueError(
                    f"Method references unknown experiment {identifier!r}; "
                    "choose an existing receipt from lab.status()."
                ) from error
            if r["status"] in {"queued", "running"}:
                raise ValueError("Wait for the commissioning/blocker experiment to finish")
            w = self.root / "experiments" / identifier / "workspace"
            for name, meta in r.get("artifacts", {}).items():
                if sha(w / name) != meta["sha256"]:
                    raise ValueError("Commissioning artifact changed")
            docs, raw, findings = review_documents(
                w, r, require_document=False, review_root=self.root
            )
            validation_sources, validation_references = source_views(
                self.root,
                w,
                r["binding"]["inputs"],
                [
                    n
                    for n in r["binding"]["inputs"]
                    if n == r["binding"]["source"] or n.endswith((".py", ".F90", ".f90"))
                ],
            )
            from .research_receipts import receipt_projection

            evidence.append(
                dict(
                    record=receipt_projection(self, r),
                    documents=docs,
                    sources=validation_sources,
                    source_references=validation_references,
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
            source_references=source_references,
            solver_development=dict(
                policy=self.solver_development_policy(),
                registration=next(
                    (r for r in self._all("capability_additions") if r["name"] == capability), None
                ),
            ),
            **fields,
            evidence=evidence,
            validation_experiments=list(validation_experiments),
            blockers=list(blockers),
            **({"limitations": list(limitations)} if limitations else {}),
        )
        identifier = "method_" + fingerprint(body)[:24]
        with self.lock():
            directory = self.root / "methods"
            directory.mkdir(exist_ok=True)
            path = directory / (identifier + ".json")
            if not path.exists():
                put(path, dict(id=identifier, status="queued", created_at=time.time(), **body))
        return self._read("methods", identifier)
