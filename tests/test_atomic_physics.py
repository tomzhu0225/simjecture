from __future__ import annotations

import json
import runpy
from pathlib import Path

import numpy as np
import pytest
from scipy.constants import e, h, m_e

FAC = runpy.run_path(str(Path(__file__).parents[1] / "skills/atomic-physics/scripts/fac_lte.py"))


def _fixture(tmp_path, *, uta=False):
    (tmp_path / "ion.en").write_text(
        "FAC 1.1.5[0.0.1]\nType = 1\nVerbose = 1\nHe Z = 2.0\nNBlocks = 1\n"
        "E0 = 0, -54.4\nNELE = 1\nNLEV = 2\n"
        "ILEV IBASE ENERGY P VNL 2J\n"
        "0 -1 0.0 0 100 1 1s1\n1 -1 40.8 1 201 3 2p1\n"
    )
    row = "1 3 0 1 40.8 0.5 0.8 1e9 0.2 1.5" if uta else "1 3 0 1 40.8 0.8 1e9 0.2"
    (tmp_path / "ion.tr").write_text(
        "FAC 1.1.5[0.0.1]\nType = 2\nVerbose = 1\nHe Z = 2.0\nNBlocks = 1\n"
        "NELE = 1\nNTRANS = 1\nMULTIP = -1\nGAUGE = 2\nMODE = 1\n" + row + "\n"
    )
    model = {
        "description": "Synthetic unit fixture",
        "atomic_mass_u": 4.0026,
        "ions": [{"levels": "ion.en", "transitions": "ion.tr"}],
    }
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model))
    return path


def test_saha_ratio_and_common_energy_reference_invariance():
    ions = [
        {
            "element": "H",
            "nuclear_charge": 1,
            "charge": 0,
            "ground_eV": -13.6,
            "weight": np.array([2]),
            "energy_eV": np.array([0.0]),
        },
        {
            "element": "H",
            "nuclear_charge": 1,
            "charge": 1,
            "ground_eV": 0.0,
            "weight": np.array([1]),
            "energy_eV": np.array([0.0]),
        },
    ]
    temperature, density = 2.0, 1e20
    fractions, _ = FAC["populations"](ions, temperature, density)
    thermal_wavelength = h / np.sqrt(2 * np.pi * m_e * temperature * e)
    ratio = np.exp(-13.6 / temperature) / (density * 1e6 * thermal_wavelength**3)
    assert fractions[1] / fractions[0] == pytest.approx(ratio, rel=1e-13)
    for ion in ions:
        ion["ground_eV"] += 10000
    shifted, _ = FAC["populations"](ions, temperature, density)
    assert shifted == pytest.approx(fractions, rel=1e-12)
    with pytest.raises(ValueError, match="adjacent"):
        FAC["populations"](ions[::-1], temperature, density)


def test_unresolved_line_area_survives_binning_and_exact_boundary():
    edges = np.arange(0, 4.0, 0.25)
    integrated = FAC["gaussian_bins"](edges, [1.0], [1e-7], [3.0])
    assert integrated.sum() == pytest.approx(3.0)
    assert integrated[3:5] == pytest.approx([1.5, 1.5])
    # A truncated window must not silently renormalize the missing half.
    truncated = FAC["gaussian_bins"]([1.0, 2.0], [1.0], [0.01], [3.0])
    assert truncated.sum() == pytest.approx(1.5)


@pytest.mark.parametrize("uta", [False, True])
def test_absolute_absorption_units_statistical_weight_and_uta_multiplier(tmp_path, uta):
    model = _fixture(tmp_path, uta=uta)
    edges = np.linspace(0, 100, 101)
    summary, spectrum = FAC["synthesize"](model, 10.0, 1e20, 10.0, edges)
    # Independent cgs frequency-integrated oscillator formula, converted Hz -> eV.
    prefactor = 0.02654008 * 4.135667696e-15 / (4.0026 * 1.66053906660e-24)
    partition = 2 + 4 * np.exp(-40.8 / 10)
    area = prefactor * 0.8 / partition * (1 - np.exp(-40.8 / 10))
    if uta:
        area *= 1.5
    integrated = np.dot(spectrum["e1_cm2_g"], np.diff(edges))
    assert integrated == pytest.approx(area, rel=2e-6)
    assert summary["boundary_charge_fraction"] == 1
    assert summary["captured_area_fraction"]["-1"] == pytest.approx(1)
    assert summary["mass_density_g_cm3"] == pytest.approx(1e20 * 4.0026 * 1.66053906660e-24)
    assert not spectrum["m1_cm2_g"].any()
    if uta:
        _, uncorrected = FAC["synthesize"](model, 10.0, 1e20, 10.0, edges, apply_uta_ci=False)
        assert spectrum["e1_cm2_g"] == pytest.approx(uncorrected["e1_cm2_g"] * 1.5)


def test_rejects_truncated_tables_and_inconsistent_ion_identity(tmp_path):
    model = _fixture(tmp_path)
    tr = tmp_path / "ion.tr"
    tr.write_text(tr.read_text().replace("NTRANS = 1", "NTRANS = 2"))
    with pytest.raises(ValueError, match="Truncated"):
        list(FAC["transition_blocks"](tr))
    _fixture(tmp_path)
    tr.write_text(tr.read_text().replace("He Z = 2.0", "W Z = 74.0"))
    with pytest.raises(ValueError, match="EN/TR"):
        FAC["synthesize"](model, 10, 1e20, 10, [0, 100])
    _fixture(tmp_path)
    tr.write_text(tr.read_text().replace("1 3 0 1", "1 3 0 3"))
    with pytest.raises(ValueError, match="weights"):
        FAC["synthesize"](model, 10, 1e20, 10, [0, 100])


@pytest.mark.parametrize("bad_edges", [[1, 0], [0, float("nan")], [-1, 1], [1]])
def test_rejects_invalid_photon_grid(tmp_path, bad_edges):
    with pytest.raises(ValueError, match="edges"):
        FAC["synthesize"](_fixture(tmp_path), 10, 1e20, 10, bad_edges)
