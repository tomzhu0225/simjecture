# Material-configured DFT workflow

`examples/dft_workflow.py fetch --case case.json --pseudo-dir pseudo` verifies
HTTPS downloads and SHA256. An existing mismatched PP is never replaced.
`run --case case.json --pseudo-dir pseudo --output fresh-run` executes offline.
An existing output is rejected, including failed runs; choose another directory.
`--smoke` performs only SCF. `--convergence` runs explicit independent controls.

The version-1 JSON case supplies cell_angstrom (right-handed primitive lattice),
atoms (species/fractional coordinates), species (label/mass/PP/source/license/hash),
functional, cutoffs in Ry, tolerances, relax/scf/dos meshes, nbnd, crystal_b path,
DOS spacing, plot range, command timeout and optional acceptance/control settings.
There is no material, electron-count, orbital-count or band-count constant.

## Implemented configuration and data paths

- `spin: nonmagnetic` or `collinear`, and/or consistent `nspin: 1` or `2`.
- `occupations`: fixed, smearing, tetrahedra, tetrahedra_lin or tetrahedra_opt.
  Smearing requires `smearing` (gaussian/gauss, mp/methfessel-paxton,
  mv/cold/marzari-vanderbilt, fd/fermi-dirac) and positive `degauss_ry`.
- `starting_magnetization`: mapping from configured species label to QE value.
  Species entries may also provide it. These are initial spin polarizations,
  not constraints on the self-consistent moment. QE 7.4 interprets magnitudes
  below one as polarization per valence electron and larger magnitudes as moments.
- Optional `tot_charge`; electrons are read from output, including odd or
  fractional counts. `scf_nbnd` optionally controls relax/SCF bands; smeared
  calculations otherwise use nbnd there too. nbnd always controls NSCF/path bands.
- `dos_occupations` optionally chooses the uniform NSCF method. Default: tetrahedra
  for fixed occupations, otherwise the configured occupations. `band_occupations`
  chooses fixed or smearing on the explicit path; tetrahedra cannot integrate a path.
- `dos_degauss_ry`/`dos_smearing` override Gaussian DOS/PDOS broadening. Defaults
  follow the configured PW smearing; PW and PP widths are in Ry, output energies
  and plotting ranges in eV. Both dos.x and projwfc.x receive consistent settings.
- `energy_reference`: auto, vbm, fermi or absolute; `energy_zero_ev` gives an
  explicit override. Auto uses VBM only for a fixed, identifiable occupied-band
  partition, otherwise the final uniform SCF Fermi energy. A path-derived Fermi
  energy is never silently used as the metal's BZ reference.
- `projection_states`: one-based atomic projector indices for marker weights,
  default [1] as a numerical demonstration. Atom/(l,m) mapping is in projwfc.out;
  the driver does not assume an element or angular channel for state 1.

## Execution and parsing

vc-relax uses the explicit cell_dofree all/shape and relaxes ions. QE 7.4 volume
mode requires ibrav=1 and is rejected for this explicit-cell driver. A new SCF
runs at the XML final geometry; each DOS and bands branch receives its own copy.

The uniform branch runs NSCF, dos.x and projwfc.x. The path uses nosym/noinv,
bands.x lsym=false/no_overlap=true, and unsymmetrized k-resolved projections.
For collinear spin, bands.x runs separately for spin_component=1 and 2 with
bands_up/bands_down inputs, logs and data; neither overwrites the other.

PW XML LSDA vectors concatenate up/down at each k point; atomic_proj.xml instead
contains spin-major k blocks and spin attributes. The parser preserves spin
labels/slices and checks every k vector, energy, state index and spin index.
PW energies are Hartree; projection energies are Ry and complex amplitudes become
modulus-squared weights. Rounded bands.x energies allow 0.00051 eV. Scalar and
LSDA DOS/PDOS column layouts and atomic LDOS channels are checked and plotted.
Higher-order smearing kernels can have negative lobes; positivity is not a
universal numerical success criterion. Projection sums are not forced to one.

Occupations come from QE arrays. Fractional occupations are not rounded into a
valence index; no universal nelec/2 or even-electron rule is imposed. A sampled
path gap is optional and may be null or negative. Only a case's explicit
acceptance contract can require a positive gap. Missing requested observables
fail clearly; metals can pass without a gap observable.

Signed total and absolute spin-density moments are retained in muB per cell;
per-atom values are arithmetic means, not atom-resolved local moments. Controls
also record moments, Fermi energy and the smearing energy contribution. Changing
smearing widths changes the variational functional; do not judge width convergence
by blindly applying a same-functional absolute-energy tolerance.

## Validation and concrete gaps

Implementation is parameter driven; real numerical coverage is reported separately
for Si and the magnetic Fe example. Synthetic fixtures verify alternate species,
metal occupations, fractional electrons and collinear spin layouts; they are not
new material calculations. Preserve original executed source and historical outputs.

Noncollinear/SOC spinor input/output is not implemented. Constrained two-Fermi
magnetization is explicitly rejected because this bands path is not qualified for
it. Advanced functional-specific controls (hybrids, Hubbard parameters, etc.)
need implementation/qualification as appropriate; accepting a functional name
alone does not establish a valid research method. This is not a material-name ban.

Sources pinned to QE 7.4: [PW input](https://github.com/QEF/q-e/blob/qe-7.4/PW/Doc/INPUT_PW.def),
[XML writer](https://github.com/QEF/q-e/blob/qe-7.4/Modules/qexsd_init.f90),
[projection writer](https://github.com/QEF/q-e/blob/qe-7.4/PP/src/write_proj.f90),
[band tool](https://github.com/QEF/q-e/blob/qe-7.4/PP/src/bands.f90),
[DOS output](https://github.com/QEF/q-e/blob/qe-7.4/PP/src/dos.f90),
[PDOS format](https://github.com/QEF/q-e/blob/qe-7.4/PP/Doc/INPUT_PROJWFC.def).


## Execution integrity and optional PDOS

`pdos` defaults to true for the full reference pipeline; an explicit JSON false
skips uniform-branch projwfc, atomic PDOS validation and that plot panel, recording
`pdos_status=not_requested`. This is a narrow output selection, not arbitrary stage
composition. The remaining full pipeline still executes relaxation/SCF/DOS/bands
and path projections; --smoke selects SCF only. Requested PDOS requires the complete
atom/radial-wavefunction inventory from projwfc.out and energy-grid agreement
with total PDOS (dos.x may use different endpoints).

Every PW stage must have XML exit_status=0. SCF and relaxation require electronic
convergence; relaxation additionally requires optimizer convergence. NSCF/bands
may normally have scf_conv=false and are checked as non-SCF calculations. These
algorithmic completion checks cannot be waived by omitting a physical convergence
target. Cutoff/k/stress accuracy remains a separate research-plan requirement.
Nonfinite bands.x values always fail.

The launcher and standalone driver now enforce the same pre-execution
[confirmed research plan](research-plan.md). Preview effective values and default
sources, obtain approval of the displayed hash, then supply both plan and receipt.
Protocol archiving alone is insufficient. Parameter/step/protocol/source changes
invalidate the confirmation. This does not replace scientific-method adjudication.

Atomic PDOS columns must be exactly E, one LDOS per spin, then all (2l+1)
m components per spin: 1+nspin*(1+2l+1). Missing and extra component columns
fail, including p (5/9 columns) and d (7/13 columns) in scalar/collinear modes.
Reference analyzers use the same generic completion reassessment for Si and Fe;
missing evidence is unqualified and failed evidence is failed. Neither is a
full pass. Reassessment creates a new report and never overwrites historical
comparison files. Explicit external optimization XML is hashed and must match
the final cell/atoms; a supplied file is evidence, not a user-plan confirmation.
