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

Sources: [Intern-Decision data interface](https://github.com/InternLM/Intern-Decision/blob/main/docs/DATA.md),
[upstream evaluation protocol](https://github.com/InternLM/Intern-Decision/blob/main/docs/EVALUATION.md),
and the retained prior Simjecture studies linked from the monitor package README.
