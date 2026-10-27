# Prospective scientific attention training cycle, 25 October 2026

This development cycle follows the frozen 0.2 interface and 16,000-row procedural
curriculum. The objective is a useful scientific-workflow improvement, with
reusable training functions and a release whose claims match the evidence.
An improvement is an empirical question; unsuccessful runs and comparisons stay
in the record. This protocol is written before scientific candidate selection or
new scientific test collection. Upstream general-benchmark base inference and a
16-update interface-training smoke check have begun; neither is a scientific win.

## Resources and continuity

Use the pinned `internlm/Intern-Decision-4B` revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`. One owned A100-40GB runtime is allocated
under `simjecture-science-20261025`; the observed initial balance was 1,229.53 CU.
The local lease caps this cycle at eight hours and 70 CU, with an independent
local release guard. After the initial completed baseline inference, the operator
reserved this host for other simulations. All subsequent model execution and
physical experiments must run remotely; all weight training must use the A100.
Authorized P40 machines and the separate remote coordinator may run compatible
experiments and orchestration. Every native actor uses a new shared lease: at most 640
starts, four concurrent roles, and twelve starts per continuation. The old lease
and all old studies remain closed and unchanged.

Raw records live in `artifacts/scientific-attention-training-20261025/`.
Code is developed on `research/monitor-coprocessor`; PR 46 stays draft during
research. Separately reproducible upstream problems receive separate PRs.

## Training and input integrity

The student receives only a causal observation and its declared decision schema.
Canonical IDs, generator labels, split membership, future outcomes, utility and
teacher answers are not input features. Scientific choices use five masked
fields: route, question reference, evidence category, primary citation and
optional secondary citation. The route combines a compatible attention action
and support kind. Host admission remains authoritative; malformed or unsupported
outputs are recorded as failures/rechecks, never silently replaced by a successful
rule decision. General decision requests retain their native question schemas.

All masked fields share a causal forward; labels supervise the preceding-token
positions. Targets never replace input masks. The compiler is checked against the
upstream compiler on all 10,751 public accuracy-suite records. Full input lengths
are checked without silent truncation. Language-backbone LoRA is the initial
update method; vision parameters and base weights remain frozen.

Development proceeds through three distinct data layers:

1. Scripted procedural supervision teaches the interface and obvious operational
   conditions. These are preferences, not measured intervention benefits.
2. Scientific state examples encode independently checkable reporting and
   diagnostic relationships, healthy near misses, valid negative results and
   knowledge gaps. Record how labels were obtained and any reviewer disagreement.
   Variants of one underlying case stay in one split. Label-only accuracy is a
   secondary metric, not evidence of improved research.
3. Actual sampled worker continuations can support a measured-return update.
   Preserve exact prompts, all sampled field probabilities, chosen values,
   checkpoint identity, verification and execution receipts. Do not infer returns
   for actions never executed. Synthetic utility is not accepted by the learner.

The initial SFT smoke check is sixteen updates over a 400-row procedural subset.
Subsequent learning rates, steps and mixtures may be selected using development
data only. Record every tried configuration. Save checkpoints and reload them to
verify predictions. Reinforcement updates require nonzero measured return
variation, exact initial behavior reproduction and at most two passes over
logged behavior. A continued-SFT control is required before attributing a gain
specifically to RL rather than additional optimization.

## Scientific-workflow comparison

Use actual native workers and physical WarpX outputs, followed by independent
recomputation of quantities and report checks. A scientific negative result is
valid when accurately reported; changing tolerances or fabricating a successful
result never earns credit. Completion requires worker return and reconciliation
of required feedback, using the previously corrected collector behavior.

Compare no discretionary monitor (with the same explicit-help/deadline fallback),
an unchanged 4B model, a learned candidate, and strong deterministic rules. Give
all comparators the same public observations, cadence, host admission and expert
budgets. Improve the rules using development cases, including quiet expiry,
recovery, source identity and unit consistency; freeze them before test runs.
Retain the earlier generic rules as a diagnostic comparator. An oracle using
private fixture truth can be an upper bound only, never a deployment baseline.

Plan up to 32 fresh configurations per primary arm (128 workflows), with balanced
healthy and problematic conditions and paired task parameters. Randomize arm
execution order and report concurrent load. Final collection may use fewer cases
if commissioning, resource limits or precision make the larger run unjustified;
record that change before inspecting its results. Prior explored mechanisms are
development knowledge. Fresh seeds alone do not establish unseen-mechanism
generalization. Explicitly distinguish interpolation, new wording/configurations
and any genuinely held-out mechanism families.

Primary measurements are independently verified completion, actual native-role
starts, elapsed time through obligation closure, unnecessary expert wakes,
missed actionable problems and detection delay. Count model inference/tool costs
and errors. Report raw components as well as declared utility:
`quality - 0.02 * native_starts - 0.1 * elapsed_seconds / 650`, with additional
penalties of 0.05 per required-feedback miss and 0.02 per actual duplicate wake.
Quality rewards accurate complete reports, not whether all physics checks pass.

Use paired differences and intervals clustered by underlying task configuration.
A claimed clear workflow win requires a supported improvement in completion, or
lower cost/time with completion preserved and no increase in unsafe/protected
edits. Cost-only claims require the paired 95% interval to exclude zero; show
completion uncertainty separately. A small cohort with equal observed success
does not by itself prove noninferiority. False alerts are reported alongside
misses and delay, never optimized by selecting an always-silent policy.

## General-decision retention and model selection

The public seven-suite benchmark is evaluation-only: Jevbench Easy/Original/Hard,
ToolACE, Typed Decision, AG News and WildJailBreak. The bundle is pinned to
upstream Git revision `565350244af860e1c276768cd80bdd9b8be93913`, with per-file hashes.
Run the same compiler, runtime and scorer for base and final candidate. Compare
decision-level accuracy, coverage and per-suite paired changes; do not compare
our backend's numerical output directly with published numbers as though they
were identical executions. Any model failures remain in coverage and denominators.

Use these tests once for the selected scientific candidate, not as optimization
data. A decline above two percentage points in unweighted suite mean, or three
points in a suite of at least 300 decisions, is a release regression trigger.
Small-suite differences still require reporting. If a model fails this screen,
report the failure; later attempts require a disclosed development role for these
tests and additional untouched evidence. Science-only adapter routing can preserve
base behavior on other requests but is not proof that adapted weights retained it.

## Release gate

Publish weights only with a verified reload, reproducible inference/training
commands, exact base provenance and upstream notices, data/split descriptions,
test results, compute costs and limitations. A task adapter is an acceptable
weight artifact; avoid implying full-parameter training. Retain negative results
and distinguish a scientific-workflow win from interface compliance or kernel
speed. Current Hugging Face write authentication is absent locally; prepare the
complete release independently while account access is resolved. No fabricated
metrics or unvalidated improvement claims may enter the model card.

## Execution amendment, before candidate selection and workflow test collection

Transport failures interrupted the initial smoke allocation and a subsequent
scientific training run (last retrieved status: 239 updates). Their weights were
not recovered and their metadata remain in the operational record. A fresh run
repeats the same 512-update configuration and seeds, adds a 64-update durability
checkpoint, and exports adapter/optimizer snapshots to the separate coordinator.
These infrastructure retries do not select a model using test performance.

Remote commissioning established the physical backend and ordinary worker
lifecycle. A healthy workflow completed with independently verified measurements;
a rule-triggered director wake also completed a controlled unit-reporting repair.
Commissioning is excluded from test estimates. The deterministic comparator also
checks sustained residual growth over four public progress records, with a quiet
allowance and tolerance for a single overshoot. Its code is frozen before tests.

The initial test cohort is 16 task configurations, two per retained mechanism,
and four arms (64 workflows). Arm order is randomized within each configuration;
at most two workflows and four native roles run concurrently. Trial directories
use opaque identifiers. A new block starts only if at least 1,600 seconds remain
in the resource lease, allowing its two waves to finish. Retain every started
workflow, including failures. Fewer completed blocks weaken precision; they do
not justify dropping unfavorable results. Additional replication, if warranted,
must be reported separately from this initial cohort. These are new executions
and parameters of development-known mechanisms, not unseen-mechanism tests.

At 16:45 UTC, before the workflow cohort started, the cycle's resource window was
extended by two hours to 21:43 UTC (26 October 05:43 China Standard Time). The
operator authorized at least eight hours of autonomous work. The extension
accommodates the interrupted setup and the planned comparison; the 70-CU total,
640 native starts, four concurrent roles, and remote-only compute constraints
remain unchanged. The runtime release guard, native lease and connection/service
deadlines were updated together before collection.

Sources: [Intern-Decision data interface](https://github.com/InternLM/Intern-Decision/blob/main/docs/DATA.md),
[upstream evaluation protocol](https://github.com/InternLM/Intern-Decision/blob/main/docs/EVALUATION.md),
and the retained prior Simjecture studies linked from the monitor package README.

## Prospective measured-return development pilot (2026-10-25 UTC)

This amendment is recorded before collecting its prefixes or sampling proposals.
The frozen primary64 study remains unchanged and is never optimizer input. Its
completed results will be reported with all failures; the three separately
proposed host fixes are only used by the new development collector.

Four fresh public checkpoints cover healthy progress, an unreported worker-owned
adapter blocker, an adapter incompatible with the next mesh, and a protected
adapter defect. Each begins with a real native worker and P40-executed control.
Each supplies four independently sampled five-field proposals from SFT step 512 at
fixed temperature 3, seeds 2026102601+100*prefix_index+draw_index. The actual
categorical distributions, chosen answers, prompt identity and model identity are
logged. Greedy primary-study decisions are not relabeled as stochastic samples.

The input contains the exact frozen task, the last eight public transcript
records, current protected/worker source and the prior control report. Evidence
longer than 1,600 characters is explicitly excerpted, preserving its source hash.
Outcomes, injected-case identities and preferences are not model inputs. This is
a one-proposal development profile over a paused public checkpoint, not a clone
of private worker state and not a full streaming-policy evaluation. The sampled
choice is reused only while two fresh artifact-verified reads 5 seconds apart
remain semantically identical. Rebinding those reads is not a second independent
model vote. The normal admission contract applies; authority remains with the
independent judge and scoped host grant.

Each admitted proposal receives an actual new native continuation with a 650-second
budget, at most 3 parent turns, 4 physical runs and 12 native starts. Explicit worker
help remains available. Provisional reports cannot satisfy completion: a normal
return, settled jobs, no pending explicit wait, reconciled required assistance,
and settled director/authority work are required. Scientific quality is checked
against saved fields and the original criteria; an accurately reported failed
physical check is a valid result. Collector/infrastructure failures are recorded
and are not fabricated task rewards. An optimizer group requires all four
assigned continuations to have measured rewards. No replacement is chosen based
on favorable returns.

Utility is predeclared as verified reporting quality minus 0.02 per native start,
minus 0.1 times actual continuation seconds/650, minus 0.05 per required feedback miss,
and minus 0.02 per dispatched duplicate wakeup. Invalid/ineligible attention adds
a 0.05 penalty; legitimate observe/recheck incurs no such penalty. Actual admission
waiting is also charged at 0.1 times seconds/650. Offline model-scoring time is recorded
separately; this pilot does not estimate deployed monitor latency. No utility is
inferred for an unexecuted intervention. Native stochasticity means observed
return differences are noisy, not proof of causal treatment benefit.

If all 16 returns are valid and there is both executed-action and measured-return
variation, run 8 optimizer updates with accumulation 4, learning rate 1e-5, KL weight
0.02, clipping [0.8, 1.2], at most two passes, initialized from step 512. Reproduce the
logged initial behavior probabilities before updating. A continued-SFT control
uses the same initialization, 8 updates, accumulation 4 and learning rate 1e-5 on the
original training mixture. No test-label feedback enters either optimizer, and
no pilot checkpoint is selected by held-out scores. A small development pilot
can validate the measured-return training path; it cannot establish RL benefit
without fresh end-to-end validation against the SFT control and strong baselines.
The 1,024 scientific test states and public general-decision suites remain
optimizer-excluded. Evaluate predeclared checkpoints once, report every result,
and do not retune on those labels. Publication claims depend on workflow and
retention evidence, not synthetic decision accuracy alone.

The primary comparison uses descriptive paired bootstrap intervals clustered by
mechanism family (both fresh-seed configurations kept together; 8 clusters,
10,000 resamples, seed 20261026). Report actual runtime and completion together.
A secondary restricted-completion metric assigns 650 seconds to an incomplete
workflow; it must never be described as actual observed speed. Quiet-family
alerts are a proxy, not independently adjudicated false alerts. Neither the
known mechanism families nor their fresh seeds demonstrate domain generalization.

The active lease was extended by two hours to 2026-10-25 21:43 UTC before
this amendment, with the original 70-compute-unit and 640-native-start caps
unchanged. All model work stays on the remote A100 and physics stays on the
remote P40 host; the local machine performs editing and orchestration only.

## Recovery amendment (2026-10-25 23:45 UTC)

The local host restarted after the first cohort's final block had started. The
remote coordinator nevertheless completed all 64 assignments. Two model-arm
trials recorded connection-refused errors, and one earlier adapted trial recorded
an invalid negative progress age. These failures remain in the original cohort;
no repaired runs replace them. The corrected audit reports missing reports as
failed reports, matching the verifier's empty parsed-value digest, and explicitly
counts monitor errors. It finds no artifact/accounting inconsistencies.

The first development preparation cohort stopped before model sampling: its
healthy prefix encountered a failed SSH solver transfer, leaving an unconfirmed
control and a stale queued receipt. The native worker reported that limitation
honestly. All four preparation attempts remain preserved in `return-pilot-v1`.
No proposal, reward, optimizer step, or held-out model score was produced by that
pilot. PR65 makes unconfirmed transport outcomes explicit without resubmission.

A new preparation cohort, `return-pilot-v2`, repeats the four declared mechanisms
with fresh opaque prefixes under source2f11949. Preparations run serially to avoid
unnecessary SSH handshake contention. This amendment is made before collecting
those prefixes; sampling temperature, sampling seeds, four draws per prefix,
utility, eligibility requirements and optimizer settings remain unchanged.
The failed cohort is not used for training, and no continuation reward is
selected or replaced based on its value.

The selected SFT adapter was preserved off Colab and restored with exact adapter
and configuration hash verification. Its original training is not repeated.
The replacement runtime is an A100-SXM4-80GB; original training and streaming
inference used an A100-SXM4-40GB. All recovery comparisons use the same replacement
runtime and repeat the numerical-kernel checks. A direct coordinator-to-Colab
connection and a remote shutdown watchdog remove the local machine from the
inference/data path. The watchdog releases the allocation before an unrenewed
short-lived Colab credential expires. No Google refresh credential is transferred.

The old leases remain closed. Recovery uses the remaining original allowances:
31.80 of the 70 compute units have been consumed, and 357 of 640 native starts
have been used (355 remote plus two earlier audits). The new native lease permits
283 starts and at most four concurrent roles. Its hard deadline is recorded in
`recovery-lease.json`; renewal cannot exceed the original compute/start ceilings.

## Prospective workflow check of the reward update (2026-10-26 UTC)

If the fixed reward pilot is eligible and both its RL update and continued-SFT
control complete, a new streaming-workflow cohort will compare four arms:
no automatic alert, the frozen scientific consistency rules, continued SFT, and
RL. This tests RL against an equal-update supervised control. The original
step 512 streaming results remain the separate primary64 study; they are not
reused as outcomes for the updated policy.

Use all eight original mechanism families with one fresh configuration each,
seeds 202610290000 plus the sorted-family index. Randomize block order and arm
order with seed 2026102604. This yields at most 32 new real workflows. The cases
are known mechanisms with fresh configurations, not unseen-domain evaluation.
All arms use the repaired common host, the same P40 backend, native worker,
5-second polling cadence and existing completion/assistance contract. Only two
workflows and four native roles may be active concurrently. A new four-arm block
requires at least 48 remaining native starts and 1,600 seconds before the lease
ends; retain incomplete/resource-limited assignments rather than fabricate data.

All model optimization and general/static evaluations finish before this timed
cohort starts. Named adapters share one resident base model on the same A100.
Before collecting outcomes, verify each named adapter against its saved reload
probes, including prompt identity, actual probabilities and weight hashes. Any
temperature conversion of a saved RL probe is explicit. Warm inputs come from
commissioning/development only. Freeze the service identities for the cohort and
reject a response labeled with another requested adapter policy. Proposals do
not themselves count as dispatched attention.

Report verified whole-workflow completion, actual starts and elapsed time,
restricted completion time, quiet-family alert proxies and all infrastructure
errors. Use paired intervals with the same family clustering and bootstrap seed
as primary64. A small, negative or inconclusive study is not a workflow win.
Do not change optimizer settings, select a checkpoint, or amend the task criteria
in response to these outcomes.

## Confirmed-outcome pilot retry (2026-10-26 UTC)

All results of return-pilot-v2 are retained, but its entire reward dataset is
excluded from the optimizer. One continuation contains an unconfirmed SSH
transfer for its refined control; a zero scientific score there does not identify
the value of the sampled attention action. This was detected before any RL
update. The base and step 512 scientific/general evaluations completed normally
and are not repeated or used to change the fixed update settings.

PR67 enforces this exclusion before writing a training reward. Confirmed solver
failures and timeouts remain legitimate outcomes; missing, queued, running or
transport-unconfirmed physical receipts are ineligible. PR66 adds an optional,
host-configured persistent SSH connection, with no silent reconnection or job
resubmission. The new preparation and continuation cohort uses that connection
through a separately recorded backend profile. Earlier cohorts keep their
original backend and files.

Return-pilot-v3 prepares four fresh prefixes of the same four mechanisms, with
opaque-prefix seed 2026102703 and sampling seed 2026102701 (plus 100*prefix_index
plus draw_index). It collects four fresh categorical proposals per prefix. No
v2 proposal or continuation is relabeled as a new on-policy sample. Temperature 3,
utility weights, eligibility gates, 8 updates, accumulation 4, learning rate 1e-5,
KL 0.02 and the continued-SFT control remain as declared. The SFT control may be
trained and evaluated before RL while real rewards are being collected; this
changes scheduling only, not its data, initialization, seed or update count.

The waiting qualified32 design was stopped before any workflow began. Its fixed
family/seed/arm assignments are retained for a later cohort under the repaired
common host. No model, optimizer setting or case is selected using either the
completed held-out scores or the eventual new workflow outcomes. Original total
compute and native-start ceilings still apply, so collection may end at the last
complete block that fits the remaining resources.
