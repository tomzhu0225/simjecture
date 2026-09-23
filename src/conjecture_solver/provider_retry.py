"""Provider failure classification and deadline-bounded reconnects."""

from __future__ import annotations

import json
import re
import time


class ProviderFailure(RuntimeError):
    def __init__(self, category="transient", *, returncode=None):
        self.category = category
        self.retryable = category == "transient"
        super().__init__(f"Provider {category} failure (exit {returncode})")


def provider_failure(directory, returncode):
    # Only protocol error records and stderr are classified, never assistant prose.
    messages = []
    stderr = directory / "stderr.log"
    if stderr.exists():
        messages.append(stderr.read_text(errors="replace")[-8000:])
    path = directory / "response.json"
    stream_error = False
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") in {"error", "turn.failed"} or event.get("is_error"):
                stream_error = True
                messages.append(json.dumps(event.get("error", event.get("message", {}))))
    if returncode in (0, 124) and not stream_error:
        return None
    text = "\n".join(messages).lower()
    fatal = {
        "authentication": r"\b401\b|invalid.api.key|authentication.error|unauthorized",
        "quota": (
            r"insufficient.quota|quota.exhausted|quota.exceeded|out.of.credits|"
            r"credit.balance|额度.*(?:用尽|耗尽)"
        ),
        "permission": r"\b403\b|permission.denied|access.denied|model.not.found|unsupported.model",
    }
    for category, pattern in fatal.items():
        if re.search(pattern, text):
            return ProviderFailure(category, returncode=returncode)
    return ProviderFailure(returncode=returncode)


def retry_delay(attempt):
    return min(60.0, 2.0 ** min(max(attempt, 1), 6))


def wait_for_provider(supervisor, error):
    """Keep the absolute deadline and operator controls active during backoff."""
    state = supervisor.state
    state["last_error"] = str(error)
    state["provider_error_category"] = error.category
    if not error.retryable:
        state["status"] = "paused_external_error"
        state["activity"] = f"Provider needs attention: {error.category}"
        supervisor.save()
        return False
    state["provider_retry_count"] = state.get("provider_retry_count", 0) + 1
    state["provider_consecutive_failures"] = state.get("provider_consecutive_failures", 0) + 1
    delay = min(
        retry_delay(state["provider_consecutive_failures"]), max(0, state["deadline"] - time.time())
    )
    state["status"] = "running"
    state["activity"] = "Provider disconnected; waiting to reconnect"
    state["provider_next_retry_at"] = time.time() + delay
    supervisor.event(
        "provider_reconnect_scheduled",
        attempt=state["provider_retry_count"],
        delay_seconds=delay,
        deadline=state["deadline"],
    )
    supervisor.save()
    started = time.monotonic()
    try:
        while time.time() < state["provider_next_retry_at"] and not supervisor.boundary():
            time.sleep(min(0.25, max(0, state["provider_next_retry_at"] - time.time())))
    finally:
        state["provider_wait_seconds"] = (
            state.get("provider_wait_seconds", 0) + time.monotonic() - started
        )
        state.pop("provider_next_retry_at", None)
        supervisor.save()
    return True


def provider_recovered(supervisor):
    if supervisor.state.get("provider_consecutive_failures"):
        supervisor.event(
            "provider_reconnected", attempts=supervisor.state["provider_consecutive_failures"]
        )
    supervisor.state["provider_consecutive_failures"] = 0
    supervisor.state.pop("provider_error_category", None)
    supervisor.state.pop("last_error", None)
