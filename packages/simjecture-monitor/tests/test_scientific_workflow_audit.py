import importlib.util
from pathlib import Path

from simjecture_monitor.events import digest


def module(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "scientific_audit_test", scripts / "audit_scientific_workflows.py"
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_absent_report_matches_failed_verifier_receipt_without_faking_an_artifact(
    tmp_path, monkeypatch
):
    audit = module(monkeypatch)
    path = tmp_path / "results.json"
    assert digest(audit.verifier_report_value(path)) == digest({})
    assert not path.exists()
    path.write_text('{"unfinished":')
    assert digest(audit.verifier_report_value(path)) == digest({})
    path.write_text('{"runs": [1, 2]}')
    assert audit.verifier_report_value(path) == {"runs": [1, 2]}


def test_family_bootstrap_retains_both_seeds_and_paired_direction(monkeypatch):
    audit = module(monkeypatch)
    records = []
    for family in ["a", "b"]:
        for seed in [0, 1]:
            for arm, value in [("rules", 1), ("adapted", 0)]:
                records.append(
                    dict(family=family, block=f"{family}-{seed}", arm=arm, complete=value)
                )
    result = audit.paired_interval(records, "rules", "complete", draws=100)
    assert result["clusters"] == 2
    assert result["difference"] == -1 and result["interval95"] == [-1, -1]
