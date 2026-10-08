# Demonstrations

Start with the [current minimal-workflow orbital investigation](../docs/demos/kepler-energy.md).
The Gray–Scott, GEM and role-validation campaigns below are preserved historical
records with their original workflow, artifacts and interpretations.

Release demonstrations are recorded scientific runs, not hand-written examples
that merely exercise an API. Portable recorded runs include the exact natural-
language input, durable claim ledger, transcript, final report, generated
programs, numerical outputs, provenance, and figures made from those outputs.
Operator-dependent demos state clearly which inputs are local and which claims
remain unresolved.

## Recorded autonomous runs

- [`gray_scott_counterexample/`](gray_scott_counterexample/) is the primary
  domain-neutral version 0.1 demo. From one natural-language hypothesis and no
  campaign instruction, the agent authored a reaction-diffusion solver and
  found a finite-domain counterexample in 23.8 minutes.
- [`collisionless_gem_reconnection/`](collisionless_gem_reconnection/) is the
  primary kinetic plasma demo. From a validated non-evidentiary GEM starting instrument,
  the agent designed and executed a held-out 12-run CUDA ensemble, falsified its
  operational child under a frozen rule, and correctly left the population root
  open.
- [`resistive_mhd_island_coalescence/`](resistive_mhd_island_coalescence/) is the
  fluid-plasma MHD demo. It bundles an operator-validated, non-evidentiary
  FLASH anchor and an audit extract from a six-hour autonomous campaign. The
  historical ledger recorded a root falsification ($p \approx -0.406$), but its
  reported interval overlaps the allowed band and does not by itself establish
  that conclusion. The repair branch remains open because the final analyzer
  lineage was not closure-eligible. See the demo's current interpretation notice.
