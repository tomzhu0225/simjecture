"""OpenAI-compatible provider client with explicit cheap/escalation routing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

import httpx

DEFAULT_BASE_URL = "https://cp.compshare.cn/v1"
DEFAULT_MODEL = "deepseek-v4-flash-0731"
ESCALATION_MODEL = "glm-5.2"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_DEFAULT_MODEL = "deepseek-v4-flash"
DEEPSEEK_ESCALATION_MODEL = "deepseek-v4-pro"


class ModelRoute(StrEnum):
    DEFAULT = "default"
    ESCALATION = "escalation"


class MissingCredential(RuntimeError):
    pass


class EscalationReasonRequired(ValueError):
    pass


class IncompleteCompletion(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelSelection:
    model: str
    route: ModelRoute
    reason: str


@dataclass(frozen=True)
class CompletionResult:
    request_id: str
    model: str
    content: str
    finish_reason: str
    usage: dict[str, Any]
    route: ModelRoute
    route_reason: str


class ModelPolicy:
    def __init__(
        self,
        *,
        default_model: str = DEFAULT_MODEL,
        escalation_model: str = ESCALATION_MODEL,
    ) -> None:
        self.default_model = default_model
        self.escalation_model = escalation_model

    @classmethod
    def from_environment(cls) -> ModelPolicy:
        return cls(
            default_model=os.getenv("ACS_DEFAULT_MODEL", DEFAULT_MODEL),
            escalation_model=os.getenv("ACS_ESCALATION_MODEL", ESCALATION_MODEL),
        )

    def select(
        self,
        route: ModelRoute = ModelRoute.DEFAULT,
        *,
        escalation_reason: str | None = None,
    ) -> ModelSelection:
        if route is ModelRoute.ESCALATION:
            if not escalation_reason or not escalation_reason.strip():
                raise EscalationReasonRequired(
                    "escalation routing requires a recorded escalation reason"
                )
            return ModelSelection(
                model=self.escalation_model,
                route=route,
                reason=escalation_reason.strip(),
            )
        return ModelSelection(
            model=self.default_model,
            route=route,
            reason="default low-cost reasoning route",
        )


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 120.0,
        policy: ModelPolicy | None = None,
        provider_name: str = "openai-compatible",
        credential_source: str | None = None,
        deepseek_thinking: Literal["enabled", "disabled"] | None = None,
    ) -> None:
        if not api_key:
            raise MissingCredential("API key is empty")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.policy = policy or ModelPolicy.from_environment()
        self.provider_name = provider_name
        self.credential_source = credential_source
        self.deepseek_thinking = deepseek_thinking

    @classmethod
    def from_environment(
        cls,
        *,
        timeout_seconds: float | None = None,
    ) -> OpenAICompatibleClient:
        configured_provider = os.getenv("ACS_MODEL_PROVIDER", "").strip().casefold()
        if configured_provider not in {"", "deepseek", "compshare"}:
            raise ValueError(
                "ACS_MODEL_PROVIDER must be 'deepseek' or 'compshare'"
            )
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        compshare_key = os.getenv("CP_API_KEY")
        use_deepseek = configured_provider == "deepseek" or (
            not configured_provider and bool(deepseek_key)
        )
        if use_deepseek:
            if not deepseek_key:
                raise MissingCredential(
                    "ACS_MODEL_PROVIDER=deepseek requires DEEPSEEK_API_KEY"
                )
            api_key = deepseek_key
            base_url = os.getenv("DEEPSEEK_API_BASE_URL", DEEPSEEK_BASE_URL)
            default_model = DEEPSEEK_DEFAULT_MODEL
            escalation_model = DEEPSEEK_ESCALATION_MODEL
            provider_name = "deepseek"
            credential_source = "DEEPSEEK_API_KEY"
            deepseek_thinking = os.getenv(
                "ACS_DEEPSEEK_THINKING", "enabled"
            ).strip().casefold()
            if deepseek_thinking not in {"enabled", "disabled"}:
                raise ValueError(
                    "ACS_DEEPSEEK_THINKING must be 'enabled' or 'disabled'"
                )
        else:
            if not compshare_key:
                raise MissingCredential(
                    "set DEEPSEEK_API_KEY for the official DeepSeek API or "
                    "CP_API_KEY for the legacy CompShare route"
                )
            api_key = compshare_key
            base_url = os.getenv("CP_API_BASE_URL", DEFAULT_BASE_URL)
            default_model = DEFAULT_MODEL
            escalation_model = ESCALATION_MODEL
            provider_name = "compshare"
            credential_source = "CP_API_KEY"
            deepseek_thinking = None
        configured_timeout = float(os.getenv("ACS_MODEL_TIMEOUT_SECONDS", "300"))
        return cls(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=(
                configured_timeout if timeout_seconds is None else timeout_seconds
            ),
            policy=ModelPolicy(
                default_model=os.getenv("ACS_DEFAULT_MODEL", default_model),
                escalation_model=os.getenv(
                    "ACS_ESCALATION_MODEL", escalation_model
                ),
            ),
            provider_name=provider_name,
            credential_source=credential_source,
            deepseek_thinking=deepseek_thinking,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def list_models(self) -> tuple[str, ...]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.base_url}/models", headers=self._headers())
            response.raise_for_status()
        payload = response.json()
        return tuple(item["id"] for item in payload.get("data", ()) if "id" in item)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> CompletionResult:
        selection = self.policy.select(route, escalation_reason=escalation_reason)
        request = {
            "model": selection.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            request["max_tokens"] = max_tokens
        if self.provider_name == "deepseek":
            # Every current Simjecture completion is a typed JSON decision. The
            # official provider's JSON mode removes one avoidable malformed-action
            # retry while retaining local schema validation as the authority.
            request["response_format"] = {"type": "json_object"}
            request["thinking"] = {
                "type": self.deepseek_thinking or "enabled"
            }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=request,
            )
            response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise IncompleteCompletion("provider returned no completion choice")
        choice = choices[0]
        content = (choice.get("message") or {}).get("content") or ""
        if not content.strip():
            raise IncompleteCompletion(
                "provider returned no usable completion content"
            )
        finish_reason = choice.get("finish_reason") or "unknown"
        return CompletionResult(
            request_id=str(payload.get("id", "")),
            model=str(payload.get("model", selection.model)),
            content=content,
            finish_reason=finish_reason,
            usage=dict(payload.get("usage") or {}),
            route=selection.route,
            route_reason=selection.reason,
        )
