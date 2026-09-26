# Methods and progress oversight in minimal mode

Minimal mode keeps planning, native tools, search, coding and exploratory calculations
with the worker. The host owns acceptance, provenance, deadlines and independent
review. A successful numerical process is not a supported scientific result.

New studies with installed capabilities require a short, source-bound methods review
before recorded **evidence** runs. Existing studies keep their saved policy. Ordinary
calculations without installed capabilities do not acquire a mandatory methods hierarchy.

## Commission, review, collect evidence

Use `lab.run(..., stage="exploration")` for commissioning and debugging. Exploration
receipts cannot be retrospectively relabelled as claim evidence. Then submit:

```python
method = lab.method(
    source="calculation.py",
    inputs=["diagnostics.py"],
    capability="flash-my-application",
    model="Resistive MHD; declared closure and neglected terms",
    geometry="Physical axes, domain, initial state, boundary conditions",
    observable="Operational definition of the measured event and falsifier",
    validation="Actual evolution benchmark, conservation and refinement evidence",
    rationale="Why this instrument; observed blockers versus anticipated difficulty",
    validation_experiments=["exp_commissioning_id"],
    blockers=[],
)
```

End the native turn so the host can review the proposal. The host also detects a
durable request and takes over after a short grace period if the CLI keeps running. `lab.status()` includes
its verdict. An approved method permits `lab.run(..., method=method["id"],
stage="evidence")`; it does not accept a scientific conclusion. Changes to its source,
listed dependencies or runtime identity require a revised proposal. Parameter cases
can vary under the same implementation; the later claim review checks their scope.

The reviewer receives frozen source, commissioning source/results, the original task,
and operator requirements. It should distinguish an isolated operator test from a
benchmark that evolves the actual solver. Physics validity remains a scientific
judgment; this is not an automatic proof of solver correctness.

## Optional explicit operator requirements

Pass `--requirements-file requirements.json` when launching a minimal study:

```json
{
  "require_method_review": true,
  "required_capability_prefixes": ["flash-", "warpx-"]
}
```

The requirements become immutable study state. Evidence must use a registered capability
whose name matches a listed prefix. Neither the worker nor the methods reviewer can
waive this rule. Prefix matching checks the selected runtime identity, not the physics
inside a binary; methods and claim reviews remain necessary. Native tools and exploration
are still available. Changing explicit task requirements requires a new study.

## Building a new runtime

An operator-authorized builder can produce a new capability descriptor. Place it in the
study's configured capability directory, then call `lab.register_capability(name)`.
The service appends its hash without replacing any original or previously added identity.
Changing a runtime requires a new name. Registration proves identity, not qualification.
The runtime still needs commissioning and methods review.

Operators may authorize inspection of solver source through their selected provider.
Protect the reference installation with filesystem read-only permissions and use a
separate writable problem/build directory. Include source/build hashes and compiler
logs in the build record. Source-access permission is distinct from publication permission.

## Progress recovery

The host inspects observable actions and durable records after native turns. Two turns
without new work add explicit recovery instructions; at three it starts a fresh native
session, retaining the study, experiment receipts, usage accounting and original deadline.
Repeated nonprogress receives responsive backoff and further bounded recovery.
Private model reasoning is not examined. A distinct action is a progress signal, not
proof of scientific progress; periodic independent review checks the latter.

Minimal workers checkpoint at most every five minutes so one long native turn cannot
postpone host checks indefinitely. Detached recorded experiments continue. Long builds
should use an idempotent builder whose result can be recovered after a checkpoint.
Every fifteen minutes, or during sustained nonprogress (at most once per two minutes),
the host can invoke a separate progress reviewer even if the worker requests no review.
Methods and progress decisions do not complete or falsify a study. Normal uncertainty
continues until the existing deadline or an independently accepted conclusion.

## Results and reporting

Declare raw arrays and compact result documents separately:

```python
receipt = lab.run(
    "calculation.py",
    outputs=["result.json", "history.npz", "snapshots.npz"],
    review_documents=["result.json"],
    method=method["id"],
)
```

If `review_documents` is omitted, compact text outputs are selected automatically.
All artifacts retain hashes; the reviewer sees raw-file metadata, not binary contents.
Use strict JSON (`null` and a reason for undefined statistics), numeric arrays instead
of pickle/object arrays, and periodic on-disk checkpoints. Non-finite JSON and explicit
failed checks are surfaced as output findings, not silently interpreted as scientific
failure or success. Record analysis of raw data if a conclusion depends on it.

The host maintains `STUDY_LEDGER.md` and `research_report.json` separately from agent
notes. They distinguish execution from scientific status, list missing committed cases,
show output findings and include supervision/usage state. Interrupted native turns
may not return token counters; missing usage is explicitly flagged rather than counted
as zero. Runtime estimates for unfinished
validation are heuristics, not reservations or promises. `RESULTS.md` remains the worker's
scientific narrative and should cite receipts and stay consistent with the ledger.

The cooperative execution backend is not a hostile-agent security boundary. Native
work can occur outside the evidence service; important exploratory findings need fresh
recorded evidence. These checks improve observability and acceptance discipline rather
than claiming to intercept every native action or to guarantee a valid discovery.

## Approval conditions and exploratory pilots

New methods/progress verdicts include `prerequisites`, an explicit list of unmet
conditions. `continue` requires an empty list. Conditional approval is rejected and
must be reviewed again; a recommendation for subsequent work is different from a
condition required to make the present approval valid.

Label timing and rank-comparison pilots with `purpose="timing"` or `purpose="parity"`
and `stage="exploration"`. Reviewers receive those labels; such pilots are not claim
tests. Missing purpose is unknown, not an inferred scientific objective.

The host's recorded stage controls evidence eligibility. A JSON output containing
`scientific_evidence_eligible=false` is preserved and flagged for independent review;
it does not itself force a solver rerun. Explain whether it is stale metadata or a
real limitation. Exploration still cannot become claim evidence, and artifact hashes
are still checked. This does not allow rewriting previous results.

## Checking numerical repair bounds

For conjunctive inclusive bounds, supplement the prose acceptance rule:

```python
commitment = lab.commit(
    "A minimally repaired prediction for the rate",
    source="calculation.py",
    cases=[["--S", "2000"]],
    acceptance="Both predeclared bounds on the S=2000 rate must hold",
    numerical_bounds=[
        {"metric": "S2000.rate", "lower": 0.025, "upper": 0.030},
        {"metric": "S2000.rate", "lower": 0.028},
    ],
    rationale="Explain the parent failure and preserve its unaffected predictions",
)
```

Repeated metric names mean AND. Use different names for different cases. Empty
intersections and non-finite bounds are rejected before recording the commitment.
This optional check validates feasibility, not the physics or the measured outcome;
natural-language rules and scientific acceptance still require independent review.
