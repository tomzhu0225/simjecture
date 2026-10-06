"""GitHub identity verification with an ephemeral, local credential inlet."""

import base64
import hashlib
import hmac
import json
import os
import socket
import struct
import threading
from urllib.parse import urlencode

OAUTH_COOKIE = "simjecture_oauth"


class GitHubLogin:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.credentials = {}
        self.socket = None

    def ready(self):
        return bool(self.credentials.get("client_id") and self.credentials.get("client_secret"))

    def start_inlet(self):
        """Credentials stay in RAM. This socket is never routed through HTTP."""
        path = self.store.root / ".oauth-inlet.sock"
        path.unlink(missing_ok=True)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(str(path))
        path.chmod(0o600)
        listener.listen(2)
        self.socket = listener

        def receive():
            while self.socket:
                try:
                    connection, _ = listener.accept()
                except OSError:
                    return
                with connection:
                    connection.settimeout(5)
                    _, uid, _ = struct.unpack(
                        "3i",
                        connection.getsockopt(
                            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                        ),
                    )
                    if uid not in {0, os.getuid()}:
                        continue
                    body = bytearray()
                    try:
                        while b"\n" not in body and len(body) <= 4096:
                            chunk = connection.recv(1024)
                            if not chunk:
                                break
                            body.extend(chunk)
                        data = json.loads(body)
                        if set(data) != {"client_id", "client_secret"} or not all(
                            isinstance(v, str) and 1 <= len(v) <= 512 for v in data.values()
                        ):
                            raise ValueError()
                        self.credentials = data
                        connection.sendall(b"OAuth credentials loaded in memory\n")
                    except (ValueError, OSError):
                        pass  # Never log credential payloads or parser exceptions.

        threading.Thread(target=receive, daemon=True).start()

    def close(self):
        listener, self.socket = self.socket, None
        if listener:
            listener.close()
            (self.store.root / ".oauth-inlet.sock").unlink(missing_ok=True)
        self.credentials = {}

    def authorization(self, owner):
        if not self.ready():
            raise ValueError("GitHub sign-in is being configured")
        if self.store.account(owner):
            raise ValueError("Sign out before changing accounts")
        state, verifier = self.store.oauth_start(owner)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return state, "https://github.com/login/oauth/authorize?" + urlencode(
            {
                "client_id": self.credentials["client_id"],
                "scope": "read:user user:email",
                "redirect_uri": self.settings()["public_origin"].rstrip("/")
                + "/api/auth/github/callback",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )

    async def callback(self, state, cookie, code):
        import httpx

        if not state or len(state) > 128 or not cookie or not hmac.compare_digest(state, cookie):
            raise ValueError("Sign-in state does not match this browser")
        pending = self.store.oauth_consume(state)
        if not pending or not code or len(code) > 512 or not self.ready():
            raise ValueError("Sign-in expired; please start again")
        self.store.oauth_hold(pending["visitor"])
        credentials = self.credentials.copy()
        # The provider token is used only during this request, then discarded.
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    **credentials,
                    "code": code,
                    "code_verifier": pending["verifier"],
                    "redirect_uri": self.settings()["public_origin"].rstrip("/")
                    + "/api/auth/github/callback",
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise ValueError("GitHub did not authorize this sign-in")
            headers = {
                "Authorization": "Bearer " + token,
                "Accept": "application/vnd.github+json",
                "User-Agent": "Simjecture-SignIn",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            profile = await client.get("https://api.github.com/user", headers=headers)
            emails = await client.get("https://api.github.com/user/emails", headers=headers)
            profile.raise_for_status()
            emails.raise_for_status()
            user = profile.json()
            if not any(e.get("verified") is True for e in emails.json()):
                raise ValueError("Verify an email address on GitHub before signing in")
            if not isinstance(user.get("id"), int) or user["id"] <= 0:
                raise ValueError("GitHub identity was not verified")
            return self.store.authorize_identity(
                pending["visitor"],
                user["id"],
                str(user.get("login", ""))[:80],
                str(user.get("name") or user.get("login", ""))[:200],
            )
