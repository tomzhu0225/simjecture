import io
import json
import subprocess
import sys
import tarfile
from types import SimpleNamespace

import pytest
from simjecture_monitor import remote_plasma
from simjecture_monitor.remote_plasma import extract_records


def test_transfer_rejects_traversal_links_and_duplicate_names(tmp_path):
    for entries in [["../escape"], ["/absolute"], ["receipt.json", "receipt.json"], ["link"]]:
        path = tmp_path / "transfer.tar"
        with tarfile.open(path, "w") as archive:
            for name in entries:
                item = tarfile.TarInfo(name)
                if name == "link":
                    item.type = tarfile.SYMTYPE
                    item.linkname = "/etc/passwd"
                archive.addfile(item)
        with pytest.raises(ValueError):
            extract_records(path, tmp_path / "received")
    assert not (tmp_path / "escape").exists()


def test_saved_fields_and_receipts_are_extracted_byte_for_byte(tmp_path):
    path = tmp_path / "transfer.tar"
    values = {"receipt.json": b'{"status":"succeeded"}', "plot000040/Level_0/Cell": b"\x00\xff"}
    with tarfile.open(path, "w") as archive:
        for name, value in values.items():
            item = tarfile.TarInfo(name)
            item.size = len(value)
            archive.addfile(item, io.BytesIO(value))
    extract_records(path, tmp_path / "received")
    for name, value in values.items():
        assert (tmp_path / "received" / name).read_bytes() == value


@pytest.mark.parametrize("failure", ["ssh_exit", "timeout", "invalid_archive"])
def test_unconfirmed_transport_is_not_left_queued_or_retried(tmp_path, monkeypatch, failure):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "inputs").write_text("actual requested control")
    (tmp_path / "environment.json").write_text(json.dumps(dict(max_runs=4)))
    profile = tmp_path / "machine.json"
    profile.write_text(
        json.dumps(
            dict(
                machine=dict(
                    known_hosts="known",
                    identity_file="identity",
                    port=22,
                    user="worker",
                    host="example.invalid",
                    run_as="scientist",
                )
            )
        )
    )
    backend = tmp_path / "backend.json"
    backend.write_text(
        json.dumps(
            dict(machine_profile=str(profile), binary="solver", remote_root="controls", gpu=0)
        )
    )
    monkeypatch.setenv("SIMJECTURE_PLASMA_BACKEND", str(backend))
    monkeypatch.setattr(
        sys, "argv", ["remote-plasma", "--name", "control", "--cells", "64", "--steps", "40"]
    )
    attempts = []

    def run(command, **kwargs):
        attempts.append(command)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 180)
        return SimpleNamespace(returncode=255 if failure == "ssh_exit" else 0)

    monkeypatch.setattr(remote_plasma.subprocess, "run", run)
    with pytest.raises((RuntimeError, subprocess.TimeoutExpired, tarfile.ReadError)):
        remote_plasma.main()
    receipt = json.loads((tmp_path / "runs/control/receipt.json").read_text())
    assert len(attempts) == 1
    assert receipt["status"] == "unknown" and receipt["returncode"] is None
    assert receipt["name"] == "control" and receipt["cells"] == 64 and receipt["steps"] == 40
    assert receipt["request_id"] and receipt["reconciliation_required"]
    assert "ended_at" not in receipt  # Remote execution has not been established.
    assert receipt["transport_status"] == ("timeout" if failure == "timeout" else "failed")
    with pytest.raises(FileExistsError):
        remote_plasma.main()
    assert len(attempts) == 1  # The original reservation still owns this run name.
