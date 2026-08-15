# Installation

## Core research runtime

Simjecture currently targets Linux because the
natural-language MVP uses Bubblewrap for workspace isolation.

Install Python 3.11 or newer, `uv`, and Bubblewrap, then clone and synchronize
the locked environment. The idempotent core installer verifies the exact Python
stack and proves that Bubblewrap can create the namespace required by a run:

```bash
git clone https://github.com/tomzhu0225/simjecture.git
cd simjecture
uv sync --frozen
uv run simjecture install core
uv run simjecture doctor --profile core
```

## Model credentials

Credentials are process-local harness inputs. They are never mounted into the
agent workspace.

```bash
export DEEPSEEK_API_KEY='your-process-local-key'
```

The official DeepSeek route is selected automatically when this variable is
present. `ACS_MODEL_PROVIDER=deepseek` makes that choice explicit. See
`.env.example` for non-secret configuration names; do not place a real key in
that tracked example.

## Optional simulation runtimes

The default Python sandbox supports ordinary numerical work. WarpX CPU and CUDA
capabilities are optional, local, release-pinned installations. They are mounted
read-only and are not downloaded by `uv sync`.

The CPU profile is provisioned and checked in one command:

```bash
uv run simjecture install warpx-cpu
```

The CUDA profile requires an operator-audited source checkout at the revision
declared by the WarpX deployment skill:

```bash
uv run simjecture install warpx-cuda \
  --source /absolute/path/to/pinned/warpx-26.07
```

Both commands are idempotent when the installed capability is healthy. Use
`--dry-run` to inspect a new provisioning command. An unhealthy existing CPU
Conda prefix is preserved unless `--repair` is explicit; an unhealthy CUDA build
is never repaired in place because that could destroy the identity of a prior
scientific instrument.

Use `simjecture doctor --json` for a machine-readable inventory. The
doctor is read-only: capability probes execute in a temporary sandbox, and
deployment records are written only by `install` under the Git-ignored
`.runtime/deployment/` directory.

Read `skills/warpx/SKILL.md` and
`skills/warpx/references/local-cuda-deployment.md` before provisioning WarpX.
Capability health preflights identify missing or incompatible local runtimes
without granting scientific-evidence status.

## Optional terminal dashboard

The scientific environment does not depend on Textual. To install the
interactive dashboard:

```bash
uv sync --frozen --extra tui
uv run simjecture tui
```

Headless `status` and `watch` remain available without that extra. See
[Terminal interface](terminal-ui.md).
