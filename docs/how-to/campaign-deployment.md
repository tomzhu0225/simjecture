# Plan and check a campaign deployment

A campaign may need a coordinator, several numerical workers, private solver
builds and tables, prior evidence, and a separately hosted attention service.
A deployment manifest records those requirements in one place. The checker uses
the existing machine registry and produces a preparation report with per-item
results, observed identities, and next actions.

This is an operator tool. It does not install software, copy inputs, start model
services, invoke research agents, create a study, or start its clock. A `ready`
report means the declared operational checks passed at that moment. It grants no
launch authorization or scientific qualification.

## Existing preparation tools

First use [machine preparation](ssh-workers.md), [runtime installation](deploy-runtimes.md)
and, when needed, **Machines → Prepare with agent** to provision the actual host.
Keep scientific commissioning under the ordinary methods-review workflow. Reuse
existing runtimes or create separately identified builds; changing a deployment
manifest does not authorize reconfiguring workers used by active studies.

The manifest refers to registered machine IDs, so SSH credentials stay in the
registry's private storage. Paths to licensed source, tables and checkpoints can
remain private; the report records their hashes and availability, not contents.
No manifest field accepts arbitrary installation commands or shell hooks.

## Manifest

The following is a template. Replace the placeholder hash with the SHA256 of the
actual hypothesis file and use an existing worker ID and registry directory:

```json
{
  "schema_version": "simjecture-deployment/1",
  "name": "Radiation-energy investigation",
  "machine_registry": "./machines",
  "software": {"simjecture_version": "0.7.0"},
  "workers": [
    {
      "id": "node-a",
      "minimum_free_bytes": 68719476736,
      "capabilities": [{"name": "flash-my-application"}]
    }
  ],
  "files": [
    {
      "id": "hypothesis",
      "path": "hypothesis.txt",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "purpose": "hypothesis"
    }
  ],
  "study": {
    "worker": {"backend": "codex", "model": "YOUR_WORKER_MODEL", "reasoning_effort": "high"},
    "director": {"backend": "codex", "model": "YOUR_DIRECTOR_MODEL", "reasoning_effort": "high"},
    "reviewer": {"backend": "codex", "model": "YOUR_REVIEWER_MODEL", "reasoning_effort": "high"},
    "wall_seconds": 172800,
    "report_reserve_seconds": 1800,
    "initial_max_experiment_bytes": 68719476736,
    "initial_max_total_bytes": 274877906944,
    "director_storage_increases": true
  }
}
```

Local paths resolve relative to the manifest, not the shell's current directory.
For a file on a worker, add `"machine": "node-a"` and an absolute worker path.
Files can describe instructions, prior evidence, restarts, materials, source
archives and attention configurations. Mark a large optional archive
`"required": false` to record its absence without blocking the plan. An optional
file that exists but has a wrong hash, cannot be read, or changes while being
hashed still blocks the check. Optional does not mean corrupted data is trusted.
Checksums establish identity, not the validity of supplied scientific results.

To pin more than the package release, set `software.python_source_sha256` to the
coordinator's reviewed source digest. The checker records this digest and always
compares each worker's Python source against the coordinator. It covers the
package's Python modules, including vendor Python, excluding `__pycache__` and
installed `builtin_skills`; it does not cover dependencies, compiled binaries,
or other package assets. Scientific runtimes use their existing capability
identities. Pin an expected `contract_sha256` on each required capability and an
expected `config_sha256` on each worker when those identities should be fixed.
Without a pin, the checker records the current identity without claiming it was
the operator's previously approved one.

The `study` block records the intended roles and initial allowances. This first
version **does not apply these settings to a launcher** or verify provider
credentials/model access. Use them when creating the eventual study through the
existing CLI or workspace. Director and reviewer backends must match the current
launcher's shared route; their models and reasoning efforts can differ. Storage
remains an initial logical allowance; neither
it nor `minimum_free_bytes` reserves disk space. Director storage delegation must
also be selected at actual launch.

## Offline plan and current checks

```bash
simjecture deployment plan --manifest deployment.json --output plan.json
simjecture deployment check --manifest deployment.json --output readiness-001.json
```

Both commands print JSON. `plan` validates the manifest and its references without
connecting to machines, reading listed files, creating a registry or creating a
study. `check` performs these operational observations:

1. Compare the coordinator package version and optional Python-source pin.
2. Run the existing registered-worker check, including its small Python launcher
   probe, and inspect configuration, capabilities, matching source and disk space.
3. Stream SHA256 checks of the explicitly listed regular files. Data contents are
   not returned. FIFOs and other non-regular files are rejected.
4. If requested, check the already running attention service and its model identity.

Live checks update the machine registry's readiness observations and the worker's
existing health-probe files. They do not prepare or reconfigure workers, dispatch
research experiments, or freeze an execution pool. An unavailable worker produces
a failed check; its files remain explicitly unchecked. Other workers are still
checked. The checker does not silently downgrade the selected execution backend.

Reports have version `simjecture-deployment-report/1`, bind the exact manifest
bytes by SHA256, retain the declared study settings, and distinguish `planned`,
`passed`, `failed` and `skipped` items. Overall `ready` requires every required
check to pass. The exit status is 0 for a valid offline plan or a ready report,
1 for a blocked report, and 2 for invalid command/manifest input. Existing report
paths are never overwritten. Re-run with a new report path after correcting a
missing file or installation; healthy existing installations are not rebuilt.

`--timeout-seconds` controls each worker's additional file/source inspection
(120 seconds by default). Large checkpoints may need longer. The reused machine
registry check retains its existing timeout. Reports are point-in-time records;
repeat checks after material changes and before launch. Source hashes do not
certify numerical accuracy, model access, or a complete reproducible environment.

## Optional attention health

List the existing attention configuration as a coordinator file with purpose
`attention_config` and its SHA256, then reference its file ID:

```json
"attention": {"config_file": "attention-settings", "required": true}
```

The optional `simjecture-monitor` client must be installed. The configuration's
socket and token-file paths follow the existing attention contract and remain
absolute. The token value is neither copied into the manifest nor included in the
report. A failed configuration hash prevents contacting the service. With
`required: false`, a service outage is reported but does not block other required
checks; the configuration file itself still needs its declared identity.

Health verifies the resident policy and pinned model identity. It does **not**
score a warm-up request, check the compute lease, supervise forwarding, or prove
recovery. Those remain explicit steps in the [attention guide](scientific-attention.md).
Likewise, solver execution, convergence and scientific claim review remain
separate from deployment readiness.

## Scope of this first version

This establishes a common manifest/report boundary for future automation. Managed
attention startup, data staging, resumable installation recipes, browser integration,
and launching directly from an audited manifest are follow-up work. A preparation
skill can use the current commands and existing installers to diagnose and resolve
failed items, while deterministic code owns identities and report semantics.
