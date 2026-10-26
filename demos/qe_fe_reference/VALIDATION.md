# Correction following integrity review (2026-10-26)

The previous full-workflow pass is withdrawn: original Fe02 relaxation XML has
exit_status=3 and opt_conv/convergence_achieved=false. The new stage gate rejects
this checkpoint. The quoted lattice is a measured geometry, not a qualified
equilibrium result. Subsequent SCF/spectral parsing and fixed-geometry energy/
moment controls remain observations, but cannot establish successful relaxation.
No new DFT was run in this fix. The original records below are retained as
historical provenance; their success labels do not override this correction.
A converged relaxation and downstream rerun are needed for a new full pass.

# Local qualification: collinear magnetic bcc Fe (2026-10-24)

The same material-configured Simjecture capability, skill, launcher, workflow,
parsers and plots used for Si completed this case. No Fe-specific core adapter
was added. Full run02 has a final Bubblewrap execution receipt and supervisor
return code 0, and all 13 declared Fe comparison checks pass. This qualifies the
specified energy/moment and integration checks, not every observable or magnetic
phase. Read the explicit stress and warning limitations below.

## Configuration and measured results

PBE; GBRV Fe v1.5 scalar-relativistic ultrasoft PP/NLCC, 16 valence electrons;
one-atom bcc primitive cell, nspin=2, cold smearing 0.02 Ry, starting polarization
0.3, no imposed total magnetization. The refined case repeats vc-relax from the
preserved run01 final geometry, then performs final-geometry SCF, independent
uniform NSCF/DOS/PDOS and path bands/projections. Settings: 60/300 Ry, relax/SCF
14^3, DOS 16^3, 16 bands per spin; Gamma-H-N-Gamma-P-H with 49 points. The exact
cell, source geometry hash and settings are in case.json and PROTOCOL.md.

| Quantity | Measured value |
|---|---:|
| Conventional a=(2V)^(1/3) | 2.8308961622 Angstrom |
| Signed total moment | 2.1896755931 muB/cell |
| Absolute moment | 2.3084270233 muB/cell |
| Final SCF pressure | +0.184320902 kbar |
| Spin DOS at final-SCF Fermi level, up/down | 0.743620887 / 0.185379113 states/eV/cell |
| Maximum bands.x/PW XML discrepancy | 0.000499867 eV |
| Projection array | 49 k points x 13 atomic states x 32 spin-resolved bands |

The cell contains one atom, so per-cell integrated moments equal their per-atom
arithmetic means. Total and absolute spin-density integrals are different
quantities; neither is a site-resolved local moment. Starting magnetization is
an initial guess, not a constraint. The final uniform SCF supplies the common
Fermi alignment. A path gap is null and is not a success requirement. Separate
up/down bands.x files prevent branch overwriting. Every k/energy/spin/projector
index was checked; selected states 5-9 match l=2 in the actual projwfc mapping.
Weights are not renormalized to unity.

## Numerical controls at the same final geometry

Differences below are relative to 60/300 Ry, 14^3 and width 0.02 Ry.

| Control | Delta E (meV/atom) | Signed moment (muB/atom) | Pressure (kbar) |
|---|---:|---:|---:|
| 50/250 Ry | +2.872146 | 2.189955271 | -2.204592 |
| 70/350 Ry | -1.755210 | 2.189751942 | -1.469631 |
| 16^3 k grid | -0.094426 | 2.201509726 | +3.927889 |
| Width 0.01 Ry | -4.098258 | 2.219811262 | +6.050119 |
| Initial polarization 0.1 | +0.000002547 | 2.189592106 | +0.459344 |
| Initial polarization 0.6 | +0.000004805 | 2.189682936 | +0.750919 |
| Initial polarization -0.3 | +0.000000025 | -2.189671215 | +0.201806 |

The prospective 60->70 Ry <=2 meV/atom and 14^3->16^3 <=3 meV/atom checks pass.
Their moment differences and the smaller-width moment change (0.030136 muB/atom)
pass 0.05 muB/atom. Multiple positive starts recover the same FM solution; the
negative start recovers its spin-reversed partner, within 8.35e-5 muB/atom in
absolute total moment and 4.81e-6 meV/atom in energy. This is not a search over
all magnetic phases. Smearing changes the variational functional: the differing-
width raw energy is reported with its smearing term and is not subjected to the
same-functional cutoff/k energy tolerance. Width is not magnetic temperature.

**Stress is not fully qualified.** The final independent SCF pressure exceeds
the BFGS internal 0.1 kbar target, and controls change pressure by several kbar.
The text P=0.18 agrees with the parsed XML/unit conversion, but energy/moment
acceptance does not establish stress convergence, an EoS, or a lattice-error
bound. One-atom symmetry also makes forces trivial. Finite broadened DOS does
not determine the complete zero-temperature Fermi surface.

## Raw warning audit and final completion

IEEE_INVALID_FLAG appears in raw QE outputs and is preserved unchanged. All 16
QE command return codes are zero, JOB DONE is present, command/input/output
hashes agree, and no SCF nonconvergence was found. The inspected eigenvalues,
occupations, k vectors, complex projection weights and DOS/PDOS arrays are finite;
spin/band indexing and pressure conversion agree. See observed_output_audit.json
and the separate final execution_receipt.json. The audit was captured before
the outer receipt; that receipt is now complete, with no timeout, cancellation,
workspace excess or output truncation. The internal origin of the IEEE flag has
not been isolated. No anomaly was found in the checked observables; this is not
a guarantee about every binary checkpoint value or all uses of this build.

## Public reference context

[Rahman et al., PRB 81, 184423 (2010)](https://arxiv.org/pdf/1005.0297)
reports PBE full-potential all-electron FLAPW bcc a=2.83 Angstrom and mean moment
2.22 muB/atom, at an optimized 0 K volume with scalar-relativistic valence and
no SOC in the baseline. Our differences are +0.00089616 Angstrom (+0.0317%) and
-0.03032441 muB/atom (-1.366%). PP/basis, BZ integration and smearing differ;
this is physical-scale context, not a tight identical-method benchmark. The
paper's muffin-tin moment and magnetization in Tesla are not substituted for
QE's integrated moment. Absolute energies across methods are not compared.
PP URL, GPL-3.0 license and SHA256 are in REFERENCES.md and case.json.

## Coverage, preserved failures and resources

- Actual small SCF: 4^3, 40/200 Ry; total/absolute 1.927806/2.010648 muB/cell.
  These are coarse execution checks, not the final magnetic reference.
- First full run01 completed all branches and project execution, but numerical
  analysis failed: 50->60 Ry 2.8121 meV/atom and 10^3->12^3 moment change 0.110615
  muB/atom exceeded targets. Original results/configuration remain preserved in
  record/underconverged_01 and the local validation directory. Thresholds were
  not relaxed; the refined run02 changed the basis/grid and reran optimization.
- Actual model-free guided **SCF-only** Fe reproduction succeeded:
  exp_a8ea13ee519a8765bd7f7935, energy difference 1.28e-10 eV and moment difference
  1.26e-8 muB/cell. There is no full Fe guided replay claim. Full Fe did execute
  through real Simjecture skill/capability discovery, sealed inputs and Bubblewrap.
- Final affected regressions: **74 passed, 1 optional smolagents skip** across
  QE/deployment/agent_skills/research_guidance. Fixtures cover replacement/multiple
  species, differing band counts, metal occupations, fractional electrons, unequal
  spin-band blocks, synthetic coupled spin execution and both actual Si/Fe formats.
  These fixture checks are not new material calculations. Ruff, strict Sphinx
  and generated local documentation links passed. No LLM/API interaction ran.
- Guided eligibility remains false by design: exploration/validation/unreviewed,
  no prospective hypothesis commitment or scientific-method adjudication. It is
  instrument commissioning, not held-out research evidence.
- One solver thread; final full Fe 768 MiB address-space and 2 GiB workspace limits.
  Reported workflow/capsule/supervisor times: 818.10/819.37/1290.30 s (not aggregate
  CPU seconds). Result bytes 845,030,150; workspace bytes 846,450,348. Minimum C
  reserve 11,355,795,456 bytes; no resource watchdog stop in accepted run02.
  Output/scratch/tmp are on D, including native TMPDIR inside the D-backed WSL VHD.

## Executed source and compact record

Full Fe executed source SHA256 a2d559ffa9cc19ad60ad180fe0e814d6dcdba04a2d5f6898317a6403ea7156f0
is retained as executed_workflow.py.txt. The final source
998b094ce5b4e13cd16a4b2acc3695896b38760e1a904b4f99fe9bb41d09ac6d
differs only by wrapping one f-string; Python AST equality was verified. Original
source hashes were not relabeled. The final bytes also ran an actual new Si
small SCF successfully; Si full archived inputs/eigenvalues/projections remain
compatible. Original complete Si execution predates the spin correction and
retains its own executed source.

record/full_reference contains compact raw inputs/logs, selected XML and complex
projections, spin tables, plot/NPZ/CSV, controls, source, receipt and per-file SHA256
manifest. No PP payload, installed environment, charge/WFC binary or bulk scratch
is in the candidate patch. Implementation gaps remain for noncollinear/SOC,
constrained two-Fermi magnetization and advanced-functional-specific controls;
these are concrete method gaps, not material-name restrictions. No commit,
push, PR, publication, unrelated cleanup or system setting change was performed.
