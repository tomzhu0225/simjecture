# Simjecture Linux launch package

This package contains matching Python and DSH bundles. Read `VERSION` for the
release number and `CHANGELOG.md` for release notes.

Requirements: Linux (including WSL2) with working Bubblewrap user namespaces,
Python 3.11+ with venv/pip, and internet access for dependencies and model calls.
Install and log in to at least one supported native agent CLI separately:
Codex GLM, Codex, Grok or AGY. The package uses that CLI's existing login and does
not contain or configure subscriptions. CUDA and numerical instruments are optional.

From the extracted directory:

```bash
sha256sum -c SHA256SUMS
bash setup.sh
bash launch.sh
```

New studies default to **minimal**. The launch form separates mode, backend and
model. Choose structured or frontier if preferred. Non-GLM native backends require
an explicit model ID. Native tools remain available; accepted evidence still
requires recorded experiments and independent review.

DSH and direct API routes remain explicit **legacy** choices. They do not silently
fall back from minimal. To install the isolated DSH runtime too, use
`bash setup.sh --with-dsh` (Node 22.19+ or 24+, npm required), then configure your
DSH provider credentials. Neither setup nor opening the interface submits a study.

For a live terminal launch:

```bash
.venv/bin/simjecture study --campaign campaigns/example \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

The terminal shows mode/backend, activity, elapsed/remaining time and experiment
counts. Redirected output gets periodic plain progress lines; `--quiet` suppresses
those lines. `simjecture tui campaigns/example` and the browser can inspect the
same durable study. Existing studies preserve mode and deadline when resumed.

Setup installs into this directory's `.venv` and `run-state`. It does not replace
global DSH, another Simjecture installation, or your existing DSH profile. The
launcher starts from `campaigns`; keep this directory and its research workspaces
when moving or backing up the installation. The package is not an offline
installer and contains no API keys or account logins. Credentials come from your
terminal environment or your own DSH configuration.

`launch.sh` forwards arguments to `simjecture web`, for example:

```bash
bash launch.sh --help
bash launch.sh /absolute/path/to/existing/campaign --read-only
```

For legacy DSH campaigns, back up the campaign before upgrading. The
research session uses a separate workspace and the `.research-v1` identity;
older conversations remain available, while the new researcher reconstructs
scientific state from the kernel. Image inspection requires a vision-capable
model. Native exploratory work does not automatically become scientific evidence.
Built-in file/shell tools enforce DSH's research-workspace policy; installed
plugins and workflow code remain trusted host-process code.

Simote is optional and distributed independently. This package does not install
Simote or configure remote machines.
