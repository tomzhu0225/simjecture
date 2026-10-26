# Study results

In a prospectively selected, numerically resolved current-sheet region of the supplied two-dimensional FLASH island-coalescence model, a collisionless electron-ion kinetic continuation at ion-scale sheet width remains adequately represented by isotropic species pressures: the time- and area-averaged departure A_s = ||P_s - tr(P_s)I/3||_F / (sqrt(3) tr(P_s)/3) is no greater than 0.20 for both ions and electrons in an independently qualified interior measurement region, after the initialization transient and over a window lasting at least half an inverse reference ion cyclotron frequency. A spatially resolved MHD sheet is thus sufficient for this particular local isotropic-pressure prediction.

Use a reduced ion/electron mass ratio of 25 and initially equal ion/electron scalar temperatures, with a nonrelativistic dimensional mapping of the normalized MHD state. Select the source state, region, physical scale, observation window and numerical decision rule prospectively, before decisive kinetic evidence. Target measured sheet half-width / ion skin depth between 0.5 and 2, and state its exact definition. The finite realization and its conditioning assumptions must be explicit. This tests local kinetic pressure behavior, not a universal reconnection rate, global two-way MHD-PIC accuracy, or a radiation claim. A transfer transient, underresolved/noisy pressure diagnostic or boundary-contaminated signal is not a scientific counterexample.


Execution: budget_exhausted. Scientific status: accepted.

- [Scientific narrative](research/RESULTS.md)
- [Evidence ledger](STUDY_LEDGER.md)
- [Machine-readable report](research_report.json)

Report assessment: unreviewed.

## 001 · guided-anchor

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_7dec20d7e3686d5778312433/workspace/)
- [assets/flash_runtime_validation.json](experiments/exp_7dec20d7e3686d5778312433/workspace/assets/flash_runtime_validation.json)
- [Receipt](experiments/exp_7dec20d7e3686d5778312433.json)

## 002 · fresh-macro256

Execution: failed.

- [Input snapshot and working files](experiments/exp_e10f88b8220dd98c85fd82ce/workspace/)
- [result.json](experiments/exp_e10f88b8220dd98c85fd82ce/workspace/result.json)
- [flash](experiments/exp_e10f88b8220dd98c85fd82ce/workspace/flash)
- [Receipt](experiments/exp_e10f88b8220dd98c85fd82ce.json)

## 003 · transfer256

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/)
- [result.json](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/result.json)
- [patch.npz](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/patch.npz)
- [patch.json](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/patch.json)
- [state.npz](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/state.npz)
- [state.json](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/state.json)
- [macro_patch.png](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/macro_patch.png)
- [source_profiles.npz](experiments/exp_1eac2c3c7e37fc758699b05d/workspace/source_profiles.npz)
- [Receipt](experiments/exp_1eac2c3c7e37fc758699b05d.json)

## 004 · fresh-macro512

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_f195949ab1410375cc7b8f44/workspace/)
- [result.json](experiments/exp_f195949ab1410375cc7b8f44/workspace/result.json)
- [flash/flash.par](experiments/exp_f195949ab1410375cc7b8f44/workspace/flash/flash.par)
- [flash/flash_run_hdf5_plt_cnt_0008](experiments/exp_f195949ab1410375cc7b8f44/workspace/flash/flash_run_hdf5_plt_cnt_0008)
- [flash/flash_run.dat](experiments/exp_f195949ab1410375cc7b8f44/workspace/flash/flash_run.dat)
- [flash/flash_run.log](experiments/exp_f195949ab1410375cc7b8f44/workspace/flash/flash_run.log)
- [Receipt](experiments/exp_f195949ab1410375cc7b8f44.json)

## 005 · fullwindow-pilot256

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/)
- [pic/result.json](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_6c9d4f3c7099c6a625d2951f/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_6c9d4f3c7099c6a625d2951f.json)

## 006 · pilot-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_2514c47e5069f2252e5d3d87/workspace/)
- [analysis.json](experiments/exp_2514c47e5069f2252e5d3d87/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_2514c47e5069f2252e5d3d87/workspace/pressure_controls.png)
- [pilot_kinetic_fields.png](experiments/exp_2514c47e5069f2252e5d3d87/workspace/pilot_kinetic_fields.png)
- [pilot_pressure_tensor.png](experiments/exp_2514c47e5069f2252e5d3d87/workspace/pilot_pressure_tensor.png)
- [Receipt](experiments/exp_2514c47e5069f2252e5d3d87.json)

## 007 · transfer256-large

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_db2d8064125c1b7179351500/workspace/)
- [result.json](experiments/exp_db2d8064125c1b7179351500/workspace/result.json)
- [large_patch.npz](experiments/exp_db2d8064125c1b7179351500/workspace/large_patch.npz)
- [large_patch.json](experiments/exp_db2d8064125c1b7179351500/workspace/large_patch.json)
- [state.npz](experiments/exp_db2d8064125c1b7179351500/workspace/state.npz)
- [state.json](experiments/exp_db2d8064125c1b7179351500/workspace/state.json)
- [macro_patch.png](experiments/exp_db2d8064125c1b7179351500/workspace/macro_patch.png)
- [source_profiles.npz](experiments/exp_db2d8064125c1b7179351500/workspace/source_profiles.npz)
- [Receipt](experiments/exp_db2d8064125c1b7179351500.json)

## 008 · boundary-large256

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_955fb2e24e33451caf514008/workspace/)
- [pic/result.json](experiments/exp_955fb2e24e33451caf514008/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_955fb2e24e33451caf514008/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_955fb2e24e33451caf514008/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_955fb2e24e33451caf514008/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_955fb2e24e33451caf514008/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_955fb2e24e33451caf514008/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_955fb2e24e33451caf514008/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_955fb2e24e33451caf514008/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_955fb2e24e33451caf514008.json)

## 009 · transfer512

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_17156d52044aff8a375a62f6/workspace/)
- [result.json](experiments/exp_17156d52044aff8a375a62f6/workspace/result.json)
- [patch.npz](experiments/exp_17156d52044aff8a375a62f6/workspace/patch.npz)
- [patch.json](experiments/exp_17156d52044aff8a375a62f6/workspace/patch.json)
- [state.npz](experiments/exp_17156d52044aff8a375a62f6/workspace/state.npz)
- [state.json](experiments/exp_17156d52044aff8a375a62f6/workspace/state.json)
- [macro_patch.png](experiments/exp_17156d52044aff8a375a62f6/workspace/macro_patch.png)
- [source_profiles.npz](experiments/exp_17156d52044aff8a375a62f6/workspace/source_profiles.npz)
- [Receipt](experiments/exp_17156d52044aff8a375a62f6.json)

## 010 · macro-source-refinement

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_2f9bf7deff8148a543a2c4f3/workspace/)
- [macro_comparison.json](experiments/exp_2f9bf7deff8148a543a2c4f3/workspace/macro_comparison.json)
- [Receipt](experiments/exp_2f9bf7deff8148a543a2c4f3.json)

## 011 · refined-source-baseline

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/)
- [pic/result.json](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_0cc759f4429f9587ef9f4c55/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_0cc759f4429f9587ef9f4c55.json)

## 012 · boundary-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_dd8c15b208658c27f2d762ad/workspace/)
- [analysis.json](experiments/exp_dd8c15b208658c27f2d762ad/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_dd8c15b208658c27f2d762ad/workspace/pressure_controls.png)
- [pilot_kinetic_fields.png](experiments/exp_dd8c15b208658c27f2d762ad/workspace/pilot_kinetic_fields.png)
- [pilot_pressure_tensor.png](experiments/exp_dd8c15b208658c27f2d762ad/workspace/pilot_pressure_tensor.png)
- [large_kinetic_fields.png](experiments/exp_dd8c15b208658c27f2d762ad/workspace/large_kinetic_fields.png)
- [large_pressure_tensor.png](experiments/exp_dd8c15b208658c27f2d762ad/workspace/large_pressure_tensor.png)
- [Receipt](experiments/exp_dd8c15b208658c27f2d762ad.json)

## 013 · mesh768-refined-source

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_af3f8c4f97f31b360a115b36/workspace/)
- [pic/result.json](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_af3f8c4f97f31b360a115b36/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_af3f8c4f97f31b360a115b36.json)

## 014 · refined-source-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_b6a2adccb584b91734873c8d/workspace/)
- [analysis.json](experiments/exp_b6a2adccb584b91734873c8d/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_b6a2adccb584b91734873c8d/workspace/pressure_controls.png)
- [pilot_kinetic_fields.png](experiments/exp_b6a2adccb584b91734873c8d/workspace/pilot_kinetic_fields.png)
- [pilot_pressure_tensor.png](experiments/exp_b6a2adccb584b91734873c8d/workspace/pilot_pressure_tensor.png)
- [refined_kinetic_fields.png](experiments/exp_b6a2adccb584b91734873c8d/workspace/refined_kinetic_fields.png)
- [refined_pressure_tensor.png](experiments/exp_b6a2adccb584b91734873c8d/workspace/refined_pressure_tensor.png)
- [Receipt](experiments/exp_b6a2adccb584b91734873c8d.json)

## 015 · integrated-handoff-validation

Execution: failed.

- [Input snapshot and working files](experiments/exp_0acc6f24de20923ef83122b7/workspace/)
- [macro.json](experiments/exp_0acc6f24de20923ef83122b7/workspace/macro.json)
- [result.json](experiments/exp_0acc6f24de20923ef83122b7/workspace/result.json)
- [patch.npz](experiments/exp_0acc6f24de20923ef83122b7/workspace/patch.npz)
- [patch.json](experiments/exp_0acc6f24de20923ef83122b7/workspace/patch.json)
- [state.npz](experiments/exp_0acc6f24de20923ef83122b7/workspace/state.npz)
- [state.json](experiments/exp_0acc6f24de20923ef83122b7/workspace/state.json)
- [flash/flash_run_hdf5_plt_cnt_0008](experiments/exp_0acc6f24de20923ef83122b7/workspace/flash/flash_run_hdf5_plt_cnt_0008)
- [macro_patch.png](experiments/exp_0acc6f24de20923ef83122b7/workspace/macro_patch.png)
- [Receipt](experiments/exp_0acc6f24de20923ef83122b7.json)

## 016 · integrated-handoff-noplot-validation

Execution: failed.

- [Input snapshot and working files](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/)
- [macro.json](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/macro.json)
- [result.json](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/result.json)
- [patch.npz](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/patch.npz)
- [patch.json](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/patch.json)
- [state.npz](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/state.npz)
- [state.json](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/state.json)
- [flash/flash_run_hdf5_plt_cnt_0008](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/flash/flash_run_hdf5_plt_cnt_0008)
- [source_profiles.npz](experiments/exp_f8a71b3d31c7baa5dc5bc97a/workspace/source_profiles.npz)
- [Receipt](experiments/exp_f8a71b3d31c7baa5dc5bc97a.json)

## 017 · integrated-handoff-current-validation

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_635537f1043786f7af0bd65e/workspace/)
- [macro.json](experiments/exp_635537f1043786f7af0bd65e/workspace/macro.json)
- [result.json](experiments/exp_635537f1043786f7af0bd65e/workspace/result.json)
- [patch.npz](experiments/exp_635537f1043786f7af0bd65e/workspace/patch.npz)
- [patch.json](experiments/exp_635537f1043786f7af0bd65e/workspace/patch.json)
- [state.npz](experiments/exp_635537f1043786f7af0bd65e/workspace/state.npz)
- [state.json](experiments/exp_635537f1043786f7af0bd65e/workspace/state.json)
- [flash/flash_run_hdf5_plt_cnt_0008](experiments/exp_635537f1043786f7af0bd65e/workspace/flash/flash_run_hdf5_plt_cnt_0008)
- [source_profiles.npz](experiments/exp_635537f1043786f7af0bd65e/workspace/source_profiles.npz)
- [Receipt](experiments/exp_635537f1043786f7af0bd65e.json)

## 018 · timestep-half

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_a3feea9cfd7050363e077857/workspace/)
- [pic/result.json](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_a3feea9cfd7050363e077857/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_a3feea9cfd7050363e077857.json)

## 019 · corrected-bin-audit-all

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_3e16729b5240dd577dbe960d/workspace/)
- [analysis.json](experiments/exp_3e16729b5240dd577dbe960d/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/pressure_controls.png)
- [pilot_kinetic_fields.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/pilot_kinetic_fields.png)
- [pilot_pressure_tensor.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/pilot_pressure_tensor.png)
- [large_kinetic_fields.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/large_kinetic_fields.png)
- [large_pressure_tensor.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/large_pressure_tensor.png)
- [refined_kinetic_fields.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/refined_kinetic_fields.png)
- [refined_pressure_tensor.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/refined_pressure_tensor.png)
- [mesh_kinetic_fields.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/mesh_kinetic_fields.png)
- [mesh_pressure_tensor.png](experiments/exp_3e16729b5240dd577dbe960d/workspace/mesh_pressure_tensor.png)
- [Receipt](experiments/exp_3e16729b5240dd577dbe960d.json)

## 020 · particle64

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/)
- [pic/result.json](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_598cf8a2dc75dceade0c52c4/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_598cf8a2dc75dceade0c52c4.json)

## 021 · fresh-evidence-macro512

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_7772fa68048aff22c2b815c3/workspace/)
- [macro.json](experiments/exp_7772fa68048aff22c2b815c3/workspace/macro.json)
- [result.json](experiments/exp_7772fa68048aff22c2b815c3/workspace/result.json)
- [patch.npz](experiments/exp_7772fa68048aff22c2b815c3/workspace/patch.npz)
- [patch.json](experiments/exp_7772fa68048aff22c2b815c3/workspace/patch.json)
- [state.npz](experiments/exp_7772fa68048aff22c2b815c3/workspace/state.npz)
- [state.json](experiments/exp_7772fa68048aff22c2b815c3/workspace/state.json)
- [flash/flash_run_hdf5_plt_cnt_0008](experiments/exp_7772fa68048aff22c2b815c3/workspace/flash/flash_run_hdf5_plt_cnt_0008)
- [source_profiles.npz](experiments/exp_7772fa68048aff22c2b815c3/workspace/source_profiles.npz)
- [flash/flash.par](experiments/exp_7772fa68048aff22c2b815c3/workspace/flash/flash.par)
- [flash/flash_run.dat](experiments/exp_7772fa68048aff22c2b815c3/workspace/flash/flash_run.dat)
- [flash/flash_run.log](experiments/exp_7772fa68048aff22c2b815c3/workspace/flash/flash_run.log)
- [Receipt](experiments/exp_7772fa68048aff22c2b815c3.json)

## 022 · refined-source-boundary-large

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_4b72bb874b27665a7cc11322/workspace/)
- [pic/result.json](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_4b72bb874b27665a7cc11322/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_4b72bb874b27665a7cc11322.json)

## 023 · remaining-controls-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/)
- [analysis.json](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/pressure_controls.png)
- [refined_kinetic_fields.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/refined_kinetic_fields.png)
- [refined_pressure_tensor.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/refined_pressure_tensor.png)
- [time_kinetic_fields.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/time_kinetic_fields.png)
- [time_pressure_tensor.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/time_pressure_tensor.png)
- [ppc_kinetic_fields.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/ppc_kinetic_fields.png)
- [ppc_pressure_tensor.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/ppc_pressure_tensor.png)
- [boundary_kinetic_fields.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/boundary_kinetic_fields.png)
- [boundary_pressure_tensor.png](experiments/exp_6cdf470bcffa5a00adfd8755/workspace/boundary_pressure_tensor.png)
- [Receipt](experiments/exp_6cdf470bcffa5a00adfd8755.json)

## 024 · staggered-field-control-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_0ae55871794048fcb4bea710/workspace/)
- [field_audit.json](experiments/exp_0ae55871794048fcb4bea710/workspace/field_audit.json)
- [Receipt](experiments/exp_0ae55871794048fcb4bea710.json)

## 025 · evidence-seed6101

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/)
- [pic/result.json](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_8e19bd425cb2bd2ef03a61ea/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_8e19bd425cb2bd2ef03a61ea.json)

## 026 · evidence-seed6102

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_882ac26f8158ec6e67fd8372/workspace/)
- [pic/result.json](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/result.json)
- [pic/moments.npz](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/moments.npz)
- [pic/history.json](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/history.json)
- [pic/initial_fields.npz](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/initial_fields.npz)
- [pic/final_fields.npz](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/final_fields.npz)
- [pic/reduced/field_energy.txt](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/reduced/field_energy.txt)
- [pic/reduced/particle_energy.txt](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/reduced/particle_energy.txt)
- [pic/warpx_used_inputs](experiments/exp_882ac26f8158ec6e67fd8372/workspace/pic/warpx_used_inputs)
- [Receipt](experiments/exp_882ac26f8158ec6e67fd8372.json)

## 027 · fresh-seed6101-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_e5666cef28e28a096181c145/workspace/)
- [analysis.json](experiments/exp_e5666cef28e28a096181c145/workspace/analysis.json)
- [pressure_controls.png](experiments/exp_e5666cef28e28a096181c145/workspace/pressure_controls.png)
- [seed6101_kinetic_fields.png](experiments/exp_e5666cef28e28a096181c145/workspace/seed6101_kinetic_fields.png)
- [seed6101_pressure_tensor.png](experiments/exp_e5666cef28e28a096181c145/workspace/seed6101_pressure_tensor.png)
- [Receipt](experiments/exp_e5666cef28e28a096181c145.json)

## 028 · fresh-seeds-final-audit

Execution: succeeded.

- [Input snapshot and working files](experiments/exp_cef42c711fc9dc4c8638c440/workspace/)
- [analysis.json](experiments/exp_cef42c711fc9dc4c8638c440/workspace/analysis.json)
- [decision.json](experiments/exp_cef42c711fc9dc4c8638c440/workspace/decision.json)
- [pressure_controls.png](experiments/exp_cef42c711fc9dc4c8638c440/workspace/pressure_controls.png)
- [seed6101_kinetic_fields.png](experiments/exp_cef42c711fc9dc4c8638c440/workspace/seed6101_kinetic_fields.png)
- [seed6101_pressure_tensor.png](experiments/exp_cef42c711fc9dc4c8638c440/workspace/seed6101_pressure_tensor.png)
- [seed6102_kinetic_fields.png](experiments/exp_cef42c711fc9dc4c8638c440/workspace/seed6102_kinetic_fields.png)
- [seed6102_pressure_tensor.png](experiments/exp_cef42c711fc9dc4c8638c440/workspace/seed6102_pressure_tensor.png)
- [Receipt](experiments/exp_cef42c711fc9dc4c8638c440.json)
