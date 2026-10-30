"""Review must use worker-recorded document bytes, even without a fetch receipt."""

import hashlib

import pytest

from conjecture_solver.research_audit import review_documents


def receipt(data):
    return {
        "outputs": ["result.json"],
        "remote_job": "job_" + "a" * 40,
        "artifacts": {},
        "remote_artifacts": {
            "result.json": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        },
    }


@pytest.mark.parametrize("size", [8, 40000])
@pytest.mark.parametrize("corruption", ["content", "size", "missing_index"])
def test_remote_documents_cannot_be_forged_in_local_workspace(tmp_path, size, corruption):
    original = b"1" * size
    record = receipt(original)
    path = tmp_path / "result.json"
    path.write_bytes(b"2" * size if corruption == "content" else original)
    # A fabricated cache receipt must not override the terminal worker index.
    record["artifacts"]["result.json"] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": size,
    }
    if corruption == "size":
        record["remote_artifacts"]["result.json"]["bytes"] += 1
    if corruption == "missing_index":
        record["remote_artifacts"].clear()
    with pytest.raises(ValueError, match="(changed|recorded|index)"):
        review_documents(tmp_path, record, review_root=tmp_path)


@pytest.mark.parametrize("size", [8, 40000])
def test_byte_identical_remote_document_does_not_need_a_fetch_receipt(tmp_path, size):
    data = b"1" * size
    record = receipt(data)
    (tmp_path / "result.json").write_bytes(data)
    docs, raw, _ = review_documents(tmp_path, record, review_root=tmp_path)
    assert not raw
    if size < 32768:
        assert docs["result.json"] == data.decode()
    else:
        assert docs["result.json"]["reference"]["sha256"] == hashlib.sha256(data).hexdigest()
        assert docs["result.json"]["reference"]["bytes"] == size
