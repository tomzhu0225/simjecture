# Minimal-mode research API

For the scientific workflow, start with [the research loop](../concepts/research-loop.md)
and [evidence and claims](../concepts/evidence-and-claims.md). This guide documents
the agent-facing operations used by that workflow.

`simjecture study` launches minimal research. The agent chooses its plan, writes
code and uses its tools; the service records evidence and independently reviews
claims. `--workflow minimal` remains an alias for `--mode minimal`.
`simjecture-supervise` and `simjecture-research` use the same launcher.

The browser and TUI launch the same workflow. Native CLI backends and the built-in
API agent (`--backend builtin` with a private `--provider-config`) remain available.
Existing minimal studies preserve their saved contracts and deadlines. Older
classical, DSH, structured and frontier runs remain readable but cannot be resumed;
see [migration](minimal-migration.md). No existing evidence is silently converted.

For installation, a complete launch recipe, and monitoring/resume commands, use
[Run a headless study](headless-studies.md). The backend uses its existing login.
Codex/GLM resume the same native thread; other configured CLI backends preserve the
working folder and evidence state. The wall deadline survives process restarts.
Operator instructions are frozen before experiments and included in every reviewer
packet; changing them requires a new study.

The generated `research/lab.py` offers a small evidence API. Optional
[research memory and comparison helpers](research-memory.md) keep observations,
interpretations and attempts traceable. Instrument-backed studies also use
[methods review](minimal-oversight.md). Core operations include:

```python
from lab import lab

experiment = lab.run("calculation.py", args=["--n", "128"],
                     inputs=["helper.py"], outputs=["result.json"], key="case-128")
state = lab.status()  # Compact receipts; compact=False includes full metadata.
# After the experiment reports succeeded:
request = lab.review([experiment["id"]], "The finite result supports ...",
                     disposition="supported",
                     challenge={"strategy": "Exhaustive finite-domain test",
                                "experiments": [experiment["id"]],
                                "outcome": "Every declared case passed"})
review = lab.review_status(request["id"])
```

`run` returns immediately. You may keep working while jobs execute, or end the model turn; the host then waits for a recorded job to finish before resuming the agent. The service snapshots source and declared local inputs,
records their hashes and arguments, and runs the experiment inside Simjecture's
selected numerical execution backend (Bubblewrap by default; cooperative PRoot
is not a security boundary). An installed capability can be selected
with `capability=NAME`. New studies automatically expose the available installed
tools. Use the advanced Tool access setting, or `--capabilities DIR`, to restrict
them; `--capabilities none` selects Python only. Available tools and the tool
actually used are separate: each receipt binds the selected runtime identity.
Resuming a study keeps its saved registry. Native tools are
available for exploration; execution success alone does not accept a claim.

## Request help and receive helper results

In a study launched with the research director enabled (`--director`), the worker
can request assistance explicitly:

```python
help_request = lab.request_help(
    "The diagnostic disagrees with the reference. Check the reader and numerical method independently.",
    success_criteria="Return a tested reader correction and an independent analysis of the discrepancy.",
    context="Describe observations, attempted fixes, relevant assumptions and unresolved questions.",
    files=["reader.py", "measurements.json"],
    key="diagnostic-help-1",
)
lab.wait("Await the requested independent checks", help_requests=[help_request["id"]])
# End this turn. After the host resumes the worker:
response = lab.help_status(help_request["id"])
```

A new request makes the director eligible immediately instead of waiting for its
normal periodic interval. It still observes provider backoff and the study budget.
The director can return concrete advice through `help_replies`, or assign one or
several `helper_tasks`. Each assignment specifies its request ID, bounded task,
completion criteria, required output filenames and timeout. The worker can keep
doing independent work while helpers run; calling `lab.wait` is optional.

Each helper uses the study's configured worker model/backend in a new context and
its own directory. `CONTEXT.json` contains the requesting worker's explanation,
success criteria, original task, operator requirements, recent notes and evidence
identities. Attached files are snapshotted with hashes under `inputs/`; the
director also supplies recent public worker activity. This is selected context,
not the worker's private reasoning or its entire native conversation. Attach the
specific source, data and explanations a helper needs.

Two helpers may run concurrently by default; additional assignments queue. The
director may set `operating_limits.helper_workers` from 1 to 16; `null` restores
the default of two. Helpers share the existing study deadline and finish before
the protected report period. Their usage is retained separately and included in
the supervisor's token accounting. They are local agent processes; execution
machines for recorded production simulations retain their existing configuration.

### Completion and return

The helper writes `HELPER_RESULT.json` with `status` (`completed` or `blocked`),
`summary`, `artifacts`, `checks`, and `unresolved`. A successful process exit alone
does not complete the assignment. The host checks the result structure, required
deliverables, unchanged context and inputs, and actual output files, then freezes
the returned artifacts with hashes. Failed, timed-out and cancelled jobs remain
visible. A blocked helper may return partial artifacts with an explicit obstacle.

Use `lab.wait(..., helpers=[task_id])` to resume after a particular helper rather
than waiting for the whole group. Help arriving during a worker turn remains pending
until a subsequent turn receives it; unrelated running simulations do not suppress
that wakeup.

A help request becomes `resolved` when advice is available or all its helper jobs
are terminal. This means a response is ready, not that the original problem is
solved. The parent must inspect each helper's status, evidence and limitations.
The host checks artifact integrity; it does not mechanically prove that the
helper fulfilled every scientific or semantic completion criterion.

Returned files never overwrite the parent's working files. Import a selected
artifact explicitly to a new destination:

```python
lab.import_helper_artifact("helper_TASK_ID", "corrected_reader.py", "candidate_reader.py")
```

The import checks the recorded hash and refuses an existing destination. Imported
work remains unreviewed and must pass the normal execution, method and claim
checks before being used as scientific evidence. Helpers may write code and run
bounded local checks; recorded production simulations remain with the parent
worker. Helpers cannot approve claims or launch further helpers through this API.

Requests and assignments are durable and replay-safe. Reusing a request key with
different content is rejected. A controller restart recognizes running helper
processes rather than duplicating them. A dead helper controller produces a
failure receipt; its identified native session, including surviving child processes,
is stopped. Helpers must keep subprocesses in that session rather than daemonizing
or detaching them. Flushed usage counters are recovered after a controller crash;
unavailable counters remain explicitly unknown. Pausing or stopping
the research supervisor cancels its helpers; raw work and completed results remain
available. Supervisor shutdown waits for bounded cleanup and final usage collection.
Private workspaces prevent accidental edit collisions between
cooperative same-account agents; they are not OS security sandboxes.

## Exploratory analysis and advisory progress

`lab.run` defaults to evidence collection. New automatic-tool studies require
methods review for instrument-backed evidence, rather than for merely having
unused tools installed. An explicit operator methods requirement applies to all
evidence, including postprocessing. Older studies keep their whole-study policy.
For diagnostics,
arithmetic validation, or reduction while method approval is pending, use:

```python
analysis = lab.analyze("reader.py", inputs=["recorded-data.json"],
                       outputs=["analysis.json"], parent_experiment="exp_SOURCE_ID")
```

This snapshots source and inputs and retains an exploratory diagnostic receipt.
It cannot authorize a claim or retrospectively promote exploratory results.
Qualify the method and collect fresh evidence before requesting claim acceptance.

Method proposals accept `validation_experiments` and `blocker_experiments` as
lists of actual `exp_...` receipt IDs. The legacy `blockers` field has the same ID
semantics. Put descriptive scientific caveats in `limitations=["..."]`.
Incorrect types identify the failing field; unknown IDs direct the caller to
`lab.status()`.

An optional target links planning to an actual recorded numeric result:

```python
lab.progress(experiment="exp_EVOLUTION_ID", output="result.json",
             path="actual_end_ns", quantity="3D time reached", unit="ns",
             target=20.5, baseline=0, estimate_rate=True,
             series="same-model-grid-seeded",
             limitations=["Startup throughput may change near stagnation"])
```

The host checks output identity and its numeric value. Quantity, unit, baseline,
target and series remain researcher declarations. Use the actual starting time
as the baseline for a restart, and separate grids/geometries/windows into distinct
series. A linear throughput estimate uses this evolution's measured wall time;
it excludes analysis/review and may change with the physics. Do not substitute
postprocessing runtime for evolution cost. Registered targets appear under
**Scientific coverage & cost** in the run monitor's research trace and in worker
and reviewer context. Measured execution costs are also included automatically
when no target has been registered. These are advisory planning signals, not
acceptance criteria or a prescribed phase schedule.

Identical requests reuse the same receipt. Change `key` for an intentional
replicate. Changed source, inputs or arguments produce a new experiment identity.
Result files and raw outputs remain under `experiments/ID/workspace/`; agents can
inspect them but must not modify recorded artifacts. Review rechecks their hashes.
The initial implementation bounds each experiment to 4 GiB and the study to
8 GiB of recorded experiment storage with conservative reservations for active experiments. These bounds do not police arbitrary native working-folder writes.

A review request returns a persistent receipt, independent of the caller's
working directory. End the model turn after submitting it: the supervisor opens
a fresh reviewer context and records the result. Codex reviewers can inspect
relevant source, data and documentation with read-only tools; they cannot modify
recorded evidence. Other adapters retain their configured review restrictions. Missing evidence
returns explicit gaps. A malformed reviewer response never becomes approval.
Each review targets one explicit claim ID and statement; the host rejects a mismatched target. Under the default CLI `repair` completion policy, approval of an original
falsification is distinct from completion, which still requires a supported repair.
The `answer` policy also allows an independently accepted root falsification to
complete the study. The workspace uses `answer` for new studies; saved policies
are retained on resume. Pending reviews survive pauses and deadlines. Scientific approval authority is
not exposed through `lab`.

For a repair, commit the prediction and exact commands first:

```python
plan = lab.commit("A bounded refined claim ...", source="validation.py",
                  cases=[["--case", "a"], ["--case", "b"]],
                  acceptance="Predeclared quantitative criteria ...", inputs=[],
                  parent="root", rationale="Smallest justified change and why ...")
fresh = lab.run("validation.py", args=["--case", "a"],
                outputs=["result.json"], commitment=plan["id"])
# Execute all committed cases, then review their receipts with claim=plan["id"].
```

New studies require evidence of active counterexample search for any supported
claim. The `challenge` identifies the strategy, submitted experiments and outcome;
the reviewer judges whether the tests actually challenge the claim. Boundary cases,
failure-prone regimes or exhaustive finite-domain testing may qualify. There is
no mandatory extra search phase or fixed number of tests.

A repair names its parent (`root` or an earlier commitment ID) and explains why
each changed assumption, scope or bound is necessary. This creates a durable
branching hypothesis tree. A repair's review includes ancestor statements and the
accepted counterexamples' actual source/results. Every ancestor must have an
accepted falsification before a supported descendant can close the study.
Minimality is judged scientifically, not by text length; scope restrictions must
explain failures rather than erase them. Experiment workspaces are immutable
snapshots, not separate Git worktrees for every hypothesis.

The service rejects changed committed source/arguments, retrospective relabelling
of earlier runs and omission of committed cases. The reviewer still must judge
whether the repair is meaningful: a fitted range tested on its own fitting data
is not validated research.

Ordinary calculations do not need a separate instrument-claim hierarchy or an
approval before every calculation. Physical adequacy, controls and convergence
remain scientific obligations and are checked at review. A supported original
claim completes the study; under `repair`, a falsified original requires an
independently supported repair. Under `answer`, a reviewed negative answer can
complete it without that repair. Unresolved evidence and normal model exit do not complete it.

This is a cooperative same-account trust model. The native CLI agent is not
adversarially isolated from host files; host-only Python methods are an interface
boundary, not an OS security boundary. A hostile-worker deployment needs separate
accounts or a separately authenticated service. Numerical execution retains its
selected backend and recorded isolation limits. No existing campaign is migrated automatically.

Native-thread continuation prompts are short; full instructions remain in
`research/RESEARCH_GUIDE.md`. `lab.status()` includes remaining wall time and
receipt/workspace paths, with full metadata available through `compact=False`.
For long solvers prefer separately recorded cases, check a pilot's output schema,
and reserve time for validation and synthesis.

Minimal is the new-study default by operator preference, not because the benchmark
established superiority. The workflow is evaluated against plain, structured and frontier runs;
see [the measured results](https://github.com/tomzhu0225/simjecture/blob/main/research/evaluations/research-service-v2/RESULTS.md) and [benchmark plan](https://github.com/tomzhu0225/simjecture/blob/main/research/evaluations/research-service-v2/PLAN.md).

Latest iteration: [scientific-rule and default-mode tests](https://github.com/tomzhu0225/simjecture/blob/main/research/evaluations/minimal-default/RESULTS.md).


## Watching and controlling a study

A terminal launch prints live activity, backend/model, elapsed/remaining time and
experiment/review counts. Redirected output gets plain periodic status lines;
use `--quiet` to suppress them. Open `simjecture web /path/to/study` or
`simjecture tui /path/to/study` to inspect the same evidence and hypothesis tree.

Pause stops the agent at the supervisor boundary; already recorded numerical jobs
may finish within their existing bounds. Resume retains the original wall deadline
and mode. Cancel and deadline exhaustion terminate verified active numerical
workers. Transient provider failures retry with backoff until the original deadline;
authentication, permission and exhausted-quota failures pause with evidence intact; ordinary agent exit and inconclusive review do not establish completion.
Provider usage is shown when the backend supplies completed-turn counters, with
resumed cumulative counts deduplicated by native thread. Missing usage is not zero.
