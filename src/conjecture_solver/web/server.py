"""Dependency-free localhost HTTP server for the Simjecture web interface."""

from __future__ import annotations

import hmac
import ipaddress
import json
import secrets
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

from .application import SimjectureWebApplication, WebApplicationError

STATIC_ROOT = Path(__file__).with_name("static")
MAX_REQUEST_BYTES = 64 * 1024
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; "
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
        super().__init__(address, SimjectureRequestHandler)


class SimjectureRequestHandler(BaseHTTPRequestHandler):
    """Serve the static client and the narrow local campaign API."""

    server: SimjectureHTTPServer
    protocol_version = "HTTP/1.1"
    server_version = "Simjecture/0.1.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        parsed = urlsplit(self.path)
        try:
            if parsed.path == "/api/bootstrap":
                payload = self.server.application.bootstrap()
                payload["control_token"] = self.server.control_token
                self._json(payload)
                return
            if parsed.path == "/api/campaigns":
                self._json(
                    {
                        "schema_version": "0.1.0",
                        "campaigns": self.server.application.campaigns(),
                    }
                )
                return
            if parsed.path == "/api/snapshot":
                token = self._one_query_value(parsed.query, "campaign")
                self._json(self.server.application.campaign_snapshot(token))
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
        if length <= 0 or length > MAX_REQUEST_BYTES:
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
            relative = "index.html"
        elif request_path.startswith("/assets/"):
            relative = request_path.removeprefix("/assets/")
        else:
            relative = "index.html"
        if relative not in {"index.html", "app.js", "styles.css"}:
            raise WebApplicationError("static resource not found", status=404)
        path = STATIC_ROOT / relative
        if not path.is_file():
            raise WebApplicationError("web assets are not installed", status=500)
        content_type = {
            ".css": "text/css; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(path.suffix, "application/octet-stream")
        body = path.read_bytes()
        self._begin(HTTPStatus.OK, content_type, len(body), cache="no-cache")
        self.wfile.write(body)

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
) -> None:
    application = SimjectureWebApplication(
        initial_run=run_directory,
        scan_roots=scan_roots,
        runs_root=runs_root,
        allow_mutations=not read_only,
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
        raise ValueError("v0.1.1 web sessions bind to localhost only") from error
    if not address.is_loopback:
        raise ValueError("v0.1.1 web sessions bind to localhost only")


__all__ = [
    "SimjectureHTTPServer",
    "create_server",
    "run_web",
    "serve_web",
]
