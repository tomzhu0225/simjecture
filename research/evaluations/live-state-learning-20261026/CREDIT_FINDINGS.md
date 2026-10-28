# Credit assignment before further updates

The nine commissioning decisions occurred 20.21–70.48 seconds after episode start.
At every corresponding elapsed time, each arm had already made exactly one native
start. Both final reports passed verification, with zero required-feedback misses
or duplicate dispatches.

Removing each arm's native-start and wall-time costs incurred before that same
elapsed time leaves the sampled-minus-wait return difference unchanged at
+0.12146138 for all nine decisions, to floating-point precision. The extra four
native starts and longer wall time in the control happened after the observations.
Reward-to-go therefore does not remove the observed noisy credit in this pair.
This does not refute its general value; it identifies where this example's
variation occurred. Nine polls still represent one sampled episode.

A separate descriptive temperature calculation conditions the stored route
probabilities on the absence of any visible question, without new inference.
Mean valid expert-proposal probabilities are 49.51%, 47.31%, 47.05%, 47.64% and
49.57% at temperatures 0.5, 1, 1.5, 2 and 3. Lowering temperature alone does not
solve the healthy-state proposal problem in these observations. These are
proposal probabilities from one episode, not measured false-dispatch rates.

The [arithmetic record](credit-audit.json) preserves the nine contrasts and
pre-decision counts. This audit creates neither training samples nor projected
scientific outcomes. The next step is the [frozen live-observation label audit](PROTOCOL.md),
followed by repeated real workflows and fresh validation. The previously
proposed reward-to-go change is not being presented as a demonstrated remedy.


## Return tradeoff in the completed C12/C13 commission

The [six-episode commission](sampling-commission-c13-completed.json) gives mean
utility 0.85960 for sampled SFT and 0.88462 for waiting under the unchanged
registered reward. The sampled arm is 10.69 seconds faster on average but uses
four more native starts in total. All six quality terms are one and feedback/
duplicate terms are zero, so the negative utility difference is entirely the
declared execution-cost tradeoff.

The coefficient 0.02 per native start and time cost 0.1 per 650 seconds imply
that one additional start requires 130 seconds saved to break even when all
other terms match. Two extra roles therefore require 260 seconds saved. This is
an explicit preference encoded by a research proxy, not a measured monetary
exchange rate or evidence that the model is intrinsically worse. Preserve it for
this cohort. Future reward experiments should declare their success/cost tradeoff
prospectively and report verified quality, wall time and native usage separately,
rather than changing coefficients after outcomes merely to obtain a positive score.

In the healthy episode the positive sampled-minus-wait return difference is
0.00245 despite neither arm dispatching automatic attention. That return would
also credit eight rejected/pending wake proposals under an episodic estimator.
This is another small-sample variance example; it does not make the likelihood-
ratio estimator mathematically invalid. It reinforces the need for repeated
controls and honest episode-level sample counts before optimizer updates.
