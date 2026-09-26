# Simjecture

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21945748.svg)](https://doi.org/10.5281/zenodo.21945748)

**Hypothesize. Simulate. Falsify.**

Simjecture is a research harness for computational science. An agent writes and runs
experiments, searches for counterexamples, and proposes small, testable repairs to
failed hypotheses. The harness records what actually ran and requires independent
review before a scientific claim can close.

**v0.5.1 is a research preview.** Minimal mode is the default: agents keep their
native tools and choose their research strategy, while Simjecture manages recorded
evidence, review and deadlines. Structured and frontier modes remain available.
The system does not establish physical truth from a successful simulation or promise
that a long agent run will produce a useful result.

## Start a study

Use Linux with Python 3.11+, [uv](https://docs.astral.sh/uv/), and an installed,
authenticated native agent CLI. Bubblewrap is the default numerical execution backend.

```bash
uv tool install 'simjecture[tui]==0.5.1'
simjecture install core
simjecture doctor --execution-backend bubblewrap

simjecture study --campaign ./runs/my-study \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

Write a falsifiable hypothesis in `hypothesis.txt`. In `instructions.md`, specify
physical scope, available instruments, resource limits and the evidence needed to
accept or reject it. Configure provider credentials in your agent's own credential
store, outside the study directory. The model name must match that configuration.

A terminal launch shows activity, backend/model, remaining time and experiment/review
counts. Inspect the same study in either interface:

```bash
simjecture web ./runs/my-study
simjecture tui ./runs/my-study
```

Resume using the same campaign path and launch options. Its recorded mode and original
wall deadline remain fixed. A normal agent exit or inconclusive result does not mark
research complete. Transient provider disconnects retry with backoff until the deadline;
authentication, permission and exhausted-quota errors pause for attention. Waiting for
a provider counts against wall time.

See [minimal-mode usage](docs/how-to/research-service.md),
[terminal progress](docs/getting-started/terminal-ui.md) and the
[browser interface](docs/getting-started/web-interface.md).

## Choose the agent, workflow and execution backend separately

| Choice | Options | What it controls |
|---|---|---|
| Native agent | `codex-glm`, `codex`, `grok`, `agy` | CLI, configured provider/model, login and native tools |
| Research mode | `minimal` (default), `structured`, `frontier` | How scientific work is organized |
| Numerical execution | `bubblewrap` (default), `proot-cooperative` | How recorded experiment processes execute |
| Legacy engine | DSH or built-in API routes | Existing campaign integrations; separate from native-study modes |

Use `--mode structured` or `--mode frontier` for another workflow. Minimal lets the
agent organize its investigation around a small evidence API; structured uses explicit
claim-scoped roles and contracts; frontier gives a persistent researcher control of
the classic claim tree. Existing campaigns retain their recorded semantics.

Native agents retain their own shell, search, file and configured provider tools.
They are trusted, cooperative processes on the study host; they are **not** enclosed
by the numerical experiment sandbox. Simjecture's supplied tools record experiments,
provenance and reviews. Native scratch work is not automatically scientific evidence.

If namespaces are unavailable, explicitly select `--execution-backend proot-cooperative`
on a dedicated non-root account. It provides execution bookkeeping and limits, **not
an OS security boundary**. Simjecture never silently falls back to it. See
[restricted containers](docs/how-to/restricted-containers.md).

[DSH integration](docs/how-to/deepseek-harness.md) remains available with native research
tools and a governed MCP boundary. [Simote integration](docs/how-to/simote-agent-roles.md)
is optional; Simjecture can run independently on a local or remote host. Deployment
to a remote host does not itself create a multi-machine experiment scheduler.

## What minimal mode enforces

The agent chooses hypotheses, code, diagnostics and the next discriminating experiment.
The host maintains the scientific record:

- **Immutable question and scope.** Operator requirements cannot be waived by a worker
  or reviewer. Repairs preserve ancestry and explain each changed assumption or bound.
- **Recorded execution.** Commands, declared inputs, runtime identity and output hashes
  accompany each experiment. Interrupted attempts remain visible.
- **Commissioning before evidence.** Instrument-backed studies receive source-bound
  methods review. Exploration and supplied examples cannot be relabelled as new evidence.
- **Counterexample search and fresh repairs.** Support includes an actual challenge
  attempt. Repaired predictions are committed before their fresh tests.
- **Independent acceptance.** A methods approval permits evidence collection; it does
  not accept a scientific claim. Unconverged, censored or missing results are not
  physical counterexamples.
- **Persistent context.** The host maintains an experiment journal and bounded research
  brief. Evidence-linked notes and comparisons help retain failed approaches and findings.
- **Bounded work.** The original deadline survives restart. Cancellation uses durable job
  records and reports unresolved cleanup rather than assuming that agent exit stopped
  every computation.

A study completes when its original claim is independently supported, or when a
falsified original leads to an independently supported repair with the required
ancestry. A deadline may end the campaign unresolved; that is recorded, not promoted
to a success.

See [methods and progress oversight](docs/how-to/minimal-oversight.md),
[research memory](docs/how-to/research-memory.md) and
[evidence and claims](docs/concepts/evidence-and-claims.md).

## Begin with a working scientific instrument

For expensive solver setup, provide a guided commissioning package: exact working
source and command, output reader, observable, validation checks, runtime and known
limitations. Reproduce that anchor in a separate bounded readiness run before spending
hours on hypothesis testing.

```bash
simjecture study --campaign ./runs/guided-study \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --guided-commission /path/to/guided_commission.json \
  --capabilities /path/to/installed-capabilities \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

Guided examples are starting instruments, not fresh evidence for the new hypothesis.
An executable smoke test does not validate a new geometry or diagnostic. The
[guided commissioning guide](docs/how-to/guided-commissioning.md) explains readiness
budgets, immutable anchors and instrument versus production review.

Optional instruments include WarpX CPU/CUDA, operator-supplied FLASH, and EOS/opacity
capabilities. For example:

```bash
simjecture install warpx-cpu
simjecture doctor --profile warpx-cpu
```

FLASH source is not redistributed. Solver source inspection can be configured separately
from a writable problem/build area. See [runtime deployment](docs/how-to/deploy-runtimes.md)
and the [scientific skills](skills/).

## What v0.5.1 changes

This release builds on v0.5.0's minimal default and shared interfaces:

- Methods/progress oversight, stalled-session recovery and deadline-bounded provider retry.
- Automatic research journaling, bounded context and evidence-linked comparisons.
- Guided anchors in native studies and explicit cooperative execution for restricted hosts.
- Updated FLASH/Python skills with guided-study, HDF5 and decision-rule lessons.
- Preserved instrument ownership across classic assignment rollover.
- Explicit unmet review prerequisites; conditional approval cannot open the evidence gate.
- Numerical checks for contradictory prospective acceptance bounds.
- Output eligibility annotations exposed for review without forcing metadata-only solver reruns.
- Durable cancellation cleanup independent of CLI-response parsing.

The [changelog](CHANGELOG.md) and [repair report](research/evaluations/guided-model-comparison-2026-09-26/RESULTS.md)
include validation and remaining limitations. General reuse of raw solver data under
independently versioned analysis still needs a fuller provenance API.

## Measured evidence and limitations

Minimal is the default by design preference, not a demonstrated universal performance
advantage. The latest [MiMo v2.6 Pro / DeepSeek V4.1 Flash comparison](docs/research/llm-comparison.md)
found faster useful progress with DeepSeek in a guided minimal FLASH study, but **no
independently accepted scientific conclusion** from either model configuration.
Unequal duration, different provider tool protocols and one trial per configuration
limit that comparison. Token totals distinguish cached input, uncached input and
output; they are not billed-cost estimates.

| Recorded evaluation | What can be inspected |
|---|---|
| [Gray–Scott](demos/gray_scott_counterexample/) | A completed 23.8-minute finite-domain counterexample campaign, programs, numerical evidence and replay |
| [Collisionless GEM](demos/collisionless_gem_reconnection/) | 12 fresh CUDA runs; finite-sample child falsification with an unresolved population root |
| [FLASH island coalescence](demos/resistive_mhd_island_coalescence/) | Working guided anchor, real fields and a historical audit; the repair remained open |
| [Guided model comparison](research/evaluations/guided-model-comparison-2026-09-26/) | MiMo/DeepSeek progress, usage, harness failures and corrective tests |

The historical FLASH narrative recorded an exponent-band falsification with an interval
that overlaps the allowed band. That overlap alone does not establish such falsification;
the earlier summary is not independently endorsed here. Provenance enables inspection,
but cannot make a faulty scientific decision correct.

Replay a completed example without an API key or new simulations:

```bash
git clone https://github.com/tomzhu0225/simjecture.git
cd simjecture
uv sync --frozen
uv run python demos/gray_scott_counterexample/verify_record.py
uv run simjecture web demos/gray_scott_counterexample/record --read-only
```

![Gray–Scott recorded numerical evidence](docs/_static/demos/gray-scott-result.png)

## Documentation and development

Start at [the documentation index](docs/index.md). Linux release assets include a
launch archive with matching Python/DSH packages, setup scripts and SHA-256 checksums.
Native-agent setup does not require installing DSH.

```bash
uv sync --all-groups --extra tui --extra dsh
uv run ruff check .
uv run pytest
uv run simjecture schemas --output schemas --check
uv run --group docs sphinx-build -W -b html docs docs/_build/html
```

`conjecture-solver` and `acs` remain compatibility aliases. The Python package remains
`conjecture_solver`. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md)
and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Citation and license

Use [CITATION.cff](CITATION.cff) and cite the exact version and Git commit used for a
result. The [concept DOI](https://doi.org/10.5281/zenodo.21945748) identifies the software
release series.

Copyright 2026 Bowen Zhu and contributors. Licensed under the
[Apache License 2.0](LICENSE).
