"""Ported V2 independent fixtures: synthetic consent added; original review file unchanged."""

import hashlib
import importlib.util
import json
import shutil
import types
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

R = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "review_qe", R / "skills/quantum-espresso/examples/dft_workflow.py"
)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


def record(material):
    return R / "demos" / material / "record/full_reference"


@pytest.mark.parametrize(
    "material,spin", [("qe_dft_reference", 0), ("qe_fe_reference", 0), ("qe_fe_reference", 1)]
)
@pytest.mark.parametrize(
    "side,bad",
    [("actual", np.nan), ("actual", np.inf), ("reference", np.nan), ("reference", np.inf)],
)
def test_band_finite_both_sides_every_spin(tmp_path, material, spin, side, bad):
    rec = record(material)
    shutil.copytree(rec / "bands", tmp_path / "bands")
    data = q.read_pw_xml(rec / "bands/out/sample.save/data-file-schema.xml")
    if side == "actual":
        name = (
            "bands.dat"
            if material == "qe_dft_reference"
            else ["bands_up.dat", "bands_down.dat"][spin]
        )
        p = tmp_path / "bands" / name
        lines = p.read_text().splitlines()
        v = lines[2].split()
        v[0] = str(bad)
        lines[2] = " ".join(v)
        p.write_text("\n".join(lines) + "\n")
    else:
        data["channels"][spin]["energies_ev"][0, 0] = bad
    with pytest.raises(ValueError):
        q.verify_band_files(tmp_path / "bands", data)


@pytest.mark.parametrize("stage", ["scf", "relax", "vc-relax", "nscf", "bands"])
def test_real_run_command_normal_stage(tmp_path, monkeypatch, stage):
    def fake(command, *, cwd, stdout, **kw):
        p = q.xml_at(cwd)
        p.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.parse(R / "tests/fixtures/qe_scf_smoke.xml")
        root = tree.getroot()
        root.find("input/control_variables/calculation").text = stage
        conv = root.find("output/convergence_info")
        if stage in ("relax", "vc-relax"):
            opt = ET.SubElement(conv, "opt_conv")
            ET.SubElement(opt, "convergence_achieved").text = "true"
        if stage in ("nscf", "bands"):
            conv.find("scf_conv/convergence_achieved").text = "false"
        tree.write(p)
        stdout.write("JOB DONE.\n")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(q.subprocess, "run", fake)
    q.run_command("pw.x", f"&CONTROL calculation='{stage}' /\n", tmp_path / "run", 2, [])


@pytest.mark.parametrize(
    "smoke,status,flag",
    [
        (False, "3", False),
        (False, "0", False),
        (True, "255", False),
        (True, "0", False),
        (True, "2", False),
    ],
)
def test_original_failure_repro_is_blocked(tmp_path, monkeypatch, smoke, status, flag):
    cfg = q.load_case(record("qe_dft_reference") / "effective_case.json")
    cfg["convergence_acceptance"] = {}
    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    for s in cfg["species"]:
        (pseudo / s["pseudo"]).write_bytes(b"fixture")
        s["sha256"] = hashlib.sha256(b"fixture").hexdigest()
    if smoke:
        cfg["acceptance"] = {}
    protocol = tmp_path / "PROTOCOL.md"
    protocol.write_text("Synthetic regression consent, no physical calculation")
    plan = q.build_plan(
        cfg, protocol.read_text(), "scf-only" if smoke else "full", False, backend="standalone"
    )
    plan_path = tmp_path / "plan.json"
    receipt = tmp_path / "confirmation.json"
    q.write_new(plan_path, plan)
    q.confirm_plan(plan_path, receipt, plan["plan_sha256"], "synthetic-review-test")
    calls = []

    def fake(command, *, cwd, stdout, **kw):
        calls.append(str(cwd))
        p = q.xml_at(cwd)
        p.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.parse(R / "tests/fixtures/qe_scf_smoke.xml")
        root = tree.getroot()
        root.find("exit_status").text = status
        conv = root.find("output/convergence_info")
        if smoke:
            conv.find("scf_conv/convergence_achieved").text = "false"
        else:
            opt = ET.SubElement(conv, "opt_conv")
            ET.SubElement(opt, "convergence_achieved").text = "false"
        tree.write(p)
        stdout.write("End of BFGS Geometry Optimization\nJOB DONE.\n")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(q.subprocess, "run", fake)
    with pytest.raises(ValueError):
        q.run(
            cfg,
            pseudo,
            tmp_path / "result",
            smoke=smoke,
            protocol=protocol,
            plan=plan_path,
            confirmation=receipt,
        )
    assert len(calls) == 1
    assert json.loads((tmp_path / "result/summary.json").read_text())["status"] == "failed"
    assert not (tmp_path / "result/scf").exists() if not smoke else True


@pytest.mark.parametrize("material,nspin", [("qe_dft_reference", 1), ("qe_fe_reference", 2)])
def test_required_and_optional_pdos(tmp_path, material, nspin):
    shutil.copytree(record(material) / "dos", tmp_path / "dos")
    q.validate_tables(tmp_path, nspin)
    for p in (tmp_path / "dos").glob("pdos.pdos_atm*"):
        p.unlink()
    with pytest.raises(ValueError, match="inventory"):
        q.validate_tables(tmp_path, nspin)
    assert q.validate_tables(tmp_path, nspin, pdos_requested=False)[1] is None


@pytest.mark.parametrize("material,nspin", [("qe_dft_reference", 1), ("qe_fe_reference", 2)])
def test_missing_m_resolved_pdos_columns_must_fail(tmp_path, material, nspin):
    shutil.copytree(record(material) / "dos", tmp_path / "dos")
    p = next((tmp_path / "dos").glob("*wfc#2(p)"))
    table = np.loadtxt(p)
    np.savetxt(p, table[:, :-nspin])
    with pytest.raises(ValueError):
        q.validate_tables(tmp_path, nspin)
