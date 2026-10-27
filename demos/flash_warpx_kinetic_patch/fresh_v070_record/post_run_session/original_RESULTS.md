# Local pressure closure after a FLASH-to-WarpX handoff

Two fresh kinetic seeds from the new FLASH source give local time-and-area-averaged departures below 0.053 for both species. Applying every contribution in the prospectively declared conservative diagnostic envelope gives upper values **0.14747 for ions and 0.15448 for electrons**, below the unchanged 0.20 threshold. All declared qualification gates pass. My scientific judgement is that this finite realization supports the local isotropic-pressure prediction within its declared numerical envelope. No credible pressure-closure counterexample was found in these completed trajectories. **Independent claim review `review_01645441bd0eaebf3e6391fd` is pending; the host-recorded original disposition remains unresolved until that verdict**; neither this judgement nor method approval is a verdict. The envelope is a diagnostic error allowance, not a statistically calibrated or rigorous continuum bound.

The refined-source baseline gives time-and-area means $A_i=0.05145$ and $A_e=0.04882$ over $t\Omega_{ci}\in[0.4,0.9]$. Doubling the kinetic mesh at unchanged particles per cell lowers these to 0.03514 and 0.04045. These shifts, 0.01630 and 0.00837, are retained as uncertainty contributions. The primary-versus-secondary spatial-bin changes are about 0.032–0.035 on the base mesh and are also retained. Small measured anisotropy alone does not establish an accurate diagnostic.

## Scientific realization and source choice

The autonomous source choice, recorded before kinetic evidence, is the first FLASH output at normalized time $t\geq0.8$, using the origin-centered coalescence sheet. FLASH evolves the supplied resistive-MHD island model with $\eta=0.001$, $\alpha=20$, scalar pressure, $\gamma=5/3$, adaptive CFL 0.4, a reflecting unit square and four ranks. The $512^2$ qualification snapshot is at 0.8001113920, from `exp_f195949ab1410375cc7b8f44`; SHA-256 `2cb14d09a0cbfcb26bec13ba223adca01dd7425841fe89952ac8a5831cd612cd`.

The sheet half-width is precisely

$$\delta=\frac{\max_{0\leq z\leq0.1}|B_x(0,z)|}{|\partial_z B_x(0,0)|},$$

using a cubic spline of the original cell-centered FLASH magnetic field. It is 0.01605016 code units, spanning 8.22 FLASH cells. Refinement from $256^2$ changes width by 1.14%; local density, pressure, magnetic field, flow and current RMS changes are below 0.8% (`exp_2f9bf7deff8148a543a2c4f3`). This is a finite-resolution qualification, not an asymptotic convergence proof.

The mapping uses $m_i=25m_e$, $T_i/T_e=1$, $n_0=10^{24}\,\mathrm{m^{-3}}$, $v_0=0.01c$, $B_0=16.3552$ T and $L_0=1.67435$ mm. Reference $d_i=26.5705$ micrometres corresponds to 0.01586914 code units. Thus $\delta/d_i=1.0114$; using the central density gives 0.9943. The artificial ion mass, temperature partition and density/length scales are extra assumptions, not information inferred from MHD. Collision frequency is deliberately zero in the kinetic realization; no claim about physical collisionality at this density is made.

The right-handed coordinate map is FLASH $(x,y,z)$ to WarpX $(X,Y,Z)=(x,-z,y)$. The transfer retains density, total scalar pressure, bulk flow, topology and current, reconstructs a potential and takes its discrete Yee-grid curl. Species drifts preserve center-of-mass flow. Initial electric field is $-\mathbf u\times\mathbf B$; FLASH resistivity is not continued in PIC. There is no fitted analytic equilibrium and no two-way coupling.

## Measurement and controls

The fixed measurement rectangle is $|X|<0.04$, $|Z|<0.015$ in code coordinates, divided into $4\times4$ equal-area bins, with $8\times8$ secondary bins. Pressure uses actual velocity $\mathbf v=\mathbf u/\sqrt{1+u^2/c^2}$ and subtracts each bin's species mean velocity. The observable is the area mean of local normalized deviatoric Frobenius norms, followed by physical-time integration over $[0.4,0.9]/\Omega_{ci}$; tensors are not averaged before taking the norm. This window lasts $0.5/\Omega_{ci}=4.3454$ ps after a 3.4763 ps initialization allowance.

Every primary bin must have at least 256 particles and effective count 512 at every integration/bracketing sample. Secondary thresholds are 128 and 256. Failed or missing bins invalidate the measurement; none are dropped. Quiet loading enforces isotropic velocity covariance per source cell. The realized finite distribution and absorbing boundary conditions condition the result.

The base patch has half-size 0.3, $384^2$ cells, 32 particles per cell per species, quadratic particle shape, explicit Yee fields, Esirkepov deposition and CFL 0.7. The timestep is $4.31945\times10^{-15}$ s, with $\Delta t\omega_{pe}=0.24368$ and $\Delta t\Omega_{ce}=0.01243$. The cell spacing is $0.4923d_e$ and about 5.84 minimum Debye lengths. The Debye scale is underresolved; actual mesh, timestep, particle, scalar-heating and energy controls are required and the finite comparison errors remain in the envelope.

| Control | Mean-$A$ difference, ions | Mean-$A$ difference, electrons | Receipt |
|---|---:|---:|---|
| FLASH source refinement | 0.00080 | 0.00148 | `exp_b6a2adccb584b91734873c8d` |
| Kinetic mesh doubled, same ppc | 0.01630 | 0.00837 | `exp_af3f8c4f97f31b360a115b36` |
| Timestep halved | 0.000556 | 0.002078 | `exp_a3feea9cfd7050363e077857` |
| Particles per cell doubled | 0.010468 | 0.002092 | `exp_598cf8a2dc75dceade0c52c4` |
| Refined-source patch enlarged, same cell scale | 0.001541 | 0.000306 | `exp_4b72bb874b27665a7cc11322` |

The corrected tensor audits are `exp_3e16729b5240dd577dbe960d` and `exp_6cdf470bcffa5a00adfd8755`. All analyzed controls pass initial density, pressure, flow, current, neutrality, secondary shear, relaxation and approximate energy-budget gates. Mean-$A$ changes for timestep, ppc and boundary controls are at most 0.00208, 0.01047 and 0.00154. The matched refined-source boundary control changes scalar pressure by at most 2.56% and density by 1.32%, inside the frozen 3% boundary tolerances. Field signals can cross the boundary-to-region distance before the observation window; no light-cone exclusion is claimed. Particle-origin diagnostics and matched larger-patch evolution address different influences.

Initial scalar-pressure and density errors are below 0.8%; current RMS mismatch is about 8.1%, neutrality exact at loading, and center-of-mass flow error about 0.0176$v_0$. Fine and base energy residuals including absorbed particles and approximate Poynting flux are approximately -0.000568 and -0.00118. The roughly 13% unclosed whole-patch energy loss is primarily absorbed-particle escape, not a closed-system heating residual. Poynting spatial quadrature remains approximate. Scalar pressure changes are controlled separately from anisotropy.

## Decision and review status

`PROTOCOL.json` prospectively freezes source selection, mapping, geometry, window, velocity/pressure convention, eligibility, numerical tolerances and uncertainty rule. The envelope adds measured source, boundary, mesh, timestep, ppc and fresh-seed changes; fourth-moment sampling estimate without assuming independent times; shear, primary-secondary difference and measured relativistic correction. It is a declared conservative diagnostic envelope, not a calibrated confidence interval. Support requires both species' upper bounds at or below 0.20, with all qualification gates passing; qualified lower bounds above 0.20 would falsify the hypothesis.

FLASH instrument readiness is `method_22eff770dcad08077eac18a8`. Production methods `method_3f23af124d2fac16cf3fe561` (FLASH stage) and `method_9cd6ea1753b9d22b49e0a090` (WarpX stage) are approved. They authorize evidence collection, not the claim. Fresh FLASH evidence `exp_7772fa68048aff22c2b815c3` completed in 877 seconds. Its selected source time is 0.8001113920335353, HDF5 SHA-256 `121527c0f4cc4714c93ce9c3ff81a33fe71873d2c6d754a10105760c31d9324c`. The transferred NPZ SHA-256 is `c04a015181c150cb0bd1162976252b0e85f3caf7458ced7d024eb0dca4e35ef7`; numerical arrays match the qualified source exactly. Exact input-map binding required data-bound production amendment `method_e1bc80492ec63eead697af43`, independently approved. Fresh seeds 6101 (`exp_8e19bd425cb2bd2ef03a61ea`) and 6102 (`exp_882ac26f8158ec6e67fd8372`) completed in 131 and 130 seconds under that binding, both reaching 0.900087883 reference cyclotron units. The source manifest placeholder points to the enclosing fresh FLASH receipt; this receipt and both kinetic parent links supply the exact experiment identity.

## Inspectable figures and provenance

- [Actual FLASH magnetic field/current/pressure with patch and measurement rectangle](plots/macro_patch.png).
- [Initial/final kinetic magnetic fields](plots/refined_kinetic_fields.png).
- [Species tensors and local anisotropy](plots/refined_pressure_tensor.png).
- [Mesh and source comparisons](plots/mesh_pressure_controls.png).
- [Timestep, particle and boundary comparisons](plots/controls_pressure_controls.png).

Raw arrays, immutable source files and hashes reside in each experiment receipt/workspace. `calculation.py` is the recorded entry point. Supplied operator helpers established execution only; source selection, physical scaling, window, controls, protocol and fresh trajectories are autonomous study decisions.

## Retained failures and limitations

The exact reproduced operator anchor `exp_7dec20d7e3686d5778312433` is permanently non-evidentiary. `exp_e10f88b8220dd98c85fd82ce` had successful FLASH evolution but an invalid directory output declaration. Integrated-handoff controls `exp_0acc6f24de20923ef83122b7` and `exp_f8a71b3d31c7baa5dc5bc97a` exposed optional plotting dependency and current-array scope failures, then `exp_635537f1043786f7af0bd65e` passed the corrected wrapper. These are implementation failures, not physical counterexamples. Independent review also corrected a secondary-bin window/aggregation omission; repaired replay and source-bound approval are recorded.

The outcome applies only to this finite, quiet-loaded, collisionless local pressure question with the selected mapping and boundaries. It does not establish universal reconnection rates, full MHD–PIC coupling accuracy, collisional plasma behavior, or radiation physics. Floor interventions are not completely audited, macro convergence uses two finite grids, Debye scales remain underresolved, and boundary-energy flux uses spatial quadrature. These limitations must accompany any final scientific disposition.

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

The point estimates above are emitted directly by the evidence-stage solver entrypoint. `exp_cef42c711fc9dc4c8638c440` is a frozen postprocessing/qualification replay and arithmetic interpretation, recorded as exploration; it is not relabeled evidence. Its analysis source is the corrected source bound in the approved method. It checks every fresh sample required by the window, initial matching, relaxation, bin/shear reconstruction and approximate energy budget; every gate passes for both seeds. The conservative ledger uses the maximum contribution over fresh and control cases rather than selecting a favorable seed. Supporting qualification outputs are not fresh hypothesis trajectories.

Fresh-evidence figures: [pressure controls](plots/fresh_pressure_controls.png), [seed6101 fields](plots/fresh_seed6101_kinetic_fields.png), [seed6101 tensors](plots/fresh_seed6101_pressure_tensor.png), [seed6102 fields](plots/fresh_seed6102_kinetic_fields.png), [seed6102 tensors](plots/fresh_seed6102_pressure_tensor.png).

The supplementary field audit `exp_0ae55871794048fcb4bea710` measures scaled final divergence of order $10^{-14}$. Electric-field RMS fluctuations change appreciably with timestep, particle count and mesh when normalized to $v_0B_0$. This is a limitation of field-noise convergence, not silently discarded evidence; local electric-to-thermal energy remains below its frozen 1% gate, and pressure, density and energy controls separately pass. No electric-wave-spectrum prediction is made.

## Rerun identity and independent review

All numerical work finished before the protected compute cutoff. Claim review `review_01645441bd0eaebf3e6391fd` was submitted using only the three evidence-stage solver receipts; exploratory controls and audits are qualification context, not relabeled hypothesis evidence. The first rejected submission included challenge IDs outside its submitted list; the subsequent rejection correctly prevented exploratory receipts from being included as claim evidence. The accepted review request includes the fresh FLASH receipt and both fresh kinetic receipts. This transport correction changes no observation or scientific rule.

The recorded rerun interface is `calculation.py`. The macro arguments are `flash --handoff --eta .001 --nx 512 --ny 512 --alpha 20 --tmax .81 --plot-interval .1 --ranks 4 --iprocs 2 --jprocs 2 --output flash --summary macro.json`. The kinetic arguments are `kinetic --patch evidence_patch.npz --output pic --ppc 32 --seed 6101 --duration-omegaci .9 --boundary-accounting --secondary-bins 8 --field-diagnostics 2 --diagnostics 36 --cfl .7 --max-grid-size 384 --moment-bins 4 --roi-x .04 --roi-z .015`; replace only the seed by 6102 for its sibling. Use a fresh workspace/output record. Exact installed capability/runtime hashes, complete declared dependencies and output hashes are in `EVIDENCE_INDEX.json` and the immutable service receipts. The full source/input map must match the approved data-bound method for evidence submission.

Scientific judgement and independent acceptance are distinct: the completed finite experiment supports the prediction under the declared error allowance, while the recorded independent claim disposition is pending. If review declines qualification, the concrete unresolved issues are whether the finite mesh/Debye controls and empirical envelope adequately bound diagnostic error, and whether retained boundary/flux approximations suffice. A further matched Debye-resolving trajectory with unchanged physical ROI/window and independent particle-count control would discriminate those numerical concerns; a physical falsification would still require a qualified departure above 0.20. No additional simulation is launched during finalization.
