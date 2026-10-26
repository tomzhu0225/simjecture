# Research plan preview and confirmation

Deployment and runtime startup checks do not authorize a scientific calculation.
The user may supply the protocol or ask the assistant to draft it. Before any
solver call, show the full effective plan and obtain approval of its displayed
SHA256. The user/operator then records that approval; an assistant must not infer
it from successful deployment or manufacture a real user's approval during tests.
An existing confirmation can be reused for exactly the same plan/source/protocol.
Changes require a new preview and confirmation.

## One shared flow

From the locked project environment (no solver runs during plan/confirm):

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py plan \
  --case demos/qe_dft_reference/case.json \
  --protocol demos/qe_dft_reference/PROTOCOL.md --plan qe-plan.json --convergence
```

Read qe-plan.json with the user: protocol text, material/PP/functional, effective
parameters, parameter_sources, steps, expected_products, inactive_parameters,
algorithmic thresholds, physical acceptance,
controls, numerical accuracy semantics, QE implicit choices and launcher limits.
Amend the case/protocol if needed and create a new plan filename. After the user
explicitly approves the displayed hash, record it (substitute the actual hash):

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py confirm \
  --plan qe-plan.json --expect-sha256 DISPLAYED_SHA256 \
  --confirmed-by USER_OR_APPROVAL_RECORD --confirmation qe-confirmation.json
uv run python scripts/run_qe_in_simjecture.py \
  --case demos/qe_dft_reference/case.json \
  --protocol demos/qe_dft_reference/PROTOCOL.md \
  --plan qe-plan.json --confirmation qe-confirmation.json \
  --pseudo-dir demos/qe_dft_reference/pseudo --output artifacts/qe-new
```

PP fetching and version/preflight checks are non-scientific preparation and do
not require this confirmation. Fetch separately as described in deployment docs.
Do not rerun old output directories. The same confirmed inputs are sealed into
the sandbox and guided package; a guided replay checks the same plan again.

The preview defaults to backend simjecture. A sandbox plan cannot be used by
a standalone process, and the launcher rejects a standalone plan. Standalone
users must preview a separate plan with --backend standalone, then confirm that
hash. Its driver run also requires the plan, receipt and protocol:

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py run \
  --case case.json --protocol PROTOCOL.md --plan plan.json \
  --confirmation confirmation.json --pseudo-dir pseudo --output fresh-result
```

Standalone execution requires QE_BIN/runtime dependencies already available. It
is not sandboxed by this driver; only per-command timeouts apply, and external
host resource supervision is required. The plan explicitly discloses this.
Launcher limits are enforced by Simjecture; differing CLI limits are rejected
until changed in the case and reconfirmed. Confirmation is a trusted local
operator record, not authentication or a cryptographic signature proving who
clicked. It does not replace Simjecture's permissions or scientific-method gates.

## Resolution and supported steps

Precedence: explicit case > selected profile (missing keys only) > CASE_DEFAULTS
and derived electronic settings. This intentionally replaces the former profile
behavior that overwrote explicit values. Existing profiles.small will not lower
explicit meshes/cutoffs: edit a separate case instead. Parameter sources appear
in the preview. Structure, species/PP hashes, functional, nbnd and a full-mode
path require explicit material information; no material or valence is invented.
Default numerical cutoffs/meshes are starting assumptions, not convergence proof.

Supported modes are full (relax, SCF, uniform NSCF/DOS, optional PDOS, bands/path
projections, optional controls) and scf-only. pdos=false disables only uniform
PDOS; path projections remain part of full. Optional case.steps must exactly
match a supported mode. Unknown parameters, conflicting steps, inactive control
settings or unavailable observables are rejected before confirmation/execution.
For SCF-only use --mode scf-only at preview; remove incompatible explicit targets
such as a path gap. For a cheap configuration, copy the case and explicitly set
its cutoffs/meshes. Do not rely on --profile small to overwrite explicit values.

The executable defaults are printed in effective_case/parameter_sources: e.g.
50/400 Ry, 1e-8 Ry electronic threshold, 6^3 SCF/relax and 8^3 DOS meshes when
omitted; nspin and stage occupations are resolved visibly. No universal accuracy
is promised. QE's automatic fixed-occupation SCF band count, neutral default and
symmetry/BFGS choices are separately disclosed. Full case parameters unused in
SCF-only do not add steps.

## Acceptance is separate from completion

Every PW stage still needs normal exit and the appropriate internal convergence
flags. Explicitly failed/interrupted optimization or SCF cannot pass because a
user omitted a physical accuracy target. V2 finite-band/PDOS integrity checks stay.

Protocol prose is retained and shown, not automatically interpreted as constraints.
The user/assistant must translate its explicit steps and precision into the
structured case before confirmation, and review their consistency. The bundled
Si/Fe cases encode their protocol control thresholds explicitly; no material
thresholds are built into the generic driver.

case.acceptance maps supported observables to finite [lower, upper] ranges.
Empty/omitted means physical_acceptance=not_requested; execution may complete,
but no user-specified physical precision has been demonstrated. Unavailable
requested observables fail before execution or when the measurement is missing.
SCF-only can request energy, force and supported spin moments, never a path gap.

Controls may have explicit convergence_acceptance keyed by zero-based control
index, e.g. {"1": {"delta_mev_per_atom": [-2, 2]}}. Collinear cases may also use
"delta_abs_mean_total_moment_muB_per_atom" (difference of absolute per-atom mean
signed total moments). Only requested controls are checked. Missing targets mean
numerical_accuracy=not_assessed, even if control SCFs ran; empty target objects
are rejected. These are user plan targets, not built-in Si/Fe tolerances. Failed
bounds cause failed execution status. Successful targets_checked is limited to
the specified controls, not stress/EoS/global extrema or all-observable accuracy.

## Audit trail

Plan schema qe-plan-1 hashes its complete canonical contents, protocol text/hash
and exact driver bytes. Receipt qe-confirmation-1 records the approved hash,
confirmed_by and time. Both are required by main/run and the launcher before
creating calculation output. Plan/receipt files are never overwritten in place.
Execution records approved_plan_sha256, confirmation, effective_case and plan;
launcher also records discovery/receipt and seals these artifacts for replay.
The historical Si/Fe raw data are unchanged. Fe02 optimization remains withdrawn;
new consent is not new numerical validation or scientific evidence eligibility.
