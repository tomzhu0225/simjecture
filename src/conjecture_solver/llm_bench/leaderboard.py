"""Task-scoped comparisons; unknown measurements never become free successes."""

import hashlib
import json
import math
import re
import statistics
from collections import defaultdict

PRICING_DATE = "2026-10-01"
PRICES = {
    "gpt-6.1-sol": {
        "input": 2.0,
        "cached": 0.10,
        "write": 2.50,
        "output": 10.0,
        "max_input": 272000,
        "source": "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
    },
    "gpt-6-astra": {
        "input": 10.0,
        "cached": 1.0,
        "write": 12.50,
        "output": 50.0,
        "max_input": 272000,
        "source": "https://developers.openai.com/api/docs/models/gpt-6-astra",
    },
    "grok-4.7": {
        "input": 2.0,
        "cached": 0.50,
        "output": 6.0,
        "max_input": 200000,
        "source": "https://docs.x.ai/developers/models/grok-4.7",
    },
    "gemini-3.8-flash": {
        "input": 0.75,
        "cached": 0.075,
        "output": 3.75,
        "source": "https://ai.google.dev/gemini-api/docs/pricing",
    },
    "deepseek-flash": {
        "input": 0.30,
        "cached": 0.006,
        "output": 1.20,
        "source": "https://api-docs.deepseek.com/quick_start/pricing/",
    },
    "deepseek-v4-pro": {
        "input": 1.32,
        "cached": 0.044,
        "output": 3.96,
        "source": "https://api-docs.deepseek.com/quick_start/pricing/",
    },
}
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "reasoning_output_tokens",
    "requests_without_usage",
    "max_request_input_tokens",
)
COHORT_FIELDS = (
    "protocol",
    "budget_seconds",
    "hardware",
    "harness_version",
    "runner_version",
    "prompt_sha256",
    "continuation_policy",
)
HISTORICAL_PILOT = {
    "date": "2026-09-30",
    "source": (
        "https://github.com/tomzhu0225/simjecture/blob/main/docs/testing/mimo-flash-comparison.md"
    ),
    "note": (
        "One trial per model and task, under a different live-simulation contract. "
        "Pro's account/isolation and sequential timing differed. Verification includes "
        "solver work and operator observation. These observations are not leaderboard "
        "repetitions or pure inference latency; token counters are not invoices."
    ),
    "observations": [
        {
            "task": "Live FLASH / 900s",
            "model": "mimo-v2.6-flash",
            "delivered": False,
            "verified_seconds": None,
            "input_tokens": 878201,
            "output_tokens": 11175,
        },
        {
            "task": "Live FLASH / 900s",
            "model": "mimo-v2.6-pro",
            "delivered": True,
            "verified_seconds": 790.85,
            "input_tokens": 1710612,
            "output_tokens": 24417,
        },
        {
            "task": "Live FLASH / 900s",
            "model": "deepseek-flash",
            "delivered": True,
            "verified_seconds": 400.45,
            "input_tokens": 2692318,
            "output_tokens": 29422,
        },
        {
            "task": "CSV control / 180s",
            "model": "mimo-v2.6-flash",
            "delivered": True,
            "verified_seconds": 114.35,
            "input_tokens": 164603,
            "output_tokens": 2954,
        },
        {
            "task": "CSV control / 180s",
            "model": "mimo-v2.6-pro",
            "delivered": True,
            "verified_seconds": 151.13,
            "input_tokens": 340400,
            "output_tokens": 7126,
        },
        {
            "task": "CSV control / 180s",
            "model": "deepseek-flash",
            "delivered": True,
            "verified_seconds": 113.69,
            "input_tokens": 2561585,
            "output_tokens": 12436,
        },
    ],
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def label(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[\w .:/+()@-]{1,160}", value):
        raise ValueError("Benchmark identity fields must be short plain labels")
    return value


def measurement(value, *, integer=False):
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value > 1e15
        or not math.isfinite(value)
        or value < 0
        or (integer and not isinstance(value, int))
    ):
        raise ValueError("Benchmark measurements must be finite nonnegative numbers")
    return value


def normalize(report):
    """Allowlist public fields, independently check a grade and retain its digest."""
    from .pack import TASKS

    if not isinstance(report, dict) or report.get("task") not in TASKS:
        raise ValueError("Expected a Simjecture Bench grade, not a historical pilot")
    if report.get("schema_version") != "0.1.0" or not label(report.get("pack_version")):
        raise ValueError("Unsupported benchmark grade schema")
    if not isinstance(report.get("passed"), bool):
        raise ValueError("Grade needs a boolean passed result")
    checks = report.get("checks")
    if (
        not isinstance(checks, list)
        or not checks
        or any(not isinstance(c, dict) or not isinstance(c.get("passed"), bool) for c in checks)
    ):
        raise ValueError("Grade needs independent numerical checks")
    if report["passed"] and (
        not all(c["passed"] for c in checks)
        or report.get("intact_inputs") is not True
        or report.get("findings_present") is not True
        or report.get("scientific_claim_approved") is not False
    ):
        raise ValueError("Inconsistent passing benchmark grade")
    raw = report.get("trial") or {}
    if not isinstance(raw, dict):
        raise ValueError("Expected trial metadata object")
    comparison = raw.get("comparison") or {}
    if not isinstance(comparison, dict):
        raise ValueError("Expected comparison metadata object")
    protocol = comparison.get("protocol") or "exploratory"
    if protocol not in {"exploratory", "controlled"}:
        raise ValueError("Unknown comparison protocol")
    cohort = {key: label(comparison.get(key)) for key in COHORT_FIELDS if key != "budget_seconds"}
    cohort["protocol"] = protocol
    cohort["budget_seconds"] = measurement(comparison.get("budget_seconds"))
    for key in ("prompt_sha256",):
        if cohort[key] is not None and not re.fullmatch("[a-f0-9]{64}", cohort[key]):
            raise ValueError("Expected a SHA256 comparison fingerprint")
    settings = raw.get("settings") or {}
    if not isinstance(settings, dict):
        raise ValueError("Expected agent settings object")
    # Unknown settings can hold credentials. Never return them to a public export.
    configuration = {
        key: label(settings.get(key))
        for key in ("reasoning_effort", "service_tier", "tool_profile")
    }
    trial = {
        "model": label(raw.get("model")),
        "agent": label(raw.get("agent")),
        "agent_version": label(raw.get("agent_version")),
        "model_version": label(raw.get("model_version")),
        "settings": configuration,
        "comparison": cohort,
        **{key: measurement(raw.get(key), integer=True) for key in TOKEN_FIELDS},
        **{
            key: measurement(raw.get(key))
            for key in (
                "wall_seconds",
                "first_verified_completion_seconds",
                "reported_cost_usd",
            )
        },
    }
    for key in ("cached_input_tokens", "cache_write_input_tokens"):
        if (
            trial[key] is not None
            and trial["input_tokens"] is not None
            and trial[key] > trial["input_tokens"]
        ):
            raise ValueError("Cache counters exceed total input tokens")
    if (
        all(
            trial[k] is not None
            for k in (
                "input_tokens",
                "cached_input_tokens",
                "cache_write_input_tokens",
            )
        )
        and trial["cached_input_tokens"] + trial["cache_write_input_tokens"] > trial["input_tokens"]
    ):
        raise ValueError("Overlapping cache counters exceed total input tokens")
    contract = report.get("task_contract_sha256")
    if contract is not None and not re.fullmatch("[a-f0-9]{64}", str(contract)):
        raise ValueError("Expected a task contract SHA256")
    identity = label(raw.get("trial_id"))
    source = report.get("source_report_sha256")
    if source is not None and not re.fullmatch("[a-f0-9]{64}", str(source)):
        raise ValueError("Expected a source report SHA256")
    # Old, unidentified reports are inspection only: regrading is not a fresh trial.
    issues = []
    if not identity:
        issues.append("Missing stable trial ID")
    if not trial["model"] or not trial["agent"] or not trial["agent_version"]:
        issues.append("Incomplete model/agent/version identity")
    if not report.get("execution_backend"):
        issues.append("Unknown execution environment")
    if protocol != "controlled":
        issues.append("Interactive/exploratory protocol")
    if not contract or any(cohort[key] is None for key in COHORT_FIELDS):
        issues.append("Incomplete comparison cohort")
    wall, verified, budget = (
        trial["wall_seconds"],
        trial["first_verified_completion_seconds"],
        cohort["budget_seconds"],
    )
    if wall is None:
        issues.append("Unknown trial elapsed time")
    if budget is not None and budget <= 0:
        issues.append("Invalid time budget")
    if report["passed"] and (verified is None or budget is None):
        issues.append("No verified completion within the declared deadline")
    if verified is not None and wall is not None and verified > wall:
        issues.append("Verification time exceeds trial elapsed time")
    missed = bool(report["passed"] and verified is not None and budget and verified > budget)
    return {
        "task": report["task"],
        "pack_version": report["pack_version"],
        "execution_backend": label(report.get("execution_backend")),
        "task_contract_sha256": contract,
        "passed": report["passed"] and not missed,
        "numeric_passed": report["passed"],
        "deadline_missed": missed,
        "trial": trial,
        "trial_key": fingerprint([report["pack_version"], report["task"], identity])
        if identity
        else None,
        "report_sha256": source or fingerprint(report),
        "issues": issues,
    }


def public_grade(report):
    """An import can retain its source hash without copying paths or private text."""
    value = normalize(report)
    return {
        key: report[key]
        for key in (
            "schema_version",
            "pack_version",
            "task",
            "passed",
        )
    } | {
        "execution_backend": report.get("execution_backend"),
        "intact_inputs": report.get("intact_inputs"),
        "findings_present": report.get("findings_present"),
        "scientific_claim_approved": report.get("scientific_claim_approved"),
        "checks": [{"passed": check["passed"]} for check in report["checks"]],
        "trial": value["trial"] | {"trial_id": (report.get("trial") or {}).get("trial_id")},
        "task_contract_sha256": value["task_contract_sha256"],
        "source_report_sha256": value["report_sha256"],
    }


def token_cost(trial):
    """A dated standard/short-context API equivalent, never a subscription invoice."""
    rate = PRICES.get(trial["model"])
    required = ("input_tokens", "output_tokens", "cached_input_tokens")
    if not rate or any(trial[k] is None for k in required) or trial["requests_without_usage"] != 0:
        return None
    if "max_input" in rate:
        maximum = trial["max_request_input_tokens"]
        if maximum is None or maximum > rate["max_input"]:
            return None
    writes = trial.get("cache_write_input_tokens")
    if "write" in rate and writes is None:
        return None
    writes = writes or 0
    uncached = trial["input_tokens"] - trial["cached_input_tokens"] - writes
    return (
        uncached * rate["input"]
        + trial["cached_input_tokens"] * rate["cached"]
        + writes * rate.get("write", rate["input"])
        + trial["output_tokens"] * rate["output"]
    ) / 1_000_000


def wilson(passes, trials):
    z = 1.959963984540054
    p = passes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    radius = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return [max(0, centre - radius), min(1, centre + radius)]


def summarize(reports, *, minimum_trials=5):
    """Separate protocols/tasks/hardware; use all attempts in success costs."""
    if (
        not isinstance(minimum_trials, int)
        or isinstance(minimum_trials, bool)
        or minimum_trials < 2
    ):
        raise ValueError("At least two trials are required for Pareto eligibility")
    normalized = [normalize(report) for report in reports]
    unique, unidentified, duplicates = {}, [], 0
    for record in normalized:
        if not record["trial_key"]:
            unidentified.append(record)
            continue
        key = record["trial_key"]
        if key in unique:
            if unique[key] != record:
                raise ValueError("Conflicting grades for one trial; keep its final host grade")
            duplicates += 1
        unique[key] = record
    cohorts, pending = defaultdict(list), []
    for record in [*unique.values(), *unidentified]:
        if record["issues"]:
            pending.append(
                {
                    "task": record["task"],
                    "model": record["trial"]["model"],
                    "agent": record["trial"]["agent"],
                    "passed": record["passed"],
                    "issues": record["issues"],
                    "report_sha256": record["report_sha256"],
                }
            )
            continue
        scope = {
            key: record[key]
            for key in (
                "task",
                "pack_version",
                "execution_backend",
                "task_contract_sha256",
            )
        } | record["trial"]["comparison"]
        cohorts[json.dumps(scope, sort_keys=True)].append(record)
    result = []
    for encoded, records in sorted(cohorts.items()):
        configurations = defaultdict(list)
        for record in records:
            trial = record["trial"]
            config = {
                key: trial[key]
                for key in (
                    "model",
                    "model_version",
                    "agent",
                    "agent_version",
                    "settings",
                )
            }
            configurations[json.dumps(config, sort_keys=True)].append(record)
        rows = []
        for config, trials in sorted(configurations.items()):
            passes = sum(t["passed"] for t in trials)
            costs = [token_cost(t["trial"]) for t in trials]
            reported = [t["trial"]["reported_cost_usd"] for t in trials]
            wall = sum(t["trial"]["wall_seconds"] for t in trials)
            times = [t["trial"]["first_verified_completion_seconds"] for t in trials if t["passed"]]
            rows.append(
                json.loads(config)
                | {
                    "trials": len(trials),
                    "passes": passes,
                    "pass_rate": passes / len(trials),
                    "pass_rate_95_interval": wilson(passes, len(trials)),
                    "median_verified_seconds": statistics.median(times) if times else None,
                    "seconds_per_success": wall / passes if passes else None,
                    "mean_trial_seconds": wall / len(trials),
                    "api_tokens_usd_per_success": sum(costs) / passes
                    if passes and all(c is not None for c in costs)
                    else None,
                    "reported_usd_per_success": sum(reported) / passes
                    if passes and all(c is not None for c in reported)
                    else None,
                    "trials_without_price": sum(c is None for c in costs),
                    "provisional": len(trials) < minimum_trials,
                    "deadline_misses": sum(t["deadline_missed"] for t in trials),
                    "pareto": None,
                    "pareto_quality_time": None,
                    "receipts": [
                        {
                            "source_report_sha256": item["report_sha256"],
                            "passed": item["passed"],
                            "numeric_passed": item["numeric_passed"],
                            "deadline_missed": item["deadline_missed"],
                            "wall_seconds": item["trial"]["wall_seconds"],
                            "first_verified_completion_seconds": item["trial"][
                                "first_verified_completion_seconds"
                            ],
                            "usage": {key: item["trial"][key] for key in TOKEN_FIELDS},
                            "api_token_cost_usd": cost,
                            "reported_cost_usd": item["trial"]["reported_cost_usd"],
                        }
                        for item, cost in zip(trials, costs, strict=True)
                    ],
                }
            )
        eligible = [
            r for r in rows if not r["provisional"] and r["api_tokens_usd_per_success"] is not None
        ]
        for row in eligible:

            def dominates(other, target=row):
                a = (
                    -other["pass_rate"],
                    other["api_tokens_usd_per_success"],
                    other["seconds_per_success"],
                )
                b = (
                    -target["pass_rate"],
                    target["api_tokens_usd_per_success"],
                    target["seconds_per_success"],
                )
                return all(x <= y for x, y in zip(a, b, strict=True)) and any(
                    x < y for x, y in zip(a, b, strict=True)
                )

            row["pareto"] = not any(dominates(other) for other in eligible)
        timed = [r for r in rows if not r["provisional"] and r["passes"]]
        for row in timed:
            row["pareto_quality_time"] = not any(
                other["pass_rate"] >= row["pass_rate"]
                and other["mean_trial_seconds"] <= row["mean_trial_seconds"]
                and (
                    other["pass_rate"] > row["pass_rate"]
                    or other["mean_trial_seconds"] < row["mean_trial_seconds"]
                )
                for other in timed
            )
        rows.sort(
            key=lambda r: (-r["pass_rate"], r["model"], r["agent"], json.dumps(r["settings"]))
        )
        result.append(
            {"id": fingerprint(json.loads(encoded)), "scope": json.loads(encoded), "rows": rows}
        )
    return {
        "schema_version": "0.1.0",
        "minimum_trials": minimum_trials,
        "pricing": {"checked_date": PRICING_DATE, "currency": "USD", "per_million_tokens": PRICES},
        "cost_note": (
            "Standard short-context API token equivalent; DeepSeek peak and Gemini introductory "
            "rates. Excludes hosted tools, cache storage, discounts, subscriptions and hardware. "
            "Missing usage stays unknown. Reported costs are operator supplied."
        ),
        "comparison_note": (
            "Controlled protocol is runner/operator declared, not independently certified. "
            "Wilson intervals describe observed pass counts; Pareto membership is descriptive, "
            "not significance. No overall cross-task rank."
        ),
        "cohorts": result,
        "unranked": pending,
        "duplicates_ignored": duplicates,
        "historical_pilot": HISTORICAL_PILOT,
    }
