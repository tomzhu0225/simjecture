# Same-weight runtime follow-up

The isolated FLA profile passed the predeclared offline gate: all 16 decisions
match, finite normalized probabilities, identical prompts/weights and at least
1.5x lower warm inference time. No adapter is trained or changed. Probabilities
can differ through floating-point execution; future policy training must collect
behavior probabilities on the actual training runtime.

Freeze this follow-up before collecting outcomes. Run eight fresh real-worker
trajectories using the existing parked-worker task: healthy and protected
completion-adapter defect, two repeats for each reference/FLA runtime. Use an
ABBA sequence of four server blocks, with one healthy and one fault trajectory
concurrent per block, randomized within block using seed 2026102406. Sequential
servers avoid loading two full models alongside the unrelated GPU simulation.
Use the unchanged pinned base, current identical worker instructions and judge
policy, 90-second fallback and original numerical criteria. Warm each server
with one common frozen checkpoint packet; retain warmup costs separately.

Share the existing four-role/240-start native lease and at most two parents.
Retain all failed runs. Record first receipt/adapter contradiction, judge start,
worker resume, model calls/errors, final report verification, starts and elapsed
time. Primary comparison is response latency; full completion time includes
variable large-worker reasoning and is secondary. This small repeated fixture,
ABBA order and shared GPU cannot establish generalization or isolated hardware
throughput. Do not compare these trajectories as controlled pairs with the prior
12-run study: the helper declaration interface has since changed.
