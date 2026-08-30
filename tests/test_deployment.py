from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.deployment import (
    PINNED_WARPX_REVISION,
    DeploymentCheck,
    DeploymentCheckStatus,
    DeploymentManager,
    DeploymentProfile,
    resolve_project_root,
)
from conjecture_solver.mvp_skills import MVPCapabilityConfig


def _capability_payload(name: str, runtime_root: str) -> dict[str, object]:
    return {
        "environment": {},
        "executable": "bin/python",
        "manifest": {
            "description": f"Test deployment for {name}",
            "executable_kind": "python-test",
            "name": name,
            "schema_version": "0.1.0",
            "skill": "warpx",
            "version": "26.07",
        },
        "runtime_root": runtime_root,
    }


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "capabilities").mkdir(parents=True)
    (root / "environments").mkdir()
    (root / "skills/warpx/scripts").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='test-deployment'\n")
    (root / "environments/warpx-cpu.yml").write_text(
        "name: acs-warpx-cpu-26-07\nchannels: [conda-forge]\n"
        "dependencies: [python=3.11, warpx=26.07]\n"
    )
    (root / "capabilities/warpx-cpu-26.07.json").write_text(
        json.dumps(
            _capability_payload("warpx-cpu-26.07", "../.runtime/warpx-cpu")
        )
    )
    (root / "capabilities/warpx-cuda-openpmd-26.07.json").write_text(
        json.dumps(
            _capability_payload(
                "warpx-cuda-openpmd-26.07",
                "../.runtime/warpx-cuda-openpmd",
            )
        )
    )
    (root / "capabilities/flash-island-coalescence-resistive-mhd-4.8.json").write_text(
        json.dumps(
            _capability_payload(
                "flash-island-coalescence-resistive-mhd-4.8",
                "../.runtime/flash-island-coalescence-resistive-mhd-4.8",
            )
        )
    )
    for name, runtime in (
        ("atomec-1.4.0", "../.runtime/atomec-1.4.0"),
        ("singularity-eos-1.12.1", "../.runtime/singularity-eos-1.12.1"),
        ("m-aneos-1.0", "../.runtime/m-aneos-1.0"),
        ("optab-1.3.1", "../.runtime/optab-1.3.1"),
    ):
        (root / "capabilities" / f"{name}.json").write_text(
            json.dumps(_capability_payload(name, runtime))
        )
    bootstrap = root / "skills/warpx/scripts/bootstrap_local_cuda.sh"
    bootstrap.write_text("#!/usr/bin/env bash\nexit 0\n")
    bootstrap.chmod(0o755)
    for relative in (
        "skills/eos/scripts/bootstrap_atomec.sh",
        "skills/eos/scripts/bootstrap_singularity_eos.sh",
        "skills/eos/scripts/bootstrap_maneos.sh",
        "skills/opacity/scripts/bootstrap_optab.sh",
        "skills/flash-mhd/scripts/bootstrap_flash.sh",
    ):
        script = root / relative
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("#!/usr/bin/env bash\nexit 0\n")
        script.chmod(0o755)
    return root


def _passing_core(_self: DeploymentManager, *, probe: bool) -> list[DeploymentCheck]:
    return [
        DeploymentCheck(
            name="core.test",
            status=DeploymentCheckStatus.PASS,
            detail=f"probe={probe}",
        )
    ]


def _materialize_runtime(root: Path, relative: str) -> Path:
    runtime = root / relative
    executable = runtime / "bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/usr/bin/env sh\nexit 0\n")
    executable.chmod(0o755)
    (runtime / "conda-meta").mkdir()
    return runtime


def test_resolve_project_root_requires_deployment_assets(tmp_path: Path) -> None:
    root = _project(tmp_path)
    assert resolve_project_root(root) == root
    with pytest.raises(FileNotFoundError, match="deployment requires a source checkout"):
        resolve_project_root(tmp_path / "missing")


def test_cli_parses_install_and_doctor_profiles() -> None:
    install = build_parser().parse_args(
        ["install", "warpx-cpu", "--dry-run", "--environment-manager", "mamba"]
    )
    assert install.profile == "warpx-cpu"
    assert install.dry_run is True
    assert install.environment_manager == "mamba"

    doctor = build_parser().parse_args(
        ["doctor", "--profile", "warpx-cuda", "--skip-probes", "--json"]
    )
    assert doctor.profile == "warpx-cuda"
    assert doctor.skip_probes is True
    assert doctor.json is True

    flash = build_parser().parse_args(["doctor", "--profile", "flash", "--json"])
    assert flash.profile == "flash"

    atomec = build_parser().parse_args(["doctor", "--profile", "atomec", "--json"])
    assert atomec.profile == "atomec"
    optab = build_parser().parse_args(["install", "optab", "--dry-run"])
    assert optab.profile == "optab"
    assert optab.dry_run is True

    flash_remote = build_parser().parse_args(
        [
            "install",
            "flash",
            "--repository",
            "git@github.com:example/flash.git",
            "--git-ref",
            "v4.8",
        ]
    )
    assert flash_remote.repository == "git@github.com:example/flash.git"
    assert flash_remote.git_ref == "v4.8"


def test_doctor_treats_uninstalled_optional_capabilities_as_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = DeploymentManager(_project(tmp_path))
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.doctor("all", probe=False)

    assert report.ready is True
    warnings = [item for item in report.checks if item.status is DeploymentCheckStatus.WARNING]
    assert len(warnings) == 7
    assert all(not item.required for item in warnings)


def test_flash_install_is_verification_only_and_never_provisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIMJECTURE_PRIVATE_ROOT", raising=False)
    root = _project(tmp_path)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.install(DeploymentProfile.FLASH, dry_run=True)

    assert report.profile == "flash"
    assert report.ready is False
    assert report.planned is False
    assert report.command == ()
    assert not (root / ".runtime").exists()
    failure = next(item for item in report.checks if item.name.startswith("capability.flash"))
    assert "official FLASH Center" in (failure.remedy or "")
    assert "private" in (failure.remedy or "")


def test_flash_install_clones_operator_repository_without_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SIMJECTURE_PRIVATE_ROOT", raising=False)
    root = _project(tmp_path)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.install(
        DeploymentProfile.FLASH,
        dry_run=True,
        repository="git@github.com:example/flash.git",
        git_ref="abc123",
    )

    assert report.planned is True
    assert report.command[0] == str(
        root / "skills/flash-mhd/scripts/bootstrap_flash.sh"
    )
    assert report.command[report.command.index("--git-url") + 1] == (
        "git@github.com:example/flash.git"
    )
    assert report.command[report.command.index("--git-ref") + 1] == "abc123"
    assert "--source" not in report.command
    assert not (root / ".runtime").exists()


def test_flash_install_uses_private_overlay_without_public_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    overlay = root / ".private/flash"
    overlay.mkdir(parents=True)
    bootstrap = overlay / "bootstrap.sh"
    bootstrap.write_text("#!/usr/bin/env bash\nexit 0\n")
    bootstrap.chmod(0o755)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    remote = manager.install(DeploymentProfile.FLASH, dry_run=True, jobs=2)
    assert remote.planned is True
    assert remote.command[0] == str(bootstrap.resolve())
    assert "--source" not in remote.command
    assert not (root / ".runtime").exists()

    source = tmp_path / "flash-source"
    source.mkdir()
    planned = manager.install(
        DeploymentProfile.FLASH,
        dry_run=True,
        source=source,
        jobs=2,
    )
    assert planned.planned is True
    assert "--source" in planned.command
    assert str(source.resolve()) in planned.command


def test_flash_private_overlay_env_overrides_checkout_dot_private(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    checkout_overlay = root / ".private/flash"
    checkout_overlay.mkdir(parents=True)
    ignored = checkout_overlay / "bootstrap.sh"
    ignored.write_text("#!/usr/bin/env bash\nexit 1\n")
    ignored.chmod(0o755)
    env_root = tmp_path / "overlay"
    env_overlay = env_root / "flash"
    env_overlay.mkdir(parents=True)
    bootstrap = env_overlay / "bootstrap.sh"
    bootstrap.write_text("#!/usr/bin/env bash\nexit 0\n")
    bootstrap.chmod(0o755)
    monkeypatch.setenv("SIMJECTURE_PRIVATE_ROOT", str(env_root))
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)
    source = tmp_path / "flash-source"
    source.mkdir()

    planned = manager.install(
        DeploymentProfile.FLASH,
        dry_run=True,
        source=source,
    )
    assert planned.command[0] == str(bootstrap.resolve())


@pytest.mark.parametrize(
    ("profile", "script", "runtime"),
    (
        ("atomec", "skills/eos/scripts/bootstrap_atomec.sh", "atomec-1.4.0"),
        (
            "singularity-eos",
            "skills/eos/scripts/bootstrap_singularity_eos.sh",
            "singularity-eos-1.12.1",
        ),
        ("m-aneos", "skills/eos/scripts/bootstrap_maneos.sh", "m-aneos-1.0"),
        ("optab", "skills/opacity/scripts/bootstrap_optab.sh", "optab-1.3.1"),
    ),
)
def test_eos_opacity_install_dry_run_is_non_mutating_and_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    profile: str,
    script: str,
    runtime: str,
) -> None:
    root = _project(tmp_path)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.install(DeploymentProfile(profile), dry_run=True, jobs=4)

    assert report.profile == profile
    assert report.planned is True
    assert report.ready is False
    assert report.command[0] == str(root / script)
    assert report.command[1:7] == (
        "--prefix",
        str((root / ".runtime" / runtime).resolve()),
        "--project-root",
        str(root),
        "--jobs",
        "4",
    )
    assert not (root / ".runtime").exists()


def test_eos_install_refuses_unmanaged_existing_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    (root / ".runtime/atomec-1.4.0").mkdir(parents=True)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.install(DeploymentProfile.ATOMEC, repair=True)

    assert report.ready is False
    assert any(item.name == "install.atomec.existing_runtime" for item in report.checks)


def test_core_doctor_enforces_locked_direct_dependency_versions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    locked = {
        "simjecture": "0.1.0",
        "httpx": "0.28.1",
        "matplotlib": "3.10.0",
        "numpy": "2.2.0",
        "pandas": "2.2.0",
        "pydantic": "2.10.0",
        "scipy": "1.15.0",
    }
    records = ["version = 1"]
    for name, version in locked.items():
        records.extend(
            (
                "",
                "[[package]]",
                f'name = "{name}"',
                f'version = "{version}"',
            )
        )
    (root / "uv.lock").write_text("\n".join(records) + "\n")
    installed = {**locked, "numpy": "1.26.4"}
    monkeypatch.setattr(
        "conjecture_solver.deployment.metadata.version",
        lambda distribution: installed[distribution],
    )
    monkeypatch.setattr("conjecture_solver.deployment.shutil.which", lambda _name: None)

    checks = DeploymentManager(root)._core_checks(probe=False)
    by_name = {item.name: item for item in checks}

    assert by_name["core.lock"].status is DeploymentCheckStatus.PASS
    assert (
        by_name["core.package.httpx"].status
        is DeploymentCheckStatus.PASS
    )
    assert (
        by_name["core.package.numpy"].status
        is DeploymentCheckStatus.FAIL
    )
    assert "locked=2.2.0" in by_name["core.package.numpy"].detail


def test_cpu_install_dry_run_is_non_mutating_and_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)
    monkeypatch.setattr(
        "conjecture_solver.deployment.shutil.which",
        lambda name: "/opt/micromamba" if name == "micromamba" else None,
    )

    report = manager.install(DeploymentProfile.WARPX_CPU, dry_run=True)

    assert report.planned is True
    assert report.ready is False
    assert report.command[:3] == ("/opt/micromamba", "create", "--yes")
    assert str(root / ".runtime/warpx-cpu") in report.command
    assert not (root / ".runtime").exists()


def test_cpu_install_creates_and_validates_managed_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)
    monkeypatch.setattr(
        "conjecture_solver.deployment.shutil.which",
        lambda name: "/opt/micromamba" if name == "micromamba" else None,
    )

    def fake_run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        prefix = Path(command[command.index("--prefix") + 1])
        relative = prefix.relative_to(prefix.parent.parent).as_posix()
        _materialize_runtime(prefix.parent.parent, relative)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("conjecture_solver.deployment.subprocess.run", fake_run)

    report = manager.install(
        DeploymentProfile.WARPX_CPU,
        capture_output=True,
    )

    assert report.ready is True
    assert report.changed is True
    assert (root / ".runtime/deployment/warpx-cpu.json").is_file()
    assert any(
        item.name == "capability.warpx-cpu-26.07.preflight"
        and item.status is DeploymentCheckStatus.PASS
        for item in report.checks
    )


def test_cpu_install_refuses_unmanaged_existing_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    (root / ".runtime/warpx-cpu").mkdir(parents=True)
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.install(DeploymentProfile.WARPX_CPU, repair=True)

    assert report.ready is False
    assert any("non-Conda" in item.detail for item in report.checks)


def test_cuda_dry_run_requires_exact_audited_source_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path)
    source = tmp_path / "warpx"
    source.mkdir()
    manager = DeploymentManager(root)
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)
    monkeypatch.setattr(
        "conjecture_solver.deployment.shutil.which",
        lambda name: "/usr/bin/git" if name == "git" else None,
    )

    def wrong_revision(
        command: tuple[str, ...], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "deadbeef\n", "")

    monkeypatch.setattr("conjecture_solver.deployment.subprocess.run", wrong_revision)
    rejected = manager.install(
        DeploymentProfile.WARPX_CUDA,
        source=source,
        dry_run=True,
    )
    assert rejected.ready is False
    assert rejected.planned is False
    assert any("deadbeef" in item.detail for item in rejected.checks)

    def pinned_revision(
        command: tuple[str, ...], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, f"{PINNED_WARPX_REVISION}\n", "")

    monkeypatch.setattr("conjecture_solver.deployment.subprocess.run", pinned_revision)
    planned = manager.install(
        DeploymentProfile.WARPX_CUDA,
        source=source,
        jobs=4,
        arch="89",
        dry_run=True,
    )
    assert planned.planned is True
    assert planned.command[-4:] == ("--jobs", "4", "--arch", "89")


def test_cuda_repair_is_structured_refusal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = DeploymentManager(_project(tmp_path))
    monkeypatch.setattr(DeploymentManager, "_core_checks", _passing_core)

    report = manager.install(DeploymentProfile.WARPX_CUDA, repair=True)

    assert report.ready is False
    assert any(item.name == "install.warpx-cuda.repair" for item in report.checks)


def test_committed_eos_and_opacity_capability_configs_parse() -> None:
    root = Path(__file__).resolve().parents[1] / "capabilities"
    expected = {
        "atomec-1.4.0": "eos",
        "singularity-eos-1.12.1": "eos",
        "m-aneos-1.0": "eos",
        "optab-1.3.1": "opacity",
    }
    for name, skill in expected.items():
        config = MVPCapabilityConfig.model_validate_json(
            (root / f"{name}.json").read_bytes()
        )
        assert config.manifest.name == name
        assert config.manifest.skill == skill
        assert config.manifest.preflight_resource is not None
        assert config.manifest.preflight_resource.startswith("examples/")
        assert config.executable == "bin/python"
