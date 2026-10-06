# Runtime and interface

The driver is `$SIMJECTURE_LBM_DRIVER`; the original solver is
`$SIMJECTURE_LBM_SOURCE`. These environment paths work inside the capability.
The runtime contains Python, Warp 1.14.0, NumPy 2.0.1 and Matplotlib 3.10.9.

Example arguments for the copied `run_cylinder.py`:

```text
--re 100 --nd 32 --speed 0.06 --height 80 --length 80 --inlet 40
--time 300 --side-sponge 8 --outlet-sponge 6 --device auto --out outputs
```

`--height` is the full domain height, `--length` the total streamwise length,
and `--inlet` the upstream distance from the cylinder centre, all in D. Outlet
distance is length minus inlet. `--nd` is cells per cylinder diameter, not the
total radial or axial cell count. The example has 2560×2560 cells and 160,000 steps.

Useful options: `--wall far|slip|noslip|periodic`, `--psm nt|linear`,
`--interface-width` in lattice cells, `--rotation` in U/R,
`--shape-a`/`--shape-b` as up to four comma-separated radial Fourier harmonics,
`--angle` in degrees, `--fp64`, and `--solver-source` for a project-owned modified
copy. `--steps` overrides the requested integration count for commissioning.
`--max-cells` defaults to 50 million as a per-launch allocation guard and can be
chosen explicitly for a resource-qualified larger study.

The driver disables LES by default. The contributor's direct Python/CLI interface
also offers Smagorinsky and surface-jet options; inspect its source before using
them. Surface jets prescribe an interface velocity, not a separately conserved
mass source. Noncircular geometry does not rotate in time when its solid velocity
is changed. Circular-cylinder rotation is compatible with the unchanged geometry.

The two FP32 population buffers need approximately `72*nx*ny` bytes of GPU memory,
plus context, force and diagnostic allocations. Estimate time from an actual
pilot on the selected machine. Hardware and statistics/output costs affect MLUPS.
The GPU sandbox monitors resident RAM, because CUDA reserves a large virtual
address range. WSL requires its Windows-provided CUDA libraries; the installer
detects `/dev/dxg` and supplies the corresponding library path.
