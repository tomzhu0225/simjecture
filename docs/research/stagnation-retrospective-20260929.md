# Aluminium Z-pinch campaign retrospective

Follow-up: the [detailed audit](stagnation-deep-audit-20260929.md) supersedes this
report's tentative causal attributions. In particular, the instrument prefixes
mean FLASH **or** WarpX in the actual code; reviewers incorrectly demanded both.
The failed 3D submission omitted its capability, and later analysis exposed further
agent-written time-grid and dimensional errors. The detailed audit also quantifies
worker restarts and identifies evidence being evicted from review packets.

Evidence cutoff: 29 September 2026, approximately 18:50 China time. This is a
retrospective snapshot, not a final campaign verdict. The continuation recovered
after the operator replenished the provider balance and remains active until its
original 19:40:51 deadline. This audit did not stop, extend, or steer it.

## What we achieved

We commissioned FLASH radiation-MHD calculations, ran an autonomous investigation,
and continued it with human scientific steering. We obtained reproducible numerical
examples where integrated escaping radiation exceeds the peak instantaneous inward
kinetic-energy reservoir. We did **not** establish a validated explanation of the
experimental Z-pinch energy excess, isolate a unique mechanism, or complete a
qualified non-axisymmetric study.

The relevant comparison is an integral over time divided by a peak reservoir, not
two interchangeable energy budgets. Initially stored magnetic energy and continued
electromagnetic input make an excess physically possible. Demonstrating their
quantitative contribution requires consistent control volumes and a closed budget.

### Sequence and scope

1. Guided commissioning included both RZ and Cartesian 3D FLASH runs. A 64×64×32
   Cartesian case reached about 20 ns in 1,749 seconds. Its roughly 1.86% mass
   change and other qualification limitations prevent treating it as validated
   mechanism evidence. “No 3D was ever run” would be incorrect.
2. The first autonomous campaign ran about 9 h 50 min and stopped on a review
   protocol failure. Its saved status report lists 25 successful experiment jobs,
   33 matrix cases plus an anchor reproduction, all research cases RZ. A successful
   job is not necessarily a scientifically admissible inner solver case.
3. The continuation began at 09:40:51 on September 29 with a 10-hour deadline,
   minimal mode, the builtin DeepSeek backend, and cooperative PRoot isolation.
   At this snapshot it has 20 recorded jobs: 16 succeeded and four failed. These
   include probes and reductions; they are not 16 independent simulations.
4. Human steering requested a specific geometry × late-drive comparison, corrected
   accounting, and a limited 3D check. A later clarification explicitly preserved
   broadband radiation as a legitimate observable.

The project has therefore already used nearly 19 hours of autonomous campaign
elapsed time, plus commissioning and human work. The current continuation alone
has not yet reached its 10-hour deadline.

## Scientific findings

The completed prospective comparison uses FLASH, aluminium plasma, RZ 128×16,
and a 0–20 ns observation interval. The original trailing annulus is at 2.5 mm;
the shifted annulus is at 3.0 mm. The held-current cases follow the original drive
through 6 ns and then hold 0.62 MA. Holding current does not turn off power.

| Case | Geometry and late drive | Escaping broadband energy | Peak inward kinetic energy | Ratio |
|---|---|---:|---:|---:|
| A | Original, rising | 482.72 J | 317.35 J | 1.521 |
| B | Original, held | 480.48 J | 317.35 J | 1.514 |
| C | Shifted, rising | 515.02 J | 343.22 J | 1.501 |
| D | Shifted, held | 510.38 J | 343.21 J | 1.487 |

Holding the late current reduces broadband output by 0.47% at the original radius
and 0.90% at the shifted radius. Moving the annulus increases output by 6.69% with
the rising drive and 6.22% with the held drive. Peak inward kinetic energy also
increases about 8.15%, so the radiation/kinetic ratio slightly decreases. Initial
magnetic energy is matched; initial thermal and kinetic energies differ slightly.
This is a useful geometry control, not an exclusive knockout of current transfer.

These observations support weak sensitivity to this particular late-drive change
over this time interval. They do not establish independence from electrical input,
prove that initial magnetic energy alone supplies the radiation, or identify a
universal explanation. Radiation is still present at the endpoint; 20 ns is a
declared observation window, not a demonstrated completed pulse.

The first campaign's saved report also records a baseline ratio around 2.53 at
40 ns and a no-trailing-annulus ratio around 1.20 at 20 ns. These remain unaccepted
model results. The latter is especially relevant: excess radiation alone cannot
uniquely diagnose the proposed trailing-plasma mechanism. The 40 ns case also
shows why the integration interval must accompany every headline ratio.

### Why the explanation remains incomplete

- The corrected reduction removes stored-radiation double counting, labels
  measurement radii, and includes pressure in the material-energy flux.
- Baseline electromagnetic closure is about 0.49% at an internal surface, but
  about 13.1% at the near-outer surface. Good internal closure cannot certify
  whole-domain escaping radiation. The outer reconstruction still needs work.
- Reconstructed boundary current relative to the supplied circuit current drifts
  from about 0.97 to 0.50. This is not established physical current loss, and the
  time dependence argues against merely applying a constant factor-of-two fix.
- The recorded longer 3D continuation attempt failed before FLASH launched:
  its input generator could not access the source/template path. A scratch pilot
  reached only about 1.1 ns on 24×24×8 cells and returned an invalid current
  diagnostic. Neither constitutes the required non-axisymmetric evidence.
- Some time-window metadata in earlier reductions mix seconds and nanoseconds.
  Correcting a displayed reference time does not automatically repair previously
  integrated dependent windows. Those products need dependency-aware reanalysis.

Our interpretation also needed correction. A ratio below one above an arbitrary
1 keV cutoff or inside 8–14 ns does not invalidate broadband excess. Experimental
comparison must specify material, spectral response, time window, and denominator.
The operator's challenge improved this framing; the video should retain it.

## Cost and orchestration audit

| Scope | Recorded input tokens | Recorded output tokens |
|---|---:|---:|
| First autonomous campaign | 126,362,191 | 5,472,739 |
| Continuation snapshot | 154,203,757 | 3,373,213 |
| Combined | 280,565,948 | 8,845,952 |

These are cumulative provider usage counters, including repeated context, not
unique text or audited charges. The continuation records 115 incomplete-usage
turns; totals should not be presented as a complete invoice. The operator reports
spending RMB 100 and replenishing another RMB 100; attribution to individual phases
requires the provider billing export. Replenishment is not additional expenditure.

Of continuation input tokens, 153,725,654 came from the main worker, 408,594 from
oversight, and 69,509 from journal summaries. Thus about 99.7% of recorded input
is worker traffic. Reducing reviewer frequency alone will not solve this cost.
We need per-request context and cache accounting before attributing all worker
traffic specifically to rereading, tool output size, or inefficient reasoning.

The continuation accumulated 117 reconnect attempts and 6,782 seconds (1 h 53 min)
of backoff waits. It also records about 636 seconds of failed provider turns;
these are separate counters, not a fully reconciled exclusive time breakdown.
There were 14 worker-turn timeouts. The event log has 131 judge starts but only
21 completed oversight events at the snapshot: attempts are not completed reviews.

The quota failure is now directly confirmed: provider records contain HTTP 402
`Insufficient Balance`. The local classifier recognizes some quota phrases but
does not match this phrase/402, and reads `error` or `message` while these error
events carry the text in `result`. This provides a concrete likely failure path;
replay the actual sanitized event against the deployed revision before fixing it.
After replenishment, the worker resumed. Retry persistence worked, but diagnosis
and user communication failed.

## Improvements, in priority order

These are proposed repairs, not implemented changes from this retrospective.

| Priority | Change | Acceptance evidence |
|---|---|---|
| P0 | Normalize provider error envelopes, including result/error/message, and classify insufficient balance separately from transport loss. | Sanitized real 402 replay enters an actionable credit-blocked state; transient disconnect still retries; replenishment can resume without losing work. |
| P0 | Show active research time, outage time, deadline, token totals, missing usage, and configurable monetary/token limits in CLI and GUI. | A synthetic outage produces matching clocks in both interfaces; spending limit pauses safely; no automatic deadline extension. |
| P0 | Preflight every solver capability in the exact registered experiment sandbox. Bind runtime, read-only source, input templates, EOS, and analysis dependencies together. | The exact 3D generator and short solver case succeed through the same launcher used by research; a missing mount is reported before a production submission. |
| P0 | Add tested scientific reduction contracts: units, stored-energy membership, surface identity, enthalpy flux, and window dependencies. | Manufactured/unit fixtures catch radiation double counting, seconds/ns mixing, wrong surface selection, and stale dependent integrals. |
| P1 | Give workers compact evidence indexes and incremental context, with explicit access to full artifacts. Track per-request input, cached input, tool-output volume, and repeated reads. | Paired runs preserve evidence quality while lowering tokens per completed decision; no claim that compaction helps until measured. |
| P1 | Make review packets reference current artifact hashes and expose scoped artifact retrieval. Invalidate review findings when their underlying reduction changes. | A corrected reduction is actually inspected; a still-failing outer budget remains rejected; stale summaries do not trigger unnecessary reruns. |
| P1 | Track progress by new evidence, repaired blockers, and resolved scientific decisions, rather than activity alone. | Repeated intentions/polls trigger a concrete blocker report, without banning legitimate debugging or imposing a rigid experiment sequence. |
| P1 | Keep optional solver availability separate from scientifically necessary requirements. | Missing WarpX does not repeatedly block a FLASH-sufficient claim; changing a genuinely required method remains explicit and auditable. |
| P1 | Make the GUI show the current hypothesis, comparison, evidence status, reviewer blocker, and delivered human steering. | An observer can distinguish solver running, agent analyzing, provider blocked, and claim awaiting review without reading raw logs. |
| P2 | Export a reproducible campaign bundle: initial conditions, binaries/source hashes, analysis version, receipts, plots, interventions, and billing caveats. | A separate process regenerates headline tables from the bundle and detects stale figures. |

Minimal mode should retain scientific freedom. These repairs strengthen execution,
measurement, and visibility rather than prescribe the agent's reasoning structure.
This attempt does not isolate a model effect: there is no matched alternate-model
run under identical code, budget, inputs, and steering. It cannot establish that
DeepSeek, minimal mode, or autonomous research in general is intrinsically poor.

## Next scientific campaign

First repair and verify the drive/current mapping and a consistently bounded energy
budget. Then repeat A and B through that verified path before interpreting their
small difference. Use tracer-resolved trailing material and current diagnostics if
the objective is to isolate trailing-plasma work, not merely vary its radius.

Only then qualify the existing 3D capability, with sufficient annulus resolution,
mass/floor diagnostics, and an affordable complete observation interval. Compare
RZ and 3D with matched physical initial conditions. Add non-axisymmetric perturbations
with a declared question and resolution check. More dimensions alone do not fix an
incorrect drive or incomplete budget.

Before spending another long allocation, declare the quantitative discriminator:
which measured mechanism contribution or timing change would support the proposed
explanation, and which result would contradict it. A useful bounded null result
is acceptable; a large radiation/kinetic ratio alone is insufficient.

## Evidence locations

- Local snapshot: `artifacts/stagnation-retrospective-20260929/evidence.json`.
- Parent status and commissioning: `research/proposals/zpinch-stagnation-energy-2026-09-26/STATUS-20260929.md`, `RESULTS.md`, and `COMMISSIONING.md`.
- Continuation corrected reduction: experiment `exp_f0af587862a0405b50383a92`.
- Four-case experiments: `exp_ef6aed863e99426b7805f946`, `exp_57d2389a79136a7e04986e6c`, `exp_5308e2c5a75bdab7b1e8770b`, `exp_e495642f37c800bd88deca25`.
- Failed recorded 3D submission: `exp_56a0a756302bafe238ab5c1f`.
- Human steering records: `artifacts/research-steering-20260929/`.

No credentials belong in the report, figures, video, or exported evidence bundle.
