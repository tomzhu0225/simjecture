# Execution and output

Read this reference when constructing an Optab run or interpreting its files.

## Before execution

Record or obtain from the capability descriptor:

- the Optab revision and executable digest;
- MPI launcher, rank count, and compiler/HDF5 identity from the build record;
- hashes of `input/fort.5`, the abundance table `input/eos.h5`, species lists,
  and every atomic or Gaunt-factor database the switches require.

Optab reads `input/` relative to the process working directory. Missing files
are interface failures, not zero opacity.

## Launching

Use only the launcher and rank count declared by the capability. Pass argv
without a shell. The smoke copies the operator-prepared preflight tree to
workspace `input/`, creates `output/`, and invokes the MPI launcher.

Required environment:

- `OPTAB_EXECUTABLE`
- `OPTAB_MPI_LAUNCHER`
- `OPTAB_MPI_RANKS`
- `OPTAB_PREFLIGHT_INPUT`

`examples/optab_runtime_smoke.py` is permanently non-evidentiary.

## Reading output

Optab writes monochromatic and mean **volume coefficients** (cm\(^{-1}\)) plus
density. Mass opacity is coefficient divided by mass density. Typical HDF5
fields include wavenumber grid, absorption, scattering, line, Planck mean, and
Rosseland mean. Decode names and units from the file; do not assume a group
structure used by another radiation code.

Preserve the abundance table with the run. An opacity result is undefined
without the exact number densities that produced it.

## Failure interpretation

Separate these outcomes:

- **interface failure:** executable, launcher, input tree, or HDF5 path failed;
- **numerical failure:** the frequency grid, means, or I/O did not produce a
  usable table;
- **model limitation:** enabled processes or atomic range cannot decide the
  claim;
- **scientific result:** available only after prospective commissioning.
