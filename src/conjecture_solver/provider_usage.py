"""Request counters and context hashes; never credentials or reasoning text.

Absent provider details stay unknown. Reported totals are not a billing estimate.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter

TOKEN_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens")


def mapping(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    return vars(value) if hasattr(value, "__dict__") else {}


def number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def reported_usage(response):
    raw = mapping(getattr(response, "raw", None))
    native = mapping(raw.get("usage"))
    fallback = mapping(getattr(response, "token_usage", None))
    inp = number(native.get("prompt_tokens", native.get("input_tokens")))
    out = number(native.get("completion_tokens", native.get("output_tokens")))
    cached = number(native.get("prompt_cache_hit_tokens"))
    if cached is None:
        cached = number(mapping(native.get("prompt_tokens_details")).get("cached_tokens"))
    reasoning = number(mapping(native.get("completion_tokens_details")).get("reasoning_tokens"))
    return {
        "input_tokens": inp if inp is not None else number(fallback.get("input_tokens")),
        "output_tokens": out if out is not None else number(fallback.get("output_tokens")),
        "cached_input_tokens": cached,
        "uncached_input_tokens": number(native.get("prompt_cache_miss_tokens")),
        "reasoning_output_tokens": reasoning,
        "source": "provider" if native else "adapter" if fallback else "unavailable",
    }


def context_metadata(request):
    """Describe actual prepared messages without logging their contents."""
    messages = []
    for message in request.get("messages", []):
        encoded = json.dumps(message, sort_keys=True, ensure_ascii=False, default=str).encode()
        messages.append(
            dict(
                role=message.get("role"),
                bytes=len(encoded),
                sha256=hashlib.sha256(encoded).hexdigest(),
                reasoning_bytes=len(str(message.get("reasoning_content") or "").encode()),
            )
        )
    tools = json.dumps(request.get("tools", []), sort_keys=True, default=str).encode()
    return dict(messages=messages, tool_schema_bytes=len(tools))


def request_accounting(path):
    """Prefer request receipts over step totals; interrupted requests remain visible."""
    requests, legacy = {}, []
    if not path.exists():
        return None
    with path.open(errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "provider_request" and event.get("request_id"):
                key = event["request_id"]
                if event.get("status") != "started" or key not in requests:
                    # Context metadata can dwarf the counters on long research runs.
                    requests[key] = {
                        "status": event.get("status", "unknown"),
                        "usage": event.get("usage"),
                    }
            elif event.get("type") == "usage":
                legacy.append(event)
    if not requests:
        if not legacy:
            return None
        return {key: sum(number(e.get(key)) or 0 for e in legacy) for key in TOKEN_FIELDS} | {
            "accounting": "legacy_steps",
            "cache_usage_complete": all(
                number(e.get("cached_input_tokens")) is not None for e in legacy
            ),
            "reasoning_usage_complete": all(
                number(e.get("reasoning_output_tokens")) is not None for e in legacy
            ),
        }
    totals = Counter({key: 0 for key in TOKEN_FIELDS})
    missing = cached_missing = reasoning_missing = 0
    states = Counter()
    for event in requests.values():
        states[event.get("status", "unknown")] += 1
        usage = event.get("usage") or {}
        missing += any(number(usage.get(k)) is None for k in ("input_tokens", "output_tokens"))
        cached_missing += number(usage.get("cached_input_tokens")) is None
        reasoning_missing += number(usage.get("reasoning_output_tokens")) is None
        for key in TOKEN_FIELDS:
            totals[key] += number(usage.get(key)) or 0
    return dict(totals) | dict(
        accounting="provider_requests",
        requests=len(requests),
        reported_requests=len(requests) - missing,
        requests_without_usage=missing,
        request_states=dict(states),
        cache_usage_complete=cached_missing == 0,
        reasoning_usage_complete=reasoning_missing == 0,
    )
