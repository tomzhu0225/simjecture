# Run a headless study

Use this workflow for terminal sessions, scripts or browserless hosts. For an
interactive first investigation, start with the
[research workspace](../getting-started/research-workspace.md).

## Prerequisites

Use Linux or WSL, Python 3.11+ and [uv](https://docs.astral.sh/uv/). Install and
authenticate a supported native CLI separately. The choices are `codex-glm`,
`codex`, `grok` and `agy`; choose the model configured for that CLI. No particular
provider or subscription is required by this workflow. Keep credentials in the
agent's own credential store, outside study directories and source control.

Install Bubblewrap using your distribution's package manager (for example,
`sudo apt install bubblewrap` on Debian/Ubuntu). Then install the preview package
and check whether this host permits the required namespaces:

```bash
uv tool install 'simjecture==0.5.3rc4'
simjecture doctor --execution-backend bubblewrap
```

For other versions and source checkouts, see
[installation](../getting-started/installation.md). Bubblewrap is the default
numerical execution backend. If namespaces are unavailable, follow the
[restricted-host guide](restricted-containers.md) before explicitly selecting
`--execution-backend proot-cooperative` on a dedicated non-root account. PRoot is
not an OS security boundary, and Simjecture never silently falls back to it.
Native agents retain their host tools and are not enclosed by the numerical sandbox.

## Prepare and launch

Write a falsifiable hypothesis in `hypothesis.txt`. In `instructions.md`, specify
physical scope, available instruments, resource limits and the evidence needed to
accept or reject it. Review both files before launch: the operator's question and
scope are frozen for the study.

Replace `BACKEND_NAME` and `MODEL_ID` with your installed backend and configured
model from the choices above, then choose a new campaign directory and budget:

```bash
BACKEND=BACKEND_NAME
MODEL=MODEL_ID
simjecture study --campaign ./runs/my-study \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --backend "$BACKEND" --model "$MODEL" --wall-seconds 3600
```

The launch prints activity, backend/model, remaining time and experiment/review
counts. Redirected output uses periodic plain status lines; `--quiet` suppresses
progress. A study can make paid provider requests through the agent you selected.

Mode, agent and numerical execution are separate choices:

- `--backend` and `--model` choose the native agent and its configured model
- `--mode minimal` is the default; `structured` and `frontier` select other
  research workflows
- `--execution-backend` chooses how recorded numerical experiments execute

In minimal mode, the CLI defaults to `--completion-policy repair`: an independently supported root,
or an accepted falsification followed by a supported repair, can complete it.
Choose `--completion-policy answer` to also allow an independently accepted root
falsification to finish the investigation, as the workspace does for new studies.
See [minimal-mode evidence and review](research-service.md) for the full contract.

The configured built-in API agent is another advanced option; it uses a private
`--provider-config` file and supports minimal mode only. See the
[command reference](../reference/cli.md). Legacy
[DSH](deepseek-harness.md) and [Simote](simote-agent-roles.md) integrations have
separate setup guides.

## Inspect, pause and resume

Inspect the same campaign from another terminal or the local browser:

```bash
simjecture status ./runs/my-study
simjecture watch ./runs/my-study
simjecture web ./runs/my-study
simjecture pause ./runs/my-study
simjecture resume ./runs/my-study
```

`status` is a snapshot; `watch` follows progress, and Ctrl-C stops only the viewer.
The optional TUI requires the `tui` extra; see the
[terminal dashboard guide](../getting-started/terminal-ui.md).

For a foreground restart, repeat the original `study` command with the same
campaign path and launch options. The recorded mode, completion policy and original
wall deadline stay fixed. Pause stops the agent at its supervisor boundary; recorded
jobs may still finish within their existing bounds. Provider retry time and pauses
count against the wall deadline. Transient disconnects retry with backoff, while
authentication, permission and exhausted-quota errors pause for attention.

A normal agent exit or inconclusive result does not complete research. To continue
beyond the original budget, prepare a linked phase with a new budget and selected
prior files using [continuation and steering](continuation-steering.md).

## Start from a working instrument

For expensive solver setup, provide a guided commissioning package: exact working
source and command, an output reader, observable, validation checks, runtime and
known limitations. Reproduce that anchor in a separate bounded readiness run before
hypothesis testing.

```bash
simjecture study --campaign ./runs/guided-study \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --guided-commission /path/to/guided_commission.json \
  --capabilities /path/to/installed-capabilities \
  --backend "$BACKEND" --model "$MODEL" --wall-seconds 3600
```

Guided examples are starting instruments, not fresh evidence for a new hypothesis.
Follow [guided commissioning](guided-commissioning.md) for the package format and
readiness budget, [runtime deployment](deploy-runtimes.md) for optional instruments,
and [SSH workers](ssh-workers.md) for multi-machine numerical execution.
