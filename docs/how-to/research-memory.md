# Research memory and experimental comparisons

Minimal mode automatically maintains an experiment journal and supplies a bounded
journal view directly in every research prompt, including fresh and recovered sessions.
This follows the controller-managed journal pattern used by AIDE. The researcher need
not invoke a recording helper or open a file to receive current history. Native tools
remain available; no experiment ordering or additional approval step is introduced.

## Automatic controller work

For every recorded attempt the host retains source/input and runtime identities, command
arguments, execution outcome and timing, bounded failure diagnostics, and hash-checked
scalar result excerpts. Excerpts are reported values, not scientifically validated facts.
The original receipts and full artifacts remain authoritative. Full projections live in
`journal/attempts/`; retained checkpoint summaries live in `journal/summaries/`.

Attempts sharing an entrypoint are linked chronologically, and implementation changes
are detected from source/dependency/runtime hashes. These links are explicitly labelled
as chronology rather than inferred causal or hypothesis relationships. Explicit worker
parent links remain distinct.

After a batch of results, an implementation change or session recovery, the controller
may run a short tool-free synthesis using the configured reviewer model. It records
observations, provisional interpretations, open questions and useful next tests with
validated receipt references. This is **unreviewed memory**, not scientific adjudication.
It cannot accept or falsify claims and does not write authoritative hypothesis records.

Synthesis is limited to 45 seconds per invocation, at least five minutes between attempts,
and a cumulative budget of the lesser of 300 seconds or 3% of the study's wall budget.
A minimum 15-second allowance and 90 seconds of remaining wall time are required before
launch. Small tasks use deterministic journal entries alone. Claim/method reviews take
precedence. Provider, format or citation failures defer synthesis; they never discard the
journal or stop the researcher. Existing process-shutdown grace still applies.

The worker-facing context is capped at 6,000 UTF-8 bytes, with omissions and full-record
retrieval paths visible. The separately generated brief defaults to 16,000 bytes. Neither
requires the agent to choose a memory tool. The following optional helpers enrich this
automatically maintained record.

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
New/recovered native sessions receive bounded current state directly in their prompt.
Updating this generated file does not count as research progress. Full receipt status
remains available through `lab.status()`, and history through
`lab.notes(limit=20, offset=0, kind="observation")`.

`experiments.tsv` provides an automatically generated attempt ledger, including failed
runs, source hashes, argument lists, parent links and measured execution time. It records
all attempts rather than deleting unsuccessful branches. Timing is execution timing,
not total agent/provider/build cost.
