# Island-coalescence investigation

The immutable original hypothesis concerns a single Sweet–Parker-like branch with exponent −0.60 to −0.40 over nominal `S_eta = 1/eta` from 250 to 4000. No claim has yet been independently accepted.

## Fresh commissioning and exploration

- Exact guided reproduction: `exp_9569a8e06fda35f472250ff6`, completed in 24.39 seconds. Permanently non-evidentiary anchor.
- Agent-owned endpoint pilot: `exp_b3c41a6108aeaaeacd486e86`, S=250, 256², completed t=3 in 444.30 seconds. Flux 0.01–0.05 crossed at t=0.07655–0.52253; rate 0.0896904. Window minimum current-sheet FWHM 14 cells. Sampled mass/energy relative drifts 9.54e−10/5.14e−6; no sampled floor hits. Exploration only.
- Endpoint pilot `exp_04e3aaf4b91379da502dcf40`, S=4000, 256², timed out after t≈2.84. This is an operational failure, not a scientific counterexample. Native exploratory inspection indicates the measurement window was reached, with only four cells across sheet FWHM. Frozen partial-field analysis is being recorded as `exp_162b05b787ba1a4785145383`.
- 384² S=1000 CFL=.4 refinement commissioning was director-cancelled as `exp_e83e063b55e3c437f3f0abcb`.

The physical model remains the supplied compressible, uniform explicit-resistivity, single-fluid MHD setup, alpha=20, gamma=5/3, reflecting square boundaries. Adaptive CFL=0.4 and explicit diffusion timestep remain active. The step limit was increased to avoid artificial termination. Four ranks use the documented MPI helper. Monitor seconds represent normalized simulation time, not a dimensional calibration.

## Planned prospective measurement

Use the guided central flux increment and first linear-interpolated crossings of 0.01 and 0.05; R=0.04/(t_high−t_low), normalized by fixed B0=vA0=L0=rho0=1. S_eta remains a nominal inverse resistivity. Fit log R versus log S by ordinary least squares on five distinct S values 250, 500, 1000, 2000, 4000. Compare 256² against 384². Eligibility requires measured evolving sheet width and convergence, flux-path agreement, finite positive fields, controlled divergence and budgets, and no detected secondary island in the measurement window. Exact thresholds and conservative uncertainty propagation will be frozen for method review before evidence.

Projected scan trajectories use tmax 0.6, 0.8, 1.2, 1.6, 2.15 respectively. Estimated combined scan/refinement cost 1800–2200 seconds; reserve at least 400 seconds for independent review/repair. Preserve censored and excluded cases. Uncertainty intervals overlapping the original exponent band will not reject that band.

Field/current and scaling plots will be drawn from recorded output arrays and labeled by stage. Integrated floor/source corrections are not emitted by this output configuration; sampled minima and conservation residuals do not exclude all between-output corrections.

## Updated qualification and review

CFL=.8/.4 N256 S1000 trajectories `exp_22b4b0e7c2fcdc0417ce7387`/`exp_450f204fb0aa5b05e30c9f0c` completed in103.6/191.3s, rate difference0.1788%. Complete N384 CFL=.8 `exp_45fced4d67b6d6b304622ac3` cost316.7s, rate0.0496429, 0.2233% change, FWHM10 cells. Compact qualification `exp_269229c0cfd7a394281e5796` is exploratory. First method `method_3af30dabc513a09932e43686` required reporting/eligibility repairs, not scientific hypothesis repair. Failed pipeline `exp_77e75a01b02a7eeb7dc220fc` preserved; corrected qualification `exp_fa798c0d82a4ac33d8f8d6b4` passed missing/ineligible refinement and censoring checks, with actual-field exploration figures.

Revised method method_3300b8c9381d0853ddf03442 approved prospective collection. `production_plan.json` records exact commands and caps; high-S refinement is first, other work conditional on a300s review reserve. No claim evidence or accepted disposition yet. Full scan plus refinement cost estimate1591s leaves inadequate margin, so coverage gaps will remain explicit if necessary.

## Prospective evidence collection

Production method `method_3300b8c9381d0853ddf03442` approved collection, not a claim. S4000 N256 `exp_71036c76cc76352d4d71cbda` completed t2.15 in198.76s, R=.0285929, FWHM4; convergence unresolved while N384 `exp_0994411061cacfc10dc58ebb` runs. S250 N256 `exp_e94a72802e57f0848a0009f1` completed in54.42s. S500 N256 exp_248a68db0bbe5af30965f781 now runs. Current critical-path estimate1142s includes20s analysis and300s independent review, with little overrun margin; other refinements remain conditional.

## Evidence coverage and recovery update

All five N256 evidence cases completed: S250 `exp_e94a72802e57f0848a0009f1`, S500 `exp_248a68db0bbe5af30965f781`, S1000 `exp_49024ba434ed878193c528a5`, S2000 `exp_6f79bf4efaa69e1b133e070f`, S4000 `exp_71036c76cc76352d4d71cbda`. N384 S250 `exp_b7941ad7af6db96c755aabf7` completed163.14s; S1000 `exp_8be5a6832b45d20c1bf947ef` still runs. N384 S4000 `exp_0994411061cacfc10dc58ebb` timed out620s after window. Recovery qualification `exp_5dab8c5f0c4a70f047c62d47` is exploratory and confirms both crossings, FWHM6 and raw/parameter identities. Recovery method method_db297e379b50870b6e6d2ec2 pending. Original timeout remains preserved. No accepted scientific disposition.
