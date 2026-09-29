---
name: iter-pack
description: Install and use the ITER ecosystem diagnostics/data pack (CHERAB, Raysect, CHERAB-IMAS, CHERAB-ITER and IMAS), or prepare guided SOLPS-ITER, JOREK and DINA-PS integrations. Use for synthetic diagnostics, fusion data interchange and these named solvers.
---

# ITER ecosystem research tools

This is a Simjecture integration of upstream projects, not an ITER-endorsed product.
The automatic `iter-pack-1.0` capability contains diagnostics and data tools.
It does **not** contain SOLPS, JOREK or DINA solver executables.

## Choose the relevant interface

- For installation, numerical demos, output formats and synthetic diagnostic research,
  read [diagnostics.md](references/diagnostics.md).
- For edge plasma / neutrals, read [solps.md](references/solps.md).
- For nonlinear MHD, read [jorek.md](references/jorek.md).
- For equilibrium evolution / coil control, read [dina.md](references/dina.md).

Use the actual installed capability shown by the tool catalogue. Read its build
record; a skill being available does not mean its solver is installed. Source
and upstream examples remain useful even when an installation is incomplete.

## Execute through Simjecture

In minimal mode, copy the relevant example into the research workspace and use
`lab.run` with capability `iter-pack-1.0`, Python script arguments, explicit inputs
and fresh output paths, following the generated `lab.py` guide. Use exploration
for readiness/debugging; commit the method and measurements before evidence runs.
In classic mode use the named capability execution tools, not generic `run_python`
(which does not contain these optional packages). In interactive preparation use
`start_simulation` for a monitored job, or the documented bounded shell interface.

The packaged demo writes `iter_pack_demo.json`, `iter_pack_demo.png`, `spectra.csv`,
`profiles.nc`, and a local `cache/` directory. Its checks establish only analytic
ray tracing, continuum scaling, schema I/O, mock camera construction and geometry
extension arithmetic. They do not validate a real tokamak diagnostic or discharge.

For research, retain the source simulation identity, geometry, atomic data source,
units, wavelength response, viewing directions and uncertainty estimates alongside
signals. Distinguish a forward signal from an inferred profile. Counterexamples
may concern diagnostic ambiguity or reconstruction bias as well as plasma physics.
