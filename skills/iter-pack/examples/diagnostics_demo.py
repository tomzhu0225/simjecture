"""Offline numerical readiness demo; synthetic data, not an ITER discharge.

CHERAB's upstream bremsstrahlung example informed the API choices:
https://github.com/cherab/core/blob/v1.5.0/demos/emission_models/bremsstrahlung.py
No external ADAS line-emission tables or machine geometry are required.
"""

import json
import os
from importlib.metadata import version
from pathlib import Path

import imas
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cherab.core import Maxwellian, Plasma, Species
from cherab.core.atomic.elements import deuterium
from cherab.core.model import Bremsstrahlung
from cherab.openadas import OpenADAS
from raysect.optical import ConstantSF, Point3D, Ray, Vector3D, World
from raysect.optical.material.emitter import UniformVolumeEmitter
from raysect.optical.material.emitter.inhomogeneous import NumericalIntegrator
from raysect.primitive import Sphere
from scipy.constants import atomic_mass, electron_mass


def chord_demo():
    world = World()
    Sphere(1.0, parent=world, material=UniformVolumeEmitter(ConstantSF(1.0)))
    impact = np.linspace(0, 0.95, 20)
    observed = np.array(
        [
            Ray(
                origin=Point3D(float(b), 0, -3),
                direction=Vector3D(0, 0, 1),
                min_wavelength=400,
                max_wavelength=401,
                bins=1,
            )
            .trace(world)
            .samples[0]
            for b in impact
        ]
    )
    expected = 2 * np.sqrt(1 - impact**2)
    return impact, observed, expected


def plasma_spectrum(density):
    world = World()
    plasma = Plasma(parent=world)
    plasma.geometry = Sphere(1.0)
    plasma.atomic_data = OpenADAS()
    plasma.integrator = NumericalIntegrator(step=0.02)
    zero = Vector3D(0, 0, 0)
    plasma.electron_distribution = Maxwellian(density, 1000.0, zero, electron_mass)
    ions = Maxwellian(density, 1000.0, zero, deuterium.atomic_weight * atomic_mass)
    plasma.composition = [Species(deuterium, 1, ions)]
    plasma.models = [Bremsstrahlung()]
    return Ray(
        origin=Point3D(0, 0, -3),
        direction=Vector3D(0, 0, 1),
        min_wavelength=400,
        max_wavelength=800,
        bins=64,
    ).trace(world)


def imas_demo():
    dd = "3.39.0"
    profiles = imas.IDSFactory(dd).core_profiles()
    profiles.ids_properties.homogeneous_time = 1
    profiles.time = [0.0]
    profiles.profiles_1d.resize(1)
    profile = profiles.profiles_1d[0]
    rho = np.linspace(0, 1, 21)
    temperature = 100 + 900 * (1 - rho**2)
    profile.grid.rho_tor_norm = rho
    profile.electrons.temperature = temperature
    profile.electrons.density = 1e19 + 9e19 * (1 - rho**2)
    profiles.validate()
    with imas.DBEntry("profiles.nc", "w", dd_version=dd) as entry:
        entry.put(profiles)
    # Explicit DD version is needed: reading DD3 with the DD4 default fails.
    with imas.DBEntry("profiles.nc", "r", dd_version=dd) as entry:
        restored = entry.get("core_profiles")
        restored.validate()
        actual = np.asarray(restored.profiles_1d[0].electrons.temperature).copy()
    return rho, temperature, actual


def extension_demo():
    # Public upstream mock data; no access to ITER internal databases is implied.
    os.environ["XDG_CACHE_HOME"] = str(Path("cache").resolve())
    from cherab.imas.datasets import bolometer_moc
    from cherab.imas.observer.bolometer import load_bolometers
    from cherab.iter.jorek.utility import (
        py_bezier_basis,
        py_bezier_basis_derivative_wrt_s,
        py_fourier_mode,
    )

    cameras = load_bolometers(bolometer_moc(), parent=World())
    h = 1e-6
    numeric = (py_bezier_basis(0.3 + h, 0.6) - py_bezier_basis(0.3 - h, 0.6)) / (2 * h)
    derivative = py_bezier_basis_derivative_wrt_s(0.3, 0.6)
    return {
        "imas_bolometers": len(cameras) == 3 and all(len(camera) == 5 for camera in cameras),
        "iter_geometry": bool(
            np.allclose(numeric, derivative, atol=1e-8)
            and np.isclose(py_fourier_mode(30.0, 1, 2), 0.5)
        ),
    }


def main():
    impact, chords, exact = chord_demo()
    low, high = plasma_spectrum(1e19), plasma_spectrum(2e19)
    ratio = np.asarray(high.samples) / np.asarray(low.samples)
    rho, temperature, restored = imas_demo()
    checks = {
        "chord_integral": bool(np.allclose(chords, exact, rtol=1e-7, atol=1e-8)),
        "density_scaling": bool(
            np.all(np.isfinite(low.samples))
            and np.all(low.samples > 0)
            and np.allclose(ratio, 4.0, rtol=1e-8)
        ),
        "imas_roundtrip": bool(np.array_equal(temperature, restored)),
    }
    checks.update(extension_demo())
    checks["completed"] = all(checks.values())
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.7))
    axes[0].plot(impact, exact, label="Analytic chord")
    axes[0].plot(impact, chords, ".", label="Raysect")
    axes[0].set(xlabel="Impact parameter / radius", ylabel="Path length (m)")
    axes[0].legend()
    axes[1].plot(low.wavelengths, low.samples, label="n = 1e19 m⁻³")
    axes[1].plot(high.wavelengths, high.samples, label="n = 2e19 m⁻³")
    axes[1].set(xlabel="Wavelength (nm)", ylabel="Radiance (W m⁻² sr⁻¹ nm⁻¹)")
    axes[1].legend()
    axes[2].plot(rho, temperature, label="Original profile")
    axes[2].plot(rho, restored, ".", label="IMAS netCDF round-trip")
    axes[2].set(xlabel="Normalized toroidal-flux radius", ylabel="Electron temperature (eV)")
    axes[2].legend()
    fig.suptitle("ITER ecosystem readiness — analytic and synthetic examples")
    fig.tight_layout()
    fig.savefig("iter_pack_demo.png", dpi=150)
    plt.close(fig)
    np.savetxt(
        "spectra.csv",
        np.c_[low.wavelengths, low.samples, high.samples],
        delimiter=",",
        header="wavelength_nm,radiance_n1,radiance_n2",
    )
    payload = {
        "checks": checks,
        "versions": {
            p: version(p)
            for p in (
                "cherab",
                "raysect",
                "imas-python",
                "imas-validator",
                "cherab-imas",
                "cherab-iter",
            )
        },
        "chord_max_abs_error": float(np.max(np.abs(chords - exact))),
        "density_squared_ratio_min": float(ratio.min()),
        "density_squared_ratio_max": float(ratio.max()),
        "data_dictionary": "3.39.0",
        "scope": "Analytic geometry, continuum scaling and IMAS I/O; not machine validation",
        "artifacts": ["iter_pack_demo.png", "profiles.nc", "spectra.csv"],
    }
    Path("iter_pack_demo.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    if not checks["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
