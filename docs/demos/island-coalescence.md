# Reconnection-rate scaling with FLASH

**A fresh Simjecture 0.7.0 investigation falsified the proposed slope band
−0.55 ≤ p ≤ −0.45.** The independent reviewer accepted the counterexample from
fresh production trajectories. The explanatory repair remained unvalidated.

![Fresh FLASH density and magnetic geometry, current-sheet evolution, and the measured scaling with the original minus-one-half reference](../_static/demos/fresh-v070-island-fields.png)

The upper rows show density with magnetic streamlines and out-of-plane current
from three saved states of the fresh production trajectory. The lower panel
compares exploratory rates with the qualified production contrast. The dashed
orange curve is the original $p=-1/2$ reference, normalized to the lowest-$S_\eta$
exploratory rate; it is not fitted to the production results.
[Download figure PDF](../_static/demos/fresh-v070-island-fields.pdf).

## The question and the counterexample

The operator supplied a commissioned FLASH resistive-MHD island-coalescence
application and the bounded hypothesis. The worker fixed the flux-window rate
measurement, admissibility checks and numerical uncertainty rule, then examined
how reconnection changes with the inverse-resistivity control $S_\eta=1/\eta$.

The decisive contrast uses $S_\eta=1000$ and $2000$:

| Quantity | Fresh reviewed result |
|---|---:|
| Rate at $S_\eta=1000$ | 0.0496886 |
| Rate at $S_\eta=2000$ | 0.0382421 |
| Effective log-slope | −0.3778 |
| Numerical sensitivity interval | [−0.4314, −0.3247] |
| Conjectured band | [−0.55, −0.45] |

The entire numerical interval lies above −0.45. This rejects the stated band,
not merely an exact −1/2 exponent. The interval propagates measured numerical
sensitivities; it is not a statistical confidence interval.

A current sheet only a few cells wide made a stable integrated rate insufficient.
Independent methods review required matched-flux profile checks and a magnetic-null
inventory as well as spatial, timestep, cadence and flux-reconstruction controls.
When the $256^2\to384^2$ rate shift grew, the worker retained that failed check
and refined to $512^2$. Two fresh $384^2$ production trajectories followed methods
approval, with fine-grid uncertainty transported into the decisive comparison.

The run completed **17 MHD trajectories, six diagnostic analyses and three failed
trajectory receipts**. GPT-6.1 Sol at medium effort served as worker; the director
and independent reviewers used high effort in separate contexts. The operator
extended the allowance and restored recorded interruption time. The investigation
then closed with an accepted report. Root falsification is established; the
subsequent repair attempts did not pass their fresh validation, so no replacement
law is claimed.

## Inspect and reproduce

The [fresh compact audit](../../demos/resistive_mhd_island_coalescence/fresh_v070_record/manifest.json)
contains the original inputs, source snapshots, all 26 receipts, methods and claim
reviews, accepted report and omission ledger. The numerical runtime was
**0.7.0, commit `cfca558cb30868d7bc12af7a9b636303f7bc500b`**.

- [Original hypothesis](../../demos/resistive_mhd_island_coalescence/fresh_v070_record/operator_input/hypothesis.txt)
- [Independent root review](../../demos/resistive_mhd_island_coalescence/fresh_v070_record/reviews/review_d8ed7a3364483fc612a029c3.json)
- {download}`Scientific report <../../demos/resistive_mhd_island_coalescence/fresh_v070_record/research/RESULTS.md>`
- [Recorded closeout](../../demos/resistive_mhd_island_coalescence/fresh_v070_record/campaign_closeout.json)
- [Figure provenance](../../demos/resistive_mhd_island_coalescence/fresh_v070_visual_data/island_study_provenance.json)

From the repository root:

```bash
uv run python scripts/verify_research_audit.py demos/resistive_mhd_island_coalescence/fresh_v070_record
uv run --extra flash-demo python scripts/render_fresh_plasma_examples.py
```

These commands check retained bytes and redraw figures without simulations or
model calls. Bulk FLASH states are explicitly omitted from the public audit;
complete native-data replay requires the original artifacts. A fresh investigation
requires an operator-supplied, qualified FLASH executable and a configured agent
backend. The retained commissioning inputs are starting material, not evidence
for a new run.

The [earlier investigations and coordinate-diagnostic audit](island-coalescence-historical.md)
remain available with their original findings and figures. Their wider slope
band and unresolved outcomes belong to those historical studies.
