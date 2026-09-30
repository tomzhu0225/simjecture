"""Shared, bounded numerical execution for local and SSH workers."""

from pathlib import Path

from .mvp_agent import BubblewrapSandbox, MVPAgentConfig, MVPArtifactInput
from .mvp_skills import MVPCapabilityRegistry


def execute_frozen(
    workspace,
    binding,
    outputs,
    *,
    timeout,
    execution_backend,
    capabilities=None,
    max_workspace_bytes=4 * 1024**3,
    max_memory_bytes=4 * 1024**3,
    gpu_ids=None,
    cpus=None,
):
    from .research_audit import output_findings
    from .research_service import sha

    workspace = Path(workspace)
    registry = (
        MVPCapabilityRegistry.discover(capabilities) if capabilities else MVPCapabilityRegistry()
    )
    capability = binding.get("worker_capability", binding["capability"])
    if capability and registry.get(capability).contract_hash != binding["runtime_sha256"]:
        raise ValueError("Runtime changed before execution")
    sandbox = BubblewrapSandbox(
        workspace,
        MVPAgentConfig(
            execution_backend=execution_backend,
            max_command_seconds=timeout,
            max_workspace_bytes=max_workspace_bytes,
            max_file_bytes=512 * 1024**2,
            max_memory_bytes=max_memory_bytes,
        ),
        registry,
    )
    sandbox.assigned_gpu_ids = gpu_ids
    sandbox.assigned_cpus = cpus
    function = sandbox.run_capability if capability else sandbox.run_python
    args = ((capability,) if capability else ()) + (tuple([binding["source"], *binding["args"]]),)
    result = function(
        *args,
        input_artifacts=tuple(
            MVPArtifactInput(path=p, sha256=h)
            for p, h in binding["inputs"].items()
            if p != binding["source"]
        ),
        program_path=binding["source"],
        program_sha256=binding["inputs"][binding["source"]],
        timeout_seconds=timeout,
    )
    artifacts = {
        str(p.relative_to(workspace)): {"sha256": sha(p), "bytes": p.stat().st_size}
        for p in sorted(workspace.rglob("*"))
        if p.is_file() and not p.is_symlink()
    }
    absent = [p for p in outputs if p not in artifacts]
    mutated = [
        p
        for p, checksum in binding["inputs"].items()
        if artifacts.get(p, {}).get("sha256") != checksum
    ]
    success = (
        not mutated
        and result.returncode == 0
        and not result.timed_out
        and not result.workspace_exceeded
        and not absent
    )
    return {
        "execution": result.model_dump(mode="json"),
        "artifacts": artifacts,
        "missing_outputs": absent,
        "input_mutations": mutated,
        "output_findings": output_findings(workspace, outputs),
        "scientific_status": "unreviewed",
        "status": "succeeded" if success else "failed",
    }
