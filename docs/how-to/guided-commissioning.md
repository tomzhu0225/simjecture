# Guided commissioning

Use guided commissioning when constructing a trustworthy starting simulation is
expensive but a validated anchor already exists.

The package declares:

- the capability and exact successful command;
- supplied files and their hashes;
- a compact validation summary;
- an optional concise protocol named by `protocol_path`, containing the
  prospective command sequence, diagnostics, controls, and stopping rules;
- limitations and permitted reuse;
- the operator statement describing what was validated.

Run with:

```bash
uv run simjecture mvp \
  --hypothesis-file hypothesis.txt \
  --guided-commission guided_commission.json \
  --output artifacts/guided-campaign
```

The harness snapshots the input package outside the writable workspace. The
workspace copy may be inspected or revised, but the original handoff remains
recoverable.

Guided material is a starting instrument, not scientific evidence for the new
hypothesis. The agent must still register prospective contracts, commission any
new or changed program, and execute fresh claim-bearing observations.

Omit `--guided-commission` for a skills-only commissioning baseline. Supply it
when the research question should begin from an expert-validated instrument or
protocol. Reports preserve which mode was used, so guided and unguided runs can
be compared without presenting them as the same level of autonomy.

Validate package structure against
`schemas/MVPGuidedCommissioningSpec.schema.json` before an expensive launch.

## Guided native studies and a separate readiness budget

The native `study` launcher accepts the same package in minimal, structured,
and frontier modes:

```bash
uv run simjecture study --mode minimal \
  --campaign artifacts/guided-study \
  --hypothesis-file demos/resistive_mhd_island_coalescence/hypothesis.txt \
  --instructions-file demos/resistive_mhd_island_coalescence/campaign_instruction.txt \
  --guided-commission demos/resistive_mhd_island_coalescence/guided_commission.json \
  --capabilities /path/to/installed-capabilities \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

Minimal mode snapshots the original files outside the writable research directory,
checks their hashes on reopen, and includes the package descriptor in worker and
reviewer context. Workspace copies can be adapted. Resume without resupplying the
package; an explicitly different package is rejected. A guided package cannot be
added to an already launched minimal study. Supplied validation outputs remain
context, never fresh observations. Do not list an output as an input to `lab.run`.

First reproduce the instrument with a separate, bounded, **model-free** readiness
run. This command executes the exact packaged command through the registered
capability and experiment sandbox; it does not launch a research agent:

```bash
uv run python -m conjecture_solver.research_guidance \
  --guided-commission demos/resistive_mhd_island_coalescence/guided_commission.json \
  --capabilities /path/to/installed-capabilities \
  --output artifacts/island-readiness --wall-seconds 600
```

Use a fresh output directory. On a restricted host, explicitly select
`--execution-backend proot-cooperative`. Inspect `readiness.json` and the actual
experiment outputs. Passing means the packaged anchor ran and passed its declared
checks; it does not independently validate its physics, new geometry, or research
claim. A copied, pre-existing validation summary is excluded from experiment
inputs. The output is permanently exploration-stage.

Within a guided minimal study, `lab.reproduce_anchor(timeout=600)` submits that
exact command as a recorded exploratory experiment. It excludes the supplied
validation summary from inputs, refuses modified package files, and returns the
same receipt on an unchanged retry. Adaptations use ordinary `lab.run`.

A useful anchor includes the exact solver setup, a tested output reader, the
relevant observable, output cadence, expected checks, measured runtime, and
limitations. A generic executable smoke test is insufficient when the research
question needs a different geometry or diagnostic. Commission that new instrument
in its own bounded development exercise before budgeting a long hypothesis study.

## Incremental methods review in minimal mode

Use `lab.method(..., scope="instrument")` for a narrowly declared readiness
checkpoint, such as analytic magnetic diffusion or an HDF5 coordinate-map reader.
The host first requires a successful recorded validation matching the proposed
source, inputs and runtime; an empty plan or stale run cannot establish readiness.
The reviewer judges that capability and names its limitations; it should not demand
an unrelated completed production matrix. A positive instrument review is recorded
but **cannot authorize `stage="evidence"`**, even with identical source hashes.

Use `scope="production"` (the default, also applied to older method records) when
the implemented instrument can measure the hypothesis. Production approval allows
fresh evidence collection; it does not require that the future comparison matrix
has already been executed, and it never decides the scientific conclusion.
Scientific support still requires counterexample attempts and the applicable
prospective commitments and independent claim review.
