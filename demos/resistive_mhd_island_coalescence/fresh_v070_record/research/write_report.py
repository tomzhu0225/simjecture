"""Current scientific synthesis from immutable fresh receipts and recorded analyses."""
from pathlib import Path
import json,math
records=[json.loads(p.read_text()) for p in Path('../experiments').glob('exp_*.json')];measurements=[]
for rec in records:
 p=Path('../experiments')/rec['id']/'workspace/result.json'
 if p.exists():
  r=json.loads(p.read_text())
  if 'config' in r:measurements.append((rec,r))
measurements.sort(key=lambda v:(v[1]['config']['S_eta'],v[1]['config']['n'],v[1]['config']['cfl'],v[0]['created_at']))
q=json.loads(Path('spatial_qualification.json').read_text());rows=[]
for rec,r in measurements:
 c=r['config'];rows.append(f"|{rec['id']}|{c['S_eta']:g}|{c['eta']:g}|{c['n']}²|{c['cfl']:g}|{c['cadence']:g}|{r['metrics']['normalized_flux_slope']:.9f}|{rec.get('execution',{}).get('wall_seconds',0):.1f}|")
cad=[]
for rec,r in measurements:
 c=r['config'];R=r['metrics']['normalized_flux_slope'];rs=r.get('rate_stride_2')
 if c['cadence']==.005 and c['cfl']==.4 and c['n']>=192 and rs is not None:cad.append({'experiment':rec['id'],'S_eta':c['S_eta'],'n':c['n'],'fine_rate':R,'stride2_rate':rs,'relative_difference':abs(rs/R-1)})
Path('cadence_comparison.json').write_text(json.dumps(cad,indent=2)+'\n')
active=[r for r in records if r['status'] in ['queued','running']];failed=[r for r in records if r['status']=='failed']
head='''# Fresh island-coalescence scaling investigation

The fresh exploratory map shows reconnection-rate slopes flatter than the proposed band over several adjacent contrasts. The selected contrast S_eta=1000→2000 has slope -0.37774 on384², with an empirical deterministic interval[-0.41409,-0.34136]. This is **not a qualified counterexample**: the S2000 shrinking-mesh-change gate fails at384², method_661a2c5064ad92c6494cf179 approves fresh evidence collection for the selected contrast. The first production case is running; no accepted root verdict exists.

The current scientific judgment is that the original band is doubtful for this finite-window, compressible coalescence observable, while remaining unresolved. The calculation does not test a common global power law or a random-exponent distribution. Neither the methods refusal nor failed execution controls establish a physical verdict.

The five-setting128² map gives rates0.0891647,0.0651272,0.0490252,0.0379460,0.0289067 at nominal S_eta=250,500,1000,2000,4000. Adjacent slopes are-0.4532,-0.4097,-0.3696,-0.3925. The selection of1000→2000 followed the prospectively recorded largest adjacent departure rule. Both selected cases reached the same flux window at128²,192²,256² and384². The latest384² rates are0.049688584 and0.038242447.

## What qualification establishes and leaves open

Recorded analysis exp_cd08ebc4f1287d48388eddc6 verifies original raw crossing-bracket HDF5 hashes and bitwise equality of magnetic arrays against the lossless magnetic series. It compares profiles at matched reconnected flux0.01,0.03,0.05, rather than at unequal physical stages. At384², full-domain bilinear null inventories through the actual upper crossing bracket contain one X point and two O points in every analyzed frame:214 frames forS1000 and291 forS2000. No resolved additional null pair appears. This does not certify subcell, between-output or ghost-layer structures.

S1000 relative rate changes shrink from0.2915% (192→256) to0.1251% (256→384). S2000 changes grow from0.0557% to0.2837%, violating the recorded shrinking-change gate. The failed gate is retained; it is not waived because the absolute changes are small. The targeted512² S2000 control completed: rate0.038317512, next relative change0.1959%, passing the unchanged shrinking-change gate. Its minimum halfwidth is5.44cells. Record exp_58adb12d461c94104daeff23 took2075.01s. Minimum reported evolving sheet halfwidth increases to5.80cells (S1000) and4.13cells (S2000) at384². At matched flux, S2000 central-current differences from256 to384 are2.14–3.24%, compared with3.06–3.78% from192 to256; full-profile relative L2 differences similarly decrease. Local profiles remain more sensitive than the integral rate.

Both complete-window256² CFL0.2 controls completed: exp_0b86a9ee47886cb02451c2c2 and exp_9a9dff759f89368261125a4b. Relative rate changes fromCFL0.4 are0.0899% and0.0717%. The present384² envelope transfers that measured same-grid256² timestep contribution; independent review must assess its scope. Divergence, boundary and net-conservation diagnostics are small; they do not individually measure floor or energyFix corrections.

Compact-output commissioning exp_c99f4a2aba5c70b7330e4ada completed actual full-window evolution and read back every one of261 saved magnetic frames bitwise equal before removing duplicate full-state files. Complete initial/final states and both actual brackets atflux0.01,0.03,0.05 are retained. Later runs store all saved magnetic arrays in magnetic_series.h5 and representative complete states infields.tar.gz. Earlier full-field archives remain immutable. No solver implementation or physical inputs were changed.

## Prospective model, measurement and decision rule

The supplied FLASH4.8 application evolves normalized2D compressible single-fluid resistive MHD, with uniform eta, alpha20, temperature3, pressure offset6, gamma5/3 and reflecting boundaries on[-0.5,0.5]². S_eta=1/eta is nominal inverse diffusivity, not a dimensional Lundquist number. The same initial-state-subtracted supplied By-path center flux is used throughout. First crossings are interpolated linearly in actual saved time; R=0.04/(t_0.05-t_0.01).

Before the map, note_29642e7a3142dea6e9d7b988 fixed the reducer, five settings, contrast-selection rule, admissibility and deterministic uncertainty. For each finest rate, u=max[0.01,2 max(successive relative changes over the last three meshes)+full crossing-bracket relative deviation+orthogonal Bx-path rate difference+measured CFL difference]. Require the last mesh change<=5% and smaller than its predecessor, u<=15%, completed crossings, positive finite rho andp>100floors, correct runtime controls, max|divB|<1e-9, boundary-normal fraction<0.05, mass drift<1e-6, energy drift<1%, and single-sheet/pre-plasmoid topology.

For rate intervals[Ra-,Ra+] and[Rb-,Rb+], propagate p- = ln(Rb-/Ra+)/ln(Sb/Sa) and p+ = ln(Rb+/Ra-)/ln(Sb/Sa). A qualified interval wholly outside[-0.55,-0.45] falsifies the root. An overlapping interval cannot falsify it. The empirical numerical envelope is not a statistical confidence interval or a rigorous continuum enclosure. Mesh samples are deterministic.

|S_eta|Meshes|Mesh term|Cadence term|Path term|CFL term|u|Mesh gate|
|---|---|---:|---:|---:|---:|---:|---|
'''
for u in q['uncertainty']:
 t=u['terms'];head+=f"|{u['S_eta']}|{u['meshes']}|{t['mesh']:.8f}|{t['cadence']:.8f}|{t['path']:.8f}|{t['CFL']:.8f}|{u['u']:.8f}|{u['mesh_gate']}|\n"
head+='''
The complete numerical terms and matched profiles are in spatial_qualification.json, generated by the recorded analysis. The earlier256² exploratory interval[-0.448977,-0.310154] missed the root band by only0.001023, motivating finer qualification. It is superseded for current interpretation by the384² assessment and its explicitly failed spatial gate.

## Cadence check

The existing0.005-cadence trajectories were reduced with every second sample while always preserving their last endpoint. This checks output sampling alone, without changing physical evolution. It is distinct from adaptive-timestep convergence. Exact per-case values are in cadence_comparison.json; the original rate_stride_2 fields are preserved in the corresponding immutable result.json receipts.

|S_eta|Mesh|Relative rate difference:0.005 vs strided≈0.01|
|---|---:|---:|
'''
for c in cad:head+=f"|{c['S_eta']:g}|{c['n']}|{c['relative_difference']:.8g}|\n"
head+='''
Actual output times need not land exactly on nominal cadence. The512² control uses0.01 output cadence for storage fit and includes its own full crossing-bracket bound; its spatial changes must be interpreted alongside these cadence checks.

## Fresh trajectory table

Rows are labelled by their actual stage in run_table.json; production cases require method approval and independent scientific review. A successful process or self-reported check is not scientific approval. `run_table.json` includes every fresh receipt, including diagnostic/failed executions, exact source/input/runtime/build identities, configuration, timing, rate, numerical checks, slope intervals and field paths/hashes.

|Experiment|S_eta|eta|Mesh|CFL|Cadence|R|Wall seconds|
|---|---:|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(rows)+'\n\n'
head+='## Current execution status\n\n'
for r in active:head+=f"- {r['id']}: {r['status']}, arguments `{r['binding']['args']}`.\n"
if not active:head+='No experiment currently active.\n'
head+='''
## Decision timeline and informative failed controls

1. Exact anchor exp_2f42b96d98fb476429596b6c evolved successfully and reached both thresholds, but its receipt failed because its declared output path differed from the actual summary path. Preserve the failed receipt and actual summary; this was an output-declaration failure.
2. Prospective protocol recorded before the five fresh128² settings. The selected1000→2000 contrast follows that rule; no global exponent was imposed.
3. Complete192² and256² spatial controls and finer output cadence. The first256² CFL0.2 attempt exp_aaef37fed668e2be86673215 lost its worker without terminal outputs. Process inspection found no remaining solver before two successful retries. This is an execution/reporting failure, not solver instability evidence.
4. Methods reviews method_cf2dda08b06de67032c4f290 and method_4e91240e074e8dcad20103cb returned revise, requiring complete CFL results, evolving-sheet qualification and correct full-window topology.
5. Review found the original topology selector omitted the S1000 upper-bracket field by relying on nominal cadence. exp_5705eedd35d71964238c0e87 hash-verifies that field at time1.070330826, finds the expected1X2O topology, and tests synthetic3-null and15-null controls. The corrected selector uses actual first-crossing indices.
6. Operator-authorized extension enabled384² refinement. S1000 exp_56eca6327dc2e3f0fd4942d4 completed in681.52s. The concurrent S2000 launch exp_bcf499766e6d03faf83066d7 failed immediately with workspace_exceeded under a9,677,488-byte residual reservation. It is a storage-allocation failure. Sequential S2000 exp_9ed2782a9af6b2446c71285a completed in977.04s under3.516GB allowance.
7. Corrected matched-flux/topology analysis exp_cd08ebc4f1287d48388eddc6 records the failed S2000 shrinking-change gate. Compact retention commissioning passed. Targeted512² qualification completed under the unchanged gate, cadence0.01 and a verified1.867GB reservation. Final arithmetic exp_8adee806b81f5d005af5e201 gives fine u1.9826% and approved transported384 allowance~2.18%, before fresh adjustments. Method_661a2c5064ad92c6494cf179 approves selected-contrast evidence collection only.

## Artifacts, identity and rerun

- `calculation.py` and inputs `island_coalescence.py`, `null_diagnostic.py` define the current driver. Immutable receipts preserve each actual source revision. No FLASH source or executable was modified.
- Every successful trajectory records the exact executable SHA256, generated parameter-file SHA256, launcher command, MPI count4 and OMP_NUM_THREADS=1. Aggregate rank use remains below16.
- `scaling.png` shows rates and contrast slopes. `fields_S1000.png` and `fields_S2000.png` show representative evolution fields; each figure identifies its mesh/status.
- `run_table.json`, `spatial_qualification.json`, `qualification.json`, and `cadence_comparison.json` retain numerical tables and diagnostic provenance. `qualification.json` is the earlier analysis with its explicitly corrected coverage omission; current spatial_qualification.json uses actual brackets.
- Raw data are in each managed experiment workspace. Earlier `fields.tar.gz` archives contain all plot HDF5. Compact runs retain all magnetic frames losslessly plus representative complete states and native parameter/log/conservation files. `fields[].retained_full_state` distinguishes retained full states from hashes of reduced snapshots.

Example rerun: lab.run('calculation.py', args=['--S','2000','--n','512','--tmax','1.8','--cadence','0.01'], inputs=['island_coalescence.py','null_diagnostic.py'], outputs=['result.json','fields.tar.gz','magnetic_series.h5'], capability='flash-island-coalescence-resistive-mhd-4.8', stage='exploration', timeout=3000). Evidence requires approved source-bound methods and fresh runs. Exact prior commands and execution/acceptance status are in the receipts.

The conditional measured-strain closure was tested in native exploratory offline extraction and substantially underpredicted both calibration rates (~25–31%). Its required5% calibration gate fails; no validation is authorized. Preserve this failure separately from the original contrast. Inferred effective thinning from observed width derivatives is not velocity-measured strain and currently lacks a validated physical interpretation. These mechanism diagnostics still require recorded reproduction. No repaired scientific claim is yet committed or supported. Any repair requires accepted falsification, an explicit explanatory scope and a prospective prediction challenged by independent fresh cases. Unresolved qualification does not complete the study.
'''
Path('RESULTS.md').write_text(head)
