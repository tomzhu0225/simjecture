---
name: flash-mhd
description: Commission, run, and assess user-installed FLASH magnetohydrodynamics and extended-MHD simulations. Use when an installed FLASH capability may provide relevant fluid-plasma evidence; do not use it as a substitute for kinetic modeling or as authority to redistribute FLASH.
---

# FLASH MHD

Use this skill to operate a FLASH executable that the operator obtained and
built under the FLASH license. The skill describes the instrument; it does not
select the scientific hypothesis, model, initial conditions, parameters,
diagnostics, acceptance thresholds, or conclusion.

## Execution contract

- Use FLASH only when the operator/campaign advertises an installed capability
  through its manifest or a qualified hosted tool registry. Do not invent a
  capability name or assume this skill includes an executable.
- Keep programs, parameter files, analysis, and outputs in the writable
  workspace. Capability action paths are workspace-relative; the runtime may
  map that workspace to another path only during execution.
- Treat the exact executable identity, compiled unit selection, runtime
  parameter file, launcher configuration, and analysis source as provenance.
- Use `stage="exploration"` with minimal mode's `lab.run`, or `stage="workbench"`
  with classic campaign tools, while repairing inputs, checking the interface, or
  qualifying a model. A workbench artifact is permanently non-evidentiary.
  Use `stage=evidence` only with a frozen, prospectively commissioned program
  and command set under the harness evidence rules.
- Treat a zero process exit status as execution success only. It does not
  establish physical validity, numerical convergence, or support for a claim.
- Follow the operator's source-access authorization. When inspection through the
  configured model provider is authorized, read the installed source to understand
  interfaces and numerical implementation. Protect the reference with filesystem
  permissions; write problem files or experimental patches in a separate workspace.
  Source inspection is not permission to publish or redistribute it. The public
  skill contains no FLASH-owned source or binary.

## Recommended use

1. Translate the active claim into observables, a falsifier, and a model class.
   Read [model validity](references/model-validity.md) before deciding whether
   ideal MHD, resistive MHD, Hall/extended MHD, or a non-FLASH instrument is
   adequate.
2. Confirm that the advertised capability was built with the required solver,
   geometry, material properties, transport terms, equation of state, and I/O.
   Runtime switches cannot activate code omitted at build time.
3. Develop an inexpensive workbench case that exercises the intended compiled
   path and diagnostics. The neutral
   [runtime smoke](examples/runtime_smoke.py) checks an operator-supplied test
   parameter file, MPI execution, and HDF5 readback; it never qualifies a
   scientific calculation.
   For evolution, start with the solver's adaptive CFL timestep and qualify its
   accuracy through the relevant physical window. Commissioning caps are examples,
   not fixed production settings. Read [adaptive stepping](references/adaptive-time-stepping.md)
   when a small timestep or unfinished trajectory dominates the wall budget.
4. Before freezing an expensive evidence command, run short, distinct,
   non-evidentiary timing pilots at representative resolution. Separate fixed
   startup/checkpoint cost from marginal evolution cost, benchmark plausible
  MPI/OpenMP topologies, and leave enough wall-time and workspace margin for
  the complete output transaction. Do not assume that more ranks are faster.
   Test the exact experiment launcher at the intended rank count. For single-node
   Open MPI, use `SIMJECTURE_MPI_HELPER` with `--ranks`. When a study execution pool
   is configured, reserve that many CPUs through `lab.run(resources=...)`. For a
   local study without an execution pool, omit `machine` and `resources` and use
   the capability's commissioned launcher. Do not hide a slot-allocation failure with
   oversubscription. A PRoot smoke may pass while larger collectives hang. Record
   that failure separately from hardware throughput. Compare native execution
   only when an operator explicitly configured the trusted process backend.
   Check timestep changes against fields and observables over a representative
   physical window; a startup scalar comparison cannot qualify stagnation physics.
5. Commission the actual representation prospectively. Check geometry,
   coordinates, units, initialization, boundaries, active physical terms,
   diagnostics, and numerical regime. Preserve quantitative metrics behind
   every qualification boolean.
6. Freeze the commissioned input-producing source and parameterized command
   interface. Generate fresh evidence with that identity, retain raw FLASH
   outputs, and perform analysis from recorded files rather than terminal
   prose.
7. Challenge the result with applicable controls and refinement studies before
   adjudication. If the required scale or closure leaves the model's validity
   domain, record the limitation and use a more appropriate instrument.

Read these resources as needed:

- [Guided studies](references/guided-studies.md): reuse a supplied anchor, qualify
  the actual HDF5 reader, distinguish pilots from evidence, and check decision rules
  before expensive campaigns.
- [Cell-centre flux paths](examples/coordinate_paths.py): optional, tested
  quadrature for uniform 2D Cartesian cell-centred magnetic components. It returns
  the average potential on the two central rows, not an exact value at the
  continuum midplane. It is not an AMR, staggered-face or RZ reader and chooses no
  scientific observable or acceptance threshold.
- [Execution and output](references/execution-output.md): command construction,
  provenance, output inspection, and failure handling.
- [Hosted HDF5 analysis](references/hosted-analysis.md): scratch/project file
  persistence, raw-output archives and single-block magnetic-field plotting.
- [Model validity](references/model-validity.md): fluid-model scope and
  qualification checks, including the limits of FLASH Hall physics.
- [Local deployment](references/local-deployment.md): operator-side acquisition,
  build, validation, and license-safe capability exposure.
- [Private install overlay](references/private-install.md): host-local bootstrap
  for `simjecture install flash --source` without publishing FLASH.
- [Runtime smoke](examples/runtime_smoke.py): a materializable, permanently
  non-evidentiary executable/hash/output health check for an already prepared
  FLASH test input.

Official resources:

- <https://flash.rochester.edu/site/flashcode/>
- <https://flash.rochester.edu/site/flashcode/user_support.html>
- <https://flash.rochester.edu/site/flashcode/user_support/flash_ug_devel.pdf>

## Boundaries

Do not infer that a fluid calculation is adequate merely because FLASH is
available. Do not turn a runtime smoke, visual resemblance, stable completion,
or a single resolution into scientific qualification. Never take hypothesis
parameters, expected outcomes, fit ranges, or decision thresholds from this
skill; derive or retrieve them within the active campaign and preserve their
provenance. Do not silently change the physical model, normalization,
observable, or numerical policy after inspecting results.
