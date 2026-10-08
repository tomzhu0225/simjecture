# Magnetic-island coalescence with FLASH

**Can one resolved reconnection-rate scaling describe a resistive-MHD island
coalescence model across its declared resistivity range?** This plasma example
connects a real FLASH simulation, field diagnostics, numerical qualification and
an autonomous attempt to test a scaling hypothesis.

![Four FLASH states showing current density and magnetic-field contours during island coalescence](../../demos/resistive_mhd_island_coalescence/figures/island_coalescence_evolution.png)

*Preserved commissioning run: 2D FLASH 4.8, 128 × 128 cells, four MPI ranks,
uniform resistivity. These are actual computed fields. The commissioning run
establishes a working instrument; it is not evidence for a scaling law.*

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

## A separate minimal-mode investigation

A fresh one-hour study uses the same physical hypothesis and commissioned FLASH
executable, with the current minimal workflow, a separate methods/claim reviewer,
and prospective repair tests. Its operator instructions explicitly require a
valid test of the exponent band and numerical controls. The classic campaign is
retained as historical context, not reused as fresh evidence.

The outcome and compact record will be added after this run finishes. Until then,
the [Kepler study](kepler-energy.md) provides a completed, independently reviewed
example of the current counterexample-and-repair loop.

## Reproduce the instrument or contribute a stronger test

The original demo provides the exact commissioning command and plotting script.
FLASH source and binaries are supplied by the operator under their upstream
license; they are not distributed with this repository. A fresh study must
commission the executable through its actual experiment launcher and retain
its own inputs, diagnostics and evidence.

Useful extensions include a justified rate diagnostic, spatial/time convergence,
branch qualification and a clearer test of the proposed scaling interval.
Start with [guided commissioning](../how-to/guided-commissioning.md) and
[the evidence rules](../concepts/evidence-and-claims.md).
