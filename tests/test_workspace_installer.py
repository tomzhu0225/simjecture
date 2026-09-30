"""Exercise the installer without network access or host package changes."""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/install-workspace.sh"


def fixture(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "uv.lock", "README.md", "LICENSE"):
        (source / name).write_text("fixture")
    for name in ("src", "skills", "capabilities", "integrations", "scripts", "environments"):
        (source / name).mkdir()
    (source / "src/module.py").write_text('print("fixture")')
    (source / "src/__pycache__").mkdir()
    (source / "src/__pycache__/private.pyc").write_text("excluded")
    binary = tmp_path / "bin"
    binary.mkdir()
    log = tmp_path / "uv.log"
    (binary / "uv").write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$INSTALL_TEST_LOG"\n')
    (binary / "bwrap").write_text("#!/bin/sh\nexit 0\n")
    for p in binary.iterdir():
        p.chmod(0o755)
    env = os.environ | dict(
        PATH=str(binary) + os.pathsep + os.environ["PATH"],
        SIMJECTURE_SOURCE_DIR=str(source),
        SIMJECTURE_INSTALL_DIR=str(tmp_path / "installed"),
        INSTALL_TEST_LOG=str(log),
    )
    return env, log, tmp_path / "installed"


def test_installer_prepares_locked_environment_and_preserves_existing_work(tmp_path):
    env, log, target = fixture(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--no-start"], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "python install 3.12" in log.read_text()
    assert "--frozen --extra workspace --no-dev" in log.read_text()
    assert (target / "app/0.5.3rc2/src/module.py").exists()
    assert not (target / "app/0.5.3rc2/src/__pycache__").exists()
    assert os.access(target / "start-workspace", os.X_OK)
    (target / "artifacts").mkdir(exist_ok=True)
    (target / "artifacts/keep.txt").write_text("user research")
    result = subprocess.run(
        ["bash", str(SCRIPT), "--no-start"], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert (target / "artifacts/keep.txt").read_text() == "user research"


def test_installer_refuses_unmanaged_destination(tmp_path):
    env, log, target = fixture(tmp_path)
    target.mkdir()
    (target / "keep").write_text("existing")
    result = subprocess.run(
        ["bash", str(SCRIPT), "--no-start"], env=env, capture_output=True, text=True
    )
    assert result.returncode != 0 and "already exists" in result.stderr
    assert not log.exists()
    assert (target / "keep").read_text() == "existing"


def test_download_checksum_failure_does_not_install(tmp_path):
    env, log, target = fixture(tmp_path)
    release = tmp_path / "release"
    release.mkdir()
    name = "simjecture-0.5.3rc2-workspace.tar.gz"
    (release / name).write_bytes(b"tampered archive")
    (release / "SHA256SUMS").write_text("0" * 64 + "  " + name + "\n")
    env.pop("SIMJECTURE_SOURCE_DIR")
    env["SIMJECTURE_RELEASE_BASE"] = release.as_uri()
    result = subprocess.run(
        ["bash", "-s", "--", "--no-start"],
        input=SCRIPT.read_text(),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not log.exists() and not target.exists()


def test_failed_upgrade_keeps_previous_version_and_research(tmp_path):
    env, log, target = fixture(tmp_path)
    target.mkdir()
    (target / ".simjecture-bootstrap").write_text("managed")
    (target / ".current-version").write_text("0.5.1\n")
    (target / "start-workspace").write_text("old launcher")
    (target / "artifacts").mkdir()
    (target / "artifacts/result.txt").write_text("research")
    (tmp_path / "bin/uv").write_text("#!/bin/sh\nexit 42\n")
    result = subprocess.run(
        ["bash", str(SCRIPT), "--no-start"], env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert (target / ".current-version").read_text() == "0.5.1\n"
    assert (target / "start-workspace").read_text() == "old launcher"
    assert (target / "artifacts/result.txt").read_text() == "research"
