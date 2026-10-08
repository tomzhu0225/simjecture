# Magnetic-island coalescence with FLASH

**Can one resolved reconnection-rate scaling describe a resistive-MHD island
coalescence model across its declared resistivity range?** This plasma example
connects a real FLASH simulation, field diagnostics, numerical qualification and
an autonomous attempt to test a scaling hypothesis.

## Read the plasma fields

![Four fresh 384 by 384 FLASH snapshots showing density, magnetic field lines and current-sheet evolution](../_static/demos/island-field-walkthrough.png)

The upper row shows density with magnetic field lines; the lower row shows the
out-of-plane current. Follow the central current sheet across the four actual
output times. Each row uses a shared color scale. These fields come from the
fresh $S_\eta=1000$, $384^2$ refinement run—not the older commissioning example.
[Download PDF](../_static/demos/island-field-walkthrough.pdf) ·
[Open SVG](../_static/demos/island-field-walkthrough.svg).

## Follow the evidence

![Actual island-coalescence evidence map: five base cases, two matched refinements and the unresolved original hypothesis](../_static/demos/island-evidence-map.png)

The 30-minute continuation completed **all five $256^2$ baseline cases and both
planned $384^2$ refinements**. The rate changes under refinement were 0.136% at
$S_\eta=250$ and 0.223% at $S_\eta=1000$. The two-point endpoint exponents were
−0.42793 and −0.42730. Those matched points are consistent with the stated band;
they do not establish its persistence across the full range.

The five-point base-grid fit gave −0.40785, with slight curvature that did not
fit the chosen 1% error boxes. Only two common refined points were available,
so the curvature test could not be repeated on the refined grid. **The original
hypothesis remains unresolved.** No repair claim was accepted.

The map summarizes actual experiment receipts and relationships. It is an
editorial evidence map; the formal claim graph still contains the open original
claim. Method approval permits evidence collection and is separate from claim
approval. Final postprocessing was recorded as exploration after a changed-input
binding blocked its evidence-stage submission. The report reviewer timed out,
so the original narrative remains unreviewed, including its stale pending-analysis
passage. The quantities above are read from the completed analysis receipt.
[Download evidence-map PDF](../_static/demos/island-evidence-map.pdf).

| Follow a figure or result | Original record |
|---|---|
| Fresh $384^2$ field trajectory | [Execution receipt](../../demos/resistive_mhd_island_coalescence/continuation_record/experiments/exp_3cfeb359d713c480a5352496.json) |
| Rates, fits, uncertainty and coverage | [Completed exploratory analysis](../../demos/resistive_mhd_island_coalescence/continuation_record/experiments/exp_cff9836110ed71a44c1d6620/workspace/analysis.json) |
| Figure arrays and source hashes | [Plotting provenance](../../demos/resistive_mhd_island_coalescence/visual_data/provenance.json) |
| Report review outcome | [Preserved finalization record](../../demos/resistive_mhd_island_coalescence/continuation_record/finalization.json) |

The continuation retained the original question, GPT-6.1 Sol medium worker and
Sol high reviewer. The operator supplied no suggested scientific interpretation.
Its numerical cutoff preserved the final 7.5 minutes for reporting; subsequent
report-scheduling repairs are documented in the [demo audit](../research/demo-audit-20261008.md).

## The physical question

The bounded model is two-dimensional, compressible, single-fluid resistive MHD
with uniform resistivity. The root claim proposes a pre-plasmoid branch

$$
R\propto S_\eta^p,\qquad -0.60\leq p\leq-0.40,
\qquad S_\eta=1/\eta\in[250,4000],
$$

that persists under spatial refinement. Here $S_\eta$ is the normalized
inverse-resistivity control used by this setup, not a dimensional Lundquist
number. The rate diagnostic, flux window, sheet resolution and branch eligibility
must be established before interpreting a fit. This single-fluid model does not
resolve electron-scale kinetic reconnection.

## The classic campaign remains available

![Four FLASH states showing current density and magnetic-field contours during island coalescence](../../demos/resistive_mhd_island_coalescence/figures/island_coalescence_evolution.png)

*Preserved commissioning run: 2D FLASH 4.8, 128 × 128 cells, four MPI ranks,
uniform resistivity. These are actual computed fields. The commissioning run
establishes a working instrument; it is not evidence for a scaling law.*


The [original demo](https://github.com/tomzhu0225/simjecture/tree/main/demos/resistive_mhd_island_coalescence)
retains the guided input, plotting code, field and profile figures, a real GUI
capture and the six-hour campaign's audit extract. No original figure or record
has been replaced by the refreshed documentation.

That campaign recorded the root as falsified and left its repair open. The later
audit identified an important interpretation error: the root's reported 95%
interval, $[-0.423266,-0.389641]$, overlaps the proposed exponent band. An upper
edge above $-0.40$ does not, by itself, reject the whole band. The repair also
missed its specified refinement case and failed final analysis-lineage checks.
Read the original record together with its appended correction.

This is a useful example of why a convincing field plot, a regression and a
recorded verdict need to be assessed separately. The historical audit extract
is not a portable, completed scientific evidence package.

## The fresh one-hour minimal run

**The refreshed study ended unresolved at its one-hour cutoff. It did not
establish a new reconnection-rate scaling.** It used the same original physical
hypothesis and FLASH executable, with GPT-6 Luna at medium effort as worker and
GPT-6.1 Sol at high effort in the separate review context.

![Fresh FLASH commissioning fields and current density from the one-hour minimal study](../_static/demos/island-minimal-field.png)

*Fresh $256^2$ commissioning trajectory at $t=0.6503$, rendered by the agent from
its recorded fields. The picture is exploratory; it is not accepted evidence for
the scaling hypothesis. Its title retains the original path-error diagnostic;
see the post-run correction below. The earlier field figures above remain unchanged.*

The reviewer requested three rounds of methods revisions before approving a
production method. It identified gauge-sensitive topology/flux diagnostics,
incomplete-measurement handling, uncertainty propagation and the rule for
comparing refinement results. The worker preserved those decisions and revised
its sources; approval of a method did not establish the physical claim.

Production approval arrived 46 minutes into the 60-minute budget, leaving about
14 minutes for final evidence collection and review. The classic campaign had
six hours and a different model/backend; these records do not isolate a workflow
or model advantage under matched conditions.

| Part of the record | Observed outcome |
|---|---|
| Recorded executions | 25 succeeded, 5 failed, 1 was cancelled; these include analysis and qualification jobs as well as simulations |
| Fresh complete evidence trajectories | $S_\eta=250$ at $96^2$ and $120^2$; $S_\eta=1000$ at $128^2$ and $160^2$ |
| Diagnostic eligibility | The four complete cases failed the declared flux-potential path-consistency screen |
| Low-resistivity endpoint | $S_\eta=4000$, $256^2$: cancelled after partial evolution; it had not reached the full measurement window |
| Scaling and refinement verdict | No eligible fresh scaling dataset; no scientific claim accepted |

The larger $S_\eta=1000$, $256^2$ pilot passed the local diagnostic screen, but it
was commissioning/exploration. It could not be relabelled as fresh claim evidence.
The incomplete $S_\eta=4000$ trajectory was censored, not treated as a physical
counterexample. Much of the budget went into diagnostic development and review;
the final record does not distinguish the exponent band with qualified data.

The campaign's ineligibility decisions are preserved, but a subsequent operator
check identified a defect in the diagnostic itself, described below. The rejected
cases should not be interpreted as evidence that FLASH failed to resolve the field.

### Post-run correction: a half-cell error in the diagnostic

**The agent's two-path check mixed a cell-centre gauge with an integration starting
at the lower cell boundary.** Its vertical path included an extra half-cell
contribution. The horizontal path used the first cell-centre row, so the two
paths did not represent the same coordinates. The worker's qualification fixture
and independent methods review missed the error.

The reviewer had identified earlier gauge and path-alignment defects and
requested corrections, including a fixture with nonzero $B_x$. The final repair
still contained the half-cell mistake, and its fixture accepted discrepancies
below 0.15 rather than establishing agreement with the exact potential. The
review caught useful problems but did not verify that this repair was correct.

A separate post-run calculation applied consistent quadrature to the *same*
retained fields. It compares the average potential on the two central cell-centre
rows along both paths; it is not an exact continuum evaluation at $y=0$.

| Case | Original maximum discrepancy | Consistent-coordinate discrepancy |
|---|---:|---:|
| $S_\eta=250$, $96^2$ | 0.248636 | $1.98\times10^{-7}$ |
| $S_\eta=250$, $120^2$ | 0.217575 | $1.37\times10^{-7}$ |
| $S_\eta=1000$, $128^2$ | 0.202556 | $1.86\times10^{-7}$ |
| $S_\eta=1000$, $160^2$ | 0.177381 | $1.50\times10^{-7}$ |

![The original diagnostic rejects four cases, while a coordinate-consistent calculation on the same fields gives discrepancies near 1e-7](../_static/demos/island-coordinate-correction.png)

An independent analytic field, $A_z=x(y^2+0.005)$, exposes the same problem:
the original formula reports a discrepancy of about 1.04 on a $96^2$ grid,
while the corrected paths match the exact row-average potential to roundoff.
The regression tests include unequal cell spacings and a shifted coordinate origin.

This correction explains the false path-screen rejections. It does **not** supply
the missing resistivity coverage, certify the remaining diagnostics, or create an
accepted scaling claim. The original sources, receipts, methods decisions and
report remain unchanged. The new check is explicitly operator-authored, after
termination; it is not attributed to the autonomous worker.

Run the analytic check without a solver, raw FLASH files or a model call:

```bash
uv run python demos/resistive_mhd_island_coalescence/postrun_coordinate_check.py
```

The [check report and source](https://github.com/tomzhu0225/simjecture/tree/main/demos/resistive_mhd_island_coalescence)
retain archive hashes and the five-case numerical comparison, including the
commissioning pilot. Rechecking those raw fields requires the original local
archives via `--study PATH`; the compact Git extract does not include them.
This is a concrete contribution opportunity: validated coordinate-aware diagnostics
can prevent an agent and its reviewer from repeatedly reasoning over a flawed test.

### Inspect the audit

The [minimal-run extract](https://github.com/tomzhu0225/simjecture/tree/main/demos/resistive_mhd_island_coalescence/minimal_record)
contains all execution receipts, methods decisions, director records, retained
source and compact outputs. It preserves the original worker report without
rewriting its conclusion. Bulk FLASH histories and native provider sessions are
omitted, with declared-file hashes recorded; this is a compact audit rather than
a complete numerical replay package.

```bash
uv run python demos/resistive_mhd_island_coalescence/verify_minimal_record.py
```

This checks retained-file integrity and recorded dispositions, without FLASH or
a model call. It does not independently reanalyse the omitted HDF5 histories.
The completed [Kepler investigation](kepler-energy.md) provides a smaller record
with full retained arrays and a no-key numerical reproduction path.

The exact source commit was `09ddd7a51387124b5e2ed38d254f76b601f9aa11`, a development
checkout based on 0.6.0 with the ancestor-review scheduling fix. The manifest fixes
that identity independently of future releases. Reported native counters totalled
57,726,924 input tokens, including 56,304,384 cached tokens, and 240,213 output
tokens. Ten turns have incomplete usage reporting; these counters are not an
invoice. A separate CUDA compilation overlapped part of the run, so its wall time
is not a controlled comparison with another model or campaign.

## A second one-hour run with Sol as worker

An operator-requested follow-up used **GPT-6.1 Sol at medium effort as worker**,
with Sol at high effort in the separate review context. The hypothesis, original
instructions, requirements, commissioning files and FLASH runtime identity were
unchanged. The post-run coordinate correction was not supplied to this worker.
The research service and supervisor matched the Luna run; a separate web
run-discovery fix was applied during monitoring.

This run reached a much broader numerical dataset, but also ended at the cutoff
**without an accepted scientific verdict**:

| Work | Recorded result |
|---|---|
| Baseline scan | Five completed $256^2$ evidence trajectories at $S_\eta=250,500,1000,2000,4000$ |
| Refinement | Completed $384^2$ runs at 250 and 1000; preserved 4000 output contains the full measurement window despite a later timeout |
| Recovery | Independent methods review approved hash-bound postprocessing of the timed-out evidence run; the timeout receipt remains unchanged |
| Recorded executions | 18 succeeded, 5 failed, 1 cancelled, including qualification and analysis jobs |
| Final analysis | Four baseline cases and three matched refinement cases passed its implemented eligibility screens; the 500 case failed the cadence-decimated window check |
| Scientific review | No claim review was recorded before the wall cutoff |

The final processing reports a four-case baseline exponent of approximately
$-0.4111$ and a three-case refined exponent of $-0.4126$. Their residual-based
95% intervals overlap the proposed exponent band. A separate joint power-law
feasibility calculation flags curvature under the agent's empirical error boxes;
that is an unreviewed result, not an accepted physical falsification.

The workflow still lost time at the analysis boundary. Campaign plotting tried
to import Matplotlib inside the FLASH runtime, where it was unavailable. The
worker replaced that rendering with SVG, but the changed source/binding and
final exploratory analysis were not approved for decisive processing before
termination. Its report also contains stale intermediate statuses; the receipts
and final host disposition are authoritative.

The [212-file compact audit](https://github.com/tomzhu0225/simjecture/tree/main/demos/resistive_mhd_island_coalescence/sol_medium_record)
preserves the original sources, outputs, figures and reviews. It includes the
successful diagnostic recovery as exploration, without promoting it to a new
evidence receipt. Bulk fields and native provider streams are omitted.

```bash
uv run python scripts/verify_research_audit.py \
  demos/resistive_mhd_island_coalescence/sol_medium_record
```

Reported native counters totalled 8,903,040 input tokens, including 8,186,624 cached
tokens, and 63,788 output tokens; four turns have incomplete usage reporting.
Compared with the Luna record, this run produced more simulation coverage and
used fewer reported tokens. Both remain unresolved. The runs shared this machine
with different concurrent work and each model was sampled once, so this is an
observed case comparison rather than a controlled model ranking.

## Reproduce the instrument or contribute a stronger test

The original demo provides the exact commissioning command and plotting script.
FLASH source and binaries are supplied by the operator under their upstream
license; they are not distributed with this repository. A fresh study must
commission the executable through its actual experiment launcher and retain
its own inputs, diagnostics and evidence.

To start a separate minimal-mode study from a source checkout, point
`--capabilities` to the directory containing your qualified island-coalescence
capability. Select your worker and reviewer models; the recorded one-hour run
used the routes shown here:

```bash
uv run simjecture study \
  --campaign artifacts/my-island-minimal \
  --hypothesis-file demos/resistive_mhd_island_coalescence/hypothesis.txt \
  --instructions-file demos/resistive_mhd_island_coalescence/minimal_instructions.txt \
  --requirements-file demos/resistive_mhd_island_coalescence/minimal_requirements.json \
  --guided-commission demos/resistive_mhd_island_coalescence/guided_commission.json \
  --capabilities /path/to/qualified/capabilities \
  --backend codex --model gpt-6-luna --reasoning-effort medium \
  --judge-model gpt-6.1-sol --judge-reasoning-effort high \
  --mode minimal --completion-policy repair --wall-seconds 3600 --director
```

A new campaign consumes model usage and produces new evidence; its transcript
and outcome need not match the recorded study. Its budget must include diagnostic
qualification, numerical controls and review, as well as solver execution.

Useful extensions include a justified rate diagnostic, spatial/time convergence,
branch qualification and a clearer test of the proposed scaling interval.
Start with [guided commissioning](../how-to/guided-commissioning.md) and
[the evidence rules](../concepts/evidence-and-claims.md).
