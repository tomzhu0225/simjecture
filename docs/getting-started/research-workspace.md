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

## Choose an agent in your conversation

Use the **Agent**, **Model**, and **Reasoning effort** selectors on Overview or in
an existing conversation:

- **Compatible API:** optionally save a base URL and key in **Connections**. Back in
  the conversation, the model selector reads the endpoint's model catalogue. If a
  provider does not expose a catalogue, select **Other model** and enter its exact ID.
  Local compatible model servers work too.
- **Installed CLI:** the workspace detects `codex`, `codex-glm`, `grok`, and `agy` on
  the server's PATH. Select the CLI and model directly in the conversation, keeping
  its existing login. No API setup is needed. Local model suggestions are not a login
  check; the first real conversation verifies authentication and model availability.

AGY's model choices come from `agy models`, not from another CLI's saved model.
New conversations remember your last valid agent/model selection. Invalid legacy
pairs are discarded rather than offered as defaults.

Each conversation remembers its choice independently. Changing it affects subsequent
messages and new studies; in-flight turns and existing studies retain their recorded
connection. Reasoning effort is separate from the model ID: for example, choose
`grok-4.7` and **High**, rather than typing `grok-4.7 high`. AGY retains its native
reasoning settings. Compatible API providers must support the selected effort value;
leave **Default** selected when the provider does not support it.

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

1. On Overview, choose **Find a first counterexample** or type your own request.
2. Choose the agent and model, then press **Enter** or **Send**. This starts the
   conversation immediately and creates its permanent named folder automatically.
   **Shift+Enter** inserts a new line, both here and inside existing conversations.
   **New conversation** returns to this composer without a project-creation form.
3. Select **Autonomous research** and choose **Grill me** for focused questions, or
   **Draft from this conversation** to use existing context. The agent fills the brief,
   asking about consequential gaps instead of inventing missing facts. Automatic
   drafting uses a disclosed one-hour budget and accepts reviewed negative results
   unless you have specified otherwise. Ordinary Python needs no simulation plugin.
4. Review the agent's proposal and press **Start research**. Manual fields are tucked
   under **Review or edit the study details**. The autonomous worker records experiments and submits evidence to
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
      simulations/
        001-wave-decay/
          output.log              # Live console, retained after completion
          workspace/              # Input snapshot and simulation outputs
          request.json            # Command, deadline, and source conversation turn
          state.json              # Completion or interruption status
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
**Installed** and **Not installed** are separate sections. Installed instruments
also show whether a readiness check has passed, failed, or has not yet been run.
WarpX CPU, EOS and opacity tools have installer buttons. Existing capability descriptors
in the checkout's `capabilities/`, `.private/*/capabilities*/`, runtime capability
directories and the configured capability directory are discovered automatically.
Installed FLASH applications are shown with their own names, versions and runtime paths;
they are not relabelled as the bundled island-coalescence application. You do not need
to supply source again for these installations. Readiness checks use the detected
application's descriptor. FLASH and WarpX CUDA setup asks for a source checkout only
when installing a new runtime. Installation jobs continue in the background and expose
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

## Linked conversations and interactive simulations

Chat responses can link directly to their proposed autonomous study and simulation
runs. These links also work after a reload. Opening a simulation keeps you in
interactive research and opens the resizable side inspector, with live output,
status, saved figures, and a stop button. Explicit simulation runs keep their own
input snapshot and outputs; ordinary agent shell commands work in the conversation's
shared `files/` folder. Closing the browser does not stop detached simulations.
Native CLI commands appear when their CLI emits public command events; managed runs
launched through the supplied simulation tool support individual cancellation.

Responses render inline and display LaTeX (`$...$`, `$$...$$`, `\(...\)`, `\[...\]`),
fenced code with syntax highlighting and Copy, and saved PNG, JPEG, GIF, WebP or SVG
figures. Agents can embed `![Caption](figure.png)` from conversation files or
`![Caption](simulation:001-wave-decay/figure.png)` from a run. Figure clicks open
the saved image. Activity labels distinguish connecting, thinking, using tools and
writing a response when the provider or CLI reports those states. They do not expose
private reasoning or invent progress percentages.

WarpX discovery also checks sibling source builds and registered Conda environments,
using CMake's compute setting to identify CPU and GPU executables. These appear as
installed even if they do not yet have a registered research capability. Their paths
are available for interactive work; autonomous evidence workflows still require the
appropriate capability registration and commissioning.

## Frontend components

The workspace uses locally vendored [Web Awesome](https://webawesome.com/docs/)
3.14.0 split panels, tabs and activity indicators, plus highlight.js 11.11.1,
KaTeX, marked and DOMPurify. It does not need a CDN at runtime. Licenses are kept
alongside the assets. `scripts/vendor_workspace.py` rebuilds the Web Awesome and
highlight.js bundle from pinned npm archives with SHA-512 integrity checks; the
selected versions are recorded in `static/vendor/workspace-vendors.json`.
