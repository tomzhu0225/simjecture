# DINA-PS guided setup

Upstream: https://github.com/iterorganization/DINA-IMAS
Inspected revision: `5c04815895832b55cf13527a86bec7c4ad5f9065`.
Use the README, `machines/iter/` scenarios and `imas/iwrap/` workflow sources.
The public release is the DINA-PS module, not the whole JINTRAC/HFPS suite.

The setup script assumes site environment modules for IMAS, XMLlib and iWrap.
`pip install imas-python` alone does not provide the Fortran IDS modules, XML
libraries and generated actors required by that full workflow. Check each
requirement before claiming the scenario simulator is usable.

The native core can be tested separately with GNU Fortran:

```sh
make FC=gfortran dina controllers -j4
```

Supply `FC=gfortran` explicitly: Make's default `f77` does not match the upstream
compiler selection. Preserve source revision and build log. The resulting
`src/green/test.exe` is a magnetic geometry/circuit component test, not a full
plasma scenario. It reads `tokamak_config.dat` from its working directory;
the upstream file is in `machines/iter/`. Keep generated matrices in a separate
run directory. Do not describe this partial test as a complete DINA installation.

A full workflow needs coil/passive structure and wall geometry, initial IDSs,
pulse schedule, code parameter XMLs, atomic data and an appropriate controller.
Follow the upstream scenario configuration, distinguish prescribed profiles from
self-consistently evolved quantities, and check current/shape tracking and time
resolution. Do not assume a standalone test executable uses arbitrary scenario
inputs without reading its fixed dimensions and interfaces.

The GUI provides **Install with agent** for that environment preparation. Register
only the workflow whose real numerical readiness example has passed, with build
and machine input identities. Other complete components may be registered under
an explicitly narrower capability name.

The 2026-09-29 local core/controller build succeeded. The supplied GREEN test,
using `machines/iter/tokamak_config.dat`, completed and reported 102 passive
structures, 12 active coils, 24 loops, 48 probes and 8385 grid points. This is
recorded as a component test only; no full scenario evolution is claimed.
