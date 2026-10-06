"""Internet-facing trial API. Never proxies the trusted operator workspace."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import fcntl
import hmac
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from ..mvp_launch import read_process_identity
from .lifecycle import GuestLifecycle
from .native import OUTPUTS
from .oauth import OAUTH_COOKIE, GitHubLogin
from .store import CapacityUnavailable, LimitReached, Store
from .worker import DEFAULT_HYPOTHESIS
from .workspace import HostedWorkspace

STATIC = Path(__file__).with_name("static")
WORKSPACE_STATIC = Path(__file__).resolve().parents[1] / "web/static"
COOKIE = "simjecture_visitor"
HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self' data:; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cache-Control": "no-store",
}


class Dispatcher:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.children = {}
        self.stopping = {}

    def tick(self):
        for pid, child in list(self.children.items()):
            if child.poll() is not None:
                del self.children[pid]
        with self.store.connect() as db:
            running = [dict(row) for row in db.execute("SELECT * FROM jobs WHERE status='running'")]
        for job in running:
            identity = read_process_identity(job["pid"]) if job["pid"] else None
            expected = json.loads(job["process_identity"]) if job["process_identity"] else None
            actual = identity.model_dump(mode="json") if identity else None
            alive = bool(actual and expected and actual["starttime"] == expected["starttime"])
            if not alive and time.time() - job["started"] > 5:
                changed = self.store.update(
                    job["id"],
                    expected_status="running",
                    status="cancelled" if job["cancel_requested"] else "interrupted",
                    finished=time.time(),
                    summary="Worker interrupted. Saved evidence remains available.",
                )
                if changed:
                    self.store.event(
                        job["id"],
                        "interrupted",
                        {"message": "Worker stopped before a terminal receipt"},
                    )
            elif alive and (
                job["cancel_requested"]
                or (job["deadline"] is not None and time.time() > job["deadline"] + 5)
            ):
                if job["pid"] not in self.stopping:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(job["pid"], signal.SIGTERM)
                    self.stopping[job["pid"]] = time.time()
                elif time.time() - self.stopping[job["pid"]] > 15:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(job["pid"], signal.SIGKILL)
        GuestLifecycle(self.store, lambda: self.settings).tick()
        if not self.store.capacity_available():
            return
        job = self.store.claim(max_active=self.settings.get("max_active_jobs", 2))
        if not job:
            return
        directory = self.store.root / "jobs" / job["id"]
        directory.mkdir(parents=True, mode=0o700)
        try:
            with (directory / "worker.log").open("a") as log:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "conjecture_solver.public.worker",
                        "--root",
                        str(self.store.root),
                        "--job",
                        job["id"],
                    ],
                    stdout=log,
                    stderr=log,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    env=dict(
                        os.environ,
                        OMP_NUM_THREADS="1",
                        OPENBLAS_NUM_THREADS="1",
                        MKL_NUM_THREADS="1",
                        MPLCONFIGDIR=str(directory / ".mpl"),
                    ),
                )
            self.children[child.pid] = child
            identity = read_process_identity(child.pid)
            self.store.update(
                job["id"],
                pid=child.pid,
                process_identity=identity.model_dump_json() if identity else None,
            )
        except Exception:
            self.store.update(
                job["id"],
                status="failed",
                finished=time.time(),
                summary="Unable to start trial worker",
            )


def create_app(root, *, dispatch=True, secure_cookies=True):
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
        from pydantic import BaseModel, ConfigDict, Field
    except ImportError as error:
        raise RuntimeError(
            "Install the public server extra: pip install 'simjecture[public]'"
        ) from error

    store = Store(Path(root))

    def settings():
        path = store.root / "settings.json"
        return json.loads(path.read_text()) if path.exists() else {}

    def ready():
        path = store.root / "provider.json"
        if not path.is_file() or path.is_symlink():
            return False
        p = json.loads(path.read_text())
        return bool(
            p.get("api_key")
            and p.get("model")
            and p.get("base_url")
            and p.get("public_enabled") is True
        )

    dispatcher = Dispatcher(store, settings())
    login = GitHubLogin(store, settings)
    workspace = HostedWorkspace(store, settings, login)
    lifecycle = GuestLifecycle(store, settings)

    @asynccontextmanager
    async def lifespan(app):
        lock = (store.root / ".dispatcher.lock").open("a")
        task = None
        try:
            if dispatch:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                login.start_inlet()

                async def poll():
                    while True:
                        try:
                            await asyncio.to_thread(dispatcher.tick)
                        except Exception:
                            # A failed poll must not kill the durable admission service.
                            import logging

                            logging.getLogger("simjecture.public").exception(
                                "Admission poll failed"
                            )
                        await asyncio.sleep(1)

                task = asyncio.create_task(poll())
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            lock.close()
            login.close()

    app = FastAPI(
        title="Simjecture public trials",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.store = store
    app.state.dispatcher = dispatcher
    app.state.login = login
    app.state.workspace = workspace

    @app.middleware("http")
    async def guards(request, call_next):
        if request.method not in {"GET", "HEAD", "POST"}:
            return JSONResponse({"detail": "Method not allowed"}, status_code=405, headers=HEADERS)
        configured = settings().get("public_origin")
        canonical = urlsplit(configured or "")
        if (
            canonical.hostname
            and request.url.hostname == "www." + canonical.hostname
            and request.method in {"GET", "HEAD"}
        ):
            target = configured.rstrip("/") + request.url.path
            if request.url.query:
                target += "?" + request.url.query
            return RedirectResponse(target, status_code=308, headers=HEADERS)
        if request.method == "POST":
            if "application/json" not in request.headers.get("content-type", ""):
                return JSONResponse({"detail": "JSON required"}, status_code=415, headers=HEADERS)
            origin = request.headers.get("origin")
            expected = configured or str(request.base_url).rstrip("/")
            if not origin or not hmac.compare_digest(origin, expected):
                return JSONResponse(
                    {"detail": "Same-origin request required"}, status_code=403, headers=HEADERS
                )
            maximum = 16384
            if request.url.path == "/api/workspace/upload":
                row = store.visitor(request.cookies.get(COOKIE))
                if not row or not store.account(row["id"]):
                    return JSONResponse(
                        {"detail": "Sign in to add files"}, status_code=403, headers=HEADERS
                    )
                if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf"]):
                    return JSONResponse(
                        {"detail": "Invalid session control token"},
                        status_code=403,
                        headers=HEADERS,
                    )
                maximum = 90 * 1024**2
            try:
                if int(request.headers.get("content-length", "0")) > maximum:
                    raise ValueError()
            except ValueError:
                return JSONResponse(
                    {"detail": "Request too large"}, status_code=413, headers=HEADERS
                )
            # Bound chunked bodies too, before FastAPI/Pydantic parses them.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > maximum:
                    return JSONResponse(
                        {"detail": "Request too large"}, status_code=413, headers=HEADERS
                    )
            request._body = bytes(body)
        try:
            response = await call_next(request)
        except CapacityUnavailable as error:
            response = JSONResponse({"detail": str(error)}, status_code=503)
        except LimitReached as error:
            response = JSONResponse({"detail": str(error)}, status_code=429)
        for name, value in HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    # Annotations are assigned explicitly because these optional types are local imports.
    def visitor(request, *, mutation=False):
        row = store.visitor(request.cookies.get(COOKIE))
        if not row:
            raise HTTPException(401, "Start a visitor session first")
        if mutation and not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), row["csrf"]
        ):
            raise HTTPException(403, "Invalid session control token")
        return row

    def public_job(job):
        return {
            k: v
            for k, v in job.items()
            if k not in {"owner", "pid", "process_identity", "quota_key"}
        }

    def owned(request, identifier):
        row = store.job(identifier, owner=visitor(request)["id"])
        if not row:
            raise HTTPException(404, "Investigation not found")
        return row

    class SessionInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        invitation: str = Field(default="", max_length=128)

    class JobInput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        mode: str = Field(pattern="^(research|reproduce)$")
        hypothesis: str = Field(default=DEFAULT_HYPOTHESIS, min_length=16, max_length=4000)

    async def health():
        return {
            "status": "ok",
            "service": "simjecture-public",
            "execution_policy": "trusted-templates",
        }

    async def bootstrap(request):
        p = settings()
        row = store.visitor(request.cookies.get(COOKIE))
        rows = workspace.campaigns(row["id"]) if row else []
        return {
            "research_ready": ready(),
            "default_hypothesis": DEFAULT_HYPOTHESIS,
            "wall_seconds": p.get("wall_seconds", 600),
            "max_active_jobs": p.get("max_active_jobs", 2),
            "experiments_per_job": p.get("experiments_per_job", 6),
            "daily_jobs": p.get("daily_jobs", 2),
            "invitation_required": bool(p.get("invitation")),
            "execution_policy": "trusted-templates",
            "allow_mutations": False,
            "modes": ["minimal"],
            "selected_campaign": rows[0]["id"] if rows else None,
            "campaigns": rows,
        }

    async def new_session(request, payload):
        p = settings()
        if p.get("invitation") and not hmac.compare_digest(payload.invitation, p["invitation"]):
            raise HTTPException(403, "A valid preview invitation is required")
        old = store.visitor(request.cookies.get(COOKIE))
        if old:
            return {"csrf_token": old["csrf"]}
        # Forwarded client addresses are accepted only from the local tunnel connector.
        ip = request.client.host if request.client else "unix-connector"
        if ip in {"127.0.0.1", "::1", "unix-connector"}:
            ip = request.headers.get("cf-connecting-ip", ip)
        token, row = store.create_visitor(ip)
        response = JSONResponse({"csrf_token": row["csrf"]})
        response.set_cookie(
            COOKIE,
            token,
            max_age=30 * 86400,
            httponly=True,
            secure=secure_cookies,
            samesite="strict",
        )
        return response

    async def me(request):
        row = visitor(request)
        return {
            "csrf_token": row["csrf"],
            "jobs": [public_job(j) for j in store.jobs(row["id"])],
            "hosting": workspace.hosting(row["id"]),
        }

    async def enqueue(request, payload):
        row = visitor(request, mutation=True)
        if payload.mode == "research" and not ready():
            raise HTTPException(
                503,
                "AI investigations await an application-eligible API connection. "
                "Numerical demos are available.",
            )
        p = settings()
        # No job may silently enter the queue after the global disk budget is exhausted.
        import shutil

        if shutil.disk_usage(store.root).free < p.get("minimum_free_bytes", 1024**3):
            raise HTTPException(503, "Trial storage is temporarily full")
        hypothesis = payload.hypothesis if payload.mode == "research" else DEFAULT_HYPOTHESIS
        job = store.enqueue(
            row["id"],
            payload.mode,
            hypothesis,
            wall_seconds=0
            if workspace.is_owner(row["id"])
            else min(1800, p.get("wall_seconds", 600)),
            daily_jobs=p.get("daily_jobs", 2),
            max_queue=p.get("max_queue", 20),
            limits=workspace.limits(row["id"]),
            privileged=workspace.is_owner(row["id"]),
        )
        return public_job(job)

    async def detail(request, identifier: str):
        job = owned(request, identifier)
        return public_job(job)

    async def events(request, identifier: str, after: int = 0):
        owned(request, identifier)
        return {"events": store.events(identifier, after=max(0, after))}

    async def cancel(request, identifier: str):
        row = visitor(request, mutation=True)
        job = store.cancel(identifier, row["id"])
        if not job:
            raise HTTPException(404, "Investigation not found")
        return public_job(job)

    async def heartbeat(request, payload: dict):
        row = visitor(request, mutation=True)
        if set(payload) != {"lease"}:
            raise HTTPException(400, "Invalid page lease")
        return lifecycle.lease(row["id"], payload["lease"])

    async def leave(request, payload: dict):
        row = visitor(request)
        if (
            set(payload) != {"lease", "csrf"}
            or not isinstance(payload["csrf"], str)
            or not hmac.compare_digest(payload["csrf"], row["csrf"])
        ):
            raise HTTPException(403, "Invalid session control token")
        return lifecycle.lease(row["id"], payload["lease"], leaving=True)

    async def artifacts(request, identifier: str):
        owned(request, identifier)
        from ..research_service import ResearchService

        directory = store.root / "jobs" / identifier / "study"
        if not (directory / "research.json").exists():
            return {"artifacts": []}
        service = ResearchService(directory)
        files = []
        for experiment in service._all("experiments"):
            for name, meta in experiment.get("artifacts", {}).items():
                if name not in OUTPUTS and not name.startswith("generated/"):
                    continue
                files.append({"experiment": experiment["id"], "name": name, **meta})
        return {"artifacts": files}

    async def download(request, identifier: str, experiment: str, name: str):
        job = owned(request, identifier)
        from ..research_service import ResearchService, sha

        directory = store.root / "jobs" / identifier / "study"
        if name not in OUTPUTS and not name.startswith("generated/"):
            raise HTTPException(404, "Artifact not found")
        try:
            service = ResearchService(directory)
            record = service._read("experiments", experiment)
            path = workspace.artifact(
                identifier, f"experiments/{experiment}/workspace/{name}", job["owner"]
            )
            meta = record.get("artifacts", {}).get(name)
            if not meta or path.is_symlink() or not path.is_file() or sha(path) != meta["sha256"]:
                raise ValueError()
        except (ValueError, OSError, LookupError):
            raise HTTPException(404, "Verified artifact not found") from None
        return FileResponse(
            path,
            filename=path.name,
            media_type="image/png"
            if name.endswith(".png")
            else "application/zip"
            if name.endswith(".zip")
            else "application/json",
            headers=HEADERS,
        )

    # Register after annotating to avoid resolving postponed annotations against missing globals.
    for endpoint in (
        new_session,
        me,
        enqueue,
        detail,
        events,
        cancel,
        artifacts,
        download,
        heartbeat,
        leave,
    ):
        endpoint.__annotations__["request"] = Request
    new_session.__annotations__["payload"] = SessionInput
    bootstrap.__annotations__["request"] = Request
    enqueue.__annotations__["payload"] = JobInput
    app.add_api_route("/healthz", health, methods=["GET"])
    app.add_api_route("/api/bootstrap", bootstrap, methods=["GET"])
    app.add_api_route("/api/session", new_session, methods=["POST"])
    app.add_api_route("/api/session/heartbeat", heartbeat, methods=["POST"])
    app.add_api_route("/api/session/leave", leave, methods=["POST"])
    app.add_api_route("/api/me", me, methods=["GET"])
    app.add_api_route("/api/jobs", enqueue, methods=["POST"], status_code=202)
    app.add_api_route("/api/jobs/{identifier}", detail, methods=["GET"])
    app.add_api_route("/api/jobs/{identifier}/events", events, methods=["GET"])
    app.add_api_route("/api/jobs/{identifier}/cancel", cancel, methods=["POST"])
    app.add_api_route("/api/jobs/{identifier}/artifacts", artifacts, methods=["GET"])
    app.add_api_route(
        "/api/jobs/{identifier}/artifacts/{experiment}/{name:path}", download, methods=["GET"]
    )

    async def workspace_get(request, name: str):
        row = visitor(request)
        try:
            query = dict(request.query_params)
            if name in {"file", "preview", "simulation-file"}:
                p = workspace.require_project(query.get("id"), row["id"])
                if name == "simulation-file":
                    job_id, _, exp_id = query.get("simulation", "").partition(".")
                    job = workspace.require_job(job_id, row["id"])
                    if job["project"] != p["id"]:
                        raise LookupError("Simulation not found")
                    path = workspace.artifact(
                        job_id, f"experiments/{exp_id}/workspace/{query.get('path', '')}", row["id"]
                    )
                    return artifact_response(path, preview=query.get("preview") == "1")
                path = workspace.project_file(p["id"], query.get("path", ""), row["id"])
                return artifact_response(path, preview=name == "preview")
            return workspace.get(name, query, row["id"], row["csrf"])
        except PermissionError as error:
            raise HTTPException(403, str(error)) from None
        except LookupError as error:
            raise HTTPException(404, str(error)) from None
        except LimitReached:
            raise
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    async def workspace_post(request, name: str, payload: dict):
        row = visitor(request, mutation=True)
        if name in {"message", "prepare", "launch", "explain-study"} and not ready():
            raise HTTPException(503, "The shared agent connection is unavailable")
        try:
            return workspace.post(name, payload, row["id"])
        except PermissionError as error:
            raise HTTPException(403, str(error)) from None
        except LookupError as error:
            raise HTTPException(404, str(error)) from None
        except LimitReached:
            raise
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    async def campaign_control(request, identifier: str, action: str):
        row = visitor(request, mutation=True)
        if action != "cancel":
            raise HTTPException(403, "This control is managed by the host")
        if not store.cancel(identifier, row["id"]):
            raise HTTPException(404, "Study not found")
        return {"message": "Stop requested"}

    async def campaigns(request):
        row = visitor(request)
        return {"campaigns": workspace.campaigns(row["id"])}

    async def snapshot(request, campaign: str):
        row = visitor(request)
        try:
            job = workspace.require_job(campaign, row["id"])
            result = workspace.projection(job)
            if not result:
                raise LookupError("Study is queued")
            result["campaign"] = campaign
            return result
        except LookupError as error:
            raise HTTPException(404, str(error)) from None

    def artifact_response(path, *, preview=False):
        inline = preview and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        return FileResponse(
            path,
            filename=path.name,
            content_disposition_type="inline" if inline else "attachment",
            headers={**HEADERS, "Content-Security-Policy": "default-src 'none'; sandbox"},
        )

    async def artifact(request, campaign: str, path: str):
        row = visitor(request)
        try:
            return artifact_response(
                workspace.artifact(campaign, path, row["id"]),
                preview=request.query_params.get("preview") == "1",
            )
        except (LookupError, ValueError, OSError):
            raise HTTPException(404, "Artifact not found") from None

    async def auth_start(request):
        row = visitor(request)
        try:
            state, url = login.authorization(row["id"])
        except ValueError as error:
            raise HTTPException(503, str(error)) from None
        response = RedirectResponse(url, status_code=302)
        response.set_cookie(
            OAUTH_COOKIE,
            state,
            max_age=600,
            httponly=True,
            secure=secure_cookies,
            samesite="lax",
            path="/api/auth/github",
        )
        return response

    async def auth_callback(request, state: str = "", code: str = ""):
        try:
            token, row = await login.callback(state, request.cookies.get(OAUTH_COOKIE), code)
        except ValueError as error:
            raise HTTPException(400, str(error)) from None
        except Exception:
            raise HTTPException(503, "GitHub sign-in is temporarily unavailable") from None
        response = RedirectResponse("/workspace", status_code=303)
        response.set_cookie(
            COOKIE,
            token,
            max_age=30 * 86400,
            httponly=True,
            secure=secure_cookies,
            samesite="strict",
        )
        response.delete_cookie(OAUTH_COOKIE, path="/api/auth/github")
        return response

    async def logout(request):
        visitor(request, mutation=True)
        response = JSONResponse({"message": "Signed out"})
        response.delete_cookie(COOKIE)
        response.delete_cookie(OAUTH_COOKIE, path="/api/auth/github")
        return response

    avatar_cache = {}

    async def avatar(request):
        import httpx
        from fastapi.responses import Response

        row = visitor(request)
        account = store.account(row["id"])
        if not account:
            raise HTTPException(404, "No account image")
        identifier = str(int(account["github_id"]))
        cached = avatar_cache.get(identifier)
        if not cached or time.time() - cached[0] > 3600:
            try:
                async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                    response = await client.get(
                        f"https://avatars.githubusercontent.com/u/{identifier}?s=80",
                        headers={"User-Agent": "Simjecture"},
                    )
                kind = response.headers.get("content-type", "").split(";", 1)[0]
                if (
                    response.status_code != 200
                    or kind not in {"image/png", "image/jpeg", "image/webp"}
                    or len(response.content) > 256000
                ):
                    raise ValueError()
                cached = (time.time(), response.content, kind)
                avatar_cache[identifier] = cached
            except (httpx.HTTPError, ValueError):
                raise HTTPException(404, "Account image unavailable") from None
        return Response(cached[1], media_type=cached[2], headers=HEADERS)

    for endpoint in (
        workspace_get,
        workspace_post,
        campaign_control,
        campaigns,
        snapshot,
        artifact,
        auth_start,
        auth_callback,
        logout,
        avatar,
    ):
        endpoint.__annotations__["request"] = Request
    app.add_api_route("/api/workspace/{name}", workspace_get, methods=["GET"])
    app.add_api_route("/api/workspace/{name}", workspace_post, methods=["POST"])
    app.add_api_route(
        "/api/campaigns/{identifier}/control/{action}", campaign_control, methods=["POST"]
    )
    app.add_api_route("/api/campaigns", campaigns, methods=["GET"])
    app.add_api_route("/api/snapshot", snapshot, methods=["GET"])
    app.add_api_route("/api/artifact", artifact, methods=["GET"])
    app.add_api_route("/api/auth/github/start", auth_start, methods=["GET"])
    app.add_api_route("/api/auth/github/callback", auth_callback, methods=["GET"])
    app.add_api_route("/api/auth/logout", logout, methods=["POST"])
    app.add_api_route("/api/auth/avatar", avatar, methods=["GET"])

    async def introduction():
        return FileResponse(STATIC / "index.html", headers=HEADERS)

    async def public_asset(name: str):
        if name not in {"app.js", "styles.css", "logo.svg"}:
            raise HTTPException(404, "Not found")
        return FileResponse(STATIC / name, headers=HEADERS)

    async def workspace_index():
        from fastapi.responses import HTMLResponse

        html = (WORKSPACE_STATIC / "workspace.html").read_text()
        html = html.replace(
            "<head>",
            '<head><meta name="simjecture-hosted" content="true" />'
            '<script src="/assets/hosted-session.js" defer></script>',
        )
        return HTMLResponse(html, headers=HEADERS)

    async def monitor_index():
        from fastapi.responses import HTMLResponse

        html = (
            (WORKSPACE_STATIC / "index.html")
            .read_text()
            .replace(
                "<head>",
                '<head><meta name="simjecture-hosted" content="true" />'
                '<script src="/assets/hosted-session.js" defer></script>',
            )
        )
        return HTMLResponse(html, headers=HEADERS)

    async def asset(name: str):
        if name == "hosted.css":
            return FileResponse(STATIC / name, headers=HEADERS)
        path = WORKSPACE_STATIC / name
        try:
            path.resolve().relative_to(WORKSPACE_STATIC.resolve())
        except ValueError:
            raise HTTPException(404, "Not found") from None
        if (
            not path.is_file()
            or path.is_symlink()
            or path.suffix not in {".js", ".css", ".svg", ".woff", ".woff2", ".png", ".ico"}
        ):
            raise HTTPException(404, "Not found")
        return FileResponse(path, headers=HEADERS)

    async def favicon():
        return FileResponse(WORKSPACE_STATIC / "brand/favicon.svg", headers=HEADERS)

    async def favicon_ico():
        return FileResponse(WORKSPACE_STATIC / "brand/favicon.ico", headers=HEADERS)

    app.add_api_route("/", workspace_index, methods=["GET"])
    app.add_api_route("/about", introduction, methods=["GET"])
    app.add_api_route("/workspace", workspace_index, methods=["GET"])
    app.add_api_route("/monitor", monitor_index, methods=["GET"])
    app.add_api_route("/public-assets/{name}", public_asset, methods=["GET"])
    app.add_api_route("/assets/{name:path}", asset, methods=["GET"])
    app.add_api_route("/favicon.svg", favicon, methods=["GET"])
    app.add_api_route("/favicon.ico", favicon_ico, methods=["GET"])
    return app


def serve(args):
    import ipaddress

    import uvicorn

    if not ipaddress.ip_address(args.host).is_loopback:
        raise ValueError("Bind the public gateway to loopback behind a TLS reverse proxy")
    app = create_app(args.root, secure_cookies=not args.development_http)
    unix_socket = getattr(args, "unix_socket", None)
    if app.state.workspace.settings().get("executor_qualified") and not unix_socket:
        raise ValueError("Managed general execution requires a private Unix HTTP socket")
    if unix_socket:
        unix_socket = Path(unix_socket)
        unix_socket.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.umask(0o077)
    options = dict(
        host=args.host,
        port=args.port,
        uds=str(unix_socket) if unix_socket else None,
        proxy_headers=False,
        access_log=False,
        timeout_keep_alive=5,
        limit_concurrency=100,
    )
    if unix_socket:

        class PrivateSocketServer(uvicorn.Server):
            async def startup(self, sockets=None):
                await super().startup(sockets)
                if unix_socket.exists():
                    unix_socket.chmod(0o600)

        PrivateSocketServer(uvicorn.Config(app, **options)).run()
    else:
        uvicorn.run(app, **options)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Serve public Simjecture trials behind HTTPS")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8788, type=int)
    parser.add_argument("--development-http", action="store_true")
    parser.add_argument(
        "--unix-socket", type=Path, help="Private Unix HTTP socket for managed execution"
    )
    serve(parser.parse_args())


if __name__ == "__main__":
    main()
