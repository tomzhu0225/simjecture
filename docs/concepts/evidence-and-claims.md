# Evidence and claims

## Evidence is prospective

A decisive claim requires a contract registered before its evidence-generating
action. The contract states what is observed, how outcomes map to dispositions,
what uncertainty matters, what makes the observation inconclusive, and which
exact program commands may generate evidence.

Agent-authored files and artifacts written while code is still being designed
remain workbench records. They cannot be promoted retroactively. An
execution-generated artifact is only eligible after the process succeeds and,
for detached work, its authenticated job receipt is reconciled as succeeded.
Failed, cancelled, or operationally unknown jobs remain non-evidence even when
they left a plausible partial output.

Every contract also declares its purpose. A `claim_decision` contract tests the
claim's predicted outcome and may support or falsify it. A `terminal_record`
contract records a bounded failure to decide—for example, an unavailable
instrument, an unrealized physical antecedent, or uncertainty that cannot be
reduced within the campaign. Completing that record can justify
`instrument_limited` or `unresolved`; it cannot justify `supported` or
`falsified`. A scientific claim can register a terminal record only after a
tracked prospective attempt under a claim-decision contract, so an agent cannot
skip the scientific test and commission only an excuse for stopping. If the scientific prediction changes, the agent must register a
successor claim rather than rewrite the contract to make failure satisfy it.

## Instruments are claims too

A simulator or analyzer must establish representation, physics controls,
boundaries, diagnostics, and numerical-regime behavior under a commissioned
contract. The supported instrument claim qualifies later bound executions; a
successful process exit alone does not.

## Claim closure

Supported and falsified dispositions require sufficient, validation-passing,
provenance-tracked evidence from one selected `claim_decision` contract version.
When a contract is amended, earlier observations remain visible but cannot
decide the new version; fresh evidence must be generated after that version was
registered. `Unresolved` and `instrument_limited` require a complete prospective
`terminal_record`, so stopping honestly remains auditable without converting a
blocked experiment into support.

The root hypothesis is immutable. A narrower operational child can close under
its own evidence contract without silently changing or overclosing the root.

## Keep the hypothesis tree scientific

A scientific child is a proposition that changes, narrows, repairs, or competes
with a physical prediction and can become the next falsification target. An
established formula, observable definition, numerical method, or implementation
cross-check normally belongs in the parent's evidence contract rather than in a
new `refines` node. If an estimator or diagnostic genuinely needs an independent
audited disposition, it is a `diagnostic_of` validation claim. This keeps the
hypothesis tree from becoming a list of analysis steps.

Finite grid samples do not by themselves establish a universal statement over a
continuous interval. Claims using terms such as “throughout,” “every,” or strict
monotonicity require an analytic argument, a validated enclosure, or an explicit
resolution-bounded scope.

## Counterexample, repair, and adjudication

A qualified counterexample closes the exact scientific claim it violates. The
Scientist role then registers a `repairs` child that cites the motivating
counterexample, explains how the replacement accommodates it, states the
minimal semantic change, and identifies a future falsification condition. The
old counterexample is motivation, not evidence for the repair. The Falsifier
role must register a fresh contract and attack the replacement again.

When a meaningful search finds no counterexample, the acting model cannot
declare its own evidence sufficient. A separate Judge context reviews the
prospective contract, provenance, validation, uncertainty, coverage, and
bounded artifact excerpts. An insufficient judgment returns concrete gaps and
the falsification loop continues while wall time remains. A sufficient judgment
means that the record is complete enough for the Judge's explicit scientific
disposition; it does not mean “supported.” The deterministic gate then checks
that the disposition matches the contract purpose. A complete
`claim_decision` case may close as supported, while a complete blocker record
closes as `instrument_limited` or `unresolved`.

A falsified scientific claim is not a finished frontier by itself. It requires a
minimal `repairs` child that accommodates the counterexample and becomes the
next falsification target. Wall-time exhaustion may bound an open investigation,
but it never becomes support.

## Auditability is not infallibility

The ledger preserves exactly what rule the agent chose and how it applied that
rule. A scientist can still choose an underpowered uncertainty design or
overstate the interpretation. The independently reviewable record makes that
error visible and prevents it from being confused with missing provenance.

Historical campaign artifacts are immutable. Later software may continue to
read legacy adjudications that lack an explicit scientific disposition, but it
must label them as legacy records and must not infer support in the user
interface. A correction is appended as a separate audit record with hashes of
the original artifacts; the original ledger and report are never silently
rewritten.

Use `simjecture corrective-audit RUN --reviewer NAME --finding TEXT
--corrected-interpretation TEXT --artifact mvp_report.json --artifact
hypothesis_ledger.json` to append that hash-chained record.
