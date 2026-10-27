# Demonstration: 2D resistive-MHD island coalescence with FLASH

## Fresh v0.7.0 investigation

The fresh 25 October investigation independently falsified the slope band
[-0.55, -0.45], with p = -0.3778 and a numerical interval [-0.4314, -0.3247].
The explanatory repair remains unvalidated.

Read the [current investigation](../../docs/demos/island-coalescence.md),
[original input](fresh_v070_record/operator_input/hypothesis.txt),
[scientific report](fresh_v070_record/research/RESULTS.md), and
[compact audit](fresh_v070_record/manifest.json). The new `fresh_v070_record/`
and `fresh_v070_visual_data/` preserve the fresh run separately from earlier work.

```bash
uv run python scripts/verify_research_audit.py demos/resistive_mhd_island_coalescence/fresh_v070_record
uv run --extra flash-demo python scripts/render_fresh_plasma_examples.py
```

The audit includes the exact operator instructions, commissioning inputs,
agent-owned sources, execution receipts and independent review decisions. Bulk
solver states are omitted with hashes; verification checks retained bytes rather
than rerunning the physics. A new agent investigation needs qualified local
capabilities and a configured backend.

## Earlier minimal records and guided FLASH anchor

Everything below describes the guided FLASH starting instrument and the earlier
minimal-workflow investigations, whose inputs, compact audits and outcomes are
retained. See the [historical walkthrough](../../docs/demos/island-coalescence-historical.md).

## Scientific question

The supplied root hypothesis asks whether the two-dimensional,
uniform-resistivity, compressible single-fluid MHD island-coalescence model
has one pre-plasmoid Sweet–Parker-like branch over the nominal control range

\[
S_\eta = 1/\eta \in [250,4000], \qquad
R \propto S_\eta^p, \qquad -0.60 \le p \le -0.40,
\]

with the inferred exponent persisting under a spatial-resolution refinement.
Here `S_eta` is a normalized inverse-resistivity control, not a dimensional
Lundquist number. The observable is the normalized reconnection rate defined
in the frozen campaign protocol; the fit uses only cases that reach the flux
window, resolve the sheet, remain pre-plasmoid, and pass the linearity check.

This is a statement about one explicitly bounded numerical model. A result
here is not a universal disproof of Sweet–Parker theory, and this FLASH
single-fluid capability cannot answer kinetic electron-scale questions.

## What is in the repository

| Path | Purpose |
| --- | --- |
| [`hypothesis.txt`](hypothesis.txt) | Exact natural-language root hypothesis for the earlier minimal studies |
| [`minimal_instructions.txt`](minimal_instructions.txt) | Operational instructions for minimal-workflow island-coalescence studies |
| [`minimal_requirements.json`](minimal_requirements.json) | Recorded minimal-workflow requirements |
| [`guided/island_coalescence.py`](guided/island_coalescence.py) | Contained launcher and validator for the operator-supplied FLASH executable |
| [`guided_commission.json`](guided_commission.json) | Frozen guided-commission manifest and limitations |
| [`guided/anchor_validation.json`](guided/anchor_validation.json) | Checked-in validation summary; permanently non-evidentiary |
| [`guided/operator_validation.json`](guided/operator_validation.json) | Separate manufactured-solution/operator check; permanently non-evidentiary |
| [`fresh_v070_record/`](fresh_v070_record/) | Fresh v0.7.0 minimal study audit with accepted root falsification |
| [`minimal_record/`](minimal_record/), [`sol_medium_record/`](sol_medium_record/), [`continuation_record/`](continuation_record/) | Preserved earlier minimal-workflow audit extracts |
| [`postrun_coordinate_check.py`](postrun_coordinate_check.py) | Analytic and post-run coordinate-consistency diagnostic check |

The raw `guided/anchor_run/` directory is ignored by Git because FLASH output
is large and depends on the operator's installation.

## Guided FLASH anchor

The bundled manifest records the exact validated starting command. In its
realized run it used:

| Quantity | Realized value |
| --- | --- |
| Model | 2D compressible single-fluid resistive MHD |
| Resistivity | explicit, uniform, `eta = 0.001` |
| Nominal control | `S_eta = 1000` |
| Grid | `128 x 128` |
| MPI layout | 4 ranks (`2 x 2`) |
| End time | `tmax = 1.2` |
| Plot states | 24 HDF5 files |
| Flux window | `psi_rec = 0.01` to `0.05` reached |
| Maximum recorded `|div B|` | `9.36e-13` |
| Anchor status | `permanently_non_evidentiary` |

The anchor demonstrates that the supplied capability can run, write readable
states, expose the requested resistive path, and produce the declared
diagnostics. It does not establish a scaling, convergence, or physical law.

The operator must obtain and build FLASH under its upstream license. No FLASH
source, binary, or modification is redistributed here. Set the launcher and
executable explicitly, then run the contained program from the repository
root:

```bash
uv sync --extra flash-demo

export FLASH_EXECUTABLE=/path/to/flash4
export FLASH_MPI_LAUNCHER=/path/to/orterun

uv run python demos/resistive_mhd_island_coalescence/guided/island_coalescence.py \
  --eta 0.001 --nx 128 --ny 128 --alpha 20 --tmax 1.2 \
  --plot-interval 0.05 --ranks 4 --iprocs 2 --jprocs 2 \
  --output demos/resistive_mhd_island_coalescence/guided/anchor_run \
  --summary demos/resistive_mhd_island_coalescence/guided/anchor_validation.json \
  --overwrite
```

The command rewrites only the marked anchor directory. The validation summary
records the executable and parameter-file hashes so the operator can audit
which local FLASH build produced the states.

## Launching a fresh minimal study

After installing and commissioning FLASH on the local machine, launch a new
minimal-workflow investigation from the repository root:

```bash
uv run simjecture study \
  --campaign artifacts/my-island-minimal \
  --hypothesis-file demos/resistive_mhd_island_coalescence/hypothesis.txt \
  --instructions-file demos/resistive_mhd_island_coalescence/minimal_instructions.txt \
  --requirements-file demos/resistive_mhd_island_coalescence/minimal_requirements.json \
  --guided-commission demos/resistive_mhd_island_coalescence/guided_commission.json \
  --capabilities /path/to/qualified/capabilities \
  --backend codex --model gpt-6.1-sol --reasoning-effort medium \
  --judge-model gpt-6.1-sol --judge-reasoning-effort high \
  --mode minimal --completion-policy repair --wall-seconds 3600 --director
```

### Visual walkthrough and continuation

The separate `continuation_record/` preserves the earlier 30-minute continuation;
the parent records are unchanged. `visual_data/` contains compact plotting arrays
with source hashes, selected-frame metadata and the original scientific/report
status. These operator-rendered figures do not add a scientific verdict.

From the repository root, redraw the field sequences, patch view, pressure maps
and evidence maps without solver runs or model calls:

```bash
uv run --extra flash-demo python scripts/render_plasma_walkthroughs.py
```

The renderer writes PNG, PDF and SVG to `docs/_static/demos/`. It verifies the
plotting-bundle hashes and checks pressure-map means against the recorded analysis.
