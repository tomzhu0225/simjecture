# SSH experiment workers: development acceptance

Tested on 2026-09-30. This feature is unreleased and separate from 0.5.3rc1.
Two operator-provided SSH hosts were used, each with two Tesla P40 GPUs and
restricted Linux namespaces. Headless workers were prepared in dedicated directories
under unprivileged service accounts. Existing research installations were preserved.
The real-host checks made no model-provider requests.

## Actual execution and recovery

| Check | Observed result |
|---|---|
| One coordinator, two SSH hosts | Both numerical jobs succeeded; about 7.98 seconds of actual execution overlap. |
| Numerical oracle | Independent NumPy array sums matched their closed-form values on both hosts. |
| Privilege and GPU visibility | Both jobs ran as non-root; CPU-only jobs had empty `CUDA_VISIBLE_DEVICES`. |
| HDF5 retention and retrieval | Each 526,336-byte array stayed remote until requested; both retrievals passed SHA256 verification. |
| Lost SSH authentication during execution | Coordinator observed unreachable transport; restoring authentication recovered the same remote job and process, including after closing an automatically multiplexed SSH connection. |
| Coordinator process killed and reopened | The existing detached worker process delivered the result without launching another job. |
| Running cancellation | Five recorded worker/launcher/experiment processes stopped, including a child configured to ignore SIGTERM; cancellation was confirmed. |
| FLASH through the dispatcher | Two-rank 64×4 RZ aluminum radiation-MHD commissioning reached 2 ns, with 41 HDF5 analysis records in about 15.85 seconds. |
| FLASH diagnostic checks | Finite fields, positive states, requested endpoint, no reported nonconvergence, radiation accounting agreement and divergence check all passed. |
| WarpX through the dispatcher | Two concurrent one-step 2D CUDA/PICMI jobs completed with native openPMD/HDF5 diagnostics and readable mesh records. |
| GPU reservation and physical assignment | Jobs received GPU IDs 0 and 1; CUDA reported one visible device per job and distinct PCI bus IDs. Execution overlapped by about 17.76 seconds. |
| Read-only source inspection | Registered WarpX runtime/dependency directories were listed through `Lab.read_instrument`. |

These are infrastructure and commissioning checks. They do not establish scientific
convergence or endorse the stagnation hypothesis. Scientific status remained
`unreviewed`; the CUDA smoke explicitly marked itself ineligible as scientific evidence.

The first GPU validation script successfully ran WarpX but failed its additional
hardware probe because the operator script assumed a `lib64` CUDA library path.
The corrected script used the installed runtime's `lib` path and passed. FLASH
initially lacked traversal permission to an existing toolchain parent directory;
a user-specific read-only traversal ACL fixed it. Both failures remained recorded.
An early disconnect-test setup completed before disruption and was excluded; the
subsequent test observed the outage during an active job.

## Automated coverage

Local workers use the same protocol and launcher as SSH workers. Coverage includes
parallel placement, pending coordinator reservations, queue serialization, request
replay, lost submission replies, coordinator recovery, frozen worker identity/code,
GPU admission, deadlines, descendant cancellation, bounded source inspection,
traversal rejection, altered artifact rejection and credential separation.

The generated native-agent client also discovers the pool, submits a numerical
job and retrieves a retained array through actual JSON RPC. A clean installed wheel
passes CLI discovery, worker preparation and numerical execution. Source archives
were built from tracked/staged files; private operator research and credentials
were excluded.

Browser tests exercise the visible Machines page, asynchronous preparation,
readiness, brief/proposal selection and continuation inheritance. Read-only HTTP
access cannot provision a worker. There were no JavaScript errors or provider calls.

The full regression suite, DSH integration tests, Ruff, JavaScript syntax, public
schemas, documentation and installed-wheel CLI are checked alongside this change.
Final regression result: **801 passed, 7 skipped**. The seven skips are local
optional runtime/cooperative-backend checks; FLASH, CUDA and cooperative execution
were separately exercised on the real hosts above. **14 DSH tests passed**.

## Operational limits

- Pools apply to minimal-mode numerical studies. Interactive simulations, remote
  agent hosting, Simote profile import and Slurm worker adapters are not included.
- CPU/RAM budgets control admission; CPU reservation does not enforce an OS quota.
  GPU visibility is cooperative, with device mappings supplied by the capability.
- Restricted-container tests explicitly use `proot-cooperative`; it is not kernel
  or network isolation. Bubblewrap remains the default where namespaces work.
- SSH waits and queueing use the original wall deadline. An unreachable worker at
  deadline expiry has an explicitly unconfirmed cancellation.
- Worker program/configuration and instrument hashes are frozen per phase. Retain
  original worker directories for later artifact retrieval and start a new phase
  after changing instruments or pool configuration.

See [setup and usage](../how-to/ssh-workers.md).
