# Diagnostics and analysis

WarpX PICMI supplies several output routes:

- `FieldDiagnostic` for selected mesh quantities such as electric and magnetic
  fields, current, and charge density;
- `ParticleDiagnostic` for selected particle position, momentum, and weighting
  records;
- `ReducedDiagnostic` for compact time series such as field or particle
  energy; and
- checkpoint diagnostics for restart rather than scientific interpretation.

For the pinned runtime, select mesh records with the PICMI keyword
`data_list`, for example `FieldDiagnostic(..., data_list=["E", "B", "J",
"rho"])`. `field_data` is not accepted by the installed PICMI standard.

Field and particle diagnostics can use openPMD output. The installed WarpX
runtime includes `openpmd_api`; analysis programs executed with the capability
can read those records. Ordinary sandbox Python may be used for portable array
analysis if data are first exported to formats available there.

The exact pinned PICMI keywords are WarpX-prefixed. For file-based HDF5 output
use, for example:

```python
picmi.FieldDiagnostic(
    name="fields",
    grid=grid,
    period=diagnostic_period,
    data_list=["E", "B", "J", "rho"],
    write_dir="openpmd_diags",
    warpx_format="openpmd",
    warpx_openpmd_backend="h5",
    warpx_openpmd_encoding="f",
)
```

The generic keyword `format="openpmd"` is rejected by the installed
`picmistandard` constructor, while omitting `warpx_format` silently selects the
default AMReX plotfile format. Inspect the used-inputs record for
`<name>.format = "openpmd"` and `<name>.openpmd_backend = "h5"`, and verify
that nonempty `.h5` records can actually be opened before qualifying the
diagnostic path. Read `examples/openpmd_field_smoke.py` for a bounded wiring
and readback example.

Iterate records with `for index in series.iterations` and use that `index` as
the iteration number. The installed `openpmd_api` `Iteration` object has
`time` and `meshes` but **no** `.iteration` attribute; `int(it.iteration)`
raises `AttributeError` after a successful WarpX write. See
`examples/openpmd_field_smoke.py`.

openPMD Python reads are deferred. Materialize each requested array before
closing its series:

```python
pending = component.load_chunk()
series.flush()
array = np.asarray(pending).copy()
series.close()
```

Do not close the series before `flush()`. Converting an unflushed pending read
can yield uninitialized values without a useful exception.

Choose outputs prospectively from the observable and falsifier. Record units,
component names, spatial selection, mode projection, time window, filtering,
normalization, and uncertainty calculation. A visually plausible plot is not a
defined estimator. When practical, derive the same physical quantity through
two genuinely different diagnostic paths and test their agreement.

Output completeness, finite values, expected iteration indices, and nonempty
particle/mesh records are execution-health checks. Conservation, convergence,
statistical reproducibility, and agreement with an analytic limit are
scientific commissioning checks. Neither category should be inferred from a
zero process exit code.

## Reduced energy accounting

Read and preserve the header of every reduced-diagnostic text file before
selecting columns. In the pinned single-level runtime, `FieldEnergy` writes the
total grid-field energy in column 2 (`total_lev0(J)`), while `ParticleEnergy`
writes total particle kinetic energy in column 2 (`total(J)`), followed by
per-species totals and then mean-energy columns. Do not sum the species totals
again with `total(J)`, and do not mistake a decline in field energy alone for
loss of total energy.

For the pinned single-level schema, materialize
`scripts/reduced_energy_budget.py` and run it with the field and particle files
instead of reimplementing column selection. The script selects totals by exact
realized header labels, verifies aligned step/time rows and finite values, and
fails on an unknown schema. Never replace its selection with slices such as
`field[:, 2:].sum(...)` or `particle[:, 2:].sum(...)`; those silently add total
columns to the components they already contain.

For a closed, source-free calculation, first assert that the field and particle
rows have identical step/time coordinates, then form the budget explicitly:

```python
field = np.atleast_2d(np.loadtxt("reduced/field_energy.txt"))
particle = np.atleast_2d(np.loadtxt("reduced/particle_energy.txt"))
assert np.array_equal(field[:, 0], particle[:, 0])
assert np.allclose(field[:, 1], particle[:, 1], rtol=0.0, atol=1.0e-30)
total = field[:, 2] + particle[:, 2]
relative_drift = (total[-1] - total[0]) / abs(total[0])
```

Report the field, particle, and combined histories together so energy transfer
cannot be confused with non-conservation. If the model has absorbing or open
boundaries, external fields or sources, collisions, radiation, particle
injection/removal, or another energy channel, add the corresponding boundary
flux/work/source terms before calling the result a total-energy balance. For
AMR or a different diagnostic schema, derive the non-overlapping total from the
realized headers and documented semantics instead of assuming column 2 has the
same meaning. The bundled script intentionally rejects those schemas until their
non-overlap semantics are explicit. Preserve the analysis program and its
component table; a prose claim of conservation is not a commissioning check.

For in-situ access in the pinned runtime, `simulation.fields` exposes the
MultiFab registry. Fetch vector fields by registry name, physical component
direction, and level; the physical component direction is distinct from the
2D array axes. In a 2D build use, for example,
`from pywarpx.warpx_pybind_2d import Direction` followed by
`simulation.fields.get("Efield_fp", dir=Direction.y, level=0)`. Registry names
include `Efield_fp`, `Bfield_fp`, `current_fp`, and `rho_fp`. A returned
MultiFab provides coordinate meshes with `mesh("x")` and `mesh("z")`; its
staggering makes component shapes differ. Record centering, box layout, valid
slices, and guard-cell handling before combining arrays. Read
`2d-xz-commissioning.md` before using in-situ arrays in any 2D estimator.

Do not delay an experiment to reverse-engineer in-situ particle containers.
Use `ParticleDiagnostic` plus openPMD for portable particle positions,
momenta, and weights unless the observable truly requires an in-step callback.
The legacy `pywarpx.particle_containers.ParticleContainerWrapper` and
`pywarpx.fields.*Wrapper` helpers are deprecated in this runtime.

When imposed particle fields coexist with self-consistent fields, a diagnostic
of `Efield_fp` alone need not be the total field gathered by particles. Preserve
and analyze the external contribution separately, and define the observable's
field source prospectively.
