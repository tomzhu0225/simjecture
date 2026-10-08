# Proposed demo: discover the material-model dependency

**Design proposal only. No campaign has been launched and no result is claimed.**

The aim is to test whether a worker identifies a missing physical ingredient and
selects an appropriate instrument without being told which tool to call. The
worker-facing `brief.txt` gives a radiation-heating question and physical scope;
it does not prescribe an EOS generator, table format, opacity package or sequence
of tool calls. Supply the ordinary tool catalogue and scientific skills, not an
answer-bearing checklist in the worker prompt.

A useful finite case is hydrogen heating through a partially ionized regime.
A constant-heat-capacity approximation is testable through deposited-energy and
temperature increments, while thermodynamic state and radiation transport remain
separate parts of the problem. The exact density and drive need commissioning;
the numbers in the brief do not establish a qualified FLASH application.

## Operator preparation

- Commission a radiation-capable FLASH build through the actual experiment
  launcher, including readable fields and energy diagnostics. Expose its source
  and table interfaces without prescribing a material closure.
- Make the tool catalogue truthful. EOS tools that evaluate an existing closure
  differ from atomic-physics generators. An electronic EOS alone is not a complete
  material EOS, and an EOS is not an opacity model. Confirm runtime availability
  and redistributable input data before starting a timed study.
- Preserve the worker's original brief. Do not insert a late instruction to use
  an EOS package and then describe that choice as unprompted discovery.
- Give the reviewer the physical claim and evidence, including the selected
  closure and its validity range. A separate retrospective records tool selection;
  it should not reward unnecessary calls or force a particular vendor/code.

## What would demonstrate the behavior

The record should show the worker recognizing whether its initial material model
can answer the question, choosing a suitable source or generator if needed,
checking units/coverage/thermodynamic consistency, and tracing the resulting data
into the actual FLASH run. Preserve the table hash, generation or acquisition
provenance, conversion source, realized FLASH parameter file, bounds encountered,
and a control that tests the table/closure's effect on the reported result.

Choosing a defensible published table can be as good a decision as generating a
new one. Simply calling an EOS tool, writing an unread table, relabelling an ideal
gas table as ionization physics, or using an unqualified material parameter set
would not establish successful tool selection. A discovered dependency that cannot
be supplied honestly is an informative unresolved outcome.

## Release scope

This is a candidate follow-up to the FLASH-to-WarpX study for the documentation
refresh. It has no allocated inference budget yet. Publish it as a recorded demo
only after a real run, scientific review and a provenance audit; until then it
remains a proposal rather than a result in the public demonstration gallery.
