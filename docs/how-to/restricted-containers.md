# Running inside a restricted container

Scientific modes (`minimal`, `structured`, `frontier`) are independent of the
experiment execution backend. Bubblewrap remains the default. Simjecture never
silently switches to weaker isolation when namespace creation fails.

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
shows that default, and it is stored in the launch contract. This environment
setting configures the form, not an invisible execution fallback. Browser host
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
