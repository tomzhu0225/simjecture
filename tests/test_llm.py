from __future__ import annotations

import httpx
import pytest

from conjecture_solver.llm import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_ESCALATION_MODEL,
    DEFAULT_MODEL,
    ESCALATION_MODEL,
    EscalationReasonRequired,
    IncompleteCompletion,
    ModelPolicy,
    ModelRoute,
    OpenAICompatibleClient,
)


def test_cheap_model_is_default() -> None:
    selection = ModelPolicy().select()
    assert selection.model == DEFAULT_MODEL
    assert selection.route is ModelRoute.DEFAULT


def test_expensive_model_requires_reason() -> None:
    policy = ModelPolicy()
    with pytest.raises(EscalationReasonRequired):
        policy.select(ModelRoute.ESCALATION)

    selection = policy.select(
        ModelRoute.ESCALATION,
        escalation_reason="cheap model failed the semantic round-trip twice",
    )
    assert selection.model == ESCALATION_MODEL
    assert "semantic round-trip" in selection.reason


def test_provider_timeout_is_configurable_without_embedding_credentials(monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("CP_API_KEY", "process-local-test-placeholder")
    monkeypatch.setenv("ACS_MODEL_TIMEOUT_SECONDS", "321")
    client = OpenAICompatibleClient.from_environment()
    assert client.timeout_seconds == 321
    assert "process-local-test-placeholder" not in repr(client)


def test_official_deepseek_environment_takes_precedence(monkeypatch) -> None:
    monkeypatch.delenv("ACS_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("ACS_DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("ACS_ESCALATION_MODEL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "official-process-local-placeholder")
    monkeypatch.setenv("CP_API_KEY", "proxy-process-local-placeholder")

    client = OpenAICompatibleClient.from_environment()

    assert client.provider_name == "deepseek"
    assert client.credential_source == "DEEPSEEK_API_KEY"
    assert client.base_url == DEEPSEEK_BASE_URL
    assert client.policy.default_model == DEEPSEEK_DEFAULT_MODEL
    assert client.policy.escalation_model == DEEPSEEK_ESCALATION_MODEL
    assert "official-process-local-placeholder" not in repr(client)
    assert "proxy-process-local-placeholder" not in repr(client)


def test_explicit_compshare_environment_preserves_legacy_route(monkeypatch) -> None:
    monkeypatch.setenv("ACS_MODEL_PROVIDER", "compshare")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "unused-official-placeholder")
    monkeypatch.setenv("CP_API_KEY", "proxy-process-local-placeholder")
    monkeypatch.delenv("ACS_DEFAULT_MODEL", raising=False)
    monkeypatch.delenv("ACS_ESCALATION_MODEL", raising=False)

    client = OpenAICompatibleClient.from_environment()

    assert client.provider_name == "compshare"
    assert client.credential_source == "CP_API_KEY"
    assert client.policy.default_model == DEFAULT_MODEL
    assert client.policy.escalation_model == ESCALATION_MODEL


def test_explicit_deepseek_provider_requires_official_key(monkeypatch) -> None:
    monkeypatch.setenv("ACS_MODEL_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("CP_API_KEY", "proxy-process-local-placeholder")

    with pytest.raises(RuntimeError, match="requires DEEPSEEK_API_KEY"):
        OpenAICompatibleClient.from_environment()


def test_provider_omits_completion_ceiling_when_none(monkeypatch) -> None:
    requests: list[dict[str, object]] = []

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]):
            del headers
            requests.append(json)
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "completion_unbounded",
                    "model": DEFAULT_MODEL,
                    "choices": [
                        {"message": {"content": "{}"}, "finish_reason": "stop"}
                    ],
                    "usage": {},
                },
            )

    monkeypatch.setattr("conjecture_solver.llm.httpx.Client", FakeClient)
    client = OpenAICompatibleClient(api_key="test-placeholder")
    client.complete([{"role": "user", "content": "Return JSON"}], max_tokens=None)
    client.complete([{"role": "user", "content": "Return JSON"}], max_tokens=123)

    assert "max_tokens" not in requests[0]
    assert requests[1]["max_tokens"] == 123


def test_provider_rejects_empty_completion_content(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]):
            del headers, json
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "completion_without_content",
                    "model": DEFAULT_MODEL,
                    "choices": [
                        {
                            "message": {"content": "", "reasoning_content": "hidden"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"completion_tokens": 2505},
                },
            )

    monkeypatch.setattr("conjecture_solver.llm.httpx.Client", FakeClient)
    client = OpenAICompatibleClient(api_key="test-placeholder")

    with pytest.raises(IncompleteCompletion, match="no usable completion content"):
        client.complete([{"role": "user", "content": "Return JSON"}])
