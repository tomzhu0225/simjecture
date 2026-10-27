# Reproducible Si example for the QE capability

This directory contains the material-specific case and research protocol.
The reusable contribution lives in `skills/quantum-espresso/` and is configured
for each material. Read PROTOCOL.md and REFERENCES.md before interpreting results.

From the repository's locked application environment:

Before the run, preview this material's effective plan. This is not a new
calculation or approval of the historical result. After the user approves the
full displayed contents/hash, record that exact confirmation:

```bash
uv run python skills/quantum-espresso/examples/dft_workflow.py plan \
  --case demos/qe_dft_reference/case.json --protocol demos/qe_dft_reference/PROTOCOL.md \
  --plan qe-plan.json --convergence
# Read qe-plan.json with the user; only after approval:
uv run python skills/quantum-espresso/examples/dft_workflow.py confirm \
  --plan qe-plan.json --expect-sha256 DISPLAYED_SHA256 \
  --confirmed-by USER_OR_APPROVAL_RECORD --confirmation qe-confirmation.json
```

```bash
uv run simjecture install quantum-espresso --jobs 1
uv run python skills/quantum-espresso/examples/dft_workflow.py fetch \
  --case demos/qe_dft_reference/case.json \
  --pseudo-dir demos/qe_dft_reference/pseudo
uv run python scripts/run_qe_in_simjecture.py \
  --case demos/qe_dft_reference/case.json \
  --protocol demos/qe_dft_reference/PROTOCOL.md \
  --pseudo-dir demos/qe_dft_reference/pseudo \
  --plan qe-plan.json --confirmation qe-confirmation.json --output artifacts/qe-si
uv run python demos/qe_dft_reference/analyze_reference.py \
  artifacts/qe-si/workspace/result
```

The launcher uses actual Simjecture skill/capability discovery and its Bubblewrap
sandbox. It runs no paid models. Its discovery.json and execution_receipt.json
identify exactly what executed. A successful run generates a guided package for
the repository's existing model-free readiness command.

The separate Si analysis reports conventional lattice constant, sampled indirect
gap, Gamma direct gap, Gamma-to-X endpoint transition and the declared energy
controls. The public references use different implementations/PPs, so they
provide physical context; same-PP convergence is assessed separately.

Pseudopotentials are fetched by URL and hash, not redistributed as Apache code.
The GBRV file is GPL-3.0 per its author site. Retain its license if redistributing
a prepared local guided package. Exclude wavefunction checkpoints and package
environments from contributions.

Current analysis requires optimization and final-SCF XML completion evidence,
bound to the final geometry. Compact archives without optimization XML are
unqualified until explicit --relax-xml evidence is supplied. Reports now use
si_reference_reassessment.json (or --output), refusing overwrite. Historical
si_reference_comparison.json is preserved, not refreshed in place.
