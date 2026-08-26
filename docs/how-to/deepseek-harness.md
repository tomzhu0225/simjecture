# Run a Simjecture campaign under DSH

The DSH integration is a native-tool profile plus a small resumable driver for
a durable Simjecture campaign. Version 0.2.2 uses a persistent Lead Scientist
and fresh, claim-scoped Falsifier, Repair Scientist, and tool-free Judge
sessions. Fresh workers see bounded kernel state rather than inherited chat.
The Python MCP process is the only scientific tool surface: it exposes campaign
state, claims, evidence contracts, skills, literature metadata, workspace files,
and bounded jobs. Generic shell, filesystem bypass, and unguarded `finish` tools are
disabled by the profile wherever the host DSH version supports disabling them.
The profile also sets DSH's approval policy to `never`: all remaining scientific
side effects already cross the typed CampaignKernel policy and Bubblewrap
boundary, so no second routine permission loop is inserted around MCP calls.

## Provision the two runtimes

Provision the Python environment and any WarpX installation on the host first;
the bundle intentionally installs neither runtime. From the repository root:

```bash
uv sync --extra dsh
source .venv/bin/activate
```

`mcp>=2,<3` is optional. It is imported only when `simjecture-mcp` starts, so
schema and kernel-fake tests do not need the extra.

Ordinary users do not set the bridge variables themselves. The Web launcher
records the hypothesis and execution envelope first, generates a stable DSH
session identity, and supplies contained paths to the profile. The variables
below are shown only to make that process boundary auditable:

```bash
mkdir -p runs
printf '%s\n' 'The initial scientific hypothesis goes here.' > hypothesis.txt
export SIMJECTURE_WORKSPACE="$PWD/runs"
export SIMJECTURE_CAMPAIGN="demo"
export SIMJECTURE_HYPOTHESIS_FILE="$PWD/hypothesis.txt"
export SIMJECTURE_CAPABILITIES="$PWD/capabilities"
export SIMJECTURE_SKILLS="$PWD/skills"
export SIMJECTURE_MCP_MAX_OUTPUT_CHARS=30000
export SIMJECTURE_MCP_TIMEOUT_SECONDS=600
export SIMJECTURE_DSH_SESSION_ID=simjecture-demo
export SIMJECTURE_DSH_SESSION_ROOT="$PWD/runs/demo/operator_input/dsh_sessions"
export SIMJECTURE_DSH_ACTIVITY_FILE="$PWD/runs/demo/operator_input/dsh_activity.jsonl"
export SIMJECTURE_DSH_STATE_FILE="$PWD/runs/demo/operator_input/dsh_state.json"
export SIMJECTURE_DSH_CONTROL_FILE="$PWD/runs/demo/operator_input/control.json"
```

The bridge uses these values for the MCP child process. It never accepts a
generic shell command or a host-wide absolute workspace path from a tool call.

## Pack and install the DSH profile

The profile bundle lives in `integrations/dsh` in a checkout and is also shipped
inside the Python wheel. Resolve, validate, and pack that copy, then install the
resulting local bundle into the isolated harness profile:

```bash
SIMJECTURE_DSH_PROFILE="$(simjecture dsh-profile)"
npm pack "$SIMJECTURE_DSH_PROFILE" --pack-destination /tmp
dsh plugin --profile simjecture add @deepseek-ai/dsh-headless@0.1.1-rc.2
dsh plugin --profile simjecture add /tmp/simjecture-dsh-bundle-0.2.2.tgz
```

For a checkout-only development install, use the directory directly when the
CLI supports local plugin paths:

```bash
dsh plugin --profile simjecture add "$PWD/integrations/dsh"
```

The bundle pins the tested DSH prerelease and MCP-client prerelease in its
`package.json`. Keep the lockfile produced by `npm pack`/the DSH plugin manager
with the deployment artifact; do not silently widen either range.

DSH `0.1.1-rc.2` requires Node.js `^22.19.0` or `>=24.0.0`. Install the DSH CLI
according to its upstream instructions and verify that `dsh` is on `PATH`
before installing this isolated profile.

## Inspect the resolved configuration

Before starting a long campaign, ask DSH to render the merged profile. The
exact option name is `--dump-config` in the prerelease CLI:

```bash
dsh --profile simjecture --dump-config
```

Confirm that the native MCP client is named `simjecture`, starts
`simjecture-mcp`, carries the `SIMJECTURE_*` environment, and has
`failOnStartupError: true`. Also confirm `approval.policy: never`, the
`simjecture` permission preset (`workspace-write` plus `never`), and that the
generic tool rows are disabled. A startup or handshake failure should stop the
scientific profile rather than silently fall back to a bypass tool.

Completed large execution and workspace-write exchanges stay fully visible for
one model request. At a later step the profile may replace the balanced exchange
on the model-facing surface with a deterministic receipt containing stable
identifiers, selected status fields, sizes, and hashes. Other oversized tool
results receive deterministic head/tail pruning. Both are model-free, and all
original events remain in the append-only DSH log and Simjecture's durable
artifacts.

The tested `deepseek-official/deepseek-v4-flash` route advertises a one-million-
token context window. The Simjecture profile performs semantic compaction for
that exact route at 50% pressure and retains a 3% verbatim tail; DSH defaults
remain in force for other routes. This is a context threshold, not a campaign
token quota: scientific work continues until a durable stop condition or the
operator's wall/action budget is reached.

The bundle intentionally does not select a scientific reasoning model. Inspect
the resolved `agent-default-model` row and configure the desired provider/model
through DSH's profile settings or a later local patch.

## Launch through the Web interface

After the profile has been installed and inspected, use the ordinary Simjecture
entry point:

```bash
uv run simjecture web
```

New browser campaigns use DSH by default. Recorded-run viewing needs neither
Node.js nor DSH, and `uv run simjecture web --engine native` retains the built-in
runner for compatibility and diagnosis. Pause and resume use the same Web and
CLI controls; resume opens the stable DSH session stored under
`operator_input/dsh_sessions` rather than starting an empty conversation.

The MCP server also supports a direct smoke launch when diagnosing the host:

```bash
simjecture-mcp --workspace "$SIMJECTURE_WORKSPACE" \
  --campaign "$SIMJECTURE_CAMPAIGN" \
  --hypothesis-file "$SIMJECTURE_HYPOTHESIS_FILE"
```

That command speaks MCP over stdio and expects an MCP client; it is not a
human-facing REPL. Use DSH's initialize/list-tools/call-tool trace to verify the
21 explicit MCP endpoints before submitting work. The persistent lead sees six
tools: two durable reads, fresh falsification and repair delegation, independent
adjudication, and guarded finalization. Each worker receives a narrower tool
surface plus a claim-scoped argument guard. Raw judge prepare/commit operations
are private to the adjudication composite.

`observation_sufficient=true` means that a linked artifact satisfies its
selected prospective contract; it is not a researcher-issued support verdict.
Falsifiers may record that contract compliance but cannot close a scientific
claim as supported. The adjudication composite refuses to start a Judge without
at least one qualifying link under the selected contract.

The Judge returns record completeness and scientific disposition separately.
For example, `decision=sufficient` with
`scientific_disposition=instrument_limited` means that the blocker record is
complete; it does **not** support the hypothesis. A `claim_decision` contract can
admit a supported or falsified disposition. A `terminal_record` contract can
admit only `instrument_limited` or `unresolved`. An insufficient record names
the missing evidence and returns the campaign to the falsification loop while
wall time remains.

Long-running actions have caller-supplied operation identifiers and return
durable jobs. Under DSH the waiter checks `job_status` below the model surface,
so one submitted run produces one terminal tool result instead of repeated
polling turns. An interrupted wait leaves the job durable and recoverable; it
never resubmits. A direct MCP client must perform these status reads itself.
Authenticated receipts let a restarted client recover known results, while
absent or invalid receipts remain `outcome_unknown`. A fresh `snapshot` includes
a bounded durable job list and remaining action/active-execution budget.
The campaign wall-time envelope charges time while its DSH researcher process
is active, including model and tool waits. The kernel additionally records
actual tool and simulation execution for durable recovery and per-command
limits. Calendar time while DSH and the MCP process are stopped is not charged.

One root MCP process owns the campaign for its lifetime. A second DSH profile or
the legacy runner fails closed instead of alternating writes through stale
in-memory ledgers. Detached simulation workers are the only exemption and use
the kernel's durable active-job lease.

## Scientific operating rule

Register a prospective evidence contract before linking an observation. Skill
materialization, literature results, workbench jobs, and partial jobs are
guidance or process metadata, not evidence. After a meaningful falsification
search, use the isolated adjudicator instead of self-certifying support. A
rejected package returns evidence gaps. An accepted package may close the claim
under its explicit scientific disposition, but `finalize_campaign` writes a
conclusion only after the global finish gate passes. A falsified frontier needs
a `repairs` child; an honestly complete blocker may close as
`instrument_limited` or `unresolved`. Preserve the durable campaign directory as
the immutable hand-off artifact. If later review finds an error, append a
corrective audit record rather than editing the original ledger, transcript, or
report.
