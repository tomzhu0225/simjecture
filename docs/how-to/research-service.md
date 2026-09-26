# Agent-owned research: minimal mode

`simjecture study` defaults to minimal mode for new native-agent studies. The
native agent chooses its plan, writes code and uses its existing tools; the
service records evidence and independently reviews claims. Select `--mode
structured` or `--mode frontier` to use the other workflows. `--workflow` is an
alias for `--mode`. The `simjecture-supervise` and `simjecture-research` entry
points use the same launcher.

Resume without a mode flag to retain the recorded mode. Changing a study's mode
requires a new campaign directory; no existing evidence is silently converted.
Old studies retain their existing scientific-policy schema. The browser and TUI
launch and monitor minimal, structured and frontier native-agent studies. Select
mode and backend separately. DSH/API remain explicit legacy choices; selecting an
unsupported combination returns an error rather than silently changing modes.
The `mvp` command remains the legacy API entry point.

```bash
simjecture study --campaign /absolute/path/to/new-study \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

From a checkout use `python -m conjecture_solver.research_supervisor` with the
checkout's `src` on `PYTHONPATH`. The backend uses its existing login. Codex/GLM
resume the same native thread; other configured CLI backends preserve the working
folder and evidence state. The wall deadline survives process restarts. Operator instructions are frozen before experiments and included in every reviewer packet; changing them requires a new study.

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
existing Bubblewrap numerical sandbox. An installed capability can be selected
with `capability=NAME`. Supply its manifest directory using `--capabilities` or
the numerical instrument registry field in the browser/TUI. With no registry,
minimal exposes only the Python numerical sandbox. Its identity is bound to the receipt. Native tools are
available for exploration; execution success alone does not accept a claim.

Identical requests reuse the same receipt. Change `key` for an intentional
replicate. Changed source, inputs or arguments produce a new experiment identity.
Result files and raw outputs remain under `experiments/ID/workspace/`; agents can
inspect them but must not modify recorded artifacts. Review rechecks their hashes.
The initial implementation bounds each experiment to 4 GiB and the study to
8 GiB of recorded experiment storage with conservative reservations for active experiments. These bounds do not police arbitrary native working-folder writes.

A review request returns a persistent receipt, independent of the caller's
working directory. End the model turn after submitting it: the supervisor opens
a fresh, tool-free reviewer context and records the result. Missing evidence
returns explicit gaps. A malformed reviewer response never becomes approval.
Each review targets one explicit claim ID and statement; the host rejects a mismatched target. Approval of an original falsification is distinct from completion of the study, which still requires a supported repair. Pending reviews survive pauses and deadlines. Scientific approval authority is
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
claim completes the study; a falsified original requires an independently
supported repair. Unresolved evidence and normal model exit do not complete it.

This is a cooperative same-account trust model. The native CLI agent is not
adversarially isolated from host files; host-only Python methods are an interface
boundary, not an OS security boundary. A hostile-worker deployment needs separate
accounts or a separately authenticated service. Numerical execution retains its
existing sandbox. No existing campaign is migrated automatically.

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
