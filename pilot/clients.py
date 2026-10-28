"""Chat clients for the pilot.

One spec string selects a provider and a model: "provider:model". The split
happens on the first colon only, so OpenRouter ids such as
"openrouter:qwen/qwen3-4b:free" work.

    anthropic    Messages API, plain HTTP
    openai       OpenAI chat completions (max_completion_tokens)
    gemini       Google's OpenAI-compatible endpoint
    openrouter   OpenRouter's OpenAI-compatible endpoint
    mock         deterministic offline replies, see pilot.mock

Every client implements chat(system, messages, max_tokens) -> Reply. A local
Hugging Face model can implement the same method later for eval.py.

Temperature is only sent when set, because OpenAI reasoning models reject it.
429 and 5xx responses, and OpenRouter's transient 402 (in-flight budget), are
retried with jittered exponential backoff, honoring Retry-After when present.
"""
from __future__ import annotations

import http.client
import json
import os
import random
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

PROVIDERS = ("anthropic", "openai", "gemini", "openrouter", "mock", "local")

RETRY_STATUSES = {408, 429, 500, 502, 503, 504, 529}
# OpenRouter answers 402 both when credits are gone and when the in-flight
# reservation (workers x max_tokens x output price) exceeds the balance.
# Only the second is transient; its body names the reason.
TRANSIENT_402_MARKER = "in_flight_budget_exhausted"
MAX_ATTEMPTS = 6
MAX_BACKOFF_S = 60.0

_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com",
}
_KEY_ENV = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
}


class ProviderError(Exception):
    """A request failed after retries, or with a non-retryable status."""

    def __init__(self, status: Optional[int], body: str):
        self.status = status
        self.body = body
        super().__init__("HTTP %s: %s" % (status, body[:500]))


class EmptyReplyError(Exception):
    """The provider returned no text (usually a reasoning model that spent
    its whole token budget before producing output)."""


@dataclass
class Reply:
    text: str
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)


def parse_spec(spec: str) -> Tuple[str, str]:
    if ":" not in spec:
        raise ValueError("model spec must look like provider:model, got %r" % spec)
    provider, model = spec.split(":", 1)
    provider = provider.strip().lower()
    if provider not in PROVIDERS:
        raise ValueError("unknown provider %r in %r (expected one of %s)" % (provider, spec, ", ".join(PROVIDERS)))
    if not model.strip():
        raise ValueError("empty model id in %r" % spec)
    return provider, model.strip()


def _backoff(attempt: int) -> float:
    return min(MAX_BACKOFF_S, 1.5 * (2 ** attempt)) + random.uniform(0, 1)


def _retryable(status: int, text: str) -> bool:
    return status in RETRY_STATUSES or (status == 402 and TRANSIENT_402_MARKER in text)


def _retry_after(headers) -> Optional[float]:
    value = headers.get("Retry-After") if headers is not None else None
    if not value:
        return None
    try:
        return min(MAX_BACKOFF_S, float(value))
    except ValueError:
        return None


def post_json(
    url: str,
    headers: Dict[str, str],
    body: Dict,
    timeout: float,
    max_attempts: int = MAX_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> Dict:
    """POST a JSON body and return the decoded JSON response, retrying on
    rate limits, server errors and connection failures."""
    data = json.dumps(body).encode("utf-8")
    all_headers = {"content-type": "application/json", "accept": "application/json"}
    all_headers.update(headers)
    last_error = "no attempts made"
    for attempt in range(max_attempts):
        req = urllib.request.Request(url, data=data, headers=all_headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            if _retryable(e.code, text) and attempt < max_attempts - 1:
                last_error = "HTTP %d: %s" % (e.code, text[:200])
                sleep(_retry_after(e.headers) or _backoff(attempt))
                continue
            raise ProviderError(e.code, text)
        except (urllib.error.URLError, socket.timeout, ConnectionError, http.client.HTTPException) as e:
            last_error = "%s: %s" % (type(e).__name__, e)
            if attempt < max_attempts - 1:
                sleep(_backoff(attempt))
                continue
            raise ProviderError(None, last_error)
    raise ProviderError(None, "gave up after %d attempts: %s" % (max_attempts, last_error))


class ChatClient:
    """Base class. Subclasses implement chat()."""

    provider = "base"

    def __init__(self, spec: str, model: str, temperature: Optional[float] = None, timeout: float = 180.0):
        self.spec = spec
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def chat(self, system: str, messages: List[Dict[str, str]], max_tokens: int) -> Reply:
        raise NotImplementedError

    @staticmethod
    def _clean(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return [{"role": m["role"], "content": m["content"]} for m in messages]


def _api_key(provider: str) -> str:
    for name in _KEY_ENV[provider]:
        value = os.environ.get(name)
        if value:
            return value
    raise ValueError("set %s to use provider %r" % (" or ".join(_KEY_ENV[provider]), provider))


def _base_url(provider: str) -> str:
    return os.environ.get(provider.upper() + "_BASE_URL", _BASE_URLS[provider]).rstrip("/")


class AnthropicClient(ChatClient):
    provider = "anthropic"

    def __init__(self, spec, model, temperature=None, timeout=180.0):
        super().__init__(spec, model, temperature, timeout)
        self.api_key = _api_key("anthropic")
        self.url = _base_url("anthropic") + "/v1/messages"

    def chat(self, system, messages, max_tokens):
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": self._clean(messages),
        }
        if self.temperature is not None:
            body["temperature"] = self.temperature
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        data = post_json(self.url, headers, body, self.timeout)
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        usage = data.get("usage") or {}
        reply = Reply(
            text=text,
            finish_reason=data.get("stop_reason"),
            usage={"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)},
        )
        if not reply.text.strip():
            raise EmptyReplyError("empty reply (stop_reason=%s)" % reply.finish_reason)
        return reply


class OpenAICompatClient(ChatClient):
    """OpenAI chat completions, also used for Gemini and OpenRouter."""

    def __init__(self, spec, model, provider, temperature=None, timeout=180.0, extra_body=None):
        super().__init__(spec, model, temperature, timeout)
        self.provider = provider
        self.api_key = _api_key(provider)
        self.url = _base_url(provider) + "/chat/completions"
        # OpenAI reasoning models require max_completion_tokens; the
        # compatible endpoints still expect max_tokens.
        self.max_tokens_key = "max_completion_tokens" if provider == "openai" else "max_tokens"
        # Extra request fields, e.g. OpenRouter's {"reasoning": {"enabled": false}}
        # to stop a model from spending hidden reasoning tokens on a short
        # structured reply.
        self.extra_body = dict(extra_body or {})

    def chat(self, system, messages, max_tokens):
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + self._clean(messages),
            self.max_tokens_key: max_tokens,
        }
        body.update(self.extra_body)
        if self.temperature is not None:
            body["temperature"] = self.temperature
        headers = {"authorization": "Bearer " + self.api_key}
        data = post_json(self.url, headers, body, self.timeout)
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError(None, "no choices in response: %s" % json.dumps(data)[:500])
        choice = choices[0]
        content = (choice.get("message") or {}).get("content") or ""
        if isinstance(content, list):  # some compatible endpoints return parts
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        usage = data.get("usage") or {}
        reply = Reply(
            text=content,
            finish_reason=choice.get("finish_reason"),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
        )
        if not reply.text.strip():
            raise EmptyReplyError("empty reply (finish_reason=%s)" % reply.finish_reason)
        return reply


def make_client(spec: str, temperature: Optional[float] = None, timeout: float = 180.0, extra_body: Optional[Dict] = None) -> ChatClient:
    """extra_body is only honored by the OpenAI-compatible providers."""
    provider, model = parse_spec(spec)
    if provider == "mock":
        from .mock import MockClient

        return MockClient(spec, model, temperature, timeout)
    if provider == "anthropic":
        return AnthropicClient(spec, model, temperature, timeout)
    if provider == "local":
        from .local_client import LocalClient  # needs the training environment

        return LocalClient(spec, model, temperature, timeout)
    return OpenAICompatClient(spec, model, provider, temperature, timeout, extra_body)
