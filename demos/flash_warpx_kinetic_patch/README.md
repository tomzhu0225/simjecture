# From a FLASH current sheet to a kinetic WarpX patch

**The two-hour autonomous study ran actual FLASH-to-WarpX transfers and completed
spatial, timestep, particle-count and boundary controls. It ended unresolved at
the cutoff, with no accepted scientific verdict.** Guided commissioning passed
on CPU and CUDA through the actual experiment launcher before the research clock.

Read the [recorded investigation](../../docs/demos/flash-warpx-patch.md) for the
source-to-patch relationship, measured results, failures and remaining gaps.
The [compact audit](record/manifest.json) retains 581 files and all 40 execution
receipts, with bulk states explicitly omitted. Verify it without a model call:

```bash
uv run python scripts/verify_research_audit.py demos/flash_warpx_kinetic_patch/record
```

This example investigates whether a resolved MHD current sheet remains adequately
represented by isotropic ion/electron pressures when followed with collisionless
kinetic dynamics at ion scales. The worker must connect its FLASH and WarpX
calculations through measured state data and test the transfer and boundaries.

The operator's [hypothesis](hypothesis.txt) and [instructions](instructions.txt)
define the scope and a two-hour budget. GPT-6.1 Sol is selected for the worker and
a separate high-effort review context. The agent chooses the source state, patch,
measurement and numerical controls. The supplied helper defaults establish
execution readiness and are not qualified scientific settings.

The operator-provided starting tools are:

- `guided/flash_islands.py`: run the operator-supplied FLASH island application.
- `guided/extract_flash.py`: retain normalized fields/moments and reconstruct a
  flux potential, with source/time/hash and coordinate provenance.
- `guided/prepare_patch.py`: map the state into SI units, construct a
  divergence-free Yee-grid magnetic field, partition scalar pressure and match
  current plus center-of-mass flow with ion/electron drifts.
- `guided/kinetic_patch.py`: initialize and evolve those data with WarpX, recording
  fields, energies and locally binned pressure tensors.

This is a **one-way local kinetic continuation**, not a two-way embedded PIC
coupler. The normalized FLASH state does not determine a unique physical length,
species or collisionality; those choices must be explicit. A kinetic difference
can arise from changed closure, initial relaxation or boundaries, so field
transfer success alone cannot validate the physical hypothesis.

The guiding literature is [Li et al. (2023)](https://arxiv.org/abs/2212.07980) on
island coalescence with adaptively embedded PIC and
[Makwana et al. (2017)](https://arxiv.org/abs/1708.02877) on two-way MHD–PIC coupling.
They motivate this local test and its controls; this demonstration does not
implement their coupling algorithms or inherit their validation.

FLASH source/binaries remain operator-supplied. The public scripts and small
commissioning summaries contain no FLASH-owned implementation. A complete fresh
run additionally needs qualified FLASH and WarpX capabilities and a configured
agent backend.
