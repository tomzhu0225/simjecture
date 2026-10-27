# Recorded investigations

These examples let you inspect the research process: the operator's question,
what the agent chose to run, the resulting data and the review decisions.
A preserved study can be read without an API key. Fresh agent runs need a
configured backend; numerical reproduction and record verification are separate
operations.

## Plasma research

Start with the pictures: these plasma walkthroughs include actual field maps,
evidence maps, short explanations of each measurement and downloadable figures.
Their linked receipts distinguish completed work from outstanding tests.

![Fresh FLASH source, local kinetic fields and pressure controls](../_static/demos/fresh-v070-coupled-fields.png)

[**Magnetic-island coalescence with FLASH**](island-coalescence.md) presents a
fresh v0.7.0 investigation that independently falsifies a bounded reconnection-rate
scaling hypothesis. The explanatory repair remains unvalidated. Inspect the real
fields, failed controls, refinement decisions and accepted counterexample.

[**A FLASH current sheet followed with WarpX**](flash-warpx-patch.md) presents a
fresh v0.7.0 investigation with an independently supported local pressure prediction.
It links a new MHD source to two prospective kinetic particle realizations, with
numerical allowances and accepted claim/report reviews. Both examples retain the
older studies in separate historical walkthroughs and immutable audit records.

[**Qin-1: from hardware design to circuits, fields and 3D plasma**](qin1-hardware-plasma.md)
connects actual CAD changes, Gmsh, Elmer/RLC, native WarpX and PyVista. Explore the
interactive fields, the stronger cold-conductor design and the five failed
plasma flux-sensitivity checks. This operator-assisted host study demonstrates
the broader toolchain; it has no formal harness-adjudicated scientific verdict.

## A complete minimal-workflow example

[**Does energy conservation guarantee an accurate orbit?**](kepler-energy.md)
uses a fresh Kepler simulation study to exercise counterexample search and the
repair completion policy. Ordinary CPU Python is enough. It falsified the original claim and supported a four-case repair after fresh
validation. The record identifies human framing, agent work, independent reviews
and the observed outcome.

## Capability and toolchain reference cases

| Case | Scope and verification |
|---|---|
| [Qin-1 hardware-to-plasma](qin1-hardware-plasma.md) | Operator-assisted CAD → Gmsh → Elmer/RLC → 3D WarpX → PyVista study with retained sensitivity checks (`demos/qin1_multiphysics/`) |
| [Quantum ESPRESSO DFT references](../how-to/quantum-espresso.md) | Material-specific diamond-Si (`demos/qe_dft_reference/`) and magnetic bcc-Fe (`demos/qe_fe_reference/`) protocols, Bubblewrap execution receipts and completion-bound reassessment |

Earlier `v0.1`–`v0.6.2` classic-workflow demo directories have been retired from
the active tree and remain available in the
[`v0.6.2` release tag](https://github.com/tomzhu0225/simjecture/tree/v0.6.2/demos)
and [research archive](../archive/index.md).

## Research audits

Longer investigations also produce useful records when they leave a question open.
The [adaptive aluminium Z-pinch audit](../research/adaptive-campaign-audit-20261004.md)
examines actual 3D trajectories, energy diagnostics, unresolved reconnection
attribution and the cost of the research process. Its data and limitations are
kept with the original dated report.

To contribute a study, include the operator input, version and source identity,
actual run records, verification instructions and a clear account of who did
which work. See [documentation development](../development/documentation.md).
