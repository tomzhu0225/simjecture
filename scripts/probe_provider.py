"""Opt-in live provider probe. The credential is read only from the environment."""

from __future__ import annotations

import argparse
import json
import time
from urllib.parse import urlsplit

import httpx

from conjecture_solver.llm import (
    IncompleteCompletion,
    ModelPolicy,
    ModelRoute,
    OpenAICompatibleClient,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        help="Override the model for this probe without changing the environment",
    )
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--allow-escalation", action="store_true")
    parser.add_argument("--reason")
    parser.add_argument(
        "--probe-live-internet",
        action="store_true",
        help=(
            "Compare the model's attempted retrieval of a current public GitHub "
            "commit with a host-side reference retrieval"
        ),
    )
    args = parser.parse_args()

    client = OpenAICompatibleClient.from_environment()
    route = ModelRoute.DEFAULT
    reason = None
    if args.model == client.policy.escalation_model:
        if not args.allow_escalation or not args.reason:
            parser.error(
                "probing the configured escalation model requires "
                "--allow-escalation and --reason"
            )
        route = ModelRoute.ESCALATION
        reason = args.reason
    elif args.model:
        client.policy = ModelPolicy(
            default_model=args.model,
            escalation_model=client.policy.escalation_model,
        )
    endpoint_host = urlsplit(client.base_url).hostname or "unknown"
    print(f"provider={client.provider_name}")
    print(f"endpoint_host={endpoint_host}")
    print(f"credential_source={client.credential_source}")
    models_started = time.perf_counter()
    models = client.list_models()
    models_seconds = time.perf_counter() - models_started
    print(f"models_available={len(models)}")
    print(f"models_latency_seconds={models_seconds:.3f}")
    completion_started = time.perf_counter()
    result = client.complete(
        [{"role": "user", "content": "Reply with exactly: provider-ok"}],
        route=route,
        escalation_reason=reason,
        max_tokens=args.max_tokens,
    )
    completion_seconds = time.perf_counter() - completion_started
    print(f"model={result.model}")
    print(f"finish_reason={result.finish_reason}")
    print(f"total_tokens={result.usage.get('total_tokens', 'unknown')}")
    print(f"completion_latency_seconds={completion_seconds:.3f}")
    print(f"response_ok={result.content.strip() == 'provider-ok'}")
    if args.probe_live_internet:
        target = "https://api.github.com/repos/openai/openai-python/commits/main"
        with httpx.Client(timeout=30.0) as host_client:
            reference_response = host_client.get(
                target,
                headers={"Accept": "application/vnd.github+json"},
            )
            reference_response.raise_for_status()
        reference = reference_response.json()
        expected_sha = str(reference["sha"])
        expected_date = str(reference["commit"]["committer"]["date"])
        try:
            internet_result = client.complete(
                [
                    {
                        "role": "user",
                        "content": (
                            "This is a controlled live-internet capability test. Fetch "
                            f"{target} now. Return exactly one compact JSON object with "
                            "keys sha, committer_date, and access_status. Do not use "
                            "remembered data or guess. If you cannot retrieve the URL "
                            "live, set sha and committer_date to null and access_status "
                            "to no_live_access."
                        ),
                    }
                ],
                route=route,
                escalation_reason=reason,
                max_tokens=256,
            )
            response_content = internet_result.content
            internet_model = internet_result.model
        except IncompleteCompletion as error:
            response_content = ""
            internet_model = result.model
            print(f"internet_probe_error={type(error).__name__}: {error}")
        try:
            observed = json.loads(response_content)
        except json.JSONDecodeError:
            observed = {}
        confirmed = (
            observed.get("sha") == expected_sha
            and observed.get("committer_date") == expected_date
        )
        self_reported_absent = (
            observed.get("sha") is None
            and observed.get("committer_date") is None
            and observed.get("access_status") == "no_live_access"
        )
        status = (
            "confirmed"
            if confirmed
            else "not_exposed"
            if self_reported_absent
            else "not_confirmed"
        )
        print(f"live_internet_access={status}")
        print(f"internet_probe_model={internet_model}")
        print(f"internet_probe_reference_sha={expected_sha}")
        print(f"internet_probe_response={response_content.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
