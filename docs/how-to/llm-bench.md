# Compare scientific coding agents

**Simjecture Bench 0.3.0** is the experimental task pack shipped with 0.5.3.
Its version is independent of the harness version. It packages finite diagnostic
coding tasks from the aluminium RZ investigation; passing does not establish a
physical mechanism, approve a scientific claim, or measure general research ability.

The current pack uses qualified tracer interpolation and float64 reductions. The [owned 42-configuration sweep](../testing/owned-llm-benchmark-20261001.md)
contains actual timing, delivery and usage results from 252 scheduled attempts;
unavailable provider observations and affected earlier qualifications stay unranked.

## Prepare a task

Open **Benchmarks** in the workspace sidebar. Choose **Prepare conversation**,
select your agent/model in the new conversation, and send the prepared request.
Preparation makes no provider request. The agent retains its normal tools.
After it finishes, return to **Benchmarks** and choose **Grade delivered results**.
The result explains failed numerical checks and preserves unknown usage counters.
Grading uses the machine's selected execution backend; it never runs submitted code
directly inside the referee process. Cooperative PRoot remains a trusted-code profile.

Interactive preparation is an exploratory entry point, not a timed leaderboard
runner. It does not impose a new chat deadline. For controlled timed trials, use
the exported task with a runner that enforces the declared budget.

The equivalent CLI is:

```bash
simjecture llm-benchmark list
simjecture llm-benchmark prepare csv-energy --output ./bench/csv
# Give bench/csv/TASK.md to your coding agent; it writes its files in bench/csv.
simjecture llm-benchmark grade csv-energy --submission ./bench/csv \
  --output ./bench/csv-grade.json --model YOUR_MODEL --agent YOUR_AGENT
```

Outputs must be new preparation directories; existing files are not overwritten.
The grader returns exit code 0 for a passing contract, 1 for a failed/incomplete
submission and 2 for a setup error. Bubblewrap is the CLI default. On a dedicated
unprivileged machine with restricted namespaces, explicitly select
`--execution-backend proot-cooperative`. This changes execution isolation, not the
task contract. Stop the agent before grading or changing immutable inputs.

## Choose a task

| Task | Suggested agent budget | Input and required work |
|---|---:|---|
| `csv-energy` | 180 s | Two recorded CSV cases; reduce escaped radiation and radiation-stage energy loss, report their difference. |
| `rz-diagnostics` | 900 s | Two recorded 64×4 and 128×4 RZ cases, 401 HDF5 frames each; reduce inward kinetic energy, tracer compression and radiation windows; deliver numerical plot data and grid differences. |

Both tasks use actual solver diagnostics and three freshly generated numerical
holdouts. The holdouts vary energies, clocks and group counts; RZ holdouts also test
leaf/covered blocks and velocity signs. They are arithmetic controls, not additional
simulations. Runtime strings, machine metadata, solver binaries, licensed source
and EOS/opacity tables are excluded. Original and packaged hashes are retained in
`conjecture_solver/llm_bench/data/provenance.json`.

The CSV task requires the base package. The RZ task additionally requires h5py,
included in `simjecture[workspace]` or `simjecture[flash-demo]`. No FLASH installation
is needed to replay recorded diagnostics. Every metric and output schema is defined
in the generated `TASK.md`; do not silently mix this task version with the earlier
live simulation pilot.

The host independently reruns `reduce.py`, checks saved results against its own
reductions, verifies immutable inputs and checks numerical plot-data arrays. It
renders canonical RZ plots after a pass. Agent PNG appearance and scientific prose
are not graded; nonempty findings are only a delivery check. This preview has no
LLM judge for scientific conclusions. The development leaderboard below is a
comparison of declared trials, not a cheating-resistant public submission service.

## Leaderboard and tradeoffs

The default page is **Official Simjecture results**, a maintained publication of
the owned sweep. It has exactly two task tabs: RZ plasma diagnostics and radiation
energy accounting. The older CSV entries were the same task under qualification
versions and a local runner, not four scientific tasks; they now live in
the retained audit downloads; current custom runs appear in **Community & local**.

Select **Rank by** completion, fastest verified completion or lowest cost per
attempt. Column headings also change the sort. The table shows numerical checks
separately from the complete delivery contract, and published input/output USD
tariffs per million tokens separately from the cost of an attempt. Time rank uses
median verified completion, so a timed-out attempt is not ranked as fast.
Cost rank uses mean API-equivalent cost across all graded attempts, including
failures. This remains defined when a model never completed the task.

Three plots are visible for each task: finish-time ranked bars, cost ranked bars,
and a cost–time Pareto plot. Bars sort completed configurations from lower to
higher values. Unfinished configurations appear last in **red**, without a verified finish-time rank. Their cost bars show recorded spending, including labelled **≥** lower bounds. Configurations that never reached inference are omitted from the public charts and table. Missing tariffs and partial cost receipts do not receive a cost rank.

In the Pareto plot, cost increases from left to right and verified finish time
increases from top to bottom: **the upper-left corner is better**. It includes
completed configurations with comparable cost estimates. Outlined points mark the observed two-objective frontier; no line joins different models. Each model has a distinct colour shared across the plots and model legend. This describes the
sample, including one-trial RZ observations; it does not establish statistical
superiority. Dashed lines connect reasoning efforts for the same model and coding
agent. Search, effort filters and clickable series names focus all three plots.
Cost uses a logarithmic axis. Hover or focus a point for its measurements.

The separate valuation ledger recovers counters from saved traces while preserving
original host grades. AGY estimates explicitly treat its input and cache-read
counters as disjoint and never add thinking tokens twice. They are labelled
estimates, not billing receipts. Interrupted requests show **≥** recorded cost
and receive no cost rank or effort connection. The optional uncached basis applies
full input tariffs to recorded cached tokens. Standard short-context tariffs,
cache storage exclusions and counter interpretations are stated in Methodology.
GPT-OSS uses a labelled Groq reference tariff because open weights have no single
hosting price. GPT Reserve is a dynamic router with no fixed model tariff.
Grok Build Fast uses its published CLI token tariff, since that profile has no
public API endpoint.

View the [standalone publication](../_static/benchmark-leaderboard.html), or export
a self-contained HTML page for hosting or sharing. It includes the curated results,
filters, rankings and plots; it needs no server, login, model request or import:

```bash
simjecture llm-benchmark export-page --output ./leaderboard.html
```

The workspace includes a leaderboard in **Benchmarks**.
Task preparation and grading remain available. **Run your model** starts fresh
timed trials using an installed coding CLI or the API coding agent configured in
Connections. Enter any supported model ID, choose its effort, select one or both
tasks, and choose repetitions. No registration in a fixed model list is needed.
The page polls progress and imports final host grades automatically.
**Import grades** accepts individual host grades or a `{ "reports": [...] }` bundle.
**Download grades** produces a portable, sanitized bundle; **Export summary** downloads an aggregate with
no submitted code, private settings, paths, transcripts or reasoning text. This
includes per-trial timing/usage counters and source report hashes so aggregate
denominators and cost calculations can be inspected.
The summary
does not upload anything publicly. Regrading or reimporting one trial does not add
another repetition. Fresh trials require fresh preparation directories.

Choose a comparison group to hold task/pack/contract, prompt, hardware, execution
backend, harness, runner version, budget and continuation policy fixed. Each row
identifies model/version, agent/version and settings, including reasoning effort.
Compare different agents as complete configurations; select a single agent/version
when attributing differences to a model. There is no overall cross-task score.

The API coding agent retains the installed harness defaults: DeepSeek uses native
tool history, while MiMo uses the default smolagents history formatter. Each API
request allows 8192 output tokens and each episode allows 24 action steps; the
timed runner continues incomplete episodes within the original deadline. CLI
agents retain their native system prompts, tools and default internal limits.
These differences are part of the tested configurations, so cross-backend results
cannot be attributed solely to model weights.

- Pass rate uses all delivered trial grades, with a 95% Wilson interval.
  A numerical pass first verified after the declared deadline counts as a timed
  failure. Do not omit unsuccessful or interrupted attempts: collect their host
  grades as well. A setup error without a grade is not silently scored as success.
- Time per success is all trial elapsed time divided by verified successes;
  median first verified completion time describes passing trials separately.
- Cost per success includes spending on failed attempts. **API tokens** is a dated
  standard API equivalent; **Reported $** is operator-supplied actual spending.
  Grok Build Fast uses its separately published CLI token rates; it is not
  available through the public xAI API. Its rate estimate is also separate from
  subscription fees and reported spending.
  Subscription fees, credits and discounts are not inferred from token counters.
- **Quality × time** uses pass rate and mean elapsed time per attempt, so it can
  include configurations without billing data. **Cost × time** uses token cost
  and elapsed time per verified success, with colour showing pass rate.
  Its Pareto calculation considers all three quantities. Hover/focus a point for
  its measurements; activate it to select the corresponding row.
- In the archive summary, fewer than five repetitions remain provisional and receive no Pareto status.
  The frontier is descriptive; five trials do not establish statistical
  superiority. Missing timings, versions or protocol fields remain visibly
  unranked. Missing usage never becomes zero cost. No model receives an entry
  merely because its price is listed.

The initial USD price snapshot was checked on **2026-10-01** against
[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Grok 4.7](https://docs.x.ai/developers/models/grok-4.7),
[Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/pricing), and
[DeepSeek Flash/Pro](https://api-docs.deepseek.com/quick_start/pricing/).
It uses standard short-context rates, DeepSeek peak rates and Gemini's introductory
rates through 2026-12-31. It excludes hosted-tool charges, cache storage, hardware,
regional/service premiums and subscription discounts. OpenAI estimates require
cache-write counts and a reported maximum request input of at most 272K; Grok
requires at most 200K. Larger or unidentified tiers stay unknown. The total output
counter must already include billed reasoning tokens; its reasoning subset is not
added a second time. A snapshot is not a historical invoice; keep the pricing
metadata with exported comparisons.

For a controlled runner, pass measurements through `grade --metadata trial.json`:

```json
{
  "model": "gpt-6.1-sol",
  "model_version": "gpt-6.1-sol",
  "agent": "codex",
  "agent_version": "RECORD_INSTALLED_VERSION",
  "settings": {"reasoning_effort": "high", "service_tier": "standard"},
  "comparison": {
    "protocol": "controlled",
    "budget_seconds": 180,
    "hardware": "RECORD_FIXED_HARDWARE",
    "harness_version": "RECORD_INSTALLED_VERSION",
    "runner_version": "RECORD_INSTALLED_VERSION",
    "prompt_sha256": "REPLACE_WITH_64_HEX_DIGITS",
    "continuation_policy": "original-deadline-generic"
  },
  "wall_seconds": null,
  "first_verified_completion_seconds": null,
  "input_tokens": null,
  "cached_input_tokens": null,
  "cache_write_input_tokens": null,
  "output_tokens": null,
  "requests_without_usage": null,
  "max_request_input_tokens": null,
  "reported_cost_usd": null
}
```

Replace placeholders with the runner's records; do not invent unknown counters.
For development builds, include the Git commit in the harness/runner version
labels so different implementations do not share a comparison group.
Record first verified completion around the host verifier call, not the agent's
completion message. A runner can fill that field in the returned grade after the
first verification. Trial identity and task contract hashes are assigned by the
host. A controlled label is an operator/runner declaration, not a certification
of deadline enforcement or submission isolation.

```bash
simjecture llm-benchmark grade csv-energy --submission ./trial-1 \
  --output ./trial-1-grade.json --metadata ./trial-1-metadata.json
simjecture llm-benchmark leaderboard --reports ./trial-*-grade.json \
  --output ./leaderboard.json
```

The MiMo/DeepSeek live-simulation pilot below remains a separate evaluation. Its
task, environment and one-off observations cannot populate this pack's controlled
leaderboard. Earlier pilots and verifier qualifications remain in the audit records and reports; they are not panels on the public leaderboard. The public page has only time bars, cost bars and the cost–time plot.
New comparisons require fresh trials. Starting timed trials uses the operator's
configured subscription/API credits. Published host grades ship with the task pack;
local trials and community imports keep their declared comparison conditions.
Community execution and billing declarations are not independently certified.

### Run a custom model from the terminal

Create a configuration array, for example:

```json
[
  {"id":"sol-high", "backend":"codex", "model":"gpt-6.1-sol", "effort":"high"},
  {"id":"custom-api", "backend":"builtin", "model":"YOUR_MODEL_ID",
   "provider_config":"/absolute/path/to/private-provider.json"}
]
```

The private provider file contains `model`, `backend`, `base_url`, `api_key`, and optionally
`protocol: "native-tools"`. Keep it outside a public submission; native CLI trials
use their existing login. Supported backends are `codex`, `codex-glm`, `grok`, `agy`
and `builtin`. AGY uses its model-profile ID for effort; Codex accepts its native
effort levels, including `ultra` where the installed model supports it.

```bash
simjecture llm-benchmark run --config models.json --output ./model-trials \
  --repeats 5 --workers 4
```

Use `--workspace /path/to/runs/.workspace` to import grades into an existing GUI,
`--tasks csv-energy` to run one task, or `--numerical-python /path/to/python` to
select the agent's numerical environment. Private traces and provider files stay
local; share only `trials/*/public-grade.json` or the GUI's **Download grades**.
Submit a result bundle under `src/conjecture_solver/llm_bench/results/community/`
with a pull request and describe your hardware, software,
agent settings and runner protocol. A community result is not relabelled as a
Simjecture-owned measurement.
Accepted community bundles are loaded automatically into separate
`community-controlled` comparison groups. Imported external GUI grades use that
label too; reimporting a known local grade preserves its existing identity.

### Pack 0.2.0 correction

Qualification exposed an ambiguity in 0.1.0's half-mass-radius definition:
interpolating individual equal-radius cells depends on their order. Version 0.2.0
sums mass at each distinct radius before interpolation and specifies the
after-reference radiation subtraction explicitly. Oracle controls and shuffled
equal-radius tests verify the repaired definition. Affected 0.1.0 qualifications
remain visible, marked invalidated for ranking; they are not silently regraded.

Pack **0.3.0** also promotes recorded float32 fields to float64 before products and
reductions. The old reference rounded density × tracer mass before summing; two
independent model implementations using float64 were rejected despite agreeing
with each other. Independent Python scalar shell integrals now check this case,
and their curves match the repaired reference exactly. Affected 0.2.0 RZ grades
remain unranked qualifications. Fresh 0.3.0 trials use an explicit float64 contract.

The timed runner gives every configuration the same failed public-case field
labels when continuing, without expected numbers or hidden-fixture contents.
The original deadline includes grading and reserves ten seconds for final
verification. Native tools and system prompts remain enabled. This measures the
whole coding-agent configuration on recorded diagnostics, not new simulation
performance or a pure model-only score. Native agents are trusted to obey the
no-verifier-inspection contract; their normal filesystem access is retained.
The numerical verifier executes submitted reducers separately under Bubblewrap.

AGY conversation usage is cumulative: successive totals must not be added.
Original grades leave token cost unknown where cache/input semantics are not
verified. The separate published valuation ledger applies the explicitly labelled
interpretation described above; those estimates are not measured invoices. Interrupted
requests and unaccounted delegated work also leave complete cost unknown;
known partial counters remain visible. API-equivalent estimates are not
subscription invoices.

## Export for Harbor

```bash
simjecture llm-benchmark export csv-energy --output ./harbor-tasks/csv-energy
simjecture llm-benchmark export rz-diagnostics --output ./harbor-tasks/rz-diagnostics
```

The export follows [Harbor's task format](https://docs.harborframework.com/core-concepts/tasks/overview):
instructions, Docker environment, task configuration, verifier and oracle solution.
It requests schema 1.3, an unprivileged agent with public networking, a fixed timeout,
and a [separate verifier container](https://docs.harborframework.com/core-concepts/tasks/separate-verifier).
Only declared artifacts transfer to the verifier. The verifier runs submitted code
under an unprivileged UID and retains grading authority in its root process; its
test code and reference reductions are not included in the agent image.

Use a Harbor version supporting those features and a working Docker host. Configure
your provider through that runner's existing native agent integration. No new paid
API scheduler is added to Simjecture. Run oracle and no-op controls before paid
trials. The local release checks cover task export/configuration and native isolated
grading; a full Docker/Harbor trial was not run on the release machine, which has no
Docker runtime. Treat the exporter as experimental rather than certified deployment.

## Record a fair comparison

Keep model, native agent/version, prompt, task version, budget, continuation policy,
thinking/output limits, execution profile and hardware fixed or explicitly reported.
Continuation must retain the original deadline and use a generic progress reminder,
not a hand-written solution hint. Use multiple fresh trials, randomize model order
and report failures as well as successes. Compare models within one fixed harness
separately from comparisons of whole agent frameworks.

Record first verified completion time, solver time when applicable, input/output
tokens, cached input, reasoning output and requests with unknown usage. Exported
native-agent traces use that runner's accounting; Simjecture request receipts apply
to its builtin provider. Null usage means unavailable, not zero. Manual CLI identity
metadata is not a provider invoice. Do not share keys, private reasoning or raw
credential-bearing transcripts in public benchmark exports.

The [MiMo/DeepSeek pilot](../testing/mimo-flash-comparison.md) used a different live
task contract and one main trial per model. It motivated this pack; it is not a
leaderboard or a statistically established completion-rate comparison.

## Add live simulation work

A live FLASH variant requires an operator-owned, qualified runtime, its exact
experiment launcher and immutable source/template/table hashes. Reuse the existing
[guided commissioning](guided-commissioning.md) and [research service](research-service.md)
to check that exact launcher before assigning a fresh simulation. Freeze executable,
inputs, grids, duration, diagnostic cadence and comparison definitions, while keeping
agent and solver timing separate. Publish that as a new task version with its own
oracle/no-op validation. The included replay tasks do not claim live commissioning
or redistribute a FLASH capability from a private machine.
