# Execution and output

The capability launches a workspace Python program. Use `subprocess.run` with
an argument list and a finite timeout to call `os.environ["FAC_SFAC"]`,
`FAC_SCRM`, or `FAC_SPOL`. Write a separate log and input file per calculation.
Each process has its own working directory. The default `OMP_NUM_THREADS=1`
can be changed for a commissioned run; record it.
To activate FAC's OpenMP work sharing, also call `InitializeMPI(thread_count)`
as the first SFAC command and `FinalizeMPI()` at the end. Setting the environment
alone does not establish that FAC initialized parallel execution. Validate a
small serial/parallel comparison before relying on a new parallel procedure.

FAC's installed reference manual and source are under `src/fac` in the
runtime. In a capability sandbox the runtime is mounted at
`/opt/acs-capabilities/fac-1.1.5`. `FAC_LTE_HELPER` points to the installed
helper; use `runpy.run_path` to access its functions, or invoke it with the
runtime's `sys.executable`.

The helper's input JSON contains:

- `description`: the actual configuration, charge-state, and process scope;
- `atomic_mass_u`: the mass used to convert per-ion absorption to mass opacity;
- `ions`: a list of objects with `levels` and `transitions`, paths relative to
  the JSON file for verbose FAC EN and TR tables, respectively.

Each EN file must describe one ion. Charge states must be distinct and
adjacent. All ions must belong to one element. Both detailed and UTA formats
are recognized. TR blocks must explicitly use `MULTIP=-1` for E1 or `+1` for
M1; summed/default multipoles are rejected to avoid ambiguous process labels.

Required command options are `--model`, `--output` (a prefix),
`--temperature-ev`, `--electron-density-cm3`, `--ion-temperature-ev`,
`--energy-min-ev`, `--energy-max-ev`, and `--bins`. Physical temperatures and
density must be positive. `--instrument-sigma-ev` adds a Gaussian standard
deviation in eV and defaults to zero. `--no-uta-ci` disables the separately
printed UTA strength multiplier for a declared sensitivity comparison.

The helper derives ion fractions from the isolated-ion partition functions,
the absolute EN energy references, and ideal nondegenerate Saha electrons.
It infers mass density from charge neutrality, `rho = ne A m_u / Zbar`.
The mass density is an output, not a second independent input.

For a transition with center E, the integrated mass absorption is proportional
to `x_q * exp(-E_lower/T) / U_q * gf * (1-exp(-E/T))`. The lower-level
weight cancels the statistical weight in `gf`. The net absorption includes
stimulated emission at the transition center. The Gaussian profile integrates
analytically over each output bin; there is no renormalization to the finite
photon window. UTA widths are standard deviations, not FWHM.

The `.npz` output contains `energy_edges_eV`, `e1_cm2_g`, `m1_cm2_g`, and
`net_bound_bound_cm2_g`, with opacity values averaged over bins. The `.json`
output records populations, mean charge, inferred density, transition counts,
input/helper/output hashes, omitted physics, the summed population at the
charge-window boundaries, and captured spectral areas. These checks verify
representation properties only. They do not label the model predictive.

No Rosseland mean, complete material table, or radiation-hydrodynamics export
is supplied: spectral gaps and omitted processes must be resolved first.
