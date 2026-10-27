# Preserved interruption and continuation on the original resource lease

R7 collection stopped after 28 attempts: 26 verified completions and two
pre-submission transport failures. Together with the two earlier attempts, the
original design then had 30 attempted IDs, 27 verified completions and three
infrastructure failures. Thirty-four original IDs remained unstarted. These are
partial-cohort counts, not a final estimate of model benefit.

## What failed

The owned P40 SSH master exited after a server-response timeout. Its required
control socket disappeared. The worker-only and rules attempts in block 08
then encountered the frozen wrapper's explicit refusal before remote submission.
Neither attempt created a solver receipt or ran a physical simulation. Their
honest unresolved reports are retained; they are not fabricated numerical failures.

The experiment controller inspected recorded transport failures but missed this
case because refusal occurred before receipt creation. This is a gap in our
evaluation orchestration, not evidence of faulty P40 GPUs or an independent
production Simjecture bug. External inspection caught the second affected attempt
before the next assignment. The controller was suspended between workflows with
no native actor active, and both attempted IDs were retained.

[The interruption record](replication-r7-interruption.json) includes their actual
outcomes, source evidence, closed-attempt audit and resource handoff. The audit
reports zero consistency violations. The combined sensitivity excludes whole
blocks 01 and 08, while the primary record retains every attempt. Do not infer
a scientific speedup from the failure penalties or compare the incomplete arm
means as if their case composition were matched.

## Recovery and unchanged bounds

A fresh P40 connection succeeded. Two separate engineering controls then ran
through per-invocation SSH transport with the same binary, inputs, GPU and
original diagnostic reader. Both executed successfully; their solver times were
about 0.97 and 1.12 seconds, and coordinator round trips were about 4.15 and
4.30 seconds. These qualification jobs are outside the scientific assignment
manifest. [Their receipts](continuation-r8-qualification.json) retain binary and
input hashes.

The next continuation uses the same frozen scientific source `04f905c`, worker
configuration, base model, continued-SFT weights, task instructions and four
policy arms. It removes the required persistent P40 socket and checks the actual
connection before each new assignment. It also recognizes the specific
pre-submission failure that the earlier classifier missed. There is no automatic
replay of a possibly submitted physical job and no replacement of a failed trial.

Transport overhead may differ between phases. Preserve that distinction and the
registered within-block comparisons; do not claim identical elapsed-time
conditions across the interruption. The newly prepared prompt and routine-help
controls are not deployed into this continuation.

The healthy A100, its supervised single model connection, and its resource guard
were retained. The old R7 orchestrators were stopped after all native roles closed;
the registered audit was then run explicitly before the handoff. No new GPU was
allocated, and neither deadline nor spending allowance was extended:

- Hard GPU deadline: **2026-10-27 09:23:48 UTC**.
- Original continuation ceiling: **70 compute units** from its original balance.
- Original native-call ceiling: **640**; 132 prior/preflight starts retained and
  at most 508 remaining starts available.
- Exactly **34 unstarted original IDs**, under the frozen original assignment order.

The [new manifest](continuation-r8-manifest.json),
[registration](continuation-r8-registration.json), [launch](continuation-r8-launch.json)
and exact scripts in `continuation-r8-operations/` make this handoff reviewable.
The aggregation check reproduced all previously registered partial statistics
exactly and rejected duplicated assignments. The finalizer will combine the
disjoint phase records and release the retained owned runtime.

## Portable-model check and local fallback

While no timed workflow was active, a fresh A100 load of the portable adapter
matched all 496 tensors and reproduced all three saved base/SFT probes within
the existing tolerance. [That check](portable-reload-evidence.json) advances
release preparation; it is not a workflow-performance result.

The user has also authorized local physics execution following a memory upgrade.
The local WSL session exposes about 62 GiB, with about 55 GiB available, and an
RTX 4000 Ada with about 20 GiB of device memory. Training remains on the A100.

A separate [local CPU qualification](local-physics-qualification.json) subsequently
ran the same 64-cell/40-step and 128-cell/80-step controls using an existing
one-dimensional executable. Both passed the unchanged field-error and charge
checks. Absolute differences in relative field error were below `3.2e-16`,
relative differences in the saved electric-field peak were below `2.3e-16`, and
the physical times matched the retained P40 references exactly.

The local solver launches took about 0.07 seconds each with two OpenMP threads.
The solver processes peaked at about 41–43 MiB; the separate analysis process
peaked at about 562 MiB. Each solver launch had an 8 GiB virtual-memory bound,
60 CPU-second bound and a 90-second external wall timer with a kill grace period.
These small controls did not require a rebuild, a GPU or a model load.

The local executable reports `WarpX 26.08-86-g3555857d39a6-dirty` and
`AMReX 26.08-36-gf2cbba4afc9e`; its exact binary hash is retained. This is a
different executable from the P40 reference. The qualification covers only these
two bounded controls, not arbitrary plasma studies or overall workflow speed.
The running comparison still uses P40s. A remote-worker-to-local execution path
has not been commissioned, so numerical agreement alone is not a tested drop-in
backend. The exact qualification commands and original diagnostic function are
retained in `local-physics-operations/`.
