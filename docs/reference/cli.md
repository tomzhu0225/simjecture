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
- `mvp`: natural-language sandbox campaign with claims and capabilities;
- `status`: compact read-only snapshot of a durable MVP run directory;
- `watch`: follow durable MVP events until a terminal report or pause;
- `pause`: request an action-boundary pause of a verified live runner;
- `resume`: repeat a stored launch contract for a paused or incomplete run;
- `web`: local research workspace and campaign monitor; the composer selects
  a native CLI or configured built-in API agent. `--engine` selects the legacy
  campaign engine, not the default workspace agent;
- `serve`: optional hosted workspace with visitor admission, GitHub sign-in and
  an operator-managed queue (`pip install 'simjecture[public]'`). General execution
  requires a private Unix HTTP socket and a separately commissioned Linux broker;
  see [server mode](../how-to/public-trials.md);
- `study`: minimal, structured or frontier studies with recorded launch contracts;
- `steer`: advisory guidance for an existing minimal study;
- `llm-benchmark`: prepare, grade, run and publish recorded-diagnostic coding tasks
  (distinct from the simulation `benchmark` command);
- `tui`: optional interactive dashboard (`uv sync --extra tui`);
- `benchmark`: deterministic planted scientific benchmarks;
- `campaign`: durable bounded campaign execution;
- `orchestrate`: fixed-DAG multi-action research campaigns;
- `package verify`: independently verify a discovery package;
- `schemas`: export or check public JSON Schemas.

Use each subcommand's `--help` output as the authoritative option reference. CLI
defaults are tested and versioned with the source; documentation examples avoid
duplicating the complete argument surface.

For live campaigns, prefer hypothesis and instruction files over long shell
arguments so the exact operator input can be reviewed before launch.
`--instruction-file` is accepted for the same reason. The primary Web client
and maintenance-mode TUI both launch through structured input files and never
build a shell command from hypothesis text.

`web`, `status`, `watch`, `pause`, and `resume` do not require the TUI extra. `watch`
Ctrl-C stops the viewer only. `pause` never uses SIGSTOP. `resume` replays every
structured option only for a contained, self-contained launch contract; unsafe
external paths are refused. See
[Web interface](../getting-started/web-interface.md) and
[Terminal interface](../getting-started/terminal-ui.md).


## Native-agent studies

For a complete setup and automation recipe, see [Run a headless study](../how-to/headless-studies.md).

`simjecture study --campaign DIR --hypothesis-file H --instructions-file I`
starts minimal mode by default. Add `--mode structured` or `--mode frontier` for
another workflow. `--backend` selects `codex-glm`, `codex`, `grok`, `agy` or
`builtin`; non-GLM backends require an explicit `--model`. Native CLI tools remain
available. `builtin` uses a private `--provider-config` file and requires the
workspace extra; it supports minimal mode only. Keep provider credentials out of
committed files and shared records.
`--wall-seconds` fixes the study budget and `--turn-seconds` controls the native
session allowance/watchdog. Resume with the same campaign and instructions;
mode and deadline are preserved. `--continue-from` instead creates a new minimal
phase with a fresh explicit budget and selected context; see
[continuation and steering](../how-to/continuation-steering.md). `simjecture-supervise` and `simjecture-research`
are equivalent launchers. The browser and TUI share the same native mode choices. Legacy `mvp` and DSH/API
remain explicit legacy routes. See [the guide](../how-to/research-service.md).

Minimal studies can select `--machine-registry DIR --machine ID`, repeating
`--machine` to choose a pool. Placement and resource requests are recorded by
`Lab.run`; local execution remains the default when no pool is selected.

New minimal studies default to `--director`; `--no-director` disables strategy
control for that launch. `--judge-model` and `--judge-reasoning-effort` choose
the director and independent reviewer route. Existing studies preserve their saved
policy on resume. See [stop and replan](../how-to/minimal-oversight.md#research-director-stop-and-replan).
