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
- `doctor`: inspect core and optional capability health, with JSON output;
- `mvp`: natural-language sandbox campaign with claims and capabilities;
- `status`: compact read-only snapshot of a durable MVP run directory;
- `watch`: follow durable MVP events until a terminal report or pause;
- `pause`: request an action-boundary pause of a verified live runner;
- `resume`: repeat a stored launch contract for a paused or incomplete run;
- `web`: local browser dashboard and reviewed campaign controls;
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
`--instruction-file` is accepted for the same reason. The optional TUI always
launches through `--hypothesis-file` and never builds a shell command.

`web`, `status`, `watch`, `pause`, and `resume` do not require the TUI extra. `watch`
Ctrl-C stops the viewer only. `pause` never uses SIGSTOP. `resume` replays every
structured option only for a contained, self-contained launch contract; unsafe
external paths are refused. See
[Web interface](../getting-started/web-interface.md) and
[Terminal interface](../getting-started/terminal-ui.md).
