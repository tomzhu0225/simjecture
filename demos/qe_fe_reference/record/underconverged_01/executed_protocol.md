# bcc Fe magnetic-metal protocol

This is a second, independently configured material example for the same generic
QE capability and workflow. Question: can the instrument relax bcc ferromagnetic
PBE Fe and produce self-consistent moments, spin-resolved DOS/PDOS and verified
path projections, without an insulating-gap assumption or Fe-specific core code?

Model: one Fe atom in the bcc primitive cell; initial conventional a=2.84 Angstrom.
PBE, scalar-relativistic GBRV Fe v1.5 USPP/NLCC (16 valence electrons); nspin=2,
no SOC and no imposed total magnetization. Starting polarization 0.3 is an initial
value, not a constrained final moment. See the exact JSON/hash and source license.

Run the small SCF first, then the same full optimization -> final SCF -> separate
uniform 12^3 NSCF/DOS/PDOS and 49-point Gamma-H-N-Gamma-P-H bands/projections.
Relax/SCF grids 10^3, 50/250 Ry, cold smearing 0.02 Ry. Use the final SCF Fermi
energy for all plots; a path-derived Fermi estimate does not represent a uniform
BZ integration. Bands are not required to have a gap. The intended Fe 3d marker
indices 5-9 must be checked against the actual projwfc atom/(l,m) mapping.

Broad physical checks: conventional a=(2V)^(1/3) within 2.7-3.0 Angstrom; positive
FM mean total moment 1.8-2.6 muB/atom; finite spin DOS/PDOS and verified bands/
projection indices; preserved SCF checkpoint and independent branches. Report
integrated signed total and absolute moments per cell separately. Here one atom
makes cell and per-atom means numerically identical, but they are not site moments.

At the final reference geometry run independent SCFs: 40/200 and 60/300 Ry;
12^3 sampling at 50/250 Ry; width 0.01 Ry; starting polarizations 0.1, 0.6 and -0.3.
Prospective targets: <=2 meV/atom for 50->60 Ry, <=3 meV/atom for 10^3->12^3,
<=0.05 muB/atom moment change for each numerical control. For positive starts,
require the same FM branch within 0.05 muB/atom and 3 meV/atom; negative start is
expected to find its spin-reversed partner (compare absolute moment and energy).
An unmet target stays failed and prompts a denser or tighter check.

Do not apply the same-functional energy tolerance to differing smearing widths:
report the variational total and smearing contribution separately, plus moment
change. degauss is a numerical integration parameter, not a physical magnetic
temperature. These controls do not establish a full EoS, phase diagram or complete
stress/DOS error bound. One-atom inversion symmetry makes atomic forces trivial.

Reference context: Rahman et al., PRB81,184423(2010), PBE full-potential all-electron
FLAPW gives a=2.83 Angstrom (0 K), mean moment 2.22 muB/atom. Our pseudopotential,
BZ sampling and smearing differ; only a bounded physical-scale comparison is made.
The paper's muffin-tin local moments and magnetization in Tesla are not the QE
integrated total moment. No cross-PP absolute energy comparison is permitted.

Preserve failure records. Synthetic fixtures and copied reference files are not
new calculations. Guided reproduction, if run, remains instrument commissioning
rather than held-out scientific hypothesis evidence.
