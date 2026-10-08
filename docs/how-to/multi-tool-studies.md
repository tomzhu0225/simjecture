# Combine scientific tools in one study

A study can use different instruments for different parts of a question. A fluid
simulation may identify a region for a kinetic follow-up; a radiation calculation
may need a material table from another package. The worker can choose those tools
from the advertised catalogue rather than receive a fixed sequence of commands.
The resulting claim still needs a traceable chain of inputs and numerical checks.

## Expose instruments and give the physical question

Commission the required execution paths and give the study access to the relevant
capability descriptors. Describe the question, domain and resource budget in the
brief. State an instrument requirement when it matters scientifically, but leave
the experimental choices to the agent where possible.

The minimal service's `required_capability_prefixes` is an **any-of** allowance:
one matching family satisfies that particular instrument check. Listing FLASH and
WarpX there does not mechanically require evidence from both. Put a two-solver
requirement in the immutable study brief and require the reviewer to inspect both
sets of receipts and their data relationship.

Installed tools and their model validity are separate facts. For example, an EOS
interpolator cannot generate missing atomic physics, and an opacity model is not
an EOS. A missing dependency should lead to an explicit tool/model decision, not
an invented table or an unrelated substitute simulation.

## Preserve the handoff

Record the upstream experiment, actual output time, source file hash and the code
that creates the downstream input. Each submission has its own workspace. Declare
the transferred data and its metadata in `inputs`; files in another experiment
are not automatically available in the next one.

| Handoff | Information needed to interpret it |
|---|---|
| Fluid state → kinetic patch | Coordinates, units, physical scale, species, temperature partition, field/current/charge consistency, interpolation and boundary assumptions |
| Material generator → radiation solver | Composition, thermodynamic variables and units, model/data provenance, coverage, interpolation, conversion, consistency checks and actual table consumption |
| Simulation → diagnostic | Source state/time, control volume, normalization, estimator, output cadence and numerical uncertainty |

Treat conversion and interpolation as numerical methods. Test them on a case
with independently known quantities, then inspect the realized downstream state.
A file that loads successfully may still have swapped coordinates or the wrong
energy normalization. The [island audit](../demos/island-coalescence.md#post-run-correction-a-half-cell-error-in-the-diagnostic)
shows a concrete failure: mixing cell-centre and boundary origins produced false
15%-threshold rejections. A known analytic potential exposed the error that the
worker and its reviewer had missed.

## Review the combined conclusion

Use exploration and `lab.analyze` while preparing a method, then submit the
relevant source, runtime, input identities and validation receipts with
`lab.method`. Changed source or inputs require the applicable new review. Fresh
evidence must match the reviewed method and any committed repair.

The reviewer should distinguish what each model can establish. A collisionless
kinetic patch initialized from a resistive-MHD snapshot is a local follow-up;
its rate is not automatically a corrected global MHD rate. An EOS evaluation
alone does not establish radiative transport. Compare controls that can separate
handoff artifacts from the physical mechanism being claimed.

The [FLASH-to-WarpX example under commissioning](https://github.com/tomzhu0225/simjecture/tree/main/demos/flash_warpx_kinetic_patch)
provides source-controlled transfer helpers and clearly labels its current
qualification status. The separate
[radiation tool-selection proposal](https://github.com/tomzhu0225/simjecture/tree/main/research/proposals/tool-selection-radiation)
is a prospective design, not a recorded result.

See [guided commissioning](guided-commissioning.md),
[the minimal research API](research-service.md) and
[the evidence model](../concepts/evidence-and-claims.md).
