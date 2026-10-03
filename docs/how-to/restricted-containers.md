# Running inside a restricted container

Scientific modes (`minimal`, `structured`, `frontier`) are independent of the
experiment execution backend. Bubblewrap remains the default. Simjecture never
silently switches to weaker isolation when namespace creation fails.

The conversation workspace and runtime installer provide a checked fallback: prefer Bubblewrap; when it cannot run, select PRoot only if
its probe succeeds under a non-root account. A sidebar warning explains that
this is cooperative execution without filesystem/network security isolation.
It can be dismissed; the mode indicator remains available to reopen it.
The workspace extra includes the process monitor. The installer can install
PRoot on Debian/Ubuntu. When invoked as root on a namespace-restricted host,
the installer creates a dedicated `simjecture` account and installs by default
under `/srv/simjecture`, with a root-owned launcher that drops privileges on
subsequent starts. The account's home is `/var/lib/simjecture`; no permissions on
`/root` or host namespace restrictions are relaxed. A custom installation path
must be accessible to that account. Existing installations without this account
marker are left untouched rather than silently migrated.
PRoot also requires host support for tracing child processes. A container can block
both user namespaces and ptrace, so installing PRoot is not a guaranteed workaround.
If both probes fail, use a supported host, a configured SSH execution worker, or
explicitly select trusted native process execution as described below. The GUI,
recorded-demo replay and benchmark
task preparation can still be used; grading executes code and requires a working
backend. Do not relax host security settings merely to make a probe pass.

Root execution itself never qualifies for this fallback. Explicit backend requests and
existing studies are not silently changed.

Check the actual host before launching:

```sh
simjecture doctor --execution-backend bubblewrap
```

If the host cannot permit namespaces, install PRoot through the OS package
manager and `simjecture[process]`, then run under a dedicated **non-root** account:

```sh
simjecture doctor --execution-backend proot-cooperative
simjecture study --campaign studies/example \
  --hypothesis-file hypothesis.txt --instructions-file instructions.txt \
  --backend codex --model mimo-v2.6-pro --executable codex-mimo \
  --execution-backend proot-cooperative --capabilities /path/to/capabilities
```

The model/provider name above is an example; use your configured agent and a
credential plan that permits your intended use. The execution backend does not
change the provider's usage terms.

The cooperative backend provides path remapping, a clean child environment,
private temporary directories, copied and hash-checked declared inputs,
output collection, wall-time limits, file-size limits, and a sampled aggregate
resident-memory watchdog. Every execution receipt names its isolation backend.
The study persists the choice; changing it requires a new study. Existing
records without the field continue to mean Bubblewrap.

## Explicit trusted native processes

This option is an unreleased source-checkout addition after 0.5.3.

PRoot can pass a basic probe while failing a larger MPI launch. On the audited P40
host, the same 16-rank collective completed natively but hung under PRoot, including
TCP and disabled-seccomp variants. Changing the declared slot count alone did not
repair that failure.

`process-cooperative` runs trusted experiments directly under a dedicated non-root
account, without PRoot or namespaces:

```sh
simjecture doctor --execution-backend process-cooperative
simjecture study --campaign studies/example \
  --hypothesis-file hypothesis.txt --instructions-file instructions.txt \
  --backend codex --execution-backend process-cooperative
```

The browser offers **Native process · trusted host** in the study execution selector
and machine advanced settings; the TUI offers the same explicit choice. Automatic
selection still probes Bubblewrap then PRoot and never silently selects native
execution. A study freezes its choice. SSH workers still drop privileges before
execution; root is refused.

The native runner copies and checks declared inputs, clears the child environment,
uses a private temporary directory, monitors aggregate RSS and cleans up recorded
descendants on cancellation or parent death. It translates registered virtual paths
in command arguments and environment variables to host paths. Programs should use
workspace-relative inputs and provided runtime environment variables such as
`FLASH_ROOT`; hard-coded `/opt/acs-*` paths inside source text are not rewritten.
Declared input copies have write bits removed and are checked after execution.
The worker account can change those bits: this detects cooperative mutations, not
hostile code. Runtime/source immutability depends on host filesystem permissions.

The process has the account's host file and network access. CPU reservations are
admission accounting, not affinity or cgroup quotas. RSS checks are sampled, and
GPU VRAM is not bounded. Use this only when that trust boundary is acceptable.
Native research agents retain their existing tools regardless of experiment backend.

**It is not a security sandbox.** Host networking is shared; PRoot is not a
kernel permission boundary, read-only bindings are not OS-enforced, and a
malicious program could escape the path view or inspect same-user processes.
Run only trusted/cooperative experiment code on a dedicated account, without
unrelated sensitive files. Native research agents retain their own tools.

CUDA reserves large virtual address ranges. Cooperative execution uses a large
address-space ceiling plus an RSS watchdog instead of treating GPU virtual
reservation as resident RAM. The watchdog is sampled and can overshoot; it is
not a cgroup hard memory guarantee. GPU VRAM has no independent harness limit.

CLI, browser, and TUI native studies support this selection. A browser host may
explicitly set `SIMJECTURE_DEFAULT_EXECUTION_BACKEND=proot-cooperative`; the UI
shows that default, and it is stored in the launch contract. An explicit environment
setting takes precedence over automatic workspace selection and is checked before use. Browser host
setup can similarly set `SIMJECTURE_DEFAULT_BACKEND`, `SIMJECTURE_DEFAULT_MODEL`,
and `SIMJECTURE_DEFAULT_CAPABILITIES`. Legacy DSH/API launch forms do not select
this backend; use native study modes for this route.

## Provider interruptions

Native supervision reconnects after transient provider exits, stream failures,
rate limits, and service overloads until the **original absolute deadline**.
Backoff grows from two seconds to a sixty-second cap; pause, cancellation, and
the deadline remain active during waiting. Codex sessions retain their thread
cursor; other adapters retain their durable files and experiment receipts.
Retries do not recreate the study or reset its experiment ledger.

Confirmed authentication, permission, model-configuration, and exhausted-credit
errors pause for operator attention. Malformed scientific reviews and harness
errors retain a bounded retry policy; they are not mistaken for network outages.

State records distinguish retry count, time spent in backoff, and elapsed time
in failed provider turns. These are measured operational counters, not an exact
measurement of all provider downtime or billing. The current budget is wall
clock: outages count toward it. An active-work budget would be a separate future
policy and must retain an absolute deadline; this change does not introduce it.
