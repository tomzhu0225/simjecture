# Compare scientific coding agents

**Simjecture Bench 0.1.0** is an experimental task pack shipped with 0.5.3rc1.
Its version is independent of the harness version. It packages finite diagnostic
coding tasks from the aluminium RZ investigation; passing does not establish a
physical mechanism, approve a scientific claim, or measure general research ability.

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
LLM judge for scientific conclusions and is not a cheating-resistant leaderboard.

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
