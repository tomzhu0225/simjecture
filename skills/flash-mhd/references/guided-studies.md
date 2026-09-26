# From a working anchor to useful evidence

Read this when a supplied FLASH example runs but the investigation is spending its
budget rebuilding interfaces, rewriting diagnostics or repeating commissioning. These
lessons concern experiment operation; obtain the physical hypothesis and thresholds
from the active study, not from this reference.

## Use the supplied instrument before replacing it

Inspect the exact anchor command, compiled application, input producer, parameter file,
output reader, expected checks and measured runtime. A generic FLASH smoke is not a
replacement for a working example of the required geometry. Reproduce the anchor with
a bounded exploratory run; in a guided minimal study, `lab.reproduce_anchor()` records
that run without making the supplied example claim evidence.

If it fails, retain the command, exit status and relevant log. Read the authorized
source and full build log before concluding the interface is opaque. Distinguish
an actual build/interface error from anticipated difficulty. An alternative solver
changes the scientific instrument and needs a physical justification and qualification,
not merely a more familiar programming language.

Reuse existing instrument IDs and approved bindings while their implementation and
scope remain applicable. A new session or assignment allowance is not a new instrument.
If access is refused, preserve that receipt and identify the assignment problem before
creating a chain of equivalent instrument versions.

## Make the output reader work on one actual file

Start with a produced file and the supplied reader. List dataset names, shapes, dtypes
and the metadata used by that reader. Locate coordinates, block bounds and refinement
information before reshaping or plotting. Do not interpret an unfamiliar dimension
order by intuition or flatten an adaptive mesh into a uniform image.

Verify placement with a known initial field, coordinate-dependent quantity or other
independent geometry check. Test the observable on an actual time sequence before
launching a parameter matrix. Confirm time values and output cadence from the files.
A reader that opens HDF5 successfully has not necessarily reconstructed the field.

If field arrays are absent, first check whether this is a scalar summary, plot output
or checkpoint and whether the relevant output was enabled. A missing dataset is an
I/O/diagnostic problem, not evidence that the corresponding physical field is zero.

Preserve raw fields and write a compact review summary identifying source files,
normalization, estimator, analysis window, exclusions and quantitative validation.
Keep failed checks and censored cases explicit. Record revised analysis rather than
editing frozen outputs. Changing only a display label or eligibility annotation is
not a reason to repeat expensive evolution; explain the annotation to review. Actual
changes to physics, initial conditions or solver numerics need appropriate new runs.

## Separate a pilot's question from the scientific question

A timing pilot asks whether the intended resolution, output cadence and process topology
fit the budget. A rank-comparison pilot asks whether performance and relevant results
are consistent. They need not reach the science measurement window merely to answer
those questions. Label them `stage="exploration", purpose="timing"` or `purpose="parity"`
in minimal mode. Classic campaigns use their workbench stage.

Measure rather than assume that more ranks are faster. Preserve ranks, threads, steps,
simulated time, elapsed time and output volume. Shorten a pilot to estimate cost without
silently shortening the later scientific protocol. Budget for refinement and review,
not only the first successful solve.

Once the implementation is ready, submit its production method and collect distinct
recorded cases. Instrument-readiness approval does not authorize hypothesis evidence.
A conditional approval with unmet prerequisites needs revision before evidence begins.

## Check the decision rule before spending the solver budget

Separate these questions: was the case in the claim's domain, was the numerical result
admissible, and did it contradict the prediction? A censored or invalid case does not
answer the last question. Preserve excluded cases and explain their exclusion.

For conjunctive bounds on one observable, calculate the intersection first. If the
largest lower bound exceeds the smallest upper bound, the rule is impossible. In
minimal repairs, `lab.commit(..., numerical_bounds=[...])` can check explicit inclusive
bounds; give each case/observable a distinct metric name and repeat it only for ANDed
constraints. The check establishes feasibility, not physical correctness.

Do not confuse rejection of an exact exponent with rejection of a permitted exponent
band. An uncertainty interval that overlaps the permitted band does not reject the
whole band merely because one endpoint lies outside. State the actual quantifier,
uncertainty criterion, admissibility domain and prospective rule used in the decision.

## Report the state that exists

Read durable experiment/job receipts, then count completed usable cases separately.
A successful analysis job is not a successful solver case; a launched batch is not a
completed matrix; a numerical result is not an accepted claim. Report uncertainty,
remaining controls, review state and cancellation status alongside plots. Worker notes
may be stale after interruption, so reconcile them against receipts.
