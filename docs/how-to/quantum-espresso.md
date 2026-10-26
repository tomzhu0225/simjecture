# Quantum ESPRESSO DFT

The optional QE capability supplies PW, DOS, band and atomic-projection tools.
The first supported environment is Linux/WSL2 x86_64 with a fixed conda-forge
QE 7.4 build and hashed dependency lock. It provides material-configured scalar and collinear DFT, including fixed
and metallic smeared occupations. Si and Fe are separate research configurations;
implementation coverage and actual numerical validation are reported separately.

## Deploy and check

From a source checkout with its locked application environment:

```bash
uv run simjecture install quantum-espresso --jobs 1
uv run simjecture doctor --profile quantum-espresso
```

Windows users can run `scripts/deploy_qe.ps1` against an existing WSL distribution.
No Docker daemon is required. Check Windows physical space as well as the Linux
filesystem's reported capacity. Use a Linux-native filesystem for the QE
environment: OpenMPI includes case-distinct links that ordinary Windows-mounted
directories may not preserve. Keep existing research environments unchanged.
Runtime identities, versions, source URLs and checksums are recorded under
`.runtime/quantum-espresso-7.4/share/build-record.json`.

The deployment preflight deliberately starts PW with EOF and requires its exact
missing-input diagnostic and version. This tests executable startup without a
material or PP. It is separate from the actual numerical commissioning below.
OpenMPI is explicitly relocated to the capability's read-only sandbox mount.

## Configure and commission a material

Read the `quantum-espresso` skill and its reference files under `skills/`.
The reusable `examples/dft_workflow.py` takes a JSON configuration for structure,
species/PP mappings, functional, tolerances, meshes, path, empty bands and controls.
It has no default material or valence-band count.

Deployment does not authorize scientific execution. First agree a research protocol
with the user (they may supply it or ask the assistant to draft it). Preview all
effective parameters, defaults and sources, selected steps and acceptance targets:

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py plan \
  --case demos/qe_dft_reference/case.json \
  --protocol demos/qe_dft_reference/PROTOCOL.md --plan qe-plan.json --convergence
```

Read the plan with the user. After explicit approval of the displayed SHA256,
record it with `confirm --plan qe-plan.json --expect-sha256 DISPLAYED_SHA256
--confirmed-by USER_OR_APPROVAL_RECORD --confirmation qe-confirmation.json` using
the same driver. Do not run that command on behalf of a user before they approve.
Explicit case values take priority; profiles only fill missing fields. Numerical
defaults are disclosed starting assumptions, not validated precision. Empty
acceptance means not_requested, and absent control targets mean not_assessed.
See `skills/quantum-espresso/references/research-plan.md` for the complete flow.

The source checkout includes a model-free Simjecture launcher. It discovers the
actual skill and capability, snapshots the supplied configuration and protocol,
materializes the versioned workflow resource, and executes in Bubblewrap:

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py fetch \
  --case demos/qe_dft_reference/case.json \
  --pseudo-dir demos/qe_dft_reference/pseudo

uv run python scripts/run_qe_in_simjecture.py \
  --case demos/qe_dft_reference/case.json \
  --protocol demos/qe_dft_reference/PROTOCOL.md \
  --pseudo-dir demos/qe_dft_reference/pseudo \
  --plan qe-plan.json --confirmation qe-confirmation.json \
  --output artifacts/qe-reference
```

Use a fresh output directory. Preview `--mode scf-only` for an SCF-only plan;
remove incompatible gap targets and explicitly set small-case parameters in a copy.
Profiles never overwrite explicit case values. Unsupported step combinations are rejected. The complete run optimizes the configured cell and ions, performs a new SCF
at the final geometry, and copies its checkpoint to independent uniform-k and
high-symmetry-path branches. DOS/PDOS use only the uniform branch. Band projection
plots require successful k-point, energy-unit and index checks.

Outputs include discovery/source identities, the actual sandbox execution receipt,
raw solver inputs/logs, final structure, parsed summaries, CSV, projections and
plots. Binary checkpoints are local scratch and must stay out of commits.
A guided package, including the same confirmed plan and receipt, is generated
only after the exact calculation passes. Changing its scientific inputs requires
a new confirmation. Reproduce
it with the existing [guided readiness](guided-commissioning.md) command:

```bash
uv run python -m conjecture_solver.research_guidance \
  --guided-commission artifacts/qe-reference/guided/guided_commission.json \
  --capabilities artifacts/qe-reference/capabilities --output artifacts/qe-readiness --wall-seconds 3600
```

## Interpret results

The Si protocol and source comparisons are in `demos/qe_dft_reference/`;
the magnetic metal example is in `demos/qe_fe_reference/`.
The skill workflow reference documents spin, occupation, broadening and energy-zero fields.
Run its `analyze_reference.py` on the completed workspace's `result/` directory.
The case includes cutoff and k-mesh energy controls and broad physical checks.
These do not establish a universal convergence bound or global band extremum.
Different PPs, functionals and lattices do not support absolute-energy comparison.

Deployment, synthetic parser tests, real computation, numerical convergence and
scientific evidence eligibility are different layers. Model-free commissioning
does not run an autonomous agent or qualify new research evidence.
Changing material or physical assumptions requires new numerical qualification.


For a Windows checkout, the conditional setup wrapper selects a new Linux-native runtime
prefix when needed, preserves existing prefixes, and calls the same public
installer and doctor. Optional arguments are -RuntimeBase (absolute Linux path),
-Uv (Linux uv executable), and -ApplicationEnvironment (existing Linux application
environment). It never migrates an existing runtime.


## Conditional setup and known prerequisite gaps

This is automated QE setup on supported Linux/x86_64 or already configured WSL2,
not a verified clean-machine one-click installation. The application environment,
working user namespaces/Bubblewrap, an available uv command (or configured path),
and python3 on PATH must already be usable. Docker is not required.

The QE bootstrap currently calls PATH python3 independently of the interpreter
running Simjecture; if absent, it can fail with exit 127. Missing uv in the QE
wrapper currently surfaces as command-not-found rather than a complete guided
installation step. Simjecture's base installation can prepare uv/Python and may
prepare Bubblewrap on supported Linux systems, but that prerequisite flow is not
fully connected to these QE wrappers. Application-package diagnostics can suggest
uv sync --frozen, and missing QE has its install command; diagnostics are therefore
partial, not entirely absent. A clean second-machine end-to-end deployment has
not been validated. These known gaps are disclosed here rather than silently
installing prerequisites or changing host settings.
