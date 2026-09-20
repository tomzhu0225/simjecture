# Simjecture Linux launch package

This package contains matching Python and DSH bundles. Read `VERSION` for the
release number and `CHANGELOG.md` for release notes.

Requirements: Linux (including WSL2) with working Bubblewrap user namespaces,
Python 3.11+ with venv/pip, Node 22.19+ (22.x) or 24+, npm, and internet access
for dependency installation and model requests. CUDA and simulation instruments
are optional and are provisioned separately.

From the extracted package directory:

```bash
sha256sum -c SHA256SUMS
bash setup.sh
export DEEPSEEK_API_KEY='your-key'
bash launch.sh
```

Open the localhost URL printed by the launcher. New campaigns use DSH, with
`deepseek-official/deepseek-flash` as the upstream default route. Provider and
model settings can be changed in this package's isolated DSH profile. Model
calls may incur provider charges; neither setup nor launching the dashboard
submits a scientific hypothesis by itself.

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

Back up an existing campaign before running it under the new release. The new
research session uses a separate workspace and the `.research-v1` identity;
older conversations remain available, while the new researcher reconstructs
scientific state from the kernel. Image inspection requires a vision-capable
model. Native exploratory work does not automatically become scientific evidence.
Built-in file/shell tools enforce DSH's research-workspace policy; installed
plugins and workflow code remain trusted host-process code.

Simote is optional and distributed independently. This package does not install
Simote or configure remote machines.
