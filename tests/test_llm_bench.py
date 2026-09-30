"""Task integrity, numeric controls, isolated execution and visible GUI entry."""

import csv
import json
import math
import threading
import tomllib

import numpy as np
import pytest

from conjecture_solver.execution import probe_execution_backend
from conjecture_solver.llm_bench import fixtures, reference
from conjecture_solver.llm_bench import pack as benchmark_pack
from conjecture_solver.llm_bench.exporter import export
from conjecture_solver.llm_bench.pack import HERE, grade, prepare, render_verified_plots
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def oracle(task, path):
    prepare(task, path)
    function = reference.csv_result if task == "csv-energy" else reference.rz_result
    values = {name: function(path / "raw" / name) for name in ("n64", "n128")}
    result = {"cases": {name: value[0] for name, value in values.items()}}
    if task == "rz-diagnostics":
        result["relative_grid_differences"] = {
            key: abs(values["n128"][0][key] - values["n64"][0][key])
            / max(abs(values["n128"][0][key]), 1e-12)
            for key in ("K_in_peak_J", "E_rad_total_J", "E_rad_compression_J")
        }
        (path / "plot-data.json").write_text(
            json.dumps({"cases": {name: value[1] for name, value in values.items()}})
        )
    (path / "result.json").write_text(json.dumps(result))
    (path / "reduce.py").write_text(
        (HERE / "reference.py").read_text()
        + f"\ndef reduce_case(directory):\n    return {function.__name__}"
        + "(directory)[0]\n"
    )
    (path / "FINDINGS.md").write_text("Oracle control only; no physical claim approval.")


@pytest.fixture
def bubblewrap():
    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Bubblewrap namespaces are required for submitted-code grading")


def test_closed_form_csv_and_unpaired_rejection(tmp_path):
    cases = fixtures.create(tmp_path / "fixtures", "csv-energy", 104)
    totals = []
    for path in cases.values():
        with (path / "radiation_boundary.csv").open() as stream:
            increments = [float(row["escaped_energy_erg"]) for row in csv.DictReader(stream)]
        result, curves = reference.csv_result(path)
        assert math.isclose(result["E_rad_total_J"], sum(increments) * 1e-7)
        assert math.isclose(curves["cumulative_radiation_J"][-1], result["E_rad_total_J"])
        totals.append(result["E_rad_total_J"])
    assert len(set(totals)) == 3
    file = next(iter(cases.values())) / "operator_budget.csv"
    file.write_text(
        "\n".join(
            line for line in file.read_text().splitlines() if not line.startswith("radiation_after")
        )
        + "\n"
    )
    with pytest.raises(ValueError, match="Unpaired"):
        reference.csv_result(file.parent)


def test_closed_form_rz_leaf_volume_and_clock(tmp_path):
    h5py = pytest.importorskip("h5py")
    path = next(iter(fixtures.create(tmp_path / "fields", "rz-diagnostics", 19).values()))
    for step, file in enumerate(sorted(path.glob("stagnation_hdf5_plt_cnt_*"))):
        clock = (0, 1e-9, 2.3e-9, 4.6e-9, 8e-9)[step]
        with h5py.File(file, "w") as f:
            f["real scalars"] = np.array(
                [(b"time", clock)], dtype=[("name", "S80"), ("value", "f8")]
            )
            f["node type"] = [1, 2, 1]
            f["bounding box"] = [
                [[0, 1], [0, 1], [0, 1]],
                [[0, 2], [0, 1], [0, 1]],
                [[1, 2], [0, 1], [0, 1]],
            ]
            for key, value in {
                "dens": 1,
                "line": 1,
                "velx": -2,
                "vely": 3,
                "velz": 0,
                "magx": 2,
                "magy": 0,
                "magz": 0,
                "eint": 10 + step,
                "erad": 1,
            }.items():
                a = np.full((3, 1, 1, 1), float(value))
                a[1] = 1e25  # Covered field contributes nothing.
                f[key] = a
    result, curves = reference.rz_result(path)
    assert math.isclose(result["K_in_peak_J"], 8 * math.pi * 1e-7)
    assert math.isclose(result["delta_stored_J"], 16 * math.pi * 1e-7)
    assert result["t_ref_ns"] == 0
    assert result["mechanism_proven"] is False
    assert len(curves["time_s"]) == 5
    assert reference.comparisons({"time_s": [1e-9]}, {"time_s": [2e-9]})[0]["passed"] is False


@pytest.mark.parametrize("task", ["csv-energy", "rz-diagnostics"])
def test_real_recorded_oracle_and_noop(tmp_path, bubblewrap, task):
    path = tmp_path / "task"
    oracle(task, path)
    report = grade(task, path)
    assert report["passed"], report["error"]
    assert report["scientific_claim_approved"] is False
    assert report["trial"]["input_tokens"] is None
    if task == "rz-diagnostics":
        render_verified_plots(task, path, report, tmp_path / "plots")
        assert (tmp_path / "plots/verified-energies.png").is_file()
    (path / "reduce.py").unlink()
    assert grade(task, path)["passed"] is False


def test_constant_answers_and_modified_inputs_rejected(tmp_path, bubblewrap):
    path = tmp_path / "task"
    oracle("csv-energy", path)
    answer = reference.csv_result(path / "raw/n64")[0]
    (path / "reduce.py").write_text(f"def reduce_case(directory):\n    return {answer!r}\n")
    report = grade("csv-energy", path)
    assert not report["passed"]
    assert any(not c["passed"] for c in report["checks"] if c["metric"].startswith("holdout"))
    oracle_path = tmp_path / "modified"
    oracle("csv-energy", oracle_path)
    (oracle_path / "raw/n64/radiation_boundary.csv").write_text("modified")
    (oracle_path / "result.json").write_text('{"cases":[]}')
    report = grade("csv-energy", oracle_path)
    assert not report["intact_inputs"] and not report["passed"]


def test_harbor_export_keeps_verifier_out_of_agent_image(tmp_path):
    export("csv-energy", tmp_path / "export")
    root = tmp_path / "export"
    spec = tomllib.loads((root / "task.toml").read_text())
    assert spec["verifier"]["environment_mode"] == "separate"
    assert spec["agent"]["user"] == "agent"
    assert spec["environment"]["network_mode"] == "public"
    assert not list((root / "environment").rglob("*reference*"))
    assert not list((root / "environment").rglob("*plt_cnt*"))
    compile((root / "tests/driver.py").read_text(), "driver", "exec")
    compile((root / "solution/solve.py").read_text(), "solve", "exec")


def test_missing_hdf5_extra_reports_setup_error_before_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_pack.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(ValueError, match="requires h5py"):
        grade("rz-diagnostics", tmp_path)


def test_browser_benchmark_preparation_and_failed_grading(tmp_path, bubblewrap):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#benchmarks")
            playwright.expect(page.locator("#benchmark-tasks")).to_contain_text("CSV energy")
            page.locator("#benchmark-tasks button").first.click()
            playwright.expect(page.locator("#chat-input")).to_have_value(
                __import__("re").compile("Complete the benchmark")
            )
            assert len(app.workspace.projects()) == 1
            assert not list(app.workspace.projects_root.glob("*/turns/*"))
            page.locator('[data-view="benchmarks"]').click()
            page.locator("#benchmark-projects button").first.click()
            playwright.expect(page.locator("#benchmark-report")).to_contain_text(
                '"passed": false', timeout=30000
            )
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
