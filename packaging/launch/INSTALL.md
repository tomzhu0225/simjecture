# Simjecture Linux launch package

This archive contains the Python distribution and a local workspace launcher.
Read `VERSION` and `CHANGELOG.md` for the release. The versioned workspace installer
linked from the repository README can also provision Python on a fresh host.

Requirements: Linux or WSL2, Python 3.11+ with venv/pip, Bubblewrap with working
user namespaces, and internet access for Python dependencies. Install and log in
to your chosen native agent CLI separately, or configure a compatible API in the
workspace's Connections page. No credentials or subscriptions are bundled.

```bash
sha256sum -c SHA256SUMS
bash setup.sh
bash launch.sh
```

Setup creates this directory's `.venv` with the workspace extra. Opening
the interface does not submit a study. Minimal is the only supported study workflow;
DSH, classical/MVP, structured and frontier routes are removed. No DSH bundle or
Node runtime is installed. `setup.sh --with-dsh` is no longer supported.

For a headless study, using your configured backend and model:

```bash
.venv/bin/simjecture study --campaign campaigns/example \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

`launch.sh` forwards arguments to `simjecture web`. To inspect an older record:

```bash
bash launch.sh /absolute/path/to/existing/campaign --read-only
```

Back up existing work and finish or pause older workflows before upgrading.
This release can inspect old records but cannot resume their removed workflows;
keep the original environment for that purpose. Existing minimal studies retain
their launch contracts and deadlines. Start a new directory when bringing an older
question into minimal, and treat old outputs as context rather than fresh evidence.

Keep the `campaigns` directory when moving or backing up this installation. This
archive is not an offline installer and does not install scientific solvers or
configure remote machines.
