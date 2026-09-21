# Researcher-led Simjecture: first redesign iteration

## Boundary

The model chooses the research strategy, decomposition, methods, and use of
supporting agents. Simjecture owns immutable claims, attributable executions,
prospective contracts, review records, resource accounting, and finalization.
A useful research note, a completed model turn, and an accepted scientific
conclusion are different events.

The existing structured scientist/falsifier/repair workflow remains available.
The opt-in `frontier` workflow gives one researcher the ability to investigate
and repair its assigned hypothesis tree without exchanging role assignments for
each step. It does not add review-recording or finalization tools to the worker.
The kernel still rejects invalid repairs and unsupported claim closure.

## Changes in the first live comparison

- A persistent native thread for codex-glm, resumed by explicit thread ID.
- A persistent research directory and concise continuation prompts.
- A progress-sensitive inactivity watchdog, bounded by the unchanged campaign
  deadline; active work is not cut off solely by a turn interval.
- A researcher role over the original root and its descendants.
- Durable host review requests, preserved across boundary stops and recovery.
- No global freeze of researcher activity merely because a numerical job runs.

The complete change is a bundle in this pilot. One cannot attribute any observed
effect to a single component without further ablation tests. GLM 5.3 is the
requested model for both conditions; these tests do not establish GPT-6 Astra
performance or compare model families.

## What the real Euler pilot exposed

Both conditions calculated correct refinement ratios. The structured workflow
obtained exploratory numbers sooner (~168 seconds vs ~268 seconds), but then
spent five fresh sessions within its 900-second budget without an approved
contract. The researcher retained one native thread across three invocations,
obtained contract approval, and generated fresh, reference-consistent data.
Neither completed the repair-and-review cycle in that budget.

The raw logs identify avoidable interface failures: incorrect operation-ID
prefixes, missing active claim bindings, and array-valued JSON evidence paths.
One reviewer approved the mathematical experiment design, but the deterministic
path checker could not evaluate the array-index paths used by the contract.
This is not a reason to weaken evidence checks. It is a reason to provide a
usable, explicitly defined path grammar and hide transport bookkeeping.

## Follow-up changes motivated by those failures

A scoped Python research client supplies host-issued identity fields, default
claim bindings, administrative research notes, and replay-safe operation IDs.
It does not choose observables, thresholds, input data, scientific outcomes, or
review decisions. Numerical request identities include the program hash and
current contract revision, so changed source or a revised contract does not
silently replay an older run. Named replicate keys permit intentional repeats.

Evidence paths retain existing object-key syntax and add deterministic array
indices (`rows.0.N`, `rows[0].N`, `$.rows[0].N`). No evaluation, wildcard, filter,
negative index, or expression is allowed. The existing scalar/type comparison
and failure-on-missing-data behavior remain intact.

These follow-up changes are not retrospectively attributed to the first pilot.
They require their own regression checks and live exercise before promotion.

## Trust model and limitations

Provider-native tools remain available as requested. The local CLI adapter is
not an OS security boundary against a deliberately malicious agent with the
same host account. A hostile-worker deployment needs account/process separation
and a scoped RPC endpoint. Numerical execution remains sandboxed; cooperative
agents must use the scientific interface for authoritative results. This
redesign does not claim adversarial isolation for unrestricted native tooling.

The code-review workforce inspected files while this prototype was evolving;
its observations are design input, not a controlled A/B result. Its assertion
that no frontier tests existed became stale as tests were added. The review
queue defect was actionable and fixed before the paired pilot launched.

Keep the mode opt-in until broader, replicated tasks show that it improves
accepted scientific outcomes, not merely activity. Follow-on tests should add
larger solver jobs, genuine provider outages, multi-claim work, explicit
censoring, and a direct Astra comparison with the same acceptance standards.
