import io
import tarfile

import pytest
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
