# Command-line reference

The primary command is `simjecture`; `conjecture-solver` and `acs` are
compatibility aliases.

The distribution is named `simjecture`. The Python import namespace remains
`conjecture_solver` so existing capability and integration code does not need to
change as part of the product rename.

```bash
uv run simjecture --help
```

Principal command families:

- `install`: idempotently provision or verify a selected runtime profile;
- `machines`: register, prepare, check and inspect local/SSH numerical workers
  (from 0.5.3rc2; [SSH guide](../how-to/ssh-workers.md));
- `doctor`: inspect core and optional capability health, with JSON output;
- `status`: compact read-only snapshot of a durable research directory;
- `watch`: follow durable research events until a terminal report or pause;
- `pause`: request an action-boundary pause of a verified live runner;
- `resume`: repeat a stored launch contract for a paused or incomplete run;
- `web`: local research workspace and campaign monitor; the composer selects
  a native CLI or configured built-in API agent;
- `serve`: optional hosted workspace with visitor admission, GitHub sign-in and
  an operator-managed queue (`pip install 'simjecture[public]'`). General execution
  requires a private Unix HTTP socket and a separately commissioned Linux broker;
  see [server mode](../how-to/public-trials.md);
- `study`: minimal research with recorded launch contracts;
- `attention`: inspect optional Conjecture 1 scientific-attention tooling, write an
  example config, verify a resident model service or score an observation
  ([scientific attention](../how-to/scientific-attention.md));
- `steer`: advisory guidance for an existing minimal study;
- `llm-benchmark`: prepare, grade, run and publish recorded-diagnostic coding tasks
  (distinct from the simulation `benchmark` command);
- `benchmark`: deterministic planted scientific benchmarks;
- `campaign`: durable bounded campaign execution;
- `orchestrate`: fixed-DAG multi-action research campaigns;
- `package verify`: independently verify a discovery package;
- `schemas`: export or check public JSON Schemas.

Use each subcommand's `--help` output as the authoritative option reference. CLI
defaults are tested and versioned with the source; documentation examples avoid
duplicating the complete argument surface.

`simjecture study limits --campaign PATH` inspects operating allowances. Add
`--limits-file FILE --reason TEXT` to update them without changing the scientific
contract or campaign deadline. The same control is **Run settings** in the browser;
see [operating settings](../how-to/operating-limits.md).

For live campaigns, prefer hypothesis and instruction files over long shell
arguments so the exact operator input can be reviewed before launch.
`--instructions-file` is accepted by `study` for the same reason. The Web client
and CLI both launch through structured input files and never
build a shell command from hypothesis text.

`web`, `status`, `watch`, `pause`, and `resume` are included in the core package. `watch`
Ctrl-C stops the viewer only. `pause` never uses SIGSTOP. `resume` preserves the saved minimal launch contract and absolute deadline.
Classical, DSH, structured and frontier runs cannot be resumed in this release. See
[Web interface](../getting-started/web-interface.md).


## Native-agent studies

For a complete setup and automation recipe, see [Run a headless study](../how-to/headless-studies.md).

`simjecture study --campaign DIR --hypothesis-file H --instructions-file I`
starts a minimal study. Minimal is the only supported workflow. `--backend` selects `codex-glm`, `codex`, `grok`, `agy` or
`builtin`; non-GLM backends require an explicit `--model`. Native CLI tools remain
available. `builtin` uses a private `--provider-config` file and requires the
workspace extra; it supports minimal mode only. Keep provider credentials out of
committed files and shared records.
The built-in API agent uses smolagents directly. API output-token budgets use provider defaults unless the private
provider profile explicitly sets `max_tokens`.
API research workers retain the preceding turn's structured tool calls and results
alongside the current evidence brief. Their action limit creates an incomplete
checkpoint, not a research conclusion or an extra model-generated summary.
Older evidence remains in project files, receipts and the research journal;
independent reviewers receive separate contexts.
`--wall-seconds` fixes the study budget and `--turn-seconds` controls the native
session allowance/watchdog. Set `--max-experiment-bytes` and `--max-total-bytes`
for the initial per-experiment and aggregate logical storage allowances; the total
must cover at least one experiment. Set `--report-reserve-seconds` to a positive
value smaller than the wall budget to reserve time for final reporting. Omitted
options retain existing defaults. Resume with the same campaign and instructions;
initial allowances, report reserve, mode and deadline are preserved. Explicitly
changing an initial allowance or report reserve on resume is rejected. Storage
allowances are logical limits, not a guaranteed physical free-space reserve. `--continue-from` instead creates a new minimal
phase with a fresh explicit budget and selected context; see
[continuation and steering](../how-to/continuation-steering.md). `simjecture-supervise` and `simjecture-research`
are equivalent launchers. The browser also launches minimal studies.
Removed workflows are described in the [migration guide](../how-to/minimal-migration.md).

For an active minimal study, `simjecture study budget --campaign DIR` reads the
authoritative clock and `simjecture study extend --campaign DIR --hours 12
--request-key KEY` grants additional time without restarting the supervisor.
See [live budget extensions](../how-to/extend-study.md) for the operator API,
agent requests, audit records and individual experiment limits.

Minimal studies can select `--machine-registry DIR --machine ID`, repeating
`--machine` to choose a pool. Placement and resource requests are recorded by
`Lab.run`; local execution remains the default when no pool is selected.

New minimal studies default to `--director`; `--no-director` disables strategy
control for that launch. `--judge-model` and `--judge-reasoning-effort` choose
the director and independent reviewer route. Existing studies preserve their saved
policy on resume. See [stop and replan](../how-to/minimal-oversight.md#research-director-stop-and-replan).
