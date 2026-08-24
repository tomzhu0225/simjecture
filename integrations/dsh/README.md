# Simjecture for DeepSeek Harness

This profile bundle makes DeepSeek Harness (DSH) the model/session runtime for
the model-independent Simjecture campaign kernel. DSH owns model routing,
retries, fresh child sessions, semantic compaction, resumable history, and the
final response. Simjecture remains authoritative for the hypothesis DAG,
evidence contracts, commissioning, provenance, sandbox, and durable simulation
jobs.

Version 0.2.2 separates scientific work into four scopes:

- a persistent, compact **Lead Scientist** reads durable state and delegates;
- a fresh **Falsifier/Experimenter** commissions and tests exactly one open
  scientific claim;
- a fresh **Repair Scientist** turns an accepted counterexample into one
  minimal contracted repair claim; and
- a fresh, tool-free **Judge** decides whether a surviving falsification case
  is sufficient.

The workers receive bounded state packets, not the lead's accumulated chat.
Their name-filtered tool sets are backed by claim-scoped mutation guards and
their handoffs are checked against the durable kernel before the lead sees them.

The npm bundle does not install the Python environment, Bubblewrap, WarpX, or
another simulation runtime. Provision those host capabilities first.

## Provision Simjecture

From the Simjecture checkout:

```bash
uv sync --extra dsh
source .venv/bin/activate
```

Create a plain-text hypothesis file and select an explicit campaign boundary:

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
```

With those values the durable campaign directory is `runs/demo`. On resume,
the hypothesis file must exactly match the immutable root stored there.

## Pack and install an isolated profile

The integration is pinned to DSH `0.1.1-rc.2`. `simjecture dsh-profile` resolves
the same bundle from either a source checkout or an installed wheel. Pack it
outside the repository or remove the generated tarball after installation:

```bash
SIMJECTURE_DSH_PROFILE="$(simjecture dsh-profile)"
npm pack "$SIMJECTURE_DSH_PROFILE" --pack-destination /tmp
dsh plugin --profile simjecture add @deepseek-ai/dsh-headless@0.1.1-rc.2
dsh plugin --profile simjecture add /tmp/simjecture-dsh-bundle-0.2.2.tgz
```

The dedicated profile is important: its base/headless composition lets this
bundle disable generic shell, filesystem, web, skill, workflow, and subagent
tools. Installing only the host row into DSH's standard Web agent preset would
also leave that preset's coding tools available.

The profile sets DSH approval to `never`; this does not bypass Simjecture's
policy. The only remaining scientific side effects are typed MCP actions checked
by CampaignKernel and executed in its sandbox. Provider/model choice is still a
DSH setting and is not hard-coded by this bundle.

Two context policies are included. Completed large tool exchanges remain
verbatim for one model request and may then be replaced on the model-facing
surface by a deterministic receipt; oversized results receive the same
model-free head/tail pruning. The original events remain byte-for-byte in DSH's
append-only log and the durable Simjecture artifacts. Separately, because
`deepseek-official/deepseek-v4-flash` advertises a one-million-token window, its
tool-heavy campaign history compacts at 50% pressure with a 3% retained tail.
All other provider/model routes retain DSH's stock compaction policy.

Inspect the resolved profile before a campaign:

```bash
dsh --profile simjecture --dump-config
```

The dump must show `mode: native`, `approval.policy: never`, the matching
`simjecture` permission preset, `mcp-simjecture`, the explicit `SIMJECTURE_*`
environment, and the bypass rows as disabled. Missing workspace or hypothesis
variables fail profile activation.

After installation, let Simjecture create the immutable launch contract and
stable session identity. The normal browser command is unchanged:

```bash
uv run simjecture web
```

New browser campaigns select DSH by default. The Python supervisor passes the
hypothesis by contained file rather than process argument, stores the DSH event
log beside the campaign, and reopens the same session on **Resume**.
`uv run simjecture web --engine native` is the explicit compatibility path.

The MCP child exposes no generic shell and no unguarded `finish` tool. Its
`finalize_campaign` endpoint can write a report only after CampaignKernel's
scientific finish gate passes. The lead sees only snapshot, claims, the three
role composites, and finalization. Each child receives only the tools required
for its assignment; the two raw judge prepare/commit endpoints remain private
to the adjudication composite.

Capability jobs, including configured WarpX capabilities, still return a
durable job ID immediately at the kernel boundary. The DSH waiter performs the
read-only lifecycle checks inside that same tool execution and exposes only the
terminal bounded report to the worker. Poll traffic therefore does not create
model turns. Cancellation detaches from the durable job rather than resubmitting
or guessing its outcome. An authenticated receipt lets a restarted DSH/MCP
client recover a known result without rerunning the simulation; a missing or
invalid receipt remains `outcome_unknown` and cannot become evidence.

## Direct bridge diagnosis

`simjecture-mcp` speaks MCP over standard input/output and is not a human REPL.
Use an MCP client to perform initialize, list-tools, and call-tool. A healthy
server advertises 21 explicit endpoints. The persistent lead sees six tools;
the fresh role composites expose narrower task-specific subsets, while raw
judge operations stay private. A direct MCP client must still reconcile a job
with `job_status`; the DSH profile performs that wait automatically.

A link marked `observation_sufficient=true` records that the artifact satisfies
its selected contract; it does not declare scientific support. The Falsifier
can make that bounded statement, but only the fresh Judge can authorize support.
Adjudication is rejected before a Judge is started when no qualifying link could
pass the kernel's deterministic closure gate.
