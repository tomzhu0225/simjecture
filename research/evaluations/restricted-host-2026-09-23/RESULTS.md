# Restricted-container deployment validation

2026-09-23. Development build `0.5.1.dev0`, code commit `2d68c71`.
This is installation and lifecycle validation, not a plasma result or a
controlled model-performance benchmark.

## Environment and execution

Ubuntu 22.04 container, 16 logical Xeon CPUs, 62 GiB RAM, two Tesla P40 GPUs.
Linux user/mount namespaces are denied by the outer container. The operator
explicitly selected the cooperative PRoot backend under a dedicated non-root
account. No kernel or network isolation is claimed.

The normal Bubblewrap route remains the default. A launch records its explicit
execution backend; resumes cannot change it. The alternative keeps a clean
experiment environment, copied/hash-checked inputs, recorded outputs, file/time
limits, sampled aggregate resident-memory monitoring, and process cleanup.
A remote test killed the worker and verified that its experiment process died.

- Local suite: **599 passed, 7 skipped**. Two skips were PRoot integration tests
  absent on the local machine; five were optional numerical runtimes.
- Remote execution/retry suite: **13 passed**, including actual PRoot tests.
- Browser: no JavaScript errors; explicit backend/model/execution defaults checked.
- Documentation: warning-free Sphinx build; Ruff and JavaScript syntax passed.

## Numerical stack

FLASH 4.8 was built privately for a 2D driven-sheet application and 2D/3D
magnetic-diffusion controls. All three passed MPI/HDF5 execution and readback
through the cooperative backend. These tests establish interface health, not
qualification of the proposed reconnection problem.

WarpX PR #7061 was pinned to
`3cb50a4b71b304f7bb64af4040a7b0b911e0ffb0`, compiled for CUDA architecture 61
with CUDA 12.4, MPI, PETSc, 2D and 3D bindings, and openPMD/HDF5. A separately
recorded compatibility patch supplies APIs missing from Ubuntu PETSc 3.15.

Six native regression runs passed: 2D/3D AMReX diffusion, their PETSc comparisons,
and two-rank versions of the 2D case. All four field-parity analyses passed their
upstream `2e-6` tolerance. The single-rank PETSc cases required exactly one KSP
iteration per solve. The two-rank cases initialized two CUDA devices.

The original upstream 3D PETSc input requested GPU-unsupported direct LU and
was rejected. The passing GPU variant explicitly selects ASM with local LU;
this configuration difference is preserved in the executed arguments.

Each P40 independently passed a Python/openPMD round trip through PRoot; a 3D
Python run did too. Independent readback found field-component shapes `(8,8)`
and `(8,8,8)`. All these smoke records retain `scientific_evidence_eligible=false`.
Debian BLAS/LAPACK dependency directories had to be included explicitly in the
capability library search path; rebuilding WarpX was unnecessary.

## Real agent calls and completion

Codex 0.156.1 and DSH 0.1.5-rc.2 each performed a small coding task with both
`mimo-v2.6-pro` and `mimo-v2.6-flash`: executing a Python sum-of-squares program
and writing its independently checked result, 385. All four standalone checks
passed. This does not establish permission for non-coding subscription usage.

Three minimal-mode studies then checked the finite sum-of-squares identity for
all integers 0 through 10, using recorded Python evidence and independent review.

| Attempt | Model | Budget | Observed wall | Result | Reported total tokens |
|---|---|---:|---:|---|---:|
| Initial | Pro | 300 s | 300.27 s | Deadline; diagnostic warning misclassified as judge tool use | 134,741 |
| Parser/config corrected | Pro | 300 s | 300.30 s | Recorded evidence succeeded; review unfinished at deadline | 199,430 |
| Final integration | Flash | 600 s | 200.20 s | Recorded evidence and independent review accepted | 113,061 |

The initial defect was fixed: a Codex item-level diagnostic is not a tool call.
A reviewer must still produce a successful terminal event and valid verdict;
actual tool calls and protocol failure events remain rejected. The unsupported
provider configuration entry producing the warning was removed as well.

The successful Flash study reported 109,912 input tokens (38,912 cached) and
3,149 output tokens. Reasoning counters are subsets of output. Counts take the
last completed-turn usage counter once per unique native thread. Interrupted
**ephemeral** reviewers may emit no counter, so the failed-attempt totals are
not complete billing measurements. Setup-assistant usage and standalone coding
checks are outside this table.

Budgets and software conditions differed, each condition has one sample, and
compilation was running during these checks. Do not interpret the table as a
model ranking or an efficiency benchmark.

## Provider interruption policy

The previous three-error cutoff was replaced for transient provider failures.
Regression tests cover more than three disconnects, successful continuation,
backoff capped at 60 seconds, an unchanged absolute deadline, and cancellation
while waiting. Authentication, permissions, and confirmed exhausted quota pause
for attention. Malformed reviews and harness defects retain bounded retries.

Outage/backoff counters do not stop the clock. Active-work budgeting is not
implemented by this change. Actual live tests here did not experience a detected
transport failure; retry behavior was exercised using controlled fixtures.

No production reconnection campaign was launched. See the
[proposed geometry and hypothesis](../../proposals/external-field-onset-2026-09-23/README.md).
