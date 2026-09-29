# Proposed rc3: continuation and operator steering

Status: design and rationale. The initial rc3 development implementation is described
in [the user guide](../how-to/continuation-steering.md). Advisory text/URL steering,
selected-file continuation, GUI actions and bounded review recovery are implemented;
attachment-specific steering and automatic cross-machine artifact relocation remain
future work. Motivated by the September28–29
aluminum-stagnation study. No new study has been launched by this proposal.

## Existing behavior, verified in rc2

- Resume preserves the existing launch contract and deadline. An expired deadline
  cannot be extended through ordinary resume (`study_launch.materialize_native`).
- Original hypothesis, operator protocol and execution mode are immutable within
  a study (`ResearchService.create`, `freeze_protocol`, study launch validation).
- The browser can prepare another study in the same conversation and receive the
  preceding study's report (`Workspace.new_study`, `deliver_study_reports`). This
  is conversational continuity, not explicit experiment/evidence lineage.
- No first-class operator steering inbox was found in the minimal service or
  supervisor. Reviewer/host feedback exists, but is not a user steering interface.

## Continuation as another phase of one investigation

Expose “Continue investigation” in the UI and a matching CLI/API operation. Preserve
an investigation identity, create a new study/phase with an explicit parent, a new
operator brief and separately authorized wall budget. Keep the parent immutable.
A new phase may change model/backend or geometry without rewriting old provenance.

Prepare a compact, reviewable handoff: original question, current claim tree, accepted
and unreviewed findings, failed alternatives, unresolved checks/reviews, selected
working programs/readers, instrument identities, data/receipt references and suggested
next experiments. Select artifacts with checksums; mount/reference bulky raw data
read-only. Support explicit path relocation with identity verification. Do not replay
the full conversation or silently copy credentials/provider sessions.

Carry prior approval scope and exclusions accurately. Old observations stay old;
exploratory outputs do not become evidence, and prior observations cannot masquerade
as fresh prospective validation. Reuse applicable instrument qualification without
repeating irrelevant smoke tests. Changed geometry, closures and observables require
appropriate qualification, rather than either automatic approval or blanket restart.

## Live steering

An operator-only, append-only inbox accepts suggestions, papers, corrections and
explicit requirements. Entries record author/time, attachments and source hashes,
parent/phase, scope and delivery state. Persist across restarts; give the worker a
bounded digest at a safe checkpoint and record acknowledgement. Show queued/seen
state in the UI. Reviewers must see applicable steering and its effective time.

Suggestions guide planning; they are not physical evidence or mandatory scripts.
Changed scientific requirements take effect prospectively, with a visible protocol
revision/branch. Existing experiments keep the instructions and contracts under which
they were run. Do not mutate completed claims or retrospectively improve acceptance
criteria. A steering note does not reset the deadline. Explicit stop/cancel commands
remain separate and act promptly under the existing process-identity checks.

## Release requirements highlighted by this run

The last study produced an empty independent-review result after8192output tokens,
then paused near its deadline. Numerous oversight calls also failed. rc3 should detect
empty/truncated output explicitly, preserve finish reasons and accurate usage, apply
bounded recovery with suitable review input/output allocation, and stop repeated
identical failing oversight from consuming the campaign. Never convert failure into
approval. Derive UI/report status from reconciled supervisor/job/deadline state so a
stopped expired run does not display “running”.

Tests should cover expired-parent continuation, immutable parent hashes, scoped
qualification/evidence inheritance, active-parent snapshots, backend changes, queued
steering across restart, idempotent delivery, reviewer visibility, prospective contract
revision, deadline preservation, empty review recovery and stale-status reconciliation.
Use a short real provider/solver continuation in addition to tests before release.

## Proposed external guidance for the Z-pinch continuation

Preserve the existing radial baseline. The next question is which energy-transfer
route explains radiation in a defined stagnation window, not merely whether cumulative
radiation can exceed instantaneous kinetic inventory.

1. Independently measure boundary Poynting/material flux and numerical correction
   terms. The previous eblib defines W_closure=dE+E_rad and W_EM_t=E_total-E_initial+
   E_rad. These are useful consistency quantities, not independent measurements of
   electromagnetic supply. An alternative boundary estimator matching an operator
   delta at one resolution is insufficient validation of all energy pathways.
2. Separate integrated whole-history radiation from a specified stagnation pulse,
   with explicit event definition, energy band and kinetic measurement time. The
   2006 Haines paper's motivating observation concerns a roughly5ns stagnation pulse;
   our20/40ns accumulated energies are not directly the same observable.
3. Run resolved axially varying RZ controls to examine compression/hotspots and m=0
   structure, then selected3D controls permitting non-axisymmetric modes. Choose
   resolution and possibly AMR from relevant wavelengths/core/current-sheet scales,
   not an arbitrary replacement of Nz=4 with a larger number. Keep symmetry controls
   as controls. A restricted axial domain needs explicit wavelength/domain checks.
4. Distinguish current transfer/secondary impacts from instability-mediated heating
   by their current profiles, timing, ion/electron temperatures and energy transfers.
   Treat physical viscosity separately from numerical dissipation; an unresolved
   heating term is not evidence for the viscous-heating hypothesis. Retain freedom
   to revise the investigation when measured scales invalidate a proposed closure.

Primary literature to guide discriminating observables, not dictate the conclusion:

- Ivanov et al. (2013), current transfer into radiatively preheated trailing plasma
  and secondary implosions: https://doi.org/10.1103/PhysRevE.88.013108
- Haines et al. (2006), instability-mediated ion viscous heating as a proposed
  explanation of stagnation-pulse excess: https://doi.org/10.1103/PhysRevLett.96.075003

These mechanisms arise in different experimental/model contexts; do not splice them
into one validated regime. The next brief should select a data anchor or remain an
explicitly idealized mechanism study. Neither this brief nor user steering can waive
scientific uncertainty, fresh tests or independent review.
