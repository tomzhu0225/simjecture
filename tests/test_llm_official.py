"""Publication isolation and independently interpretable time/cost rankings."""

import copy

import pytest

from conjecture_solver.llm_bench.official import dashboard, export_page, tariff, valuation


def test_official_edition_has_two_tasks_not_qualification_versions():
    result = dashboard()
    assert result["attempts"] == 252
    assert [task["id"] for task in result["tasks"]] == ["rz-diagnostics", "csv-energy"]
    assert all(task["cohort"]["pack_version"] == "0.3.0" for task in result["tasks"])
    assert all(len(task["rows"]) == 42 for task in result["tasks"])
    assert sum(r["passes"] for r in result["tasks"][0]["rows"]) == 34
    assert sum(r["passes"] for r in result["tasks"][1]["rows"]) == 100


def test_unit_tariff_and_attempt_cost_are_separate_with_no_success():
    csv = dashboard()["tasks"][1]
    row = next(r for r in csv["rows"] if r["model"] == "mimo-v2.6-flash")
    assert row["passes"] == 0
    assert row["tariff"]["input"] > 0 and row["tariff"]["output"] > 0
    assert row["cost_per_attempt"] > 0
    assert row["cost_coverage"] == "partial"
    assert "ranked_cost_per_attempt" not in row["ranks"]


def test_time_ranking_requires_verified_completion_and_cost_bounds_are_not_ranks():
    for task in dashboard()["tasks"]:
        timed = [r for r in task["rows"] if "median_verified_seconds" in r["ranks"]]
        ordered = sorted(timed, key=lambda r: r["median_verified_seconds"])
        assert ordered[0]["ranks"]["median_verified_seconds"] == 1
        assert all(r["passes"] for r in timed)
        assert all(r["passes"] for r in task["rows"] if "ranked_cost_per_attempt" in r["ranks"])
        assert all(
            "ranked_cost_per_attempt" not in r["ranks"]
            for r in task["rows"]
            if r["cost_coverage"] == "partial"
        )


def test_agy_estimates_are_labelled_and_effort_tariffs_match():
    result = dashboard()["tasks"][0]
    variants = [r for r in result["rows"] if r["family"] == "agy/gemini-3.8-flash"]
    assert {r["effort"] for r in variants} == {"low", "medium", "high"}
    assert all(r["cost_per_attempt"] > 0 and r["cost_coverage"] == "estimated" for r in variants)
    assert tariff("gemini-3.8-flash-low") == tariff("gemini-3.8-flash-high")
    assert tariff("gpt-oss-120b-medium")["reference"]
    assert tariff("gpt-reserve") is None


def test_cache_math_and_reasoning_are_not_double_counted():
    usage = {
        "input_tokens": 1000,
        "cached_input_tokens": 900,
        "cache_write_input_tokens": 0,
        "output_tokens": 100,
        "reasoning_output_tokens": 80,
    }
    entry = {"usage": usage}
    rate = {"input": 2, "cached": 0.2, "output": 10}
    assert valuation(entry, rate) == pytest.approx(0.00138)
    assert valuation(entry, rate, cached=False) == pytest.approx(0.003)
    altered = copy.deepcopy(entry)
    altered["usage"]["reasoning_output_tokens"] = 0
    assert valuation(altered, rate) == valuation(entry, rate)


def test_standalone_publication_ranks_and_effort_connections(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    path = tmp_path / "leaderboard.html"
    assert export_page(path)["attempts"] == 252
    errors = []
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1100})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(path.as_uri())
        playwright.expect(page.locator("#benchmark-task-tabs button")).to_have_count(2)
        assert page.locator(".benchmark-effort-line").count() == 6
        for kind in ("time", "cost"):
            bars = page.locator(f"#benchmark-{kind}-bars .benchmark-bar-row")
            assert bars.count() == 42
            data = bars.evaluate_all("""els => els.map(e => ({
                value:e.dataset.value, finished:e.dataset.finished, rank:e.dataset.rank,
                width:e.querySelector('.benchmark-bar-fill').getBoundingClientRect().width,
                height:e.querySelector('.benchmark-bar-fill').getBoundingClientRect().height
            }))""")
            ranked = [float(d["value"]) for d in data if d["rank"]]
            assert ranked == sorted(ranked)
            unfinished = [d for d in data if d["finished"] == "false"]
            assert unfinished
            assert all(
                d["value"] == "0" and d["width"] == 0 and d["height"] == 0 for d in unfinished
            )
        dots = page.locator(".benchmark-official-dot").evaluate_all("""els => els.map(e => ({
            cost:Number(e.dataset.cost), time:Number(e.dataset.time),
            x:Number(e.getAttribute('cx')), y:Number(e.getAttribute('cy'))
        }))""")
        for a in dots:
            for b in dots:
                if a["cost"] < b["cost"]:
                    assert a["x"] < b["x"]
                if a["time"] < b["time"]:
                    assert a["y"] < b["y"]
        assert page.locator(".benchmark-official-dot.pareto").count() == 2
        assert page.locator(".benchmark-pareto-front").count() == 1
        first = page.locator("#benchmark-leaderboard > div > table > tbody > tr").first
        playwright.expect(first).to_contain_text("DeepSeek Flash")
        page.locator("#benchmark-sort").select_option("cost")
        playwright.expect(first).to_contain_text("GPT-6 Luna")
        page.locator("#benchmark-search").fill("gpt 6.1")
        assert page.locator(".benchmark-effort-line").count() == 1
        assert page.locator("#benchmark-leaderboard > div > table > tbody > tr").count() == 6
        assert page.locator("#benchmark-your-work").is_hidden()
        assert page.locator(".benchmark-submit-link").is_visible()
        page.set_viewport_size({"width": 390, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors
        browser.close()
