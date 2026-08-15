# Claim summary

- status: `completed`
- iterations: 75
- open: claim_root
- closed: claim_confirm_seed_ensemble, claim_instr_simulator, claim_instr_analyzer

## Finish notes

- claim_root remains open at finish; child claims may still bound the root
- closed_claim_count=3
- open_claim_count=1

## Claims

| id | kind | relation | status | contracts | evidence | statement |
| --- | --- | --- | --- | ---: | ---: | --- |
| claim_root | scientific | root | open | 0 | 0 | In two-dimensional, non-relativistic, fully kinetic, collisionless electron-ion GEM-type Harris-sheet reconnection at... |
| claim_confirm_seed_ensemble | scientific | refines | falsified | 1 | 1 | In the fixed guided 2D fully kinetic Harris-sheet regime (Lx=25.6 di, Lz=12.8 di, nx=256, mass ratio 25, duration 12/... |
| claim_instr_simulator | instrument | instrument_of | supported | 2 | 1 | The frozen program guided/gem_collisionless.py executed through capability warpx-cuda-openpmd-26.07 realizes the full... |
| claim_instr_analyzer | instrument | instrument_of | supported | 1 | 1 | The frozen program analyze_ensemble.py executed through capability warpx-cpu-26.07 reads per-run guided simulator sum... |

## Details

### `claim_root`

Evidence contracts: (none)

Evidence: (none)

Closed reason: (open)

### `claim_confirm_seed_ensemble`

Evidence contracts: 1 (latest v1)
- observable: campaign/ensemble_result.json produced by the frozen analyzer: seed-ensemble mean late-window normalized flux-slope rates mu at Ti/Te=1 versus 20 for ppc=16 ...
- decision_rule: supported: decision.supported true in ensemble JSON, requiring valid_groups_R16, valid_groups_R8, R16_ge_125, R8_ge_125. falsified: decision.falsified true (...
- machine_validation_checks: 19

Evidence:
- `campaign/ensemble_result.json` (iter 70, contract v1, sufficient, validation passed, commissioned by claim_instr_analyzer, run_capability): Twelve fresh paired seed runs (3 seeds x Ti/Te 1 and 20 x ppc 16 and 8) plus the frozen analyzer: all runs passed 26/26 five-aspect checks and the exact-head...

Closed reason: The frozen analyzer's campaign/ensemble_result.json shows decision.falsified=true under the pre-registered rule: all four groups have 3 energy-valid runs (>=2 required), yet R16 = 1.0122389478936142 and R8 = 1.0857860945099447 are both below the 1.25 threshold. Per-seed ppc16 ratios were 0.823, 1...

### `claim_instr_simulator`

Evidence contracts: 2 (latest v2)
- observable: Fresh commissioning summary JSON written by guided/gem_collisionless.py under the corrected contract: all five-aspect checks true (26 leaves), CUDA backend r...
- decision_rule: Instrument supported iff the corrected commissioning run exits 0 and every registered check passes on the fresh commissioning summary JSON; otherwise close a...
- machine_validation_checks: 34
- commissioning_aspects: boundaries, diagnostics, numerical_regime, physics_controls, representation

Evidence:
- `campaign/commission_summary.json` (iter 54, contract v2, sufficient, validation passed, run_capability): Evidence-stage commissioning under the corrected v2 contract: guided/gem_collisionless.py via warpx-cuda-openpmd-26.07 completed 1156 explicit CUDA steps, wr...

Closed reason: The corrected evidence-stage commissioning of guided/gem_collisionless.py under warpx-cuda-openpmd-26.07 exited 0, wrote 14 readable openPMD HDF5 field states plus reduced FieldEnergy/ParticleEnergy files, and passed all 26 machine-checked five-aspect validation assertions (representation, physic...

### `claim_instr_analyzer`

Evidence contracts: 1 (latest v1)
- observable: Commissioning/JSON output of analyze_ensemble.py on the 12 deterministic fixture runs: per-run OLS late-window mu equals fixture truth (0.15/0.05) to <=1e-6 ...
- decision_rule: Instrument supported iff commissioning exits 0 and every registered check is satisfied on the commissioning JSON; otherwise close as instrument_limited/unres...
- machine_validation_checks: 23
- commissioning_aspects: boundaries, diagnostics, numerical_regime, physics_controls, representation

Evidence:
- `fixtures/commission_output.json` (iter 47, contract v1, sufficient, validation passed, run_capability): Evidence-stage commissioning run of analyze_ensemble.py under warpx-cpu-26.07 on the 12 deterministic fixture manifests satisfied every registered validation...

Closed reason: The commissioning run of analyze_ensemble.py under warpx-cpu-26.07 on 12 deterministic fixture runs exited 0 and satisfied every registered machine-checked validation assertion: exact OLS mu recovery (relative error 5.6e-16 <= 1e-6), exact-header energy total selection, aligned energy rows, energ...

