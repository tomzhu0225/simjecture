# Engineering campaigns

The engineering domain applies the Simjecture evidence loop to a software
repository. The implementation is allowed to change, while the goal, base
commit, path policy, and validation commands are frozen. A failed command is a
counterexample to that patch hypothesis; a passing command supports the patch
only within the declared contract.

The current MVP provides deterministic campaign primitives. It does not yet
open a pull request. It can now run a host-controlled model loop: the model
returns a typed edit proposal, while the host writes only approved files in an
isolated worktree. An operator can still edit the worktree between
`patch-create` and `patch-validate`. A final adjudication stage is available
for an external holdout contract and an independent deterministic diff review.

## Contract

Write a JSON contract outside the target repository. Commands are argv arrays,
not shell strings, so shell expansion is never performed by the campaign
runner. This example is intentionally generic; replace the repository path and
checks with the target project's actual acceptance contract.

```json
{
  "schema_version": "0.1.0",
  "campaign_id": "warpx-radiation-transport",
  "goal": "Implement the bounded radiation-transport feature without changing the public solver contract.",
  "repository": "/absolute/path/to/warpx",
  "base_commit": null,
  "editable_paths": ["Source/**", "Tools/**"],
  "protected_paths": ["tests/**", ".github/**", "CMakeLists.txt"],
  "checks": [
    {
      "name": "targeted-tests",
      "stage": "targeted",
      "command": ["ctest", "--test-dir", "build", "-R", "radiation", "--output-on-failure"],
      "timeout_seconds": 900
    },
    {
      "name": "full-tests",
      "stage": "full",
      "command": ["ctest", "--test-dir", "build", "--output-on-failure"],
      "timeout_seconds": 3600
    }
  ],
  "require_clean_repository": true,
  "max_patch_attempts": 32,
  "max_output_chars": 30000
}
```

The visible contract must not contain checks with stage: "holdout". Keep
those in a separate holdout file that is readable by the host adjudicator but
not by the coding agent. For example:

```json
{
  "schema_version": "0.1.0",
  "holdout_id": "warpx-radiation-held-out-v1",
  "campaign_id": "warpx-radiation-transport",
  "repository": "/absolute/path/to/warpx",
  "base_commit": "0123456789abcdef0123456789abcdef01234567",
  "checks": [
    {
      "name": "held-out-parameter-case",
      "stage": "holdout",
      "command": ["ctest", "--test-dir", "build", "-R", "radiation-held-out"],
      "timeout_seconds": 1800
    }
  ],
  "max_output_chars": 30000
}
```

The campaign resolves `base_commit` to a full commit ID when it is created.
The target repository must be clean, and the campaign output must be outside
that repository. This prevents a local experiment directory from becoming an
unreviewed part of the candidate patch.

## Run the deterministic loop

```bash
uv run simjecture engineering create contract.json \
  --output /tmp/simjecture-engineering/warpx-radiation-transport

uv run simjecture engineering commission \
  /tmp/simjecture-engineering/warpx-radiation-transport

uv run simjecture engineering patch-create \
  /tmp/simjecture-engineering/warpx-radiation-transport patch-001 \
  --diagnosis "The transport update is not connected to the registered source term." \
  --prediction "Connecting the source term will make the targeted test pass while preserving the API."
```

The command prints the isolated worktree. Edit only files allowed by the
contract, then validate and commit the patch:

```bash
uv run simjecture engineering patch-validate \
  /tmp/simjecture-engineering/warpx-radiation-transport patch-001 \
  --message "connect radiation transport source term"

uv run simjecture engineering adjudicate \
  /tmp/simjecture-engineering/warpx-radiation-transport patch-001 \
  --holdout /secure/holdouts/warpx-radiation-held-out-v1.json \
  --assert-accepted

uv run simjecture engineering status \
  /tmp/simjecture-engineering/warpx-radiation-transport
```

The automatic loop uses the same campaign contract and never receives the
holdout object:

```bash
uv run simjecture engineering agent-run \
  /tmp/simjecture-engineering/warpx-radiation-transport \
  --holdout /secure/holdouts/warpx-radiation-held-out-v1.json \
  --assert-accepted
```

The model response is not a shell command. It is one JSON
`EngineeringPatchProposal` containing a diagnosis, a falsifiable prediction,
a commit message, and text edits. Existing files require the exact SHA-256
provided beside the source snapshot; replacement edits also require one
unambiguous anchor. The host rejects absolute paths, traversal, symlinks, protected files,
duplicate paths, stale hashes, and oversized edits before anything is written.
After a visible counterexample, the next proposal is created as a child of
that exact candidate commit. A visible pass without a holdout is reported as
`validated`, not `accepted`.

If a check fails, the patch record is marked `counterexample`, and its exact
commit, diff hash, command output, and failure reason are retained. A refined
child patch can then be created from that commit:

```bash
uv run simjecture engineering patch-create \
  /tmp/simjecture-engineering/warpx-radiation-transport patch-002 \
  --parent patch-001 \
  --diagnosis "The first patch omitted the timestep coupling exposed by the failing test." \
  --prediction "Adding the coupling will satisfy the same frozen contract."
```

The resulting campaign has a patch DAG rather than an overwritten edit
history. `status --json` is suitable for the Web UI integration planned for a
later increment. A patch that passes the visible checks is only `validated`;
`adjudicate` can promote it to `accepted`, mark it as a holdout
`counterexample`, or reject it for a diff-integrity violation.

## What this MVP does and does not prove

The path policy rejects protected files and changes outside `editable_paths`.
Validation commands are run in the candidate worktree without a shell, and a
command that modifies tracked files after the candidate commit is rejected.
The evidence record is therefore tied to an exact commit and diff.

The checks in the visible JSON contract are visible to the implementer. The
external holdout file is the protected validation layer: keep it outside the
target repository, campaign output, agent prompt, and agent-readable
filesystem. The command records only its content hash and post-run receipts,
so the candidate cannot edit the acceptance boundary after seeing evidence.
This is an operational secrecy boundary, not a cryptographic claim that a
same-user process cannot discover every host file.

The deterministic diff judge independently recomputes the candidate commit,
parent commit, changed paths, policy violations, and worktree cleanliness. It
does not decide whether the implementation is semantically correct; the
holdout commands and, later, an optional model or human reviewer provide that
separate judgment.

For a release-quality campaign, add held-out parameter cases, property or
metamorphic tests, independent numerical benchmarks, and a clean-room run.
The engineering campaign should treat a passing CI as bounded evidence, not as
proof that the implementation is universally correct.

For numerical WarpX work, the protected layer should include applicable
conservation, positivity, limiting-regime, refinement, MPI-layout, and CPU/GPU
consistency checks in addition to ordinary unit tests.
