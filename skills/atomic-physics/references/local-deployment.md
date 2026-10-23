# Local deployment

Install with `simjecture install fac`; check with `simjecture doctor --profile fac`.
The equivalent source-checkout commands are `uv run simjecture install fac`
and `uv run simjecture doctor --profile fac --json`.

This profile builds FAC revision `6196889ac611f909dd99366fe447486411e27950`,
whose internal version is 1.1.5, in `.runtime/fac-1.1.5`. It uses managed
Python, NumPy, SciPy, C/Fortran compilers, and OpenMP. It installs the SFAC,
SCRM, and SPOL command-line programs; it does not install the PFAC extension.

`--source DIR` accepts an existing Git checkout at that revision. The bootstrap
fetches the committed source into its own build copy and leaves the supplied
tree untouched. `--dry-run` plans installation; `--repair` rebuilds a managed
runtime. Existing unmanaged directories are preserved.

FAC's core is GPL-3.0 and bundled numerical dependencies retain their notices.
The independently written Simjecture adapter does not relicense FAC. Source
and binaries remain in the ignored runtime. Upstream source and license:
<https://github.com/flexible-atomic-code/fac>.

The runtime's `share/build-record.json` records the source revision, executable
hashes, and LTE helper hash. Capability identity includes all three executables
and `share/fac_lte.py`. Reinstall after changing the helper; a working-tree
edit does not change an existing runtime's helper.

The doctor probe computes hydrogen 1s–2p lines and checks energy/oscillator
strength limits. It is permanently non-evidentiary and does not qualify W.
