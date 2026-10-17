"""Built-in agent transport using Hugging Face smolagents, shared by chat and studies.

This is a cooperative local agent, like the supported external CLIs. Numerical
evidence still goes through ResearchService. API reviewers can read only recorded review assets.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

ACTIVE_COMMANDS: set[int] = set()


def require_runtime():
    if importlib.util.find_spec("smolagents") is None:
        raise ValueError("Install the built-in agent with: uv sync --extra workspace")


def read_provider(path, *, api_only=False):
    if not path or not Path(path).is_file():
        raise ValueError("Choose an agent and model in the conversation before starting")
    config = json.loads(Path(path).read_text())
    if api_only and config.get("backend", "builtin") != "builtin":
        raise ValueError("An API reviewer requires an API profile; select its CLI backend instead")
    if not config.get("model") or not config.get("base_url"):
        raise ValueError(
            "Choose a model in the conversation and configure its API endpoint if needed"
        )
    return config


def model_for(
    config, model=None, timeout=90, max_tokens=None, *, native_tools=False, completion_check=None
):
    timeout = config.get("request_timeout_seconds", timeout)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("request_timeout_seconds must be positive and finite")
    output_limit = max_tokens if max_tokens is not None else config.get("max_tokens")
    if output_limit is not None and (
        isinstance(output_limit, bool) or not isinstance(output_limit, int) or output_limit <= 0
    ):
        raise ValueError("max_tokens must be a positive integer or omitted for provider defaults")
    require_runtime()
    from smolagents import OpenAIServerModel

    deepseek = "deepseek" in (model or config["model"]).lower() or (
        urlparse(config["base_url"]).hostname == "api.deepseek.com"
    )

    class ActivityModel(OpenAIServerModel):
        # smolagents uses textual action/observation history, not native tool
        # messages. Keep provider-only reasoning alongside that public memory.
        # DeepSeek requires it on assistant messages whenever tools are supplied.
        def _prepare_completion_kwargs(self, *args, **kwargs):
            original_messages = kwargs.get("messages")
            if native_tools and original_messages is not None:
                # Ask the library for parameters, not its lossy history conversion.
                kwargs["messages"] = [{"role": "user", "content": ""}]
            request = super()._prepare_completion_kwargs(*args, **kwargs)
            if native_tools and original_messages is not None:
                from .workspace_protocol import native_messages

                request["messages"] = native_messages(original_messages)
            if deepseek and request.get("tools"):
                request["tool_choice"] = "auto"
                if not hasattr(self, "reasoning_messages"):
                    self.reasoning_messages = {}
                prefix = hashlib.sha256()
                for message in request["messages"]:
                    prefix.update(json.dumps(message, sort_keys=True).encode())
                    if message["role"] != "assistant":
                        continue
                    key = prefix.hexdigest()
                    content = message.get("content") or ""
                    if isinstance(content, list):
                        content = "\n".join(part.get("text", "") for part in content)
                    call_ids = [c["id"] for c in message.get("tool_calls", [])]
                    if key not in self.reasoning_messages:
                        self.reasoning_messages[key] = next(
                            (
                                record["reasoning_content"]
                                for record in reversed(getattr(self, "reasoning_records", []))
                                if any(
                                    marker and (marker in content or marker in call_ids)
                                    for marker in record["markers"]
                                )
                            ),
                            "",
                        )
                    # Freeze each historical message: repeated answer text or
                    # reused provider call IDs must not rewrite the cached prefix.
                    message["reasoning_content"] = self.reasoning_messages[key]
            from .provider_usage import context_metadata

            if getattr(self, "usage_request_id", None):
                emit(
                    "provider_context",
                    request_id=self.usage_request_id,
                    **context_metadata(request),
                )
            return request

        def remember_reasoning(self, response):
            reasoning = getattr(response.raw.choices[0].message, "reasoning_content", None)
            if isinstance(reasoning, str):
                markers = [call.id for call in response.tool_calls or []]
                for call in response.tool_calls or []:
                    if call.function.name == "final_answer":
                        arguments = call.function.arguments
                        if isinstance(arguments, str):
                            with contextlib.suppress(ValueError):
                                arguments = json.loads(arguments)
                        if isinstance(arguments, dict) and isinstance(arguments.get("answer"), str):
                            markers.append(arguments["answer"])
                if isinstance(response.content, str) and response.content.strip():
                    markers.append(response.content.strip())
                if markers:
                    if not hasattr(self, "reasoning_records"):
                        self.reasoning_records = []
                    self.reasoning_records.append(
                        {"markers": markers, "reasoning_content": reasoning}
                    )

        def generate(self, messages, *args, **kwargs):
            if native_tools:
                # Text delimiters belong to the legacy transcript format. Native
                # calls are already structured; never trim their accompanying text.
                kwargs.pop("stop_sequences", None)
            prefix = getattr(self, "conversation_history", [])
            if prefix:
                messages = [messages[0], *prefix, *messages[1:]]
            tools = kwargs.get("tools_to_call_from") or []
            explicit_completion = deepseek and any(tool.name == "final_answer" for tool in tools)
            total_input = total_output = 0
            generation_id = uuid.uuid4().hex
            for attempt in range(4):
                emit("activity", state="thinking", label="Thinking")
                from .provider_usage import mapping, reported_usage

                self.usage_request_id = uuid.uuid4().hex
                receipt = dict(
                    request_id=self.usage_request_id,
                    generation_id=generation_id,
                    attempt=attempt + 1,
                    reason="completion_check" if attempt else "generation",
                    model=self.model_id,
                    sdk_max_retries=1,
                )
                emit("provider_request", status="started", **receipt)
                started = time.monotonic()
                try:
                    response = super().generate(messages, *args, **kwargs)
                except Exception as error:
                    emit(
                        "provider_request",
                        status="failed",
                        **receipt,
                        seconds=time.monotonic() - started,
                        error_type=type(error).__name__,
                        http_status=getattr(error, "status_code", None),
                    )
                    if getattr(self, "abort_on_request_error", False):
                        from .workspace_protocol import ProviderRequestFailure

                        raise ProviderRequestFailure(error) from error
                    raise
                finally:
                    self.usage_request_id = None
                raw = mapping(getattr(response, "raw", None))
                choice = mapping((raw.get("choices") or [{}])[0])
                native_content = mapping(choice.get("message")).get("content")
                emit(
                    "provider_request",
                    status="succeeded",
                    **receipt,
                    seconds=time.monotonic() - started,
                    provider_request_id=raw.get("id"),
                    usage=reported_usage(response),
                    finish_reason=choice.get("finish_reason"),
                    tool_call_count=len(response.tool_calls or []),
                    content_trimmed=isinstance(native_content, str)
                    and native_content != response.content,
                )
                if response.token_usage:
                    total_input += response.token_usage.input_tokens
                    total_output += response.token_usage.output_tokens
                if deepseek:
                    self.remember_reasoning(response)
                if not explicit_completion or response.tool_calls:
                    break
                if completion_check is not None:
                    # A host-owned validator may finish a fully verified task
                    # without another request just to reformat its final answer.
                    # A false result, missing receipt or exception cannot approve.
                    try:
                        verified = completion_check() is True
                    except Exception:
                        verified = False
                    emit("completion_probe", verified=verified)
                    if verified:
                        from smolagents.models import (
                            ChatMessageToolCall,
                            ChatMessageToolCallFunction,
                        )

                        response.tool_calls = [
                            ChatMessageToolCall(
                                id="host_verified_" + uuid.uuid4().hex,
                                type="function",
                                function=ChatMessageToolCallFunction(
                                    name="final_answer",
                                    arguments={"answer": "Host checks verified task delivery."},
                                ),
                            )
                        ]
                        break
                # Plain text may be a progress preamble, not a final answer.
                # Require an explicit completion handoff without using the
                # provider's unsupported forced tool_choice setting.
                if response.content and not any(
                    marker in str(response.content)
                    for marker in ("<tool_call>", "<tool_result>", "<result>")
                ):
                    emit("progress", text=str(response.content))
                if attempt == 3:
                    raise RuntimeError(
                        "The provider repeatedly returned text without taking a tool action "
                        "or explicitly finishing the turn. Work is saved; "
                        "this turn did not complete."
                    )
                messages = [
                    *messages,
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": str(response.content or "")}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "COMPLETION CHECK: Your text does not finish this turn. "
                                    "If it announces work, perform the next tool action now. "
                                    "Use structured tool calls, never tool-call XML "
                                    "or invented tool results in text. "
                                    "If answered or blocked, call final_answer with the "
                                    "answer, concrete blocker, or essential question. "
                                    "Never finalize merely to promise work. For greetings "
                                    "and ordinary questions, use final_answer for the reply."
                                ),
                            }
                        ],
                    },
                ]
            if response.token_usage:
                response.token_usage.input_tokens = total_input
                response.token_usage.output_tokens = total_output
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
    if output_limit is not None:
        extra["max_tokens"] = output_limit
    return ActivityModel(
        model_id=model or config["model"],
        api_base=config["base_url"],
        api_key=config.get("api_key") or "local",
        client_kwargs={"timeout": timeout, "max_retries": 1},
        retry=False,  # The SDK and persistent supervisor own transport recovery.
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
    def read_skill(name: str, path: str = "SKILL.md", offset: int = 0) -> str:
        """Read an installed research skill or its reference/example file.

        Args:
            name: Skill name from AVAILABLE SIMJECTURE RESEARCH SKILLS.
            path: Relative resource inside that skill; defaults to SKILL.md.
            offset: Character offset; follow next_offset to read the complete resource.
        """
        resource = skills.read(name, path, max_chars=32000, offset=offset)
        emit("activity", state="working", label="Reading skill", detail=f"{name}/{path}")
        return json.dumps(resource)

    @tool
    def read_file(path: str, offset: int = 0, max_bytes: int = 64000) -> str:
        """Read a UTF-8 project file or list a directory.

        Args:
            path: Relative path in the working directory; use . to list files.
            offset: Byte offset for a file or entry offset for a directory.
            max_bytes: File page size, 1..256000; follow next_offset for more.
        """
        p = contained(root, path)
        if type(offset) is not int or offset < 0 or not 1 <= max_bytes <= 256000:
            raise ValueError("Choose a nonnegative offset and a bounded page size")
        if p.is_dir():
            entries = sorted(p.iterdir())
            selected = entries[offset : offset + 200]
            return json.dumps(
                dict(
                    entries=[x.name + ("/" if x.is_dir() else "") for x in selected],
                    next_offset=offset + len(selected)
                    if offset + len(selected) < len(entries)
                    else None,
                )
            )
        with p.open("rb") as stream:
            stream.seek(offset)
            block = stream.read(max_bytes + 3)
        from .review_assets import decode_page

        content, consumed = decode_page(block, max_bytes)
        if offset == 0 and consumed == p.stat().st_size:
            return content
        end = offset + consumed
        return json.dumps(
            dict(
                content=content,
                offset=offset,
                next_offset=end if end < p.stat().st_size else None,
                total_bytes=p.stat().st_size,
            )
        )

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
            emit("command", id=job["id"], name=job["name"])
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
        from .console_log import ConsoleLog
        from .web.jobs import tail

        logs = contained(root, f"tool_logs/{uuid.uuid4().hex}")
        logs.mkdir(parents=True)
        timed_out = False
        with (
            (logs / "output.log").open("w+b", buffering=0) as output,
            subprocess.Popen(
                ["/bin/bash", "-c", command],
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
                start_new_session=True,
            ) as child,
        ):
            console = ConsoleLog(child.stdout, output, logs)
            ACTIVE_COMMANDS.add(child.pid)
            try:
                child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                console.join()
                ACTIVE_COMMANDS.discard(child.pid)
            if console.error:
                raise OSError(f"Could not retain tool output: {console.error}")
        label = "Command timed out." if timed_out else f"Exit code: {child.returncode}"
        return (
            label
            + "\n"
            + tail(logs / "output.log")
            + f"\nFull console and rotated archives: {logs.relative_to(root)}/"
        )

    @tool
    def fetch_page(url: str, offset: int = 0) -> str:
        """Fetch a public web page or textual resource for research, preserving its URL.

        Args:
            url: HTTP or HTTPS URL to retrieve.
            offset: Byte offset; follow next_offset to retrieve further pages.
        """
        import httpx

        from .review_assets import decode_page

        if not url.startswith(("https://", "http://")):
            raise ValueError("Use an HTTP or HTTPS URL")
        if type(offset) is not int or offset < 0:
            raise ValueError("Choose a nonnegative byte offset")
        with httpx.stream(
            "GET",
            url,
            headers={"Range": f"bytes={offset}-{offset + 100003}"},
            follow_redirects=True,
            timeout=30,
        ) as response:
            response.raise_for_status()
            body = b""
            skip = 0 if response.status_code == 206 else offset
            for chunk in response.iter_bytes(chunk_size=65536):
                removed = min(skip, len(chunk))
                skip -= removed
                body += chunk[removed:]
                if len(body) >= 100004:
                    break
        content, consumed = decode_page(body, 100000)
        return json.dumps(
            dict(
                url=url,
                content=content,
                offset=offset,
                next_offset=offset + consumed if len(body) > consumed else None,
            )
        )

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
        def run_command(name: str, command: str, timeout_seconds: int = 7200) -> str:
            """Start a long installation/build command with persistent live monitoring.
            Returns immediately; poll simulation_status with its ID until completion.
            Run the shell command in foreground, without nohup or a trailing ampersand.
            The job survives individual agent tool calls and appears in Commands.
            Shell pipefail is enabled so a failed compiler cannot be hidden by tail/tee.

            Args:
                name: Short descriptive build or installation name.
                command: Foreground shell command, run from the conversation files directory.
                timeout_seconds: Maximum job duration in seconds (up to seven days).
            """
            result = workspace.start_simulation(
                project,
                dict(
                    name=name,
                    command="set -o pipefail\n" + command,
                    timeout_seconds=timeout_seconds,
                    kind="command",
                ),
            )
            emit("command", id=result["id"], name=result["name"])
            return json.dumps({k: result[k] for k in ("id", "name", "status", "work_directory")})

        @tool
        def run_simulation(name: str, command: str, timeout_seconds: int = 3600) -> str:
            """Launch an interactive simulation in a permanent named run folder.
            Project input files are copied into its workspace; run the command in foreground.
            Returns immediately. The browser opens a side monitor with live logs and outputs.
            Save run-specific figures in the returned work_directory; keep cross-run reports
            in the conversation files directory. Copied project inputs are not run outputs.
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
            inherited_files: list[str] | None = None,
            machine_ids: list[str] | None = None,
            allow_solver_development: bool | None = None,
            capability_directory: str | None = None,
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
                instrument: Optional required installed solver, e.g. warpx-cpu.
                    Available tools remain automatic unless explicitly restricted.
                inherited_files: Parent research-relative paths for a continuation.
                    Omit to preserve the existing selection.
                machine_ids: Prepared execution worker IDs. Omit to preserve the current selection.
                allow_solver_development: Allow private solver forks; defaults true for new studies.
                    Omit to preserve the user's current setting. Readiness is not evidence approval.
                capability_directory: auto exposes all available installed tools (the default).
                    Use a descriptor file/directory to restrict access, or an empty string for
                    Python only. Omit to preserve the current access setting.
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
                    inherited_files=inherited_files,
                    machine_ids=machine_ids,
                    allow_solver_development=allow_solver_development,
                    **(
                        {"capability_directory": capability_directory}
                        if capability_directory is not None
                        else {}
                    ),
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
            After registering, check the returned catalogue ID. Check/install are
            asynchronous: use list to follow their state and report. Do not claim
            readiness until the selected capability check reports passed. A host
            shell test or a relocated copy does not replace this backend check.

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

        @tool
        def execution_machines(
            action: str = "list", machine: str = "", configuration: dict | None = None
        ) -> str:
            """Inspect or prepare registered execution workers through saved SSH connections.

            Args:
                action: list, status, prepare, check, or configure an authorized worker.
                machine: Worker ID for status; not an SSH address or a credential.
                configuration: Explicit changes for configure: config, root, run_as or label.
            """
            if action == "list":
                return json.dumps(workspace.machines())
            if action == "status":
                return json.dumps(workspace.machine_jobs(machine))
            if action == "prepare":
                return json.dumps(workspace.prepare_machine(machine))
            if action == "check":
                return json.dumps(workspace.check_machine(machine))
            if action == "configure":
                return json.dumps(workspace.configure_machine(machine, configuration or {}))
            raise ValueError("Use list, status, prepare, check or configure")

        @tool
        def execution_machine_command(machine: str, command: str, timeout_seconds: int = 60) -> str:
            """Run an operator-authorized SSH setup command; never scientific evidence.

            Args:
                machine: Registered worker ID. Credentials remain on the coordinator.
                command: Shell command to inspect or prepare that machine's software.
                timeout_seconds: Bounded wait, 1-7200 seconds. Output and receipt are retained.
            """
            return json.dumps(workspace.machine_command(machine, command, timeout_seconds))

        tools += [
            draft_study,
            research_tools,
            execution_machines,
            execution_machine_command,
            run_simulation,
            run_command,
            simulation_status,
            progress_update,
        ]
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
    session_dir=None,
    action_limit=None,
    review_root=None,
):
    if judge and session_dir is not None:
        raise ValueError("Independent reviewers cannot resume a worker session")
    deadline = time.time() + wall_seconds if wall_seconds is not None else float("inf")
    native_tools = (judge and review_root is not None) or (
        not judge
        and (
            "deepseek" in (model or config["model"]).lower()
            or urlparse(config["base_url"]).hostname == "api.deepseek.com"
        )
    )
    llm = model_for(
        config,
        model,
        timeout=config.get("request_timeout_seconds") or max(1, wall_seconds or 600),
        native_tools=native_tools,
    )
    if judge:
        review_tools = []
        if review_root is not None:
            from smolagents import tool

            from .review_assets import read_asset

            @tool
            def read_review_asset(
                sha256: str, json_path: str = "", offset: int = 0, max_bytes: int = 16384
            ) -> str:
                """Read a complete recorded review object through verified byte pages.

                Args:
                    sha256: SHA256 from the supplied source or packet reference.
                    json_path: Optional object.keys or array[0] selection in a JSON object.
                    offset: Byte offset into the complete file or selected JSON encoding.
                    max_bytes: Page size from 1 to 65536; next_offset reaches further pages.
                """
                return json.dumps(
                    read_asset(
                        review_root,
                        sha256,
                        json_path=json_path or None,
                        offset=offset,
                        max_bytes=max_bytes,
                    )
                )

            review_tools = [read_review_asset]
        messages = [
            {
                "role": "user",
                "content": prompt
                + "\nReturn the requested verdict JSON concisely; omit any preamble.",
            }
        ]
        attempt = 0
        while attempt < 2:
            if time.time() >= deadline:
                raise ValueError("Independent review deadline exhausted")
            options = {"tools_to_call_from": review_tools} if review_tools else {}
            response = llm.generate(messages, **options)
            if response.token_usage:
                emit(
                    "usage",
                    input_tokens=response.token_usage.input_tokens,
                    output_tokens=response.token_usage.output_tokens,
                )
            raw = getattr(response, "raw", None)
            choices = (
                raw.get("choices", []) if isinstance(raw, dict) else getattr(raw, "choices", [])
            )
            first = choices[0] if choices else None
            finish = (
                first.get("finish_reason")
                if isinstance(first, dict)
                else getattr(first, "finish_reason", None)
            )
            emit(
                "review_response",
                attempt=attempt + 1,
                finish_reason=finish,
                empty=not bool(response.content and response.content.strip()),
            )
            if response.tool_calls:
                if not review_tools:
                    raise ValueError("Independent reviewer attempted a tool call")
                calls = json.loads(response.model_dump_json())["tool_calls"]
                messages.append(dict(role="assistant", content=response.content, tool_calls=calls))
                for call in response.tool_calls:
                    try:
                        if call.function.name != "read_review_asset":
                            raise ValueError("Reviewer can only read recorded review assets")
                        arguments = call.function.arguments
                        if isinstance(arguments, str):
                            arguments = json.loads(arguments)
                        result = read_review_asset(**arguments)
                        emit("review_read", tool="read_review_asset", arguments=arguments)
                    except (ValueError, TypeError, KeyError, OSError) as error:
                        result = json.dumps(dict(error=str(error)))
                    messages.append(dict(role="tool", tool_call_id=call.id, content=result))
                continue
            if response.content and response.content.strip() and finish != "length":
                return response.content
            attempt += 1
        raise ValueError(
            "Independent reviewer returned empty or truncated output after two bounded attempts"
        )
    from .workspace_protocol import ProviderRequestFailure, agent_type, step_messages

    llm.abort_on_request_error = True

    action_limit = action_limit if action_limit is not None else config.get("action_limit")
    if action_limit is not None and (type(action_limit) is not int or action_limit < 1):
        raise ValueError("action_limit must be a positive integer or omitted")

    ToolCallingAgent = agent_type(native_tools=native_tools, checkpoint=session_dir is not None)

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
        max_steps=action_limit or sys.maxsize,
        return_full_result=True,
        verbosity_level=-1,
        step_callbacks=[step_event],
        instructions=(
            "You are Simjecture's research assistant. Work on the user's actual request. "
            "Distinguish observations, hypotheses and independently accepted findings. "
            "Use files and tools to do work, not just suggest commands. Never expose credentials. "
            "If you announce an action, perform it before ending the turn. Use final_answer "
            "for a completed answer, a concrete blocker, or an essential question, never "
            "merely a promise of future work. "
            "For interactive requests return after doing the requested task. For autonomous "
            "research follow the supplied research service guide and hand off for reviews. "
            "Only use draft_study when an autonomous investigation would serve the request. "
            "For interactive simulations, prefer run_simulation so the user can follow live "
            "progress while continuing the conversation. Files belong to this conversation; "
            "never place research results in /tmp. Use Markdown with LaTeX equations and "
            "fenced, language-labelled code. Link figures using relative project paths, e.g. "
            "![Description](figure.png), or simulation:<run-id>/figure.png for run outputs. "
            "For installation requests, read the relevant skill and deployment guide, inspect "
            "the required user source/hardware, then attempt the documented setup/build. "
            "Do not exhaustively scan Simjecture implementation or unrelated solver units "
            "before attempting a build. Inspect implementation only to diagnose a concrete "
            "tool/API error. Use the managed prerequisite installer from the guide. "
            "For installations and builds use run_command, then poll simulation_status until "
            "completion and verify the result. Never detach a process with nohup or & inside "
            "terminal: its child processes are cleaned up when that command ends. "
            "During extended work use progress_update for meaningful milestones, blockers "
            "and next actions. Do not expose private reasoning or invent progress percentages. "
            "Do not invent user inputs, results or tool installation success."
        ),
    )
    from .workspace_sessions import load_session, save_session

    session_root = (
        Path(session_dir)
        if session_dir is not None
        else (root.parent if workspace and project else None)
    )
    session_config = {**config, "model": model or config["model"]}
    session = load_session(session_root, session_config) if session_root is not None else {}
    history = session.get("history", [])
    llm.conversation_history = history
    llm.reasoning_records = session.get("reasoning_records", [])
    llm.reasoning_messages = session.get("reasoning_messages", {})
    previous_reasoning_messages = dict(llm.reasoning_messages)
    previous_reasoning = len(llm.reasoning_records)
    if session_root is not None:
        emit("session", resumed=bool(history), backend="builtin")
    transport_failed = False
    with contextlib.redirect_stdout(sys.stderr):
        # Tool/step events use the original stream while library chatter stays out of JSONL.
        try:
            result = agent.run(prompt)
        except ProviderRequestFailure as error:
            transport_failed = True
            raise error.cause from None
        finally:
            if session_root is not None:
                # Research turns already receive a fresh durable evidence brief.
                # Retain the preceding turn's exact calls/results for continuity,
                # without repeatedly appending full briefs for a day-long study.
                # Earlier evidence remains in files, receipts and the research journal.
                # A reconnect that fails before doing any work must not erase
                # the preceding turn's executed receipts or private reasoning.
                preserve_previous = transport_failed and not any(
                    getattr(step, "tool_calls", None) and getattr(step, "observations", None)
                    for step in agent.memory.steps
                )
                messages = list(history) if preserve_previous or session_dir is None else []
                from smolagents.memory import FinalAnswerStep

                for step in [] if preserve_previous else agent.memory.steps:
                    if isinstance(step, FinalAnswerStep):
                        messages.append({"role": "assistant", "content": str(step.output)})
                        continue
                    messages.extend(step_messages(step))
                save_session(
                    session_root,
                    session_config,
                    history=messages,
                    reasoning_records=(
                        llm.reasoning_records[previous_reasoning:]
                        if session_dir is not None and not preserve_previous
                        else llm.reasoning_records
                    ),
                    reasoning_messages=(
                        previous_reasoning_messages
                        if preserve_previous
                        else {}
                        if session_dir is not None
                        else llm.reasoning_messages
                    ),
                )
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
        "hours (0.01 to 168), completion_policy ('answer' or 'repair'). "
        "question must be a text string; success_criteria and constraints may be "
        "text strings or lists of text strings, joined with blank lines on import. "
        "Each text field must fit within 20,000 characters after joining. This prepares "
        "an editable brief; it does not launch a study. Existing project files are available. "
        "New studies automatically receive all available installed tools; the agent chooses "
        "the tools used for each experiment. Use instrument with its installed catalogue tool "
        "or variant ID only when a solver is an explicit scientific requirement. "
        "capability_directory='auto' exposes all available tools; a registered descriptor "
        "file/directory restricts them, and an empty string selects Python only. "
        "Omitted tool fields preserve the saved brief's access setting. "
        "Include machine_ids when using prepared remote workers."
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
            " For registered SSH machines, w.machines() lists saved connections and hardware; "
            "w.prepare_machine('id') installs the headless worker; w.check_machine('id') "
            "checks readiness. w.machine_command('id','shell command',timeout_seconds=60) "
            "runs a bounded operator-authorized setup command over its saved connection, "
            "returning a recorded result; credentials stay on the coordinator. "
            "w.configure_machine('id',{'config':{'capabilities':['/remote/descriptors']}}) "
            "registers that worker's instrument directories. "
            "Reprepare after changing configuration. "
            "These commands prepare machines; their outputs are not research evidence."
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
            "Save run-specific analysis and figures in that run's returned work_directory; "
            "keep cross-run reports and comparisons in the shared project files directory. "
            "Copied project inputs are not outputs of the new run. "
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
    parser.add_argument("--session-dir", type=Path)
    parser.add_argument("--action-limit", type=int)
    parser.add_argument("--review-root", type=Path)
    args = parser.parse_args(argv)
    config = read_provider(args.provider_config, api_only=args.judge)
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
                session_dir=args.session_dir,
                action_limit=args.action_limit,
                review_root=args.review_root,
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
