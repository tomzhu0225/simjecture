"""Model-independent execution kernel for a durable MVP campaign.

``MVPAgentRunner`` owns the model conversation and the report loop.  This
module owns the boundary between a typed action and the scientific workspace.
Keeping that boundary in a small object lets other front-ends (in particular a
durable DSH supervisor) execute exactly the same action semantics without
having to impersonate a model turn.

The first extraction deliberately uses a host protocol rather than copying the
large amount of existing claim/provenance code.  The host is the compatibility
adapter supplied by ``MVPAgentRunner``; no completion client or model state is
read by this class.  All validation and persistence still happen in the same
order as the original runner.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .mvp_agent import MVPAgentAction


class CampaignWriterBusyError(RuntimeError):
    """A second mutating action would race a durable campaign writer."""


class CampaignOperationInProgressError(RuntimeError):
    """An operation id names an action whose outcome is not yet known."""


class CampaignOperationFailedError(RuntimeError):
    """An idempotent operation previously failed and must not be rerun."""


class CampaignBudgetExceededError(RuntimeError):
    """The durable campaign action or wall-clock budget is exhausted."""


def _failed_operation_replay_message(operation_id: str, error: object) -> str:
    """Explain immutable failed receipts without inviting an unsafe replay."""

    detail = str(error).strip() or "the earlier action failed"
    return (
        f"operation_id {operation_id!r} is a durable failed receipt and cannot be "
        f"rerun: {detail}. Reusing this operation_id only replays that failure; "
        "after correcting the action or changing campaign preconditions, submit "
        "the action with a new operation_id."
    )


ACTION_JOURNAL_FILE = "action_journal.json"
BUDGET_FILE = "kernel_budget.json"
RUNTIME_SCHEMA_VERSION = "0.1.0"
SNAPSHOT_MAX_ARTIFACTS = 12
SNAPSHOT_MAX_JOBS = 16
SNAPSHOT_MAX_LITERATURE_SEARCHES = 4
RESOURCE_SNAPSHOT_DIRECTORY = "kernel_resource_snapshot"
RESOURCE_SNAPSHOT_RECORD = "snapshot.json"


class CampaignKernel:
    """Execute model-neutral campaign actions against an existing MVP host.

    The host protocol is intentionally duck-typed to preserve the public MVP
    imports while making the execution surface reusable.  A host supplies the
    established manifest, guided-commissioning, literature, skill, capability,
    artifact, and claim-ledger helpers.  ``perform`` is the only method that
    mutates the scientific workspace; it delegates to the host's compatibility
    implementation after applying the startup gate.  The explicit methods make
    lifecycle/reconciliation callers independent of the model loop.
    """

    def __init__(self, host: Any) -> None:
        if host is None:
            raise TypeError("CampaignKernel requires an execution host")
        self.host = host
        self._job_supervisor: Any | None = None
        self._writer_lock_depth = 0
        self._writer_lock_handle: Any | None = None
        self._authenticated_worker_jobs: set[str] = set()
        self._memory_journal: dict[str, Any] = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "next_sequence": 1,
            "operations": {},
        }

    @classmethod
    def open(
        cls,
        host: Any | None = None,
        *,
        workspace: str | Path | None = None,
        root: str | Path | None = None,
        output: str | Path | None = None,
        campaign: str | Path | None = None,
        hypothesis: str | None = None,
        config: Any | Mapping[str, Any] | None = None,
        skills: Any | None = None,
        capabilities: Any | None = None,
        literature_search: Any | None = None,
        **_ignored: Any,
    ) -> CampaignKernel:
        """Open a kernel over a runner or durable operator campaign.

        A prebuilt runner remains the most explicit form.  For model-free
        front-ends (MCP/DSH), ``workspace``/``campaign`` points at an MVP
        output directory containing ``operator_input/launch.json`` or
        ``mvp_manifest.json``.  The opener reconstructs the same sandbox,
        skills, capability registry, and claim ledger but never constructs a
        completion client call.  A fresh directory must supply ``hypothesis``;
        an existing durable directory supplies it from its manifest.
        """

        if host is None:
            target = cls._resolve_target(
                workspace=workspace,
                root=root,
                output=output,
                campaign=campaign,
            )
            from .campaign_jobs import CampaignInterprocessLock

            # Runner construction eagerly touches the claim ledger, so the
            # lock must cover construction as well as manifest initialization.
            with CampaignInterprocessLock(target):
                host = cls._build_standalone_host(
                    workspace=workspace,
                    root=root,
                    output=output,
                    campaign=campaign,
                    hypothesis=hypothesis,
                    config=config,
                    skills=skills,
                    capabilities=capabilities,
                    literature_search=literature_search,
                )
                kernel = cls(host)
                kernel.initialize()
                kernel._ensure_runtime_files()
                kernel._persist_resource_roots()
                return kernel
        kernel = cls(host)
        with kernel._writer_lock():
            kernel.initialize()
            kernel._ensure_runtime_files()
            kernel._persist_resource_roots()
        return kernel

    @classmethod
    def open_existing(
        cls,
        *,
        workspace: str | Path | None = None,
        root: str | Path | None = None,
        output: str | Path | None = None,
        campaign: str | Path | None = None,
    ) -> CampaignKernel:
        """Reopen an initialized campaign without locking during reconstruction.

        Detached workers start only after the parent has durably created the
        manifest, ledgers, runtime files, resource identity, and worker
        handshake.  Those files are replaced atomically, so rebuilding the
        in-memory host from them is read-only and does not need to monopolize
        the campaign writer lock.  A short lock still protects final contract
        validation before the returned kernel may execute its leased action.

        This deliberately refuses incomplete campaigns.  Fresh campaign
        creation and recovery continue to use :meth:`open`, whose lock covers
        all potentially creating initialization paths.
        """

        target = cls._resolve_target(
            workspace=workspace,
            root=root,
            output=output,
            campaign=campaign,
        )
        required_files = (
            "mvp_manifest.json",
            "hypothesis_ledger.json",
            ACTION_JOURNAL_FILE,
            BUDGET_FILE,
            cls._resource_file(target).name,
        )
        for name in required_files:
            path = target / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"existing campaign is missing initialized file: {name}")

        # The expensive claim/provenance/resource reconstruction is read-only
        # for a fully initialized campaign and all of its inputs are atomic
        # snapshots.  Keep it outside the cross-process writer lock so status
        # polling remains responsive while a worker starts.
        host = cls._build_standalone_host(
            workspace=target,
            root=None,
            output=None,
            campaign=None,
            hypothesis=None,
            config=None,
            skills=None,
            capabilities=None,
            literature_search=None,
        )
        kernel = cls(host)

        from .campaign_jobs import CampaignInterprocessLock

        # Existing-only preconditions make these verification calls
        # non-creating.  The lock prevents a control-plane mutation from
        # interleaving with the final immutable-contract checks.
        with CampaignInterprocessLock(target):
            kernel.initialize()
            kernel._persist_resource_roots()
        return kernel

    @staticmethod
    def _resolve_target(
        *,
        workspace: str | Path | None,
        root: str | Path | None,
        output: str | Path | None,
        campaign: str | Path | None,
    ) -> Path:
        target: Path | None = None
        if campaign is not None:
            campaign_value = Path(campaign).expanduser()
            if campaign_value.is_absolute() or workspace is None:
                target = campaign_value.resolve()
            else:
                workspace_value = Path(workspace).expanduser().resolve()
                direct = workspace_value / campaign_value
                grouped = workspace_value / "campaigns" / campaign_value
                target = (direct if direct.exists() or not grouped.exists() else grouped).resolve()
        elif output is not None:
            target = Path(output).expanduser().resolve()
        elif root is not None:
            target = Path(root).expanduser().resolve()
        elif workspace is not None:
            target = Path(workspace).expanduser().resolve()
        if target is None:
            raise ValueError("CampaignKernel.open requires workspace or output")
        return target

    @staticmethod
    def _resource_file(root: Path) -> Path:
        return root / "kernel_resources.json"

    @staticmethod
    def _snapshot_default_resources(
        root: Path,
        *,
        skills: Any,
        capabilities: Any,
    ) -> tuple[Any, Any]:
        """Freeze repository resources before an immutable campaign starts.

        Built-in skills and capability JSON files live in the checkout and can
        legitimately change while a long simulation is running. Detached
        workers must nevertheless reopen the exact catalog recorded by the
        campaign manifest. Copy the small declarative inputs into the campaign
        and retain capability runtime references as read-only symlinks; runtime
        identity remains guarded by the existing capability hashes.
        """

        from .mvp_skills import MVPCapabilityRegistry, MVPSkillCatalog

        source_skills = getattr(skills, "root", None)
        source_capabilities = getattr(capabilities, "root", None)
        if source_skills is None or source_capabilities is None:
            raise ValueError("default kernel resources must have discovery roots")
        source_skills = Path(source_skills).resolve()
        source_capabilities = Path(source_capabilities).resolve()
        destination = root / RESOURCE_SNAPSHOT_DIRECTORY
        if destination.is_symlink():
            raise ValueError("kernel resource snapshot must not be a symlink")

        if not destination.exists():
            temporary = Path(
                tempfile.mkdtemp(
                    prefix=f".{RESOURCE_SNAPSHOT_DIRECTORY}.",
                    dir=root,
                )
            )
            try:
                skill_destination = temporary / "skills"
                skill_destination.mkdir()
                for manifest_path in sorted(source_skills.glob("*/manifest.json")):
                    skill_root = manifest_path.parent
                    shutil.copytree(
                        skill_root,
                        skill_destination / skill_root.name,
                    )
                capability_destination = temporary / "capabilities"
                capability_destination.mkdir()
                for config_path in sorted(source_capabilities.glob("*.json")):
                    if config_path.is_symlink() or not config_path.is_file():
                        raise ValueError("capability configuration must be a regular file")
                    shutil.copy2(
                        config_path,
                        capability_destination / config_path.name,
                    )
                    payload = json.loads(config_path.read_text(encoding="utf-8"))
                    references = [payload.get("runtime_root")]
                    mounts = payload.get("read_only_mounts") or {}
                    if not isinstance(mounts, Mapping):
                        raise ValueError("capability read_only_mounts must be an object")
                    references.extend(mounts.values())
                    for reference in references:
                        if not isinstance(reference, str) or not reference:
                            continue
                        relative = Path(reference)
                        if relative.is_absolute():
                            continue
                        source = (source_capabilities / relative).resolve()
                        if not source.is_dir():
                            raise ValueError(f"capability resource is unavailable: {source}")
                        link = Path(os.path.abspath(capability_destination / relative))
                        if not link.is_relative_to(temporary):
                            raise ValueError("relative capability resource escapes its snapshot")
                        link.parent.mkdir(parents=True, exist_ok=True)
                        if link.exists() or link.is_symlink():
                            if not link.is_symlink() or link.resolve() != source:
                                raise ValueError("capability snapshot references conflict")
                            continue
                        link.symlink_to(source, target_is_directory=True)
                candidate_skills = MVPSkillCatalog.discover(temporary / "skills")
                candidate_capabilities = MVPCapabilityRegistry.discover(
                    temporary / "capabilities",
                    ignore_unavailable=False,
                )
                if candidate_skills.hashes != skills.hashes:
                    raise ValueError("kernel skill snapshot identity does not match its source")
                if candidate_capabilities.hashes != capabilities.hashes:
                    raise ValueError(
                        "kernel capability snapshot identity does not match its source"
                    )
                (temporary / RESOURCE_SNAPSHOT_RECORD).write_text(
                    json.dumps(
                        {
                            "schema_version": RUNTIME_SCHEMA_VERSION,
                            "skill_hashes": candidate_skills.hashes,
                            "capability_hashes": candidate_capabilities.hashes,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                os.replace(temporary, destination)
            except BaseException:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
        if not destination.is_dir() or destination.resolve() != destination:
            raise ValueError("kernel resource snapshot is not a regular directory")

        frozen_skills = MVPSkillCatalog.discover(destination / "skills")
        frozen_capabilities = MVPCapabilityRegistry.discover(
            destination / "capabilities",
            ignore_unavailable=False,
        )
        record_path = destination / RESOURCE_SNAPSHOT_RECORD
        if record_path.is_symlink() or not record_path.is_file():
            raise ValueError("kernel resource snapshot has no identity record")
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("kernel resource snapshot identity is invalid") from error
        if (
            record.get("schema_version") != RUNTIME_SCHEMA_VERSION
            or record.get("skill_hashes") != frozen_skills.hashes
            or record.get("capability_hashes") != frozen_capabilities.hashes
        ):
            raise ValueError("kernel resource snapshot identity changed")
        return frozen_skills, frozen_capabilities

    def _prepare_host_resources(self) -> None:
        """Install a campaign-pinned catalog before manifest validation."""

        root = self._campaign_root
        if root is None:
            return
        from .mvp_skills import MVPCapabilityRegistry, MVPSkillCatalog

        resource_path = self._resource_file(root)
        if resource_path.exists():
            recorded = self._load_resource_roots(root)
            skills = getattr(self.host, "skills", None)
            capabilities = getattr(self.host, "capabilities", None)
            if recorded["skills_root"] is not None:
                skills = MVPSkillCatalog.discover(recorded["skills_root"])
            if recorded["capabilities_root"] is not None:
                capabilities = MVPCapabilityRegistry.discover(
                    recorded["capabilities_root"],
                    ignore_unavailable=False,
                )
            if skills is not None:
                self.host.skills = skills
            if capabilities is not None:
                self.host.capabilities = capabilities
                sandbox = getattr(self.host, "sandbox", None)
                if sandbox is not None:
                    sandbox.capabilities = capabilities
            self.host._kernel_resource_roots = recorded
            return

        # Standalone construction already chose explicit or snapshotted roots.
        if isinstance(getattr(self.host, "_kernel_resource_roots", None), Mapping):
            return
        skills = getattr(self.host, "skills", None)
        capabilities = getattr(self.host, "capabilities", None)
        if getattr(skills, "root", None) is None or getattr(capabilities, "root", None) is None:
            return
        frozen_skills, frozen_capabilities = self._snapshot_default_resources(
            root,
            skills=skills,
            capabilities=capabilities,
        )
        self.host.skills = frozen_skills
        self.host.capabilities = frozen_capabilities
        sandbox = getattr(self.host, "sandbox", None)
        if sandbox is not None:
            sandbox.capabilities = frozen_capabilities
        self.host._kernel_resource_roots = {
            "skills_root": str(frozen_skills.root),
            "capabilities_root": str(frozen_capabilities.root),
        }

    @classmethod
    def _load_resource_roots(cls, root: Path) -> dict[str, str | None]:
        path = cls._resource_file(root)
        if not path.exists():
            return {"skills_root": None, "capabilities_root": None}
        if path.is_symlink() or not path.is_file():
            raise ValueError("kernel resource configuration is not a regular file")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("invalid kernel resource configuration") from error
        if payload.get("schema_version") != RUNTIME_SCHEMA_VERSION:
            raise ValueError("unsupported kernel resource configuration schema")
        result: dict[str, str | None] = {}
        for key in ("skills_root", "capabilities_root"):
            value = payload.get(key)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"kernel resource {key} must be a path or null")
                resolved = Path(value).expanduser().resolve()
                if not resolved.is_dir():
                    raise ValueError(f"kernel resource {key} is unavailable: {resolved}")
                value = str(resolved)
            result[key] = value
        return result

    @staticmethod
    def _build_standalone_host(
        *,
        workspace: str | Path | None,
        root: str | Path | None,
        output: str | Path | None,
        campaign: str | Path | None,
        hypothesis: str | None,
        config: Any | Mapping[str, Any] | None,
        skills: Any | None,
        capabilities: Any | None,
        literature_search: Any | None,
    ) -> Any:
        """Construct the compatibility host used by a model-free kernel."""

        from .mvp_agent import BubblewrapSandbox, MVPAgentConfig, MVPAgentRunner
        from .mvp_launch import load_launch_request
        from .mvp_skills import discover_builtin_mvp_resources

        # An explicit campaign/output is a destination, not merely one of a
        # list of existing directories.  Falling back to an existing parent
        # would silently create a new manifest in the bridge workspace when a
        # requested campaign has not been created yet.
        target = CampaignKernel._resolve_target(
            workspace=workspace,
            root=root,
            output=output,
            campaign=campaign,
        )
        target.mkdir(parents=True, exist_ok=True)
        recorded_resources = CampaignKernel._load_resource_roots(target)
        selected_skills_root = (
            str(Path(skills).expanduser().resolve())
            if isinstance(skills, (str, Path))
            else recorded_resources["skills_root"]
        )
        selected_capabilities_root = (
            str(Path(capabilities).expanduser().resolve())
            if isinstance(capabilities, (str, Path))
            else recorded_resources["capabilities_root"]
        )

        # ``load_launch_request`` is itself the durable operator-input gate.
        # Let malformed, stale, or externally-dependent launch contracts fail
        # loudly instead of silently falling back to a weaker manifest/default
        # reconstruction.
        launch = load_launch_request(target)
        manifest: dict[str, Any] = {}
        manifest_path = target / "mvp_manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text())

        launch_config: Any | None = None
        manifest_config: Any | None = None
        if launch is not None:
            if hypothesis is not None and hypothesis != launch.hypothesis:
                raise ValueError("supplied hypothesis does not match the immutable operator launch")
            selected_hypothesis = launch.hypothesis
            selected_instruction = launch.instruction
            launch_config = MVPAgentConfig(
                max_iterations=launch.max_iterations,
                max_wall_seconds=launch.max_wall_seconds,
                max_command_seconds=launch.max_command_seconds,
                max_workspace_bytes=launch.max_workspace_mb * 1024 * 1024,
                max_file_bytes=launch.max_file_mb * 1024 * 1024,
                max_memory_bytes=launch.max_memory_mb * 1024 * 1024,
                max_tool_output_chars=launch.max_tool_output_chars,
                command_heartbeat_seconds=launch.command_heartbeat_seconds,
                recent_full_turns=launch.recent_full_turns,
                max_model_retries=launch.max_model_retries,
                model_failover_after=launch.model_failover_after,
            )
            if config is None:
                config = launch_config
            if skills is None and launch.skills_directory:
                from .mvp_skills import MVPSkillCatalog

                skills = MVPSkillCatalog.discover(launch.skills_directory)
                selected_skills_root = str(Path(launch.skills_directory).expanduser().resolve())
            if capabilities is None and launch.capability_directory:
                from .mvp_skills import MVPCapabilityRegistry

                capabilities = MVPCapabilityRegistry.discover(
                    launch.capability_directory,
                    ignore_unavailable=False,
                )
                selected_capabilities_root = str(
                    Path(launch.capability_directory).expanduser().resolve()
                )
        else:
            selected_hypothesis = hypothesis or manifest.get("hypothesis")
            selected_instruction = manifest.get("campaign_instruction")
            if manifest.get("config"):
                manifest_config = MVPAgentConfig.model_validate(manifest["config"])
                if config is None:
                    config = manifest_config
        if not isinstance(selected_hypothesis, str) or not selected_hypothesis.strip():
            raise ValueError(
                "model-free CampaignKernel.open requires a hypothesis in launch.json, "
                "mvp_manifest.json, or the hypothesis argument"
            )
        if config is None:
            config = MVPAgentConfig()
        elif isinstance(config, Mapping):
            config = MVPAgentConfig.model_validate(config)
        elif not isinstance(config, MVPAgentConfig):
            # MCP BridgeConfig intentionally has a smaller host-facing shape
            # than MVPAgentConfig.  Its output bound belongs to the bridge,
            # not the immutable scientific run contract.  Reconstruct the
            # durable limits from launch.json/manifest instead of silently
            # replacing them with defaults (which would fail identity checks
            # on the first worker reopen).
            config = launch_config or manifest_config or MVPAgentConfig()

        builtin_skills, builtin_capabilities = discover_builtin_mvp_resources()
        # A fresh default campaign owns an immutable copy of the declarative
        # resources it starts with. Explicit resource roots remain explicit:
        # their launch contract already records that operator-managed choice.
        if (
            not CampaignKernel._resource_file(target).exists()
            and skills is None
            and capabilities is None
            and selected_skills_root is None
            and selected_capabilities_root is None
        ):
            builtin_skills, builtin_capabilities = CampaignKernel._snapshot_default_resources(
                target,
                skills=builtin_skills,
                capabilities=builtin_capabilities,
            )
            selected_skills_root = str(builtin_skills.root)
            selected_capabilities_root = str(builtin_capabilities.root)
        if skills is None and selected_skills_root is not None:
            from .mvp_skills import MVPSkillCatalog

            skills = MVPSkillCatalog.discover(selected_skills_root)
        if capabilities is None and selected_capabilities_root is not None:
            from .mvp_skills import MVPCapabilityRegistry

            capabilities = MVPCapabilityRegistry.discover(
                selected_capabilities_root,
                ignore_unavailable=False,
            )
        if isinstance(skills, (str, Path)):
            from .mvp_skills import MVPSkillCatalog

            skills = MVPSkillCatalog.discover(skills)
        if isinstance(capabilities, (str, Path)):
            from .mvp_skills import MVPCapabilityRegistry

            capabilities = MVPCapabilityRegistry.discover(capabilities)
        if selected_skills_root is None:
            discovery_root = getattr(skills, "root", None)
            if discovery_root is not None:
                selected_skills_root = str(Path(discovery_root).resolve())
        if selected_capabilities_root is None:
            # A runtime root is not the directory containing capability JSON
            # manifests. Persist the registry's actual discovery root instead
            # of guessing from an installation path such as `.runtime/`.
            discovery_root = getattr(capabilities, "root", None)
            if discovery_root is not None:
                selected_capabilities_root = str(Path(discovery_root).resolve())
        skills = skills or builtin_skills
        capabilities = capabilities or builtin_capabilities

        guided = None
        if launch is not None and launch.guided_commission:
            from .mvp_guidance import MVPGuidedCommissioningPackage

            guided = MVPGuidedCommissioningPackage.read(launch.guided_commission)

        if literature_search is None:
            recorded_identity = (manifest.get("literature_search") or {}).get("identity")
            if isinstance(recorded_identity, dict):
                # Reopen the configured public client when possible so a
                # worker preserves the exact manifest identity and startup
                # search gate.  Unknown host clients retain identity for
                # manifest validation but cannot silently invent search hits.
                if recorded_identity.get("name") == "public-literature-search":
                    from .literature import PublicLiteratureSearchClient

                    literature_search = PublicLiteratureSearchClient(
                        timeout_seconds=(
                            launch.literature_search_timeout_seconds if launch is not None else 20.0
                        )
                    )
                else:

                    class _RecordedSearch:
                        identity = recorded_identity

                        def search(self, **_kwargs: Any) -> Any:
                            raise RuntimeError(
                                "the recorded literature provider is unavailable "
                                "to this model-free worker"
                            )

                    literature_search = _RecordedSearch()
            elif not manifest_path.exists():
                # Match the CLI's default bounded public reconnaissance client
                # for a fresh model-free campaign.  Existing manifests with an
                # explicit null provider retain their historical contract.
                from .literature import PublicLiteratureSearchClient

                literature_search = PublicLiteratureSearchClient(
                    timeout_seconds=(
                        launch.literature_search_timeout_seconds if launch is not None else 20.0
                    )
                )

        class _NoModelCompletion:
            def complete(self, *_args: Any, **_kwargs: Any) -> Any:
                raise RuntimeError(
                    "model-free CampaignKernel has no completion client; use execute"
                )

        sandbox = BubblewrapSandbox(target / "workspace", config, capabilities)
        runner = MVPAgentRunner(
            hypothesis=selected_hypothesis,
            campaign_instruction=selected_instruction,
            output_directory=target,
            completion_client=_NoModelCompletion(),
            sandbox=sandbox,
            config=config,
            skills=skills,
            capabilities=capabilities,
            guided_commissioning=guided,
            literature_search=literature_search,
        )
        runner._kernel_resource_roots = {
            "skills_root": selected_skills_root,
            "capabilities_root": selected_capabilities_root,
        }
        return runner

    @property
    def hypothesis(self) -> str:
        return self.host.hypothesis

    @property
    def manifest_path(self) -> Any:
        return self.host.manifest_path

    @property
    def artifact_provenance_path(self) -> Any:
        return self.host.artifact_provenance_path

    @property
    def claim_store(self) -> Any:
        return self.host.claim_store

    @property
    def skills(self) -> Any:
        return self.host.skills

    @property
    def capabilities(self) -> Any:
        return self.host.capabilities

    def initialize(self) -> None:
        """Validate/create the immutable run manifest and guided input.

        This delegates to the established implementation so old output
        directories retain their schema compatibility and identity checks.
        """

        self._prepare_host_resources()
        self.host._initialize()
        self._persist_resource_roots()

    @property
    def _campaign_root(self) -> Path | None:
        output = getattr(self.host, "output", None)
        if output is None:
            return None
        return Path(output).expanduser().resolve()

    @contextmanager
    def _writer_lock(self, *, wait_seconds: float = 0.0):
        """Hold the campaign mutation lock, re-entrant within one kernel."""

        root = self._campaign_root
        if root is None:
            yield
            return
        if self._writer_lock_depth:
            self._writer_lock_depth += 1
            try:
                yield
            finally:
                self._writer_lock_depth -= 1
            return
        from .campaign_jobs import (
            CampaignInterprocessLock,
            CampaignLockBusyError,
        )

        deadline = time.monotonic() + max(0.0, wait_seconds)
        while True:
            try:
                handle = CampaignInterprocessLock(root).acquire()
                break
            except CampaignLockBusyError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
        self._writer_lock_handle = handle
        self._writer_lock_depth = 1
        try:
            yield
        finally:
            self._writer_lock_depth = 0
            self._writer_lock_handle = None
            handle.release()

    @staticmethod
    def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
        encoded = (
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n"
        )
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    def _load_action_journal(self) -> dict[str, Any]:
        root = self._campaign_root
        if root is None:
            return self._memory_journal
        path = root / ACTION_JOURNAL_FILE
        if not path.exists():
            return {
                "schema_version": RUNTIME_SCHEMA_VERSION,
                "next_sequence": 1,
                "operations": {},
            }
        if path.is_symlink() or not path.is_file():
            raise ValueError("action journal is not a regular file")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema_version") != RUNTIME_SCHEMA_VERSION
            or not isinstance(payload.get("next_sequence"), int)
            or payload["next_sequence"] < 1
            or not isinstance(payload.get("operations"), dict)
        ):
            raise ValueError("invalid durable action journal")
        sequences = [
            record.get("sequence")
            for record in payload["operations"].values()
            if isinstance(record, Mapping)
        ]
        if any(not isinstance(sequence, int) or sequence < 1 for sequence in sequences):
            raise ValueError("action journal contains an invalid sequence")
        if sequences and max(sequences) >= payload["next_sequence"]:
            raise ValueError("action journal sequence is not monotonic")
        return payload

    def _persist_action_journal(self, payload: Mapping[str, Any]) -> None:
        root = self._campaign_root
        if root is None:
            self._memory_journal = dict(payload)
            return
        self._atomic_json_write(root / ACTION_JOURNAL_FILE, payload)

    def _load_budget(self) -> dict[str, Any]:
        root = self._campaign_root
        config = getattr(self.host, "config", None)
        max_actions = getattr(config, "max_iterations", None)
        max_wall = float(getattr(config, "max_wall_seconds", 21_600.0))
        max_command = float(getattr(config, "max_command_seconds", 600.0))
        defaults = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "max_actions": max_actions,
            "max_wall_seconds": max_wall,
            "max_command_seconds": max_command,
            "action_count": 0,
            "accumulated_active_seconds": 0.0,
        }
        if root is None:
            return getattr(self, "_memory_budget", defaults)
        path = root / BUDGET_FILE
        if not path.exists():
            return defaults
        if path.is_symlink() or not path.is_file():
            raise ValueError("kernel budget is not a regular file")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != RUNTIME_SCHEMA_VERSION:
            raise ValueError("invalid kernel budget schema")
        # Early v0.2 development builds stored ``started_at`` and therefore
        # charged calendar downtime. Migrate that unpublished shape without
        # charging idle time; the durable budget now records cumulative tool
        # and simulation execution only.
        if "accumulated_active_seconds" not in payload and "started_at" in payload:
            payload["accumulated_active_seconds"] = 0.0
            payload.pop("started_at", None)
        required = {
            "max_actions",
            "max_wall_seconds",
            "max_command_seconds",
            "action_count",
            "accumulated_active_seconds",
        }
        if not required.issubset(payload):
            raise ValueError("kernel budget is missing required fields")
        if not isinstance(payload["action_count"], int) or payload["action_count"] < 0:
            raise ValueError("kernel budget action_count is invalid")
        active_seconds = payload["accumulated_active_seconds"]
        if (
            isinstance(active_seconds, bool)
            or not isinstance(active_seconds, (int, float))
            or not math.isfinite(float(active_seconds))
            or float(active_seconds) < 0
        ):
            raise ValueError("kernel budget accumulated_active_seconds is invalid")
        # The manifest is the immutable source of configured limits. A changed
        # budget file must not silently widen a campaign after a restart.
        if payload["max_actions"] != max_actions:
            raise ValueError("kernel action budget does not match the run contract")
        for key, expected in (
            ("max_wall_seconds", max_wall),
            ("max_command_seconds", max_command),
        ):
            if float(payload[key]) != expected:
                raise ValueError(f"kernel budget {key} does not match the run contract")
        return payload

    def _persist_budget(self, payload: Mapping[str, Any]) -> None:
        root = self._campaign_root
        if root is None:
            self._memory_budget = dict(payload)
            return
        self._atomic_json_write(root / BUDGET_FILE, payload)

    def _ensure_runtime_files(self) -> None:
        """Create the durable journal/budget without consuming an action."""

        journal = self._load_action_journal()
        if (
            self._campaign_root is not None
            and not (self._campaign_root / ACTION_JOURNAL_FILE).exists()
        ):
            self._persist_action_journal(journal)
        budget = self._load_budget()
        if self._campaign_root is not None and not (self._campaign_root / BUDGET_FILE).exists():
            self._persist_budget(budget)

    def _persist_resource_roots(self) -> None:
        root = self._campaign_root
        if root is None:
            return
        raw = getattr(self.host, "_kernel_resource_roots", None)
        if not isinstance(raw, Mapping):
            raw = {
                "skills_root": getattr(getattr(self.host, "skills", None), "root", None),
                "capabilities_root": getattr(
                    getattr(self.host, "capabilities", None), "root", None
                ),
            }
        payload: dict[str, Any] = {"schema_version": RUNTIME_SCHEMA_VERSION}
        for key in ("skills_root", "capabilities_root"):
            value = raw.get(key)
            if value is not None:
                path = Path(value).expanduser().resolve()
                if not path.is_dir():
                    raise ValueError(f"kernel resource {key} is unavailable: {path}")
                value = str(path)
            payload[key] = value
        path = self._resource_file(root)
        if path.exists():
            existing = self._load_resource_roots(root)
            if existing != {key: payload[key] for key in ("skills_root", "capabilities_root")}:
                raise ValueError("kernel resource roots changed after campaign initialization")
            return
        self._atomic_json_write(path, payload)

    @staticmethod
    def _canonical_action(action: Any) -> dict[str, Any]:
        dumped = (
            dict(action) if isinstance(action, Mapping) else action.model_dump(mode="json")
        )
        if not isinstance(dumped, dict):
            raise TypeError("campaign action must serialize to an object")
        if dumped.get("input_artifacts") is None:
            dumped.pop("input_artifacts", None)
        return dumped

    @staticmethod
    def _operation_fingerprint(
        action_payload: Mapping[str, Any],
        timeout_seconds: float | None,
    ) -> str:
        encoded = json.dumps(
            {
                "action": dict(action_payload),
                "timeout_seconds": timeout_seconds,
            },
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _validate_operation_id(operation_id: str) -> str:
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if len(operation_id) > 256 or "\x00" in operation_id:
            raise ValueError("operation_id is invalid")
        return operation_id

    @staticmethod
    def _action_result_succeeded(result: Any) -> bool:
        if not isinstance(result, dict):
            return True
        execution = result.get("execution_result")
        if isinstance(execution, dict) and not CampaignKernel._action_result_succeeded(execution):
            return False
        return not (
            result.get("timed_out") is True
            or result.get("workspace_exceeded") is True
            or (isinstance(result.get("returncode"), int) and result["returncode"] != 0)
        )

    def _remaining_wall_seconds(self, budget: Mapping[str, Any]) -> float:
        active = float(budget.get("accumulated_active_seconds", 0.0))
        return max(0.0, float(budget["max_wall_seconds"]) - active)

    def _charge_active_seconds(self, elapsed_seconds: float) -> None:
        """Persist actual action runtime without charging process downtime."""

        elapsed = max(0.0, float(elapsed_seconds))
        if not math.isfinite(elapsed):
            raise ValueError("active budget charge must be finite")
        budget = self._load_budget()
        budget["accumulated_active_seconds"] = (
            float(budget.get("accumulated_active_seconds", 0.0)) + elapsed
        )
        self._persist_budget(budget)

    def _effective_timeout(
        self,
        requested: float | None,
        *,
        budget: Mapping[str, Any] | None = None,
    ) -> float:
        current = budget or self._load_budget()
        remaining = self._remaining_wall_seconds(current)
        if remaining <= 0:
            raise CampaignBudgetExceededError("campaign wall-clock budget is exhausted")
        max_command = float(current["max_command_seconds"])
        selected = max_command if requested is None else float(requested)
        if not math.isfinite(selected) or selected <= 0:
            raise ValueError("timeout_seconds must be positive and finite")
        return min(selected, max_command, remaining)

    def _reserve_sequence(self) -> tuple[int, dict[str, Any], dict[str, Any]]:
        journal = self._load_action_journal()
        budget = self._load_budget()
        max_actions = budget.get("max_actions")
        count = int(budget.get("action_count", 0))
        if max_actions is not None and count >= int(max_actions):
            raise CampaignBudgetExceededError("campaign action budget is exhausted")
        sequence = int(journal["next_sequence"])
        journal["next_sequence"] = sequence + 1
        budget["action_count"] = count + 1
        return sequence, journal, budget

    def _update_operation_record(
        self,
        journal: dict[str, Any],
        operation_id: str,
        *,
        status: str | None = None,
        result: Any = None,
        error: str | None = None,
        job_id: str | None = None,
    ) -> None:
        record = journal["operations"].get(operation_id)
        if not isinstance(record, dict):
            return
        if status is not None:
            record["status"] = status
        if result is not None:
            record["result"] = result
        if error is not None:
            record["error"] = error
        if job_id is not None:
            record["job_id"] = job_id
        record["updated_at"] = datetime.now(UTC).isoformat()

    def _reconcile_jobs_locked(self) -> None:
        """Receipt terminal workers while this kernel owns the writer lock."""

        if self._campaign_root is None and self._job_supervisor is None:
            return
        jobs = self._jobs()
        listing = getattr(jobs, "jobs", None)
        status_reader = getattr(jobs, "status", None)
        if not callable(listing) or not callable(status_reader):
            return
        for item in tuple(listing()):
            current = status_reader(item.job_id)
            current = self._reconcile_worker_receipt(item.job_id, current)
            current = self._reject_unverified_worker_success(current)
            if getattr(current, "status", None) is not None and current.status.terminal:
                self._refresh_durable_indexes()
                if self._should_finalize_job(current):
                    self._finalize_host_operation(
                        current.operation_id,
                        current.status.value,
                        job_id=current.job_id,
                    )
                self._sync_operation_from_job(current)

    def _finalize_host_operation(
        self,
        operation_id: str,
        status: str,
        *,
        job_id: str | None,
    ) -> None:
        callback = getattr(self.host, "_finalize_operation_provenance", None)
        if callable(callback):
            callback(operation_id, status, job_id=job_id)

    def _should_finalize_job(self, state: Any) -> bool:
        """Require an authenticated receipt before promoting worker success."""

        if getattr(getattr(state, "status", None), "value", None) != "succeeded":
            return True
        return (
            not self._job_requires_authenticated_receipt(state)
            or state.job_id in self._authenticated_worker_jobs
        )

    def _job_requires_authenticated_receipt(self, state: Any) -> bool:
        try:
            request = self._jobs().request_record(state.job_id)
        except (AttributeError, KeyError, RuntimeError, ValueError):
            return False
        metadata = getattr(request, "metadata", {})
        return all(
            isinstance(metadata.get(key), str) and metadata.get(key)
            for key in ("worker_request_sha256", "worker_result_path", "request_path")
        )

    def _reject_unverified_worker_success(self, state: Any) -> Any:
        status = getattr(getattr(state, "status", None), "value", None)
        if (
            status != "succeeded"
            or not self._job_requires_authenticated_receipt(state)
            or state.job_id in self._authenticated_worker_jobs
        ):
            return state
        reject = getattr(self._jobs(), "reject_unverified_success", None)
        if not callable(reject):
            return state
        return reject(
            state.job_id,
            detail=(
                "typed worker exited successfully without a valid authenticated "
                "receipt; scientific outcome is unknown"
            ),
        )

    def _sync_operation_from_job(self, state: Any) -> None:
        operation_id = getattr(state, "operation_id", None)
        if not isinstance(operation_id, str):
            return
        journal = self._load_action_journal()
        record = journal.get("operations", {}).get(operation_id)
        if not isinstance(record, dict):
            return
        status = getattr(getattr(state, "status", None), "value", None)
        if status is None:
            return
        result_record = None
        result_reader = getattr(self._jobs(), "result_record", None)
        if callable(result_reader):
            result_record = result_reader(state.job_id)
        result = None
        if result_record is not None and "result" not in record:
            result = result_record.model_dump(mode="json")
        self._update_operation_record(
            journal,
            operation_id,
            status=status,
            result=result,
            job_id=state.job_id,
        )
        self._persist_action_journal(journal)

    def recover_interrupted_action(self) -> None:
        """Record an unreceipted action outcome before a resumed campaign runs."""

        self.host._recover_interrupted_action()

    def perform(
        self,
        action: MVPAgentAction,
        *,
        iteration: int,
        timeout_seconds: float = 600.0,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        _operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Run one typed action with all existing MVP safety invariants.

        The compatibility method is kept on the runner for one release so
        existing callers which invoke ``runner._perform`` continue to work.
        ``MVPAgentRunner._perform`` itself is a thin delegation to this method.
        """

        action = self._normalize_action(action)
        if _operation_id is not None:
            operation_id = self._validate_operation_id(_operation_id)
            with self._writer_lock():
                self._reconcile_jobs_locked()
                try:
                    return self._execute_operation_locked(
                        operation_id,
                        action,
                        timeout_seconds=timeout_seconds,
                        progress_callback=progress_callback,
                        legacy_iteration=iteration,
                    )
                finally:
                    self._reconcile_jobs_locked()

        if self._action_mutates_campaign(action):
            with self._writer_lock():
                self._reconcile_jobs_locked()
                self._assert_writer_available()
                try:
                    return self._run_host_action(
                        action,
                        iteration=iteration,
                        timeout_seconds=timeout_seconds,
                        progress_callback=progress_callback,
                    )
                finally:
                    self._reconcile_jobs_locked()
        return self._run_host_action(
            action,
            iteration=iteration,
            timeout_seconds=timeout_seconds,
            progress_callback=progress_callback,
        )

    @staticmethod
    def _normalize_action(action: Any) -> Any:
        if isinstance(action, Mapping):
            # The MCP bridge speaks a flat JSON action while the legacy MVP
            # runner speaks frozen Pydantic action objects.  Keep the one
            # parser at this boundary so workers and synchronous callers share
            # the exact action grammar.
            from .mvp_agent import parse_mvp_action

            return parse_mvp_action(json.dumps(dict(action), separators=(",", ":")))
        return action

    def _run_host_action(
        self,
        action: Any,
        *,
        iteration: int,
        timeout_seconds: float,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        # mvp_agent records a provisional artifact operation from this
        # transient context. Restore the previous value even when the action
        # raises so a reused host cannot leak provenance between operations.
        marker = object()
        previous = getattr(self.host, "_kernel_operation_id", marker)
        if operation_id is not None:
            self.host._kernel_operation_id = operation_id
        try:
            self.host._enforce_literature_startup(action)
            return self.host._perform_compat(
                action,
                iteration=iteration,
                timeout_seconds=timeout_seconds,
                progress_callback=progress_callback,
            )
        finally:
            if operation_id is not None:
                if previous is marker:
                    with suppress(AttributeError):
                        delattr(self.host, "_kernel_operation_id")
                else:
                    self.host._kernel_operation_id = previous

    def _execute_operation_locked(
        self,
        operation_id: str,
        action: Any,
        *,
        timeout_seconds: float | None,
        progress_callback: Callable[[dict[str, Any]], None] | None,
        legacy_iteration: int | None = None,
        job_id: str | None = None,
        defer_provenance: bool = False,
    ) -> dict[str, Any]:
        action_payload = self._canonical_action(action)
        fingerprint = self._operation_fingerprint(action_payload, timeout_seconds)
        journal = self._load_action_journal()
        existing = (journal.get("operations") or {}).get(operation_id)
        if existing is not None:
            if not isinstance(existing, Mapping) or existing.get("fingerprint") != fingerprint:
                from .campaign_jobs import JobConflictError

                raise JobConflictError(
                    f"operation_id {operation_id!r} already names a different action"
                )
            existing_status = str(existing.get("status", ""))
            if existing_status in {"succeeded", "failed", "cancelled"}:
                if isinstance(existing.get("result"), Mapping):
                    return dict(existing["result"])
                if existing_status == "failed":
                    raise CampaignOperationFailedError(
                        _failed_operation_replay_message(
                            operation_id,
                            existing.get("error") or "the earlier action failed",
                        )
                    )
                raise CampaignOperationInProgressError(
                    f"operation {operation_id!r} has no durable replay result"
                )
            if existing_status == "outcome_unknown":
                raise CampaignOperationInProgressError(
                    f"operation {operation_id!r} has an unknown outcome and cannot rerun"
                )
            if job_id is None or existing.get("job_id") != job_id:
                raise CampaignOperationInProgressError(
                    f"operation {operation_id!r} is already {existing_status or 'in progress'}"
                )
            # A detached worker is the only caller allowed to claim a queued
            # supervisor operation. It must match the durable job binding.
            if existing_status not in {"submitted", "queued"}:
                raise CampaignOperationInProgressError(
                    f"operation {operation_id!r} cannot be rerun from {existing_status}"
                )
            sequence = int(existing["sequence"])
            budget = self._load_budget()
            journal["operations"][operation_id]["status"] = "running"
            journal["operations"][operation_id]["updated_at"] = datetime.now(UTC).isoformat()
            self._persist_action_journal(journal)
        else:
            if self._action_mutates_campaign(action):
                self._assert_writer_available(exclude_operation_id=operation_id)
            sequence, journal, budget = self._reserve_sequence()
            effective_timeout = self._effective_timeout(timeout_seconds, budget=budget)
            now = datetime.now(UTC).isoformat()
            journal["operations"][operation_id] = {
                "operation_id": operation_id,
                "sequence": sequence,
                "fingerprint": fingerprint,
                "action": action_payload,
                "requested_timeout_seconds": timeout_seconds,
                "effective_timeout_seconds": effective_timeout,
                "status": "running",
                "job_id": job_id,
                "created_at": now,
                "updated_at": now,
            }
            self._persist_budget(budget)
            self._persist_action_journal(journal)
        if existing is not None:
            effective_timeout = self._effective_timeout(timeout_seconds, budget=budget)
            journal["operations"][operation_id]["effective_timeout_seconds"] = effective_timeout
            self._persist_action_journal(journal)

        call_iteration = sequence if legacy_iteration is None else legacy_iteration
        try:
            result = self._run_host_action(
                action,
                iteration=call_iteration,
                timeout_seconds=effective_timeout,
                progress_callback=progress_callback,
                operation_id=operation_id,
            )
            status = "succeeded" if self._action_result_succeeded(result) else "failed"
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            self._update_operation_record(
                journal,
                operation_id,
                status="failed",
                error=detail,
                job_id=job_id,
            )
            self._persist_action_journal(journal)
            if job_id is None and not defer_provenance:
                self._finalize_host_operation(operation_id, "failed", job_id=None)
            raise
        self._update_operation_record(
            journal,
            operation_id,
            status=status,
            result=result,
            job_id=job_id,
        )
        self._persist_action_journal(journal)
        # An async worker must leave artifacts provisional until the parent
        # authenticates its receipt. Synchronous callers have no detached
        # receipt boundary, so finalize their successful outcome here.
        if job_id is None and not defer_provenance:
            self._finalize_host_operation(operation_id, status, job_id=None)
        return result

    def _prepare_detached_operation_locked(
        self,
        operation_id: str,
        action: Any,
        *,
        timeout_seconds: float | None,
        job_id: str,
    ) -> tuple[int, float, str]:
        """Claim a supervisor-reserved operation without running it under flock."""

        from .campaign_jobs import JobConflictError

        action_payload = self._canonical_action(action)
        fingerprint = self._operation_fingerprint(action_payload, timeout_seconds)
        journal = self._load_action_journal()
        record = journal.get("operations", {}).get(operation_id)
        if not isinstance(record, dict):
            raise CampaignOperationInProgressError(
                f"detached operation {operation_id!r} has no supervisor reservation"
            )
        if record.get("fingerprint") != fingerprint:
            raise JobConflictError(
                f"operation_id {operation_id!r} already names a different action"
            )
        if record.get("job_id") != job_id:
            raise CampaignOperationInProgressError(
                f"operation {operation_id!r} is bound to a different durable job"
            )
        status = str(record.get("status", ""))
        if status not in {"submitted", "queued"}:
            if status == "failed":
                raise CampaignOperationFailedError(
                    _failed_operation_replay_message(
                        operation_id,
                        record.get("error") or "the earlier action failed",
                    )
                )
            raise CampaignOperationInProgressError(
                f"operation {operation_id!r} cannot start from {status or 'unknown'}"
            )
        sequence = record.get("sequence")
        if not isinstance(sequence, int) or sequence < 1:
            raise ValueError("detached operation has an invalid durable sequence")
        budget = self._load_budget()
        effective_timeout = self._effective_timeout(timeout_seconds, budget=budget)
        record["status"] = "running"
        record["effective_timeout_seconds"] = effective_timeout
        record["updated_at"] = datetime.now(UTC).isoformat()
        self._persist_action_journal(journal)
        return sequence, effective_timeout, fingerprint

    def _finish_detached_operation_locked(
        self,
        operation_id: str,
        *,
        fingerprint: str,
        job_id: str,
        status: str,
        result: Mapping[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Persist a detached result without overwriting concurrent control actions."""

        journal = self._load_action_journal()
        record = journal.get("operations", {}).get(operation_id)
        if (
            not isinstance(record, dict)
            or record.get("fingerprint") != fingerprint
            or record.get("job_id") != job_id
        ):
            raise ValueError("detached operation reservation changed during execution")
        self._update_operation_record(
            journal,
            operation_id,
            status=status,
            result=dict(result) if result is not None else None,
            error=error,
            job_id=job_id,
        )
        self._persist_action_journal(journal)

    def _execute_detached_operation(
        self,
        operation_id: str,
        action: Any,
        *,
        timeout_seconds: float | None,
        progress_callback: Callable[[dict[str, Any]], None] | None,
        job_id: str,
    ) -> dict[str, Any]:
        """Run one leased writer job while leaving status/cancellation responsive.

        The short lock sections establish and finish durable chronology. During
        the simulation itself, the active supervisor job is the writer lease:
        every other scientific mutation acquires the campaign lock, observes
        that lease, and is rejected. Control-plane status and cancellation can
        therefore remain available without allowing a second scientific writer.
        """

        with self._writer_lock(wait_seconds=30.0):
            self._reconcile_jobs_locked()
            self._assert_writer_available(exclude_operation_id=operation_id)
            sequence, effective_timeout, fingerprint = self._prepare_detached_operation_locked(
                operation_id,
                action,
                timeout_seconds=timeout_seconds,
                job_id=job_id,
            )
        active_started = time.monotonic()
        try:
            result = self._run_host_action(
                action,
                iteration=sequence,
                timeout_seconds=effective_timeout,
                progress_callback=progress_callback,
                operation_id=operation_id,
            )
            status = "succeeded" if self._action_result_succeeded(result) else "failed"
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            with self._writer_lock(wait_seconds=30.0):
                self._finish_detached_operation_locked(
                    operation_id,
                    fingerprint=fingerprint,
                    job_id=job_id,
                    status="failed",
                    error=detail,
                )
                self._charge_active_seconds(time.monotonic() - active_started)
            raise
        with self._writer_lock(wait_seconds=30.0):
            self._finish_detached_operation_locked(
                operation_id,
                fingerprint=fingerprint,
                job_id=job_id,
                status=status,
                result=result,
            )
            self._charge_active_seconds(time.monotonic() - active_started)
        return result

    def execute_operation(
        self,
        operation_id: str,
        action: Any,
        *,
        timeout_seconds: float | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        _job_id: str | None = None,
        _defer_provenance: bool = False,
    ) -> dict[str, Any]:
        """Execute one idempotent kernel operation with a durable sequence.

        ``operation_id`` and the canonical typed action form the immutable
        request identity. A replay returns the recorded result; a conflicting
        action or an unknown/in-flight outcome is rejected and never rerun.
        Caller-supplied iteration numbers are intentionally not accepted: the
        kernel allocates the monotonic sequence persisted in ``action_journal``.
        """

        operation_id = self._validate_operation_id(operation_id)
        if isinstance(action, Mapping) and action.get("action") == "cancel_job":
            return self._execute_cancel_operation(
                operation_id,
                action,
                timeout_seconds=timeout_seconds,
            )
        action = self._normalize_action(action)
        if _job_id is not None:
            if not _defer_provenance:
                raise ValueError("detached operations must defer provenance finalization")
            return self._execute_detached_operation(
                operation_id,
                action,
                timeout_seconds=timeout_seconds,
                progress_callback=progress_callback,
                job_id=_job_id,
            )
        with self._writer_lock():
            self._reconcile_jobs_locked()
            if self._action_mutates_campaign(action):
                self._assert_writer_available(exclude_operation_id=operation_id)
            active_started = time.monotonic()
            try:
                return self._execute_operation_locked(
                    operation_id,
                    action,
                    timeout_seconds=timeout_seconds,
                    progress_callback=progress_callback,
                    job_id=_job_id,
                    defer_provenance=_defer_provenance,
                )
            finally:
                self._charge_active_seconds(time.monotonic() - active_started)
                self._reconcile_jobs_locked()

    @staticmethod
    def _adjudication_action_payload(
        *,
        claim_id: str,
        contract_version: int,
        case_for_sufficiency: str,
    ) -> dict[str, Any]:
        return {
            "action": "record_adjudication",
            "claim_id": claim_id.strip().casefold(),
            "contract_version": contract_version,
            "case_for_sufficiency": case_for_sufficiency,
        }

    @staticmethod
    def _packet_sha256(packet: Mapping[str, Any]) -> str:
        encoded = json.dumps(
            dict(packet),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def prepare_adjudication(
        self,
        operation_id: str,
        *,
        claim_id: str,
        contract_version: int,
        case_for_sufficiency: str,
    ) -> dict[str, Any]:
        """Return a bounded immutable case for a fresh independent DSH judge.

        This method does not call a model.  The operation id lets the DSH
        composite tool discover a verdict that was durably recorded before a
        transport failure, avoiding a second judge turn on retry.
        """

        operation_id = self._validate_operation_id(operation_id)
        if not isinstance(contract_version, int) or isinstance(contract_version, bool):
            raise ValueError("contract_version must be an integer")
        if contract_version < 1:
            raise ValueError("contract_version must be at least 1")
        if not isinstance(case_for_sufficiency, str) or len(case_for_sufficiency.strip()) < 16:
            raise ValueError("case_for_sufficiency must contain at least 16 characters")
        payload = self._adjudication_action_payload(
            claim_id=claim_id,
            contract_version=contract_version,
            case_for_sufficiency=case_for_sufficiency,
        )
        fingerprint = self._operation_fingerprint(payload, None)
        with self._writer_lock(wait_seconds=2.0):
            self._reconcile_jobs_locked()
            journal = self._load_action_journal()
            existing = journal.get("operations", {}).get(operation_id)
            if existing is not None:
                if not isinstance(existing, Mapping) or existing.get("fingerprint") != fingerprint:
                    from .campaign_jobs import JobConflictError

                    raise JobConflictError(
                        f"operation_id {operation_id!r} already names a different action"
                    )
                if existing.get("status") == "succeeded" and isinstance(
                    existing.get("result"), Mapping
                ):
                    return {
                        "already_recorded": True,
                        "result": dict(existing["result"]),
                    }
                if existing.get("status") == "failed":
                    raise CampaignOperationFailedError(
                        _failed_operation_replay_message(
                            operation_id,
                            existing.get("error") or "the earlier adjudication failed",
                        )
                    )
                recovered = self._recover_recorded_adjudication(operation_id)
                if recovered is not None:
                    self._update_operation_record(
                        journal,
                        operation_id,
                        status="succeeded",
                        result=recovered,
                    )
                    self._persist_action_journal(journal)
                    return {"already_recorded": True, "result": recovered}
                raise CampaignOperationInProgressError(
                    f"adjudication operation {operation_id!r} is already in progress"
                )
            self._assert_writer_available()
            selected_id, selected_version, packet = self.host._prepare_adjudication_request(
                claim_id=claim_id,
                contract_version=contract_version,
                case_for_sufficiency=case_for_sufficiency,
            )
            return {
                "already_recorded": False,
                "operation_id": operation_id,
                "claim_id": selected_id,
                "contract_version": selected_version,
                "case_sha256": self._packet_sha256(packet),
                "packet": packet,
            }

    def record_adjudication(
        self,
        operation_id: str,
        *,
        claim_id: str,
        contract_version: int,
        case_for_sufficiency: str,
        case_sha256: str,
        verdict: Mapping[str, Any],
        model: str,
        route: str,
        judge_run_id: str,
        usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Commit a structured verdict produced by the isolated DSH judge."""

        operation_id = self._validate_operation_id(operation_id)
        payload = self._adjudication_action_payload(
            claim_id=claim_id,
            contract_version=contract_version,
            case_for_sufficiency=case_for_sufficiency,
        )
        fingerprint = self._operation_fingerprint(payload, None)
        with self._writer_lock():
            self._reconcile_jobs_locked()
            self._assert_writer_available(exclude_operation_id=operation_id)
            journal = self._load_action_journal()
            existing = journal.get("operations", {}).get(operation_id)
            if existing is not None:
                if not isinstance(existing, Mapping) or existing.get("fingerprint") != fingerprint:
                    from .campaign_jobs import JobConflictError

                    raise JobConflictError(
                        f"operation_id {operation_id!r} already names a different action"
                    )
                if existing.get("status") == "succeeded" and isinstance(
                    existing.get("result"), Mapping
                ):
                    return dict(existing["result"])
                if existing.get("status") == "failed":
                    raise CampaignOperationFailedError(
                        _failed_operation_replay_message(
                            operation_id,
                            existing.get("error") or "the earlier adjudication failed",
                        )
                    )
                recovered = self._recover_recorded_adjudication(operation_id)
                if recovered is not None:
                    self._update_operation_record(
                        journal,
                        operation_id,
                        status="succeeded",
                        result=recovered,
                    )
                    self._persist_action_journal(journal)
                    return recovered
                raise CampaignOperationInProgressError(
                    f"adjudication operation {operation_id!r} is already in progress"
                )

            selected_id, selected_version, packet = self.host._prepare_adjudication_request(
                claim_id=claim_id,
                contract_version=contract_version,
                case_for_sufficiency=case_for_sufficiency,
            )
            if not isinstance(case_sha256, str) or case_sha256 != self._packet_sha256(packet):
                raise ValueError(
                    "adjudication case changed after judge preparation; prepare a fresh case"
                )
            from .mvp_agent import MVPJudgeVerdict

            parsed_verdict = MVPJudgeVerdict.model_validate(dict(verdict))
            sequence, journal, budget = self._reserve_sequence()
            now = datetime.now(UTC).isoformat()
            journal["operations"][operation_id] = {
                "operation_id": operation_id,
                "sequence": sequence,
                "fingerprint": fingerprint,
                "action": payload,
                "requested_timeout_seconds": None,
                "effective_timeout_seconds": None,
                "status": "running",
                "created_at": now,
                "updated_at": now,
            }
            self._persist_budget(budget)
            self._persist_action_journal(journal)
            active_started = time.monotonic()
            try:
                result = self.host._record_adjudication_verdict(
                    claim_id=selected_id,
                    contract_version=selected_version,
                    case_for_sufficiency=case_for_sufficiency,
                    verdict=parsed_verdict,
                    iteration=sequence,
                    model=model,
                    route=route,
                    request_id=judge_run_id,
                    usage=dict(usage or {}),
                    operation_id=operation_id,
                    case_sha256=case_sha256,
                )
                self._set_external_adjudication_loop_state(
                    claim_id=selected_id,
                    verdict=parsed_verdict,
                    iteration=sequence,
                )
            except Exception as error:
                self._update_operation_record(
                    journal,
                    operation_id,
                    status="failed",
                    error=f"{type(error).__name__}: {error}",
                )
                self._persist_action_journal(journal)
                self._charge_active_seconds(time.monotonic() - active_started)
                raise
            self._update_operation_record(
                journal,
                operation_id,
                status="succeeded",
                result=result,
            )
            self._persist_action_journal(journal)
            self._charge_active_seconds(time.monotonic() - active_started)
            return result

    def _recover_recorded_adjudication(
        self,
        operation_id: str,
    ) -> dict[str, Any] | None:
        """Receipt a verdict persisted just before its journal update."""

        records = [
            record
            for record in getattr(self.host, "_adjudications", ())
            if getattr(record, "operation_id", None) == operation_id
        ]
        if not records:
            return None
        if len(records) != 1:
            raise ValueError("adjudication operation has duplicate durable records")
        record = records[0]
        claim_id = record.verdict.claim_id
        contract_version = record.verdict.contract_version
        claim = self.claim_store.ledger.by_id().get(claim_id)
        if claim is None:
            raise ValueError("recorded adjudication references an unknown claim")

        from .mvp_agent import MVPJudgeDecision
        from .mvp_claims import ClaimDisposition

        response: dict[str, Any] = {
            "adjudication": record.model_dump(mode="json"),
        }
        if record.verdict.decision == MVPJudgeDecision.SUFFICIENT:
            disposition = record.verdict.scientific_disposition
            if disposition is None:
                # Version 0.1 persisted "sufficient" without an independent
                # scientific disposition. It is safe to replay only when that old
                # verdict was already applied to the matching supported claim.
                if not (
                    record.schema_version == "0.1.0"
                    and claim.status == ClaimDisposition.SUPPORTED
                    and claim.decisive_contract_version == contract_version
                ):
                    raise ValueError(
                        "legacy sufficient adjudication has no scientific disposition; "
                        "an open claim requires a fresh explicit adjudication"
                    )
                disposition = ClaimDisposition.SUPPORTED
            if claim.status == ClaimDisposition.OPEN:
                _selected_id, _selected_version, packet = self.host._prepare_adjudication_request(
                    claim_id=claim_id,
                    contract_version=contract_version,
                    case_for_sufficiency=record.requested_case,
                )
                if record.case_sha256 is not None and record.case_sha256 != self._packet_sha256(
                    packet
                ):
                    raise ValueError(
                        "recorded adjudication case no longer matches durable evidence"
                    )
                response["closure"] = self.claim_store.close(
                    claim_id=claim_id,
                    status=disposition,
                    reason=(
                        "Independent judge accepted a complete terminal record and "
                        f"assigned scientific disposition {disposition.value}: "
                        + record.verdict.rationale
                    ),
                    contract_version=contract_version,
                    iteration=record.iteration,
                )
            elif (
                claim.status == disposition and claim.decisive_contract_version == contract_version
            ):
                response["closure"] = {
                    "closed": claim.model_dump(mode="json"),
                    "claim_ledger": self.claim_store.ledger.compact_summary(),
                    "decisive_contract_version": contract_version,
                }
            else:
                raise ValueError(
                    "recorded adjudication scientific disposition conflicts with claim"
                )
        else:
            response["continue_required"] = True
            response["evidence_gaps"] = list(record.verdict.evidence_gaps)
            response["next_test"] = record.verdict.next_test
        self._set_external_adjudication_loop_state(
            claim_id=claim_id,
            verdict=record.verdict,
            iteration=record.iteration,
        )
        return response

    def _set_external_adjudication_loop_state(
        self,
        *,
        claim_id: str,
        verdict: Any,
        iteration: int,
    ) -> None:
        setter = getattr(self.host, "_set_loop_state", None)
        if not callable(setter):
            return
        from .mvp_agent import (
            MVPJudgeDecision,
            MVPLoopStage,
            MVPResearchRole,
        )
        from .mvp_claims import ClaimDisposition, ClaimKind

        if verdict.decision == MVPJudgeDecision.SUFFICIENT:
            disposition = verdict.scientific_disposition
            if disposition == ClaimDisposition.FALSIFIED:
                setter(
                    stage=MVPLoopStage.REPAIR,
                    role=MVPResearchRole.SCIENTIST,
                    active_claim_id=claim_id,
                    detail=(
                        "Judge accepted the counterexample record; the Scientist is "
                        "forming the smallest repair claim."
                    ),
                    iteration=iteration,
                )
                return
            open_scientific = [
                claim
                for claim in self.claim_store.ledger.claims
                if claim.kind == ClaimKind.SCIENTIFIC and claim.status == ClaimDisposition.OPEN
            ]
            if open_scientific:
                target = max(
                    open_scientific,
                    key=lambda claim: (claim.updated_iteration, claim.id),
                )
                setter(
                    stage=MVPLoopStage.FALSIFICATION,
                    role=MVPResearchRole.FALSIFIER,
                    active_claim_id=target.id,
                    detail=(
                        "One branch reached an adjudicated terminal disposition; open "
                        "scientific work remains."
                    ),
                    iteration=iteration,
                )
                return
            setter(
                stage=MVPLoopStage.COMPLETE,
                role=MVPResearchRole.JUDGE,
                active_claim_id=claim_id,
                detail=(
                    "Independent judge accepted a complete terminal record with "
                    f"disposition {getattr(disposition, 'value', disposition)}."
                ),
                iteration=iteration,
                status="completed",
            )
        else:
            setter(
                stage=MVPLoopStage.FALSIFICATION,
                role=MVPResearchRole.FALSIFIER,
                active_claim_id=claim_id,
                detail="Judge found evidence gaps; the Falsifier is continuing the search.",
                iteration=iteration,
            )

    def finalize_campaign(
        self,
        operation_id: str,
        *,
        final_answer: str,
    ) -> dict[str, Any]:
        """Write the terminal report only after the scientific finish gate passes."""

        operation_id = self._validate_operation_id(operation_id)
        if not isinstance(final_answer, str) or not final_answer.strip():
            raise ValueError("final_answer must be a non-empty string")
        if len(final_answer) > 16_384:
            raise ValueError("final_answer exceeds the 16,384-character limit")
        payload = {"action": "finalize_campaign", "final_answer": final_answer}
        fingerprint = self._operation_fingerprint(payload, None)
        with self._writer_lock():
            self._reconcile_jobs_locked()
            self._assert_writer_available(exclude_operation_id=operation_id)
            journal = self._load_action_journal()
            existing = journal.get("operations", {}).get(operation_id)
            if existing is not None:
                if not isinstance(existing, Mapping) or existing.get("fingerprint") != fingerprint:
                    from .campaign_jobs import JobConflictError

                    raise JobConflictError(
                        f"operation_id {operation_id!r} already names a different action"
                    )
                if existing.get("status") == "succeeded" and isinstance(
                    existing.get("result"), Mapping
                ):
                    return dict(existing["result"])
                if existing.get("status") == "failed":
                    raise CampaignOperationFailedError(
                        _failed_operation_replay_message(
                            operation_id,
                            existing.get("error") or "the earlier finalization failed",
                        )
                    )
                report = self._existing_terminal_report(final_answer=final_answer)
                if report is not None:
                    self._update_operation_record(
                        journal,
                        operation_id,
                        status="succeeded",
                        result=report,
                    )
                    self._persist_action_journal(journal)
                    return report
                raise CampaignOperationInProgressError(
                    f"finalization operation {operation_id!r} is already in progress"
                )

            prior_report = self._existing_terminal_report(final_answer=final_answer)
            if prior_report is not None:
                return prior_report
            gate_error = self.host._finish_gate_error()
            if gate_error is not None:
                raise ValueError(gate_error)

            # Finalization is an administrative commit, not a new scientific
            # experiment.  Allocate chronology without making an exhausted
            # action budget prevent an already-valid conclusion from being saved.
            sequence = int(journal["next_sequence"])
            journal["next_sequence"] = sequence + 1
            now = datetime.now(UTC).isoformat()
            journal["operations"][operation_id] = {
                "operation_id": operation_id,
                "sequence": sequence,
                "fingerprint": fingerprint,
                "action": payload,
                "requested_timeout_seconds": None,
                "effective_timeout_seconds": None,
                "status": "running",
                "created_at": now,
                "updated_at": now,
            }
            self._persist_action_journal(journal)
            budget = self._load_budget()
            try:
                report = self.host._write_report(
                    status="completed",
                    final_answer=final_answer,
                    iterations=max(sequence, int(budget.get("action_count", 0))),
                    started_at=datetime.now(UTC),
                    elapsed=float(budget.get("accumulated_active_seconds", 0.0)),
                ).model_dump(mode="json")
            except Exception as error:
                self._update_operation_record(
                    journal,
                    operation_id,
                    status="failed",
                    error=f"{type(error).__name__}: {error}",
                )
                self._persist_action_journal(journal)
                raise
            self._update_operation_record(
                journal,
                operation_id,
                status="succeeded",
                result=report,
            )
            self._persist_action_journal(journal)
            return report

    def _existing_terminal_report(self, *, final_answer: str) -> dict[str, Any] | None:
        path = getattr(self.host, "report_path", None)
        if path is None or not Path(path).is_file():
            return None
        from .mvp_agent import MVPAgentReport

        report = MVPAgentReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
        if report.hypothesis != self.hypothesis:
            raise ValueError("completed campaign report has a different hypothesis")
        if report.final_answer != final_answer:
            raise ValueError("campaign is already finalized with a different conclusion")
        return report.model_dump(mode="json")

    def _execute_cancel_operation(
        self,
        operation_id: str,
        action: Mapping[str, Any],
        *,
        timeout_seconds: float | None,
    ) -> dict[str, Any]:
        job_id = action.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("cancel_job operation requires a job_id")
        action_payload = {"action": "cancel_job", "job_id": job_id}
        fingerprint = self._operation_fingerprint(action_payload, timeout_seconds)
        with self._writer_lock():
            journal = self._load_action_journal()
            existing = (journal.get("operations") or {}).get(operation_id)
            if existing is not None:
                if existing.get("fingerprint") != fingerprint:
                    from .campaign_jobs import JobConflictError

                    raise JobConflictError(
                        f"operation_id {operation_id!r} already names a different action"
                    )
                if isinstance(existing.get("result"), Mapping):
                    return dict(existing["result"])
                if existing.get("status") == "failed":
                    raise CampaignOperationFailedError(
                        _failed_operation_replay_message(
                            operation_id,
                            existing.get("error") or "the earlier cancellation failed",
                        )
                    )
                raise CampaignOperationInProgressError(
                    f"operation {operation_id!r} is already in progress"
                )
            sequence, journal, budget = self._reserve_sequence()
            effective = self._effective_timeout(timeout_seconds, budget=budget)
            now = datetime.now(UTC).isoformat()
            journal["operations"][operation_id] = {
                "operation_id": operation_id,
                "sequence": sequence,
                "fingerprint": fingerprint,
                "action": action_payload,
                "requested_timeout_seconds": timeout_seconds,
                "effective_timeout_seconds": effective,
                "status": "running",
                "created_at": now,
                "updated_at": now,
            }
            self._persist_budget(budget)
            self._persist_action_journal(journal)
            active_started = time.monotonic()
            try:
                state = self.cancel_job(job_id)
            except Exception as error:
                self._update_operation_record(
                    journal,
                    operation_id,
                    status="failed",
                    error=f"{type(error).__name__}: {error}",
                )
                self._persist_action_journal(journal)
                self._charge_active_seconds(time.monotonic() - active_started)
                raise
            result = state.model_dump(mode="json") if hasattr(state, "model_dump") else dict(state)
            status = getattr(getattr(state, "status", None), "value", "failed")
            operation_status = "failed" if status in {"outcome_unknown", "failed"} else "succeeded"
            self._update_operation_record(
                journal,
                operation_id,
                status=operation_status,
                result=result,
            )
            self._persist_action_journal(journal)
            self._charge_active_seconds(time.monotonic() - active_started)
            return result

    # Named aliases are useful to non-MVP front-ends and make the safety
    # boundary discoverable without reaching into private host helpers.
    execute = perform

    def manifest(self) -> dict[str, Any]:
        """Return the immutable run identity that will be persisted."""

        return self.host._manifest()

    def snapshot(self) -> dict[str, Any]:
        """Return a read-only projection for supervisors and attachers.

        The snapshot is assembled from the same durable stores used by the
        runner.  It deliberately contains no model messages and does not infer
        scientific conclusions from process liveness.
        """

        all_states: list[Any] = []
        jobs_projection: list[dict[str, Any]] = []
        budget = self._load_budget()
        if self._campaign_root is not None or self._job_supervisor is not None:
            with self._writer_lock(wait_seconds=2.0):
                self._reconcile_jobs_locked()
                all_states = sorted(
                    self._jobs().jobs(),
                    key=lambda item: (item.created_at, item.job_id),
                )
                active_states = [state for state in all_states if not state.status.terminal]
                active_ids = {state.job_id for state in active_states}
                terminal_states = [
                    state for state in reversed(all_states) if state.job_id not in active_ids
                ]
                states = (
                    active_states
                    + terminal_states[: max(0, SNAPSHOT_MAX_JOBS - len(active_states))]
                )[:SNAPSHOT_MAX_JOBS]
                jobs_projection = [state.model_dump(mode="json") for state in states]
                budget = self._load_budget()
        max_actions = budget.get("max_actions")
        action_count = int(budget.get("action_count", 0))
        remaining_actions = None if max_actions is None else max(0, int(max_actions) - action_count)
        raw_provenance = self.host._artifact_provenance
        raw_artifacts = raw_provenance.get("artifacts", {})
        artifact_items = list(raw_artifacts.items()) if isinstance(raw_artifacts, Mapping) else []
        artifact_provenance = {
            **{key: value for key, value in raw_provenance.items() if key != "artifacts"},
            "artifact_count": len(artifact_items),
            "artifacts_truncated": len(artifact_items) > SNAPSHOT_MAX_ARTIFACTS,
            "artifacts": dict(artifact_items[-SNAPSHOT_MAX_ARTIFACTS:]),
        }
        literature_records: list[dict[str, Any]] = []
        for record in self.host._literature_searches:
            payload = record.model_dump(mode="json")
            sources = payload.pop("sources", [])
            payload["source_count"] = len(sources)
            payload["sources"] = [
                {
                    key: source.get(key)
                    for key in (
                        "id",
                        "kind",
                        "provider",
                        "title",
                        "publication_year",
                        "doi",
                        "url",
                    )
                }
                for source in sources[:5]
            ]
            literature_records.append(payload)
        claim_store = self.claim_store
        return {
            "hypothesis": self.hypothesis,
            "manifest": self.manifest(),
            "claim_ledger": claim_store.ledger.compact_summary(max_claims=12),
            "skill_hashes": dict(self.skills.hashes),
            "capability_hashes": dict(self.capabilities.hashes),
            "artifact_provenance": artifact_provenance,
            "literature_search_count": len(literature_records),
            "literature_searches_truncated": (
                len(literature_records) > SNAPSHOT_MAX_LITERATURE_SEARCHES
            ),
            "literature_searches": literature_records[-SNAPSHOT_MAX_LITERATURE_SEARCHES:],
            "job_count": len(all_states),
            "jobs_truncated": len(all_states) > len(jobs_projection),
            "jobs": jobs_projection,
            "budget": {
                "max_actions": max_actions,
                "action_count": action_count,
                "remaining_actions": remaining_actions,
                "max_wall_seconds": float(budget["max_wall_seconds"]),
                "accumulated_active_seconds": float(budget.get("accumulated_active_seconds", 0.0)),
                "remaining_wall_seconds": self._remaining_wall_seconds(budget),
                "max_command_seconds": float(budget["max_command_seconds"]),
            },
        }

    def enforce_startup(self, action: MVPAgentAction) -> None:
        """Apply the literature startup gate for a prospective action."""

        self.host._enforce_literature_startup(action)

    @staticmethod
    def _action_mutates_campaign(action: MVPAgentAction) -> bool:
        """Return whether an action can write campaign or claim state."""

        from .mvp_agent import MVPActionKind

        return action.action in {
            MVPActionKind.SEARCH_LITERATURE,
            MVPActionKind.WRITE_FILE,
            MVPActionKind.RUN_PYTHON,
            MVPActionKind.MATERIALIZE_SKILL_RESOURCE,
            MVPActionKind.RUN_CAPABILITY,
            MVPActionKind.AUTHOR_AND_RUN_CAPABILITY,
            MVPActionKind.REGISTER_CLAIM,
            MVPActionKind.REGISTER_EVIDENCE_CONTRACT,
            MVPActionKind.LINK_CLAIM_EVIDENCE,
            MVPActionKind.CLOSE_CLAIM,
            MVPActionKind.REQUEST_ADJUDICATION,
        }

    def _active_job_states(self, *, exclude_operation_id: str | None = None) -> tuple[Any, ...]:
        if self._campaign_root is None and self._job_supervisor is None:
            return ()
        jobs = self._jobs()
        listing = getattr(jobs, "jobs", None)
        if not callable(listing):
            return ()
        return tuple(
            state
            for state in listing()
            if not state.status.terminal
            and (exclude_operation_id is None or state.operation_id != exclude_operation_id)
        )

    def _assert_writer_available(self, *, exclude_operation_id: str | None = None) -> None:
        active = self._active_job_states(exclude_operation_id=exclude_operation_id)
        if active:
            operations = ", ".join(str(state.operation_id) for state in active)
            raise CampaignWriterBusyError(
                "campaign has a non-terminal durable writer job "
                f"({operations}); reconcile or cancel it before a mutating action"
            )

    def _refresh_durable_indexes(self) -> None:
        """Reload worker-written indexes before the parent mutates or observes.

        Workers write each JSON index atomically.  A parent kernel, however,
        keeps in-memory projections for fast claim/provenance validation.  The
        refresh is performed only after a terminal job receipt, when the
        worker is no longer a writer and the one-writer rule makes replacing
        these projections safe.
        """

        for attribute, loader_name in (
            ("_artifact_provenance", "_load_artifact_provenance"),
            ("_capability_preflights", "_load_capability_preflights"),
            ("_literature_searches", "_load_literature_searches"),
        ):
            loader = getattr(self.host, loader_name, None)
            if callable(loader):
                setattr(self.host, attribute, loader())
        claim_store = getattr(self.host, "claim_store", None)
        reload_ledger = getattr(claim_store, "_load_or_create", None)
        if callable(reload_ledger):
            claim_store._ledger = reload_ledger()

    # ---- durable action jobs ---------------------------------------------

    def _jobs(self) -> Any:
        if self._job_supervisor is None:
            from .campaign_jobs import CampaignJobSupervisor

            output = getattr(self.host, "output", None)
            if output is None:
                raise RuntimeError("CampaignKernel host has no output directory for durable jobs")
            self._job_supervisor = CampaignJobSupervisor(Path(output) / "jobs")
        return self._job_supervisor

    @staticmethod
    def _worker_handshake_path(request_path: Path) -> Path:
        return request_path.with_suffix(".handshake.json")

    def _write_worker_handshake(self, path: Path, payload: Mapping[str, Any]) -> None:
        self._atomic_json_write(path, payload)

    def start_job(self, request: Mapping[str, Any] | Any) -> Any:
        """Submit one typed sandbox action behind a durable worker handshake."""

        from .campaign_jobs import (
            KERNEL_WORKER_SCHEMA_VERSION,
            CampaignJobRequest,
            CampaignJobStatus,
            JobConflictError,
            kernel_worker_request_sha256,
            kernel_worker_result_path,
        )
        from .mvp_agent import parse_mvp_action

        if not isinstance(request, Mapping):
            raise TypeError(
                "CampaignKernel.start_job accepts only a typed action mapping; "
                "use CampaignJobSupervisor directly for internal process tests"
            )
        payload = dict(request)
        raw_operation_id = str(payload.pop("operation_id", "") or "")
        if not raw_operation_id:
            raw_operation_id = (
                "op_"
                + hashlib.sha256(
                    json.dumps(
                        {key: value for key, value in payload.items() if key != "iteration"},
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()[:32]
            )
        operation_id = self._validate_operation_id(raw_operation_id)
        raw_argv = payload.get("argv", ())
        if isinstance(raw_argv, (str, bytes)) or not isinstance(raw_argv, (list, tuple)):
            raise ValueError("job request argv must be a list of strings")
        if any(not isinstance(item, str) or not item for item in raw_argv):
            raise ValueError("job request argv must contain non-empty strings")
        original_argv = tuple(raw_argv)
        if not original_argv:
            raise ValueError("job request requires a non-empty argv")
        kind = str(payload.get("kind", "python"))
        if getattr(self.host, "sandbox", None) is None:
            raise RuntimeError("typed action jobs require a sandboxed campaign host")
        research_note = str(payload.get("research_note", f"DSH job: {kind}"))
        if kind == "python":
            action_payload = {
                "action": "run_python",
                "research_note": research_note,
                "argv": list(original_argv),
                "active_claim_id": payload.get("active_claim_id"),
            }
        elif kind == "capability":
            action_payload = {
                "action": "run_capability",
                "research_note": research_note,
                "capability": str(payload.get("capability", "")),
                "argv": list(original_argv),
                "stage": str(payload.get("stage", "workbench")),
                "active_claim_id": payload.get("active_claim_id"),
            }
        else:
            raise ValueError("job kind must be 'python' or 'capability'")
        if "input_artifacts" in payload:
            action_payload["input_artifacts"] = payload["input_artifacts"]
        action = parse_mvp_action(json.dumps(action_payload, separators=(",", ":")))
        canonical_action = self._canonical_action(action)
        raw_timeout = payload.get("timeout_seconds")
        if raw_timeout is not None:
            if (
                isinstance(raw_timeout, bool)
                or not isinstance(raw_timeout, (int, float))
                or not math.isfinite(float(raw_timeout))
                or float(raw_timeout) <= 0
            ):
                raise ValueError("job request timeout_seconds must be positive and finite")
            requested_timeout: float | None = float(raw_timeout)
        else:
            requested_timeout = None
        output = Path(self.host.output).expanduser().resolve()
        operation_key = hashlib.sha256(operation_id.encode()).hexdigest()[:32]
        request_directory = output / "kernel_jobs"
        request_path = request_directory / f"{operation_key}.json"
        handshake_path = self._worker_handshake_path(request_path)
        worker_payload = {
            "schema_version": KERNEL_WORKER_SCHEMA_VERSION,
            "operation_id": operation_id,
            "campaign": str(output),
            "timeout_seconds": requested_timeout,
            "action": canonical_action,
        }
        worker_digest = kernel_worker_request_sha256(worker_payload)
        worker_payload["worker_request_sha256"] = worker_digest
        result_path = kernel_worker_result_path(request_path)
        command = (
            sys.executable,
            "-m",
            "conjecture_solver.kernel_worker",
            "--request",
            str(request_path),
            "--campaign",
            str(output),
            "--handshake",
            str(handshake_path),
        )
        # Caller iteration is deliberately excluded: sequence allocation is a
        # kernel-owned durable concern, not an MCP-provided ordering hint.
        metadata = {
            **{key: value for key, value in payload.items() if key != "iteration"},
            "kind": kind,
            "action": canonical_action,
            "request_path": str(request_path),
            "worker_request_sha256": worker_digest,
            "worker_result_path": str(result_path),
            "handshake_path": str(handshake_path),
            "requested_timeout_seconds": requested_timeout,
        }
        with self._writer_lock():
            jobs = self._jobs()
            reload_operations = getattr(jobs, "_load_operation_index", None)
            if callable(reload_operations):
                jobs._operations = reload_operations()
            self._reconcile_jobs_locked()
            existing_job_id = getattr(jobs, "_operations", {}).get(operation_id)
            if existing_job_id is not None:
                existing_request = jobs.request_record(existing_job_id)
                existing_metadata = existing_request.metadata
                if (
                    existing_metadata.get("action") != canonical_action
                    or existing_metadata.get("requested_timeout_seconds") != requested_timeout
                ):
                    raise JobConflictError(
                        f"operation_id {operation_id!r} already names a different request"
                    )
                return self.job_status(existing_job_id)
            journal = self._load_action_journal()
            fingerprint = self._operation_fingerprint(
                canonical_action, requested_timeout
            )
            existing_record = (journal.get("operations") or {}).get(operation_id)
            if existing_record is not None:
                if existing_record.get("fingerprint") != fingerprint:
                    raise JobConflictError(
                        f"operation_id {operation_id!r} already names a different action"
                    )
                recorded_job = existing_record.get("job_id")
                if isinstance(recorded_job, str) and recorded_job:
                    return self.job_status(recorded_job)
                raise CampaignOperationInProgressError(
                    f"operation {operation_id!r} was durably submitted and cannot rerun"
                )
            self._assert_writer_available(exclude_operation_id=operation_id)
            budget = self._load_budget()
            effective_timeout = self._effective_timeout(requested_timeout, budget=budget)
            sequence, journal, budget = self._reserve_sequence()
            now = datetime.now(UTC).isoformat()
            journal["operations"][operation_id] = {
                "operation_id": operation_id,
                "sequence": sequence,
                "fingerprint": fingerprint,
                "action": canonical_action,
                "requested_timeout_seconds": requested_timeout,
                "effective_timeout_seconds": effective_timeout,
                "status": "submitted",
                "job_id": None,
                "created_at": now,
                "updated_at": now,
            }
            self._persist_budget(budget)
            self._persist_action_journal(journal)
            request_directory.mkdir(parents=True, exist_ok=True)
            self._atomic_json_write(request_path, worker_payload)
            desired_request = CampaignJobRequest(
                operation_id=operation_id,
                argv=command,
                cwd=str(output),
                timeout_seconds=effective_timeout,
                metadata=metadata,
            )
            state = jobs.start(request=desired_request)
            job_id = getattr(state, "job_id", None)
            if job_id is None and isinstance(state, Mapping):
                job_id = state.get("job_id")
            status = getattr(getattr(state, "status", None), "value", None)
            if status is None and isinstance(state, Mapping):
                status = state.get("status")
            journal = self._load_action_journal()
            record = journal["operations"].get(operation_id)
            if isinstance(record, dict):
                record["job_id"] = job_id
                record["status"] = status if status in {"failed", "cancelled"} else "queued"
                record["updated_at"] = datetime.now(UTC).isoformat()
            self._persist_action_journal(journal)
            supervisor = (
                getattr(jobs, "supervisor_record", lambda _job: None)(job_id) if job_id else None
            )
            if (
                supervisor is not None
                and status not in {"failed", "cancelled"}
                and hasattr(supervisor, "identity")
            ):
                handshake = {
                    "schema_version": KERNEL_WORKER_SCHEMA_VERSION,
                    "job_id": job_id,
                    "operation_id": operation_id,
                    "request_path": str(request_path),
                    "request_sha256": desired_request.request_sha256,
                    "worker_request_sha256": worker_digest,
                    "state_status": status or CampaignJobStatus.RUNNING.value,
                    "identity": supervisor.identity.model_dump(mode="json"),
                }
                self._write_worker_handshake(handshake_path, handshake)
            return state

    def _reconcile_worker_receipt(self, job_id: str, state: Any) -> Any:
        """Recover a known worker outcome after the MCP supervisor restarts."""

        from .campaign_jobs import (
            KERNEL_WORKER_SCHEMA_VERSION,
            CampaignJobStatus,
            kernel_worker_request_sha256,
            kernel_worker_result_path,
        )

        if getattr(state, "status", None) not in {
            CampaignJobStatus.OUTCOME_UNKNOWN,
            CampaignJobStatus.SUCCEEDED,
            CampaignJobStatus.FAILED,
            CampaignJobStatus.CANCELLED,
        }:
            return state
        jobs = self._jobs()
        request = jobs.request_record(job_id)
        metadata = request.metadata
        raw_request_path = metadata.get("request_path")
        raw_result_path = metadata.get("worker_result_path")
        expected_digest = metadata.get("worker_request_sha256")
        if not all(
            isinstance(value, str) and value
            for value in (raw_request_path, raw_result_path, expected_digest)
        ):
            return state
        output = Path(self.host.output).resolve()
        kernel_jobs = output / "kernel_jobs"
        request_path = Path(raw_request_path).expanduser()
        result_path = Path(raw_result_path).expanduser()
        if request_path.is_symlink() or result_path.is_symlink():
            return state
        request_path = request_path.resolve()
        result_path = result_path.resolve()
        if (
            not request_path.is_relative_to(kernel_jobs)
            or not result_path.is_relative_to(kernel_jobs)
            or result_path != kernel_worker_result_path(request_path)
            or not request_path.is_file()
            or not result_path.is_file()
            or result_path.stat().st_size > 4_000_000
        ):
            return state
        try:
            worker_request = json.loads(request_path.read_text(encoding="utf-8"))
            worker_receipt = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return state
        if not isinstance(worker_request, dict) or not isinstance(worker_receipt, dict):
            return state
        action = metadata.get("action")
        expected_action = action.get("action") if isinstance(action, Mapping) else None
        if (
            worker_request.get("schema_version") != KERNEL_WORKER_SCHEMA_VERSION
            or worker_request.get("worker_request_sha256") != expected_digest
            or kernel_worker_request_sha256(worker_request) != expected_digest
            or worker_receipt.get("schema_version") != KERNEL_WORKER_SCHEMA_VERSION
            or worker_receipt.get("worker_request_sha256") != expected_digest
            or worker_receipt.get("operation_id") != request.operation_id
            or worker_receipt.get("action") != expected_action
            or not isinstance(worker_receipt.get("ok"), bool)
            or not isinstance(worker_receipt.get("action_executed"), bool)
            or (
                worker_receipt.get("ok") is True
                and worker_receipt.get("action_executed") is not True
            )
        ):
            return state
        self._authenticated_worker_jobs.add(job_id)
        updated = state
        if state.status == CampaignJobStatus.OUTCOME_UNKNOWN:
            receipt_text = json.dumps(
                worker_receipt,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            updated = jobs.accept_external_result(
                job_id,
                returncode=0 if worker_receipt["ok"] else 1,
                detail="reconciled from authenticated durable kernel-worker receipt",
                receipt_text=receipt_text,
            )
        journal = self._load_action_journal()
        record = journal.get("operations", {}).get(request.operation_id)
        if isinstance(record, dict):
            record["job_id"] = job_id
            record["status"] = updated.status.value
            if isinstance(worker_receipt.get("result"), Mapping):
                record["result"] = worker_receipt["result"]
            record["updated_at"] = datetime.now(UTC).isoformat()
            self._persist_action_journal(journal)
        return updated

    def job_status(self, job_id: str) -> Any:
        """Reconcile and return one durable action job."""

        # A non-terminal supervisor state is a small control-plane record and
        # does not mutate any scientific campaign index.  Reading it before the
        # campaign lock keeps ordinary polling responsive while another process
        # performs a short startup/finalization mutation.  Terminal transitions
        # still take the lock before authenticating receipts and refreshing
        # scientific state.
        state = self._jobs().status(job_id)
        if not state.status.terminal:
            return state

        with self._writer_lock(wait_seconds=2.0):
            # Re-read after acquiring the lock: another reconciler may have
            # completed or corrected the durable lifecycle meanwhile.
            state = self._jobs().status(job_id)
            state = self._reconcile_worker_receipt(job_id, state)
            state = self._reject_unverified_worker_success(state)
            if getattr(state, "status", None) is not None and state.status.terminal:
                self._refresh_durable_indexes()
                if self._should_finalize_job(state):
                    self._finalize_host_operation(
                        state.operation_id,
                        state.status.value,
                        job_id=state.job_id,
                    )
                self._sync_operation_from_job(state)
        return state

    @staticmethod
    def _job_stream_summary(text: str, *, tail_chars: int = 4_000) -> dict[str, Any]:
        """Keep failure context visible without flooding an MCP response."""

        return {
            "characters": len(text),
            "truncated": len(text) > tail_chars,
            "tail": text[-tail_chars:],
        }

    @classmethod
    def _compact_job_value(cls, value: Any, *, depth: int = 0) -> Any:
        """Bound a worker receipt while preserving status and artifact metadata."""

        if depth > 8:
            return "... depth truncated ..."
        if isinstance(value, Mapping):
            compact: dict[str, Any] = {}
            for key, item in list(value.items())[:200]:
                name = str(key)
                if name in {"stdout", "stderr"} and isinstance(item, str):
                    compact[name] = cls._job_stream_summary(item)
                else:
                    compact[name] = cls._compact_job_value(item, depth=depth + 1)
            return compact
        if isinstance(value, (list, tuple)):
            return [cls._compact_job_value(item, depth=depth + 1) for item in value[:200]]
        if isinstance(value, str) and len(value) > 4_000:
            return cls._job_stream_summary(value)
        if isinstance(value, Path):
            return value.as_posix()
        return value

    def job_report(self, job_id: str) -> dict[str, Any]:
        """Return bounded lifecycle, request identity, and diagnostic output.

        ``job_status`` remains the small internal/recovery API. MCP callers need
        enough information to diagnose a failed simulation, so this view keeps
        the state fields at the top level and adds bounded terminal details.
        """

        jobs = self._jobs()
        state = self.job_status(job_id)
        request = jobs.request_record(job_id)
        receipt = jobs.result_record(job_id)
        report = state.model_dump(mode="json")
        metadata = request.metadata
        report["request"] = {
            "request_sha256": request.request_sha256,
            "timeout_seconds": request.timeout_seconds,
            "kind": metadata.get("kind"),
            "capability": metadata.get("capability"),
            "stage": metadata.get("stage"),
            "action": self._compact_job_value(metadata.get("action")),
        }
        if receipt is not None:
            report["result"] = {
                "status": receipt.status.value,
                "outcome": receipt.outcome.value if receipt.outcome is not None else None,
                "returncode": receipt.returncode,
                "timed_out": receipt.timed_out,
                "started_at": receipt.started_at,
                "finished_at": receipt.finished_at,
                "detail": receipt.detail,
                "stdout": self._job_stream_summary(receipt.stdout),
                "stderr": self._job_stream_summary(receipt.stderr),
            }
            for line in reversed(receipt.stdout.splitlines()):
                if not line.startswith("{"):
                    continue
                try:
                    worker_receipt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(worker_receipt, dict) and "ok" in worker_receipt:
                    report["worker_receipt"] = self._compact_job_value(worker_receipt)
                    break
        return report

    def record_terminal_observation(
        self,
        operation_id: str,
        *,
        claim_id: str,
        contract_version: int,
        job_ids: list[str],
        path: str,
        alternatives_considered: list[str],
        feasibility_assessment: str,
    ) -> dict[str, Any]:
        """Materialize a receipt-backed observation for a terminal contract.

        Failed scientific jobs cannot be treated as successful scientific
        evidence, but their authenticated receipts are exactly the facts an
        independent judge needs to distinguish an instrument/resource limit
        from an unresolved scientific result.  This boundary copies only
        kernel-verified lifecycle facts into a fresh, successful sandbox
        artifact.  Researcher judgments about alternative tests remain
        explicitly labelled and are never presented as kernel-verified facts.
        """

        from .mvp_claims import ClaimDisposition, ClaimKind, EvidencePurpose

        operation_id = self._validate_operation_id(operation_id)
        normalized_claim_id = claim_id.strip().casefold()
        if not normalized_claim_id:
            raise ValueError("claim_id must be non-empty")
        if (
            not isinstance(contract_version, int)
            or isinstance(contract_version, bool)
            or contract_version < 1
        ):
            raise ValueError("contract_version must be a positive integer")
        if not job_ids or len(job_ids) > 16 or len(set(job_ids)) != len(job_ids):
            raise ValueError("job_ids must contain 1 to 16 unique durable job ids")
        if any(not isinstance(job_id, str) or not job_id for job_id in job_ids):
            raise ValueError("job_ids must contain non-empty strings")
        if not alternatives_considered or len(alternatives_considered) > 16:
            raise ValueError("alternatives_considered must contain 1 to 16 entries")
        if any(
            not isinstance(item, str) or not item.strip() or len(item) > 2_000
            for item in alternatives_considered
        ):
            raise ValueError(
                "alternatives_considered entries must contain 1 to 2,000 characters"
            )
        if (
            not isinstance(feasibility_assessment, str)
            or len(feasibility_assessment.strip()) < 16
            or len(feasibility_assessment) > 8_000
        ):
            raise ValueError(
                "feasibility_assessment must contain 16 to 8,000 characters"
            )

        # Reconcile each receipt before taking the campaign writer lock.  The
        # terminal reports are immutable after reconciliation, while avoiding
        # recursive lock acquisition through job_status().
        reports = {job_id: self.job_report(job_id) for job_id in job_ids}
        terminal_statuses = {"succeeded", "failed", "cancelled", "outcome_unknown"}
        nonterminal = [
            job_id
            for job_id, report in reports.items()
            if report.get("status") not in terminal_statuses
        ]
        if nonterminal:
            raise ValueError(
                "terminal observations require terminal durable jobs; still active: "
                + ", ".join(nonterminal)
            )

        with self._writer_lock():
            self._reconcile_jobs_locked()
            self._assert_writer_available(exclude_operation_id=operation_id)
            claim = self.claim_store.ledger.by_id().get(normalized_claim_id)
            if claim is None:
                raise ValueError(f"unknown claim_id: {normalized_claim_id}")
            if claim.kind != ClaimKind.SCIENTIFIC:
                raise ValueError("terminal observations are valid only for scientific claims")
            contracts = {contract.version: contract for contract in claim.evidence_contracts}
            selected_contract = contracts.get(contract_version)
            if selected_contract is None:
                raise ValueError(
                    f"claim {normalized_claim_id} has no evidence contract "
                    f"version {contract_version}"
                )
            if selected_contract.evidence_purpose != EvidencePurpose.TERMINAL_RECORD:
                raise ValueError(
                    "record_terminal_observation requires a terminal_record contract"
                )

            journal = self._load_action_journal()
            is_replay = operation_id in (journal.get("operations") or {})
            if not is_replay:
                if claim.status != ClaimDisposition.OPEN:
                    raise ValueError(f"claim is already closed: {normalized_claim_id}")
                if claim.evidence_contracts[-1].version != contract_version:
                    raise ValueError(
                        "terminal observations require the newest active evidence contract"
                    )
                try:
                    self.host.sandbox.artifact_metadata(path)
                except ValueError:
                    pass
                else:
                    raise ValueError(
                        "terminal observation path already exists; use a fresh path"
                    )

            linked_attempts: dict[str, tuple[Any, Any]] = {}
            for evidence in claim.evidence:
                provenance = evidence.provenance
                prior_contract = contracts.get(evidence.contract_version)
                if (
                    provenance is None
                    or provenance.job_id not in reports
                    or prior_contract is None
                    or prior_contract.evidence_purpose != EvidencePurpose.CLAIM_DECISION
                    or not provenance.tracked
                    or provenance.generated_iteration is None
                    or provenance.generated_iteration <= prior_contract.registered_iteration
                ):
                    continue
                linked_attempts[provenance.job_id] = (evidence, prior_contract)
            missing_links = sorted(set(job_ids) - set(linked_attempts))
            if missing_links:
                raise ValueError(
                    "terminal jobs must already be linked as prospective attempts "
                    "under a prior claim_decision contract: "
                    + ", ".join(missing_links)
                )

            attempts: list[dict[str, Any]] = []
            any_failed = False
            any_timed_out = False
            for job_id in job_ids:
                evidence, prior_contract = linked_attempts[job_id]
                provenance = evidence.provenance
                assert provenance is not None
                report = reports[job_id]
                canonical_report = json.dumps(
                    report,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
                result = report.get("result")
                result = result if isinstance(result, Mapping) else {}
                timed_out = bool(
                    result.get("timed_out") is True
                    or provenance.execution_timed_out is True
                )
                execution_succeeded = provenance.execution_succeeded is True
                any_timed_out = any_timed_out or timed_out
                any_failed = any_failed or not execution_succeeded
                attempts.append(
                    {
                        "evidence_path": evidence.path,
                        "decision_contract_version": prior_contract.version,
                        "observation_sufficient": evidence.observation_sufficient,
                        "job_id": job_id,
                        "operation_id": provenance.operation_id,
                        "job_report_sha256": hashlib.sha256(
                            canonical_report.encode()
                        ).hexdigest(),
                        "status": report.get("status"),
                        "request": report.get("request"),
                        "result": {
                            "status": result.get("status"),
                            "outcome": result.get("outcome"),
                            "returncode": result.get("returncode"),
                            "timed_out": result.get("timed_out"),
                            "started_at": result.get("started_at"),
                            "finished_at": result.get("finished_at"),
                            "detail": result.get("detail"),
                        },
                        "linked_provenance": {
                            "tracked": provenance.tracked,
                            "evidence_eligible": provenance.evidence_eligible,
                            "execution_succeeded": provenance.execution_succeeded,
                            "execution_returncode": provenance.execution_returncode,
                            "execution_timed_out": provenance.execution_timed_out,
                            "execution_workspace_exceeded": (
                                provenance.execution_workspace_exceeded
                            ),
                            "execution_stage": provenance.execution_stage,
                            "capability": provenance.capability,
                            "program_path": provenance.program_path,
                            "program_sha256": provenance.program_sha256,
                            "command_argv": list(provenance.command_argv),
                        },
                    }
                )

            if any_timed_out:
                terminal_cause = "resource_or_command_cap"
            elif any_failed:
                terminal_cause = "execution_or_instrument_failure"
            else:
                terminal_cause = "completed_but_scientifically_indecisive"
            budget = self._load_budget()
            document = {
                "schema_version": "0.1.0",
                "record_kind": "kernel_authenticated_terminal_observation",
                "record_complete": True,
                "claim_id": normalized_claim_id,
                "terminal_contract_version": contract_version,
                "prior_decision_contract_versions": sorted(
                    {item[1].version for item in linked_attempts.values()}
                ),
                "kernel_verified": {
                    "selected_jobs_all_terminal": True,
                    "attempt_count": len(attempts),
                    "terminal_cause": terminal_cause,
                    "required_observation_complete": not any_failed,
                    "claim_tested": False if any_failed else None,
                    "attempts": attempts,
                    "configured_limits": {
                        "max_actions": (
                            None
                            if budget["max_actions"] is None
                            else int(budget["max_actions"])
                        ),
                        "max_wall_seconds": float(budget["max_wall_seconds"]),
                        "max_command_seconds": float(budget["max_command_seconds"]),
                    },
                },
                "researcher_assessment": {
                    "verified_by_kernel": False,
                    "alternatives_considered": [
                        item.strip() for item in alternatives_considered
                    ],
                    "feasibility_assessment": feasibility_assessment.strip(),
                },
                "scientific_disposition": None,
                "judge_required": True,
            }
            encoded = json.dumps(
                document,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
                default=str,
            ) + "\n"
            program = (
                "from pathlib import Path\n"
                f"target = Path({path!r})\n"
                "target.parent.mkdir(parents=True, exist_ok=True)\n"
                f"target.write_text({encoded!r}, encoding='utf-8')\n"
            )
            action = {
                "action": "run_python",
                "research_note": (
                    "Materialize the kernel-authenticated terminal observation "
                    "after its prospective terminal_record contract."
                ),
                "argv": ["-c", program],
                "active_claim_id": normalized_claim_id,
                "input_artifacts": [],
            }
            result = self._execute_operation_locked(
                operation_id,
                self._normalize_action(action),
                timeout_seconds=30.0,
                progress_callback=None,
            )
            metadata = self.host.sandbox.artifact_metadata(path)
            provenance = self.host._evidence_provenance(metadata)
            if not (
                provenance.tracked
                and provenance.evidence_eligible
                and provenance.execution_succeeded is True
                and provenance.generated_iteration is not None
                and provenance.generated_iteration > selected_contract.registered_iteration
            ):
                raise ValueError(
                    "kernel-generated terminal observation did not retain fresh "
                    "evidence-eligible provenance"
                )
            return {
                "path": path,
                "sha256": metadata["sha256"],
                "bytes": metadata["bytes"],
                "claim_id": normalized_claim_id,
                "contract_version": contract_version,
                "terminal_cause": terminal_cause,
                "job_ids": list(job_ids),
                "execution": {
                    "returncode": result.get("returncode"),
                    "timed_out": result.get("timed_out"),
                    "scientific_evidence_eligible": result.get(
                        "scientific_evidence_eligible"
                    ),
                },
            }

    def cancel_job(self, job_id: str) -> Any:
        """Cancel one job only after its persisted process identity verifies."""

        return self._jobs().cancel(job_id)
