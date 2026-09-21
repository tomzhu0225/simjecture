# Frontier workflow pilot (predeclared)

Question: does a persistent researcher workflow reduce orchestration friction
without weakening scientific acceptance, compared with the existing structured
role workflow? This is an implementation pilot, not a model ranking or proof
that any frontier model is universally superior.

Both conditions use codex-glm with requested model `glm-5.3`, the same kernel,
scientific review policy, numerical sandbox, hypotheses, operator task text,
resource limits and fresh initial model sessions. Reviewers use fresh sessions
and the same requested model. No simulated model responses count as live results.

Structured condition: existing falsifier/repair role routing, fresh research
folders/model sessions and a fixed session time limit. Frontier condition:
researcher authority across its own descendants, a persistent research folder,
explicit native thread resumption, concise continuation prompts, and an
inactivity watchdog instead of interrupting observable progress. Independent
approval and finalization authority remain unavailable to both workers.

Two self-contained numerical tasks:

1. A deliberately false second-order accuracy claim for explicit Euler on
   y'=-y, y(0)=1, at t=1, over the finite refinement set N={16,32,64,128}.
   The worker must test it and propose/test a scientifically meaningful repair.
2. A true finite-grid energy conservation claim for implicit midpoint on the
   harmonic oscillator, h={0.2,0.1,0.05}, T=20, q(0)=1,p(0)=0.

Each arm gets 900 wall-clock seconds, a 180-second session limit/inactivity
watchdog, 1 GiB workspace and 120 seconds per numerical job. Initial pilot:
one run per task/condition (four live runs), counterbalanced launch order.
Runs may overlap; elapsed-time comparisons therefore include shared service
and host variability. No significance or reliable model-quality inference
will be made from this small sample.

Primary observations: independently accepted campaign outcome and correctness
against an independent arithmetic reference. Also record first usable numerical
artifact, source/contract review failures, worker session starts and distinct
native threads, tool/operation counts, repeated orientation, provider-reported
tokens, and stop reason. Record missing data as missing. A time limit or parser
failure is not scientific falsification; a correct exploratory artifact is not
accepted scientific support. Preserve unsuccessful runs and raw provider traces
privately; publish only compact metrics and relevant non-sensitive artifacts.

Implementation and task hashes are recorded at launch. Correctness grader is
independent of the model's natural-language conclusion. Any implementation fix
made after starting a run must be logged and the affected comparison identified;
do not silently relabel it as the original condition. Keep the new mode opt-in
unless evidence supports broader adoption.
