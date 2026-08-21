# Simjecture for DeepSeek Harness

This patch-only bundle gives DeepSeek Harness (DSH) one scientific tool
surface backed by the model-independent Simjecture campaign kernel. DSH owns
the model loop, provider, retries, session history, and final response.
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
dsh plugin --profile simjecture add /tmp/simjecture-dsh-bundle-0.2.0-rc.1.tgz
```

The dedicated profile is important: its base/headless composition lets this
bundle disable generic shell, filesystem, web, skill, workflow, and subagent
tools. Installing only the host row into DSH's standard Web agent preset would
also leave that preset's coding tools available.

The profile sets DSH approval to `never`; this does not bypass Simjecture's
policy. The only remaining scientific side effects are typed MCP actions checked
by CampaignKernel and executed in its sandbox. Provider/model choice is still a
DSH setting and is not hard-coded by this bundle.

Inspect the resolved profile before a campaign:

```bash
dsh --profile simjecture --dump-config
```

The dump must show `mode: native`, `approval.policy: never`, the matching
`simjecture` permission preset, `mcp-simjecture`, the explicit `SIMJECTURE_*`
environment, and the bypass rows as disabled. Missing workspace or hypothesis
variables fail profile activation.

Run a one-shot autonomous campaign with:

```bash
dsh --profile simjecture \
  'Test the supplied root hypothesis. Continue through commissioning, simulation, evidence review, and subhypothesis refinement until the evidence supports a defensible stopping point.'
```

The MCP child exposes no generic shell and no `finish` tool. Capability jobs,
including a configured WarpX capability, return quickly with a durable job id.
The agent follows them through `job_status`. Each worker authenticates its
durable receipt against the original request, so a DSH or MCP restart can
recover a known result without rerunning the simulation. A missing or invalid
receipt remains an unknown process outcome and cannot become scientific
evidence. The restart snapshot reports every bounded durable job ID and the
remaining budget. Calendar time while the MCP process is stopped does not
consume active execution budget.

## Direct bridge diagnosis

`simjecture-mcp` speaks MCP over standard input/output and is not a human REPL.
Use an MCP client to perform initialize, list-tools, and call-tool. A healthy
server advertises 18 explicit tools. Start with `snapshot`; do not interpret a
job result until `job_status` reports a terminal receipt.
