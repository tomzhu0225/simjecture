# Simjecture for DeepSeek Harness

This profile bundle gives DeepSeek Harness (DSH) one scientific tool surface
backed by the model-independent Simjecture campaign kernel. DSH owns the model
loop, provider, retries, conversation compaction, resumable session history,
and final response.
Simjecture remains authoritative for the hypothesis DAG, evidence contracts,
commissioning, provenance, sandbox, and durable simulation jobs.

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

The integration is pinned to DSH `0.1.1-rc.2`. Pack it outside the repository
or remove the generated tarball after installation:

```bash
npm pack ./integrations/dsh --pack-destination /tmp
dsh plugin --profile simjecture add @deepseek-ai/dsh-headless@0.1.1-rc.2
dsh plugin --profile simjecture add /tmp/simjecture-dsh-bundle-0.2.0-rc.2.tgz
```

The dedicated profile is important: its base/headless composition lets this
bundle disable generic shell, filesystem, web, skill, workflow, and subagent
tools. Installing only the host row into DSH's standard Web agent preset would
also leave that preset's coding tools available.

The profile sets DSH approval to `never`; this does not bypass Simjecture's
policy. The only remaining scientific side effects are typed MCP actions checked
by CampaignKernel and executed in its sandbox. Provider/model choice is still a
DSH setting and is not hard-coded by this bundle.

One route-specific operational policy is included: because
`deepseek-official/deepseek-v4-flash` advertises a one-million-token window, its
tool-heavy campaign history compacts at 10% pressure with a 3% retained tail.
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
scientific finish gate passes. The researcher cannot call the two raw
adjudication endpoints: it sees one composite tool that freezes the evidence
case, starts a fresh tool-free child with a strict verdict schema, and commits
that independent result. Capability jobs,
including a configured WarpX capability, return quickly with a durable job id.
The agent follows them through `job_status`. Each worker authenticates its
durable receipt against the original request, so a DSH or MCP restart can
recover a known result without rerunning the simulation. A missing or invalid
receipt remains an unknown process outcome and cannot become scientific
evidence. The restart snapshot reports every bounded durable job ID and the
remaining budget. DSH compaction and process resume preserve the event-sourced
model history, while the first resumed action reconciles it with this
authoritative snapshot. Calendar time while the MCP process is stopped does not
consume active execution budget.

## Direct bridge diagnosis

`simjecture-mcp` speaks MCP over standard input/output and is not a human REPL.
Use an MCP client to perform initialize, list-tools, and call-tool. A healthy
server advertises 21 explicit endpoints. The DSH researcher sees 19 of them;
the other two are scoped away and used only by the adjudication composite.
Start with `snapshot`; do not interpret a job result until `job_status` reports
a terminal receipt.
