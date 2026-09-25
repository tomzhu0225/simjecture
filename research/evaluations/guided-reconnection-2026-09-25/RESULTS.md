# Guided commissioning restoration

The earlier FLASH island-coalescence campaign supplied a complete runnable anchor
and application-specific HDF5/flux analysis, not just executable access or prose.
This is a major confounder in comparing it with the recent unguided 3D campaign.
It does not establish that classic mode is better than minimal.

## Implemented

- Native minimal, structured and frontier studies accept `--guided-commission`.
  Existing package schemas are reused. Original inputs survive workspace edits
  and are verified on resume. Minimal prompts include the starting command and
  package limitations. Review context identifies supplied, non-evidentiary inputs.
- A bounded model-free readiness command runs the exact anchor through the
  registered capability and sandbox, in a separate study directory and budget.
- `scope="instrument"` methods reviews target an incremental instrument capability.
  They cannot authorize hypothesis evidence. Production methods still need the
  actual hypothesis measurement but not an already completed comparison matrix.
- Supplied outputs cannot be declared as fresh experiment inputs and outputs.
  A non-evidentiary marker no longer masquerades as numerical failure; claim review
  still rejects output explicitly carrying that marker.
- Native structured launch now compares canonical hypothesis text on resume,
  including files with a trailing newline.

## Real solver readiness

The historical `128x128`, four-rank, eta=0.001, tmax=1.2 anchor reproduced unchanged
through Bubblewrap in **19.84 seconds** including recording and analysis. It used
**zero model tokens**. Its 24 HDF5 states reproduced both flux-window crossing
times and the normalized flux slope exactly at the reported precision:

- crossings: 0.2603382385 and 1.0763841963;
- flux slope: 0.0490168472;
- maximum recorded |div B|: 9.3614e-13.

This checks a reusable starting pipeline. It does not qualify the new open-end 3D
instrument or support the scaling hypothesis. See [the receipt extract](anchor-readiness.json).
Two local setup attempts are preserved: an invalid duplicate runtime identity
entry was rejected, and a wrapper with an unavailable sandbox interpreter failed
before FLASH. The corrected sandbox run above is the readiness result.

## Paired agent pilot

Both corrected GLM 5.3 trials reached their 600-second budgets:

| Mode | Time to reproduced anchor | Scaling cases beyond anchor | Accepted scientific conclusion | Reported tokens |
|---|---:|---|---|---:|
| Minimal | 194 s | 0 | No | 1,513,332 |
| Structured | 489 s | 0 | No | 3,379,112 |

Minimal had 1,264,256 cached input tokens; structured had 3,266,688. Minimal thus
had MORE uncached input (227,630 versus 96,304), despite fewer total tokens. These
numbers do not establish a monetary-cost advantage. Minimal's interrupted final
review has no usage receipt; its total is a lower bound. Worker usage was recovered
from native cumulative session counters once per thread, including interrupted turns.

Minimal initially duplicated the program name in its argument list, then reproduced
the anchor. Its production reviewer identified real omissions: declared numerical
controls were recorded but not enforced, and a stated bootstrap falsifier was not
implemented. Its narrow instrument reviewer also prematurely approved a plan without
a fresh run. Structured initially mistyped one character of a source hash and was
correctly rejected; it later reproduced the anchor. Neither reached a scaling fit.

After observing these failures, the final revision adds `lab.reproduce_anchor()`
and rejects instrument-readiness requests without a successful current-binding
validation BEFORE spending reviewer tokens. These fixes were tested separately;
the paired results above are not performance measurements of that final revision.

The first pair was stopped and EXCLUDED because the private runtime lacked classic
mode's automatic-preflight parameter file. Its reported cost remains recorded:
2,514,156 tokens for minimal and 2,976,302 for structured. An earlier structured
launch failed before any model call on a trailing-newline comparison. No failed
attempt was deleted or silently counted as scientific evidence.

See [the comparison plan](PLAN.md), [measurements](measurements.json), and
[exporter](export_results.py). This is one short trial per mode on shared hardware
and provider, not a replication of the original six-hour campaign or a statistically
established ranking. Guided assets repair a missing foundation; they have not yet
proved efficient end-to-end scientific completion. No default-mode change follows.


## Final validation and scope

The final `lab.reproduce_anchor` implementation ran the actual FLASH anchor through
Bubblewrap in **20.09 seconds**, with zero model tokens; see
[its receipt extract](final-helper-readiness.json). The full final suite passed
**651 tests, with 9 optional-environment skips**; 92 targeted research-service tests,
Ruff and the Sphinx warning-as-error build also passed. Tests cover all three
native modes, resume preservation, changed package rejection, stale/missing
validation, source/output overlap, and the instrument-versus-evidence gate.

The lockfile was synchronized to the already declared development version and
existing optional process dependency; no dependency range was changed. This is a
local development revision. Nothing was published or deployed to the remote host;
no further ten-hour campaign was launched. The 3D reconnection instrument remains
unqualified. These changes restore the guided starting path and address observed
interface failures; they do not establish a scientific completion-rate advantage.
