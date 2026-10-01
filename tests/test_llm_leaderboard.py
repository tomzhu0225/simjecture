"""Fair denominators, pricing uncertainty, trial identity and visible controls."""

import copy
import json
import threading

import httpx
import pytest

from conjecture_solver.llm_bench.leaderboard import normalize, public_grade, summarize
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def trial(identifier, *, model="deepseek-flash", passed=True, wall=50, budget=180, effort="high"):
    return {
        "schema_version": "0.1.0",
        "pack_version": "0.1.0",
        "task": "csv-energy",
        "task_contract_sha256": "a" * 64,
        "execution_backend": "bubblewrap",
        "passed": passed,
        "checks": [{"passed": passed}],
        "intact_inputs": True,
        "findings_present": True,
        "scientific_claim_approved": False,
        "trial": {
            "trial_id": identifier,
            "model": model,
            "agent": "native",
            "agent_version": "1.0",
            "settings": {"reasoning_effort": effort},
            "wall_seconds": wall,
            "first_verified_completion_seconds": wall if passed else None,
            "input_tokens": 1_000_000,
            "cached_input_tokens": 500_000,
            "cache_write_input_tokens": 0,
            "output_tokens": 10_000,
            "requests_without_usage": 0,
            "max_request_input_tokens": 100_000,
            "comparison": {
                "protocol": "controlled",
                "budget_seconds": budget,
                "hardware": "fixed-cpu",
                "harness_version": "0.5.3rc2",
                "runner_version": "1.0",
                "prompt_sha256": "b" * 64,
                "continuation_policy": "original-deadline-generic",
            },
        },
    }


def row(reports):
    return summarize(reports)["cohorts"][0]["rows"][0]


def test_failures_count_toward_success_cost_and_time():
    success = trial("1")
    failed = trial("2", passed=False, wall=180)
    value = row([success, failed])
    assert value["trials"] == 2 and value["passes"] == 1
    assert value["api_tokens_usd_per_success"] == pytest.approx(2 * 0.165)
    assert value["seconds_per_success"] == 230
    assert value["median_verified_seconds"] == 50
    assert sum(r["wall_seconds"] for r in value["receipts"]) == value["seconds_per_success"]
    assert sum(r["api_token_cost_usd"] for r in value["receipts"]) == pytest.approx(
        value["api_tokens_usd_per_success"]
    )
    assert value["pass_rate_95_interval"][0] < 0.5 < value["pass_rate_95_interval"][1]
    assert value["pareto"] is None and value["provisional"]


def test_late_numerical_pass_counts_as_failure_not_excluded():
    late = trial("late", wall=190)
    value = row([trial("on-time"), late])
    assert value["trials"] == 2 and value["passes"] == 1
    assert value["deadline_misses"] == 1
    assert value["seconds_per_success"] == 240
    assert normalize(late)["numeric_passed"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("cached_input_tokens", None),
        ("requests_without_usage", None),
        ("requests_without_usage", 1),
        ("output_tokens", None),
    ],
)
def test_partial_usage_is_unknown_even_when_other_trials_are_complete(field, value):
    unknown = trial("unknown")
    unknown["trial"][field] = value
    result = row([trial("known"), unknown])
    assert result["api_tokens_usd_per_success"] is None
    assert result["trials_without_price"] == 1
    assert result["seconds_per_success"] == 50


def test_openai_cache_writes_and_context_tiers_are_required():
    report = trial("sol", model="gpt-6.1-sol")
    report["trial"]["cache_write_input_tokens"] = 100_000
    assert row([report])["api_tokens_usd_per_success"] == pytest.approx(1.2)
    for field, value in [
        ("cache_write_input_tokens", None),
        ("max_request_input_tokens", None),
        ("max_request_input_tokens", 272001),
    ]:
        missing = copy.deepcopy(report)
        missing["trial"][field] = value
        assert row([missing])["api_tokens_usd_per_success"] is None


def test_reasoning_tokens_are_not_billed_twice_and_subscription_spend_stays_separate():
    report = trial("subscription", model="gemini-3.8-flash")
    before = row([report])["api_tokens_usd_per_success"]
    report["trial"]["reasoning_output_tokens"] = 9000
    report["trial"]["reported_cost_usd"] = 0
    result = row([report])
    assert result["api_tokens_usd_per_success"] == before
    assert result["reported_usd_per_success"] == 0
    assert before > 0


def test_task_budget_hardware_prompt_and_effort_are_kept_separate():
    reports = [trial(str(i)) for i in range(6)]
    reports[1]["trial"]["comparison"]["budget_seconds"] = 900
    reports[2]["trial"]["comparison"]["hardware"] = "other-cpu"
    reports[3]["trial"]["comparison"]["prompt_sha256"] = "c" * 64
    reports[4]["task"] = "rz-diagnostics"
    reports[5]["trial"]["settings"]["reasoning_effort"] = "max"
    cohorts = summarize(reports)["cohorts"]
    assert len(cohorts) == 5
    same = next(c for c in cohorts if len(c["rows"]) == 2)
    assert {r["settings"]["reasoning_effort"] for r in same["rows"]} == {"max", "high"}


def test_pareto_requires_repeats_and_preserves_tied_and_unknown_configurations():
    reports = []
    for model in ["deepseek-flash", "grok-4.7", "gpt-6-astra", "unpriced-model"]:
        reports.extend(trial(f"{model}-{i}", model=model) for i in range(5))
    rows = {r["model"]: r for r in summarize(reports)["cohorts"][0]["rows"]}
    assert rows["deepseek-flash"]["pareto"] is True
    assert rows["grok-4.7"]["pareto"] is False
    assert rows["gpt-6-astra"]["pareto"] is False
    assert rows["unpriced-model"]["pareto"] is None
    assert rows["unpriced-model"]["pareto_quality_time"] is True
    tied = [trial(f"same-{i}", effort="max") for i in range(5)]
    assert all(r["pareto"] for r in summarize(reports[:5] + tied)["cohorts"][0]["rows"])


def test_same_trial_is_not_counted_twice_and_conflicting_receipts_are_rejected():
    report = trial("same")
    result = summarize([report, report])
    assert result["duplicates_ignored"] == 1
    assert result["cohorts"][0]["rows"][0]["trials"] == 1
    altered = copy.deepcopy(report)
    altered["trial"]["model"] = "grok-4.7"
    with pytest.raises(ValueError, match="Conflicting"):
        summarize([report, altered])


def test_private_fields_are_excluded_and_exploratory_runs_remain_unranked():
    report = trial("safe")
    report["trial"]["settings"]["api_key"] = "private-key-value"
    report["verified_plot_data"] = {"secret": "private-key-value"}
    report["error"] = "/private/user/workspace"
    cleaned = public_grade(report)
    assert "private" not in json.dumps(cleaned)
    assert normalize(cleaned) == normalize(report)
    assert "private" not in json.dumps(summarize([report]))
    report["trial"]["comparison"]["protocol"] = "exploratory"
    result = summarize([report])
    assert not result["cohorts"] and result["unranked"][0]["passed"]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, 10**400])
def test_invalid_measurements_are_rejected(value):
    report = trial("invalid")
    report["trial"]["wall_seconds"] = value
    with pytest.raises(ValueError, match="measurements"):
        summarize([report])


def test_forged_pass_and_historical_task_are_rejected():
    report = trial("forged")
    report["checks"][0]["passed"] = False
    with pytest.raises(ValueError, match="Inconsistent"):
        summarize([report])
    report["task"] = "previous-live-flash-pilot"
    with pytest.raises(ValueError, match="historical pilot"):
        summarize([report])


def test_published_historical_observations_do_not_populate_ranked_cohorts():
    data = summarize([])
    assert len(data["historical_pilot"]["observations"]) == 6
    assert not data["cohorts"] and not data["unranked"]


def test_import_http_replays_do_not_inflate_trials_and_export_has_no_private_settings(tmp_path):
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            token = client.get("/api/workspace/bootstrap").json()["control_token"]
            headers = {"X-Simjecture-Token": token}
            report = trial("imported")
            report["trial"]["settings"]["api_key"] = "do-not-export"
            for _ in range(2):
                response = client.post(
                    "/api/workspace/import-benchmark-reports",
                    headers=headers,
                    json={"reports": [report]},
                )
                assert response.status_code == 200, response.text
            result = client.get("/api/workspace/benchmarks").json()
            assert result["imported_trials"] == 1
            assert result["leaderboard"]["cohorts"][0]["rows"][0]["trials"] == 1
            assert "do-not-export" not in json.dumps(result)
    finally:
        server.shutdown()
        server.server_close()


def test_gui_grade_uses_actual_turn_identity_and_marks_unaccounted_turns_unknown(tmp_path):
    from conjecture_solver.web.workspace import load, put

    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    workspace = app.workspace
    project = workspace.prepare_benchmark({"task": "csv-energy"})
    directory = workspace.directory(project["id"])
    selected = load(directory / "project.json")
    selected["agent"] = {"backend": "codex", "model": "gpt-6.1-sol"}
    put(directory / "project.json", selected)
    turn = directory / "turns/1000000000"
    turn.mkdir()
    put(
        turn / "request.json",
        {
            "message": "test fixture",
            "created_at": 1,
            "agent": {"backend": "builtin", "model": "deepseek-flash", "reasoning_effort": "high"},
        },
    )
    event = {
        "type": "provider_request",
        "request_id": "fixture",
        "status": "finished",
        "usage": {"input_tokens": 1000, "output_tokens": 10, "cached_input_tokens": 900},
    }
    (turn / "events.jsonl").write_text(json.dumps(event) + "\n")
    report = workspace.grade_benchmark({"project": project["id"]})
    assert report["trial"]["model"] == "deepseek-flash"
    assert report["trial"]["input_tokens"] == 1000
    assert report["trial"]["cached_input_tokens"] == 900
    assert report["trial"]["reasoning_output_tokens"] is None
    missing = directory / "turns/2000000000"
    missing.mkdir()
    put(missing / "request.json", load(turn / "request.json"))
    report = workspace.grade_benchmark({"project": project["id"]})
    assert report["trial"]["input_tokens"] is None
    assert report["trial"]["requests_without_usage"] is None
    other = load(missing / "request.json")
    other["agent"]["model"] = "gpt-6-astra"
    put(missing / "request.json", other)
    assert workspace.grade_benchmark({"project": project["id"]})["trial"]["model"] == "mixed-models"


def test_browser_leaderboard_import_chart_filter_and_export(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#benchmarks")
            playwright.expect(page.locator("#benchmark-leaderboard")).to_contain_text(
                "Build the first comparison"
            )
            page.locator("#benchmark-pricing summary").click()
            playwright.expect(page.locator("#benchmark-price-table")).to_contain_text("gpt-6.1-sol")
            page.locator("#benchmark-history summary").click()
            playwright.expect(page.locator("#benchmark-history-table")).to_contain_text(
                "mimo-v2.6-pro"
            )
            records = [trial(f"deepseek-{i}") for i in range(5)]
            records += [trial(f"grok-{i}", model="grok-4.7") for i in range(5)]
            records += [trial("other", budget=900)]
            page.locator("#benchmark-import-files").set_input_files(
                [
                    {
                        "name": f"{i}.json",
                        "mimeType": "application/json",
                        "buffer": json.dumps(r).encode(),
                    }
                    for i, r in enumerate(records)
                ]
            )
            playwright.expect(page.locator("#benchmark-overview")).to_contain_text("11")
            picker = page.locator("#benchmark-cohort")
            group = next(o for o in picker.locator("option").all() if "180s" in o.inner_text())
            picker.select_option(group.get_attribute("value"))
            playwright.expect(page.locator("#benchmark-leaderboard")).to_contain_text(
                "Pareto frontier"
            )
            assert page.locator("#benchmark-tradeoff svg circle").count() == 2
            page.locator("#benchmark-chart").select_option("cost-time")
            page.locator("#benchmark-tradeoff svg circle").first.click()
            assert page.locator(".benchmark-highlight").count() == 1
            with page.expect_download() as info:
                page.locator("#benchmark-export").click()
            exported = json.loads(__import__("pathlib").Path(info.value.path()).read_text())
            assert len(exported["cohorts"]) == 2
            for theme, width in [("dark", 1440), ("light", 390)]:
                page.evaluate("theme=>document.documentElement.dataset.theme=theme", theme)
                page.set_viewport_size({"width": width, "height": 1100})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
