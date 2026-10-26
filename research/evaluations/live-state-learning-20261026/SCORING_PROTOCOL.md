# Frozen checkpoint scoring on live observations

Score the same 24 observations frozen in the native label audit with all four
previously evaluated checkpoints: base, SFT step 512, the eight-update continued
SFT control and the eight-update measured-return RL pilot. This is development
analysis of saved real observations, not a new workflow-effectiveness test. It
creates no optimizer updates, new model weights or intervention outcomes.

The base is `internlm/Intern-Decision-4B` revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`. Adapter weight SHA-256 values are:

- SFT512: `922bfef8e221f5df39ec3a3740d3e9e97fbcd2358c34679f774a0085227ae780`.
- Continued SFT: `76bf1bdf4c6d6a261211057d3cab4c8609131788827569f9c33f802d3491dab5`.
- RL: `dac85c84f7dc7416baed29c04beaad8482df5998a0be90d827e22e713754f0be`.

Use the verified single-pass masked-field compiler and FLA prefill runtime,
temperature 1 and an 8,192-token full-input limit. Preserve raw probabilities,
prompt hashes, actual token counts, model identities and scoring time for every
assigned model/observation pair. Record an over-budget input or failed inference
explicitly; do not silently omit it. All four policies use one resident base on
the same remote A100. Restore saved adapter probes before scoring, with maximum
absolute probability discrepancy at most `1e-4` after any needed temperature
conversion. Stop on failed qualification.

Keep original independent greedy decisions and the optional constrained decoder
separate during later analysis. Native reference judgments are incomplete at
registration; do not represent provisional agreement as audited accuracy or
change the selected observations/models based on these scores. The eventual
two-reviewer labels remain judgments, not measured intervention value.

The coordinator preserves rows, model manifests, qualification probes, runner
and source hashes before execution. No weights or model inference are placed on
the local host. Use a fresh, owned A100 allocation bounded to 20 minutes, the
remaining original 70-compute-unit ceiling, and credential expiry. No previous
lease or endpoint is reused. Preserve complete or partial outputs off-runtime
and release promptly. No physical simulations or native workflow actors are
required for this scoring phase.
