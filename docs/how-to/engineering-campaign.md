# Engineering campaigns

The engineering domain applies the Simjecture evidence loop to a software
repository. The implementation is allowed to change, while the goal, base
commit, path policy, and validation commands are frozen. A failed command is a
counterexample to that patch hypothesis; a passing command supports the patch
only within the declared contract.

The current MVP provides deterministic campaign primitives. It does not yet
ask an LLM to edit the repository or open a pull request. An operator or a
future coding agent edits the worktree between `patch-create` and
`patch-validate`.

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

uv run simjecture engineering status \
  /tmp/simjecture-engineering/warpx-radiation-transport
```

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
later increment.

## What this MVP does and does not prove

The path policy rejects protected files and changes outside `editable_paths`.
Validation commands are run in the candidate worktree without a shell, and a
command that modifies tracked files after the candidate commit is rejected.
The evidence record is therefore tied to an exact commit and diff.

The checks in the JSON contract are still visible to the implementer. They are
not a hidden holdout suite. For a release-quality campaign, add an external
protected validation layer with held-out parameter cases, property or
metamorphic tests, independent numerical benchmarks, and a clean-room run.
The engineering campaign should treat a passing CI as bounded evidence, not as
proof that the implementation is universally correct.

For numerical WarpX work, the protected layer should include applicable
conservation, positivity, limiting-regime, refinement, MPI-layout, and CPU/GPU
consistency checks in addition to ordinary unit tests.
