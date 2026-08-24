# Guided commissioning

Use guided commissioning when constructing a trustworthy starting simulation is
expensive but a validated anchor already exists.

The package declares:

- the capability and exact successful command;
- supplied files and their hashes;
- a compact validation summary;
- an optional concise protocol named by `protocol_path`, containing the
  prospective command sequence, diagnostics, controls, and stopping rules;
- limitations and permitted reuse;
- the operator statement describing what was validated.

Run with:

```bash
uv run simjecture mvp \
  --hypothesis-file hypothesis.txt \
  --guided-commission guided_commission.json \
  --output artifacts/guided-campaign
```

The harness snapshots the input package outside the writable workspace. The
workspace copy may be inspected or revised, but the original handoff remains
recoverable.

Guided material is a starting instrument, not scientific evidence for the new
hypothesis. The agent must still register prospective contracts, commission any
new or changed program, and execute fresh claim-bearing observations.

Omit `--guided-commission` for a skills-only commissioning baseline. Supply it
when the research question should begin from an expert-validated instrument or
protocol. Reports preserve which mode was used, so guided and unguided runs can
be compared without presenting them as the same level of autonomy.

Validate package structure against
`schemas/MVPGuidedCommissioningSpec.schema.json` before an expensive launch.
