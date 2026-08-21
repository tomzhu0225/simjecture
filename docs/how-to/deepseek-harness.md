# Run a Simjecture campaign under DSH

The DSH integration is a native-tool profile for a durable Simjecture campaign.
The Python MCP process is the only scientific tool surface: it exposes campaign
state, claims, evidence contracts, skills, literature metadata, workspace files,
and bounded jobs. Generic shell, filesystem bypass, and `finish` tools are
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

Set the campaign boundary explicitly before launching DSH. The workspace is
the parent of the named campaign directory, and the hypothesis is supplied by
a host-owned text file:

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

The bridge uses these values for the MCP child process. It never accepts a
generic shell command or a host-wide absolute workspace path from a tool call.

## Pack and install the DSH profile

The patch-only bundle lives in `integrations/dsh`. Validate and pack it with
the DSH CLI from the repository root, then install the resulting local bundle
into the profile you use for the harness:

```bash
npm pack ./integrations/dsh --pack-destination /tmp
dsh plugin --profile simjecture add @deepseek-ai/dsh-headless@0.1.1-rc.2
dsh plugin --profile simjecture add /tmp/simjecture-dsh-bundle-0.2.0-rc.1.tgz
```

For a checkout-only development install, use the directory directly when the
CLI supports local plugin paths:

```bash
dsh plugin --profile simjecture add "$PWD/integrations/dsh"
```

The bundle pins the tested DSH prerelease and MCP-client prerelease in its
`package.json`. Keep the lockfile produced by `npm pack`/the DSH plugin manager
with the deployment artifact; do not silently widen either range.

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

The bundle intentionally does not select a scientific reasoning model. Inspect
the resolved `agent-default-model` row and configure the desired provider/model
through DSH's profile settings or a later local patch.

The MCP server also supports a direct smoke launch when diagnosing the host:

```bash
simjecture-mcp --workspace "$SIMJECTURE_WORKSPACE" \
  --campaign "$SIMJECTURE_CAMPAIGN" \
  --hypothesis-file "$SIMJECTURE_HYPOTHESIS_FILE"
```

That command speaks MCP over stdio and expects an MCP client; it is not a
human-facing REPL. Use DSH's initialize/list-tools/call-tool trace to verify
the 18 explicit tools before submitting work. Job results are bounded and must
be checked with `job_status` before interpreting them as observations. Each
long-running action has a caller-supplied operation identifier. The detached
worker writes an authenticated durable receipt, allowing a restarted DSH/MCP
client to recover a known result without rerunning the simulation; absent or
invalid receipts remain `outcome_unknown`. A fresh `snapshot` includes a bounded
durable job list (with operation IDs) and remaining action/active-execution
budget, so it is sufficient to rediscover and poll work from a lost session.
Only actual tool and simulation execution is charged to the wall envelope;
time while DSH and the MCP process are stopped is not.

One root MCP process owns the campaign for its lifetime. A second DSH profile or
the legacy runner fails closed instead of alternating writes through stale
in-memory ledgers. Detached simulation workers are the only exemption and use
the kernel's durable active-job lease.

## Scientific operating rule

Register a prospective evidence contract before linking an observation. Skill
materialization, literature results, workbench jobs, and partial jobs are
guidance or process metadata, not evidence. Close claims with a disposition and
reason, and preserve the durable campaign directory as the hand-off artifact.
