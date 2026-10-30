"""Worker-resident data identities, review views, and logical storage accounting."""

from .worker_protocol import TERMINAL, contained, safe_relative


class ArtifactService:
    def artifact_policy(self):
        # An absent field is a historical eager-collection contract, never a migration.
        return self.manifest.get("artifact_policy", "eager")

    def resolve_remote_inputs(self, references):
        if references is None:
            return {}
        if not isinstance(references, dict):
            raise ValueError("remote_inputs maps destination names to {experiment, path}")
        pool = self.execution_pool() or {}
        result = {}
        for destination, reference in references.items():
            path = safe_relative(destination)
            if path.as_posix() != destination:
                raise ValueError("Use canonical relative remote-input destinations")
            if not isinstance(reference, dict) or set(reference) != {"experiment", "path"}:
                raise ValueError("Each remote input specifies exactly experiment and path")
            source_path = safe_relative(reference["path"])
            if source_path.as_posix() != reference["path"]:
                raise ValueError("Use a canonical recorded artifact path")
            try:
                record = self._read("experiments", reference["experiment"])
            except FileNotFoundError as error:
                raise ValueError(
                    "Remote input must reference an experiment in this study"
                ) from error
            machine = record.get("machine")
            worker = pool.get("workers", {}).get(machine)
            if not worker or not record.get("remote_job"):
                raise ValueError("Remote input must be a recorded artifact on a selected worker")
            if not worker["probe"].get("features", {}).get("artifact_inputs"):
                raise ValueError(
                    "Worker lacks artifact_inputs; prepare a capable worker for a new study"
                )
            if record.get("remote_terminal_status", record["status"]) not in TERMINAL:
                raise ValueError("Wait for the source worker's terminal artifact receipt")
            metadata = record.get("remote_artifacts", {}).get(reference["path"])
            if metadata is None:
                raise ValueError("Remote input is absent from the recorded artifact inventory")
            from .execution_pool import job_identifier
            from .worker_protocol import RemoteArtifactInput

            if record["remote_job"] != job_identifier(self, record):
                raise ValueError(
                    "Recorded source job differs from this study's experiment identity"
                )
            remote = RemoteArtifactInput(
                job=record["remote_job"],
                path=reference["path"],
                sha256=metadata["sha256"],
                bytes=metadata["bytes"],
            ).model_dump()
            result[destination] = remote | {
                "experiment": record["id"],
                "machine": machine,
                "worker_id": worker["probe"]["worker_id"],
            }
        if len({r["machine"] for r in result.values()}) > 1:
            raise ValueError("Resident inputs must share one worker; migration must be explicit")
        return result

    def remote_input_review(self, binding):
        """Expose every dependency; cached text is readable, resident data is uninspected."""
        from .review_assets import source_views

        result = {}
        for destination, reference in binding.get("remote_inputs", {}).items():
            view = reference | {
                "location": "worker",
                "inspected": False,
                "note": "Recorded identity is not content inspection or scientific qualification",
            }
            workspace = self.root / "experiments" / reference["experiment"] / "workspace"
            path = contained(workspace, reference["path"])
            if path.suffix.lower() in {".py", ".f90", ".h", ".par", ".txt", ".json", ".md", ".sh"}:
                view["source_dependency"] = True
                if path.is_file():
                    sources, references = source_views(
                        self.root,
                        workspace,
                        {reference["path"]: reference["sha256"]},
                        [reference["path"]],
                    )
                    view.update(sources=sources, source_references=references, location="cached")
                else:
                    view["note"] = (
                        "Remote text/code dependency is not inspected. Fetch it before relying on "
                        "its contents for source qualification; missing inspection is a review gap."
                    )
            result[destination] = view
        return result

    @staticmethod
    def remote_footprint(record):
        """A logical retained footprint, not a guarantee of free physical disk space."""
        inventory = sum(m["bytes"] for m in record.get("remote_artifacts", {}).values())
        recorded = (record.get("execution") or {}).get("workspace_bytes", 0)
        return max(inventory, recorded)

    def artifact_storage(self):
        from .mvp_agent import BubblewrapSandbox

        used = BubblewrapSandbox._tree_bytes(self.root / "experiments")
        reserved = 0
        for record in self._all("experiments"):
            local = BubblewrapSandbox._tree_bytes(
                self.root / "experiments" / record["id"] / "workspace"
            )
            footprint = local
            if self.artifact_policy() == "remote" and record.get("machine"):
                footprint = max(local, self.remote_footprint(record))
                used += footprint - local
            if record["status"] in {"queued", "running"}:
                reserved += max(
                    0,
                    record.get("workspace_limit_bytes", self.manifest["max_experiment_bytes"])
                    - footprint,
                )
        return dict(used_bytes=used, reserved_bytes=reserved)
