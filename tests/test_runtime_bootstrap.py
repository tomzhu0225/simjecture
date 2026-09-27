import hashlib
import io

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
