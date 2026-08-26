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

Official DeepSeek campaigns retain thinking mode by default. For a
latency-oriented demonstration, `ACS_DEEPSEEK_THINKING=disabled` selects the
provider's non-thinking mode without changing campaign turn limits, evidence
contracts, or audit gates. This is an explicit quality/latency tradeoff rather
than the scientific default.

## Optional simulation runtimes

The default Python sandbox supports ordinary numerical work. WarpX and FLASH
capabilities are optional local instruments. They are mounted read-only and are
not downloaded by `uv sync`.

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

FLASH uses a different deployment boundary. Its source is obtained directly
from the [FLASH Center code-request page](https://flash.rochester.edu/site/flashcode/coderequest.html)
under the upstream license, which restricts redistribution. Simjecture therefore
ships only the generic `flash-mhd` skill and an application-specific capability
interface; it never downloads, accepts a license for, or redistributes FLASH
source or binaries. After the operator builds and registers the local runtime,
verify its exact executable, MPI launch, and HDF5 readback with:

```bash
uv run simjecture doctor --profile flash
```

`simjecture install flash` is intentionally a verification alias: it does not
provision or modify FLASH. Follow
`skills/flash-mhd/references/local-deployment.md` for the local layout and
qualification boundary. A FLASH executable is compiled for a selected
application and physics configuration; it must not be treated as a universal
MHD binary.

## Local web interface

The browser dashboard itself is included with the core installation. Recorded
campaigns can be opened without Node.js or a model runtime:

```bash
uv run simjecture web demos/gray_scott_counterexample/record --read-only
```

New browser-launched campaigns use DeepSeek Harness by default. Install the
pinned DSH profile once per machine with the
[DSH deployment guide](../how-to/deepseek-harness.md), then use the same command:

```bash
uv run simjecture web
```

It binds only to localhost and can discover, launch, or attach to durable
campaigns. `uv run simjecture web --engine native` selects the built-in
compatibility engine when DSH is intentionally unavailable. See
[Web interface](web-interface.md).

## Optional terminal dashboard (maintenance mode)

The scientific environment does not depend on Textual. The Web interface is
the primary interactive client; install the compatibility dashboard for SSH or
browserless operation:

```bash
uv sync --frozen --extra tui
uv run simjecture tui
```

Headless `status` and `watch` remain available without that extra. See
[Terminal interface](terminal-ui.md).
