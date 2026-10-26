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
