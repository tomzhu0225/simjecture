---
name: warpx
description: Author, commission, and diagnose simulations with the pinned WarpX 26.07 PICMI capability. Use for any hypothesis whose decisive evidence may require WarpX, especially multidimensional, collisional, electromagnetic, or fully kinetic particle-in-cell calculations.
---

# WarpX 26.07 PICMI skill

Use this skill when a hypothesis can be challenged with a particle-in-cell
calculation supported by the installed `warpx-cpu-26.07` or
`warpx-cuda-openpmd-26.07` capability. The skill
explains the instrument; it does not prescribe the scientific question,
parameters, diagnostics, or conclusion.

## Execution contract

- Author the PICMI Python program and any analysis programs in the writable
  workspace using workspace-relative action paths such as `probe.py`, never
  `/work/probe.py`. The sandbox maps the working directory to `/work` only at
  execution time.
- Execute a PICMI program with `run_capability`, selecting
  `warpx-cuda-openpmd-26.07` for local 2D GPU work or `warpx-cpu-26.07` for
  the CPU fallback, and an argv whose first item is the workspace-relative
  Python filename. Arguments are passed directly to the pinned Python
  interpreter; there is no shell.
- The capability has no host home, network, provider credential, or writable
  location outside `/work`.
- Before GPU production work, read `references/gpu-launch-tuning.md`. The CUDA
  capability is non-MPI, 2D-only, and provides HDF5 openPMD diagnostics.
- Ordinary `run_python` does not contain `pywarpx`. Use `run_capability` for
  programs that import `pywarpx`; use ordinary Python for independent analysis
  when its installed packages suffice.
- Treat a zero exit status as execution success only. It is not scientific or
  numerical qualification.
- The harness health-checks each exact capability build once and caches the result.
  Do not repeat generic import, CUDA, or openPMD smokes inside each campaign when
  `capability_preflight` is healthy.
- Use `stage=workbench` while authoring, debugging, or revising PICMI programs.
  Workbench artifacts are provenance-recorded but permanently non-evidentiary and
  need no claim or contract. Once the program is stable, freeze it and use
  `stage=evidence` for prospective five-aspect qualification and scientific runs.

## Recommended use

1. Translate the active subhypothesis into observables and a falsifier.
2. Derive scientific parameters from the active hypothesis, explicit operator
   input, or sources retrieved during the campaign. Preserve that provenance in
   the workspace. Then choose a supported geometry, field model, boundaries,
   species distributions, time-integration scheme, and runtime. For
   electromagnetic calculations, read `references/time-integration.md` before
   fixing the timestep.
3. Iterate on unknown interfaces and candidate programs in the workbench. Before
   promoting a stable WarpX program, register a prospective evidence contract on
   its instrument claim and transition to the complete physical commissioning
   contract. Workbench success cannot be promoted retroactively; the evidence-stage
   qualification must generate fresh artifacts from the frozen source.
4. Begin workbench development with an inexpensive anchor that exercises the intended model and
   diagnostic path. Make the program emit a compact JSON commissioning summary
   with qualification booleans below a top-level `checks` object, and register
   exact `validation_checks` such as `checks.completed` for its named
   booleans. Tag checks as `representation`, `physics_controls`, `boundaries`,
   `diagnostics`, or `numerical_regime`; one qualifying contract must cover all
   five. `physics_controls` verifies that the interactions, forcing, sources,
   or constitutive controls required by the claim are present in the realized
   run and have a measured effect where relevant. An
   `interface` check is useful but cannot qualify a scientific run by itself.
   Commission the mathematical representation, not only execution.
   Keep the commissioned program source immutable and parameterize anchors,
   sweeps, and controls through arguments or configuration. Changed source must
   be recommissioned before it can generate scientific evidence.
5. Inspect the realized input and outputs. Challenge charge balance, current
   and force balance, energy, boundaries, particle loading, interaction/source
   activation, resolution, timestep, particle statistics, finite-domain
   effects, and diagnostic definitions as relevant. Preserve quantitative
   metrics behind every qualification boolean; do not make a boolean a mere
   restatement of the requested inputs.
6. Establish a numerical practice before using production runs as evidence.
7. Preserve raw outputs and write analysis code in the workspace. Do not rely
   only on terminal prose.

Read these resources as needed:

- `references/picmi-interface.md`: main Python construction sequence.
- `references/2d-xz-commissioning.md`: required reading before any 2D Cartesian
  run; coordinate, field-source, equilibrium, and preflight invariants.
- `references/diagnostics.md`: field, particle, reduced, and openPMD outputs.
- `references/time-integration.md`: explicit and implicit PICMI evolve schemes,
  timestep selection, and solver qualification.
- `references/numerical-risks.md`: common validity failures.
- `references/resource-scaling.md`: controlling experiment cost.
- `references/cpu-launch-tuning.md`: required before a long local-host CPU
  campaign; detects MPI support, benchmarks OpenMP count/affinity and AMReX
  block size, and records the Ryzen 9 9900X calibration.
- `references/gpu-launch-tuning.md`: required before a local-host CUDA run;
  verifies the actual backend, supplies the WSL launch environment, benchmarks
  GPU block sizes, and records RTX 4000 Ada CPU/GPU comparisons.
- `references/local-cuda-deployment.md`: required when installing or repairing
  the CUDA/openPMD runtime on this or a new machine; use its pinned bootstrap,
  post-install validation, and failure signatures.
- `examples/minimal_smoke.py`: a one-step neutral-plasma interface smoke test;
  it is deliberately not a scientific template. Its JSON booleans are under
  `checks`.
- `examples/implicit_em_smoke.py`: a one-step 2D theta-implicit electromagnetic
  wiring and native-input smoke test; it is also permanently non-evidentiary.
  Its JSON booleans are under `checks`. Run it in the workbench only when the
  implicit interface itself is relevant; it does not prove loaded-plasma stability.
- Host repository demos and operator launch scripts outside this skill tree are
  not skill resources: sandbox agents cannot `read_skill` or
  `materialize_skill_resource` them.
- `examples/openpmd_field_smoke.py`: a one-step 2D field-diagnostic wiring and
  openPMD/HDF5 readback smoke test; it is permanently non-evidentiary and is the
  CPU and CUDA/openPMD capabilities' cached harness preflight. Campaign agents
  normally need not repeat it. Its JSON booleans are under `checks`.
- `scripts/benchmark_cpu_threads.py`: run an isolated, validated OpenMP scaling
  sweep for an operator-supplied PICMI program and exact argument list. Never
  infer MPI support merely from the presence of `mpiexec`; the script queries
  the loaded AMReX library.
- `scripts/run_local_cuda.sh`: operator-side launcher for the project-local 2D
  CUDA runtime. Autonomous sandbox work uses the named CUDA capability instead.
  Skill `scripts/` are host/operator tools: they are not exact-reuse sandbox
  programs and typically cannot run inside the capability (for example they
  may call `nvidia-smi`). Use `examples/*.py` for in-sandbox exact reuse.
- `scripts/bootstrap_local_cuda.sh`: create the pinned CUDA, non-MPI HDF5, and
  openPMD environments and compile the 2D WarpX binding from an audited source
  checkout.
- `scripts/probe_local_cuda.py`: prove CUDA-aware AMReX plus an openPMD HDF5
  write/read round trip after deployment.
- `scripts/benchmark_gpu.py`: run a guarded, validated CUDA block-size sweep;
  it passes the operator-supplied program arguments through unchanged except
  for the explicitly named block-size option.
- `scripts/reduced_energy_budget.py`: materialize this deterministic sandbox-safe
  reader for pinned single-level `FieldEnergy` plus `ParticleEnergy` diagnostics.
  It selects exact total columns by realized header, refuses unknown schemas,
  and prevents adding totals to their component/species columns.

Official WarpX 26.07 documentation:

- <https://warpx.readthedocs.io/en/latest/usage/python.html>
- <https://warpx.readthedocs.io/en/latest/usage/parameters.html>
- <https://warpx.readthedocs.io/en/latest/usage/workflows/analysis.html>

## Boundaries

Do not infer that WarpX is preferable merely because it is installed. A
smaller analytic or ordinary-Python calculation may be a better discriminator.
Do not claim that a runtime smoke test qualifies a physical regime. Do not
silently change an observable or numerical policy after seeing a result;
record the reason and treat the changed calculation as a new attempt.
Never obtain scientific parameters, expected outcomes, acceptance thresholds,
or benchmark definitions from this skill, its smoke examples, host-performance
records, or an earlier demonstration. Retrieve or derive them within the active
campaign and preserve their source.
