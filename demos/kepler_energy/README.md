# Kepler orbit: counterexample, repair and fresh validation

This minimal-mode study falsified an energy-only accuracy claim, then obtained
independent support for a narrower four-case claim using fresh experiments.
Read the [illustrated walkthrough](../../docs/demos/kepler-energy.md) for the
question, measurements, review decisions, attribution and limitations.

- `hypothesis.txt` and `instructions.txt`: operator inputs for a new study.
- `record/manifest.json`: exact source, model and dependency identities,
  outcome, usage, export scope and file hashes.
- `record/experiments/`: original receipts, code, numerical arrays and plots.
- `record/commitments/` and `record/reviews/`: prospective repairs and verdicts.
- `record/STUDY_LEDGER.md`: the generated evidence summary.

Verify the retained record from the repository root without a model call:

```bash
uv sync --frozen
uv run python demos/kepler_energy/verify_record.py
```

Run the original twelve-case numerical experiment again in a new directory:

```bash
uv run python demos/kepler_energy/reproduce.py \
  --experiment exp_70ff32e6d28ef9ccd7312295 \
  --output artifacts/kepler-reproduction
```

Regenerate the documentation figure from the original arrays:

```bash
uv run python demos/kepler_energy/plot_results.py
```

Verification checks the record; reproduction executes the numerical program.
Neither starts a new agent study or establishes a new reviewed verdict. Follow
[the first-study tutorial](../../docs/getting-started/first-run.md) to do that.
