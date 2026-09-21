# Codex base-prompt audit and direct GLM baseline

The proposed explanation was that a long Codex coding system prompt conflicted
with Simjecture's research workflow. All **26 available native sessions** from
the original pilot and token-accounted repeat instead recorded
`base_instructions.text = ""`, with model-default provenance for GLM 5.3.
This includes workers and the persisted reviewers. Missing ephemeral reviewers
were not audited. See [prompt-audit.json](prompt-audit.json).

This is an empty configured base, not absence of all model context. The inspected
worker had 5,544 characters of injected developer guidance containing skills and
permissions, plus environment, native tool schemas and the Simjecture task.
The direct baseline's worker developer guidance has the identical SHA-256:
`ff4db9f93a609b0fedfff053670e46abd8d2dd984d19447d74678e2f56960ed7`.

Codex documents `model_instructions_file` as an override for built-in instructions;
see the [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
The installed CLI rejected an explicitly empty instruction file before either
model session started. Those failed preflights are retained privately. The live
baseline used the existing empty model default, verified in both new session
records. No account-wide settings or native tool permissions were changed.

## Direct native-tools baseline

We then ran the same mathematical hypotheses directly through codex-glm/GLM 5.3,
without Simjecture's tool adapter, contract approvals, queue or continuation loop.
Each received a 900-second maximum and a fresh session; both ran concurrently.
This changes the workflow, not the already-empty base prompt. It is not a
prompt-removal A/B test. See the [predeclared plan](PLAIN-BASELINE-PLAN.md).

| Task | Natural exit time | Input | Cached input (included) | Output | Total | Numerical calculation |
|---|---:|---:|---:|---:|---:|---|
| Euler | 295.1 s | 278,687 | 224,896 | 9,975 | 288,662 | Correct for all four N |
| Midpoint | 187.1 s | 95,422 | 51,136 | 6,308 | 101,730 | Correct for all three h and every step |

Both processes exited normally. After reading each source, we reran an unchanged
copy with Python in a separate verification directory and reproduced every row.
An independent arithmetic checker confirmed the requested Euler errors and
ratios. Midpoint source uses simultaneous old q,p, evaluates every step, and
matches reference maximum energy errors 5.551115123125783e-16,
2.098321516541546e-14 and 3.430589146091734e-14.

There are material limitations:

- Both added unrelated diagnostic rows. The supplied prompt mentioned both task
  schemas; that wording was ambiguous and is a weakness of this evaluation.
  Strict original row-schema checks fail. Requested rows were selected explicitly
  for the numerical check; this is not silently treated as full schema compliance.
- Euler correctly falsified the original ratio claim and explained approximate
  first-order behavior. Its repaired bounds were the observed minimum and maximum,
  tested against the same data used to define them. That is a descriptive summary,
  not a convincing independent prospective repair test.
- No result passed Simjecture's acceptance gates. Do not equate native process
  exit or correct calculations with a kernel-accepted scientific investigation.
- One sample per task, different evaluation time and a lighter workflow do not
  establish a general speedup or model ranking. Reported tokens are not billing.

Full data: [plain-baseline-results.json](plain-baseline-results.json). Raw source,
outputs, prompts, session receipts and independent reruns are retained privately
under `.private/frontier-eval/plain-empty-base/`.

## DSH and interpretation

The installed DSH minimal preset defines a short fixed persona and two native
tools, suppressing additional prompt assembly and runtime snapshots. Its standard
preset adds agent instructions and a broader tool set. Simjecture's own DSH
composition additionally supplies detailed scientific-role coordination guidance.
Thus “raw DSH” depends on the chosen preset; changing to it changes runtime,
prompt assembly and tools together. No live DSH comparison was performed here.
Local definitions: `@deepseek-ai/dsh/config/agent-presets/minimal/agent.cordis.yml`,
`config/agent-presets/standard/agent.cordis.yml`, and this repository's
`integrations/dsh/cordis.patch.yml`.

The default Codex coding base prompt cannot explain these runs as proposed,
because it was absent in the recorded sessions. Other injected context may still
interact with task instructions; this experiment does not isolate that effect.
The direct runs show that GLM can perform the core calculations within five
minutes with the same empty base and injected developer guidance. The remaining
problems include harness coordination overhead, ambiguous output instructions,
and the distinction between a plausible numerical answer and a properly tested
repair. Further evaluation should score those separately.
