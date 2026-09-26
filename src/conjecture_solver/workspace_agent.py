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

    extra = (
        {"reasoning_effort": config["reasoning_effort"]} if config.get("reasoning_effort") else {}
    )
    return OpenAIServerModel(
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

    tools = [read_file, write_file, terminal, fetch_page]
    if project is not None and workspace is not None:

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

        tools += [draft_study, research_tools]
    return tools


def run_agent(
    prompt, root, config, *, model=None, wall_seconds=900, judge=False, project=None, workspace=None
):
    deadline = time.time() + wall_seconds
    llm = model_for(config, model, timeout=min(90, max(1, wall_seconds)))
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
        max_steps=24,
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
            "Do not invent user inputs, results or tool installation success."
        ),
    )
    with contextlib.redirect_stdout(sys.stderr):
        # Tool/step events use the original stream while library chatter stays out of JSONL.
        result = agent.run(prompt)
        if result.state != "success":
            return (
                "This turn reached its action limit. Work so far is saved; "
                "continue from the project files.\n\n" + str(result.output)
            )
        return str(result.output)


def run_external(prompt, root, config, turn, workspace=None):
    """Reuse the native CLI supervision adapter for an interactive turn."""
    from .agent_supervisor import AgentSupervisor

    directory = turn / "cli"
    args = argparse.Namespace(
        campaign=root,
        state_dir=directory,
        workflow="frontier",
        wall_seconds=900,
        turn_seconds=900,
        backend=config["backend"],
        model=config["model"],
        judge_model=config.get("judge_model", config["model"]),
        executable=config["backend"],
        reasoning_effort=config.get("reasoning_effort") or None,
    )
    supervisor = AgentSupervisor(args)
    (directory / "research").symlink_to(root, target_is_directory=True)
    output = directory / "turn"
    output.mkdir()
    emit("tool", name=config["backend"], arguments={"task": "Working in project files"})
    # Native CLI agents can access the same durable brief and installation bridge.
    prompt += (
        "\nTo prepare an autonomous study, write a JSON object to STUDY_BRIEF.json in "
        "the project files directory, with question, success_criteria, constraints, "
        "hours (0.01 to 168), completion_policy ('answer' or 'repair'). This prepares "
        "an editable brief; it does not launch a study. Existing project files are available."
    )
    if workspace:
        prompt += (
            "\nFor research software inventory, reuse the local Python bridge: "
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
    rc = supervisor.launch(output, prompt)
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-config", required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--wall-seconds", type=float, default=900)
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

        def expired(*_):
            raise KeyboardInterrupt("Turn stopped or time budget reached; project files are saved")

        signal.signal(signal.SIGALRM, expired)
        signal.signal(signal.SIGTERM, expired)
        signal.signal(signal.SIGINT, expired)
        signal.alarm(max(1, int(args.wall_seconds)))
        if config.get("backend", "builtin") != "builtin":
            answer = run_external(
                args.prompt_file.read_text(),
                args.cwd.resolve(),
                config,
                args.prompt_file.parent,
                workspace,
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
