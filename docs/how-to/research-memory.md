# Research memory and experimental comparisons

Minimal mode provides optional research memory, a bounded recovery brief, and scalar
comparisons over recorded outputs. Native tools remain available. These helpers impose
no experiment ordering and do not add an approval step.

## Preserve the distinction between measurements and explanations

```python
from lab import lab

observation = lab.note(
    "No onset was measured before t=8.",
    kind="observation", experiments=["exp_recorded_id"],
)
interpretation = lab.note(
    "Numerical diffusion and a physical pressure barrier remain competing explanations.",
    kind="interpretation", experiments=["exp_recorded_id"],
)
question = lab.note("Is the current layer resolved?", kind="question")
```

Notes are worker statements, not approved facts. Experiment links must reference real
receipts and retain their execution-binding fingerprints. Literature can be linked through
`sources=["https://..."]`; these references are not automatically verified. Notes cannot
accept a claim, waive operator requirements, or replace recorded evidence.

Correct a note by submitting a new note with `supersedes=old_note["id"]`. The previous
entry remains available. Use `kind="implementation"` for a code correction, keeping it
separate from a change in the scientific hypothesis. Hypothesis repairs still use the
existing `lab.commit` and independent review rules.

## Write down what an experiment can distinguish

```python
plan = lab.note(
    "Refine the mesh while holding the physical setup fixed.",
    kind="next_test",
    alternatives={
        "numerical diffusion": "the onset changes appreciably with resolution",
        "physical barrier": "onset and magnetic pressure converge together",
    },
    estimated_seconds=600,
)
receipt = lab.run(
    "calculation.py", outputs=["result.json"],
    parent_experiment="exp_recorded_id", purpose="diagnostic", plan=plan["id"],
    stage="exploration",
)
```

The predictions above are illustrative, not sufficient reconnection diagnostics. The
agent selects and justifies the actual discriminating test. Estimated cost is advisory;
it neither reserves resources nor extends the deadline. Notes link intentions to attempts,
while receipts retain what actually ran. Purpose labels are optional: `baseline`, `debug`,
`diagnostic`, `comparison`, or `validation`. They are not enforced stages. A failed
execution is not automatically a physical counterexample, and a debug branch is not a
repaired hypothesis.

## Compare recorded values without retyping them

```python
comparison = lab.compare(
    ["exp_baseline", "exp_refined"],
    {"onset": ["result.json", "onset.reconnection_onset"],
     "divergence": ["result.json", "final_state.divb_max_scaled"]},
)
```

The helper checks the selected output hashes and uses Simjecture's existing JSON path
parser. It returns each scalar with its experiment, artifact hash and path. A failed job,
missing field, invalid JSON, and a recorded `null` remain distinct. None becomes a zero
or a claim disposition. Invalid or non-finite JSON must be corrected through a new
recorded analysis, not by editing old outputs. Large/binary data needs a compact recorded
analysis first. The helper does not choose a "best" scientific result from a scalar.

## Resume from compact state

`lab.brief()` produces a bounded JSON view (default 16,000 UTF-8 bytes) of the immutable
hypothesis, independent review state, active jobs, recent attempts, unresolved questions,
proposed tests and missing committed cases. Dropped entries are counted explicitly;
full records remain accessible. Long hypotheses are labelled as abridged and remain in
the original guide/manifest. Notes remain labelled as unreviewed.

The host writes `research/RESEARCH_BRIEF.md` and `research_brief.json` at checkpoints.
New/recovered native sessions are directed to the brief instead of the full transcript.
Updating this generated file does not count as research progress. Full receipt status
remains available through `lab.status()`, and history through
`lab.notes(limit=20, offset=0, kind="observation")`.

`experiments.tsv` provides an automatically generated attempt ledger, including failed
runs, source hashes, argument lists, parent links and measured execution time. It records
all attempts rather than deleting unsuccessful branches. Timing is execution timing,
not total agent/provider/build cost.
