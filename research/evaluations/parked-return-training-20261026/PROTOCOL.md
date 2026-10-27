# Parked workflow return collection

The previous reward pilot resumed an awake worker from a public checkpoint.
The deployed coprocessor instead observes a parked worker waiting for an
asynchronous scientific job. This phase first commissions a collector for that
actual lifecycle. Commissioning is not a model-effectiveness or RL-update study.
The previous training and 28-workflow evaluation remain unchanged.

## Commissioning before a larger cohort

Freeze one `progressing_work` configuration with seed `202610310000`. Run one
sampled-policy episode and one no-automatic-attention episode, with assignment
order seed `2026103101`. Both use fresh native workers, the same real WarpX
64-cell/40-step and 128-cell/80-step controls on the remote P40, identical
scientific criteria, and the ordinary terminal-event/90-second fallback wakeup
policy. Worker-requested help and repair remain available in both arms.

The sampled behavior is the previously development-selected SFT step-512
adapter, whose weights SHA-256 is
`922bfef8e221f5df39ec3a3740d3e9e97fbcd2358c34679f774a0085227ae780`, on the pinned
Intern-Decision-4B base revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`. Use temperature 3, an 8,192-token
limit, and the qualified dense FLA prefill runtime. Derive each decision's
sampling seed from the frozen episode seed and request index. No behavior
checkpoint is selected using the completed workflow test scores.

The main worker first submits its real job and yields. Samples are requested
only while it is parked, before a discretionary alert has been consumed, and
when no help/director/authority operation is already active. The existing host
admission contract decides whether a proposal can dispatch attention. A proposal
does not itself wake the parent; the normal lifecycle consumes actual returned
attention, terminal events or the fallback boundary.

The run records request observations, exact behavior distributions and choices,
model/adapter identity, temperature, admission receipts, real native work,
physics receipts, and independently verified final reports. The exporter checks
that request times lie inside recorded parking intervals and do not overlap
active main-worker invocations. Missing responses are incomplete coverage, not
invented neutral/negative returns. Recorded provider failures, unconfirmed solver
transport or inconsistent artifacts make the cohort ineligible.

Both source and physical-backend fingerprints are frozen before execution.
Only a complete assigned cohort can be exported. All failed and unstarted
assignments remain recorded. Every commissioning row has split `commissioning`,
the output is `commissioning.jsonl`, and optimizer eligibility remains false
even if both scientific tasks succeed. No optimizer runs in commissioning.

## Return definition for subsequent training

Future training requires at least two sampled-policy and two wait episodes per
configuration, collected in randomized order under a new prospective plan.
Separate native episodes share configuration, criteria, worker/host policy and
resource budget; they do not claim an identical private worker prefix.

Use the declared execution-cost utility:

```text
U = verified whole-workflow quality
    − 0.02 × native starts
    − 0.1 × actual elapsed seconds / 650
    − 0.05 × required feedback misses
    − 0.02 × duplicate attention dispatches
```

An accurately reported failed original physics check can complete the task.
Known incomplete/incorrect worker outcomes receive the measured quality zero;
collector/infrastructure failures do not become fabricated task failures.
Invalid model proposals are recorded but receive no arbitrary fixed penalty
when suppressed by the host. Their actual delay or scientific consequence is
already represented in the episode outcome. Report inference count, input
tokens and model scoring time separately; these coefficients are research
proxies, not monetary prices.

Every sampled decision in an episode receives that episode's utility minus the
mean utility of the configuration's separate wait episodes. Retain all decisions
and all assigned episodes, including zero-opportunity episodes. Polls are not
independent scientific outcomes. The trainer uses an episodic clipped-policy
surrogate, verifies initial adapter/configuration hashes and reproduces logged
probabilities before updating. Commissioning determines whether collection works;
it supplies neither optimizer examples nor a claim of intervention advantage.

Any larger training study must declare update settings, repeated baselines,
fresh validation tasks, general-decision retention checks, and resource limits
before collecting its outcomes. It must address both false alerts and workflow
benefit, and include scientific mechanisms beyond the original templates before
claiming broader generalization. A lower training loss is not sufficient for a
model-weight release.

## Resource boundary

All model inference/training stays on the remote A100 and all physics stays on
the P40. The local host performs only editing, orchestration and lightweight
tests. No allocation from an earlier lease is reused after release.

Commissioning uses only the remaining original allowances: 38 native starts
remain after 602 of 640 were used. Its new lease therefore permits at most 38
starts, at most 12 per episode and four concurrent roles; the two-episode block
requires 24 starts available before launch. The last recorded cumulative Colab
consumption was 63.33 compute units. This is historical accounting, not a live
balance. Recheck the account before
allocating, preserve the original 70-unit ceiling, and use a separate short-lived
lease/guard that releases only its owned endpoint. A single new allocation is
bounded to at most 55 minutes and may stop sooner at the compute-unit or
credential-expiry boundary. Release it promptly after commissioning and artifact
preservation. This manifest covers commissioning only; a larger cohort needs its
own frozen experimental plan.
