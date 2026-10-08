import hashlib
import io
import subprocess

import pytest

from conjecture_solver import runtime_bootstrap as bootstrap


def test_micromamba_bootstrap_verifies_download_and_reuses_binary(tmp_path, monkeypatch):
    payload = b"fixture binary"
    monkeypatch.setattr(bootstrap.platform, "system", lambda: "Linux")
    monkeypatch.setattr(bootstrap.platform, "machine", lambda: "x86_64")
    monkeypatch.setitem(
        bootstrap.MICROMAMBA_ASSETS, "x86_64", ("linux-64", hashlib.sha256(payload).hexdigest())
    )
    downloads = []

    def download(url, **kwargs):
        downloads.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(bootstrap.urllib.request, "urlopen", download)
    target = bootstrap.ensure_micromamba(tmp_path / "runtime", dry_run=True)
    assert not (tmp_path / "runtime").exists() and not downloads
    assert bootstrap.ensure_micromamba(tmp_path / "runtime") == target
    assert bootstrap.ensure_micromamba(tmp_path / "runtime") == target
    assert len(downloads) == 1


def test_micromamba_bad_checksum_never_publishes_executable(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.platform, "system", lambda: "Linux")
    monkeypatch.setattr(bootstrap.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        bootstrap.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(b"corrupt")
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        bootstrap.ensure_micromamba(tmp_path)
    assert not list((tmp_path / "bootstrap").iterdir())


def test_dependency_installation_retries_and_then_reuses_completed_environment(
    tmp_path, monkeypatch
):
    prefix = tmp_path / "optab"
    calls = []
    monkeypatch.setattr(bootstrap, "ensure_micromamba", lambda _: "/verified/micromamba")

    def run(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, command)
        (prefix / "conda-meta").mkdir(parents=True)
        (prefix / "conda-meta/history").write_text("installed")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.prepare_runtime_environment("optab", prefix)
    bootstrap.prepare_runtime_environment("optab", prefix)
    bootstrap.prepare_runtime_environment("optab", prefix)
    assert len(calls) == 2
    assert "gfortran_linux-64=12" in calls[1]
    assert any(p.startswith("hdf5=") for p in calls[1])


def test_dependency_preparation_preserves_unmanaged_files(tmp_path):
    prefix = tmp_path / "existing"
    prefix.mkdir()
    valuable = prefix / "notes"
    valuable.write_text("keep")
    with pytest.raises(ValueError, match="unmanaged"):
        bootstrap.prepare_runtime_environment("optab", prefix)
    assert valuable.read_text() == "keep"


def test_cuda_registration_tracks_nested_active_native_library(tmp_path, monkeypatch):
    import json
    import runpy
    import sys
    from pathlib import Path

    from conjecture_solver.mvp_skills import MVPCapabilityInstallation

    repo = Path(__file__).parents[1]
    runtime = tmp_path / ".runtime/warpx-cuda-openpmd"
    package = runtime / "lib/python3.12/site-packages/pywarpx"
    nested = package / "site-packages/pywarpx/warpx_pybind_2d.so"
    for p, value in [
        (runtime / "bin/python", b"fixture interpreter"),
        (runtime / "share/build-record.json", b"{}"),
        (runtime / "conda-meta/history", b"fixture dependencies"),
        (package / "__init__.py", b""),
        (package / "libamrex.so", b"fixture amrex"),
        (nested, b"active solver version one"),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value)
    (runtime / "bin/python").chmod(0o755)
    for name in ("cuda-toolkit-12.4", "warpx-cuda-openpmd-deps"):
        (tmp_path / ".runtime" / name).mkdir()
    (tmp_path / "capabilities").mkdir()
    template = "warpx-cuda-openpmd-26.07.json"
    (tmp_path / "capabilities" / template).write_bytes(
        (repo / "capabilities" / template).read_bytes()
    )
    exists = Path.exists

    def device_exists(path):
        if str(path).startswith("/dev/"):
            return str(path) == "/dev/nvidia0"
        return exists(path)

    monkeypatch.setattr(Path, "exists", device_exists)
    monkeypatch.setattr(sys, "argv", ["register_cuda_runtime.py", str(tmp_path)])
    runpy.run_path(str(repo / "scripts/register_cuda_runtime.py"), run_name="__main__")
    descriptor = runtime / "capabilities" / template
    config = json.loads(descriptor.read_text())
    assert str(nested.relative_to(runtime)) in config["identity_files"]
    installed = MVPCapabilityInstallation.read(descriptor)
    nested.write_bytes(b"active solver changed while metadata stayed the same")
    with pytest.raises(RuntimeError, match="changed after campaign discovery"):
        installed.assert_runtime_identity()
    assert MVPCapabilityInstallation.read(descriptor).contract_hash != installed.contract_hash
