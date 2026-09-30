"""Numerical holdouts, not additional physical simulation evidence."""

import csv
import random


def create(root, task, seed):
    rng = random.Random(seed)
    cases = {}
    for index in range(3):
        folder = root / f"holdout-{index}"
        folder.mkdir(parents=True)
        clocks = [value * rng.uniform(0.9, 1.1) for value in (0.2, 0.8, 2, 3.1, 5.2, 9)]
        increments = [rng.uniform(0.3, 4) * (i + 1) * 1e7 for i in range(6)]
        groups = list(range(1, index + 3))
        with (folder / "radiation_boundary.csv").open("w") as stream:
            writer = csv.writer(stream)
            writer.writerow(["group", "time_s", "dt_s", "escaped_energy_erg"])
            for clock, energy in zip(clocks, increments, strict=True):
                for group in groups:
                    writer.writerow([group, clock * 1e-9, 1e-10, energy * group / sum(groups)])
        with (folder / "operator_budget.csv").open("w") as stream:
            writer = csv.writer(stream)
            writer.writerow(
                ["tag", "time_s", "dt_s", "kinetic_erg", "magnetic_erg", "internal_erg"]
            )
            for clock, energy in zip(clocks, increments, strict=True):
                scale = rng.uniform(0.75, 1.25)
                writer.writerow(["radiation_before", clock * 1e-9, 1e-10, 8e8, 1e9, 2e9])
                writer.writerow(
                    [
                        "radiation_after",
                        clock * 1e-9,
                        1e-10,
                        8e8 - 0.1 * energy,
                        1e9 - 0.2 * energy,
                        2e9 - (scale - 0.3) * energy,
                    ]
                )
                writer.writerow(["unrelated_stage", clock * 1e-9, 1e-10, 1e20, 1e20, 1e20])
        if task == "rz-diagnostics":
            _fields(folder, index, rng)
        cases[folder.name] = folder
    return cases


def _fields(folder, index, rng):
    import h5py
    import numpy as np

    nr, nz = 5 + index, 2 + index
    shape = (3, 1, nz, nr)
    scale = rng.uniform(0.6, 1.4)
    for step, clock in enumerate((0, 1e-9, 2.3e-9, 4.6e-9, 8e-9)):
        with h5py.File(folder / f"stagnation_hdf5_plt_cnt_{step:04d}", "w") as file:
            file["real scalars"] = np.array(
                [(b"time", clock)], dtype=[("name", "S80"), ("value", "f8")]
            )
            file["node type"] = np.array([1, 2, 1])
            file["bounding box"] = np.array(
                [
                    [[0, 0.3], [0, 2], [0, 1]],
                    [[0, 0.6], [0, 2], [0, 1]],
                    [[0.3, 0.6], [0, 2], [0, 1]],
                ]
            )
            grid = np.broadcast_to(np.arange(nr), shape)
            rho = (
                np.ones(shape)
                * (index + 1)
                * 1e-5
                * scale
                * (1 + 0.2 * np.exp(-((grid - (nr - 1) * (1 - step / 6)) ** 2)))
            )
            rho[1] = 1e12  # Covered blocks must not contribute.
            vr = np.ones(shape) * (-1e6, -3e6, -5e6, -4e6, -2e6)[step] * scale
            vr[:, :, ::2, ::2] *= -0.25
            for key, value in {
                "dens": rho,
                "line": 0.8 + grid * 0.01,
                "velx": vr,
                "vely": np.ones(shape) * 2e6,
                "velz": np.ones(shape) * 1e6,
                "magx": np.ones(shape) * 0.1 * scale,
                "magy": np.ones(shape) * 0.2,
                "magz": np.ones(shape) * 0.3,
                "eint": np.ones(shape) * (1e12 + step * 2e11) * scale,
                "erad": np.ones(shape) * 1e9,
            }.items():
                file[key] = value
