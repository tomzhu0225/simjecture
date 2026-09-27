"""Built-in agent transport using Hugging Face smolagents, shared by chat and studies.

This is a cooperative local agent, like the supported external CLIs. Numerical
evidence still goes through ResearchService. Reviewers receive no tools.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ACTIVE_COMMANDS: set[int] = set()


def require_runtime():
    if importlib.util.find_spec("smolagents") is None:
        raise ValueError("Install the built-in agent with: uv sync --extra workspace")


def read_provider(path):
    if not path or not Path(path).is_file():
        raise ValueError("Choose an agent and model in the conversation before starting")
    config = json.loads(Path(path).read_text())
    if not config.get("model") or not config.get("base_url"):
        raise ValueError(
            "Choose a model in the conversation and configure its API endpoint if needed"
        )
    return config


def model_for(config, model=None, timeout=90):
    require_runtime()
    from smolagents import OpenAIServerModel

    class ActivityModel(OpenAIServerModel):
        def generate(self, messages, *args, **kwargs):
            prefix = getattr(self, "conversation_history", [])
            if prefix:
                messages = [messages[0], *prefix, *messages[1:]]
            emit("activity", state="thinking", label="Thinking")
            response = super().generate(messages, *args, **kwargs)
            from .web.activity import describe_tool

            if response.tool_calls and response.tool_calls[0].function.name != "final_answer":
                call = response.tool_calls[0].function
                arguments = call.arguments
                if isinstance(arguments, str):
                    with contextlib.suppress(ValueError):
                        arguments = json.loads(arguments)
                emit("activity", state="working", **describe_tool(call.name, arguments))
            else:
                emit("activity", state="responding", label="Writing a response")
            return response

    extra = (
        {"reasoning_effort": config["reasoning_effort"]} if config.get("reasoning_effort") else {}
    )
    return ActivityModel(
        model_id=model or config["model"],
        api_base=config["base_url"],
        api_key=config.get("api_key") or "local",
        client_kwargs={"timeout": timeout, "max_retries": 1},
        max_tokens=8192,
        **extra,
    )


def public_error(error, config=None):
    message = str(error)
    if config and config.get("api_key"):
        message = message.replace(config["api_key"], "[redacted]")
    return message[:1500]


def emit(kind, **fields):
    print(
        json.dumps({"type": kind, "time": time.time(), **fields}, default=str),
        file=sys.__stdout__,
        flush=True,
    )


def contained(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Use a path inside this project's files directory")
    return path


def agent_tools(root, deadline, project=None, workspace=None):
    from smolagents import tool

    from .agent_skills import research_skills

    skills = research_skills()

    @tool
    def read_skill(name: str, path: str = "SKILL.md") -> str:
        """Read an installed research skill or its reference/example file.

        Args:
            name: Skill name from AVAILABLE SIMJECTURE RESEARCH SKILLS.
            path: Relative resource inside that skill; defaults to SKILL.md.
        """
        resource = skills.read(name, path, max_chars=32000)
        emit("activity", state="working", label="Reading skill", detail=f"{name}/{path}")
        return json.dumps(resource)

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 project file or list a directory.

        Args:
            path: Relative path in the working directory; use . to list files.
        """
        p = contained(root, path)
        if p.is_dir():
            return "\n".join(x.name + ("/" if x.is_dir() else "") for x in sorted(p.iterdir()))[
                :20000
            ]
        if p.stat().st_size > 256000:
            return "File exceeds 256 KB. Use a focused analysis command to inspect it."
        return p.read_text()

    @tool
    def write_file(path: str, content: str) -> str:
        """Write a UTF-8 project file, for example a simulation or analysis script.

        Args:
            path: Relative path in the working directory.
            content: Complete text to write.
        """
        p = contained(root, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Saved {path} ({len(content)} characters)"

    @tool
    def terminal(command: str, timeout_seconds: int = 120) -> str:
        """Run a shell command on the execution machine in the project directory.
        Use it for analysis, environment setup and invoking the existing lab client.
        Temporary calculations are exploration, not accepted scientific evidence.

        Args:
            command: Shell command to execute.
            timeout_seconds: Maximum execution time, between 1 and 600 seconds.
        """
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError("The turn deadline has expired")
        timeout = min(max(1, timeout_seconds), 600, remaining)
        emit(
            "activity",
            state="running_command",
            label="Running a command",
            detail=command.splitlines()[0][:300],
        )
        if workspace is not None and project is not None:
            job = workspace.start_simulation(
                project,
                dict(
                    name=command.splitlines()[0][:70],
                    command=command,
                    timeout_seconds=timeout,
                    kind="command",
                ),
            )
            emit("simulation", id=job["id"], name=job["name"])
            try:
                while True:
                    result = workspace.simulation(project, job["id"])
                    if result["status"] in {
                        "succeeded",
                        "failed",
                        "cancelled",
                        "timed_out",
                        "interrupted",
                    }:
                        return (
                            f"{result['status']} · exit code {result.get('returncode')}\n"
                            + result["output"]
                        )
                    time.sleep(0.2)
            finally:
                with contextlib.suppress(ValueError, OSError):
                    workspace.stop_simulation(project, job["id"])
        environment = os.environ.copy()
        environment["PATH"] = (
            str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
        )
        with subprocess.Popen(
            ["/bin/bash", "-c", command],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=environment,
            start_new_session=True,
        ) as child:
            ACTIVE_COMMANDS.add(child.pid)
            try:
                output, _ = child.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                output, _ = child.communicate()
                return "Command timed out.\n" + output[-24000:]
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                ACTIVE_COMMANDS.discard(child.pid)
        return f"Exit code: {child.returncode}\n{output[-24000:]}"

    @tool
    def fetch_page(url: str) -> str:
        """Fetch a public web page or textual resource for research, preserving its URL.

        Args:
            url: HTTP or HTTPS URL to retrieve.
        """
        import httpx

        if not url.startswith(("https://", "http://")):
            raise ValueError("Use an HTTP or HTTPS URL")
        with httpx.stream("GET", url, follow_redirects=True, timeout=30) as response:
            response.raise_for_status()
            body = b""
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) >= 100000:
                    break
        return url + "\n" + body[:100000].decode(errors="replace")

    tools = [read_file, write_file, terminal, fetch_page, read_skill]
    if project is not None and workspace is not None:

        @tool
        def progress_update(message: str) -> str:
            """Share a concise public progress update during an extended investigation.
            Explain the current stage, finding/blocker and next action, not private reasoning.

            Args:
                message: Short factual status update for the user.
            """
            return json.dumps(workspace.progress_update(project, message))

        @tool
        def run_simulation(name: str, command: str, timeout_seconds: int = 3600) -> str:
            """Launch an interactive simulation in a permanent named run folder.
            Project input files are copied into its workspace; run the command in foreground.
            Returns immediately. The browser opens a side monitor with live logs and outputs.
            This is exploration, not independently accepted scientific evidence.

            Args:
                name: Short human-readable simulation name.
                command: Shell command to run, using the copied project inputs.
                timeout_seconds: Maximum run time in seconds.
            """
            result = workspace.start_simulation(
                project, dict(name=name, command=command, timeout_seconds=timeout_seconds)
            )
            emit("simulation", id=result["id"], name=name)
            return json.dumps({k: result[k] for k in ("id", "name", "status", "work_directory")})

        @tool
        def simulation_status(identifier: str) -> str:
            """Read live logs, status and result files of an interactive simulation.

            Args:
                identifier: Simulation ID returned by run_simulation.
            """
            return json.dumps(workspace.simulation(project, identifier))

        @tool
        def draft_study(
            question: str,
            success_criteria: str,
            constraints: str,
            hours: float = 1,
            completion_policy: str = "answer",
            instrument: str = "",
        ) -> str:
            """Prepare an editable autonomous study brief for the user to launch.
            Preserve their objective. Ask about consequential missing information.
            Never claim that preparing this brief starts or completes research.

            Args:
                question: Precise claim to test, grounded in the user's objective.
                success_criteria: Measurements, evidence and counterexamples that answer it.
                constraints: Fixed assumptions, allowed changes and required tools or inputs.
                hours: Requested wall-time budget, between 0.01 and 168 hours.
                completion_policy: answer accepts a negative result; repair seeks a tested repair.
                instrument: Installed catalogue tool ID, e.g. warpx-cpu; empty for ordinary Python.
            """
            brief = workspace.save_brief(
                project,
                dict(
                    question=question,
                    success_criteria=success_criteria,
                    constraints=constraints,
                    hours=hours,
                    completion_policy=completion_policy,
                    instrument=instrument,
                ),
            )
            emit("brief", brief=brief)
            return "Study brief prepared. The user can edit it and press Start research."

        @tool
        def research_tools(action: str = "list", name: str = "", path: str = "") -> str:
            """List, install, check or register scientific software on this machine.
            Install only software requested by the user. Use terminal for custom setup,
            then register its existing capability-directory path here. Registration
            records availability; each study still needs scientific validation.

            Args:
                action: list, install, check or register.
                name: Catalogue tool ID or a descriptive name for a custom tool.
                path: Existing capability directory for register, or supplied source for install.
            """
            if action == "list":
                return json.dumps(workspace.catalogue())
            if action == "register":
                return json.dumps(workspace.register_tool(dict(name=name, path=path)))
            if action in {"install", "check"}:
                return json.dumps(
                    workspace.start_install(dict(name=name, action=action, source=path))
                )
            raise ValueError("Unknown tool action")

        tools += [draft_study, research_tools, run_simulation, simulation_status, progress_update]
    return tools


def run_agent(
    prompt,
    root,
    config,
    *,
    model=None,
    wall_seconds=None,
    judge=False,
    project=None,
    workspace=None,
):
    deadline = time.time() + wall_seconds if wall_seconds is not None else float("inf")
    llm = model_for(config, model, timeout=min(600, max(1, wall_seconds or 600)))
    if judge:
        response = llm.generate([{"role": "user", "content": prompt}])
        if response.tool_calls:
            raise ValueError("Independent reviewer attempted a tool call")
        if response.token_usage:
            emit(
                "usage",
                input_tokens=response.token_usage.input_tokens,
                output_tokens=response.token_usage.output_tokens,
            )
        return response.content
    from smolagents import ToolCallingAgent

    def step_event(step, **kwargs):
        if time.time() >= deadline:
            raise TimeoutError("Turn deadline reached")
        for call in step.tool_calls or []:
            # final_answer contains prose rather than an operation.
            if call.name != "final_answer":
                emit("tool", name=call.name, arguments=call.arguments)
        if step.observations and not step.is_final_answer:
            emit("observation", text=public_error(step.observations, config)[:1500])
        if step.token_usage:
            emit(
                "usage",
                input_tokens=step.token_usage.input_tokens,
                output_tokens=step.token_usage.output_tokens,
            )

    agent = ToolCallingAgent(
        tools=agent_tools(root, deadline, project, workspace),
        model=llm,
        max_steps=sys.maxsize if wall_seconds is None else 24,
        return_full_result=True,
        verbosity_level=-1,
        step_callbacks=[step_event],
        instructions=(
            "You are Simjecture's research assistant. Work on the user's actual request. "
            "Distinguish observations, hypotheses and independently accepted findings. "
            "Use files and tools to do work, not just suggest commands. Never expose credentials. "
            "For interactive requests return after doing the requested task. For autonomous "
            "research follow the supplied research service guide and hand off for reviews. "
            "Only use draft_study when an autonomous investigation would serve the request. "
            "For interactive simulations, prefer run_simulation so the user can follow live "
            "progress while continuing the conversation. Files belong to this conversation; "
            "never place research results in /tmp. Use Markdown with LaTeX equations and "
            "fenced, language-labelled code. Link figures using relative project paths, e.g. "
            "![Description](figure.png), or simulation:<run-id>/figure.png for run outputs. "
            "During extended work use progress_update for meaningful milestones, blockers "
            "and next actions. Do not expose private reasoning or invent progress percentages. "
            "Do not invent user inputs, results or tool installation success."
        ),
    )
    from .workspace_sessions import load_session, save_session

    session = load_session(root.parent, config) if workspace and project else {}
    history = session.get("history", [])
    llm.conversation_history = history
    if workspace and project:
        emit("session", resumed=bool(history), backend="builtin")
    with contextlib.redirect_stdout(sys.stderr):
        # Tool/step events use the original stream while library chatter stays out of JSONL.
        try:
            result = agent.run(prompt)
        finally:
            if workspace and project:
                messages = list(history)
                from smolagents.memory import FinalAnswerStep

                for step in agent.memory.steps:
                    if isinstance(step, FinalAnswerStep):
                        messages.append({"role": "assistant", "content": str(step.output)})
                        continue
                    messages.extend(
                        json.loads(message.model_dump_json()) for message in step.to_messages()
                    )
                save_session(root.parent, config, history=messages)
        if result.state != "success":
            return (
                "This turn reached its action limit. Work so far is saved; "
                "continue from the project files.\n\n" + str(result.output)
            )
        return str(result.output)


def run_external(prompt, root, config, turn, workspace=None, *, wall_seconds=None):
    """Reuse the native CLI supervision adapter for an interactive turn."""
    from .agent_supervisor import AgentSupervisor

    directory = turn / "cli"
    args = argparse.Namespace(
        campaign=root,
        state_dir=directory,
        workflow="frontier",
        wall_seconds=wall_seconds or 0,
        turn_seconds=wall_seconds or 0,
        unbounded_interactive=wall_seconds is None,
        backend=config["backend"],
        model=config["model"],
        judge_model=config.get("judge_model", config["model"]),
        executable=config["backend"],
        reasoning_effort=config.get("reasoning_effort") or None,
        interactive_activity=True,
    )
    supervisor = AgentSupervisor(args)
    from .workspace_sessions import load_session, save_session

    session = load_session(root.parent, config) if workspace else {}
    if session.get("cursor"):
        supervisor.state["worker_cursor"] = session["cursor"]
    emit("session", resumed=bool(session.get("cursor")), backend=config["backend"])
    (directory / "research").symlink_to(root, target_is_directory=True)
    output = directory / "turn"
    output.mkdir()
    emit("tool", name=config["backend"], arguments={"task": "Working in project files"})
    emit("activity", state="connecting", label="Connecting to " + config["backend"])
    # Native CLI agents can access the same durable brief and installation bridge.
    prompt += (
        "\nTo prepare an autonomous study, write a JSON object to STUDY_BRIEF.json in "
        "the project files directory, with question, success_criteria, constraints, "
        "hours (0.01 to 168), completion_policy ('answer' or 'repair'). This prepares "
        "an editable brief; it does not launch a study. Existing project files are available."
    )
    if workspace:
        prompt += (
            f"\nUse {sys.executable} for the workspace bridge and project file analysis. "
            "Scientific runtimes may have separate interpreters. "
            "For research software inventory, reuse the local Python bridge: "
            "from conjecture_solver.web.workspace import Workspace; "
            f"w = Workspace({str(workspace.root)!r}); "
            "w.catalogue() lists tools. "
            "w.start_install({'name':'warpx-cpu','action':'install'}) "
            "starts a requested supported installation. For other user-requested software, "
            "install it with your native tools, create a Simjecture capability descriptor, "
            "then w.register_tool({'name':'Tool name','path':'/capability/directory'}). "
            "Registered tools appear in the browser catalogue. "
            "Installation is not scientific validation."
        )
        prompt += (
            "\nDuring extended work share public progress with w.progress_update("
            f"{root.parent.name!r}, 'Current stage, observed finding/blocker, and next action'). "
            "Use this at meaningful milestones; do not expose private reasoning. "
            "For interactive simulations use w.start_simulation("
            f"{root.parent.name!r}, {{'name':'Run name','command':'python calculation.py',"
            "'timeout_seconds':3600}). Run commands in foreground; this launches a background "
            "job with permanent inputs/outputs and a live browser monitor. "
            f"w.simulation({root.parent.name!r}, 'run-id') reads status, output and files. "
            "Use this for numerical runs instead of untracked background shell processes. "
            "Use Markdown, LaTeX equations, language-labelled code fences, and image links "
            "to saved relative file paths or simulation:<run-id>/figure.png. "
            "All numerical attempts, including smoke tests, belong in project files and "
            "must launch through start_simulation so their logs and outputs appear in the "
            "monitor. Never use /tmp for simulation inputs or outputs. The interface above "
            "is sufficient; inspect host implementation only after a concrete API error. "
            "Interactive work has no default time limit. Save a brief PROGRESS.md during "
            "long preparation or analysis and use progress_update to explain your current "
            "stage, findings and next action periodically. Launch bounded simulation jobs "
            "so the user can follow them; return control once the requested work is ready. "
            "Do not let plotting setup block launching a valid pilot. Use runtime interface "
            "metadata: a native-input-file binary does not imply available Python bindings; "
            "do not search for pywarpx when python_bindings is false. For cross-solver work, "
            "reuse prior inputs/results and state model, forcing, unit and diagnostic "
            "differences before calling it a replication. Do not silently remove driving "
            "or change boundaries just to get a run."
        )
    try:
        rc = supervisor.launch(output, prompt)
    finally:
        if workspace and supervisor.state.get("worker_cursor"):
            save_session(root.parent, config, cursor=supervisor.state["worker_cursor"])
    messages = []
    for line in (output / "response.json").read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            messages.append(item.get("text", ""))
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            messages.append(event["result"])
        if event.get("event") == "result":
            messages.append(event.get("result", {}).get("response", ""))
    if rc:
        raise ValueError(
            f"{config['backend']} exited with code {rc}. Check its login and model settings. "
            + (output / "stderr.log").read_text()[-1000:]
        )
    return "\n\n".join(messages) or "The CLI turn ended. Inspect the project files for its output."


def interrupted_turn_summary(directory, turn, seconds, *, timed_out):
    """Describe observed saved work, without inventing a scientific result."""
    from .web.jobs import list_jobs

    reason = (
        f"The agent reached its {(seconds or 0) / 60:g}-minute conversation-turn limit."
        if timed_out
        else "The agent turn was stopped."
    )
    jobs = [j for j in list_jobs(directory) if j.get("source_turn") == turn.name]
    files = [p for p in (directory / "files").rglob("*") if p.is_file() and not p.is_symlink()]
    lines = [reason, "This is an agent interruption, not a verdict that the simulation failed."]
    if jobs:
        lines += [f"- {j['name']}: {j['status']}." for j in jobs]
    else:
        lines.append("No simulation was registered with this turn's workspace monitor.")
    lines.append(f"Conversation files remain in {directory / 'files'} ({len(files)} files).")
    lines.append(
        "Ask to continue from the saved work; running managed simulations keep their own deadlines."
    )
    return "\n\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-config", required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--wall-seconds", type=float, default=None)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--project")
    args = parser.parse_args(argv)
    config = read_provider(args.provider_config)
    workspace = None
    if args.workspace:
        from .web.workspace import Workspace

        workspace = Workspace(args.workspace)
    try:

        def expired(signum, *_):
            summary = (
                interrupted_turn_summary(
                    args.cwd.resolve().parent,
                    args.prompt_file.parent,
                    args.wall_seconds,
                    timed_out=signum == signal.SIGALRM,
                )
                if workspace and args.project
                else ("Agent time budget reached" if signum == signal.SIGALRM else "Agent stopped")
            )
            raise KeyboardInterrupt(summary)

        signal.signal(signal.SIGALRM, expired)
        signal.signal(signal.SIGTERM, expired)
        signal.signal(signal.SIGINT, expired)
        if args.wall_seconds is not None:
            signal.alarm(max(1, int(args.wall_seconds)))
        if config.get("backend", "builtin") != "builtin":
            answer = run_external(
                args.prompt_file.read_text(),
                args.cwd.resolve(),
                config,
                args.prompt_file.parent,
                workspace,
                wall_seconds=args.wall_seconds,
            )
            brief = args.cwd / "STUDY_BRIEF.json"
            if workspace and brief.exists():
                workspace.save_brief(args.project, json.loads(brief.read_text()))
        else:
            answer = run_agent(
                args.prompt_file.read_text(),
                args.cwd.resolve(),
                config,
                model=args.model,
                wall_seconds=args.wall_seconds,
                judge=args.judge,
                project=args.project,
                workspace=workspace,
            )
        emit("result", subtype="success", result=answer)
        return 0
    except Exception as error:
        emit("result", subtype="error", is_error=True, result=public_error(error, config))
        return 1
    except KeyboardInterrupt as error:
        emit("result", subtype="error", is_error=True, result=str(error))
        return 124
    finally:
        signal.alarm(0)
        for pid in ACTIVE_COMMANDS.copy():
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
        if workspace and args.project:
            with contextlib.suppress(OSError, ValueError):
                workspace.write_conversation(args.project)


if __name__ == "__main__":
    raise SystemExit(main())
