# Recorded investigations

Read the [illustrated documentation gallery](../docs/demos/index.md) for the
question, numerical results and review decisions behind each example. Exact
software/model identities belong to the individual records; a new package release
does not turn an older campaign into a new run.

## Current minimal workflow

| Study | What you can inspect |
|---|---|
| [Kepler orbital accuracy](kepler_energy/) | Completed counterexample-and-repair loop: original code/arrays, fresh validation and accepted reviews; no-key verification and numerical reproduction |
| [FLASH island coalescence](../docs/demos/island-coalescence.md) | A separate one-hour minimal run ended unresolved; its audit and a tested post-run coordinate correction are preserved alongside the classic record |
| [FLASH → WarpX kinetic patch](flash_warpx_kinetic_patch/) | Tested transfer helpers and CPU/CUDA commissioning; the two-hour autonomous investigation is running, with no scientific result claimed yet |

A recorded execution is different from an accepted scientific conclusion. Each
example states what is retained, what is omitted, and which claims remain open.
Verification of an extract does not substitute for rerunning its simulations or
independent scientific review.

## Historical records

- [Gray–Scott counterexample](gray_scott_counterexample/): the version 0.1 classic
  campaign authored a reaction–diffusion solver and found a bounded-domain
  counterexample in 23.8 minutes. Its original contract and limitations remain
  with the record.
- [Collisionless GEM reconnection](collisionless_gem_reconnection/): a guided
  classic campaign executed a twelve-run CUDA ensemble. Its finite operational
  child was falsified under the recorded rule; the population root remained open.
- [Resistive-MHD island coalescence](resistive_mhd_island_coalescence/): original
  FLASH commissioning figures and six-hour campaign audit. The historical root
  interval overlaps the proposed exponent band; read the appended interpretation
  correction. The repair remained open because its final analysis lineage was
  ineligible.
- [Agent-role validation](agent_roles_validation/): preserved role coordination
  and review records from the earlier workflow.

To contribute a study, retain the operator input, sources, commands, relevant
outputs and review decisions. Distinguish human framing and commissioning from
autonomous scientific work and later corrections. See
[the contribution guide](../CONTRIBUTING.md) and
[documentation development](../docs/development/documentation.md).
