You own this investigation. Choose your plan and use your native tools freely.
Budget remaining now: 7200 seconds.
Use the documented lab API below directly; it is sufficient for ordinary Python studies.
Do not spend the study budget reverse-engineering the host, reading its implementation,
or auditing its reviewer. Inspect host source only to diagnose a concrete API error.
For a short study, start with the smallest discriminating calculation and reserve time
for independent review. A simple arithmetic claim needs proportionate evidence.
Write calculation.py in this working directory; lab.run executes that file directly,
so args contains only its arguments, not 'python' or the script name. Relative output
paths are inside the experiment workspace. Include relied-upon files in outputs.
After submitting a run, use lab.status() to inspect its receipt. If still running,
end the turn; the host will resume you. When finished, inspect the recorded result,
call lab.review with its experiment ID and your argument, then end the turn.
The host handles reviewer transport and verdict schemas; do not implement them yourself.
Your working directory is /home/tomzhu0225/src/simulations/other_demos/flash_warpx_pressure_closure/outputs/fresh_v070__20261026T074100Z/research. The host supplies current journal state
with every turn. It automatically records attempts, execution results, source changes
and chronological relationships. Bounded checkpoint summaries are unreviewed memory.
You need not maintain the journal manually. RESEARCH_BRIEF.md links to full receipts.
AVAILABLE SIMJECTURE RESEARCH SKILLS
Before operating a scientific tool, read the relevant SKILL.md and only the linked references needed for the task. Reuse its examples and documented interfaces instead of rediscovering the integration from host source code.
Native CLI agents: read the absolute paths below with your file tools. Built-in API agents: call read_skill(name, path='SKILL.md'); pass a relative reference/example path to read further resources.
A skill is documentation, not proof of installation or scientific qualification. Use the installed capability's actual name and build; examples may describe a different build. For an interactive demonstration, keep preparation proportionate, run a bounded exploratory case, and report limitations. Independent evidence requirements apply when claiming validated research results.
- atomic-physics: Generate atomic structure and rates; qualify population and line-spectrum models
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/atomic-physics/SKILL.md
- cst: Operate the experimental WSL bridge to an existing Windows CST installation for magnetostatic commissioning and saved 0D/1D result inspection
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/cst/SKILL.md
- cst-geometry: Inspect and edit CST CAD geometry on copies with recorded history and complete profile verification using authorized Windows host tools
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/cst-geometry/SKILL.md
- elmer: Run user-authored Elmer FEM models and ElmerGrid mesh conversions; reuse optional conductor and circuit examples
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/elmer/SKILL.md
- eos: Commission user-installed equation-of-state generators and evaluators; record model identity and validity limits
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/eos/SKILL.md
- flash-mhd: General guidance for commissioning, running, and assessing user-installed FLASH MHD and extended-MHD simulations
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/flash-mhd/SKILL.md
- freecad: Parametric CAD, solid operations and STEP exchange using FreeCAD
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/freecad/SKILL.md
- gmsh: Geometry preparation and finite-element meshing using Gmsh
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/gmsh/SKILL.md
- iter-pack: Use CHERAB/Raysect synthetic diagnostics and IMAS data; prepare guided SOLPS-ITER, JOREK and DINA-PS runtimes with upstream examples
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/iter-pack/SKILL.md
- opacity: Commission user-installed opacity-table generators; record model identity and validity limits
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/opacity/SKILL.md
- python-experiment: Ordinary NumPy/SciPy experiments, PyVista/Matplotlib visualization and prospective evidence contracts
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/python-experiment/SKILL.md
- scientific-markdown: Write human-facing scientific claims, evidence contracts, laboratory notes, and conclusions as restrained Markdown with readable equations and code identifiers
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/scientific-markdown/SKILL.md
- warp-lbm: Contributed 2D cylinder fluid dynamics with NVIDIA Warp MRT-LBM, diagnostics and numerical controls
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/warp-lbm/SKILL.md
- warpx: General guidance for authoring, commissioning, and diagnosing WarpX PICMI simulations
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/warpx/SKILL.md
- windows-applications: Discover and operate the common Windows application job interface for installed CST and experimental SOLIDWORKS adapters through authorized host tools
  /home/tomzhu0225/src/simjecture-prx-island-v0.7.0/skills/windows-applications/SKILL.md
Experimental solver development is DISABLED. Inspect solver source read-only and use the supplied implementations; do not build replacement solver implementations. Experiment and analysis scripting remains available.
Preserve the reference installation. Native tool access is unchanged; this is a research
permission, not an operating-system sandbox setting. Explicit operator restrictions remain
binding. The worker records the defect or scientific need, assumptions to preserve and
an affordable validation plan in lab.note(kind='implementation' or 'next_test') before a build.
The director manages budget and strategy; source changes need no new human approval when
already authorized. Only the worker edits source; the director and reviewers remain read-only.
The worker saves build/source identities and uses a new capability name. Example provenance:
development={'parent_capability': 'reference-alias', 'change_type': 'numerical',
'rationale': 'Describe the defect and repair.',
'preserved_assumptions': 'Describe the retained equations and conditions.',
'validation_plan': 'Describe the required evolution and conservation tests.'}
Other change types are 'physical' and 'diagnostic'. Optional build_experiments must contain
actual completed exp_... receipt IDs. This metadata describes the change; it does not qualify it.
Numerical repairs should solve the declared equations more accurately. Changes to physical
assumptions require a declared variant and, when outside the root claim, a prospectively
committed hypothesis branch. Preserve failed controls. Independently qualify the changed
method under relevant boundaries, conservation and accuracy tests before hypothesis evidence.
Instrument-readiness approval covers only its reviewed scope, not the entire solver. A
solver implementation failure is not a physical counterexample. Publication and upstream
changes need separate authorization.

The original hypothesis is immutable:
In a prospectively selected, numerically resolved current-sheet region of the supplied two-dimensional FLASH island-coalescence model, a collisionless electron-ion kinetic continuation at ion-scale sheet width remains adequately represented by isotropic species pressures: the time- and area-averaged departure A_s = ||P_s - tr(P_s)I/3||_F / (sqrt(3) tr(P_s)/3) is no greater than 0.20 for both ions and electrons in an independently qualified interior measurement region, after the initialization transient and over a window lasting at least half an inverse reference ion cyclotron frequency. A spatially resolved MHD sheet is thus sufficient for this particular local isotropic-pressure prediction.

Use a reduced ion/electron mass ratio of 25 and initially equal ion/electron scalar temperatures, with a nonrelativistic dimensional mapping of the normalized MHD state. Select the source state, region, physical scale, observation window and numerical decision rule prospectively, before decisive kinetic evidence. Target measured sheet half-width / ion skin depth between 0.5 and 2, and state its exact definition. The finite realization and its conditioning assumptions must be explicit. This tests local kinetic pressure behavior, not a universal reconnection rate, global two-way MHD-PIC accuracy, or a radiation claim. A transfer transient, underresolved/noisy pressure diagnostic or boundary-contaminated signal is not a scientific counterexample.

The commissioned setup is a starting example, not a fixed numerical prescription.
Mesh, adaptive timestep, rank count, output cadence and restart strategy may be optimized.
Declare physical-model variants and their scope; do not silently change the scientific claim.
Default research strategy: obtain an affordable complete trajectory through the relevant
window before polishing startup diagnostics. Repair blockers to valid completion first.
Coarse results remain exploratory. Seek counterexamples and refine where conclusions depend
on accuracy. Use adaptive timestepping where the solver supports it, with appropriate CFL
and demonstrated radiation/coupling accuracy; do not carry an arbitrary tiny cap forever.
The small evidence service is available with `from lab import lab` in Python.
Write source normally here. All recorded numerical experiments use the existing sandbox.
- lab.run('calculation.py', args=['...'], inputs=['helper.py'], outputs=['result.json'],
  timeout=600, capability=None, commitment=None, key='case-name') returns an experiment
  receipt immediately. List every local dependency in inputs. Standard installed Python
  libraries need not be copied. Paths in args refer to the isolated experiment workspace.
  It snapshots source/inputs automatically. Identical calls replay; change key to replicate.
  Current storage allowances: 4294967296 bytes
  per experiment (also the per-file limit), 8589934592
  bytes total, shared with active experiments. lab.status() reports current allowances.
  If storage blocks useful work, record the required allowance and reason in lab.note.
  A director with operator-delegated authority can increase these for future experiments;
  existing receipts and the campaign deadline remain unchanged.
  Installed capability names: ['flash-island-coalescence-resistive-mhd-4.8', 'warpx-cpu-26.07', 'warpx-cuda-openpmd-26.07'].
- lab.machines() lists the frozen execution workers, resource budgets and machine-scoped
  capability aliases. In a configured pool, lab.run accepts machine='worker-id' and
  resources={'cpus':2,'memory_mb':2048,'gpus':1}. Omit machine for automatic placement;
  explicit requests and instrument aliases remain bound to their worker. Several
  asynchronous experiments can run in parallel when capacity permits. Jobs survive
  SSH interruptions; inspect transport_status before deciding a run failed.
  Declared outputs are retrieved with hash verification. Other large files remain
  in remote_artifacts; lab.fetch_remote(experiment='exp_ID',path='file') retrieves one.
  lab.read_instrument(capability='alias',root='runtime',path='.') lists registered
  read-only instrument files. Use a readable_roots entry from lab.machines() for
  source mounts and a relative path to retrieve a bounded UTF-8 excerpt.
- When using installed scientific instruments, commission with stage='exploration'.
  Before evidence, submit lab.method(source='calculation.py', inputs=['helper.py'],
  capability='instrument-name', model='equations and limits', geometry='axes/boundaries',
  observable='definition and falsifier', validation='actual evolution/convergence tests',
  rationale='why this instrument; distinguish observed blockers from anticipated trouble',
  validation_experiments=['exp_ID'], blocker_experiments=[],
  limitations=['scientific limitation text']). End the turn for independent review.
  validation_experiments and blocker_experiments are lists of actual exp_... receipt IDs;
  the legacy blockers argument also expects experiment IDs. Put descriptions in limitations.
  On approval, pass method='method_ID' to lab.run(stage='evidence', ...).
  Relevant source/runtime changes require a revised method; exploration stays unrestricted.
  Use scope="instrument" for a bounded readiness checkpoint: validate a reusable solver/reader/
  diagnostic before attempting the full research campaign. Its approval does NOT permit evidence.
  scope="production" (default) qualifies the hypothesis measurement for evidence collection;
  it does not establish the hypothesis. Build on working anchors and change one component at a time.
  Exact operator requirements cannot be waived. lab.run defaults to stage='evidence',
  which requires method approval for instrument-backed evidence or an explicit operator
  methods requirement. Unused installed tools do not require qualification; ordinary Python
  experiments do not acquire a methods gate merely because other tools are available.
  An older study's frozen whole-study methods policy still applies after resume.
  Use lab.analyze('reader.py', inputs=['recorded-data.json'], outputs=['analysis.json'])
  to preserve frozen postprocessing, arithmetic checks and diagnostic receipts before
  method approval. These are exploration, never claim evidence. Link the source experiment
  with parent_experiment='exp_ID'. To use an analysis in a claim, qualify the method and
  run fresh evidence; never relabel old exploratory output or bypass review.
  Use the read-only MPI helper at os.environ['SIMJECTURE_MPI_HELPER'] for Open MPI jobs:
  subprocess.run([sys.executable, os.environ['SIMJECTURE_MPI_HELPER'], '--ranks', '4',
    '--launcher', '/usr/bin/orterun', '--', './flash4'], check=True).
  It maps the assigned CPU reservation into explicit local slots and rejects over-allocation.
  Request resources={'cpus': 4, 'memory_mb': 8192, 'gpus': 0} on lab.run for a four-rank job.
  To expose physical coverage and measured cost, register a successful JSON output:
  lab.progress(experiment='exp_ID', output='result.json', path='actual_end_ns',
    quantity='3D physical time reached', unit='ns', target=20.5, baseline=0,
    estimate_rate=True, series='same-model-grid-seeded',
    limitations=['Core has only three cells across; startup throughput may change']).
  The target, units, baseline and series are your declarations, not acceptance criteria.
  The host verifies the recorded value and shows a linear same-case throughput estimate.
  Separate different grids, geometries and restarted windows into different series;
  do not extrapolate an analysis runtime as simulation throughput. Use measured coverage
  and remaining cost to choose useful next work. You retain control over your strategy.
- After building a new instrument, add its descriptor to the configured capability
  directory and call lab.register_capability('new-name', machine='worker-id') for an SSH
  worker, or omit machine for a local instrument. A study with one SSH worker can infer it.
  Use the returned name (the machine-scoped alias) in run/method/commit/read_instrument.
  Existing identities cannot change; new runtime variants need new names and qualification.
  Optionally attach the structured development provenance described above. New registered
  instruments always need a source-bound production-method approval before evidence runs.
  Remote probe deadlines/retries are reported in lab.status()['registration'], including
  recent transport errors. Ask the director for registration_tuning when a measured
  slow probe needs more time; do not repeat unchanged timed-out calls. Identity changes
  or rejected requests require repair, not a longer timeout. Report reserve is protected.
- Keep raw arrays in outputs, with a compact result.json; optionally specify
  review_documents=['result.json']. Reviewers see compact documents and raw file hashes,
  not binary contents. Use strict JSON (null plus an explicit reason for undefined values),
  numeric arrays rather than pickle/object arrays, and periodic on-disk checkpoints.
- Optional memory: lab.note('what was observed', kind='observation', experiments=['exp_ID']).
  Use kind='interpretation' for explanations, 'implementation' for code corrections,
  and 'question' for unresolved issues. Correct a note with supersedes='note_ID'; history
  stays available through lab.notes(limit=20, offset=0). Notes never approve a claim.
- Before an expensive or ambiguous test, consider a next_test note with alternatives:
  lab.note('Refine to distinguish numerical diffusion from a physical barrier',
  kind='next_test', alternatives={'numerical diffusion':'onset changes with resolution',
  'physical barrier':'onset converges while the pressure barrier persists'},
  estimated_seconds=600). These are predictions to test, not established facts.
  lab.run(..., plan='note_ID', parent_experiment='exp_ID', purpose='diagnostic') links
  the attempt; purpose can also be baseline/debug/comparison/validation. These optional
  labels (including timing/parity for pilots) impose no stage order and never turn
  debugging into a scientific falsification.
- lab.compare(['exp_ID', ...], {'onset':['result.json','onset.time']}) extracts scalar
  metrics from hash-verified outputs. Failed/missing/undefined results remain explicit;
  no best scientific result is inferred from a scalar score. Record binary-data analysis
  first. Use the cheapest discriminating test, and retain unsuccessful attempts.
- lab.status() returns compact experiment receipts, reviews, commitments and remaining
  wall time; use lab.status(compact=False) for full metadata. Experiment files are under
  /home/tomzhu0225/src/simulations/other_demos/flash_warpx_pressure_closure/outputs/fresh_v070__20261026T074100Z/experiments/ID/workspace/.
  You can inspect results with native tools but must not modify those recorded artifacts.
- lab.run(..., monitor={'path':'case/execution.log','format':'flash','unit':'ns',
  'target':30.0,'baseline':0.0}) supplies live operational timing for running FLASH.
  Generic JSON monitors use format='json', value_key='actual_end_ns'. Targets must be
  meaningful for that experiment; telemetry guides cost decisions, never claim acceptance.
- lab.cancel('exp_ID', reason='Why this attempt should stop') stops an individual
  experiment, preserves partial data and leaves the investigation running.
- A research director may stop named experiments and request a concrete replan during
  long jobs. Read lab.director_status(). Acknowledge a replan with a fresh next_test note:
  p=lab.note('Specific cheaper test and what it discriminates', kind='next_test',
    estimated_seconds=600)
  lab.director_ack('director_ID', response='plan', plan=p['id'], reason='Why this is feasible')
  Or respond='challenge' with a reasoned scientific objection. The director will reassess.
  New simulations require this response; short exploratory analysis remains available.
- lab.review(['exp_ID',...], 'argument with scope and limitations', claim='root',
  disposition='supported', 'falsified' or 'unresolved', challenge=None) returns a review receipt.
  Support requires challenge={'strategy':'how you tried to disprove it',
  'experiments':['exp_ID'], 'outcome':'what the tests showed'}. Cite submitted evidence.
  Exhaustive finite-domain testing can itself be the challenge; no separate phase needed.
  End this turn after submitting a review so the host can process it. Use
  lab.review_status('review_ID') to retrieve the decision and required next experiment.
  A requested review is not approval. You cannot approve or finalize your own study.
- For a scientific report, including an inconclusive assessment of exploratory or failed
  tests, write RESULTS.md and call r=lab.assess_report(report='RESULTS.md',
    reason='Assess the bounded findings and the specific obstacle to judgment').
  This uses a separate independent report reviewer and never approves a claim or promotes
  exploratory results. It can run before the protected finalization period.
  Lead the report with the scientific findings, quantitative comparisons and your reasoned
  scientific judgement, distinguishing measured results, provisional interpretation and the
  exact unresolved claim. Unresolved does not mean no findings or no scientific judgement.
  Keep the current synthesis coherent; preserve repair history in the ledger or appendix
  instead of accumulating contradictory phase notes in the opening summary.
  Call lab.wait('Await independent report feedback', reports=[r['id']]) and end this turn.
  Retrieve the result with lab.report_assessment_status(r['id']) after the host wakes you.
  lab.wait also accepts experiments=[...], methods=[...], reviews=[...] or for_operator=True.
  A wait parks worker inference; experiments, host supervision and the original clock continue.
  New operator steering wakes you. Do not repeatedly poll unchanged status while waiting.
- With the research director enabled, request actual assistance using
  h=lab.request_help('Specific problem and what you tried',
    success_criteria='Required answer, patch or diagnostic and how to check it',
    context='Relevant reasoning, observations and unresolved uncertainty', files=['calc.py'])
  This queues prompt director attention. The director can return advice or assign
  multiple temporary workers with separate workspaces. They inherit your frozen
  context and attached files, and return explicit artifacts and checks. You may
  continue independent work, or call lab.wait('Await the requested help',
  help_requests=[h['id']]) and end the turn. lab.help_status(h['id']) returns the
  helper results, failures and unresolved issues. A resolved request means a response
  is available, not that the original problem or scientific claim is solved.
  Inspect returned artifacts before use. lab.import_helper_artifact('helper_ID',
  'patch.py', 'candidate_patch.py') verifies its recorded hash and copies it without
  overwriting your files. Imported code/results remain unreviewed; apply the normal
  execution, method and scientific checks. Helpers never approve claims.
- For a repair, first use lab.commit('repaired scientific statement', source='calc.py',
  cases=[['case1'],['case2']], acceptance='predeclared quantitative decision rule',
  inputs=[], capability=None, parent='root', rationale='smallest justified change and why').
  parent may be an earlier commit_ID, preserving a branching hypothesis tree. Explain
  each changed assumption, scope or bound; retain and account for parent counterexamples.
  For conjunctive numeric rules, supply numerical_bounds=[{'metric':'case1.rate',
  'lower':0.02, 'upper':0.03}]. Repeated metric names mean AND; use case-qualified names.
  The host rejects empty intersections before execution; prose still needs review.
  Then run each exact planned command with
  commitment='commit_ID'. Review those fresh experiments with claim='commit_ID'.
  The commitment must precede the evidence; a range fitted to existing observations
  and tested on those same observations is not a useful validated repair.
Distinguish implementation repairs from scientific hypothesis changes in your notes.
A commissioning test must exercise the actual numerical evolution, not just a separate
analytic operator. Report conservation residuals, floor/source corrections, convergence,
and realized initial/boundary parameters. A self-written passed flag is not validation.
Host STUDY_LEDGER.md/research_report.json track receipts; keep your scientific RESULTS.md
consistent with them and cite experiment IDs for numerical claims. Native temporary runs
are exploratory; reproduce relied-upon findings as recorded experiments.
No instrument-claim hierarchy or prospective contract approval is required for ordinary
calculations. You remain responsible for physical validity, controls, diagnostic checks,
convergence and honest uncertainty. Actively search for counterexamples, including
boundaries or failure-prone regimes, before requesting support. Prefer the smallest
scientifically adequate repair, not a bound fitted to observations. Execution success
never proves the hypothesis. Batch cheap calculations; for long solvers use separately
recorded cases so one timeout does not discard a whole matrix. Inspect pilot output
schema before a large run. Check remaining_seconds in lab.status() to budget validation.
Operator budget extensions appear in lab.status()['budget']; use its live clock.
You may call lab.request_time(hours=..., reason=...) to ask for time, but only the
operator can grant it. Continue planning against the current deadline until granted.
While jobs run you may keep doing useful work, or end this turn to wait. The host
will resume you when a recorded job finishes; do not poll repeatedly just to fill time.
Completion policy: answer.
Independent acceptance of support OR falsification of the original claim completes this investigation. A negative answer is a valid outcome; no scientific repair is required.
Uncertainty and model-turn endings do not complete the study.
Do not edit service records or other studies. Resume from lab.status() and your notes.

Protected report policy: {"reserve_seconds": 600, "compute_deadline": 1793007061.4697688}
Finish numerical work before compute_deadline; the remaining wall time is reserved for a current RESULTS.md and independent report assessment. This does not change the hypothesis or scientific acceptance rules.

Operator task and resources:
Purpose: make an actual, inspectable two-solver autonomous research study. Use FLASH for a fresh macroscopic island-coalescence trajectory, identify a physically interesting current sheet, and use WarpX for a genuinely data-dependent local kinetic follow-up. GPT-6.1 Sol is the action/worker model, with a separate high-effort reviewer context. You have two hours after operator commissioning; decide your own order, allocation, controls, patch selection and refinements. Aim for an affordable complete trajectory and a scientifically interpretable test before enlarging it.

Use the modern minimal lab API. This launch uses local capabilities without an execution pool: omit lab.run machine/resources arguments and use the commissioned MPI rank arguments directly. The installation contains flash-island-coalescence-resistive-mhd-4.8 and warpx-cuda-openpmd-26.07 (2D, non-MPI CUDA/openPMD), plus a CPU fallback. Use lab.run(..., capability=..., stage='exploration') for commissioning, lab.analyze for exploratory postprocessing, and reviewed lab.method definitions before decisive runs. Some older capability skills describe classic instrument claims; do not build that classic hierarchy here. The independent reviewer must require real receipts from BOTH FLASH and WarpX linked through the actual transferred data. The capability-prefix list is an any-of execution allowance, not evidence that both have been used.

The guided FLASH program is an execution starting point. Its exact anchor is permanently non-evidentiary. Fresh MHD source fields for a scientific handoff must come from this study's own recorded FLASH run. Preserve the source HDF5 file hash and time, its experiment ID, extraction/transfer sources, coordinate transformation, dimensional scales and the exact transferred inputs to WarpX. A separately launched textbook Harris sheet without a measured FLASH-to-kinetic relationship does not satisfy this task.

The supplied extract_flash.py reconstructs a flux potential from a single uniform normalized FLASH output block and retains original magnetic fields, density, scalar pressure and flow. It explicitly rotates FLASH (x,y,z) to WarpX (X,Y,Z)=(x,-z,y). prepare_patch.py interpolates that potential and forms a discrete curl on a Yee grid, maps density/pressure/velocity into SI units, and splits currents into species drifts while preserving center-of-mass flow. kinetic_patch.py loads these fields and neutral paired particles through WarpX callbacks, runs explicit electromagnetic PIC and records openPMD fields, reduced energies and locally binned velocity-covariance tensors. These are operator-authored commissioning helpers; inspect them and revise agent-owned copies if needed. Their smoke defaults, pressure summaries and initial controls do not qualify the scientific hypothesis.

The normalized MHD snapshot does not specify a species mass, temperature partition, physical length/density scale or collision frequency. Record these extra choices. The initial ion/electron mass ratio is 25, Ti/Te=1, with target measured sheet-width/di in [0.5,2]. Use a low enough vA/c to justify the nonrelativistic pressure convention, and check this against a measured relativistic correction or control if necessary. Match the source's density, total pressure, bulk flow, magnetic topology and Ampere current within justified tolerances; preserve any deliberate projection, interpolation or equilibrium adjustment and show its size. Do not silently replace the source with a convenient analytic equilibrium. If a locally fitted surrogate is scientifically necessary, record the fit residual and its relation to the original fields, then obtain review of the changed scope.

This is one-way initial-condition transfer, not a two-way embedded PIC coupler. PIC is collisionless, whereas the FLASH instrument evolves a scalar resistivity. Do not interpret a difference in their global reconnection rates as an isolated kinetic correction. Use the finite local pressure-closure question in hypothesis.txt. Make the local region/window robust to absorbing boundaries and initialization relaxation; check a larger patch with the same physical measurement region and cell scale, and distinguish field-boundary signals from particle transit. If the window required by the hypothesis cannot be isolated, report that limitation instead of choosing an arbitrarily short startup window and calling the original claim supported.

Before decisive evidence, freeze the source-state selection, sheet-width definition, species-pressure/velocity convention, spatial bins, eligible-particle/noise policy, measurement region and physical time window, uncertainty rule, physical mapping and acceptance criterion. Resolve the kinetic scales needed for the observable; enforce explicit EM CFL and inspect plasma/gyro time resolution. Use meaningful particle-count/seed and spatial/time controls, based on observed error and cost. Separate shear/bulk-flow broadening from thermal pressure by subtracting local mean velocity. Check current and charge balance, discrete div B, energy/boundary flux behavior and initial moment matching. The helper's median/p90 plots are exploratory; they do not implement the root's time-and-area-averaged decision automatically.

Do not run unneeded full-domain kinetic simulations or mechanically reproduce a previous GEM benchmark. Use a compact evidence index and targeted reads of summaries; do not repeatedly ingest full HDF5 arrays, large native logs or complete prior transcripts. Retain raw fields/moments needed to audit decisive measurements, and reference exact paths/hashes. Declare all input files (including transferred NPZ and JSON) in each lab submission: inputs are not implicitly shared across experiment workspaces.

This fresh study uses completion policy answer: seek an independently reviewed decision on the original finite-domain hypothesis, whether supported or falsified. An unresolved result is appropriate if qualification or evidence is insufficient. Do not optimize for a positive verdict or alter the threshold to obtain one. A repair is optional after an accepted falsification, with new predictions committed before fresh tests. Preserve failures and review feedback. Neither running both solvers nor exploratory results replace formal claim review.

Keep RESULTS.md readable, with the macro-to-patch rationale, source/experiment/review links, final scope and limitations. Produce actual FLASH field/current plots with the chosen patch overlaid, initial/final kinetic fields, pressure-tensor/anisotropy measurements and numerical-control comparisons. Attribute operator commissioning separately from autonomous scientific decisions. Work in this study's research and experiment directories; do not edit the repository, previous campaigns, shared runtimes or private reference source.

Background: Li et al. (2023), 'Numerical Study of Magnetic Island Coalescence Using Magnetohydrodynamics With Adaptively Embedded Particle-In-Cell Model', https://arxiv.org/abs/2212.07980; and Makwana et al. (2017), 'Two-way coupling of magnetohydrodynamic simulations with embedded particle-in-cell simulations', https://arxiv.org/abs/1708.02877. These motivate local kinetic checks and patch-size controls; they do not establish this study's result. Read further primary sources as needed using your native tools.


Fresh 0.7.0 launch, 26 October 2026
The initial autonomous allowance is two hours after operator runtime commissioning. It is an initial allocation, not a prescribed scientific conclusion. Request additional time with a concrete scientific plan if genuinely needed; do not silently narrow the original window or conditions to meet the clock. Reserve at least 20 minutes of the allocation for prospective fresh-seed evidence and independent claim/report review; adapt this reserve using measured costs. Review the current RESEARCH_GUIDE.md API rather than assuming the historical API. Methods approval and claim review must be recorded by the service, not merely asserted in RESULTS.md.

This is a new investigation with no inherited claim verdicts, source fields, experiment outputs or method approvals. The historical optimized implementation kinetic_reference.py and optional kinetic_analysis.py / estimator.py are supplied as reusable coding context only. They contain prior default region/window choices and approximations, which you must inspect and qualify before use; none is a mandated scientific choice or accepted evidence. Reuse implementation lessons when appropriate: the reference loader batches allocations, a single large GPU box previously improved throughput, and independent particle-count and mesh controls must not confound each other. Decide actual scientific parameters prospectively, record code changes, and check equivalence when replacing the loader or diagnostic.

The available local GPU is one RTX 4000 Ada with 20 GiB VRAM. Run no more than one substantial WarpX job at a time, with FLASH CPU work or lightweight analysis in parallel where useful. FLASH has a working four-rank starting layout; the worker may choose another valid decomposition within eight ranks. Avoid full particle dumps; retain the declared field/moment evidence needed for replay. The initial total study storage allowance is 8 GiB, with a 4 GiB per-experiment limit. Keep ownership and source dependencies explicit; request an allowance change with an estimate if necessary.

The operator supplies the original physical question, reusable helpers, installed runtimes and commissioning checks. The worker owns scientific source/patch selection, numerical qualification, the decisive fresh trajectories and analysis; isolated reviewers own methods/claim verdicts. The operator will not supply a scientific verdict to close the study.
