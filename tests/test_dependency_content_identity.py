"""OverlayFS inode changes must not invalidate a verified source snapshot."""

import hashlib
import json
import shutil

import pytest

from conjecture_solver.mvp_skills import _dependency_identity


def snapshot(root):
    root.mkdir()
    (root / "solver.F90").write_text("! reference source\n")
    (root / ".simjecture-source-manifest.json").write_text(
        json.dumps(
            {
                "solver.F90": hashlib.sha256((root / "solver.F90").read_bytes()).hexdigest(),
            }
        )
    )
    return _dependency_identity(root)


def test_source_identity_survives_different_inode_with_identical_bytes(tmp_path):
    root = tmp_path / "source"
    expected = snapshot(root)
    inode = root.stat().st_ino
    root.rename(tmp_path / "old-source")
    shutil.copytree(tmp_path / "old-source", root)
    assert root.stat().st_ino != inode
    assert _dependency_identity(root) == expected
    (root / "solver.F90").write_text("! modified source\n")
    with pytest.raises(RuntimeError, match="source file changed"):
        _dependency_identity(root)


@pytest.mark.parametrize(
    "files",
    [{"../outside": "a" * 64}, {"/etc/passwd": "a" * 64}, {}, [], {"solver.F90": "unverified"}],
)
def test_manifest_rejects_escape_or_invalid_hashes(tmp_path, files):
    snapshot(tmp_path / "source")
    (tmp_path / "source/.simjecture-source-manifest.json").write_text(json.dumps(files))
    with pytest.raises(ValueError):
        _dependency_identity(tmp_path / "source")


def test_manifest_rejects_external_symlink(tmp_path):
    snapshot(tmp_path / "source")
    (tmp_path / "outside").write_text("! reference source\n")
    source = tmp_path / "source/solver.F90"
    source.unlink()
    source.symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="escapes"):
        _dependency_identity(source.parent)


@pytest.mark.parametrize("kind", ["directory", "broken-symlink"])
def test_manifest_path_must_be_regular_file(tmp_path, kind):
    snapshot(tmp_path / "source")
    manifest = tmp_path / "source/.simjecture-source-manifest.json"
    manifest.unlink()
    if kind == "directory":
        manifest.mkdir()
    else:
        manifest.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="regular file"):
        _dependency_identity(manifest.parent)
