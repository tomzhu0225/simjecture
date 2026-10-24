"""The public excerpt verifier checks arithmetic and status beyond file hashes."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = Path("demos/qin1_multiphysics")
ASSETS = Path("docs/_static/demos/qin1")
spec = importlib.util.spec_from_file_location("qin1_record", ROOT / DEMO / "verify_record.py")
assert spec is not None and spec.loader is not None
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def test_retained_qin1_excerpt():
    result = verifier.verify(ROOT)
    assert result["matched_EM_comparisons_recomputed"] == 3
    assert result["plasma_controls_recomputed"] == 5
    assert result["failed_flux_checks"] == 5
    assert result["passed_edge_checks"] == 5
    assert result["viewer_cases_checked"] == 4


@pytest.mark.parametrize("corruption", ["field_peak", "flux_verdict", "execution_status"])
def test_qin1_verifier_rejects_inconsistent_record_with_updated_hash(tmp_path, corruption):
    shutil.copytree(ROOT / DEMO, tmp_path / DEMO)
    shutil.copytree(ROOT / ASSETS, tmp_path / ASSETS)
    filename = "em.json" if corruption == "field_peak" else "plasma.json"
    path = tmp_path / DEMO / "record" / filename
    data = json.loads(path.read_text())
    if corruption == "field_peak":
        data["cases"]["paired_feed_n3"]["peak_B7_T"] *= 1.1
    elif corruption == "flux_verdict":
        data["sensitivity"][0]["flux_within_10percent"] = True
    else:
        data["records"][0]["complete_requested_220ns"] = False
    path.write_text(json.dumps(data, indent=2) + "\n")
    manifest_path = tmp_path / DEMO / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest[str(path.relative_to(tmp_path))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    with pytest.raises(AssertionError):
        verifier.verify(tmp_path)
