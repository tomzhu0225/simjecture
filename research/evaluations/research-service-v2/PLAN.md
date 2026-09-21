# Research service benchmark v2 (before live agent launches)

Compare plain codex-glm, structured Simjecture, frontier Simjecture and the new
minimal research service, all requesting GLM 5.3. Hold native tools, login and
model constant. Use the current corrected implementation, then freeze it before
launch. This is a workflow benchmark, not a model ranking or a prompt ablation.

Simple tasks: the original finite Euler and midpoint claims, 900 seconds each.
Use task-specific output instructions to remove the previous mixed-schema error.
Use the normal 600-second session/inactivity interval, not the earlier 180-second
stress interval. Two simple tasks times four workflows = eight runs.

Hard task: real operator-installed FLASH 4.8 driven resistive/viscous MHD,
3600 seconds per workflow, same finite case matrix and diagnostic definition.
Freeze the physical protocol after transport and timing calibration, before
launching any hard-task agent. Record executable/input hashes, grid and sampling
convergence, declared controls and a scoped conclusion. Do not equate Ohmic
heating with topological reconnection or generalize to a complete Z-pinch.

At most four agent workflows concurrently. Limit each FLASH run to two MPI ranks;
background reference calculations use at most four further ranks on the 24-CPU
host. Keep per-study storage bounded and preserve the existing Grok investigation.
The first comparison has one run per task/workflow; do not claim statistical
superiority. Preserve failures, provider errors and accounting gaps.

Primary outcome is external scientific deliverable assessment, common to every
workflow: source/outputs actually substantiate the finite conclusion, required
controls and refinements exist, and a falsified claim has a meaningful prospective
repair test. Also report native/kernel/service completion flags separately.
A timestamped observer records benchmark-plan.json and result receipts; the agent
cannot define success just by exiting or setting a boolean. Post-hoc fitted
bounds checked against fitting data do not pass the repair requirement.

Report numerical correctness, scientific sufficiency, task completion, wall time,
worker/reviewer tokens (input, cached input, output), actual solver runtime,
provenance coverage and reasons for failure. Score correct uncertainty explicitly;
unresolved is not completion or false scientific support. Fixed-budget runs and
naturally completed plain runs are not equivalent accepted outcomes.

No DSH or alternative-model speed claims follow from this GLM-controlled matrix.
Additional backends can be added as separately identified experimental factors.

Transport note: after freezing the simple matrix, the hard-matrix implementation adds stdin transport for Codex prompts larger than48KB, avoiding the OS per-argument limit. Scientific instructions are unchanged by this transport fix. Each matrix records its own complete source hashes. Independent external grading is recorded separately from in-budget workflow reviewers and may overlap live runs; shared-provider load is a limitation of timing comparisons.

Hardware correction: the first plasma attempt was invalidated after live process
inspection showed native OpenMPI ranks pinned to CPUs0-3 while sandboxed ranks
could use CPUs0-23. All benchmark-owned trial processes were stopped; the unrelated
Grok study was preserved. The corrected plasma matrix gets fresh full 3600-second
budgets, fresh contexts and explicit binding_policy=none in both driver and capability
environments. Scientific parameters and decision thresholds are unchanged. Preserve
the aborted attempt and its token usage as setup overhead, not as workflow failures.
Completed reference field solutions may be reused because their numerical model,
rank count and parameters are unchanged; a repeated case checks numerical consistency.

Post-freeze hardening in the development tree (not attributed to timed benchmarks): source review includes the entry script regardless of extension and rejects oversized code; input snapshots use streaming copies and precheck storage bounds; non-GLM CLI backends require an explicit model; the full operator protocol is frozen before experiments and included in every scientific review. The external benchmark grader already sees the original full task protocol, but the frozen minimal supervisor only supplied the root hypothesis to its internal reviewer. Report this limitation; do not claim the later fixes were benchmarked in the timed matrix.

Current-revision follow-up: the prototype minimal plasma run was superseded at1183seconds after the agent grouped14cases (~3.7GB raw output) into an experiment with a hidden2GiB cap. Its tokens and partial work remain recorded. The current service uses4GiB per-experiment /8GiB per-study dynamic reservations, visible limits, full-protocol review binding and job-aware waiting. It receives a fresh3600-second plasma run in plasma-current, staggered later than the other three arms. A sequential current-revision Euler/midpoint follow-up runs when a workflow slot becomes free. Do not claim a strictly simultaneous timing comparison for this revision.

Grading audit: the first structured-midpoint packet omitted its actual legacy execution receipt and was rejected partly on that basis. The receipt exists, its source hash matches, and an independent rerun reproduced every row. The corrected packet was accepted under the common scientific-evidence standard. Preserve the first assessment; do not alter its legacy ledger eligibility. Filename compliance, evidence adequacy and native/kernel termination are reported separately.
