# v0.5.0 release validation

Minimal is the default for new native-agent studies in the CLI, browser and TUI.
Structured and frontier remain selectable. DSH/API are explicit legacy choices;
unsupported mode/backend combinations are rejected rather than silently changed.
Native tools remain available. Installed numerical solvers are exposed through
an explicit capability registry; minimal otherwise provides the Python sandbox.

This release preference is not a claim that minimal is universally faster,
cheaper or more scientifically capable. Earlier comparisons remain available in
[the v2 report](../research-service-v2/RESULTS.md) and
[the simple-task follow-up](../minimal-default/RESULTS.md).

## One-hour packaged FLASH study

The release candidate was installed into an isolated environment and ran the
same 17-case driven-sheet resistive-MHD protocol, requesting GLM 5.3. No model
or simulation was mocked in this study. The agent owned the investigation and
was not redirected during it.

| Measurement | Result |
|---|---|
| Actual elapsed wall time | 3,601.51 seconds |
| Exit / durable status | 124 / budget_exhausted |
| Required cases with complete raw-field evidence | 15 / 17 |
| Recorded experiment receipts | 15 succeeded, 2 timed out |
| Missing required cases | Both temporal-refinement cases |
| Scientific conclusion | Unresolved; no accepted completion |
| Independent raw-field integral comparisons | All 12 reported baseline integrals agree; maximum relative error 2.32e-16 |
| Periodic transport controls | All three pass |
| Process cleanup | No recorded experiment workers or FLASH processes remained running |

Raw-field coverage, execution-receipt status and accepted claim closure are
separate measures; auditing retained outputs never rewrites a failed receipt.

The low-resistivity grid check again failed: integrated dissipation changes by
5.970% and 5.832% between the 256 and 384 grids, above the predeclared 5% limit.
All other measured spatial-refinement checks passed. The agent recognised this
numerical limitation, retained its results and correctly reported unresolved
rather than treating missing or unconverged evidence as support or falsification.
A fresh external assessment agreed with the numerical analysis and provenance.
This remains a bounded current-sheet diagnostic, not a demonstrated Z-pinch
reconnection mechanism or MRT result.

The 15/17 coverage is greater than the preceding minimal trial's 13/17, but these
are single runs with different scheduling and shared-resource conditions. It is
not evidence of a statistically established performance advantage.

## Token accounting

| Category | Reported tokens |
|---|---:|
| Input | 12,302,765 |
| Cached input, included above | 12,026,496 |
| Uncached input | 276,269 |
| Output | 47,090 |
| Total input + output | 12,349,855 |
| Separate external assessment | 142,542 |

The total is higher than the preceding one-hour minimal trial's 4,961,038.
Most of this run's input was cached; uncached input was close to the preceding
trial's 274,759. No subscription-credit or monetary-cost conclusion follows.
This is **not** a demonstrated token-efficiency improvement.

Counters are the last cumulative native usage once per unique thread, including
interrupted turns when counters exist. Reasoning tokens are part of output,
not added again. Missing counters are not zero. Implementation-assistant usage
is not included. The browser reports available completed-turn counters; this
final audit also uses matching native session counters and can therefore be
more complete than live UI usage.

[measurements.json](measurements.json) includes numerical checks, the external
assessment, usage categories and source hashes. [export_results.py](export_results.py)
regenerates it from private receipts. Raw native transcripts and large field
files are not published.

## Release engineering and interface checks

Validation covered:

- Full Python regression suite and GitHub CI, including documentation and the
  separate WarpX instrument job. The application CI run before the final report
  passed 585 tests with five optional-runtime skips.
- Fourteen DSH integration tests, including the real CLI/MCP profile against
  local test-provider fixtures; these are not additional paid scientific trials.
- Installation from the extracted Linux archive without DSH. The optional DSH
  installer retains its pinned runtime and Node version requirements.
- Actual installed CLI pause/resume with the original deadline preserved,
  deadline exit, live terminal output and cancellation after a numerical sandbox
  had started. Network/quota failures were injected into transport fixtures and
  correctly paused without scientific completion.
- Desktop/mobile browser checks: visible mode/backend, compatible launch choices,
  folded guidance, minimal hypothesis tree and read-only controls. The terminal
  shows activity, job/review counts and elapsed/remaining time.
- Resume-contract validation, study-wide ownership locking, missing-backend
  preflight, custom supervisor-directory monitoring and native process identity
  matching. A packaging test caught and fixed an old identity matcher that had
  rejected the new CLI entry points.
- Source/package content checks, checksums, lint and a warning-free documentation
  build. Private workspaces, environments and the proprietary FLASH runtime are
  excluded from the distributed artifacts.

The long study used a frozen candidate wheel. Later fixes concern launch control,
backend streaming, status projection and packaging; they have separate regression
and installed-package checks. The scientific evidence service itself has an
identical Python AST between that candidate and the final application. The source
comparison is recorded, rather than attributing all final changes to the earlier
frozen run.

All scientific completion rules remain: accepted original support, or accepted
original falsification followed by an independently supported prospective repair.
Normal model exit, missing evidence and timeout do not prove a claim. Native
agents still use cooperative same-account access; this is not adversarial
isolation of the worker from its host.
