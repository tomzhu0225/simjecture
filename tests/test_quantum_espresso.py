"""Synthetic parser/config tests are not physical calculations."""

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qe_workflow", ROOT / "skills/quantum-espresso/examples/dft_workflow.py"
)
qe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qe)


def approved_run_args(cfg, folder, smoke=False, convergence=False, backend="standalone"):
    """Synthetic user consent for solver-stub regression fixtures only."""
    folder.mkdir(parents=True, exist_ok=True)
    protocol = folder / "PROTOCOL.md"
    protocol.write_text("Synthetic protocol; no real DFT or human research approval claimed")
    plan = qe.build_plan(
        cfg, protocol.read_text(), "scf-only" if smoke else "full", convergence, backend=backend
    )
    plan_path, confirmation = folder / "plan.json", folder / "confirmation.json"
    qe.write_new(plan_path, plan)
    qe.confirm_plan(plan_path, confirmation, plan["plan_sha256"], "synthetic-test-user")
    return {"protocol": protocol, "plan": plan_path, "confirmation": confirmation}


@pytest.fixture
def case():
    cfg = json.loads((ROOT / "demos/qe_dft_reference/case.json").read_text(encoding="utf-8-sig"))
    cfg["convergence_acceptance"] = {}
    return cfg


def test_material_replacement_multiple_species_and_band_count(case, tmp_path):
    cfg = copy.deepcopy(case)
    cfg["species"] = [
        {"label": "A", "mass": 9.0, "pseudo": "a.UPF", "sha256": "a" * 64},
        {"label": "B", "mass": 19.0, "pseudo": "b.UPF", "sha256": "b" * 64},
    ]
    cfg["atoms"] = [
        {"species": "A", "fractional": [0, 0, 0]},
        {"species": "B", "fractional": [0.2, 0.3, 0.4]},
        {"species": "B", "fractional": [0.6, 0.7, 0.8]},
    ]
    cfg["functional"] = "PZ"
    cfg["nbnd"] = 19
    cfg["path"] = [
        {"k": [0, 0, 0], "points": 3, "label": "start"},
        {"k": [0.1, 0.2, 0.3], "points": 1, "label": "end"},
    ]
    path = tmp_path / "case.json"
    path.write_text(json.dumps(cfg))
    parsed = qe.load_case(path)
    inp = qe.pw_input(parsed, "bands", parsed["cell_angstrom"], parsed["atoms"])
    assert "nat=3, ntyp=2" in inp and "nbnd=19" in inp
    assert "A 9.0 a.UPF" in inp and "B 19.0 b.UPF" in inp
    assert "input_dft='PZ'" in inp and "Si" not in inp
    assert "0.1 0.2 0.3 1" in inp


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c.update(spin="noncollinear"),
        lambda c: c.update(occupations="smearing", smearing="mv", degauss_ry=-0.01),
        lambda c: c.update(ecutwfc_ry=-1),
        lambda c: c["species"][0].update(pseudo="../unsafe.UPF"),
        lambda c: c["atoms"][0].update(species="missing"),
        lambda c: c.update(scf_k=[4, 0, 4]),
    ],
)
def test_reject_unsupported_or_malformed_case(case, tmp_path, mutation):
    mutation(case)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(case))
    with pytest.raises(ValueError):
        qe.load_case(path)


def test_hash_failure_preserves_existing_file(case, tmp_path):
    path = tmp_path / case["species"][0]["pseudo"]
    path.write_bytes(b"not a pseudopotential")
    with pytest.raises(ValueError, match="mismatch"):
        qe.fetch(case, tmp_path)
    assert path.read_bytes() == b"not a pseudopotential"


def test_uniform_mesh_uses_tetrahedra_path_keeps_order(case):
    nscf = qe.pw_input(case, "nscf", case["cell_angstrom"], case["atoms"], [7, 8, 9])
    bands = qe.pw_input(case, "bands", case["cell_angstrom"], case["atoms"])
    assert "occupations='tetrahedra'" in nscf and "7 8 9 0 0 0" in nscf
    assert "nosym=.true., noinv=.true." in bands
    assert "occupations='fixed'" in bands


def test_synthetic_projection_units_amplitudes_and_order(tmp_path):
    # Two k points, three bands, one atomic orbital: deliberately not Si dimensions.
    ev = np.array([[-2.0, 0.0, 3.0], [-1.0, 1.0, 4.0]])
    k = np.array([[0.0, 0.0, 0.0], [0.1, 0.2, 0.3]])
    nodes = []
    for ik in range(2):
        ry = ev[ik] / (qe.HARTREE_EV / 2)
        nodes += [
            f"<K-POINT>{' '.join(map(str, k[ik]))}</K-POINT>",
            f"<E>{' '.join(map(str, ry))}</E>",
            '<PROJS><ATOMIC_WFC index="1">0.3 0.4 0.0 0.5 0.6 0.8</ATOMIC_WFC></PROJS>',
        ]
    xml = (
        '<PROJECTIONS><HEADER NUMBER_OF_K-POINTS="2" NUMBER_OF_BANDS="3" '
        'NUMBER_OF_ATOMIC_WFC="1"/><EIGENSTATES>' + "".join(nodes) + "</EIGENSTATES></PROJECTIONS>"
    )
    path = tmp_path / "atomic_proj.xml"
    path.write_text(xml)
    ref = {"energies_ev": ev, "k": k}
    weights = qe.read_projections(path, ref)
    np.testing.assert_allclose(weights[:, 0, :], [[0.25, 0.25, 1.0], [0.25, 0.25, 1.0]])
    with pytest.raises(ValueError, match="energies"):
        qe.read_projections(path, dict(ref, energies_ev=ev[:, ::-1]))
    with pytest.raises(ValueError, match="ordering"):
        qe.read_projections(path, dict(ref, k=k[::-1]))


def test_truncated_band_table_is_rejected(tmp_path):
    path = tmp_path / "bands.dat"
    path.write_text(" &plot nbnd= 3, nks= 2 /\\n0 0 0 1 2\\n")
    with pytest.raises(ValueError):
        qe.read_filband(path)


def test_failed_solver_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("QE_BIN", str(tmp_path))
    executable = tmp_path / "pw.x"
    executable.write_text("#!/bin/sh\\necho deliberate-failure\\nexit 7\\n".replace("\\n", "\n"))
    executable.chmod(0o755)
    receipts = []
    with pytest.raises(RuntimeError, match="failed"):
        qe.run_command("pw.x", "test input", tmp_path / "run", 10, receipts)
    assert receipts[0]["returncode"] == 7
    assert "deliberate-failure" in (tmp_path / "run/pw.out").read_text(encoding="utf-8-sig")


def test_capability_and_cli_registration():
    from conjecture_solver.cli import build_parser
    from conjecture_solver.mvp_skills import MVPCapabilityConfig, MVPSkillCatalog

    cfg = MVPCapabilityConfig.model_validate_json(
        (ROOT / "capabilities/quantum-espresso-7.4.json").read_text(encoding="utf-8-sig")
    )
    assert cfg.manifest.skill == "quantum-espresso"
    catalog = MVPSkillCatalog.discover(ROOT / "skills")
    assert "quantum-espresso" in catalog
    parser = build_parser()
    args = parser.parse_args(["install", "quantum-espresso"])
    assert args.profile == "quantum-espresso"


@pytest.mark.parametrize(
    "code,stdout,expected",
    [
        (
            1,
            (
                "Program PWSCF v.7.4\nError in routine  read_namelists (2):\n"
                "could not find namelist &control"
            ),
            0,
        ),
        (1, "Program PWSCF v.7.4\nunrelated solver failure", 1),
        (127, "libmpi not found", 1),
        (
            1,
            (
                "Program PWSCF v.9.9\nError in routine  read_namelists (2):\n"
                "could not find namelist &control"
            ),
            1,
        ),
    ],
)
def test_startup_probe_accepts_only_expected_eof(tmp_path, monkeypatch, code, stdout, expected):
    import runpy
    import subprocess
    from types import SimpleNamespace

    for name in ("pw.x", "dos.x", "bands.x", "projwfc.x"):
        (tmp_path / name).write_text("synthetic")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QE_BIN", str(tmp_path))
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=code, stdout=stdout, stderr=""),
    )
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(ROOT / "skills/quantum-espresso/examples/runtime_smoke.py"))
    assert error.value.code == expected
    report = json.loads((tmp_path / "qe_runtime_smoke.json").read_text(encoding="utf-8-sig"))
    assert report["scope"] == "deployment availability, not numerical validity"


def test_real_smoke_xml_pressure_units():
    # Recorded QE text reports P=4.57 kbar; XML uses Hartree/Bohr^3.
    data = qe.read_pw_xml(ROOT / "tests/fixtures/qe_scf_smoke.xml")
    assert data["pressure_kbar"] == pytest.approx(4.57, abs=0.006)
    assert data["nelec"] == 8
    assert data["total_energy_ev"] == pytest.approx(-260.9557831325364, abs=1e-8)


def test_launcher_seals_configured_inputs(case, tmp_path, monkeypatch):
    import hashlib
    import sys
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "qe_launcher", ROOT / "scripts/run_qe_in_simjecture.py"
    )
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    pseudo_dir = tmp_path / "pseudo"
    pseudo_dir.mkdir()
    pp = pseudo_dir / "other.UPF"
    pp.write_bytes(b"synthetic alternate material")
    species = [
        {
            "label": "Other",
            "mass": 11.0,
            "pseudo": pp.name,
            "sha256": hashlib.sha256(pp.read_bytes()).hexdigest(),
        }
    ]
    case["profiles"]["replacement"] = {
        "species": species,
        "atoms": [{"species": "Other", "fractional": [0, 0, 0]}],
        "nbnd": 19,
    }
    for key in ("species", "atoms", "nbnd"):
        case.pop(key)
    case["launcher_limits"] = {"memory_mib": 768}
    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps(case))
    protocol = tmp_path / "PROTOCOL.md"
    protocol.write_text("Synthetic test protocol, not physical commissioning")
    approved_cfg = qe.load_case(case_path, "replacement")
    consent = approved_run_args(approved_cfg, tmp_path / "consent", backend="simjecture")
    # The launcher's actual protocol must be the reviewed text.
    protocol.write_bytes(consent["protocol"].read_bytes())
    captured = {}

    class Registry:
        def __contains__(self, name):
            return name == "quantum-espresso-7.4"

        def get(self, name):
            return SimpleNamespace(runtime_root=tmp_path / "synthetic-runtime")

        def descriptors(self):
            return [{"name": "synthetic-registry"}]

    class Sandbox:
        def __init__(self, workspace, config, registry):
            captured.update(workspace=workspace, config=config)

        def run_capability(self, name, argv, **kwargs):
            captured.update(name=name, argv=argv, kwargs=kwargs)
            folder = captured["workspace"] / "result"
            folder.mkdir()
            (folder / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "synthetic": True,
                        "approved_plan_sha256": json.loads(
                            (captured["workspace"] / "plan.json").read_text()
                        )["plan_sha256"],
                    }
                )
            )
            return SimpleNamespace(returncode=0, model_dump_json=lambda **k: "{}")

    monkeypatch.setattr(
        launcher.MVPCapabilityRegistry, "discover", classmethod(lambda cls, *a, **k: Registry())
    )
    monkeypatch.setattr(launcher, "BubblewrapSandbox", Sandbox)
    out = tmp_path / "integration"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "launcher",
            "--project",
            str(ROOT),
            "--case",
            str(case_path),
            "--protocol",
            str(protocol),
            "--plan",
            str(consent["plan"]),
            "--confirmation",
            str(consent["confirmation"]),
            "--pseudo-dir",
            str(pseudo_dir),
            "--profile",
            "replacement",
            "--output",
            str(out),
            "--memory-mib",
            "768",
        ],
    )
    assert launcher.main() == 0
    replay = list((out / "capabilities").glob("*.json"))
    assert [p.name for p in replay] == ["quantum-espresso-7.4.json"]
    assert json.loads(replay[0].read_text())["runtime_root"] == str(tmp_path / "synthetic-runtime")
    inputs = captured["kwargs"]["input_artifacts"]
    assert {x.path for x in inputs} == {
        "case.json",
        "PROTOCOL.md",
        "pseudo/other.UPF",
        "plan.json",
        "confirmation.json",
        "effective_case.json",
    }
    assert captured["kwargs"]["program_path"] == "workflow.py"
    assert captured["config"].max_memory_bytes == 768 * 1024**2
    assert (out / "guided/pseudo/other.UPF").read_bytes() == pp.read_bytes()
    assert captured["kwargs"]["program_sha256"] == qe.digest(out / "workspace/workflow.py")


def test_cell_dofree_is_explicit_and_compatible(case, tmp_path):
    generated = qe.pw_input(case, "vc-relax", case["cell_angstrom"], case["atoms"], [4, 4, 4])
    assert "cell_dofree='all'" in generated
    case["cell_dofree"] = "volume"
    p = tmp_path / "case.json"
    p.write_text(json.dumps(case))
    with pytest.raises(ValueError, match="ibrav=0"):
        qe.load_case(p)


def test_utf8_bom_case(case, tmp_path):
    case["description"] = "Unicode Gamma: \u0393"
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(case, ensure_ascii=False).encode("utf-8"))
    assert qe.load_case(path)["description"] == case["description"]


def test_runtime_lock_rejects_wrong_architecture(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "qe_bootstrap", ROOT / "src/conjecture_solver/runtime_bootstrap.py"
    )
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    monkeypatch.setattr(bootstrap.platform, "system", lambda: "Linux")
    monkeypatch.setattr(bootstrap.platform, "machine", lambda: "aarch64")
    with pytest.raises(ValueError, match="x86_64"):
        bootstrap.prepare_runtime_environment("quantum-espresso", tmp_path / "runtime")
    assert not (tmp_path / "runtime").exists()


def test_reference_path_unicode():
    cfg = qe.load_case(ROOT / "demos/qe_dft_reference/case.json")
    assert cfg["path"][0]["label"] == "\u0393"


def test_recorded_full_qe_indexing_and_tables():
    # Real QE 7.4 record; this test parses historical data, it runs no new DFT.
    record = ROOT / "demos/qe_dft_reference/record/full_reference"
    bands = qe.read_pw_xml(record / "bands/out/sample.save/data-file-schema.xml")
    k, eigenvalues = qe.read_filband(record / "bands/bands.dat")
    np.testing.assert_allclose(k, bands["k"], atol=1e-6, rtol=0)
    np.testing.assert_allclose(eigenvalues, bands["energies_ev"], atol=0.00051, rtol=0)
    weights = qe.read_projections(record / "bands/out/sample.save/atomic_proj.xml", bands)
    assert weights.shape == (105, 8, 12)
    assert bands["nocc"] == 4
    dos, pdos = qe.validate_tables(record)
    assert np.isfinite(dos).all() and np.isfinite(pdos).all()


def test_qe_lock_is_a_discoverable_packaged_skill_resource():
    from conjecture_solver.mvp_skills import MVPSkillCatalog

    catalog = MVPSkillCatalog.discover(ROOT / "skills")
    _, content = catalog.read_bytes("quantum-espresso", "references/linux64.lock", max_bytes=65536)
    rows = content.decode().splitlines()
    assert rows[0] == "@EXPLICIT"
    assert len(rows[1:]) == 90
    assert all(row.startswith("https://conda.anaconda.org/conda-forge/") for row in rows[1:])
    assert all(len(row.rsplit("#", 1)[1]) == 64 for row in rows[1:])


@pytest.mark.parametrize("k_delta, expected_exit", [(0.3, 0), (9.0, 1)])
def test_si_reference_analysis_checks_controls(case, tmp_path, monkeypatch, k_delta, expected_exit):
    import runpy
    import sys

    # Synthetic report fixture; neither branch executes a physical calculation.
    summary = {
        "configuration": case,
        "status": "passed",
        "checks": {"completed": True},
        "occupied_bands": 1,
        "path_gap_ev": 0.5,
        "convergence": [
            {"settings": {"ecutwfc_ry": 60}, "delta_mev_per_atom": -0.3},
            {"settings": {"scf_k": [12, 12, 12]}, "delta_mev_per_atom": k_delta},
        ],
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    (tmp_path / "final_structure.json").write_text(
        json.dumps({"cell_angstrom": case["cell_angstrom"], "atoms": case["atoms"]})
    )
    energy = np.zeros((105, 3))
    energy[:, 1:] = [1, 2]
    np.savez(tmp_path / "verified_projections.npz", energies_ev=energy)
    import xml.etree.ElementTree as ET

    for stage in ("relax", "scf"):
        tree = ET.parse(ROOT / "tests/fixtures/qe_scf_smoke.xml")
        out = tree.getroot().find("output/atomic_structure")
        for i in range(3):
            out.find(f"cell/a{i + 1}").text = " ".join(
                map(str, np.array(case["cell_angstrom"])[i] / qe.BOHR_ANGSTROM)
            )
        for node, atom in zip(out.findall("atomic_positions/atom"), case["atoms"], strict=True):
            node.text = " ".join(
                map(
                    str,
                    np.array(atom["fractional"])
                    @ np.array(case["cell_angstrom"])
                    / qe.BOHR_ANGSTROM,
                )
            )
        if stage == "relax":
            opt = ET.SubElement(tree.getroot().find("output/convergence_info"), "opt_conv")
            ET.SubElement(opt, "convergence_achieved").text = "true"
        path = qe.xml_at(tmp_path / stage)
        path.parent.mkdir(parents=True)
        tree.write(path)
    monkeypatch.setattr(sys, "argv", ["analyze_reference", str(tmp_path)])
    with pytest.raises(SystemExit) as outcome:
        runpy.run_path(str(ROOT / "demos/qe_dft_reference/analyze_reference.py"))
    assert outcome.value.code == expected_exit
    report = json.loads((tmp_path / "si_reference_reassessment.json").read_text())
    assert report["checks"]["k_10x10x10_to_12x12x12_2mev_per_atom"] == (expected_exit == 0)


@pytest.fixture
def metallic_case(case):
    case.update(
        spin="collinear",
        nspin=2,
        occupations="smearing",
        smearing="mv",
        degauss_ry=0.02,
        dos_degauss_ry=0.03,
        starting_magnetization={"A": 0.3, "B": -0.1},
        species=[
            {"label": "A", "mass": 9.0, "pseudo": "a.UPF", "sha256": "a" * 64},
            {"label": "B", "mass": 19.0, "pseudo": "b.UPF", "sha256": "b" * 64},
        ],
        atoms=[
            {"species": "A", "fractional": [0, 0, 0]},
            {"species": "B", "fractional": [0.2, 0.3, 0.4]},
        ],
        nbnd=3,
        path=[
            {"label": "start", "k": [0, 0, 0], "points": 1},
            {"label": "end", "k": [0.1, 0.2, 0.3], "points": 1},
        ],
        acceptance={},
        projection_states=[1, 2],
    )
    return case


def synthetic_spin_xml(path, counts=(3, 3), nspin=2):
    import xml.etree.ElementTree as ET

    tree = ET.parse(ROOT / "tests/fixtures/qe_scf_smoke.xml")
    output = tree.getroot().find("output")
    for atom, label in zip(
        output.findall("atomic_structure/atomic_positions/atom"), ["A", "B"], strict=True
    ):
        atom.set("name", label)
    bs = output.find("band_structure")
    bs.clear()
    ET.SubElement(bs, "lsda").text = "true" if nspin == 2 else "false"
    ET.SubElement(bs, "noncolin").text = "false"
    ET.SubElement(bs, "spinorbit").text = "false"
    ET.SubElement(bs, "nelec").text = "3.25"
    ET.SubElement(bs, "fermi_energy").text = str(1.25 / qe.HARTREE_EV)
    ET.SubElement(bs, "occupations_kind").text = "smearing"
    if nspin == 2:
        ET.SubElement(bs, "nbnd_up").text = str(counts[0])
        ET.SubElement(bs, "nbnd_dw").text = str(counts[1])
    else:
        counts = (sum(counts),)
        ET.SubElement(bs, "nbnd").text = str(counts[0])
    for ik, k in enumerate(([0, 0, 0], [0.1, 0.2, 0.3])):
        node = ET.SubElement(bs, "ks_energies")
        ET.SubElement(node, "k_point", weight="0.5").text = " ".join(map(str, k))
        energy = np.concatenate(
            [np.arange(n) * 0.7 - 1 + spin * 0.4 + ik * 0.1 for spin, n in enumerate(counts)]
        )
        ET.SubElement(node, "eigenvalues").text = " ".join(map(str, energy / qe.HARTREE_EV))
        occ = np.concatenate([np.linspace(0.9 - ik * 0.1, 0.05, n) for n in counts])
        ET.SubElement(node, "occupations").text = " ".join(map(str, occ))
    tree.write(path, encoding="utf-8")
    return qe.read_pw_xml(path)


def synthetic_spin_projections(path, bands):
    import xml.etree.ElementTree as ET

    root = ET.Element("PROJECTIONS")
    ET.SubElement(
        root,
        "HEADER",
        **{
            "NUMBER_OF_K-POINTS": "2",
            "NUMBER_OF_BANDS": "3",
            "NUMBER_OF_SPIN_COMPONENTS": "2",
            "NUMBER_OF_ATOMIC_WFC": "2",
        },
    )
    states = ET.SubElement(root, "EIGENSTATES")
    for spin, channel in enumerate(bands["channels"], 1):
        for ik, k in enumerate(bands["k"]):
            ET.SubElement(states, "K-POINT").text = " ".join(map(str, k))
            ET.SubElement(states, "E").text = " ".join(
                map(str, channel["energies_ev"][ik] * 2 / qe.HARTREE_EV)
            )
            projections = ET.SubElement(states, "PROJS")
            for iw in (1, 2):
                ET.SubElement(
                    projections, "ATOMIC_WFC", index=str(iw), spin=str(spin)
                ).text = " ".join([f"{0.1 * spin} {0.2 * iw}"] * 3)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8")
    return root


def test_metallic_collinear_configuration_propagates(metallic_case, tmp_path):
    path = tmp_path / "metal.json"
    path.write_text(json.dumps(metallic_case))
    cfg = qe.load_case(path)
    for stage in ("vc-relax", "scf", "nscf", "bands"):
        text = qe.pw_input(cfg, stage, cfg["cell_angstrom"], cfg["atoms"], [3, 4, 5])
        assert "nspin=2" in text and "occupations='smearing'" in text
        assert "smearing='mv', degauss=0.02" in text and "nbnd=3" in text
        assert "starting_magnetization(1)=0.3" in text and "starting_magnetization(2)=-0.1" in text
        assert "Si" not in text
    dos, projection = qe.postprocess_options(cfg)
    assert "bz_sum='smearing'" in dos
    assert "degauss=0.03, ngauss=-1" in dos and "degauss=0.03, ngauss=-1" in projection
    cfg.update(dos_occupations="tetrahedra_opt")
    assert "occupations='tetrahedra_opt'" in qe.pw_input(
        cfg, "nscf", cfg["cell_angstrom"], cfg["atoms"], [3] * 3
    )
    assert "degauss=" not in qe.postprocess_options(cfg)[0]


@pytest.mark.parametrize("nspin,counts", [(1, (3, 3)), (2, (3, 3)), (2, (4, 2))])
def test_fractional_electrons_and_xml_spin_blocks(tmp_path, nspin, counts):
    data = synthetic_spin_xml(tmp_path / "pw.xml", counts, nspin)
    assert data["nelec"] == 3.25 and data["nspin"] == nspin
    assert data["nocc"] is None
    assert [x["energies_ev"].shape[1] for x in data["channels"]] == (
        list(counts) if nspin == 2 else [sum(counts)]
    )
    assert data["fermi_energy_ev"] == pytest.approx(1.25)
    assert all(x["nocc"] is None for x in data["channels"])


def test_metal_uses_final_scf_fermi_and_does_not_require_gap(metallic_case, tmp_path):
    bands = synthetic_spin_xml(tmp_path / "pw.xml")
    scf = dict(bands, fermi_energy_ev=0.75)
    edges, reference = qe.spectral_reference(bands, scf, metallic_case)
    assert edges == {"path_gap_ev": None, "path_vbm_ev": None, "path_cbm_ev": None}
    assert reference == {"value_ev": 0.75, "origin": "final_scf_fermi"}
    metallic_case["energy_zero_ev"] = -2.0
    assert qe.spectral_reference(bands, scf, metallic_case)[1]["value_ev"] == -2
    metallic_case.pop("energy_zero_ev")
    with pytest.raises(ValueError, match="reference unavailable"):
        qe.spectral_reference(bands, dict(scf, fermi_energy_ev=None), metallic_case)


def test_lsda_projection_spin_order_and_per_spin_band_files(tmp_path):
    import xml.etree.ElementTree as ET

    bands = synthetic_spin_xml(tmp_path / "pw.xml")
    path = tmp_path / "atomic_proj.xml"
    tree = synthetic_spin_projections(path, bands)
    weights = qe.read_projections(path, bands)
    assert weights.shape == (2, 2, 6)
    np.testing.assert_allclose(weights[:, 0, :3], 0.05)
    np.testing.assert_allclose(weights[:, 0, 3:], 0.08)
    for channel in bands["channels"]:
        file = tmp_path / f"bands_{channel['label']}.dat"
        lines = [" &plot nbnd= 3, nks= 2 /"]
        for k, energy in zip(bands["k"], channel["energies_ev"], strict=True):
            lines.extend([" ".join(map(str, k)), " ".join(f"{x:.3f}" for x in energy)])
        file.write_text("\n".join(lines) + "\n")
    assert qe.verify_band_files(tmp_path, bands) < 0.00051
    up = (tmp_path / "bands_up.dat").read_bytes()
    (tmp_path / "bands_down.dat").write_bytes(up)
    with pytest.raises(ValueError, match="energy indexing"):
        qe.verify_band_files(tmp_path, bands)
    tree.findall("EIGENSTATES/PROJS")[2].find("ATOMIC_WFC").set("spin", "1")
    ET.ElementTree(tree).write(path, encoding="utf-8")
    with pytest.raises(ValueError, match="spin index"):
        qe.read_projections(path, bands)


def test_spin_dos_columns_and_plotting(metallic_case, tmp_path):
    bands = synthetic_spin_xml(tmp_path / "pw.xml")
    projection = tmp_path / "atomic_proj.xml"
    synthetic_spin_projections(projection, bands)
    weights = qe.read_projections(projection, bands)
    directory = tmp_path / "dos"
    directory.mkdir()
    np.savetxt(directory / "dos.dat", [[-1, 0.2, 0.1, 0], [1, 0.3, 0.4, 2]])
    # A signed higher-order-smearing lobe is finite data, not a universal failure.
    np.savetxt(directory / "pdos.pdos_tot", [[-1, 0.2, 0.1, -0.01, 0.03], [1, 0.3, 0.4, 0.2, 0.3]])
    np.savetxt(
        directory / "pdos.pdos_atm#1(A)_wfc#1(s)",
        [[-1, 0.2, 0.1, 0.2, 0.1], [1, 0.3, 0.4, 0.3, 0.4]],
    )
    (directory / "projwfc.out").write_text("state # 1: atom 1 (A), wfc 1 (l=0 m=1)\n")
    dos, pdos = qe.validate_tables(tmp_path, 2)
    edges, reference = qe.spectral_reference(bands, bands, metallic_case)
    assert edges["path_gap_ev"] is None
    qe.plot_results(tmp_path, bands, weights, dos, pdos, metallic_case, reference)
    saved = np.load(tmp_path / "verified_projections.npz")
    assert saved["spin_labels"].tolist() == ["up", "down"]
    assert saved["band_slices"].tolist() == [[0, 3], [3, 6]]
    assert (tmp_path / "bands_dos_pdos.png").stat().st_size > 1000
    header = (tmp_path / "bands.csv").read_text().splitlines()[0]
    assert "up_band_1" in header and "down_band_1" in header
    with pytest.raises(ValueError, match="spin layout"):
        qe.validate_tables(tmp_path, 1)


def test_original_si_inputs_and_raw_reanalysis_are_compatible(case):
    import runpy

    record = ROOT / "demos/qe_dft_reference/record/full_reference"
    original = runpy.run_path(str(record / "executed_workflow.py.txt"))
    geometry = json.loads((record / "final_structure.json").read_text())
    for stage in ("vc-relax", "scf", "nscf", "bands"):
        cell = case["cell_angstrom"] if stage == "vc-relax" else geometry["cell_angstrom"]
        atoms = case["atoms"] if stage == "vc-relax" else geometry["atoms"]
        mesh = case["dos_k"] if stage == "nscf" else case["scf_k"]
        assert qe.pw_input(case, stage, cell, atoms, mesh) == original["pw_input"](
            case, stage, cell, atoms, mesh
        )
    path = record / "bands/out/sample.save/data-file-schema.xml"
    current, old = qe.read_pw_xml(path), original["read_pw_xml"](path)
    np.testing.assert_array_equal(current["energies_ev"], old["energies_ev"])
    assert current["nocc"] == old["nocc"] == 4
    projection = record / "bands/out/sample.save/atomic_proj.xml"
    np.testing.assert_array_equal(
        qe.read_projections(projection, current), original["read_projections"](projection, old)
    )
    scf = qe.read_pw_xml(record / "scf/out/sample.save/data-file-schema.xml")
    edges, zero = qe.spectral_reference(current, scf, case)
    assert edges["path_gap_ev"] == pytest.approx(0.6139796488905915, abs=1e-10)
    assert zero["origin"] == "vbm"


@pytest.mark.parametrize("pdos_requested", [True, False])
def test_synthetic_metal_workflow_runs_both_spin_branches(
    metallic_case, tmp_path, monkeypatch, pdos_requested
):
    import hashlib
    import re
    import shutil

    metallic_case["pdos"] = pdos_requested
    # Coupled orchestration fixture: every solver is a stub, never real physics evidence.
    template = tmp_path / "synthetic_pw.xml"
    bands = synthetic_spin_xml(template)
    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    for species in metallic_case["species"]:
        payload = ("synthetic " + species["label"]).encode()
        (pseudo / species["pseudo"]).write_bytes(payload)
        species["sha256"] = hashlib.sha256(payload).hexdigest()
    commands = []

    def fake_command(binary, text, directory, timeout, receipts, label=None):
        directory.mkdir(parents=True, exist_ok=True)
        stem = label or binary.replace(".x", "")
        (directory / (stem + ".in")).write_text(text)
        (directory / (stem + ".out")).write_text(
            "Synthetic solver stub; End of BFGS Geometry Optimization; JOB DONE.\n"
        )
        commands.append((binary, directory.name, stem))
        receipts.append({"synthetic": True, "binary": binary, "stem": stem})
        if binary == "pw.x":
            assert "nspin=2" in text and "occupations='smearing'" in text
            saved = directory / "out/sample.save/data-file-schema.xml"
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template, saved)
            if directory.name == "relax":
                import xml.etree.ElementTree as ET

                tree = ET.parse(saved)
                conv = tree.getroot().find("output/convergence_info")
                opt = ET.SubElement(conv, "opt_conv")
                ET.SubElement(opt, "convergence_achieved").text = "true"
                tree.write(saved)
        elif binary == "bands.x":
            spin = int(re.search(r"spin_component=(\d)", text).group(1))
            channel = bands["channels"][spin - 1]
            lines = [" &plot nbnd= 3, nks= 2 /"]
            for k, energy in zip(bands["k"], channel["energies_ev"], strict=True):
                lines.extend([" ".join(map(str, k)), " ".join(f"{x:.3f}" for x in energy)])
            (directory / f"bands_{channel['label']}.dat").write_text("\n".join(lines) + "\n")
        elif binary == "dos.x":
            assert "bz_sum='smearing'" in text and "degauss=0.03" in text
            np.savetxt(directory / "dos.dat", [[-1, 0.2, 0.1, 0], [1, 0.3, 0.4, 2]])
        elif directory.name == "dos":
            (directory / "projwfc.out").write_text("state # 1: atom 1 (A), wfc 1 (l=0 m=1)\n")
            assert "degauss=0.03" in text
            np.savetxt(
                directory / "pdos.pdos_tot", [[-1, 0.2, 0.1, 0.1, 0.05], [1, 0.3, 0.4, 0.2, 0.3]]
            )
            np.savetxt(
                directory / "pdos.pdos_atm#1(A)_wfc#1(s)",
                [[-1, 0.2, 0.1, 0.2, 0.1], [1, 0.3, 0.4, 0.3, 0.4]],
            )
        else:
            synthetic_spin_projections(directory / "out/sample.save/atomic_proj.xml", bands)

    monkeypatch.setattr(qe, "run_command", fake_command)
    result = tmp_path / "result"
    consent = approved_run_args(metallic_case, tmp_path / "consent")
    summary = qe.run(metallic_case, pseudo, result, **consent)
    assert summary["status"] == "passed" and summary["spin_components"] == 2
    assert summary["pdos_status"] == ("validated" if pdos_requested else "not_requested")
    assert any(x[:2] == ("projwfc.x", "dos") for x in commands) == pdos_requested
    assert summary["path_gap_ev"] is None and summary["occupied_bands"] is None
    assert summary["energy_reference"]["origin"] == "final_scf_fermi"
    assert (result / "bands/bands_up.in").is_file() and (result / "bands/bands_down.in").is_file()
    assert [x[2] for x in commands if x[0] == "bands.x"] == ["bands_up", "bands_down"]
    assert summary["checks"]["branches_independent"] and summary["checks"]["checkpoint_preserved"]


def test_integrated_moment_units_and_signed_total(tmp_path):
    import xml.etree.ElementTree as ET

    path = tmp_path / "pw.xml"
    synthetic_spin_xml(path)
    tree = ET.parse(path)
    mag = tree.getroot().find("output/magnetization")
    mag.find("absolute").text = "2.7"
    ET.SubElement(mag, "total").text = "-2.4"
    tree.write(path, encoding="utf-8")
    data = qe.read_pw_xml(path)
    assert data["magnetization"]["total_muB_per_cell"] == -2.4
    assert data["magnetization"]["absolute_muB_per_cell"] == 2.7
    assert data["magnetization"]["mean_total_muB_per_atom"] == -1.2
    assert data["magnetization"]["mean_absolute_muB_per_atom"] == 1.35


def test_recorded_fe_collinear_metal_format():
    # Actual Fe record: this regression parses data, it does not launch another DFT run.
    record = ROOT / "demos/qe_fe_reference/record/full_reference"
    cfg = json.loads((record / "effective_case.json").read_text())
    bands = qe.read_pw_xml(record / "bands/out/sample.save/data-file-schema.xml")
    scf = qe.read_pw_xml(record / "scf/out/sample.save/data-file-schema.xml")
    assert bands["nspin"] == 2 and bands["energies_ev"].shape == (49, 32)
    assert [x["energies_ev"].shape[1] for x in bands["channels"]] == [16, 16]
    assert qe.verify_band_files(record / "bands", bands) <= 0.00051
    projections = qe.read_projections(record / "bands/out/sample.save/atomic_proj.xml", bands)
    assert projections.shape == (49, 13, 32)
    dos, pdos = qe.validate_tables(record, 2)
    assert dos.shape[1] == 4 and pdos.shape[1] == 5
    edges, reference = qe.spectral_reference(bands, scf, cfg)
    assert edges["path_gap_ev"] is None and reference["origin"] == "final_scf_fermi"
    assert scf["nelec"] == 16 and len(scf["atoms"]) == 1
    assert scf["magnetization"]["total_muB_per_cell"] == pytest.approx(2.189675593060556)
    assert (
        scf["magnetization"]["absolute_muB_per_cell"] > scf["magnetization"]["total_muB_per_cell"]
    )
    # Independent raw text prints P=0.18 kbar; XML stress uses Hartree/Bohr^3.
    assert scf["pressure_kbar"] == pytest.approx(0.18, abs=0.0051)


@pytest.mark.parametrize("status", ["2", "3", "255", None])
def test_pw_rejects_nonzero_or_missing_exit(tmp_path, status):
    import xml.etree.ElementTree as ET

    tree = ET.parse(ROOT / "tests/fixtures/qe_scf_smoke.xml")
    node = tree.getroot().find("exit_status")
    if status is None:
        tree.getroot().remove(node)
    else:
        node.text = status
    path = tmp_path / "pw.xml"
    tree.write(path)
    with pytest.raises(ValueError, match="exit_status"):
        qe.read_pw_xml(path)


@pytest.mark.parametrize("calculation,flag", [("scf", "scf_conv"), ("vc-relax", "opt_conv")])
@pytest.mark.parametrize("value", ["false", None])
def test_pw_requires_stage_convergence(tmp_path, calculation, flag, value):
    import xml.etree.ElementTree as ET

    tree = ET.parse(ROOT / "tests/fixtures/qe_scf_smoke.xml")
    conv = tree.getroot().find("output/convergence_info")
    if flag == "opt_conv":
        conv.append(ET.Element(flag))
        ET.SubElement(conv.find(flag), "convergence_achieved").text = "true"
    node = conv.find(f"{flag}/convergence_achieved")
    if value is None:
        conv.find(flag).remove(node)
    else:
        node.text = value
    path = tmp_path / "pw.xml"
    tree.write(path)
    with pytest.raises(ValueError, match=flag):
        qe.read_pw_xml(path, calculation)


@pytest.mark.parametrize("calculation", ["nscf", "bands"])
def test_non_scf_does_not_require_scf_flag(tmp_path, calculation):
    import xml.etree.ElementTree as ET

    tree = ET.parse(ROOT / "tests/fixtures/qe_scf_smoke.xml")
    tree.getroot().find("output/convergence_info/scf_conv/convergence_achieved").text = "false"
    path = tmp_path / "pw.xml"
    tree.write(path)
    assert qe.read_pw_xml(path, calculation)["energies_ev"].size


@pytest.mark.parametrize(
    "material,filename", [("qe_dft_reference", "bands.dat"), ("qe_fe_reference", "bands_down.dat")]
)
@pytest.mark.parametrize("bad", ["NaN", "Inf", "-Inf", "truncated"])
def test_nonfinite_and_truncated_band_files(tmp_path, material, filename, bad):
    import shutil

    record = ROOT / "demos" / material / "record/full_reference"
    for p in (record / "bands").glob("*.dat"):
        shutil.copyfile(p, tmp_path / p.name)
    p = tmp_path / filename
    lines = p.read_text().splitlines()
    if bad == "truncated":
        lines.pop()
    else:
        fields = lines[2].split()
        fields[0] = bad
        lines[2] = " ".join(fields)
    p.write_text("\n".join(lines) + "\n")
    bands = qe.read_pw_xml(record / "bands/out/sample.save/data-file-schema.xml")
    with pytest.raises(ValueError, match="Nonfinite|Truncated"):
        qe.verify_band_files(tmp_path, bands)


@pytest.mark.parametrize("mutation", ["all", "one", "unknown", "grid"])
def test_atomic_pdos_inventory_and_grid(tmp_path, mutation):
    import shutil

    record = ROOT / "demos/qe_dft_reference/record/full_reference/dos"
    shutil.copytree(record, tmp_path / "dos")
    files = sorted((tmp_path / "dos").glob("pdos.pdos_atm*"))
    if mutation in {"one", "all"}:
        for p in files if mutation == "all" else files[:1]:
            p.unlink()
    elif mutation == "unknown":
        shutil.copyfile(files[0], files[0].with_name("pdos.pdos_atm#99(X)_wfc#1(s)"))
    else:
        table = np.loadtxt(files[0])
        table[:, 0] += 0.05
        np.savetxt(files[0], table)
    with pytest.raises(ValueError, match="inventory|grid"):
        qe.validate_tables(tmp_path, 1)


def test_pdos_not_requested_needs_no_pdos_outputs(tmp_path):
    (tmp_path / "dos").mkdir()
    np.savetxt(tmp_path / "dos/dos.dat", [[-1, 0.2, 0], [1, 0.3, 1]])
    dos, pdos = qe.validate_tables(tmp_path, 1, pdos_requested=False)
    assert dos.shape == (2, 3) and pdos is None


@pytest.mark.parametrize("smoke", [True, False])
def test_failed_pw_stops_before_downstream_and_writes_failed_summary(
    case, tmp_path, monkeypatch, smoke
):
    import hashlib
    import types
    import xml.etree.ElementTree as ET

    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    for species in case["species"]:
        (pseudo / species["pseudo"]).write_bytes(b"synthetic")
        species["sha256"] = hashlib.sha256(b"synthetic").hexdigest()
    commands = []

    def stopped(command, *, cwd, stdout, **kwargs):
        commands.append(command)
        path = qe.xml_at(cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.parse(ROOT / "tests/fixtures/qe_scf_smoke.xml")
        tree.getroot().find("exit_status").text = "255" if smoke else "3"
        tree.write(path)
        stdout.write("End of BFGS Geometry Optimization\nJOB DONE.\n")
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(qe.subprocess, "run", stopped)
    out = tmp_path / "result"
    if smoke:
        case["acceptance"] = {}
    consent = approved_run_args(case, tmp_path / "consent", smoke=smoke)
    with pytest.raises(ValueError, match="exit_status"):
        qe.run(case, pseudo, out, smoke=smoke, **consent)
    assert len(commands) == 1
    assert json.loads((out / "summary.json").read_text())["status"] == "failed"
    assert not (out / "dos").exists()


def test_filband_nonfinite_k_coordinates(tmp_path):
    path = tmp_path / "bands.dat"
    path.write_text(" &plot nbnd= 1, nks= 1 /\nNaN 0 0\n1.0\n")
    with pytest.raises(ValueError, match="Nonfinite"):
        qe.read_filband(path)


@pytest.mark.parametrize("material,nspin", [("qe_dft_reference", 1), ("qe_fe_reference", 2)])
@pytest.mark.parametrize("channel", ["p", "d"])
@pytest.mark.parametrize("extra", [-1, 1])
def test_complete_m_resolved_pdos_columns(tmp_path, material, nspin, channel, extra):
    import shutil

    shutil.copytree(ROOT / "demos" / material / "record/full_reference/dos", tmp_path / "dos")
    file = next((tmp_path / "dos").glob("*(p)"))
    if channel == "d":
        # Synthetic angular replacement, not a second material calculation.
        log = tmp_path / "dos/projwfc.out"
        text = log.read_text().replace("l=1", "l=2")
        log.write_text(text)
        for old in list((tmp_path / "dos").glob("*(p)")):
            table = np.loadtxt(old)
            table = np.column_stack([table, np.zeros((len(table), 2 * nspin))])
            new = old.with_name(old.name[:-2] + "d)")
            np.savetxt(new, table)
            old.unlink()
        file = next((tmp_path / "dos").glob("*(d)"))
    qe.validate_tables(tmp_path, nspin)
    table = np.loadtxt(file)
    changed = (
        table[:, :-nspin] if extra < 0 else np.column_stack([table, np.zeros((len(table), nspin))])
    )
    np.savetxt(file, changed)
    with pytest.raises(ValueError, match="PDOS spin columns"):
        qe.validate_tables(tmp_path, nspin)
    assert qe.validate_tables(tmp_path, nspin, pdos_requested=False)[1] is None


@pytest.mark.parametrize("material", ["qe_dft_reference", "qe_fe_reference"])
@pytest.mark.parametrize("state", ["missing", "failed", "qualified"])
def test_reference_analyzer_reassesses_completion(tmp_path, monkeypatch, material, state):
    import runpy
    import shutil
    import sys
    import xml.etree.ElementTree as ET

    record = ROOT / "demos" / material / "record/full_reference"
    shutil.copytree(record, tmp_path / "result")
    root = tmp_path / "result"
    if material == "qe_dft_reference":
        bands = qe.read_pw_xml(qe.xml_at(root / "bands"))
        np.savez(root / "verified_projections.npz", energies_ev=bands["energies_ev"])
    if state != "missing":
        tree = ET.parse(qe.xml_at(root / "scf"))
        node = ET.SubElement(tree.getroot().find("output/convergence_info"), "opt_conv")
        ET.SubElement(node, "convergence_achieved").text = (
            "true" if state == "qualified" else "false"
        )
        path = qe.xml_at(root / "relax")
        path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(path)
    historical = root / (
        "si_reference_comparison.json"
        if material == "qe_dft_reference"
        else "fe_reference_comparison.json"
    )
    before = historical.read_bytes()
    monkeypatch.setattr(sys, "argv", ["analyze_reference", str(root)])
    with pytest.raises(SystemExit) as outcome:
        runpy.run_path(str(ROOT / "demos" / material / "analyze_reference.py"))
    assert outcome.value.code == (0 if state == "qualified" else 1)
    prefix = "si" if material == "qe_dft_reference" else "fe"
    result = json.loads((root / f"{prefix}_reference_reassessment.json").read_text())
    assert result["qualification"]["status"] == ("unqualified" if state == "missing" else state)
    assert result["checks"]["workflow_passed"] == (state == "qualified")
    assert historical.read_bytes() == before
    with pytest.raises(SystemExit) as repeat:
        runpy.run_path(str(ROOT / "demos" / material / "analyze_reference.py"))
    assert repeat.value.code == 2
