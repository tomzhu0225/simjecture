"""Paid, operator-requested native-agent trials. Private traces stay here."""

import concurrent.futures
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from conjecture_solver.llm_bench.leaderboard import public_grade, summarize
from conjecture_solver.llm_bench.pack import TASKS, grade, prepare
from conjecture_solver.provider_usage import request_accounting
from conjecture_solver.worker_protocol import private_put

VERSION = "native-public-feedback-v4"


@dataclass
class Campaign:
    root: Path
    work: Path
    numerical_python: Path
    workspace: Path | None
    workers: int
    harness_version: str

    @property
    def hardware(self):
        metadata = {
            "machine": platform.machine(),
            "cpus": os.cpu_count(),
            "workers": self.workers,
            "numeric_versions": {
                k: importlib.metadata.version(k) for k in ["numpy", "h5py", "matplotlib"]
            },
        }
        return (
            "linux-"
            + hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()[:12]
        )


def read_events(path):
    result = []
    if not path.exists():
        return result
    for line in path.read_text(errors="replace").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            result.append(value)
    return result


def native_usage(backend, turns):
    """Use provider receipts; retain known partial counters without pricing them."""
    fields = (
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "reasoning_output_tokens",
    )
    total = {key: None for key in fields}
    cursor, maximum = None, None
    complete, delegation = True, False
    counts = []
    agy_latest = None
    for directory in turns:
        events = read_events(directory / "events.jsonl")
        if backend in {"codex", "codex-glm"}:
            for event in events:
                if event.get("type") == "thread.started":
                    cursor = event.get("thread_id")
                if event.get("type") == "turn.completed" and event.get("usage"):
                    counts.append(event["usage"])
                kind = event.get("item", {}).get("type", "")
                delegation |= "collab" in kind or "agent_tool" in kind
            complete &= any(e.get("type") == "turn.completed" for e in events)
        elif backend == "builtin":
            account = request_accounting(directory / "events.jsonl")
            if account:
                counts.append(dict(account))
                complete &= account.get("requests_without_usage") == 0
                if not account.get("cache_usage_complete"):
                    counts[-1]["cached_input_tokens"] = None
                if not account.get("reasoning_usage_complete"):
                    counts[-1]["reasoning_output_tokens"] = None
            else:
                complete = False
            sizes = [
                e.get("usage", {}).get("input_tokens")
                for e in events
                if e.get("type") == "provider_request" and isinstance(e.get("usage"), dict)
            ]
            sizes = [value for value in sizes if isinstance(value, int)]
            if sizes:
                maximum = max([maximum or 0, *sizes])
        elif backend == "grok":
            messages = {}
            for index, event in enumerate(events):
                cursor = event.get("session_id") or cursor
                message = event.get("message", {})
                usage = message.get("usage") if isinstance(message, dict) else None
                if event.get("type") == "assistant" and isinstance(usage, dict):
                    messages[message.get("id", index)] = usage
            for usage in messages.values():
                cached, writes = (
                    usage.get("cache_read_input_tokens"),
                    usage.get("cache_creation_input_tokens"),
                )
                inputs = usage.get("input_tokens")
                combined = (
                    inputs + cached + writes
                    if all(isinstance(v, int) for v in (inputs, cached, writes))
                    else None
                )
                counts.append(
                    {
                        "input_tokens": combined,
                        "output_tokens": usage.get("output_tokens"),
                        "cached_input_tokens": cached,
                        "cache_write_input_tokens": writes,
                        "reasoning_output_tokens": None,
                    }
                )
                if combined is not None:
                    maximum = max(maximum or 0, combined)
            complete &= any(e.get("type") == "result" for e in events)
            # A resumed transcript can replay messages; do not assert complete accounting.
            complete &= len(turns) == 1
        elif backend == "agy":
            for event in events:
                if event.get("event") == "result":
                    result = event.get("result", {})
                    cursor = result.get("conversation_id") or cursor
                    if isinstance(result.get("usage"), dict):
                        usage = result["usage"]
                        # A quota-error result can reset every counter to zero.
                        # Keep the preceding cumulative receipt, not that reset.
                        if agy_latest is None or any(
                            isinstance(usage.get(k), int) and usage[k] > 0
                            for k in ("input_tokens", "output_tokens", "cache_read_tokens")
                        ):
                            agy_latest = usage
            # AGY uses cumulative conversation totals. Cache semantics are undocumented.
            complete = False
    if backend in {"codex", "codex-glm"} and cursor:
        logs = list((Path.home() / ".codex/sessions").glob("**/*" + cursor + "*.jsonl"))
        rolling, sizes = [], []
        for log in logs:
            for event in read_events(log):
                info = event.get("payload", {}).get("info")
                if isinstance(info, dict):
                    if isinstance(info.get("total_token_usage"), dict):
                        rolling.append(info["total_token_usage"])
                    last = info.get("last_token_usage") or {}
                    if isinstance(last.get("input_tokens"), int):
                        sizes.append(last["input_tokens"])
        if rolling:
            counts = [rolling[-1]]
        elif len(turns) > 1:
            counts = counts[-1:]  # Native turn totals are cumulative for this thread.
            complete = False
        if sizes:
            maximum = max(sizes)
    if counts:
        for key in fields:
            if all(isinstance(value.get(key), int) and value[key] >= 0 for value in counts):
                total[key] = sum(value[key] for value in counts)
    if agy_latest:
        total.update(
            output_tokens=agy_latest.get("output_tokens"),
            cached_input_tokens=agy_latest.get("cache_read_tokens"),
            reasoning_output_tokens=agy_latest.get("thinking_tokens"),
        )
    return total | {
        "requests_without_usage": 0 if complete and not delegation else 1,
        "max_request_input_tokens": maximum,
    }, cursor


def availability_error(directory):
    """Inspect provider error channels, never an assistant's research prose."""
    messages = []
    for event in read_events(directory / "events.jsonl"):
        if event.get("type") in {"error", "turn.failed", "provider_error"}:
            error = event.get("error", event.get("message", ""))
            messages.append(json.dumps(error, ensure_ascii=False))
    stderr = directory / "stderr.log"
    if stderr.exists():
        for line in stderr.read_text(errors="replace").splitlines():
            if line.startswith("AGY_ERROR:"):
                try:
                    error = json.loads(line.partition(":")[2])
                except ValueError:
                    continue
                if isinstance(error, dict):
                    if (
                        error.get("status") == "RESOURCE_EXHAUSTED"
                        or error.get("error_code") == 429
                    ) and re.search(
                        r"quota.*(?:reached|exhausted|exceeded)|insufficient.balance|usage.limit",
                        json.dumps(error),
                        re.I,
                    ):
                        return "Provider quota exhausted"
                    messages.append(json.dumps(error, ensure_ascii=False))
            elif not line.lstrip().startswith(("{", "[")):
                # Native authentication failures may precede JSON streaming.
                messages.append(line)
    diagnostic = "\n".join(messages)
    if re.search(r"套餐已到期|coding.plan.*expired|subscription.*expired", diagnostic, re.I):
        return "Coding subscription expired"
    if re.search(
        r"not authenticated|invalid.api.key|authentication.required|unauthorized",
        diagnostic,
        re.I,
    ):
        return "Provider authentication unavailable"
    if re.search(r"insufficient.balance|quota.exhausted|usage.limit", diagnostic, re.I):
        return "Provider quota exhausted"
    if re.search(r"not.supported.when|model.*not.available|model.*not.found", diagnostic, re.I):
        return "Provider model unavailable"
    return None


def inference_observed(turns, usage):
    """Zero-receipt setup failures are separate from interrupted paid work."""
    if any((usage.get(k) or 0) > 0 for k in ("input_tokens", "output_tokens")):
        return True
    for directory in turns:
        for event in read_events(directory / "events.jsonl"):
            item = event.get("item")
            if (
                event.get("type") == "item.completed"
                and isinstance(item, dict)
                and item.get("type")
                in {
                    "agent_message",
                    "reasoning",
                    "command_execution",
                    "web_search",
                }
            ):
                return True
            message = event.get("message")
            if (
                event.get("type") == "assistant"
                and isinstance(message, dict)
                and message.get("content")
            ):
                return True
            result = event.get("result")
            if not isinstance(result, dict):
                continue
            receipt = result.get("usage")
            if isinstance(receipt, dict) and any(
                isinstance(receipt.get(k), int) and receipt[k] > 0
                for k in ("input_tokens", "output_tokens", "thinking_tokens")
            ):
                return True
    return False


def command(campaign, config, prompt, prompt_path, cursor, remaining):
    backend = config["backend"]
    model = config["model"]
    effort = config.get("effort")
    if backend in ["codex", "codex-glm"]:
        result = [backend, "exec"] + (["resume", cursor] if cursor else [])
        result += [
            "--model",
            model,
            "--json",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
        ]
        if backend == "codex":
            result += ["-c", 'service_tier="default"']
        if effort:
            result += ["-c", f'model_reasoning_effort="{effort}"']
        return result + [prompt]
    if backend == "grok":
        result = [
            "grok",
            "--oauth",
            "--prompt-file",
            str(prompt_path),
            "--model",
            model,
            "--output-format",
            "streaming-messages-json",
            "--always-approve",
        ]
        if effort:
            result += ["--reasoning-effort", effort]
        if cursor:
            result += ["--resume", cursor]
        return result
    if backend == "agy":
        result = [
            "agy",
            "--print",
            prompt,
            "--model",
            model,
            "--output-format",
            "stream-json",
            "--print-timeout",
            "0",
            "--dangerously-skip-permissions",
        ]
        result += ["--conversation", cursor] if cursor else ["--new-project"]
        return result
    return [
        sys.executable,
        "-m",
        "conjecture_solver.workspace_agent",
        "--provider-config",
        str(Path(config["provider_config"]).resolve()),
        "--prompt-file",
        str(prompt_path),
        "--cwd",
        str(prompt_path.parent.parent / "work"),
        "--model",
        model,
        "--wall-seconds",
        str(max(1, int(remaining))),
    ]


def agent_version(backend):
    if backend == "builtin":
        return "simjecture-smolagents-" + importlib.metadata.version("smolagents")
    if backend == "agy":
        path = Path(subprocess.check_output(["which", "agy"], text=True).strip()).resolve()
        return "agy-cli-sha256-" + hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return (
        subprocess.check_output([backend, "--version"], text=True, timeout=10)
        .strip()
        .splitlines()[0]
    )


def run_trial(campaign, config, task, repetition):
    identifier = config["id"] + "-" + task + "-" + str(repetition)
    directory = campaign.root / "trials" / identifier
    existing = directory / "public-grade.json"
    if existing.exists():
        return json.loads(existing.read_text())
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    work = campaign.work / "trials" / identifier
    if work.exists():
        raise RuntimeError("Interrupted trial requires explicit recovery: " + identifier)
    prepare(task, work)
    (work / "ENVIRONMENT.md").write_text(
        f"Numerical Python interpreter: {campaign.numerical_python}. "
        "Work only on this task. Do not inspect any verifier, oracle, prior trial "
        "or another agent output.\n"
    )
    for p in (work / "raw").rglob("*"):
        if p.is_file():
            p.chmod(0o444)
    budget = TASKS[task]["seconds"]
    prompt = (
        f"Read TASK.md and ENVIRONMENT.md in your current directory. Complete the benchmark, "
        f"preserve the raw inputs, and deliver all requested code, numerical results and findings. "
        "Keep your native tools. Do not inspect a verifier, oracle, prior trial "
        "or another agent output. "
        f"The fixed budget is {budget} seconds including verification; "
        "finish when your files are ready."
    )
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    version = agent_version(config["backend"])
    start = time.monotonic()
    deadline = start + budget
    turns = []
    cursor = None
    report = None
    setup_error = None
    provider_interruption = None
    attempt = 0
    private_put(
        directory / "state.json",
        {
            "status": "running",
            "model": config["model"],
            "task": task,
            "repetition": repetition,
            "started_at": time.time(),
        },
    )
    print(
        json.dumps(
            {"event": "trial_started", "id": identifier, "model": config["model"], "task": task}
        ),
        flush=True,
    )
    while time.monotonic() < deadline - 10:
        turn = directory / ("turn-" + str(attempt))
        turn.mkdir(mode=0o700)
        turns.append(turn)
        current_prompt = prompt if attempt == 0 else public_feedback(report)
        prompt_path = turn / "prompt.txt"
        prompt_path.write_text(current_prompt)
        remaining = deadline - time.monotonic() - 10
        argv = command(campaign, config, current_prompt, prompt_path, cursor, remaining)
        env = dict(os.environ)
        env["PATH"] = str(campaign.numerical_python.parent) + os.pathsep + env.get("PATH", "")
        if config["backend"] == "builtin":
            argv[argv.index("--cwd") + 1] = str(work)
        with (turn / "events.jsonl").open("w") as out, (turn / "stderr.log").open("w") as err:
            (turn / "events.jsonl").chmod(0o600)
            (turn / "stderr.log").chmod(0o600)
            child = subprocess.Popen(
                argv, cwd=work, stdout=out, stderr=err, env=env, start_new_session=True
            )
            try:
                child.wait(timeout=max(1, remaining))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        usage, cursor = native_usage(config["backend"], turns)
        report = grade(task, work, timeout=max(1, min(120, deadline - time.monotonic())))
        elapsed = time.monotonic() - start
        if report["passed"] and elapsed <= budget:
            break
        unavailable = availability_error(turn)
        if unavailable:
            if inference_observed(turns, usage):
                provider_interruption = unavailable
            else:
                setup_error = unavailable
            break
        attempt += 1
        if child.returncode:
            time.sleep(min(5, max(0, deadline - time.monotonic() - 10)))
    elapsed = time.monotonic() - start
    if report is None:
        report = grade(task, work, timeout=30)
    usage, cursor = native_usage(config["backend"], turns)
    metadata = {
        "model": config["model"],
        "agent": config["backend"],
        "agent_version": version,
        "settings": {
            "reasoning_effort": config.get("effort"),
            "service_tier": "standard",
            "tool_profile": "native-default-cooperative",
        },
        "comparison": {
            "protocol": "controlled",
            "budget_seconds": budget,
            "hardware": campaign.hardware,
            "harness_version": campaign.harness_version,
            "runner_version": VERSION,
            "prompt_sha256": prompt_hash,
            "continuation_policy": "public-field-labels-original-deadline",
        },
        "wall_seconds": elapsed,
        "first_verified_completion_seconds": elapsed if report["passed"] else None,
        **usage,
    }
    report["trial"].update(metadata)
    if setup_error:
        report["trial"]["invalidated_reason"] = setup_error + " - no successful inference"
        report["trial"]["comparison"]["protocol"] = "exploratory"
    if provider_interruption:
        report["trial"]["provider_interruption"] = provider_interruption
    private_put(directory / "grade.json", report)
    public = public_grade(report)
    if setup_error:
        private_put(
            directory / "availability.json",
            {"status": "blocked", "reason": setup_error, "model": config["model"]},
        )
    if provider_interruption:
        private_put(directory / "provider-interruption.json", {"reason": provider_interruption})
    private_put(existing, public)
    from conjecture_solver.web.workspace import Workspace

    if campaign.workspace:
        Workspace(campaign.workspace).import_benchmark_reports({"reports": [public]})
    private_put(
        directory / "state.json",
        {
            "status": "blocked"
            if setup_error
            else "passed"
            if report["passed"] and elapsed <= budget
            else "failed",
            "elapsed_seconds": elapsed,
            "model": config["model"],
            "task": task,
        },
    )
    print(
        json.dumps(
            {
                "event": "trial_finished",
                "id": identifier,
                "passed": report["passed"] and elapsed <= budget,
                "wall_seconds": round(elapsed, 2),
                "blocked": bool(setup_error),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
            }
        ),
        flush=True,
    )
    return public


def public_feedback(report):
    """Uniform labels only: no expected values or hidden-fixture contents."""
    failed = [
        c["metric"]
        for c in (report or {}).get("checks", [])
        if not c["passed"] and not c["metric"].startswith("holdout")
    ]
    if report and not report.get("findings_present"):
        failed.append("FINDINGS.md missing or empty")
    if report and not report.get("intact_inputs"):
        failed.append("Raw inputs changed")
    if report and report.get("error"):
        failed.append("Reducer could not be independently reexecuted")
    return (
        "Continue the same TASK.md using saved PROGRESS.md and outputs. "
        "The host has not verified the required contract. Preserve the original "
        "deadline. Failed public-case fields: "
        + ", ".join(failed[:30])
        + ". Check all required deliverables and implement the stated definitions. "
        "No expected answers or hidden-fixture data are supplied."
    )


def run_campaign(
    configurations,
    output,
    *,
    repeats=5,
    workers=4,
    tasks=None,
    numerical_python=None,
    workspace=None,
    task_repeats=None,
):
    if not 1 <= repeats <= 100 or not 1 <= workers <= 16:
        raise ValueError("Use 1-100 repetitions and 1-16 workers")
    if not configurations or len(configurations) > 100:
        raise ValueError("Provide 1-100 model configurations")
    identifiers = set()
    for config in configurations:
        if not isinstance(config, dict) or config.get("backend") not in {
            "codex",
            "codex-glm",
            "grok",
            "agy",
            "builtin",
        }:
            raise ValueError("Unsupported coding-agent backend")
        if not re.fullmatch(r"[\w.-]{1,100}", config.get("id", "")):
            raise ValueError("Each configuration needs a safe id")
        if config["id"] in identifiers:
            raise ValueError("Duplicate configuration id")
        identifiers.add(config["id"])
        if not isinstance(config.get("model"), str) or not config["model"].strip():
            raise ValueError("Each configuration needs a model identifier")
        if config["backend"] == "builtin" and not Path(config.get("provider_config", "")).is_file():
            raise ValueError("API coding agents need an existing private provider config")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    configurations = [dict(config) for config in configurations]
    for config in configurations:
        if config["backend"] == "builtin":
            provider = json.loads(Path(config["provider_config"]).read_text())
            if not isinstance(provider, dict) or not provider.get("base_url"):
                raise ValueError("Provider configuration requires base_url")
            if config.get("effort"):
                provider["reasoning_effort"] = config["effort"]
            config["effort"] = provider.get("reasoning_effort") or None
            frozen = output / "provider-configs" / (config["id"] + ".json")
            private_put(frozen, provider)
            config["provider_config"] = str(frozen)
    # Resolving a virtualenv's Python symlink discards its dependency environment.
    numeric = Path(numerical_python or sys.executable).expanduser().absolute()
    source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    campaign = Campaign(
        output,
        output / "work",
        numeric,
        Path(workspace).resolve() if workspace else None,
        workers,
        "simjecture-runner-" + source,
    )
    tasks = tasks or list(TASKS)
    if any(task not in TASKS for task in tasks):
        raise ValueError("Unknown benchmark task")
    task_repeats = task_repeats or {}
    if any(
        task not in tasks or type(count) is not int or not 1 <= count <= 100
        for task, count in task_repeats.items()
    ):
        raise ValueError("Task repetitions must be 1-100 for selected tasks")
    repetitions = {task: task_repeats.get(task, repeats) for task in tasks}
    jobs = []
    rng = random.Random(61001)
    for repetition in range(1, max(repetitions.values()) + 1):
        group = list(configurations)
        rng.shuffle(group)
        for task in tasks:
            if repetition <= repetitions[task]:
                jobs.extend((config, task, repetition) for config in group)
    # Paths and keys stay private. The progress manifest only contains identity.
    identities = [
        {k: c.get(k) for k in ("id", "backend", "model", "effort")} for c in configurations
    ]
    private_put(
        output / "plan.json",
        {
            "version": VERSION,
            "hardware": campaign.hardware,
            "repeats": repeats,
            "workers": workers,
            "configurations": identities,
            "trials": len(jobs),
            "tasks": tasks,
            "task_repeats": repetitions,
            "policy": (
                "fresh native sessions; uniform public-field feedback; original deadlines; "
                "independent numerical grading; private traces excluded"
            ),
        },
    )
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_trial, campaign, *job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as error:
                failures.append(
                    {
                        "id": futures[future][0]["id"],
                        "task": futures[future][1],
                        "error_type": type(error).__name__,
                    }
                )
                print(json.dumps({"event": "runner_error", **failures[-1]}), flush=True)
    reports = [
        json.loads(p.read_text()) for p in sorted((output / "trials").glob("*/public-grade.json"))
    ]
    private_put(output / "leaderboard.json", summarize(reports))
    private_put(output / "runner-errors.json", failures)
    print(
        json.dumps(
            {
                "event": "campaign_finished",
                "graded_trials": len(reports),
                "runner_errors": len(failures),
            }
        ),
        flush=True,
    )
    return {"output": str(output), "graded_trials": len(reports), "runner_errors": len(failures)}


def cli(args):
    configs = json.loads(args.config.read_text())
    task_repeats = {}
    for item in args.task_repeats or []:
        task, separator, count = item.partition("=")
        if not separator:
            raise ValueError("Use --task-repeats TASK=COUNT")
        task_repeats[task] = int(count)
    return run_campaign(
        configs,
        args.output,
        repeats=args.repeats,
        workers=args.workers,
        tasks=args.tasks,
        numerical_python=args.numerical_python,
        workspace=args.workspace,
        task_repeats=task_repeats,
    )
