# Preserved transport interruptions and bounded continuations

**Latest state:** R9 stopped after nine verified workflows when a read-only
connection check failed before starting the next assignment. The A100 was
released at **2026-10-27 08:39:51 UTC**. All native roles are closed; the temporary
Windows task and local failsafe are absent. The original cohort has 47 recorded
attempts, 43 verified completions, four earlier infrastructure failures and 17
unstarted IDs. The failed readiness check is not an additional scientific
attempt. [The terminal evidence](replication-through-r9.json) preserves its exit
code, a later successful read-only check, the audit and cleanup. Stderr was not
retained, so the precise SSH cause is unknown. The exception skipped R9's final
model-probability probes; only its initial probability qualification is verified.

**Audited R8 status:** R8 also stopped, after eight attempts and seven verified
completions. The A100 was released at **2026-10-27 06:17:44 UTC**. Across all
phases there are 38 attempted original IDs, 34 verified completions, four
infrastructure failures and 26 unstarted IDs. The sections below retain the R7
handoff history; they do not describe a currently running allocation.

The R8 interruption was a connection timeout before the P40 SSH session was
established, on continued-SFT assignment `bswf-e587cb0721bd8468`. The wrapper
preserved request `34db54300d304aadb6a448108a64ab32` with an unknown execution
receipt. Four subsequent read-only checks, alternating direct and existing proxy
routes, found no matching remote job directory. All four checks succeeded in
0.54–0.69 seconds. This is evidence of current reachability, not sustained
reliability or a demonstrated proxy advantage. The unsuccessful assignment and
its original receipt remain unchanged. No GPU hardware failure is established.

The controller stopped further assignments, the audit found zero consistency
violations, and the final three model probes remained within the original
tolerance. The release guard exited after releasing its owned runtime; the local
temporary Windows task then unregistered itself. See
[the complete partial record](replication-through-r8.json). The next
[assignment list](continuation-unstarted-after-r8.json) contains only the original
26 unstarted IDs. A new bounded inference lease and transport qualification have
now been established for R9, whose separate manifest governs their resumed
execution. That R9 runtime has now also been released as described above; each
release receipt applies only to its own allocation.

## R9: retry connection establishment, preserve submitted jobs

Both controls passed through a study-only SSH alias with `ConnectionAttempts 3`,
15-second connection timeout, no persistent control socket, and strict host-key
verification. This permits bounded TCP connection retries before an SSH command
is submitted. It does not retry a failed remote command or an ambiguous physical
submission. The existing 180-second transfer bound remains. The pre-assignment
connection check allows 55 seconds and stops the phase before starting a worker
if connectivity is unavailable.

The coordinator previously had no user SSH configuration. Its new configuration
contains only the study alias. `ssh -G` for the original P40 hostname was
byte-identical before and after installation. The alias resolves to the same
P40 host and port; it uses the existing known-hosts file and credentials. Neither
GGDD settings nor the original machine profile were changed. A separately hashed
study profile selects the alias. The controller checks configuration and profile
hashes before each assignment.

The first setup check failed because the host-key alias omitted the nonstandard
SSH port. It stopped before any solver or native actor started. Correcting the
alias to the existing known-host identity allowed both controls to execute and
pass their unchanged numerical checks. Their round trips were 4.19 and 4.46
seconds. This qualifies the tested path, not its future uptime or resilience to
an established-session disconnect. The failed setup receipt is retained in the
[launch evidence](continuation-r9-launch.json); the successful controls are in
[the qualification](continuation-r9-qualification.json).

R9 uses a new A100 with unchanged weights and fresh prediction qualification.
The 26 assignments, 55-compute-unit ceiling, 15:21:17 UTC hard stop and remaining
469 native starts are recorded in its [registration](continuation-r9-registration.json)
and launch evidence. The local CPU qualification remains a numerical fallback;
it has not been substituted into the original cohort.

The inference SSH connection subsequently exited between assignments. Its
supervisor established a replacement **37.3 seconds** after the old connection
ended, within the existing 90-second inter-workflow gap. Collection continued
with no extra failed assignment at that interruption. The connection identities
and timings are in [the R9 interim evidence](continuation-r9-interim-evidence.json).
No timed model request was active at that point; this does not demonstrate an
in-flight recovery within the unchanged 25-second host request bound. The earlier
forced in-flight qualification remains evidence for its tested instance, not a
guarantee for every future outage.

## Earlier R7 interruption

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
The collected comparison used P40s. A remote-worker-to-local execution path
has not been commissioned, so numerical agreement alone is not a tested drop-in
backend. The exact qualification commands and original diagnostic function are
retained in `local-physics-operations/`.
