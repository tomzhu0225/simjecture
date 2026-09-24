# Learning from existing autonomous research systems — 2026-09-24

This iteration adds optional research memory and experiment comparisons to Simjecture's
minimal mode. It follows inspection of three downloaded source repositories and extends
our existing receipt, artifact verification and JSON-path implementations. It does not
replace the research engine or introduce a multi-agent framework dependency.

## References inspected

The checkouts are retained privately under `.private/references-20260924`. Exact revisions
and inspected paths are recorded in [references.json](references.json).

| Reference | Source observation | Adaptation |
|---|---|---|
| [Karpathy autoresearch](https://github.com/karpathy/autoresearch/blob/228791fb499afffb54b46200aca536f79142f117/program.md) | Compact attempt ledger preserves kept, discarded and crashed experiments; evaluation is protected | Generate experiments.tsv from receipts, keep failed attempts, compare actual recorded values |
| [AIDE](https://github.com/WecoAI/aideml/blob/60b3978ddf65b71f86eb7c64506965048a1398cf/aide/journal.py) | Journal nodes link code, plans, execution, parents and evaluation; distinguishes draft/debug/improvement | Optional experiment parent and purpose links; implementation debugging remains separate from hypothesis repair |
| [AI Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2/blob/96bd51617cfdbb494a9fc283af00fe090edfae48/ai_scientist/treesearch/agent_manager.py) | Experiment manager tracks goals, stage history and progression | Retain pending questions and discriminating tests in recovery context, without adopting its fixed ML stages |
| [Kosmos paper](https://arxiv.org/html/2511.02824v1) | Structured research memory links claims to analyses/literature | Evidence-linked notebook and bounded brief; this is conceptual inspiration, not a Kosmos source integration |

Reference implementations were inspected, not executed or vendored. No source code was
copied into Simjecture. AIDE's checkout is MIT-licensed; the inspected AI Scientist-v2
checkout carries its own AI Scientist Source Code License. These checkouts are not
included in our package. We make no claim to reproduce another system's performance.

## Implemented changes

1. **Optional evidence-linked notebook.** `lab.note` separates observations,
   interpretations, implementation corrections, questions and next tests. Receipt IDs
   must exist and their execution-binding hashes are retained. Notes are explicitly
   worker statements, never independent adjudications. Literature references are stored
   but not automatically verified.
2. **Preserved correction history.** A new note may supersede an earlier one, but the
   earlier entry remains retrievable. Notes cannot silently change the claim they correct.
3. **Discriminating-test plans.** A next-test note can state different expected outcomes
   under competing explanations and an estimated cost. `lab.run(plan=...)` links what
   was proposed to what ran. Cost estimates do not reserve resources or extend deadlines.
4. **Experimental lineage.** Optional parent/purpose metadata separates baseline,
   diagnostic, debugging, comparison and validation attempts. These are labels, not a
   prescribed stage sequence. They neither falsify a hypothesis nor bypass repair rules.
5. **Bounded recovery context.** `lab.brief()` and generated RESEARCH_BRIEF.md preserve
   current claim/review state, active jobs, unresolved questions, pending tests, recent
   attempts and missing cases. The default JSON payload is limited to 16,000 UTF-8 bytes.
   Omitted entries are counted and full records remain accessible. Generated brief
   refreshes are excluded from the progress detector.
6. **Verified scalar comparisons.** `lab.compare` extracts values using the existing
   JSON-path grammar and verifies selected output hashes. Failed executions, missing
   fields, invalid JSON and recorded nulls remain distinct. It does not invent a zero,
   rank a scientific conclusion, or treat a solver exit as physical validation.
7. **Automatic attempt ledger.** experiments.tsv includes source hashes, commands,
   parent links, proposed-test IDs, purpose, execution status and measured execution time.
   Failed and unsuccessful attempts are retained.
8. **Integration into recovery and oversight.** New/recovered workers read the generated
   brief; periodic progress reviews receive bounded research state instead of an
   ever-growing status dump. Native tools and ordinary calculations remain available.

## Measurement and validation

Read-only replay of the completed reconnection study:

| Context | Serialized UTF-8 bytes |
|---|---:|
| Existing compact status | 18,986 |
| Default brief (16,000-byte ceiling) | 4,224 |
| Brief with a 4,096-byte ceiling | 3,649 |
| Brief with a 2,048-byte ceiling | 1,924 |

The default brief is approximately **77.8% smaller in this comparison**. It reports all
24 attempts and their status totals, while retaining 12 recent attempt entries and
explicitly counting omitted entries. This is a context-size measurement, not a token-cost
or scientific-completion-rate improvement. Original manifest, experiment, commitment and
review records were hash-checked before and after replay and did not change.

The comparison helper also detected the original run's non-finite JSON (`NaN`) and its
failed execution. Both were returned as unavailable values with explicit reasons, not
fabricated reconnection-onset values. The old artifacts were not modified.

Regression coverage includes persistent notes, supersession, invalid references,
pre-existing test plans, debug lineage, idempotent retries, optional-memory compatibility,
old unanswered questions surviving many newer notes, bounded UTF-8 output, generated-file
exclusion from progress, failed-attempt retention, JSON paths, non-finite metrics and
artifact tampering. Test counts and the live run are recorded in validation.json. The full local suite passed **629 tests**, with 9 skips for unavailable optional
dependencies/runtimes. The final remote non-root checks passed **32 tests**, and the documentation build passed with warnings treated as
errors. All five changed Python modules on the remote match the tested local source.

A live MiMo v2.6 Pro integration check starts from an explicitly faulty finite arithmetic
baseline, records it as exploration, writes observation/implementation/test-plan notes,
records a corrected child attempt, compares both, inspects the brief, and submits the
correct evidence for independent review. The run completed with independently accepted support in **143.3 seconds**, retaining
both attempts and three linked notes. Available judge usage was **9,640 input + 303 output
= 9,943 tokens**. The worker was interrupted for review handoff and supplied no final
usage counter; total run usage is unknown. During the run, queued review state exposed
a null-verdict error in the brief builder. The supervisor recovered and completed the
review; the defect and stale-error display were subsequently fixed, with a regression
covering pending reviews. The result is recorded in validation.json.
This is a functional integration check; its supplied instructions specifically exercise
the new API and do not establish spontaneous adoption on an open-ended research task.

## What we deliberately did not transplant

Autoresearch's fixed training budget is not a universal simulation or agent-turn budget.
Its one-file optimization scope and single scalar metric do not fit general plasma
investigations. AIDE's scalar best-node selection and AI Scientist-v2's fixed ML stages
also need domain-specific justification before use here. Simjecture retains its existing
hypothesis, counterexample, prospective-repair and independent-review rules.

No new long plasma campaign was launched and no public package was published. A
controlled long-duration comparison with plain-agent and earlier minimal-mode baselines
is still needed to measure scientific completion, invalid conclusions, reviewer overhead
and actual token spending. The closed Kosmos/Google systems were not benchmarked or
claimed to be integrated.

See [API usage](../../../docs/how-to/research-memory.md).
