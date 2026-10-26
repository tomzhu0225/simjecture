# Integrity review addendum (2026-10-26)

New algorithmic completion, finite-band and requested atomic-PDOS guards are
regression-tested separately; no fresh full Si DFT was run. Archived raw evidence
and source hashes remain unchanged. IEEE_INVALID_FLAG also occurs in the Si logs,
not only Fe; its origin remains unresolved. The Fe full-pass correction is
recorded in ../qe_fe_reference/VALIDATION.md. Implementation validation is separate from the historical numerical record below;
the draft PR records the current regression commands and limitations.

# Local qualification (2026-10-24)

The original Si-configured workflow and a separate
model-free Simjecture guided reproduction passed. Their exact executed source is retained in record/full_reference/executed_workflow.py.txt. This record does not claim an
autonomous LLM/API run, held-out hypothesis evidence or all-material validation.


## Current driver correction and validation coverage

The original driver improperly converted the nonmagnetic Si example's validation
scope into a generic restriction. The current driver implements configured
scalar/collinear spin, fixed/smeared/tetrahedron occupations and widths, QE
occupation arrays and spin blocks, separate up/down bands files, spin DOS/PDOS,
and final-SCF Fermi alignment. A gap is optional and never a general success gate.
Concrete SOC/noncollinear/two-Fermi gaps are documented in the skill reference.

The final affected regression set has 74 passes and 1 optional smolagents skip,
including a coupled synthetic metal workflow, fractional electrons, unequal PW
spin-band block counts, real Si/Fe formats, spin projection indices and moment units. The archived Si eigenvalues/projections are exactly
unchanged under the new parser; four PW input types are byte-identical. This is
reanalysis/input compatibility, not a new complete Si DFT run. In addition, the
final source actually ran a new small Si SCF through the real project entry
(return code 0; record/generalization). Current numerical
magnetic-metal coverage is recorded separately in ../qe_fe_reference/VALIDATION.md.
The original Si records below retain their actual source hashes and test counts;
they are not silently relabeled as new-version executions.
## Actual checks

| Layer | Actual outcome |
|---|---|
| Isolated QE runtime | QE 7.4 conda-forge hac89879_0; 90 exact hashed artifacts; Linux x86_64 WSL2 |
| Initial public installer | Installed and verified in a new isolated Linux-native prefix; base/research Conda preserved |
| Final Windows deployment wrapper | Two real invocations: install and doctor both ready=true, changed=false on each invocation |
| Runtime identity after repeat | Original and resolved replay configurations point to identical binary identity |
| Final affected regression modules | 74 passed, 1 skipped: optional smolagents unavailable |
| Si acceptance success/failure tests | Included in the final count; explicitly synthetic, no DFT executed |
| Real-output parsing regression | Recorded 105 path points, 12 bands, 8 atomic projectors; actual filband/XML/complex projection order verified |
| Historical configuration tests | Replacement species, multi-species cells, different functional, path and 19 bands; the original rejection of spin/metal modes was a functional bug corrected below |
| Whole-repository Ruff | Passed |
| PowerShell, Bash, replay helper | Syntax and helper --help passed; time-stamped replay wrapper assembled from validated commands, not separately rerun end to end |
| Documentation | Sphinx 8.2.3, warnings-as-errors, frozen docs dependencies; generated local links: 0 failures |
| Full configured Si through Simjecture | Passed real skill/capability discovery, sealed inputs and Bubblewrap; all 12 QE commands completed |
| Independent guided reproduction | succeeded, source/config hashes agree, no missing outputs, input mutations or output findings |
| Paid LLM/provider interaction | Not performed |

The four affected modules are test_quantum_espresso.py, test_deployment.py,
test_agent_skills.py and test_research_guidance.py. The final run includes the acceptance and actual Fe format regressions. Historical
qualification_checks.json retains the older run's actual 61+2 counts; overlapping
regression totals are not added to the final number.

## Si configuration and measurements

PBE; GBRV Si v1 scalar-relativistic ultrasoft PP/NLCC, four valence electrons per
atom; two-atom diamond primitive cell; nonmagnetic fixed occupations; 50/250 Ry
wavefunction/density cutoffs; electronic threshold 1e-9 Ry. Ideal fractional
positions start at conventional a=5.47 Angstrom; full-cell/ion BFGS relaxation and
a fresh SCF use an unshifted 10x10x10 grid (47 irreducible points). Independent
uniform 12x12x12 NSCF has 72 tetrahedron points, 12 bands; the separate
Gamma-X-W-K-Gamma-L path has 105 points. See case.json for all settings.

| Observable | Measured |
|---|---:|
| Conventional lattice a | 5.4676573543 Angstrom |
| Primitive volume | 40.8642827095 Angstrom^3 |
| Final pressure | 0.0000230647 kbar |
| Maximum force | 3.37e-33 Ry/Bohr, symmetry constrained |
| Sampled indirect path gap | 0.6139796489 eV |
| Gamma direct gap | 2.5581664260 eV |
| Gamma-to-X endpoint transition | 0.7560455508 eV |
| Cell total energy | -261.1400496140 eV, only comparable with the same setup |
| Maximum rounded bands.x vs PW XML difference | <=0.00051 eV |

The primitive vectors retain equal lengths and 60-degree mutual angles (maximum
reported deviation 7.11e-15 degrees). Ideal diamond symmetry makes forces nearly
zero; this is not a general displaced-atom force benchmark. The plot uses
verified atomic state 1 marker weights; projwfc.out retains the full atom/(l,m)
mapping and atomic_proj.xml contains all eight projectors. No projection sum was
forced to unity. All uniform DOS/PDOS tables were finite and branch checkpoints
were independent; the final SCF XML was unchanged.

Controls at this same final geometry, relative to 50/250 Ry and 10^3:

| Control | Signed energy change (meV/atom) | Pressure (kbar) |
|---|---:|---:|
| 40/200 Ry, 10^3 | +0.092999 | +0.015238 |
| 60/300 Ry, 10^3 | -0.337611 | +0.001613 |
| 50/250 Ry, 8^3 | +1.560256 | +0.052010 |
| 50/250 Ry, 12^3 | -0.288308 | +0.005052 |

The declared <=2 meV/atom checks for 50->60 Ry and 10^3->12^3 pass. These pairwise
energy checks do not bound all stress, lattice, DOS or band-extremum errors.
The Si analysis exits nonzero when a required control is absent or fails.

## Public reference context

[Csonka et al., PRB 80, 035107 (2009), Table II](https://arxiv.org/abs/0903.4037)
reports PBE lattice a=5.466 Angstrom (different implementation). This result is
+0.00165735 Angstrom, about +0.0303%, from that reference and inside the declared
broad 5.44-5.50 Angstrom interval.

The [official GPAW PBE tutorial](https://gpaw.readthedocs.io/tutorialsexercises/electronic/pbe0/pbe0.html)
uses PAW, a=5.43 Angstrom, 200 eV plane waves and an 8^3 Gamma-centered grid. Its
Gamma direct / Gamma-X endpoint values are 2.559 / 0.707 eV; our differences are
-0.000834 / +0.049046 eV. The endpoint transition is not the true internal-line
fundamental gap. Different PP, lattice and basis allow only physical-scale
comparison, not tight numerical identity. Absolute total energies are never
cross-compared. PBE gaps are not experimental quasiparticle gaps.

## Reproduction and evidence policy

Guided experiment exp_1f73965c7f406ef9bbf54ca7 completed in 420.32 s. Its fresh
workflow took 278.59 s. Total-energy and sampled-gap differences from the original
are 1.60e-11 and 2.22e-12 eV. See guided_verification.json for source-bound checks.
The original workflow took 334.53 s; supervised launcher wall time was 500.23 s.

scientific_evidence_eligible=false is intentional guided-commissioning policy:
the actual experiment has stage=exploration, purpose=validation and
scientific_status=unreviewed. It reproduces a supplied anchor without a
prospective hypothesis commitment or source-bound scientific-method adjudication.
It is not a missing numerical validation flag and has not been changed to imply
research acceptance. A future hypothesis needs its own registered protocol,
method review, fresh evidence and adjudication. No LLM agent/API interaction was
exercised; real project execution and model-free readiness were exercised.

Original capability/replay contract hashes differ because the local replay
snapshot resolves runtime_root to an absolute path. Their binary identity is
identical, and both original executed copies share their historical workflow hash. The
current source is different after the documented spin correction; its small SCF
and archived-output compatibility checks are recorded separately.
Final discovery evidence is in final_discovery_identity.json.

## Preserved failures and resources

Full attempt 01 failed before SCF because QE 7.4 volume cell freedom requires
ibrav=1; the explicit-cell driver now requires all/shape. Attempt 02 was stopped
by its own C-disk guard and remains a failure. Attempt 03 completed the pipeline
but failed the 6^3->8^3 2 meV target (9.844 meV/atom); production sampling was
increased to 10^3 and checked against 12^3. Its raw record was not overwritten.
The first guided discovery tried optional uninstalled capabilities; the launcher
now emits a QE-only resolved snapshot instead. Synthetic parser passes were not
used as substitutes for those actual calculations.

The final case used one thread, a 768 MiB address-space limit and a 512 MiB
workspace limit. Existing guided service defaults are 4 GiB address space and
workspace; it still uses one solver thread. Both runs had a task-only low-disk
watchdog; no stop triggered. Observed solver RSS was about 55-66 MiB and WSL
resident memory about 1.62 GiB at a sampled point, not a certified peak. Minimum
C reserve in the accepted run was about 14.00 GiB. Output/scratch/tmp physically
reside on D; no installation was repeated during final qualification.

Logical retained footprints (du -sb): QE prefix 830,890,276 bytes; attempt 03
174,384,491; accepted run 04 201,323,582; guided study 202,040,445; isolated docs
dependencies 62,418,729. The three completed workflows after resource recovery
used 807.56 s of workflow wall time, or about 1,200.41 s including their guarded
launchers; these are not measured aggregate CPU-seconds. Detailed retained cache
and earlier-task footprints stay in the local operator handoff.

Compact raw/derived evidence is in record/full_reference (about 2 MB) with a
per-file SHA256 manifest. No PP payload, wavefunctions, charge-density checkpoints
or installed packages are committed. Historical small SCF evidence and its XML
pressure-unit regression remain separate. The PP URL/hash/license are in the
case and REFERENCES.md. No push, PR, publication, paging change, reboot,
unrelated-process stop or data cleanup was performed.
