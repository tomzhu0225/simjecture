# Study results

In a prospectively selected, numerically resolved current-sheet region of the supplied two-dimensional FLASH island-coalescence model, a collisionless electron-ion kinetic continuation at ion-scale sheet width remains adequately represented by isotropic species pressures: the time- and area-averaged departure A_s = ||P_s - tr(P_s)I/3||_F / (sqrt(3) tr(P_s)/3) is no greater than 0.20 for both ions and electrons in an independently qualified interior measurement region, after the initialization transient and over a window lasting at least half an inverse reference ion cyclotron frequency. A spatially resolved MHD sheet is thus sufficient for this particular local isotropic-pressure prediction.

Use a reduced ion/electron mass ratio of 25 and initially equal ion/electron scalar temperatures, with a nonrelativistic dimensional mapping of the normalized MHD state. Select the source state, region, physical scale, observation window and numerical decision rule prospectively, before decisive kinetic evidence. Target measured sheet half-width / ion skin depth between 0.5 and 2, and state its exact definition. The finite realization and its conditioning assumptions must be explicit. This tests local kinetic pressure behavior, not a universal reconnection rate, global two-way MHD-PIC accuracy, or a radiation claim. A transfer transient, underresolved/noisy pressure diagnostic or boundary-contaminated signal is not a scientific counterexample.


Execution: budget_exhausted. Scientific status: unresolved.

- [Scientific narrative](research/RESULTS.md)
- [Evidence ledger](STUDY_LEDGER.md)
- [Machine-readable report](research_report.json)

Report assessment: unreviewed.

## 001 · guided-anchor

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_eef180c184d79e03a3485285/workspace/)
- [guided/flash_anchor_validation.json](experiments/exp_eef180c184d79e03a3485285/workspace/guided/flash_anchor_validation.json)
- [Receipt](experiments/exp_eef180c184d79e03a3485285.json)

## 002 · continuation-fine32

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_a1842d496f9ccf18d93f7647/workspace/)
- [kinetic/result.json](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/result.json)
- [kinetic/history.json](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/history.json)
- [kinetic/moments.npz](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/moments.npz)
- [kinetic/initial_fields.npz](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/initial_fields.npz)
- [kinetic/final_fields.npz](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/final_fields.npz)
- [kinetic/reduced/field_energy.txt](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/reduced/field_energy.txt)
- [kinetic/reduced/particle_energy.txt](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/reduced/particle_energy.txt)
- [kinetic/warpx_used_inputs](experiments/exp_a1842d496f9ccf18d93f7647/workspace/kinetic/warpx_used_inputs)
- [Receipt](experiments/exp_a1842d496f9ccf18d93f7647.json)

## 003 · continuation-historical-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/)
- [analysis.json](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/pressure_controls.png)
- [fine_kinetic_fields.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/fine_kinetic_fields.png)
- [fine_pressure_tensor.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/fine_pressure_tensor.png)
- [bigfine_kinetic_fields.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/bigfine_kinetic_fields.png)
- [bigfine_pressure_tensor.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/bigfine_pressure_tensor.png)
- [timestep_kinetic_fields.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/timestep_kinetic_fields.png)
- [timestep_pressure_tensor.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/timestep_pressure_tensor.png)
- [particles_kinetic_fields.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/particles_kinetic_fields.png)
- [particles_pressure_tensor.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/particles_pressure_tensor.png)
- [base_kinetic_fields.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/base_kinetic_fields.png)
- [base_pressure_tensor.png](experiments/exp_4b404fe3e1562cfb62f5daee/workspace/base_pressure_tensor.png)
- [Receipt](experiments/exp_4b404fe3e1562cfb62f5daee.json)

## 004 · complete-qualification

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_2170ea427cd8f5af2df39f06/workspace/)
- [analysis.json](experiments/exp_2170ea427cd8f5af2df39f06/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/pressure_controls.png)
- [fine_kinetic_fields.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/fine_kinetic_fields.png)
- [fine_pressure_tensor.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/fine_pressure_tensor.png)
- [bigfine_kinetic_fields.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/bigfine_kinetic_fields.png)
- [bigfine_pressure_tensor.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/bigfine_pressure_tensor.png)
- [timestep_kinetic_fields.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/timestep_kinetic_fields.png)
- [timestep_pressure_tensor.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/timestep_pressure_tensor.png)
- [particles_kinetic_fields.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/particles_kinetic_fields.png)
- [particles_pressure_tensor.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/particles_pressure_tensor.png)
- [base_kinetic_fields.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/base_kinetic_fields.png)
- [base_pressure_tensor.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/base_pressure_tensor.png)
- [source_qualification.json](experiments/exp_2170ea427cd8f5af2df39f06/workspace/source_qualification.json)
- [macro_patch.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/macro_patch.png)
- [fine32_kinetic_fields.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/fine32_kinetic_fields.png)
- [fine32_pressure_tensor.png](experiments/exp_2170ea427cd8f5af2df39f06/workspace/fine32_pressure_tensor.png)
- [Receipt](experiments/exp_2170ea427cd8f5af2df39f06.json)

## 005 · current-report-assessment-package

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_e441d15856a4cb51f299ec82/workspace/)
- [report_snapshot.json](experiments/exp_e441d15856a4cb51f299ec82/workspace/report_snapshot.json)
- [review_report.md](experiments/exp_e441d15856a4cb51f299ec82/workspace/review_report.md)
- [Receipt](experiments/exp_e441d15856a4cb51f299ec82.json)
