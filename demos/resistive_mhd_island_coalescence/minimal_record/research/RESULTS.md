# Island coalescence scaling investigation

## Question and scope

Test the supplied two-dimensional, compressible, uniform-resistivity FLASH 4.8
island-coalescence model over nominal $S_\eta=1/\eta\in[250,4000]$. This is
not a dimensional Lundquist number. The immutable claim predicts one resolved,
pre-plasmoid branch with $R\propto S_\eta^p$, $-0.60\le p\le-0.40$, with the
inferred exponent persisting under spatial refinement. Conclusions apply only
to sampled cases in this fluid model; they do not establish a continuous-domain
or universal Sweet–Parker statement.

## Prospective measurement protocol

- Observable: mean flux-transfer rate over $\Psi_{rec}=0.01$ to $0.05$, using
  the guided center-flux reconstruction from both $B_x$ and $B_y$ paths. Normalize
  $d\Psi/dt$ by $B_{up}^2/\sqrt{\rho_{up}}$; $B_{up}$ and $\rho_{up}$ are the
  initial-state means at $x=0$, $0.08\le |y|\le0.12$, with domain length $L=1$.
- Fit: ordinary least squares in $(\log S_\eta,\log R)$, with two-sided 95%
  Student-$t$ confidence limits ($n-2$ degrees of freedom). Preserve the two
  flux paths at saved 0.05 cadence and after 0.10 cadence decimation; require all
  four rates to be finite and positive. Use their full per-case envelope and
  enumerate every mixed low/high rate choice ($2^n$ combinations) when propagating
  exponent uncertainty. This carries observed flux-path and output-cadence
  sensitivity into the decision. A fit interval
  rejects the allowed exponent band only if the entire interval is disjoint from
  $[-0.60,-0.40]$. An interval overlapping the band is inconclusive.
- Resolution: at least four cells across the nominal Sweet–Parker width
  $L/\sqrt{S_\eta}$ and at least four cells across measured central-sheet
  $|J_z|$ FWHM throughout the sampled flux window. This is a minimum screen,
  not a claim of asymptotic convergence. The matched refinement uses 1.25x grids
  and adds at least one nominal-width cell; the analyzer also records measured
  current-FWHM changes. Base grids are $N=96,128,128,192,256$ at
  $S_\eta=250,500,1000,2000,4000$; the matched subset is $S_\eta=250,1000,4000$
  at $N=120,160,320$.
- Pre-plasmoid screen: reconstruct common-gauge $A_z(x,0)$ from both field
  components with an anchored lower-left boundary, require relative path mismatch
  $\le0.15$, and detect full-domain extrema before applying the interior ROI.
  Require no secondary extrema of prominence $\ge0.005$ in
  $|x|\in[0.04,0.22]$ during saved flux-window states. Cases that fail this
  screen are reported as plasmoid-ineligible for the original branch; cases
  missing the full flux window are censored, never physical counterexamples.
- Branch rule: form each log-residual interval from the asymmetric case-rate
  bounds. Flag a practical departure only if the entire interval lies beyond
  $\pm\ln(1.25)$. Treat it as a robust branch counterexample only when the same
  matched $S_\eta$ departs in both base and refined families.
- Refinement and decision: compare the five-point base fit with a matched
  three-point, 1.25x-grid fit spanning the nominal interval. The exponent-change
  interval must lie wholly inside $[-0.10,0.10]$ to call persistence within this
  predeclared margin. Grid disagreement is unresolved numerical sensitivity,
  not a physical falsifier; otherwise the comparison is inconclusive. The trajectories use
  prospective $t_{max}=0.8,1.0,1.25,1.75,2.6$ at
  $S_\eta=250,500,1000,2000,4000$, with adaptive CFL stepping and
  unchanged explicit resistivity, boundaries, initialization, four ranks and
  $0.05$ plot cadence. These horizons scale the anchor's observed flux-window
  time approximately as $\sqrt{S_\eta}$, with extra margin at the high end;
  failure to reach the window is censoring. The four-cell floor is a budget-aware
  revision from the initial eight-cell proposal: pilot costs ruled out the latter
  across the full base scan and a refinement spanning the interval. The initial
  sheet also requires $N/\alpha\ge4$; hence the $S_\eta=250$ base mesh is $N=96$.
  Cases that fail the measured-width screen remain ineligible. Finite
  observations that do not reject the band do not prove the universal claim.
  Numerical eligibility additionally requires max relative mass drift $\le10^{-8}$,
  max relative total-energy drift $\le10^{-4}$, and saved density/pressure minima
  above $100$ times their $10^{-12}$ configured floors. The capability exposes
  no per-step floor or `energyFix` correction counters; saved snapshots cannot
  rule out intermediate corrections. The plotted fit bands describe regression
  uncertainty, not a complete discretization or model-form error budget.

## Receipts and observations

- Exact guided anchor reproduction: `exp_9569a8e06fda35f472250ff6` (fresh
  commissioning, exploration only; not claim evidence). It completed at
  $S_\eta=1000$, $128^2$, four MPI ranks. Its built-in flux window was reached;
  see the recorded receipt and result for measured values and realized controls.
- Higher-resolution pilot: `exp_bed50fd68869aa9e6441647b` (exploration,
  non-evidentiary) completed at $256^2$ in 173.37 s, reached the full flux window,
  and used 3,046 steps. Its native timing log attributes 168.585 s to evolution,
  6.899 s to I/O output, and about 0.12 s per plot write. The archived summary's
  zero-secondary-extrema field is invalid and is not used: it came from an incorrect
  $A_z$ path. Corrected analyses `exp_221d739770cc181b8d261c22` and
  `exp_a37d7d1cc856fe2690be2b19` recompute the screen from archived fields with
  $A_z(x,0)=-\int B_y(x,0)\,dx$.
- A two-rank $128^2$ parity trajectory (`exp_2444697e49621bb414513f34`)
  completed with unchanged physical controls and output cadence; it follows replan
  note `note_d901f678751c9854f397b3b8` acknowledged by director receipt
  `director_77310f1cbac90d0ac353f3d2`. It completed in 41.97 s versus 20.46 s
  for the four-rank anchor; both reached $t=1.2$ in 1,519 steps with identical
  timestep minimum/median/maximum $10^{-6}/7.66\times10^{-4}/9.29\times10^{-4}$.
  The flux-window rate and crossings matched to printed precision. The 256² pilot
  used 3,046 steps with timestep minimum/median/maximum
  $10^{-6}/3.75\times10^{-4}/4.64\times10^{-4}$. Four ranks are retained.
- Corrected archived-field analysis succeeded as `exp_221d739770cc181b8d261c22`:
  the 256² $S_\eta=1000$ pilot had an eight-cell nominal width, four-cell measured
  current FWHM, no secondary extrema under the declared central-sheet screen, and
  a normalized rate near 0.05986. This one exploratory point is not a scaling
  result. Its field/current plot is fresh exploration.
- The initial analysis attempt `exp_fa28259d7b5c3d92a6ba7043` failed because its
  relative input paths omitted the preserved `exploratory/` directory; the
  corrected run above used the hash-verified input copies. No decisive runs have
  started.
- Current analysis source `analysis.py` was rerun against the same archived
  pilot as `exp_a37d7d1cc856fe2690be2b19` to qualify the final screen and
  plotting changes. Final driver validation `exp_aeb0d8442b3e9d877cd2e442`
  completed the four-rank 128² full-window trajectory with all declared checks
  true and `case_eligible=true` (exploration only). The pilot field/current
  figure is copied below as fresh exploration; the associated one-case scaling
  panel is explicitly not a scaling result.
- Revised analyzer plus archived-field analysis completed as `exp_8313678346fff2098a293d5e`; it rederived both flux-path rates at 0.05 and 0.10 cadence, found 1.67e-3 maximum relative cadence sensitivity, common-gauge A-path mismatch 0.0505, mass drift 8.22e-15, total-energy drift 8.07e-6, saved minima $\rho=0.952$ and $p=5.86$, and no central secondary extrema. It marks the one-case exponent analysis inconclusive by construction.
- Synthetic analyzer qualification `exp_7052ef4de75c3cf5e51e6e77` passed all eleven fixtures: missing-path censoring, gauge-shift invariant extrema detection/non-detection and ROI exclusion, common-gauge field reconstruction, known $p=-0.5$ fit, matched refinement, branch departure, and matching by $S_\eta$ despite different case IDs.
- Current `calculation.py` diagnostics were re-run directly against the archived pilot fields, `flash_run.dat`, and `flash_run.log` in `exp_9eead225adfcb6a4329f7c1a`; all checks and `case_eligible` passed, including mass/energy budgets and saved floor margins. It explicitly records correction-counter unavailability. A first audit attempt `exp_f1af58b8dce1c98f27a42a5f` failed on a missing audit-fixture argument and is retained.
- Final synthetic analyzer qualification `exp_4d2102cc29ffc028acbda391` passed all eleven fixture checks under the current analyzer source, including the 1.25x matched-grid increment and matching branch departures by $S_\eta$ across different run IDs.
- Final archived-pilot reanalysis `exp_5e08d217c2e19a178e93c2d1` used that same source, recomputed both paths/cadences, branch fit, common-gauge field diagnostics, conservation and floor checks. It finds one eligible exploratory point and correctly reports base/refinement exponents and persistence as inconclusive with fewer than three points. Its single-case plots remain exploration only.

### Fresh exploration figure: field and current density

![FLASH island-coalescence field magnitude, flux contours, and reconstructed current density at the flux-window midpoint](figures/field_current_exploration_S1000_N256.png)

Source: common-gauge archived-field analysis `exp_8313678346fff2098a293d5e`,
parent trajectory `exp_bed50fd68869aa9e6441647b`. This is exploration, not claim
evidence. The single-case scaling panel is stored at
`figures/scaling_exploration_single_case.png`; the one-case branch residual panel
is `figures/branch_exploration_single_case.png`. No exponent is inferable from
these single-case figures.

Prior production method `method_d10ca9c3e2d5794d2e4528e6` was returned for
revision; it remains preserved as a methods review, not claim evidence. The
revised driver/analyzer/protocol identities and receipts `exp_4d2102cc29ffc028acbda391`,
`exp_5e08d217c2e19a178e93c2d1`, and `exp_9eead225adfcb6a4329f7c1a` are being
submitted for another methods review. No decisive runs have started.

The corrected grid plan and exact case-specific timeouts are in
[`scan_plan.json`](scan_plan.json). A two-point cost model from the four-rank
128² final-driver validation (22.58 s) and 256² pilot (173.37 s), cubic in grid
and linear in physical time, estimates 535 s for the five base cases plus 790 s
for the three-point 1.25x refinement, or about 1,325 s total. This estimate is
extrapolated from $S_\eta=1000$ and does not qualify high-$S_\eta$ crossing times.
The low and high base endpoints will be measured first; refine only if measured
costs preserve at least 180 s for independent final review.

## Figures

No figure is yet a claim-evidence figure. Planned plots will be regenerated from
the hash-verified output archives and compact summaries of their cited receipts.
Field/current-density panels show $|B|$, common-gauge $A_z$ contours satisfying
the two component paths within tolerance, and reconstructed $J_z$ at the output
nearest $\Psi_{rec}=0.03$; scaling plots will show both resolution families,
flux-path/cadence spread, fitted 95% bands, branch residuals, and the matched
exponent comparison.

### Current analyzer repair and budgeted next steps

A subsequent independent methods review identified remaining edge cases in slope uncertainty, asymmetric branch residuals, common-gauge $A_z$ alignment, incomplete-cadence serialization, and interpreting grid disagreement. The current `analysis.py` repairs these: it enumerates all mixed per-case rate-envelope endpoints, uses the full asymmetric residual interval, reconstructs both paths from a shared anchor at $y=0$, serializes incomplete rates as null with censoring, and calls grid disagreement numerical sensitivity. The current 18-fixture qualification passed locally immediately before resubmission; its archived record is pending below. Its nonzero-$B_x$ analytic fixture had relative path mismatch $0.00365$, and mixed-bound slopes exactly matched brute-force enumeration. These are software/diagnostic checks, not evidence about the physical claim.

The prospective decision protocol in `scan_plan.json` now matches the implemented mixed-endpoint and asymmetric branch rules. The available 1097-second budget does not cover the estimated 1325-second base-plus-refinement matrix together with a 180-second independent-review reserve and method/analysis overhead. After production-method approval, obtain the $S_\eta=250$ and 4000 base endpoints first, record realized steps, window crossings, eligibility and cost, then continue distinct base points only if the measured budget preserves the review reserve. The matched refinement is held; if it cannot fit, exponent persistence remains unresolved. No decisive trajectories have yet been run.

A final methods pass found that assessment order could still call a band violation physical before checking refinement compatibility. The current repair blocks all physical falsification when matched spatial refinement is not meaningful, and classifies incompatible matched slopes as numerical sensitivity before considering band violations. New fixtures now exercise (i) both base and refined slope intervals disjoint below the allowed band while their slope comparison is incompatible and (ii) repeated branch departure on unchanged grids. Both are required to remain inconclusive. These checks are synthetic and do not constitute hypothesis evidence.

### Low-end eligibility diagnostics and remaining-budget plan

The production method approved prospective collection as `method_f75c0653e79695559ea0db0d`; this is methods approval, not claim acceptance. Fresh evidence trajectory `exp_c82be7437f3086601d26cdc7` at $S_\eta=250$, $N=96$ reached the unchanged flux window in 10.07 s (crossings near $t=0.0796$ and $0.5303$) but failed the declared common-gauge $A_z$ path tolerance with maximum relative mismatch 0.2486. Archive reanalysis `exp_f49cff6483331225ebbcccde` confirmed all four path/cadence rates were positive (about 0.11386–0.11473 normalized), the flux window was crossed, but the case remained ineligible due to the same mismatch. The generated field/current plot is fresh exploration/reanalysis, not claim evidence.

The planned single mesh sensitivity `exp_9782e73d183bd77e86261640` at $S_\eta=250$, $N=120$ also reached both thresholds (16.33 s) but still failed `az_path_consistency`; the driver reports maximum relative mismatch 0.2176 and measured current-sheet FWHM 6 cells. Thus the low-end pair does not meet the predeclared eligibility rule, and neither is a physical counterexample. No further low-mesh trials are planned without a diagnosed correction.

The original full scan forecast (1325 s) is infeasible with about 692 s remaining. The remaining useful path is fresh method-approved base evidence near the middle and high ends, using the existing $S_\eta=1000$ commissioning only as cost guidance. Approximate four-rank estimates from $N^3t$ scaling are 24 s for $S_\eta=1000,N=128,t_{max}=1.25$, 111 s for $S_\eta=2000,N=192,t_{max}=1.75$, and 376 s for $S_\eta=4000,N=256,t_{max}=2.6$. These estimates are uncertain outside $S_\eta=1000$. Prioritize the high endpoint to measure actual cost/window completion, then add the $S_\eta=2000$ and/or a fresh $S_\eta=1000$ base run only if at least 180 s remains for final independent review plus analysis overhead. Any resulting exponent is a finite sampled subset; the low endpoint is currently ineligible and refinement persistence is unresolved.

### Final budgeted recovery attempts and unresolved status

The two-resolution analyzer experiment `exp_9a4a279813623fb451214a08` exited with a missing-output failure because both inputs inherited the fallback case identifier `exploratory`, so their field-plot filenames collided. Its completed JSON computation is retained in that failed receipt; we do not treat it as a clean stand-alone analysis receipt. The N=128 single-case archived analysis `exp_e6fb1905c98142e1d39a62c7` succeeded; the existing N=256 archived pilot analysis `exp_524cf7f12140e1f2e5cc0115` also succeeded. They show current-source A-path mismatches of 0.2026 (N=128, ineligible) and 0.1274 (N=256, eligible for its exploratory diagnostic), respectively. This is consistent with spatial recovery but does not prove convergence.

The one preplanned middle-resolution recovery run `exp_e7019f81e0a9d3630488f26e` ($S_\eta=1000,N=160$) completed the unchanged flux window in 56.55 s. It measured normalized rate 0.05982, central current FWHM 4 cells, and maximum relative $A_z$ path mismatch 0.1774, above the prospective 0.15 cutoff. It is therefore ineligible. Together, the evidence-stage cases at $S_\eta=250,N=96$ (`exp_c82be7437f3086601d26cdc7`), $S_\eta=250,N=120$ (`exp_9782e73d183bd77e86261640`), $S_\eta=1000,N=128$ (`exp_9e3db9fe2b479941a809ebd9`), and $S_\eta=1000,N=160$ all reached their windows but failed the A-path screen. No threshold was relaxed. The low-end rate estimates are not admitted to a scaling fit.

The attempted $S_\eta=4000,N=256$ base trajectory `exp_81db920f97d08ffcaf40fb10` was cancelled by the research director and is preserved as a partial run. Its native log/data and 28 saved states reach $t=1.3501$; reconstructing flux from saved fields gives $\Delta\Psi=0.03236$, below the required upper threshold 0.05. This case is censored, not a physical counterexample. It has no complete summary or eligibility decision.

The current fresh evidence has zero eligible cases at distinct $S_\eta$ values: the $S_\eta=1000,N=256$ result is commissioning/exploration, not fresh claim evidence, even though its archived diagnostics pass. Thus no prospective exponent fit or branch decision is defined, and no matched refinement persistence can be assessed. The physical hypothesis remains unresolved. The limiting practical issue is the strict common-gauge path-consistency screen at lower/middle resolution, plus the one-hour budget; more mesh refinement without a diagnosed correction is not justified here. The incomplete high endpoint cannot enter a fit. Do not infer continuous-domain or universal claims.

Latest field/current images from hash-verified recorded archives are exploration-only: [S_eta=250, N=96](figures/field_current_exploration_S250_N96.png), [S_eta=1000, N=128](figures/field_current_exploration_S1000_N128.png), and [S_eta=1000, N=256](figures/field_current_exploration_S1000_N256.png). The N=128 image is from `exp_e6fb1905c98142e1d39a62c7`; the N=256 image is from `exp_524cf7f12140e1f2e5cc0115`. No claim-evidence scaling plot exists because fewer than three eligible fresh resistivities were collected. The production method approval is `method_f75c0653e79695559ea0db0d`; no independent scientific claim review has been requested because there is no eligible scaling dataset to adjudicate.

A final single-case archive check and field/current plot for the fresh $S_\eta=1000,N=160$ trajectory succeeded as `exp_b22ef9a7df952405819815ef`. It reproduces all four positive rate estimates (0.05972–0.05983), mass drift $5.0\times10^{-15}$, total-energy drift $1.52\times10^{-5}$, and no detected secondary extrema in saved flux-window states. The A-path mismatch in the plotted state near $t=0.6503$ is 0.0776, but the maximum across saved window states is 0.1774; the case therefore correctly fails the window-wide 0.15 eligibility rule. The field/current image is fresh exploration, not claim evidence: [S_eta=1000, N=160](figures/field_current_exploration_S1000_N160.png).

With 81 s remaining at the latest checkpoint, no further trajectory fits while retaining review time. A planning-only heuristic using the three $S_\eta=1000$ mismatch values (N=128: 0.2026; N=160: 0.1774; N=256: 0.1274, the last from exploration) and a linear fit against $1/N$ projects the 0.15 threshold near N=200, approximately 0.146 at N=208. This is not convergence evidence. If the study resumes with new budget and method review, one N=208 full-window case is the smallest targeted spatial-recovery test; failure should end blind mesh escalation. This prediction is recorded as an unreviewed next-test note, not a result.
