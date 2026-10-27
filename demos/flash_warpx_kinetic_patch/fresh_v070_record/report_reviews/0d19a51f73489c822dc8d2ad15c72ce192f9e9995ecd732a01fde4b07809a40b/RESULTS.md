# Local pressure closure after a FLASH-to-WarpX handoff

Two fresh kinetic seeds from the new FLASH source give local time-and-area-averaged departures below 0.053 for both species. Applying every contribution in the prospectively declared conservative diagnostic envelope gives upper values **0.14747075 for ions and 0.15448238 for electrons**, below the unchanged **0.20** threshold. All declared qualification gates pass. **Independent claim review `review_01645441bd0eaebf3e6391fd` is resolved: decision `approved`, disposition `supported`.** Its support applies to this particular finite, conditioned local prediction. No credible pressure-closure counterexample was found in the completed trajectories. The envelope is a diagnostic error allowance, not a statistically calibrated or rigorous continuum bound.

The independent reviewer reproduced the fresh means from retained pressure tensors, checked control outputs and their identities, and judged the retained allowances sufficient for this threshold decision. The verdict records no evidence gaps and no required next test. Debye underresolution, electric-field noise sensitivity, approximate boundary-flux quadrature and finite-grid convergence still prevent general solver or continuum validation. Formal claim acceptance and report assessment remain separate authorities; the claim verdict does not itself accept this report.

The refined-source qualification baseline gives time-and-area means A_i=0.05145 and A_e=0.04882 over tΩ_ci∈[0.4,0.9]. Doubling the kinetic mesh at unchanged particles per cell lowers these to 0.03514 and 0.04045. These shifts, 0.01630 and 0.00837, are retained as uncertainty contributions. At fixed CFL, this mesh change also halves the timestep; a separate timestep-only control addresses that sensitivity. The primary-versus-secondary spatial-bin changes are about 0.032–0.035 on the base mesh and are also retained. Small measured anisotropy alone does not establish an accurate diagnostic.

## Fresh evidence and complete uncertainty ledger

| Species | Seed 6101 | Seed 6102 | Maximum fresh mean | Additive envelope | Upper value |
|---|---:|---:|---:|---:|---:|
| ions | 0.04938627 | 0.04779225 | 0.04938627 | 0.09808448 | 0.14747075 |
| electrons | 0.04732667 | 0.05204808 | 0.05204808 | 0.10243430 | 0.15448238 |

| Contribution | Ions | Electrons |
|---|---:|---:|
| source | 0.00079725 | 0.00148375 |
| boundary | 0.00154058 | 0.00030560 |
| mesh | 0.01630407 | 0.00836643 |
| timestep | 0.00055578 | 0.00207841 |
| particle_count | 0.01046842 | 0.00209196 |
| full_fresh_seed_range | 0.00159401 | 0.00472141 |
| sampling_two_sigma_no_time_independence | 0.02184214 | 0.02183159 |
| subbin_flow_pressure_upper | 0.00998560 | 0.00566121 |
| primary_secondary_mean_A_difference | 0.03418260 | 0.03455045 |
| relativistic_trace_correction | 0.00081403 | 0.02134350 |

The point estimates are emitted directly by the evidence-stage solver entrypoint. `exp_cef42c711fc9dc4c8638c440` is a frozen postprocessing/qualification replay and arithmetic interpretation, recorded as exploration; it is not relabeled evidence. Its analysis source is the corrected source bound in the approved method. It checks every fresh sample required by the window, initial matching, relaxation, bin/shear reconstruction and approximate energy budget; every gate passes for both seeds. The conservative ledger uses the maximum contribution over fresh and control cases rather than selecting a favorable seed. Supporting qualification outputs are not fresh hypothesis trajectories.

The independent claim review reproduces ion means 0.04938627 and 0.04779225 and electron means 0.04732667 and 0.05204808. Both fresh trajectories cover the complete [0.4,0.9]/Ω_ci window. The reviewer found finite, positive pressure tensors and populated required bins, confirmed local species-flow subtraction before averaging departures, and reported finer-bin means below 0.084.

Fresh-evidence figures: [pressure controls](plots/fresh_pressure_controls.png), [seed6101 fields](plots/fresh_seed6101_kinetic_fields.png), [seed6101 tensors](plots/fresh_seed6101_pressure_tensor.png), [seed6102 fields](plots/fresh_seed6102_kinetic_fields.png), [seed6102 tensors](plots/fresh_seed6102_pressure_tensor.png).

## Scientific realization and source choice

The autonomous source choice, recorded before kinetic evidence, is the first FLASH output at normalized time t≥0.8, using the origin-centered coalescence sheet. FLASH evolves the supplied resistive-MHD island model with η=0.001, α=20, scalar pressure, γ=5/3, adaptive CFL 0.4, a reflecting unit square and four ranks. The 512² qualification snapshot is at 0.8001113920, from `exp_f195949ab1410375cc7b8f44`; SHA-256 `2cb14d09a0cbfcb26bec13ba223adca01dd7425841fe89952ac8a5831cd612cd`.

The sheet half-width is precisely

$$\delta=\frac{\max_{0\leq z\leq0.1}|B_x(0,z)|}{|\partial_z B_x(0,0)|},$$

using a cubic spline of the original cell-centered FLASH magnetic field. It is 0.01605016 code units, spanning 8.22 FLASH cells (8.218 at the retained precision). Refinement from 256² changes width by 1.14%; local density, pressure, magnetic field, flow and current RMS changes are below 0.8% (`exp_2f9bf7deff8148a543a2c4f3`). This is a finite-resolution qualification, not an asymptotic convergence proof.

The mapping uses m_i=25m_e, T_i/T_e=1, n_0=10²⁴ m⁻³, v_0=0.01c, B_0=16.3552 T and L_0=1.67435 mm. Reference d_i=26.5705 micrometres corresponds to 0.01586914 code units. Thus δ/d_i=1.0114; using the central density gives 0.9943. The artificial ion mass, temperature partition and density/length scales are extra assumptions, not information inferred from MHD. Collision frequency is deliberately zero in the kinetic realization; no claim about physical collisionality at this density is made.

The right-handed coordinate map is FLASH (x,y,z) to WarpX (X,Y,Z)=(x,−z,y). The transfer retains density, total scalar pressure, bulk flow, topology and current, reconstructs a potential and takes its discrete Yee-grid curl. Species drifts preserve center-of-mass flow. Initial electric field is −u×B; FLASH resistivity is not continued in PIC. There is no fitted analytic equilibrium and no two-way coupling.

## Measurement and controls

The fixed measurement rectangle is |X|<0.04, |Z|<0.015 in code coordinates, divided into 4×4 equal-area bins, with 8×8 secondary bins. Pressure uses actual velocity v=u/√(1+u²/c²) and subtracts each bin's species mean velocity. For each species, the local observable is

$$A_s=\frac{\|P_s-\operatorname{tr}(P_s)I/3\|_F}{\sqrt{3}\,\operatorname{tr}(P_s)/3}.$$

The estimator takes the area mean of these local departures, followed by physical-time integration over [0.4,0.9]/Ω_ci, with interpolated window endpoints. Tensors are not averaged before taking the norm. This window lasts 0.5/Ω_ci=4.3454 ps after a 3.4763 ps initialization allowance.

Every primary bin must have at least 256 particles and effective count 512 at every integration/bracketing sample. Secondary thresholds are 128 and 256. Failed or missing bins invalidate the measurement; none are dropped. Quiet loading enforces isotropic velocity covariance per source cell. The realized finite distribution and absorbing boundary conditions condition the result.

The base patch has half-size 0.3, 384² cells, 32 particles per cell per species, quadratic particle shape, explicit Yee fields, Esirkepov deposition and CFL 0.7. Fields use Silver–Mueller boundaries and particles are absorbed. The timestep is 4.31945×10⁻¹⁵ s, with Δtω_pe=0.24368 and ΔtΩ_ce=0.01243. The cell spacing is 0.4923d_e and about 5.84 minimum Debye lengths; the finer mesh remains at about 2.92 minimum Debye lengths. The Debye scale is underresolved. Actual mesh, timestep, particle, scalar-heating and energy controls are therefore required, and the finite comparison errors remain in the envelope.

| Control | Mean-A difference, ions | Mean-A difference, electrons | Receipt |
|---|---:|---:|---|
| FLASH source refinement | 0.00080 | 0.00148 | `exp_b6a2adccb584b91734873c8d` |
| Kinetic mesh doubled, same ppc | 0.01630 | 0.00837 | `exp_af3f8c4f97f31b360a115b36` |
| Timestep halved | 0.000556 | 0.002078 | `exp_a3feea9cfd7050363e077857` |
| Particles per cell doubled | 0.010468 | 0.002092 | `exp_598cf8a2dc75dceade0c52c4` |
| Refined-source patch enlarged, same cell scale | 0.001541 | 0.000306 | `exp_4b72bb874b27665a7cc11322` |

The corrected tensor audits are `exp_3e16729b5240dd577dbe960d` and `exp_6cdf470bcffa5a00adfd8755`. All analyzed controls pass initial density, pressure, flow, current, neutrality, secondary shear, relaxation and approximate energy-budget gates. Mean-A changes for timestep, ppc and boundary controls are at most 0.00208, 0.01047 and 0.00154. The matched refined-source boundary control changes scalar pressure by at most 2.56% and density by 1.32%, inside the frozen 3% boundary tolerances. Field signals can cross the boundary-to-region distance before the observation window; no light-cone exclusion is claimed. Particle-origin diagnostics and matched larger-patch evolution address different influences.

### Initial matching: qualification baseline versus fresh seeds

The approximately 8.1% current mismatch and 0.0176v_0 flow error belong to the refined-source qualification baseline, seed 4101 (`exp_0cc759f4429f9587ef9f4c55`). They are not the measured initialization errors of fresh seeds 6101 and 6102. The source-bound audits give:

| Trajectory | Current-y RMS relative mismatch | Center-of-mass flow RMS error / v_0 | Density RMS relative error, either species | Ion scalar-pressure RMS relative error | Electron scalar-pressure RMS relative error |
|---|---:|---:|---:|---:|---:|
| Qualification baseline, seed 4101 | 0.08087791 | 0.01761989 | 0.00471369 | 0.00748456 | 0.00662550 |
| Fresh seed 6101 | 0.10417913 | 0.01898742 | 0.00792716 | 0.00748839 | 0.00788173 |
| Fresh seed 6102 | 0.09397843 | 0.02090113 | 0.00590116 | 0.00806272 | 0.00732590 |

Thus the fresh current mismatches are approximately 10.42% and 9.40%, and fresh flow errors are 0.01899v_0 and 0.02090v_0. All three trajectories pass the unchanged initial-current limit 0.20, flow limit 0.03v_0, and density/scalar-pressure RMS limits 0.03. Neutrality is exact at loading in all three audit records. The earlier statement that initial scalar-pressure and density errors are below 0.8% describes the qualification baseline; fresh seed 6102 has an ion scalar-pressure RMS error of approximately 0.8063%.

These values are retained in `qualified_mesh_source.json` and `fresh_analysis.json`, respectively. Their SHA-256 identities match the corresponding `analysis.json` artifacts recorded in `EVIDENCE_INDEX.json`: `bbe8f85936918a32a024fd03340534d1945238c0b9c3e2c44d1340abd1671144` for the qualification audit and `ee59ec4324e7e648220a909431826a4854693f72b6000e689e02169d8d928d1c` for the fresh audit.

Fine-mesh and base qualification energy residuals including absorbed particles and approximate Poynting flux are approximately −0.000568 and −0.00118. The roughly 13% unclosed whole-patch energy loss is primarily absorbed-particle escape, not a closed-system heating residual. Poynting spatial quadrature remains approximate. Scalar pressure changes are controlled separately from anisotropy.

The supplementary field audit `exp_0ae55871794048fcb4bea710` measures scaled final divergence of order 10⁻¹⁴. Electric-field RMS fluctuations change appreciably with timestep, particle count and mesh when normalized to v_0B_0. This is a limitation of field-noise convergence, not discarded evidence; local electric-to-thermal energy remains below its frozen 1% gate, and pressure, density and energy controls separately pass. No electric-wave-spectrum prediction is made.

## Decision rule, methods and evidence identity

`PROTOCOL.json` prospectively freezes source selection, mapping, geometry, window, velocity/pressure convention, eligibility, numerical tolerances and uncertainty rule. The envelope adds measured source, boundary, mesh, timestep, ppc and fresh-seed changes; a fourth-moment sampling estimate without assuming independent times; shear, primary-secondary difference and measured relativistic correction. It is a declared conservative diagnostic envelope, not a calibrated confidence interval. Support requires both species' upper bounds at or below 0.20, with all qualification gates passing. With all gates passing, a lower bound above 0.20 for at least one species would falsify the hypothesis; otherwise the result is unresolved. These rules and thresholds have not changed during report revision.

FLASH instrument readiness is `method_22eff770dcad08077eac18a8`. Production methods `method_3f23af124d2fac16cf3fe561` (FLASH stage) and `method_9cd6ea1753b9d22b49e0a090` (WarpX stage) are approved. They authorize evidence collection, not the claim. Fresh FLASH evidence `exp_7772fa68048aff22c2b815c3` completed in 877 seconds. Its selected source time is 0.8001113920335353, HDF5 SHA-256 `121527c0f4cc4714c93ce9c3ff81a33fe71873d2c6d754a10105760c31d9324c`. The transferred NPZ SHA-256 is `c04a015181c150cb0bd1162976252b0e85f3caf7458ced7d024eb0dca4e35ef7`; numerical arrays match the qualified source exactly.

Exact input-map binding required data-bound production amendment `method_e1bc80492ec63eead697af43`, independently approved. Fresh seeds 6101 (`exp_8e19bd425cb2bd2ef03a61ea`) and 6102 (`exp_882ac26f8158ec6e67fd8372`) completed in 131 and 130 seconds under that binding, both reaching 0.900087883 reference cyclotron units. The source manifest placeholder points to the enclosing fresh FLASH receipt; this receipt and both kinetic parent links supply the exact experiment identity.

The accepted claim-review request contains only those three evidence-stage solver receipts. Exploratory controls and audits supply qualification context without being promoted to fresh hypothesis evidence. The independent reviewer checked that context and accepted the finite threshold conclusion.

## Independent verdict and report assessment

The resolved review is [review_01645441bd0eaebf3e6391fd](../reviews/review_01645441bd0eaebf3e6391fd.json), bound to packet SHA-256 `4c043a3b17947fef37c13d348fe4762fea9a6e511a8a3dc60a2995d75f37712a`. Its formal verdict is `decision: approved`, `disposition: supported` for claim `root`. It reports `evidence_gaps: []` and `next_test: null`. The rationale supports this particular finite realization and observable, finding the inspected pressure controls and retained allowances sufficient for the unchanged 0.20 threshold decision.

This supersedes the report's previous statement that claim review was pending. The original run-finalization snapshot in `research_report.json` and `STUDY_LEDGER.md` recorded the claim as unresolved before the verdict arrived; that historical snapshot is not the later independent claim decision. Execution status `budget_exhausted` likewise describes the numerical allowance, not scientific rejection.

Report assessment is distinct. The original report request `report_75366f4bc1426551f99a8d7d` was deferred when protected review ended, and original finalization recorded `report_status: unreviewed` with a report-assessment validation error. No report acceptance can be inferred from that error, from a proposed assessment that failed validation, or from the subsequent claim approval. This revised report incorporates the completed independent claim verdict and the report-audit corrections; acceptance of the revised report requires its separate report-assessment record.

Numerical execution used an **initial two-hour allowance**, and all numerical work finished before the protected compute cutoff. Independent claim/report review was completed in a **separately authorized post-run review-only session**, using existing results. That session's authorization allowed 30 minutes of review, explicitly prohibited new numerical executions, and did not provide human scientific steering or a human scientific verdict. This revision creates no new simulations, claims, methods or receipts and changes no scientific data or thresholds.

## Inspectable figures and provenance

- [Actual FLASH magnetic field/current/pressure with patch and measurement rectangle](plots/macro_patch.png).
- [Initial/final kinetic magnetic fields for the refined-source qualification baseline](plots/mesh_refined_kinetic_fields.png).
- [Species tensors and local anisotropy for the refined-source qualification baseline](plots/mesh_refined_pressure_tensor.png).
- [Mesh and source comparisons](plots/mesh_pressure_controls.png).
- [Timestep, particle and boundary comparisons](plots/controls_pressure_controls.png).

The two qualification figure paths above are the existing files under `plots/`. Their hashes match the original refined-source figure artifacts in `exp_3e16729b5240dd577dbe960d`: `d0acd3bc41dd86a3bc644fadab4ef05a9d2d55c2d9ca48e1d543aa59e305e973` for fields and `7e756ffc93462d3b10683aeab6468b2d3fcafe3ed453d12d0ef875742d05e2d4` for tensors.

Raw arrays, immutable source files and hashes reside in each experiment receipt/workspace. `calculation.py` is the recorded entry point. Supplied operator helpers established execution only; source selection, physical scaling, window, controls, protocol and fresh trajectories are autonomous study decisions. `EVIDENCE_INDEX.json` and the immutable service receipts retain exact source/input bindings, solver capability/runtime identities, dependencies and output hashes. No solver-source development is recorded.

## Retained failures and limitations

The exact reproduced operator anchor `exp_7dec20d7e3686d5778312433` is permanently non-evidentiary. `exp_e10f88b8220dd98c85fd82ce` had successful FLASH evolution but an invalid directory output declaration. Integrated-handoff controls `exp_0acc6f24de20923ef83122b7` and `exp_f8a71b3d31c7baa5dc5bc97a` exposed optional plotting dependency and current-array scope failures, then `exp_635537f1043786f7af0bd65e` passed the corrected wrapper. These are implementation failures, not physical counterexamples.

Method `method_f0380ba28af101b8b3bdbff8` received `revise` because its production scope excluded the kinetic pressure measurement and qualification; bounded source/transfer readiness was subsequently approved at instrument scope. Methods `method_8b44b842b918a6fc6c34250f` and `method_1e3c2a33bf19188e9cb5f8d0` received `revise` because the secondary-bin audit began at tΩ_ci≥0.475 rather than covering the complete [0.4,0.9] integration/bracketing window, and omitted the required primary-versus-secondary mean-A difference. Corrected replay on retained commissioning tensors and subsequent source-bound approvals resolved those implementation gaps. The material bin differences remain in the uncertainty ledger.

The historical FLASH reconnection-flux-window check was not reached. It concerns a reconnection-rate diagnostic outside the declared local pressure measurement. The independent claim verdict explicitly found that failed check and the copied non-evidence annotation did not invalidate the fresh local-pressure evidence. The operator anchor remains non-evidentiary, and exploratory controls remain exploratory.

Claim-review transport also required correction: the first rejected submission included challenge IDs outside its submitted list; a subsequent rejection prevented exploratory receipts from being included as claim evidence. The accepted request contains the fresh FLASH receipt and both fresh kinetic receipts. These transport corrections change no observation or scientific rule.

The outcome applies only to this finite, quiet-loaded, collisionless local pressure question with the selected mapping and boundaries. It does not establish universal reconnection rates, full MHD–PIC coupling accuracy, collisional plasma behavior, or radiation physics. Floor interventions are not completely audited, macro convergence uses two finite grids, Debye scales remain underresolved, and boundary-energy flux uses spatial quadrature. Electric-field noise is sensitive to numerical settings. These limitations accompany the supported claim and prevent extrapolation to general solver or continuum validation.

## Rerun identity and further discrimination

The recorded rerun interface is `calculation.py`. The macro arguments are:

```text
flash --handoff --eta .001 --nx 512 --ny 512 --alpha 20 --tmax .81 --plot-interval .1 --ranks 4 --iprocs 2 --jprocs 2 --output flash --summary macro.json
```

The kinetic arguments are:

```text
kinetic --patch evidence_patch.npz --output pic --ppc 32 --seed 6101 --duration-omegaci .9 --boundary-accounting --secondary-bins 8 --field-diagnostics 2 --diagnostics 36 --cfl .7 --max-grid-size 384 --moment-bins 4 --roi-x .04 --roi-z .015
```

Replace only the seed by 6102 for its sibling. Use a fresh workspace/output record. Exact installed capability/runtime hashes, complete declared dependencies and output hashes are in `EVIDENCE_INDEX.json` and the immutable service receipts. The full source/input map must match the approved data-bound method for evidence submission. These are retained rerun instructions; no rerun was performed during review or report revision.

The independent verdict requires no further test for acceptance of this finite claim. Broader numerical questions remain outside that acceptance: a matched Debye-resolving trajectory with unchanged physical mapping, ROI and window, together with independent particle-count and timestep controls, would test whether pressure estimates remain within the retained allowances as field noise changes. More accurate boundary-flux quadrature and further matched larger-patch comparisons would test the remaining flux and boundary approximations. These are possible future discriminating tests, not completed evidence or newly authorized executions. Physical falsification would still require all qualification gates to pass and at least one species' lower bound to exceed the unchanged 0.20 threshold.
