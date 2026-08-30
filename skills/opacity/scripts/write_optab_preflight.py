#!/usr/bin/env python3
"""Write a cheap fully ionized hydrogen Optab input tree for the doctor probe."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

N_SPECIES = 11000
RHO_G_CM3 = 1.0e-6
TEMPERATURE_K = 1.160451812e5  # 10 eV
M_U_G = 1.66053906660e-24
TOTAL = 1
ELECTRON = 10
H_II = 101

FORT5 = """&switches
line_molecules = 0
line_kurucz_phoenix = 0
line_kurucz_gfpred = 0
line_kurucz_gfall = 0
rayleigh_scattering_h2 = 0
rayleigh_scattering_he = 0
rayleigh_scattering_h = 0
electron_scattering = 1
cia = 0
photoion_h2 = 0
photoion_topbase = 0
photoion_mathisen = 0
photoion_verner = 0
photoion_h_minus = 0
brems_h_minus = 0
brems_h2_minus = 0
brems_atomicions = 1
/
&radtemp
temp2 = 1.160451812d5
/
&block_cyclic
iblock = 1
/
&grid_log_const
k_total = 16
grd_min = 3d0
grd_max = 6d0
/
&mpi_decomp
kprc = 1
lprc = 1
mprc = 1
jprc = 1
/
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    (root / "h5").mkdir(exist_ok=True)
    (root / "1016620_Supplementary_Data").mkdir(exist_ok=True)
    (root / "fort.5").write_text(FORT5)
    (root / "mol_source.dat").write_text("")
    n_h = RHO_G_CM3 / (1.008 * M_U_G)
    ndens = np.zeros((1, N_SPECIES), dtype=np.float64)
    ndens[0, H_II - 1] = n_h
    ndens[0, ELECTRON - 1] = n_h
    ndens[0, TOTAL - 1] = 2.0 * n_h
    import h5py

    with h5py.File(root / "eos.h5", "w") as handle:
        handle.create_dataset("n_layer", data=np.array([1], dtype=np.int32))
        handle.create_dataset("n_species", data=np.array([N_SPECIES], dtype=np.int32))
        handle.create_dataset(
            "temp", data=np.array([TEMPERATURE_K], dtype=np.float64)
        )
        handle.create_dataset("rho", data=np.array([RHO_G_CM3], dtype=np.float64))
        handle.create_dataset("ndens", data=ndens)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
