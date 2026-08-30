# Execution and output

Read this reference when constructing an EOS evaluation or interpreting its
files.

## Before execution

Record or obtain from the capability descriptor:

- the package name, version, and executable digest;
- the named model, composition or parameter input, and unit system;
- hashes of workspace programs and any material input files.

Do not infer a model from a package name. Singularity-EOS in particular exposes
many closures; only the constructed type was evaluated.

## Launching

Pass commands as an argument vector, without a shell. Run each attempt in a
distinct workspace directory. Preserve standard output, standard error, the
exact input, and the realized output inventory.

The capability smokes are interface checks, not physical commissioning:

- `atomec-1.4.0` uses the runtime interpreter and imports `atoMEC`.
- `singularity-eos-1.12.1` uses `SINGULARITY_EOS_QUERY` when set, otherwise the
  `singularity_eos` Python module.
- `m-aneos-1.0` uses `MANEOS_QUERY` and copies `MANEOS_PREFLIGHT_INPUT` to
  `ANEOS.INPUT` in the workspace.

## Query JSON contract

Scientific and smoke programs should write compact JSON with a top-level
`checks` object and scalar fields sufficient to audit the evaluation. When a
query driver is used, prefer this result shape:

```json
{
  "schema_version": "0.1.0",
  "package": "singularity-eos",
  "model": "IdealGas",
  "units": "cgs",
  "density": 1.0,
  "temperature": 1.0,
  "pressure": 0.6666666666666666,
  "specific_internal_energy": 1.0,
  "specific_heat": 1.0
}
```

Declare density, temperature, pressure, energy, and heat-capacity units in the
same document. Singularity-EOS defaults to CGS (g/cm\(^3\), K, dyn/cm\(^2\),
erg/g, erg/(g K)). atoMEC native electronic energies are Hartree per ion and
pressures Hartree per Bohr cubed unless the program converted them. M-ANEOS
`ANEOSV` uses CGS with temperature in eV.

## Singularity query driver

When `SINGULARITY_EOS_QUERY` is set, the operator-built driver accepts:

```text
eos-query IdealGas RHO_G_CM3 TEMPERATURE_K GM1 CV OUTPUT.json
eos-query IdealElectrons RHO_G_CM3 TEMPERATURE_K ABAR ZBAR OUTPUT.json
```

`IdealElectrons` still requires \(\bar{Z}\) as an input. A successful query
proves only that the named closure evaluated.

## M-ANEOS query driver

When `MANEOS_QUERY` is set, the operator-built driver accepts:

```text
maneos-query RHO_G_CM3 TEMPERATURE_EV OUTPUT.json
```

It reads `ANEOS.INPUT` from the current working directory. Initialization
output is not scientific evidence.

## Failure interpretation

Separate these outcomes:

- **interface failure:** executable, input, or output path failed;
- **numerical failure:** SCF, table lookup, or phase logic did not produce a
  usable state;
- **model limitation:** the named closure cannot decide the claim;
- **scientific result:** available only after prospective commissioning.
