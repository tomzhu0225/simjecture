# Fresh resistive-MHD island-coalescence investigation

The original slope-band hypothesis is **falsified** by the fresh, qualified S_eta=1000→2000 contrast. Independent review `review_d8ed7a3364483fc612a029c3` accepted p_eff=−0.37775156 with deterministic numerical interval **[−0.43140540,−0.32467595]**, wholly above the claimed band [−0.55,−0.45]. This is a counterexample in the supplied fixed physical model. It establishes neither a common global power law nor a result for other physical models.

The explanatory repair is **unfinished**. Recorded calibration of a measured-strain transient-width closure underpredicts the anchor rates by about 25–31% and fails its fixed 5% duration-replay gate. An amplitude-budget extension also fails that gate. A response-derived effective thinning coefficient remains phenomenological and unvalidated. No repaired scientific claim was committed or independently supported, and no new-resistivity validation trajectories were collected. The study's repair completion policy is therefore not satisfied.

## Accepted production evidence

Source-bound production method `method_661a2c5064ad92c6494cf179` was independently approved before these fresh observations. The root reviewer inspected hash-verified production summaries, magnetic series and retained crossing-bracket fields, independently reproduced the rates, numerical envelopes and sampled topology, and accepted the falsification.

|Quantity|S_eta=1000|S_eta=2000|
|---|---:|---:|
|eta|0.001|0.0005|
|Mesh|384²|384²|
|First crossing, flux0.01|0.2587485323|0.4022872241|
|First crossing, flux0.05|1.0637624179|1.4482540773|
|R|0.04968858391|0.03824212964|
|Relative numerical allowance|1.3075619%|2.3908687%|
|R interval|[0.04903887490,0.05033829292]|[0.03732781052,0.03915644876]|
|Wall time|547.28s|772.91s|
|Receipt|exp_40aac93038caa57671014925|exp_755dffd11e2a3f05a6b86b49|

The same supplied By-path center flux, with each run's initial value subtracted, defines both rates. First crossings are linearly interpolated between actual saved times:

$$R=\frac{0.04}{t(\psi_{rec}=0.05)-t(\psi_{rec}=0.01)},\qquad p_{eff}=\frac{\ln(R_b/R_a)}{\ln(S_b/S_a)}.$$

Endpoint propagation uses p_low=ln(Rb_low/Ra_high)/ln2 and p_high=ln(Rb_high/Ra_low)/ln2. Its lower endpoint is0.01859 above−0.45. These are deterministic empirical numerical envelopes, not statistical confidence intervals or rigorous continuum bounds. Mesh points are not treated as Gaussian samples. [contrast.json](contrast.json) preserves the arithmetic, checks and values; [evaluate_contrast.py](evaluate_contrast.py) is its fixed evaluator. The accepted verdict rests on the two production receipts and independently reviewed uncertainty rule, not promotion of exploratory analyses.

![Scaling and contrast slopes](scaling.png)

Gray points are the exploratory five-setting map. Navy points and their numerical envelopes show the accepted fresh contrast. No common fitted exponent is imposed.

## Physical setup and prospective protocol

The supplied FLASH4.8 application evolves normalized 2D compressible single-fluid resistive MHD with uniform eta. The initial state, alpha=20, temperature=3, pressure offset=6, gamma=5/3, reflecting boundaries and square[-0.5,0.5]² remain fixed. S_eta=1/eta is nominal inverse magnetic diffusivity, not a dimensional Lundquist number. The reference executable was reused without source modification or compilation.

Before the fresh map, note_29642e7a3142dea6e9d7b988 fixed the reducer, five logarithmically separated settings 250,500,1000,2000,4000, adjacent-contrast selection, uncertainty and admissibility. The128² exploratory rates were0.0891647,0.0651272,0.0490252,0.0379460,0.0289067, with adjacent slopes−0.4532,−0.4097,−0.3696,−0.3925. The recorded largest-departure rule selected1000→2000. These data remain exploratory qualification; the scientific verdict uses later fresh production.

For each finest control, u=max[0.01,2max(successive relative rate changes over the last three meshes)+full crossing-bracket relative deviation+orthogonal Bx-path rate difference+measured same-mesh CFL difference]. The last mesh change must be<= 5% and smaller than its predecessor; u<=15%. Other gates require complete crossings, finite positive rho andp>100floors, correct runtime parameters, max|divB|<1e−9, boundary-normal fraction<0.05, mass drift<1e−6, energy drift<1%, and the declared single-sheet/pre-plasmoid topology. A qualified slope interval wholly outside the entire band falsifies it; overlap cannot falsify it.

## Spatial, timestep and diagnostic qualification

Both selected settings completed the flux window at 128²,192²,256² and384². S1000 rate changes shrink0.2915%→0.1251% over192→256→384. S2000 initially failed the gate:0.0557% over192→256, then0.2837% over256→384. That failure was preserved. The additional512² control exp_58adb12d461c94104daeff23 gives R=0.038317512 and next change0.1959%, smaller than0.2837%, passing the unchanged gate; it cost2075.01s. Matched-flux384→512 central-current differences shrink to about0.7–1.3%. Minimum reported evolving halfwidths are5.80cells at S1000/384 and5.44cells at S2000/512, distinct from the legacy initial-width flag.

Complete-window256² CFL0.4/0.2 controls change rates by0.0899% and0.0717%. The approved scope transfers that measured timestep contribution to finer grids. Striding0.005-cadence trajectories to approximately0.01 while retaining the last endpoint changes rates by at most8.30e−6 relative; [cadence_comparison.json](cadence_comparison.json) lists each case. Actual saved times are used. Fresh S2000's full crossing-bracket allowance is1.5464%, which is retained in its conservative envelope.

The fine-grid allowances are1.3076% (S1000/384) and1.9826% (S2000/512). Independent methods review explicitly approved transport to fresh384² S2000 production: retain the fine absolute allowance, add the observed512→384 shift and any fresh-anchor difference, then add excess fresh cadence uncertainty; use the larger of this, the direct fresh error sum and the1% floor. Here the absolute components are0.00075969324,0.00007506496 and0.00000031722; the extra relative cadence component is0.00207215724. They yield2.3909%. This does not pretend that the historical384² shrinking gate passed. [final_qualification.json](final_qualification.json) and [spatial_qualification.json](spatial_qualification.json) preserve the recorded controls and matched profiles.

## Admissibility and full-domain fields

The fresh production cases realize uniform explicit resistivity, identical initial fields and the intended reflecting boundaries. Max|divB| values are5.59e−12/6.54e−12; boundary-normal fractions0.01182/0.01726; mass drifts1.34e−14/1.62e−14; energy drifts3.56e−6/7.96e−6. Minimum densities0.944/0.928 and pressures5.863/5.759 are far above1e−12 floors. Net conservation does not separately identify floor or energyFix corrections, which are unexported.

Full-domain bilinear null inventories cover all saved cell-center fields from initialization through the actual upper brackets. There is one X point and two O points in every 214/146 production frame. The final bracket fluxes are0.0500673/0.0500714. No extra resolved null pair appears. This qualifies saved-field topology, without certifying subcell, between-output or ghost-layer structures. The independent root reviewer reproduced this bounded assessment.

![S1000 fresh production fields](fields_S1000.png)

![S2000 fresh production fields](fields_S2000.png)

These full-domain Jz maps and magnetic-potential contours use nearest saved states at flux0.01,0.03,0.05. Crossing times use the prescribed interpolation. [figure_provenance.json](figure_provenance.json) identifies each source receipt, member, time, index and SHA256.

## Repair investigation and remaining scientific need

The measured profiles change substantially across the flux window. Independently defined half-amplitude width and upstream peak field vary with stage and resistivity. This makes stationary geometry questionable but does not establish the causal reason for the flatter slope. Strain, upstream supply, finite geometry and longitudinal evolution require a predictive closure and independent challenges.

The imported helper proposal used w=sigma², measured inward velocity strain a(psi), upstream peak B_u(psi), common initial w0 and

$$\dot w=-2a(\psi)w+2\eta,\qquad\dot\psi=\eta\sqrt{2/\pi}\,B_u(\psi)/\sqrt w.$$

Knots were fixed at flux0,0.01,0.03,0.05, with arithmetic anchor means and linear interpolation. Width was determined from the half-amplitude profile, not J. No rate coefficient was fitted. Its required calibration gate was duration error<= 5% on both anchors before validation. Recorded retained-field analysis exp_ed30761478eaae5229acd789 reproduces extraction and ODE integration from registered inputs:

|S_eta|Anchor R|Model R|Rate underprediction|Duration error|
|---|---:|---:|---:|---:|
|1000|0.049688584|0.037249353|25.03%|33.39%|
|2000|0.038242447|0.026457552|30.82%|44.54%|

This necessary replay gate fails, so that candidate stops before validation. Other proposed gates—complete omitted-EMF accounting and all closure uncertainties—remain unfinished; the report does not imply they passed. [conditional_calibration.json](conditional_calibration.json) records the failed replay, not an accepted scientific counterexample to a committed repair.

A local magnetic-slope/amplitude-budget extension checked without rate fitting in exp_7eb023a1353c625c137e6b4e also fails the fixed 5% duration-replay gate on one anchor. The alternative effective thinning coefficient inferred from observed width derivatives improves calibration but uses response-derived information; it is not measured strain and is nonzero initially despite zero initial flow. It cannot presently establish the mechanism or justify new validation. [amplitude_calibration.json](amplitude_calibration.json) and [effective_width_calibration.json](effective_width_calibration.json) preserve these exploratory diagnostics.

No new-resistivity FLASH validation cases were run for these proposals. ODE values at proposed settings are uncommitted planning calculations, not independent observations. No replacement exponent band, repaired physical law or completed mechanism is claimed. The smallest remaining scientific need is a closure that explains the width/amplitude budget, survives calibration without rate rescaling and makes a frozen prediction at a new setting, followed by qualified fresh simulations. No such supported repair exists here.

## Every fresh run and decision timeline

[run_table.json](run_table.json) contains all fresh receipts, including failed trajectories and analyses: S_eta/eta/mesh, arguments, timing, rate or explicit null reason, numerical checks, production slope intervals, fields and hashes, source/input/runtime identities, execution and scientific status. Analysis rows are not counted as independent MHD trajectories.

|Receipt|Kind/stage|S_eta / mesh|Execution|R or note|
|---|---|---|---|---|
|exp_2f42b96d98fb476429596b6c|trajectory/exploration|1000 / 128²|failed|undefined; see receipt|
|exp_a2d9039a3b1d3ba9ec78f86c|trajectory/exploration|250 / 128²|succeeded|0.08916469|
|exp_349433d01686c1d23c0186c8|trajectory/exploration|500 / 128²|succeeded|0.06512725|
|exp_ff929c68f5acb2eafb2f340b|trajectory/exploration|1000 / 128²|succeeded|0.04902521|
|exp_42cf28ee0c7c41a2f8d923be|trajectory/exploration|2000 / 128²|succeeded|0.03794595|
|exp_b2df128c1c1ecc1d990f7dc5|trajectory/exploration|4000 / 128²|succeeded|0.02890667|
|exp_c90e9b96ba8406a99246fb8e|trajectory/exploration|1000 / 192²|succeeded|0.04948176|
|exp_82b78fe2f19144b3b6ca29af|trajectory/exploration|2000 / 192²|succeeded|0.03815518|
|exp_f2da6ae1b2ce992ddf16cf82|trajectory/exploration|1000 / 256²|succeeded|0.04962642|
|exp_d72d5627834d2ca1456a280c|trajectory/exploration|2000 / 256²|succeeded|0.03813394|
|exp_aaef37fed668e2be86673215|trajectory/exploration|1000 / 256²|failed|undefined; see receipt|
|exp_0b86a9ee47886cb02451c2c2|trajectory/exploration|1000 / 256²|succeeded|0.04967105|
|exp_9a9dff759f89368261125a4b|trajectory/exploration|2000 / 256²|succeeded|0.03816129|
|exp_bc3989c6f90215ea0fc96df9|analysis/exploration|—|succeeded|postprocessing|
|exp_56eca6327dc2e3f0fd4942d4|trajectory/exploration|1000 / 384²|succeeded|0.04968858|
|exp_bcf499766e6d03faf83066d7|trajectory/exploration|2000 / 384²|failed|undefined; see receipt|
|exp_5705eedd35d71964238c0e87|analysis/exploration|—|succeeded|postprocessing|
|exp_9ed2782a9af6b2446c71285a|trajectory/exploration|2000 / 384²|succeeded|0.03824245|
|exp_cd08ebc4f1287d48388eddc6|analysis/exploration|—|succeeded|postprocessing|
|exp_c99f4a2aba5c70b7330e4ada|trajectory/exploration|1000 / 128²|succeeded|0.04903149|
|exp_58adb12d461c94104daeff23|trajectory/exploration|2000 / 512²|succeeded|0.03831751|
|exp_8adee806b81f5d005af5e201|analysis/exploration|—|succeeded|postprocessing|
|exp_755dffd11e2a3f05a6b86b49|trajectory/evidence|2000 / 384²|succeeded|0.03824213|
|exp_40aac93038caa57671014925|trajectory/evidence|1000 / 384²|succeeded|0.04968858|
|exp_ed30761478eaae5229acd789|analysis/exploration|—|succeeded|postprocessing|
|exp_7eb023a1353c625c137e6b4e|analysis/exploration|—|succeeded|postprocessing|

1. Exact anchor exp_2f42b96d98fb476429596b6c evolved successfully but its receipt failed because declared and actual summary paths differed. Its actual fresh output and failed receipt remain preserved; this is not physics evidence.
2. Recorded the prospective protocol, completed five exploratory settings and selected the declared contrast. The early256² interval missed the band by only0.001023, motivating further refinement.
3. Completed spatial/CFL/cadence controls. exp_aaef37fed668e2be86673215 lost its worker without terminal outputs; process inspection found no remaining solver before successful retries. This is an execution/reporting failure, not instability evidence.
4. Independent methods reviews required evolving-sheet and topology qualification. The original nominal-cadence selector omitted S1000's actual upper bracket; exp_5705eedd35d71964238c0e87 verifies that field and known3-/15-null controls. Corrected analysis uses actual crossing indices; earlier overstated coverage remains in the record.
5. Operator-authorized extension enabled384² controls. Concurrent S2000 launch exp_bcf499766e6d03faf83066d7 failed under a9.7MB residual reservation; sequential retry succeeded. No storage failure was treated as physics. The failed384² convergence gate was retained, followed by successful512² qualification.
6. Compact retention was commissioned with bitwise readback. Corrected source-bound method_661a2c5064ad92c6494cf179 approved the selected production contrast and conservative uncertainty transport.
7. Fresh production completed sequentially in773s and547s. Review_d8ed7a3364483fc612a029c3 accepted original falsification. This acceptance is independent of later repair success.
8. Recorded unsuccessful closure calibrations. No failed calibration was retuned into supported validation, and no exploratory artifact was promoted to hypothesis evidence.

## Reproducibility and retained artifacts

[calculation.py](calculation.py) uses [island_coalescence.py](island_coalescence.py) and [null_diagnostic.py](null_diagnostic.py). Every receipt preserves the exact source revision. Production driver SHA256 is `2b78c89dc7551f90848e8989d2c50c379e9d3428281858c9343d2b231ec71183`; executable SHA256 is `40cf57b987e85f9befc01abae4e89f27c230d1eb42391ba3abea8655a0f7024b`; capability-runtime SHA256 is `1dbefbee9b1ae4784d75f242e60d9cb64e12f95a30c2017d0a5b8e5b04e36d80`. Parameter hashes and complete launcher commands are in both production summaries and the run table. Four MPI ranks and OMP_NUM_THREADS=1 were used, within the 16-rank aggregate limit. No solver was modified or rebuilt.

Each compact trajectory retains every saved magx/magy array losslessly in magnetic_series.h5, with exact readback checked before duplicate removal. fields.tar.gz retains complete initial/final states and both brackets at flux0.01,0.03,0.05, plus parameters, logs and conservation history. Older full-field archives are immutable. fields[].retained_full_state and magnetic_series_index distinguish retained complete states from reduced-snapshot identities; hashes of removed full states are not presented as retrievable files.

Exact fresh production reruns use lab.run('calculation.py', ...) with inputs=['island_coalescence.py','null_diagnostic.py'], outputs=['result.json','fields.tar.gz','magnetic_series.h5'], capability='flash-island-coalescence-resistive-mhd-4.8', method='method_661a2c5064ad92c6494cf179', stage='evidence', and a new key:

|Case|args|timeout|
|---|---|---:|
|S1000|['--S','1000','--n','384','--tmax','1.15','--cadence','0.005']|1000s|
|S2000|['--S','2000','--n','384','--tmax','1.6','--cadence','0.01']|1300s|

Run sequentially after checking the required storage allowance. The method ID applies only to its recorded source/input/runtime binding and selected scope. Offline diagnostic sources and exact inputs are in their corresponding receipts. Source/build hashes establish identity, not correctness; numerical and independent reviews supply the separate qualification.

**Current disposition:** original band independently falsified; physical explanation and supported repair unfinished. No solver execution is active. The full investigation is not marked complete.
