# Conditional proposal: transient thinning opposed by resistive broadening

**Disposition: no defensible numerical repair prediction is identified by the attached records alone.** The bounded candidate below has a precise prediction procedure, but requires additional calibration diagnostics before it can be committed. No repaired claim is committed, validated or scientifically accepted here. Proceed only if the parent workflow independently accepts the selected root contrast as a counterexample. A failed calibration gate ends this candidate; it does not authorize adding fit parameters.

This assessment uses only `CONTEXT.json` and the three supplied files under `inputs/`. It neither reads parent trajectories nor imports earlier studies. `fresh_record_analysis.json`, reproduced by `python analyze_fresh.py`, records input hashes and the small calculations below. The supplied executable driver was inspected as text and was not imported or run.

## Observations and their limits

The root concerns the contrast-dependent slope of the initial-subtracted flux-window rate, not a global fitted exponent. The selected S_eta=1000→2000 contrast has exploratory 384² rates 0.049688584 and 0.038242447. Its slope is −0.377740 and its recorded empirical interval is [−0.414086, −0.341359]. The S2000 shrinking-change mesh gate fails; the supplied report lists a 512² control as running. This packet provides no result from that control or independent acceptance. These are qualifications and observations, not an accepted falsification.

For the positive-y central Bx profile define B_u as max|Bx| over 0<y<0.1 and h as the first outward crossing of B_u/2, with linear interpolation. Define sigma=h/0.6744897501960817, the width of an error-function template. Unlike the driver's legacy B/J width, this width does not use measured current. It remains a local profile diagnostic rather than an established sheet thickness or true far-upstream field.

| S_eta | flux | time | B_u | sigma |
|---:|---:|---:|---:|---:|
|1000|0.01|0.258749|0.97255|0.017861|
|1000|0.03|0.651017|0.79028|0.012561|
|1000|0.05|1.063762|0.76516|0.012702|
|2000|0.01|0.402296|0.94428|0.010517|
|2000|0.03|0.921754|0.84832|0.009560|
|2000|0.05|1.448254|0.84209|0.008705|

The recomputed crossing durations are 0.805013886 and 1.045958177, exactly reproducing the recorded rates to floating-point precision. Sigma changes by −28.9% and −17.2%, and B_u by −21.3% and −10.8%, from flux 0.01 to 0.05. At matched flux 0.05 the upstream peaks differ by about 10%. Profiles and local currents have larger mesh sensitivity than the integral rate. The 384² inventories contain 1 X and 2 O points in every retained window frame; this is a resolved, sampled topology observation.

Thus stationary sheet geometry is a questionable assumption for this observable. These observations do **not** establish strain, inflow, outflow speed, a shared evolution clock, negligible boundary electromotive force, or resistivity-independent upstream driving. The finite box, pressure evolution and compressibility could change all of them. O-point separation is available but is not automatically the diffusion-region length. Replacing the nominal inverse diffusivity by a measured local Lundquist number would require predicting its B, density and length factors independently.

## One candidate mechanism and its frozen mathematical form

The candidate is kinematic transient compression of one sheet, opposed by resistive broadening, with upstream flux depletion represented by a common flux-stage function. It retains memory of the initial width. It does not balance steady inflow against steady outflow and does not assume stationary Sweet–Parker length, Alfvénic exhaust or incompressibility.

Use normalized diffusivity eta=1/S_eta and the same flux sign and initial subtraction as the supplied reducer. With w=sigma², propose

$$
\frac{dw}{dt}=-2a(\psi)w+2\eta,\qquad
\frac{d\psi}{dt}=\eta\sqrt{\frac{2}{\pi}}\frac{B_u(\psi)}{\sqrt{w}},
\qquad w(0)=w_0,\quad\psi(0)=0.
$$

Here a is the measured inward velocity strain, approximately −∂v_y/∂y at the central sheet. For a Gaussian current layer in linear transverse strain, the width equation describes compression plus diffusion. The associated reconnecting field is locally Bx≈−B_u erf[y/(sqrt(2w))]. Prescribing B_u independently allows upstream supply/depletion; it is an empirical closure, not a derivation of the full compressible induction equation. The coefficient 2 and the factor sqrt(2/pi) are fixed by this template and cannot be fitted to rates.

Let T(q;eta) be the first model crossing of flux q. Predict

$$
\widehat{\Delta t}(S_\eta)=T(0.05;1/S_\eta)-T(0.01;1/S_\eta),\qquad
\widehat R(S_\eta)=0.04/\widehat{\Delta t}(S_\eta).
$$

Solve from the common initial state, including the pre-window phase. Never initialize the model at a validation-measured crossing, width or current. The model supplies both crossing times. No validation-measured field appears on its right-hand side. The flux equation neglects longitudinal-current and boundary/ideal-EMF contributions; those omissions are explicit testable assumptions, not exact consequences of the flux definition.

For constant positive a the width solution is w=w0 exp(−2at)+(eta/a)[1−exp(−2at)]; its a→0 limit is w0+2eta t. Transient and diffusion-limited limits need not give a single exponent for a finite flux interval. This illustrates the candidate's memory, not a fit or explanation of the observed slope.

## Required calibration before any commitment

There are no numerical values for a, w0 or complete B_u(stage) in this proposal: the packet lacks the initial profile and velocity fields needed to fix them. The following procedure fixes them without new resistivity settings or fitting a rate exponent.

1. In the parent workflow, reduce retained full states of the fresh S1000 and S2000 calibration trajectories at the initial state and both actual brackets of flux 0.01, 0.03 and 0.05. Interpolate diagnostics using actual bracket flux weights. Use the finest independently qualified calibration fields and the preceding mesh for uncertainty. A pending 512 result is not an input here. The older full-field archives are reported to retain all frames; later compact runs retain the required full-state brackets.
2. Fix knots q=[0,0.01,0.03,0.05]. At each knot measure B_u and h exactly as above on each side of the sheet. Fit v_y−v_y(0)=−a y by unweighted least squares over |y|≤h, averaging the two central x columns. Require at least four cell centers across 2h. Do not infer strain from J or from a fitted rate. Use both velocity components to measure longitudinal variation, rotation and compression as challenges to the local closure.
3. At each knot set a(q) and B_u(q) to the arithmetic mean of the two anchors' values; connect knots linearly in flux, without smoothing or free coefficients. Set w0 to the mean of their initial independently measured (h/0.6744897501960817)², requiring initial profiles to agree within 1%. No extrapolation of these functions beyond flux [0,0.05] is permitted.
4. Calibration gates: each anchor's B_u must be within 10% of its common knot mean. For strain, require |a_anchor−a_mean| sqrt(w_mean)/v_A,u≤0.1 at every knot, with v_A,u=B_u/sqrt(rho_u), rho_u measured at the corresponding B peak and averaged between sides/anchors. A near-zero strain uses this absolute dimensionless criterion. Preceding-to-finest changes in B_u, h and the dimensionless strain must each be ≤5% (strain absolute change ≤0.05 in the same normalization). The velocity regression relative L2 residual must be ≤20% wherever its fitted velocity norm is nonzero; exactly zero measured and fitted profiles pass.
5. Check the erf-template Bx residual inside |y|≤h: relative L2 residual ≤10% on both anchors at all knots. Compute actual central ∂xBy and boundary/ideal electromotive contributions from the full state using the supplied flux-path sign convention. The time-integrated sum of their absolute omitted flux contributions over the calibration window must be ≤0.0008 (2% of 0.04). More saved states from the already retained archives are needed to bound this integral; a few knot samples cannot certify it. Confirm discrete induction closure against the observed flux change to ≤0.0008 as well.
6. Replay this fixed model at S1000 and S2000. Require duration errors ≤5% and predicted h at each knot within 10% of independent measured h. Replays are calibration checks only. No additional rescaling, diffusivity-dependent coefficient, knot insertion or endpoint-time adjustment is allowed. Failure ends this candidate before validation.
7. Before validation, save and hash the coefficient table, initial width, calibration sources, mesh uncertainties, full predicted crossing times/rates/durations for both new settings, numerical integration settings and the rules below. Halve reduced-model integration step and require predicted duration changes ≤0.2%. Reserve this integration error separately. Numeric predictions must exist before any new validation trajectory is inspected.

The omitted-EMF gate may fail, strain may depend strongly on resistivity, and a Gaussian profile may fit a snapshot without obeying its width equation. These are substantive reasons to reject this candidate. A successful replay would still not establish a unique physical explanation. The supplied packet supports neither assuming the gates pass nor choosing parameter values now.

## Smallest discriminating diagnostic

First request only offline extraction of the existing anchors' initial and flux-bracket full states (at most seven unique snapshots per anchor). Export Bx, By, vx, vy, rho and pressure on the central transverse cut, plus the longitudinal center cut and flux-path endpoint values. Record state hashes, actual times, fluxes and interpolation weights. This can measure strain, independently defined width, local field supply, longitudinal current and boundary EMF without a new trajectory or solver change.

Compare measured a with the sign and magnitude required for the observed width evolution. A constant-strain segment would require dw/dt=−2aw+2eta; finite differences between the measured knot widths provide a preliminary segment check. Rapid thinning accompanied by negligible or outward strain challenges this mechanism directly. If these sparse fields survive the gates, inspect already retained additional times to resolve the integrated omitted EMF and strain evolution; do not claim that three flux samples establish a time history. Set a 120-second wall cap for an initial streamed extraction, with archive I/O overruns reported rather than silently extending the budget. No extraction was possible here because only reduced records, not those full states, were supplied.

## Prospectively selected independent challenges

Choose S_eta=750 (eta=0.0013333333333333333) and 1500 (eta=0.0006666666666666666), before obtaining any data at these settings. Neither is in the five-setting map. The first mildly extrapolates beyond the calibration anchors; the second interpolates. The scope is only these two settings, identical initial state, boundaries, normalization and single-sheet regime. It does not claim the entire [250,4000] domain.

Use the unchanged compiled solver and source-bound parent workflow, 384², CFL0.4, cadence0.005, four MPI ranks, one thread. Planning horizon caps are 1.3 and 1.8. Once numeric predictions exist, both predicted upper crossings must be ≤tmax/1.2; otherwise stop this budgeted plan before validation. Do not pick replacement settings after viewing outcomes. Incomplete windows or a budget stop are inconclusive, not failed mechanisms. Record executable, driver/reducer and parameter-file SHA256, exact launcher/argv and calibration-state hashes with each future receipt. Future execution, method review and scientific acceptance belong to the parent; none are performed here.

Rate and numerical admissibility use the supplied first-linear-crossing reducer. Retain the original positivity, uniform-eta, conservation, boundary, divergence, topology and shrinking-mesh-change gates. Additionally require per-case deterministic relative rate uncertainty u≤0.03 for this 10%-accuracy proposal. Compute the original last-three-mesh + bracket + orthogonal-path + measured-CFL envelope with its 1% floor; do not transfer a mesh envelope to a new eta without justified numerical controls. A topology/regime change is out of scope, not automatic confirmation or refutation of the kinematic law.

For each qualified new case form the observed duration interval

$$
I_{\rm obs}=\left[\frac{0.04}{R(1+u)},\frac{0.04}{R(1-u)}\right],
$$

and the fixed prediction interval I_pred=[0.898,1.102] times predicted duration. This combines the prospectively chosen 10% model allowance and 0.2% integration allowance additively; it is not a confidence interval. No later coefficient-uncertainty enlargement is allowed. One disjoint pair of intervals falsifies this bounded candidate. Both wholly contained observed intervals are required for a two-case survival result; partial overlap is inconclusive. Freeze point predictions, not a fitted exponent band.

Also challenge the mechanism on validation fields without feeding them into the predictor: predicted half-amplitude widths and B_u at flux 0.01,0.03,0.05 must agree within 10% plus independently bounded diagnostic error ≤5%; a definitely >15% discrepancy at any knot refutes the proposed field mechanism even if the rate happens to agree. Re-evaluate the omitted-flux integral gate of 0.0008 and strain dimensionless discrepancy gate 0.1. A definitely exceeded gate in an otherwise admissible trajectory refutes the associated closure assumption. Diagnose evolving sheet length, outflow, density/pressure pileup and X/O positions: strong longitudinal structure or geometry changes correlated with residuals identify what the simple model omits. Such correlations do not validate a replacement law.

## Recorded-cost budget and acceptance boundary

Completed 384² trajectories cost 681.5 s at S1000 through tmax1.3 and 977.0 s at S2000 through tmax1.8, including recorded execution overhead. These are actual completed records; pending 512 costs are forecasts only. The observed throughputs are 524.2 and 542.8 wall seconds per unit simulated time.

| New setting | Time cap | Planning cost | With 50% reserve |
|---:|---:|---:|---:|
|750, 384²|1.3|681.5 s|1022.3 s|
|1500, 384²|1.8|960.3 s|1440.5 s|
|Total, sequential| |1641.8 s (27.4 min)|2462.7 s (41.0 min)|

The reserve corresponds to 2.74 rank-hours at four ranks. Lower S can impose a tighter explicit-diffusion step, so this is a planning estimate, not a runtime guarantee. Sequential execution minimizes peak storage. Recorded S1000 archive size was 0.784 GB; the S2000 peak raw/archive forecast was about 2.92 GB. Reserve at least 3.1 GB per active trajectory and release temporary reservation between runs. Actual retained size for the new settings is unknown; do not prune protected data to fit this proposal.

Two 384² trajectories fit the requested approximate two-trajectory envelope for **screening**, but do not by themselves qualify their numerical uncertainty. Additional independent new-setting 192/256 and CFL controls are not included in that headline. A rough recorded analogue adds 129.9+286.0+172.1+372.2=960.2 s for two lower-mesh pairs and 442.8+585.1=1027.9 s for two 256² CFL0.2 controls. The combined base would be about 3630 s (60.5 min), or about 90.8 min with 50% reserve, before offline work or a 512 refinement. Exact new-setting costs can differ. Do not label the cheaper two-run outcome accepted validation if its controls are unavailable. If only the two-run allocation exists, keep the result provisional or postpone validation.

The present deliverable therefore completes a conditional research proposal, not a repaired scientific result. Additional calibration from retained fields is required before commitment; additional numerical controls may be required before independent acceptance. The smallest justified next action is the offline two-anchor diagnostic, which may reject this mechanism without paying for either new trajectory.
