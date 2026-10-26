# Magnetic bcc Fe example: historical full qualification withdrawn

The archived Fe02 optimization did not converge (exit_status=3/opt_conv=false).
It is an incomplete historical case, not a passed relaxed-structure benchmark.
See [current archive status](record/full_reference/CURRENT_STATUS.md); the old
archival README/comparison retain historical claims, not current qualification.
No new full calculation has been performed after the integrity fixes.

This case exercises the same material-configured capability, launcher, workflow,
parsers and plots as Si. It provides no Fe-specific solver adapter. Read
PROTOCOL.md and REFERENCES.md; actual results and limits are recorded in VALIDATION.md.

From the locked project environment with QE deployed:

Before the run, preview this material's effective plan. This is not a new
calculation or approval of the historical result. After the user approves the
full displayed contents/hash, record that exact confirmation:

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py plan \
  --case demos/qe_fe_reference/case.json --protocol demos/qe_fe_reference/PROTOCOL.md \
  --plan qe-plan.json --convergence
# Read qe-plan.json with the user; only after approval:
uv run python skills/quantum-espresso/examples/dft_workflow.py confirm \
  --plan qe-plan.json --expect-sha256 DISPLAYED_SHA256 \
  --confirmed-by USER_OR_APPROVAL_RECORD --confirmation qe-confirmation.json
```

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py fetch \
  --case demos/qe_fe_reference/case.json --pseudo-dir demos/qe_fe_reference/pseudo
uv run python scripts/run_qe_in_simjecture.py \
  --case demos/qe_fe_reference/case.json --protocol demos/qe_fe_reference/PROTOCOL.md \
  --pseudo-dir demos/qe_fe_reference/pseudo --plan qe-plan.json --confirmation qe-confirmation.json --output artifacts/qe-fe
uv run python demos/qe_fe_reference/analyze_reference.py artifacts/qe-fe/workspace/result
```

Use a fresh output directory. For SCF-only, create a case copy with explicit cheap parameters and compatible acceptance,
then preview --mode scf-only. Profiles only fill missing fields.
The first implemented modes are configurable scalar/collinear spin and fixed,
smeared or uniform tetrahedron occupations. Numerical coverage is case-specific;
SOC/noncollinear, constrained two-Fermi and advanced-functional paths have the
concrete gaps listed in the skill reference, rather than a ban on material names.

The analyzer now reassesses optimization/SCF evidence, not just summary labels.
It writes a new fe_reference_reassessment.json, refuses existing output paths,
and exits nonzero for failed or missing completion evidence. --output chooses a
new report path; --relax-xml can explicitly supply preserved optimization XML
when a compact archive omitted it. The XML must pass completion and match the
analyzed final geometry. Missing proof cannot restore a full pass.
