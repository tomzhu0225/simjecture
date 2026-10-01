"""Curated task leaderboards, separate from local runs and contributed receipts."""

import json
import re
from pathlib import Path

from .leaderboard import PRICES, PRICING_DATE, normalize, summarize

RESULTS = Path(__file__).with_name("results")
EDITION = "owned-2026-10-01"
TASK_DESCRIPTIONS = {
    "rz-diagnostics": {
        "title": "RZ plasma diagnostics",
        "description": (
            "Write a reproducible analysis of two recorded plasma simulations: kinetic "
            "energy, compression, radiation windows, grid differences and plot data."
        ),
        "inputs": "64 × 4 and 128 × 4 RZ grids · 401 HDF5 frames each",
    },
    "csv-energy": {
        "title": "Radiation energy accounting",
        "description": (
            "Write a reducer for two recorded CSV cases. Compare escaped radiation with "
            "the energy removed by the radiation operator, then deliver results and findings."
        ),
        "inputs": "Two solver CSV cases · three independent numerical holdouts",
    },
}


def tariff(model):
    base = re.sub(r"-(low|medium|high)$", "", model) if model.startswith("gemini-") else model
    base = {
        "claude-opus-4-6-thinking": "claude-opus-4-6",
        "gemini-3.1-pro": "gemini-3.1-pro-preview",
    }.get(base, base)
    if base == "gpt-oss-120b-medium":
        return {
            "input": 0.15,
            "cached": 0.075,
            "output": 0.60,
            "source": "https://console.groq.com/docs/model/openai/gpt-oss-120b",
            "basis": "Groq reference tariff for open weights; not AGY subscription billing",
            "reference": True,
        }
    rate = PRICES.get(base)
    return dict(rate) if rate else None


def valuation(entry, rate, *, cached=True):
    """Value recorded counters. Partial receipts remain explicitly lower bounds."""
    if not entry or not rate:
        return None
    usage = entry["usage"]
    inp, out = usage.get("input_tokens"), usage.get("output_tokens")
    if inp is None or out is None:
        return None
    hits, writes = usage.get("cached_input_tokens"), usage.get("cache_write_input_tokens")
    if not cached:
        return (inp * rate["input"] + out * rate["output"]) / 1_000_000
    if hits is None or writes is None or hits + writes > inp:
        return None
    return (
        (inp - hits - writes) * rate["input"]
        + hits * rate["cached"]
        + writes * rate.get("write", rate["input"])
        + out * rate["output"]
    ) / 1_000_000


def rank(rows, metric, *, reverse=False):
    eligible = [r for r in rows if r.get(metric) is not None]
    eligible.sort(key=lambda r: r[metric], reverse=reverse)
    previous, place = None, None
    for index, row in enumerate(eligible, 1):
        if row[metric] != previous:
            place = index
        row["ranks"][metric] = place
        previous = row[metric]


def dashboard(bundle=None, ledger=None):
    """Only this publication's current task contracts populate official rankings."""
    if bundle is None:
        path = RESULTS / f"{EDITION}.json"
        if not path.exists():
            return None
        bundle = json.loads(path.read_text())
    if ledger is None:
        path = RESULTS / f"{EDITION}-valuation.json"
        ledger = json.loads(path.read_text()) if path.exists() else {"entries": []}
    entries = {e["trial_id"]: e for e in ledger["entries"]}
    pack = max(bundle["pack_versions"], key=lambda v: tuple(int(x) for x in v.split(".")))
    reports = [r for r in bundle["reports"] if r["pack_version"] == pack]
    summary = summarize(reports)
    tasks = []
    for task, description in TASK_DESCRIPTIONS.items():
        cohorts = [c for c in summary["cohorts"] if c["scope"]["task"] == task]
        if len(cohorts) > 1:
            raise ValueError("An official edition must have one fixed protocol per task")
        cohort = cohorts[0] if cohorts else None
        rows = []
        for config in bundle["configurations"]:
            selected = [
                r
                for r in reports
                if r["task"] == task
                and r["trial"]["agent"] == config["backend"]
                and r["trial"]["model"] == config["model"]
                and r["trial"]["settings"]["reasoning_effort"] == config["effort"]
            ]
            observed = [r for r in selected if not r["trial"].get("invalidated_reason")]
            aggregate = next(
                (
                    r
                    for r in (cohort or {}).get("rows", [])
                    if r["agent"] == config["backend"]
                    and r["model"] == config["model"]
                    and r["settings"]["reasoning_effort"] == config["effort"]
                ),
                None,
            )
            rate = tariff(config["model"])
            receipts = []
            costs, uncached_costs, coverages = [], [], []
            for report in observed:
                entry = entries.get(report["trial"]["trial_id"])
                if entry and entry["source_report_sha256"] != report["source_report_sha256"]:
                    raise ValueError("Valuation source does not match its host report")
                cost, uncached = valuation(entry, rate), valuation(entry, rate, cached=False)
                costs.append(cost)
                uncached_costs.append(uncached)
                coverage = entry["coverage"] if entry else "missing"
                coverages.append(coverage)
                record = normalize(report)
                receipts.append(
                    {
                        "passed": record["passed"],
                        "numeric_passed": record["numeric_passed"],
                        "findings_present": record["findings_present"],
                        "provider_interruption": record["trial"]["provider_interruption"],
                        "wall_seconds": record["trial"]["wall_seconds"],
                        "usage": entry["usage"] if entry else record["trial"],
                        "cost_usd": cost,
                        "uncached_cost_usd": uncached,
                        "coverage": coverage,
                        "source_report_sha256": report["source_report_sha256"],
                    }
                )
            coverage = (
                "no-inference"
                if not observed
                else "unpriced"
                if not rate
                else "missing"
                if "missing" in coverages
                else "partial"
                if "partial" in coverages
                else "estimated"
                if "agy-estimate" in coverages
                else "complete"
            )

            def mean(values):
                return (
                    sum(values) / len(values)
                    if values and all(v is not None for v in values)
                    else None
                )

            base = (
                re.sub(r"-(low|medium|high)$", "", config["model"])
                if config["backend"] == "agy" and config["model"].startswith("gemini-")
                else config["model"]
            )
            row = dict(aggregate or {}) | {
                "id": config["id"],
                "model": config["model"],
                "agent": config["backend"],
                "effort": config["effort"],
                "family": f"{config['backend']}/{base}",
                "family_label": base,
                "tariff": rate,
                "cost_coverage": coverage,
                "cost_per_attempt": mean(costs),
                "uncached_cost_per_attempt": mean(uncached_costs),
                "unavailable_attempts": len(selected) - len(observed),
                "availability_reasons": sorted(
                    {
                        r["trial"]["invalidated_reason"]
                        for r in selected
                        if r["trial"].get("invalidated_reason")
                    }
                ),
                "trials": len(observed),
                "passes": sum(normalize(r)["passed"] for r in observed),
                "numeric_passes": sum(all(c["passed"] for c in r["checks"]) for r in observed),
                "receipts": receipts,
                "ranks": {},
            }
            row.setdefault("pass_rate", None)
            row.setdefault("median_verified_seconds", None)
            row.setdefault("mean_trial_seconds", None)
            row["ranked_cost_per_attempt"] = (
                row["cost_per_attempt"]
                if row["passes"] and coverage in {"complete", "estimated"}
                else None
            )
            row["ranked_uncached_cost_per_attempt"] = (
                row["uncached_cost_per_attempt"]
                if row["passes"] and coverage in {"complete", "estimated"}
                else None
            )
            rows.append(row)
        rank(rows, "pass_rate", reverse=True)
        rank(rows, "median_verified_seconds")
        rank(rows, "ranked_cost_per_attempt")
        rank(rows, "ranked_uncached_cost_per_attempt")
        tasks.append(
            description
            | {
                "id": task,
                "budget_seconds": 900 if task == "rz-diagnostics" else 180,
                "repeats": bundle["task_repeats"][task],
                "rows": rows,
                "cohort": cohort["scope"] if cohort else None,
            }
        )
    return {
        "edition": EDITION,
        "date": "2026-10-01",
        "pack_version": pack,
        "status": bundle["status"],
        "configurations": len(bundle["configurations"]),
        "attempts": bundle["completed_formal_trials"],
        "unavailable_attempts": bundle["unavailable_formal_trials"],
        "pricing_date": PRICING_DATE,
        "tasks": tasks,
        "valuation_policy": ledger.get("policy", []),
        "report_url": "https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/docs/testing/owned-llm-benchmark-20261001.md",
    }


def export_page(output):
    """Write a self-contained read-only publication, requiring no GUI or model calls."""
    static = Path(__file__).parent.parent / "web" / "static"
    workspace = (static / "workspace.html").read_text()
    start = workspace.index('        <section id="view-benchmarks"')
    end = workspace.index('        <section id="view-tools"', start)
    section = workspace[start:end].replace(
        'class="view benchmark-view" hidden', 'class="view benchmark-view"'
    )
    section = section.replace(
        '<div class="benchmark-actions">',
        '<div class="benchmark-actions"><a class="benchmark-submit-link" '
        'href="https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/'
        'src/conjecture_solver/llm_bench/results/community/README.md" '
        'target="_blank" rel="noopener noreferrer">Contribute a model</a>',
        1,
    )
    css = (static / "workspace.css").read_text()
    script = (static / "workspace-benchmarks.js").read_text()
    publication = dashboard()
    if publication is None:
        raise ValueError("No published result edition is installed")
    from .leaderboard import summarize

    pack = {
        "official": publication,
        "published_trials": publication["attempts"],
        "community_trials": 0,
        "campaigns": [],
        "tasks": [],
        "grade_reports": [],
        "leaderboard": summarize([]),
    }
    encoded = json.dumps(pack).replace("<", "\\u003c")
    html = (
        '<!doctype html><html lang="en" data-theme="light"><head>'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Simjecture · Official model leaderboard</title><style>"
        + css
        + "body{display:block;padding:0}.publication-main .benchmark-view{padding:0}"
        ".publication-main{max-width:1480px;margin:auto;padding:32px}"
        + "@media(max-width:650px){.publication-main{padding:18px}}"
        + '</style></head><body><main class="publication-main">'
        + section
        + "</main><script>"
        + script
        + "</script><script>"
        + "WorkspaceBenchmarks.render("
        + encoded
        + ',{readonly:true,api:async()=>{throw Error("Use the workspace to run a model.")},'
        "refresh:async()=>{},toast:()=>{}});"
        + 'for(const id of ["benchmark-run","benchmark-your-work"'
        '])document.getElementById(id).hidden=true;'
        + 'document.getElementById("benchmark-source").parentElement.hidden=true;'
        + "</script></body></html>"
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    return {
        "output": str(output),
        "edition": publication["edition"],
        "attempts": publication["attempts"],
    }
