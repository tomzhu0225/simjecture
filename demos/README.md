# Recorded investigations and reference cases

Read the [illustrated documentation gallery](../docs/demos/index.md) for the
question, numerical results and review decisions behind each example. Exact
software/model identities belong to the individual records; a new package release
does not turn an older campaign into a new run.

## Autonomous minimal-workflow studies

| Study | What you can inspect |
|---|---|
| [Kepler orbital accuracy](kepler_energy/) | Completed counterexample-and-repair loop: original code/arrays, fresh validation and accepted reviews; no-key verification and numerical reproduction |
| [FLASH island coalescence](resistive_mhd_island_coalescence/) | Fresh v0.7.0 minimal study with an independently accepted counterexample to the proposed reconnection-rate slope band, plus preserved earlier minimal audits and the coordinate-diagnostic check |
| [FLASH → WarpX kinetic patch](flash_warpx_kinetic_patch/) | Fresh v0.7.0 minimal study linking a FLASH current sheet to local kinetic pressure measurements with accepted claim/report reviews, plus preserved earlier minimal audits |

A recorded execution is different from an accepted scientific conclusion. Each
example states what is retained, what is omitted, and which claims remain open.
Verification of an extract does not substitute for rerunning its simulations or
independent scientific review.

## Capability and toolchain reference cases

| Case | What you can inspect |
|---|---|
| [Qin-1 hardware-to-plasma](qin1_multiphysics/) | Operator-assisted local toolchain study spanning CAD, meshing, EM/circuits, native 3D plasma and visualization, with retained sensitivity checks and execution limits |
| [Quantum ESPRESSO Si reference](qe_dft_reference/) | Material-specific diamond-Si DFT protocol (`vc-relax`, SCF, bands, DOS and `projwfc.x`), Bubblewrap launcher inputs, and completion-bound reassessment |
| [Quantum ESPRESSO bcc Fe reference](qe_fe_reference/) | Collinear spin-polarized bcc-Fe protocol and reassessment record demonstrating how non-converged structural optimization (`exit_status=3`) is rejected |

Earlier classic (`v0.1`–`v0.6.2` `mvp`/DSH) demo directories have been retired from
`main` and remain preserved in the [`v0.6.2` release tag](https://github.com/tomzhu0225/simjecture/tree/v0.6.2/demos).

To contribute a study, retain the operator input, sources, commands, relevant
outputs and review decisions. Distinguish human framing and commissioning from
autonomous scientific work and later corrections. See
[the contribution guide](../CONTRIBUTING.md) and
[documentation development](../docs/development/documentation.md).
