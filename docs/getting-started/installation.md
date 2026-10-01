# Installation

## One-command browser preview installation

On Linux or inside an existing WSL distribution:

```bash
curl -fsSL https://github.com/tomzhu0225/simjecture/releases/download/v0.5.2/install.sh | bash
```

This command selects stable **0.5.2**. Existing research data and older program versions are preserved.

For the **0.5.3rc3 preview**, including SSH workers and refreshed interfaces:

```bash
curl -fsSL https://github.com/tomzhu0225/simjecture/releases/download/v0.5.3rc3/install.sh | bash
```

The preview installs beside older versions. It retains projects, provider settings
and runtime directories. See [rc3 scope and checks](../testing/0.5.3rc3-acceptance.md)
and [SSH worker setup](../how-to/ssh-workers.md).

No Git, Python environment or CLI agent setup is required in advance. The bootstrap
fetches the versioned workspace bundle and verifies its SHA-256 checksum, installs uv
and Python 3.12 when needed, then installs the locked workspace dependencies. It starts
the GUI on localhost. In **Connections**, add a compatible API endpoint/key; choose its
model in the message composer. Existing CLI agents are optional.

The installer uses `~/simjecture` by default:

- `app/<version>/`: source and an isolated Python environment for that release;
- `.runtime/`: shared installed scientific tools;
- `artifacts/projects/`: permanent conversations, input files and simulation/study outputs;
- `start-workspace`: start the installed version again.

An unrelated existing destination is never overwritten. Set `SIMJECTURE_INSTALL_DIR`
to choose another folder. Re-running the installer retries incomplete setup, and a new
release installs beside the old version before switching the launcher. It does not
remove older versions or research outputs.

To install without starting, or choose a different web port:

```bash
curl -fsSL https://github.com/tomzhu0225/simjecture/releases/download/v0.5.2/install.sh | bash -s -- --no-start
~/simjecture/start-workspace --port 8765
```

On Debian/Ubuntu the installer attempts to install Bubblewrap with apt; a non-root
user may see a sudo password prompt. `--no-system-packages` skips that step. Namespace
availability is checked separately: installing a binary cannot enable kernel features
blocked by a container host. The GUI remains usable if numerical execution requires
attention. See [restricted containers](../how-to/restricted-containers.md); isolation
is never silently weakened.

### Managed installation and restricted hosts

On namespace-restricted hosts, a root invocation prepares a dedicated non-root
account and uses `/srv/simjecture` by default. The printed launcher handles future
root invocations by dropping privileges. A visible warning explains cooperative
PRoot execution. Existing unrelated installations are preserved.

Research tool Install buttons provision their own compatible dependencies using
managed environments and a shared package cache. System scientific compilers,
MPI and HDF5 do not have to be installed by hand. FLASH still requires the user's
licensed source and an application choice; FLASH and CUDA use the built-in agent
for configuration, build, registration and actual backend readiness checks.

### SSH servers

The workspace runs on the SSH server. Experiments run there by default; the rc3 preview can
select additional SSH workers through Machines. The installer prints a forwarding
command; run it on your local computer, for example:

```bash
ssh -N -L 8766:127.0.0.1:8765 user@your-server
```

Open `http://localhost:8766` locally. Use the SSH host and port you normally connect to;
behind a relay/NAT they may differ from the server's own address. The GUI is not exposed
as a public listener. Keep the server terminal open or use a session manager; detached
agents and simulation jobs keep their own deadlines if the web server closes.

### Source checkout

Developers can install from their current checkout with `bash scripts/install-workspace.sh`,
or manage dependencies themselves:

```bash
git clone https://github.com/tomzhu0225/simjecture.git
cd simjecture
uv sync --frozen --extra workspace
uv run simjecture doctor --profile core
uv run simjecture web
```

## Native agent login

For browser setup, run `./scripts/launch-workspace.sh`, choose an agent and model on
Overview, and send your first message. **Connections** is only needed
to add an optional compatible API endpoint and key. See the
[research workspace guide](research-workspace.md) for a complete first investigation.

New studies default to minimal mode. Install and log in with Codex GLM, Codex,
Grok or AGY independently, then choose that backend and model in the launcher.
Simjecture does not redistribute those CLIs or subscriptions. Native tools remain
available; numerical execution defaults to Bubblewrap, with explicit cooperative PRoot
selection available on supported restricted hosts. No DeepSeek
API key or DSH install is required for native-agent studies.

## Legacy API credentials

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

The default Python sandbox supports ordinary numerical work. WarpX, FLASH,
equation-of-state, and opacity capabilities are optional local instruments.
They are mounted read-only and are not downloaded by `uv sync`.

The CPU profile is provisioned and checked in one command:

```bash
uv run simjecture install warpx-cpu
```

The CUDA profile can fetch the pinned source and provision its build prerequisites.
The bundled recipe builds 2D; use the GUI agent to discuss other dimensions or
application requirements. An audited source checkout can also be supplied:

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

`simjecture install flash` does not download FLASH. Follow
`skills/flash-mhd/references/local-deployment.md` for the local layout. A FLASH
executable is compiled for a selected application and physics configuration; it
must not be treated as a universal MHD binary. For a private one-command rebuild of a tree you already obtained, or a clone of
a remote only you configured, attach an overlay as described in
`skills/flash-mhd/references/private-install.md`. The public tree still contains
no FLASH download URL.

Equation-of-state and opacity-table generators use the same installer path as
WarpX CPU. The command clones a pinned upstream revision into `.runtime/` and
runs a non-evidentiary probe:

```bash
uv run simjecture install atomec
uv run simjecture install singularity-eos
uv run simjecture install m-aneos
uv run simjecture install optab
```

Use `--dry-run` to inspect a new provisioning command. An unhealthy
installer-managed prefix is preserved unless `--repair` is explicit. Follow
`skills/eos/references/local-deployment.md` and
`skills/opacity/references/local-deployment.md`. An EOS capability is not an
opacity table; Optab consumes an external abundance table rather than solving
thermodynamic closure. FLASH remains operator-supplied because its license
restricts redistribution.

## Local web interface

The browser dashboard itself is included with the core installation. Recorded
campaigns can be opened without Node.js or a model runtime:

```bash
uv run simjecture web demos/gray_scott_counterexample/record --read-only
```

The default browser entry point is the research workspace. Use a compatible API or
an installed native CLI. The experiment monitor remains available at `/monitor` and
can inspect existing study records. The legacy DSH engine is an explicit alternative;
it is not required for ordinary workspace setup. See [Web interface](web-interface.md).

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
