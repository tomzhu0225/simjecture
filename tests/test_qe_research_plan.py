"""Research-consent regression fixtures; no QE, network, or paid API execution."""

import hashlib
import importlib.util
import json
import runpy
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qe_plan", ROOT / "skills/quantum-espresso/examples/dft_workflow.py"
)
qe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qe)


@pytest.fixture
def case():
    cfg = json.loads((ROOT / "demos/qe_dft_reference/case.json").read_text())
    cfg["acceptance"] = {}
    cfg["convergence_acceptance"] = {}
    return cfg


def consent(cfg, folder, mode="full", convergence=False, backend="standalone"):
    folder.mkdir(parents=True, exist_ok=True)
    protocol = folder / "PROTOCOL.md"
    protocol.write_bytes(b"Synthetic research plan: no physical calculation is authorized\n")
    plan = qe.build_plan(cfg, protocol.read_bytes().decode(), mode, convergence, backend=backend)
    path, receipt = folder / "plan.json", folder / "confirmation.json"
    qe.write_new(path, plan)
    qe.confirm_plan(path, receipt, plan["plan_sha256"], "synthetic-user")
    return {"protocol": protocol, "plan": path, "confirmation": receipt}


def assert_no_calculation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unconfirmed or invalid plan reached scientific execution")

    monkeypatch.setattr(qe, "run_command", forbidden)


def test_unconfirmed_driver_stops_before_output_or_solver(case, tmp_path, monkeypatch):
    assert_no_calculation(monkeypatch)
    with pytest.raises(ValueError, match="confirmation"):
        qe.run(case, tmp_path / "absent", tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_profile_fills_missing_never_overrides_explicit(case, tmp_path):
    case["profiles"]["test"] = {"ecutwfc_ry": 900, "mixing_beta": 0.2}
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case))
    cfg = qe.load_case(path, "test")
    assert cfg["ecutwfc_ry"] == case["ecutwfc_ry"] and cfg["mixing_beta"] == 0.2
    plan = qe.build_plan(cfg, "Explicit research protocol")
    assert plan["parameter_sources"]["ecutwfc_ry"] == "explicit case"
    assert "profile test" in plan["parameter_sources"]["mixing_beta"]


def test_plan_discloses_resolved_defaults_and_empty_acceptance(case):
    case.pop("launcher_limits", None)
    for key in ("ecutwfc_ry", "conv_thr_ry", "acceptance"):
        case.pop(key)
    plan = qe.build_plan(case, "Assisted protocol ready for user review")
    assert plan["effective_case"]["ecutwfc_ry"] == 50
    assert plan["effective_case"]["conv_thr_ry"] == 1e-8
    assert plan["parameter_sources"]["ecutwfc_ry"] == "builtin CASE_DEFAULTS"
    assert plan["parameter_sources"]["launcher_limits.memory_mib"] == "builtin LAUNCHER_DEFAULTS"
    assert plan["acceptance_semantics"]["physical_targets"] == "not_requested"
    assert plan["acceptance_semantics"]["numerical_accuracy"] == "not_assessed"
    assert "QE automatic" in plan["qe_defaults"]["scf_nbnd"]


@pytest.mark.parametrize(
    "change", ["parameter", "steps", "precision", "pdos", "protocol", "plan", "receipt"]
)
def test_changes_invalidate_consent_before_calculation(case, tmp_path, monkeypatch, change):
    files = consent(case, tmp_path / "consent")
    if change == "parameter":
        case["ecutwfc_ry"] += 1
    elif change == "steps":
        case["steps"] = ["scf"]
    elif change == "precision":
        case["acceptance"] = {"max_force_ry_bohr": [0, 0.001]}
    elif change == "pdos":
        case["pdos"] = False
    elif change == "protocol":
        files["protocol"].write_text("Changed protocol")
    elif change == "plan":
        data = json.loads(files["plan"].read_text())
        data["mode"] = "scf-only"
        files["plan"].write_text(json.dumps(data))
    else:
        files["confirmation"].write_text(
            '{"schema_version":"qe-confirmation-1","plan_sha256":"bad"}'
        )
    assert_no_calculation(monkeypatch)
    with pytest.raises(ValueError):
        qe.run(case, tmp_path, tmp_path / "run", **files)
    assert not (tmp_path / "run").exists()


def test_confirmation_requires_displayed_hash_and_refuses_overwrite(case, tmp_path):
    files = consent(case, tmp_path / "consent")
    with pytest.raises(ValueError, match="hash"):
        qe.confirm_plan(files["plan"], tmp_path / "bad.json", "wrong", "synthetic-user")
    plan = qe.read_plan(files["plan"])
    with pytest.raises(FileExistsError):
        qe.confirm_plan(files["plan"], files["confirmation"], plan["plan_sha256"], "synthetic-user")


@pytest.mark.parametrize("mode,pdos", [("scf-only", False), ("full", False), ("full", True)])
def test_supported_step_selections(case, mode, pdos):
    case["pdos"] = pdos
    plan = qe.build_plan(case, "Protocol", mode)
    if mode == "scf-only":
        assert plan["steps"] == ["scf"]
    else:
        assert ("pdos" in plan["steps"]) == pdos


@pytest.mark.parametrize("bad", ["steps", "gap", "controls", "unknown", "empty_control_target"])
def test_unimplemented_or_unevaluable_requests_rejected(case, bad):
    mode, controls = "full", False
    if bad == "steps":
        case["steps"] = ["dos"]
    elif bad == "gap":
        mode = "scf-only"
        case["acceptance"] = {"path_gap_ev": [0, 2]}
    elif bad == "controls":
        mode, controls = "scf-only", True
    elif bad == "unknown":
        case["acceptance"] = {"unimplemented_precision": [0, 1]}
    else:
        controls = True
        case["convergence_acceptance"] = {"0": {}}
    with pytest.raises(ValueError):
        qe.build_plan(case, "Protocol", mode, controls)


def test_control_precision_targets_have_explicit_semantics(case):
    case["convergence_acceptance"] = {"0": {"delta_mev_per_atom": [-1, 1]}}
    plan = qe.build_plan(case, "Protocol", convergence=True)
    assert plan["acceptance_semantics"]["numerical_accuracy"] == "targets_requested"
    cfg = plan["effective_case"]
    for difference, expected in [(0.5, True), (2.0, False)]:
        summary = {
            "checks": {},
            "magnetization": {"mean_total_muB_per_atom": None, "total_muB_per_cell": None},
            "convergence": [{"delta_mev_per_atom": difference}],
        }
        qe.evaluate_acceptance(summary, cfg)
        assert summary["checks"]["control_0_delta_mev_per_atom"] is expected


def test_confirmed_scf_only_executes_stub_with_no_accuracy_claim(case, tmp_path, monkeypatch):
    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    for item in case["species"]:
        payload = b"synthetic PP, not physical"
        (pseudo / item["pseudo"]).write_bytes(payload)
        item["sha256"] = hashlib.sha256(payload).hexdigest()
    files = consent(case, tmp_path / "consent", "scf-only")
    calls = []

    def fake(command, *, cwd, stdout, **kwargs):
        calls.append(command)
        path = qe.xml_at(cwd)
        path.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "tests/fixtures/qe_scf_smoke.xml", path)
        stdout.write("JOB DONE.\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(qe.subprocess, "run", fake)
    summary = qe.run(case, pseudo, tmp_path / "run", **files)
    assert len(calls) == 1 and summary["status"] == "passed"
    assert summary["physical_acceptance"] == "not_requested"
    assert summary["numerical_accuracy"] == "not_assessed"
    assert summary["approved_plan_sha256"] == qe.read_plan(files["plan"])["plan_sha256"]


def test_direct_cli_preview_and_unconfirmed_execution(case, tmp_path, monkeypatch):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case))
    protocol = tmp_path / "PROTOCOL.md"
    protocol.write_text("Human-readable draft protocol")
    plan = tmp_path / "plan.json"
    assert_no_calculation(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "plan",
            "--case",
            str(path),
            "--protocol",
            str(protocol),
            "--plan",
            str(plan),
            "--mode",
            "scf-only",
        ],
    )
    qe.main()
    assert qe.read_plan(plan)["steps"] == ["scf"]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "run",
            "--case",
            str(path),
            "--protocol",
            str(protocol),
            "--plan",
            str(plan),
            "--pseudo-dir",
            str(tmp_path),
            "--output",
            str(tmp_path / "run"),
        ],
    )
    with pytest.raises(ValueError, match="confirmation"):
        qe.main()
    assert not (tmp_path / "run").exists()


def test_launcher_rejects_mismatch_before_discovery(case, tmp_path, monkeypatch):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case))
    cfg = qe.load_case(path)
    files = consent(cfg, tmp_path / "consent", backend="simjecture")
    launcher = runpy.run_path(str(ROOT / "scripts/run_qe_in_simjecture.py"))

    def forbidden(*args, **kwargs):
        pytest.fail("Unconfirmed launcher reached capability discovery")

    monkeypatch.setattr(launcher["MVPCapabilityRegistry"], "discover", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "launcher",
            "--project",
            str(ROOT),
            "--case",
            str(path),
            "--protocol",
            str(files["protocol"]),
            "--plan",
            str(files["plan"]),
            "--confirmation",
            str(files["confirmation"]),
            "--pseudo-dir",
            str(tmp_path),
            "--output",
            str(tmp_path / "run"),
            "--memory-mib",
            "4096",
        ],
    )
    with pytest.raises(SystemExit) as error:
        launcher["main"]()
    assert error.value.code == 2 and not (tmp_path / "run").exists()


def test_scf_only_plan_needs_no_unused_band_path(case):
    for key in ("path", "plot_energy_ev", "dos_k", "relax_k"):
        case.pop(key)
    plan = qe.build_plan(case, "SCF-only protocol", "scf-only")
    assert plan["steps"] == ["scf"]
    assert "path" in plan["inactive_parameters"]
    assert "dos/dos.dat" not in plan["expected_products"]


def test_source_identity_change_invalidates_confirmation(case, tmp_path, monkeypatch):
    files = consent(case, tmp_path / "consent")
    monkeypatch.setattr(qe, "digest", lambda path: "f" * 64)
    assert_no_calculation(monkeypatch)
    with pytest.raises(ValueError, match="changed"):
        qe.run(case, tmp_path, tmp_path / "run", **files)
    assert not (tmp_path / "run").exists()


def test_confirmed_direct_cli_executes_only_selected_scf(case, tmp_path, monkeypatch):
    pseudo = tmp_path / "pseudo"
    pseudo.mkdir()
    for item in case["species"]:
        (pseudo / item["pseudo"]).write_bytes(b"synthetic")
        item["sha256"] = hashlib.sha256(b"synthetic").hexdigest()
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case))
    cfg = qe.load_case(path, mode="scf-only")
    files = consent(cfg, tmp_path / "consent", "scf-only")
    calls = []

    def fake(command, *, cwd, stdout, **kwargs):
        calls.append(command)
        xml = qe.xml_at(cwd)
        xml.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "tests/fixtures/qe_scf_smoke.xml", xml)
        stdout.write("JOB DONE.\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(qe.subprocess, "run", fake)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "driver",
            "run",
            "--case",
            str(path),
            "--protocol",
            str(files["protocol"]),
            "--plan",
            str(files["plan"]),
            "--confirmation",
            str(files["confirmation"]),
            "--pseudo-dir",
            str(pseudo),
            "--output",
            str(tmp_path / "run"),
        ],
    )
    qe.main()
    report = json.loads((tmp_path / "run/summary.json").read_text())
    assert len(calls) == 1 and report["status"] == "passed"
    assert report["pdos_status"] == "not_requested"


@pytest.mark.parametrize("material", ["qe_dft_reference", "qe_fe_reference"])
def test_example_precision_targets_are_structured_before_confirmation(material):
    cfg = qe.load_case(ROOT / "demos" / material / "case.json")
    plan = qe.build_plan(cfg, "Example protocol targets", convergence=True)
    assert plan["effective_case"]["convergence_acceptance"]
    assert plan["acceptance_semantics"]["numerical_accuracy"] == "targets_requested"


def test_sandbox_plan_cannot_be_run_as_standalone(case, tmp_path, monkeypatch):
    files = consent(case, tmp_path / "consent", backend="simjecture")
    monkeypatch.setattr(qe, "current_execution_context", lambda: "standalone")
    assert_no_calculation(monkeypatch)
    with pytest.raises(ValueError, match="changed"):
        qe.run(case, tmp_path, tmp_path / "run", **files)
    assert not (tmp_path / "run").exists()


def test_standalone_plan_cannot_be_submitted_to_launcher(case, tmp_path, monkeypatch):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case))
    cfg = qe.load_case(path)
    files = consent(cfg, tmp_path / "consent", backend="standalone")
    launcher = runpy.run_path(str(ROOT / "scripts/run_qe_in_simjecture.py"))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "launcher",
            "--project",
            str(ROOT),
            "--case",
            str(path),
            "--protocol",
            str(files["protocol"]),
            "--plan",
            str(files["plan"]),
            "--confirmation",
            str(files["confirmation"]),
            "--pseudo-dir",
            str(tmp_path),
            "--output",
            str(tmp_path / "run"),
        ],
    )
    with pytest.raises(ValueError, match="changed"):
        launcher["main"]()
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("origin", ["profile", "case", "builtin"])
def test_launcher_limit_sources_match_resolution_and_stay_stable(case, tmp_path, origin):
    case.pop("launcher_limits", None)
    case["profiles"]["review"] = {"launcher_limits": {"memory_mib": 768}}
    if origin == "case":
        case["launcher_limits"] = {"memory_mib": 640}
    elif origin == "builtin":
        case["profiles"]["review"] = {}
    path = tmp_path / "case.json"
    path.write_text(json.dumps(case))
    resolved = qe.load_case(path, "review")
    plan = qe.build_plan(resolved, "Synthetic resource provenance review")
    limits = plan["effective_case"]["launcher_limits"]
    sources = plan["parameter_sources"]
    value, source = {
        "profile": (768, "profile review (fill missing only)"),
        "case": (640, "explicit case"),
        "builtin": (1024, "builtin LAUNCHER_DEFAULTS"),
    }[origin]
    assert limits["memory_mib"] == value
    assert sources["launcher_limits.memory_mib"] == source
    assert limits["workspace_mib"] == 512 and limits["wall_seconds"] == 3600
    for key in ("workspace_mib", "wall_seconds"):
        assert sources["launcher_limits." + key] == "builtin LAUNCHER_DEFAULTS"
    if origin != "builtin":
        assert sources["launcher_limits"] == source
    # Re-resolving an effective case must retain each leaf's provenance.
    assert qe.build_plan(qe.resolve_case(resolved), "Synthetic resource provenance review") == plan
