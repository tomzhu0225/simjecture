# Research workspace

The workspace starts with a conversation. Bring a task, a paper, simulation outputs,
or a hypothesis. Work interactively with an agent, then prepare a bounded autonomous
investigation when the question and evidence requirements are clear.

## Start the browser

From the Linux source checkout:

```bash
./scripts/launch-workspace.sh
```

The launcher installs the locked optional `workspace` dependencies with `uv` and opens
the local browser. Equivalent commands:

```bash
uv sync --frozen --extra workspace
uv run --extra workspace simjecture web
```

Use the browser on the workstation's remote desktop if that is how you normally
access the machine. Files and simulations run on the machine serving the page.
The server binds to localhost. Closing the browser or web server leaves agent turns,
installations and autonomous studies running independently. Stop them with their
project controls before shutting down the workstation when necessary.

## Connect an agent

In **Connections**, choose one of:

- **Built-in agent:** enter an OpenAI-compatible base URL, API key, and exact model
  identifier. Local compatible model servers work too. Save and test performs a small
  tool-call request, so it checks more than the availability of an endpoint.
- **Installed CLI:** the workspace detects `codex`, `codex-glm`, `grok`, and `agy` on
  the server's PATH. Choose a model and keep the CLI's existing login. The connection
  check verifies the executable; the first real conversation verifies authentication.

The built-in agent uses Hugging Face **smolagents** and its compatible API transport.
Native CLI execution reuses Simjecture's existing supervision adapter. Both routes
can read and write project files, execute local commands, prepare study briefs, and
use the same research service. These are cooperative local agents with access to the
host account, as with the existing native CLI integrations.

Keys are saved in mode-0600 files under `artifacts/.workspace/`, outside project
folders, and never returned by the settings API. Each autonomous API study references
a separate frozen connection file so changing the default connection does not
silently change an existing study's provider. Do not place keys in chat messages.

## Your first study

1. On Overview, choose **Find a first counterexample**, then **Start a project**.
2. Send the request. The agent can make a small calculation and prepare a study brief.
3. Select **Autonomous research**. Review the question, required evidence, constraints,
   time budget, and completion policy. Ordinary Python needs no simulation plugin.
4. Start the study. The autonomous worker records experiments and submits evidence to
   a separate tool-free reviewer. Watch progress in the project or experiment monitor.
5. Open the result, evidence ledger, and simulation files from the study card.

**Answer the question** permits independently accepted support or falsification of the
original claim to complete the investigation. **Seek a supported claim or tested repair**
keeps the existing repair loop. Uncertainty is never counted as an accepted answer.
Existing CLI studies keep their original default and saved policy.

Interactive research returns after a requested task. It can prepare an editable brief;
it does not silently start an unbounded investigation. Autonomous research uses the
existing minimal research core, with its evidence, method, provenance, deadline,
recovery and independent-review checks. Its pause/resume/stop controls reuse the
existing verified process controls. A paused study retains its original deadline.

## Permanent files, arranged by project

Project and study folders use names you can recognize:

```text
artifacts/
  projects/
    2026-09-26-reconnection-onset/
      README.md                   # Links to the project's work
      CONVERSATION.md              # Readable saved discussion
      project.json                # Project metadata and study references
      files/                      # Uploads and interactive agent outputs
      turns/                      # Detailed conversation/activity records
      studies/
        001-test-inflow-averaging/
          project-brief.json      # The agreed brief for this study
          RESULTS_INDEX.md        # Human-readable simulation/output navigation
          STUDY_LEDGER.md         # Host-maintained evidence record
          research_report.json
          research/
            project_inputs/       # Snapshot of the project's inputs at launch
            RESULTS.md            # Agent's scientific narrative, when written
          experiments/            # Immutable receipts, source snapshots and outputs
```

Nothing in this project lifecycle is stored in an automatically removed temporary
directory. Internal experiment receipts retain their stable IDs for reproducibility;
the browser and results index group outputs by experiment number and name. Failed and
interrupted work remains available. Raw numerical sandbox commissioning probes may
use the existing installer's temporary directories; they are not your study results.

Browser uploads support files up to 20 MB. For larger datasets, copy them to the
project's displayed `files/` path. Launch currently snapshots up to 512 MB of project
inputs; the research service's existing separate experiment storage limits still apply.
Tool installations are shared on the machine; a project's inputs and study outputs
belong to that project.

## Research tools

The catalogue reuses `simjecture install` and `simjecture doctor` implementations.
WarpX CPU, EOS and opacity tools have installer buttons. FLASH and WarpX CUDA ask for
an existing source checkout. Installation jobs continue in the background and expose
their reports and logs. The catalogue also detects configured executable installations.

You can ask your project agent to install other software and register its Simjecture
capability directory. Registered instruments appear in the catalogue and study selector.
An installation check means the tool can run; it is not scientific qualification for
a particular experiment. Required commissioning and independent methods review remain
part of the autonomous research core.

## Development validation

```bash
uv run --extra workspace pytest tests/test_workspace.py
# Optional full browser acceptance test:
uv pip install playwright
uv run --extra workspace python -m playwright install chromium
.venv/bin/pytest tests/test_workspace_browser.py
```

The integration tests use a deterministic compatible API server. They exercise the real
agent SDK, file operations, study launch, numerical execution and reviewer transport;
they are not a benchmark of any provider's scientific reasoning. Existing CLI transport
is also tested with a deterministic executable. Enter your own connection in the
browser to evaluate a real research task.
