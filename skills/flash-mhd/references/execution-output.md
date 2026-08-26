# Execution and output

Read this reference when constructing a FLASH run or interpreting its files.

## Before execution

Record or obtain from the capability descriptor:

- the FLASH release and executable digest;
- the compiled simulation unit, setup options, dimensions, grid backend, I/O,
  and included physics implementations;
- the MPI implementation, rank count, OpenMP settings, and launcher arguments;
- hashes of the runtime parameter file and any workspace initialization or
  analysis programs.

Do not infer compiled features from runtime parameters. FLASH setup selects
implementations before compilation; an accepted but inactive parameter is not
evidence that its physical term was realized.

## Launching

FLASH accepts a runtime parameter file through `-par_file`. Pass commands as an
argument vector, without a shell. Use only the launcher and process topology
qualified for the installed capability. The presence of an MPI executable on
the host does not prove that it is compatible with the FLASH build.

Run each attempt in a distinct workspace directory. Preserve standard output,
standard error, the FLASH log, the exact parameter file, and the realized
output inventory. Bound workbench attempts with a timeout and stop retrying an
unchanged deterministic failure.

Before registering a long evidence command, use at least one shorter
non-evidentiary pilot at the intended resolution and process topology. When
startup, checkpoint, or first-output cost is significant, use two short pilot
durations to estimate both fixed cost and marginal cost per unit simulated
time. Check the estimate against the command timeout, campaign wall budget, and
workspace ceiling with explicit safety margin. A pilot may qualify feasibility
or document a resource blocker, but its measurements do not become scientific
evidence. If the complete prospective command cannot finish within the hard
limit, record a resource/instrument limitation rather than treating partial
output as a physical counterexample or silently shortening the protocol after
seeing results.

Use `examples/runtime_smoke.py` only through a capability that provides
`FLASH_EXECUTABLE`, `FLASH_MPI_LAUNCHER`, `FLASH_PREFLIGHT_PARFILE`, and
`FLASH_MPI_RANKS`. The script copies the operator-prepared parameter file into
the writable workspace, verifies MPI process completion, and reads back fresh
HDF5 output. Those checks are interface checks, not a physical commissioning
contract.

## Reading output

FLASH plot and checkpoint files are typically HDF5. Read their metadata rather
than assuming variable order, array orientation, block layout, coordinate
placement, or refinement level. In particular:

- decode the stored variable names;
- use block coordinates and bounding boxes to place data;
- distinguish cell-, face-, and node-centered quantities;
- retain units and normalization from the realized model;
- reconstruct derived fields from authoritative stored variables when a
  diagnostic variable is absent or stale;
- distinguish checkpoint state from reduced plot output.

Write compact JSON analysis summaries with a top-level `checks` object and
quantitative metrics supporting each boolean. Preserve the analysis source and
raw data that determine those metrics.

## Failure interpretation

A clean exit proves only that the executable returned successfully. Unknown
runtime parameters, missing compiled units, timestep collapse, positivity
repairs, excessive divergence error, output corruption, or launcher mismatch
can invalidate an otherwise completed run. Separate these outcomes:

- **interface failure:** executable, launcher, input, or output path failed;
- **numerical failure:** the requested discretization did not produce a usable
  solution;
- **model limitation:** FLASH ran, but the compiled fluid model cannot decide
  the claim;
- **scientific result:** available only after prospective commissioning and
  the applicable controls.
