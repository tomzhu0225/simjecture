"""Dependency-free localhost HTTP server for the Simjecture web interface."""

from __future__ import annotations

import hmac
import ipaddress
import json
import mimetypes
import secrets
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from .application import (
    API_SCHEMA_VERSION,
    MAX_ARTIFACT_BYTES,
    SimjectureWebApplication,
    WebApplicationError,
)

STATIC_ROOT = Path(__file__).with_name("static")
MAX_REQUEST_BYTES = 64 * 1024
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data: blob:; connect-src 'self' data:; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
ARTIFACT_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"
    ),
    "Cross-Origin-Resource-Policy": "same-origin",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
DANGEROUS_INLINE_SUFFIXES = frozenset({".htm", ".html", ".js", ".mjs", ".xhtml", ".xml"})
STATIC_ASSETS = frozenset(
    {
        "index.html",
        "app.js",
        "markdown.js",
        "styles.css",
        "interface.css",
        "study-navigation.js",
        "brand/simjecture-lockup-light.svg",
        "brand/simjecture-lockup-dark.svg",
        "brand/favicon.svg",
        "brand/favicon.ico",
        "workspace.html",
        "workspace.js",
        "workspace-theme.js",
        "workspace-panels.js",
        "workspace.css",
        "workspace-components.js",
        "workspace-rich.js",
        "workspace-monitor.js",
        "workspace-benchmarks.js",
        "vendor/highlight-11.11.1.min.js",
        "vendor/highlight-github-dark.css",
        "vendor/dagre-2.0.0.min.js",
        "vendor/dompurify-3.4.14.min.js",
        "vendor/katex-0.18.4.min.js",
        "vendor/katex-auto-render-0.18.4.min.js",
        "vendor/marked-18.0.10.umd.js",
    }
)
STATIC_ASSETS = STATIC_ASSETS | frozenset(
    p.relative_to(STATIC_ROOT).as_posix()
    for p in (STATIC_ROOT / "vendor/webawesome-3.14.0").rglob("*")
    if p.is_file() and p.suffix in {".js", ".css", ".svg"}
)


class SimjectureHTTPServer(ThreadingHTTPServer):
    """HTTP server carrying one application and an unguessable control token."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        application: SimjectureWebApplication,
        *,
        verbose: bool = False,
    ) -> None:
        self.application = application
        self.control_token = secrets.token_urlsafe(32)
        self.verbose = verbose
        self._handoff_at = 0
        self._handoff_thread = None
        self._machine_poll_at = 0
        self._machine_poll_thread = None
        super().__init__(address, SimjectureRequestHandler)

    def service_actions(self):
        from ..machine_availability import POLL_SECONDS

        if time.monotonic() >= self._machine_poll_at and not (
            self._machine_poll_thread and self._machine_poll_thread.is_alive()
        ):
            self._machine_poll_at = time.monotonic() + POLL_SECONDS
            self._machine_poll_thread = threading.Thread(
                target=self.application.workspace.poll_machine_availability, daemon=True
            )
            self._machine_poll_thread.start()
        if not self.application.allow_mutations or time.monotonic() < self._handoff_at:
            return
        if self._handoff_thread and self._handoff_thread.is_alive():
            return
        self._handoff_at = time.monotonic() + 5
        self._handoff_thread = threading.Thread(
            target=self.application.workspace.deliver_study_reports, daemon=True
        )
        self._handoff_thread.start()


class SimjectureRequestHandler(BaseHTTPRequestHandler):
    """Serve the static client and the narrow local campaign API."""

    server: SimjectureHTTPServer
    protocol_version = "HTTP/1.1"
    server_version = "Simjecture/0.2.2"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        parsed = urlsplit(self.path)
        try:
            if parsed.path.startswith("/api/workspace/"):
                self._workspace_get(parsed)
                return
            if parsed.path == "/api/bootstrap":
                payload = self.server.application.bootstrap()
                payload["control_token"] = self.server.control_token
                self._json(payload)
                return
            if parsed.path == "/api/campaigns":
                self._json(
                    {
                        "schema_version": API_SCHEMA_VERSION,
                        "campaigns": self.server.application.campaigns(),
                    }
                )
                return
            if parsed.path == "/api/snapshot":
                token = self._one_query_value(parsed.query, "campaign")
                self._json(self.server.application.campaign_snapshot(token))
                return
            if parsed.path == "/api/execution":
                query = parse_qs(parsed.query, keep_blank_values=True)
                token = self._one_value(query, "campaign")
                raw_iteration = self._one_value(query, "iteration")
                try:
                    iteration = int(raw_iteration)
                except ValueError as error:
                    raise WebApplicationError(
                        "execution iteration must be an integer",
                        status=400,
                    ) from error
                self._json(self.server.application.execution(token, iteration))
                return
            if parsed.path == "/api/artifact":
                query = parse_qs(parsed.query, keep_blank_values=True)
                token = self._one_value(query, "campaign")
                relative = self._one_value(query, "path")
                self._artifact(token, relative)
                return
            if parsed.path.startswith("/api/"):
                raise WebApplicationError("API endpoint not found", status=404)
            self._static(parsed.path)
        except WebApplicationError as error:
            self.close_connection = True
            self._error(error.status, str(error))
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self._error(500, "local web interface failed to process the request")

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        parsed = urlsplit(self.path)
        try:
            self._authorize_mutation()
            payload = self._read_json_body()
            if parsed.path.startswith("/api/workspace/"):
                self.server.application._require_mutations()
                self._workspace_post(parsed, payload)
                return
            if parsed.path == "/api/campaigns":
                result = self.server.application.create_campaign(payload)
                self._json(result, status=HTTPStatus.CREATED)
                return
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) == 5 and parts[:2] == ["api", "campaigns"] and parts[3] == "control":
                result = self.server.application.control(parts[2], parts[4])
                self._json(result)
                return
            raise WebApplicationError("API endpoint not found", status=404)
        except WebApplicationError as error:
            self.close_connection = True
            self._error(error.status, str(error))
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self._error(500, "local web interface failed to process the request")

    def log_message(self, format: str, *args: Any) -> None:
        if self.server.verbose:
            super().log_message(format, *args)

    def _authorize_mutation(self) -> None:
        supplied = self.headers.get("X-Simjecture-Token", "")
        if not hmac.compare_digest(supplied, self.server.control_token):
            raise WebApplicationError("invalid control token", status=403)
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise WebApplicationError("mutating requests require application/json", status=415)
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        if origin and host and origin != f"http://{host}":
            raise WebApplicationError("cross-origin control request rejected", status=403)

    def _read_json_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError as error:
            raise WebApplicationError("invalid content length", status=400) from error
        endpoint = urlsplit(self.path).path
        maximum = (
            96 * 1024**2
            if endpoint == "/api/workspace/upload"
            else 4 * 1024**2
            if endpoint == "/api/workspace/import-benchmark-reports"
            else MAX_REQUEST_BYTES
        )
        if length <= 0 or length > maximum:
            raise WebApplicationError("request body is empty or too large", status=413)
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WebApplicationError("request body is not valid JSON", status=400) from error
        if not isinstance(payload, dict):
            raise WebApplicationError("request body must be a JSON object", status=400)
        return payload

    def _static(self, request_path: str) -> None:
        if request_path in {"", "/"}:
            relative = (
                "index.html" if self.server.application.registry.initial_token else "workspace.html"
            )
        elif request_path == "/workspace":
            relative = "workspace.html"
        elif request_path in {"/favicon.svg", "/favicon.ico"}:
            relative = "brand/" + request_path.removeprefix("/")
        elif request_path.startswith("/assets/"):
            relative = request_path.removeprefix("/assets/")
        else:
            relative = "index.html"
        if relative not in STATIC_ASSETS:
            raise WebApplicationError("static resource not found", status=404)
        path = STATIC_ROOT / relative
        if not path.is_file():
            raise WebApplicationError("web assets are not installed", status=500)
        content_type = {
            ".css": "text/css; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }.get(path.suffix, "application/octet-stream")
        body = path.read_bytes()
        self._begin(HTTPStatus.OK, content_type, len(body), cache="no-cache")
        self.wfile.write(body)

    def _workspace_get(self, parsed):
        workspace = self.server.application.workspace
        query = parse_qs(parsed.query)
        endpoint = parsed.path.removeprefix("/api/workspace/")
        try:
            if endpoint == "bootstrap":
                self._json(
                    dict(
                        settings=workspace.settings(),
                        projects=workspace.projects(),
                        control_token=self.server.control_token,
                        allow_mutations=self.server.application.allow_mutations,
                    )
                )
            elif endpoint == "project":
                self._json(workspace.project(self._one_value(query, "id")))
            elif endpoint == "simulation":
                self._json(
                    workspace.simulation(
                        self._one_value(query, "id"), self._one_value(query, "simulation")
                    )
                )
            elif endpoint == "tools":
                self._json(workspace.catalogue())
            elif endpoint == "benchmarks":
                self._json(workspace.benchmark_catalogue())
            elif endpoint == "machines":
                self._json(workspace.machines())
            elif endpoint == "machine-jobs":
                self._json(workspace.machine_jobs(self._one_value(query, "id")))
            elif endpoint == "machine":
                from ..execution import probe_execution_backend

                self._json(probe_execution_backend("bubblewrap"))
            elif endpoint == "continuation-preview":
                from ..research_continuation import preview

                root = self.server.application.registry.resolve(self._one_value(query, "id"))
                self._json(preview(root))
            elif endpoint == "study":
                from ..research_continuation import steering
                from ..study_status import study_status
                from .workspace import load

                app = self.server.application
                token = self._one_value(query, "id")
                root = app.registry.resolve(token)
                snapshot = app.campaign_snapshot(token)
                result = root / "research" / "RESULTS.md"
                status = study_status(root)
                self._json(
                    dict(
                        snapshot=snapshot,
                        live={
                            k: status[k]
                            for k in (
                                "status",
                                "activity",
                                "remaining",
                                "elapsed",
                                "backend",
                                "model",
                                "mode",
                                "provider_attention",
                                "provider_wait_seconds",
                                "usage",
                                "usage_details",
                                "instrument_requirement",
                            )
                        },
                        steering=steering(root),
                        continuation=status["manifest"].get("continuation"),
                        report=load(root / "research_report.json") | {"status": status["status"]},
                        results=result.read_text()[:100000]
                        if result.is_file()
                        and not result.is_symlink()
                        and result.resolve().is_relative_to(root)
                        else "",
                    )
                )
            elif endpoint in {"file", "preview", "simulation-file"}:
                from ..workspace_agent import contained

                project = workspace.directory(self._one_value(query, "id"))
                root = project / "files"
                if endpoint == "simulation-file":
                    from .jobs import read, resolve

                    job = resolve(project, self._one_value(query, "simulation"))
                    root = (
                        project / "files"
                        if read(job / "request.json").get("kind") == "command"
                        else job / "workspace"
                    )
                if root.is_symlink() or not root.resolve().is_relative_to(project.resolve()):
                    raise ValueError("Invalid artifact directory")
                path = contained(root, self._one_value(query, "path"))
                if not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
                    raise ValueError("File is missing or exceeds 64 MB")
                body = path.read_bytes()
                preview = endpoint == "preview" or query.get("preview") == ["1"]
                if preview and path.suffix.lower() not in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".webp",
                    ".svg",
                }:
                    raise ValueError("Only saved figures can be previewed inline")
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    (mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                    if preview
                    else "application/octet-stream",
                )
                self.send_header(
                    "Content-Disposition",
                    ("inline" if preview else "attachment")
                    + "; filename*=UTF-8''"
                    + quote(path.name),
                )
                self.send_header("Content-Length", str(len(body)))
                for key, value in ARTIFACT_SECURITY_HEADERS.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)
            else:
                raise WebApplicationError("Workspace endpoint not found", status=404)
        except (ValueError, OSError) as error:
            raise WebApplicationError(str(error), status=400) from error

    def _workspace_post(self, parsed, payload):
        workspace = self.server.application.workspace
        endpoint = parsed.path.removeprefix("/api/workspace/")
        try:
            if endpoint == "settings":
                result = workspace.save_settings(payload)
            elif endpoint == "test":
                result = workspace.test_connection()
            elif endpoint == "api-settings":
                result = workspace.save_api(payload)
            elif endpoint == "models":
                result = workspace.models(payload.get("backend"))
            elif endpoint == "agent":
                result = workspace.select_agent(payload.get("project"), payload)
            elif endpoint == "explain-study":
                result = workspace.queue_study_report(
                    payload.get("project"), payload.get("campaign")
                )
            elif endpoint == "prepare-continuation":
                result = workspace.prepare_continuation(payload, self.server.application)
            elif endpoint == "steer-study":
                from ..research_continuation import submit

                root = self.server.application.registry.resolve(payload.get("campaign"))
                result = submit(root, payload.get("message"), key=payload.get("request_key"))
            elif endpoint == "new-study":
                result = workspace.new_study(payload.get("project"))
            elif endpoint == "prepare":
                result = workspace.prepare(payload.get("project"), payload)
            elif endpoint == "simulations":
                result = workspace.start_simulation(payload.get("project"), payload)
            elif endpoint == "stop-simulation":
                result = workspace.stop_simulation(
                    payload.get("project"), payload.get("simulation")
                )
            elif endpoint == "delete-project":
                result = workspace.delete_project(payload.get("project"), payload)
            elif endpoint == "projects":
                result = workspace.create(payload)
            elif endpoint == "prepare-benchmark":
                result = workspace.prepare_benchmark(payload)
            elif endpoint == "grade-benchmark":
                result = workspace.grade_benchmark(payload)
            elif endpoint == "import-benchmark-reports":
                result = workspace.import_benchmark_reports(payload)
            elif endpoint == "start-benchmark-campaign":
                result = workspace.start_benchmark_campaign(payload)
            elif endpoint == "save-machine":
                result = workspace.save_machine(payload)
                self.server._machine_poll_at = 0
            elif endpoint == "prepare-machine":
                result = workspace.prepare_machine(payload.get("id"))
                self.server._machine_poll_at = 0
            elif endpoint == "check-machine":
                result = workspace.check_machine(payload.get("id"))
            elif endpoint == "refresh-machine":
                result = workspace.refresh_machine_availability(payload.get("id"))
            elif endpoint == "prepare-machine-chat":
                result = workspace.prepare_machine_chat(payload)
            elif endpoint == "cancel-machine-job":
                result = workspace.cancel_machine_job(payload.get("id"), payload.get("job"))
            elif endpoint == "fetch-remote-artifact":
                from ..research_service import ResearchService

                root = self.server.application.registry.resolve(payload.get("campaign"))
                result = ResearchService(root).fetch_remote(
                    payload.get("experiment"), payload.get("path")
                )
            elif endpoint == "message":
                result = workspace.send(payload.get("project"), payload)
            elif endpoint == "stop":
                result = workspace.stop(payload.get("project"))
            elif endpoint == "brief":
                result = workspace.save_brief(payload.get("project"), payload)
            elif endpoint == "upload":
                result = workspace.upload(payload.get("project"), payload)
            elif endpoint == "install":
                result = workspace.start_install(payload)
            elif endpoint == "tool-demo":
                result = workspace.run_tool_demo(payload)
            elif endpoint == "register-tool":
                result = workspace.register_tool(payload)
            elif endpoint == "launch":
                result = workspace.launch(payload.get("project"), payload, self.server.application)
            else:
                raise WebApplicationError("Workspace endpoint not found", status=404)
            self._json(result)
        except (ValueError, OSError, TypeError) as error:
            from ..workspace_agent import public_error
            from .workspace import load

            raise WebApplicationError(
                public_error(error, load(workspace.settings_path)), status=400
            ) from error

    def _artifact(self, token: str, relative: str) -> None:
        resource = self.server.application.artifact(token, relative)
        filename = quote(resource.path.name, safe="")
        disposition = (
            "attachment" if resource.path.suffix.lower() in DANGEROUS_INLINE_SUFFIXES else "inline"
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", resource.content_type)
        self.send_header("Content-Length", str(resource.size))
        self.send_header(
            "Content-Disposition",
            f"{disposition}; filename*=UTF-8''{filename}",
        )
        self.send_header("Cache-Control", "no-store")
        for key, value in ARTIFACT_SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
        with resource.path.open("rb") as stream:
            while chunk := stream.read(64 * 1024):
                self.wfile.write(chunk)

    def _json(self, payload: Any, *, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._begin(status, "application/json; charset=utf-8", len(body), cache="no-store")
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message, "status": status}, status=status)

    def _begin(self, status: int, content_type: str, length: int, *, cache: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", cache)
        if self.close_connection:
            self.send_header("Connection", "close")
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def _one_query_value(self, query: str, name: str) -> str:
        return self._one_value(parse_qs(query, keep_blank_values=True), name)

    @staticmethod
    def _one_value(query: dict[str, list[str]], name: str) -> str:
        values = query.get(name)
        if not values or len(values) != 1 or not values[0]:
            raise WebApplicationError(f"query parameter {name} is required", status=400)
        return values[0]


def create_server(
    application: SimjectureWebApplication,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    verbose: bool = False,
) -> SimjectureHTTPServer:
    _validate_loopback(host)
    if not 0 <= port <= 65_535:
        raise ValueError("port must be between 0 and 65535")
    return SimjectureHTTPServer((host, port), application, verbose=verbose)


def serve_web(
    *,
    run_directory: str | Path | None = None,
    scan_roots: tuple[str | Path, ...] = (),
    runs_root: str | Path = "artifacts",
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    read_only: bool = False,
    verbose: bool = False,
    engine: str = "dsh",
) -> None:
    application = SimjectureWebApplication(
        initial_run=run_directory,
        scan_roots=scan_roots,
        runs_root=runs_root,
        allow_mutations=not read_only,
        default_engine=engine,
    )
    server = create_server(application, host=host, port=port, verbose=verbose)
    actual_port = server.server_address[1]
    url = f"http://{host}:{actual_port}/"
    print(f"Simjecture web interface: {url}", flush=True)
    print("Press Ctrl-C to stop the local interface; campaigns continue independently.", flush=True)
    if open_browser:
        threading.Timer(0.15, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def run_web(**kwargs: Any) -> int:
    serve_web(**kwargs)
    return 0


def _validate_loopback(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ValueError("Simjecture web sessions bind to localhost only") from error
    if not address.is_loopback:
        raise ValueError("Simjecture web sessions bind to localhost only")


__all__ = [
    "SimjectureHTTPServer",
    "create_server",
    "run_web",
    "serve_web",
]
