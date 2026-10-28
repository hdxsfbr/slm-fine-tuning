import io
import json
import urllib.error

import pytest

from pilot import clients
from pilot.clients import EmptyReplyError, ProviderError, Reply, make_client, parse_spec, post_json


# --- spec parsing -----------------------------------------------------------


def test_parse_spec_splits_on_first_colon_only():
    assert parse_spec("openrouter:qwen/qwen3-4b:free") == ("openrouter", "qwen/qwen3-4b:free")
    assert parse_spec("anthropic:claude-x") == ("anthropic", "claude-x")


@pytest.mark.parametrize("spec", ["gpt-4o", "hf:qwen", "openai:", ":model"])
def test_parse_spec_rejects_bad_specs(spec):
    with pytest.raises(ValueError):
        parse_spec(spec)


# --- retry ------------------------------------------------------------------


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _http_error(code, headers=None):
    return urllib.error.HTTPError("http://x", code, "err", headers or {}, io.BytesIO(b'{"error":"x"}'))


def test_retries_429_then_succeeds(monkeypatch):
    attempts = []
    sleeps = []

    def fake_urlopen(req, timeout):
        attempts.append(req)
        if len(attempts) < 3:
            raise _http_error(429)
        return _FakeResponse(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    out = post_json("http://x", {}, {"a": 1}, timeout=1, sleep=sleeps.append)
    assert out == {"ok": True}
    assert len(attempts) == 3
    assert len(sleeps) == 2


def test_retries_openrouter_in_flight_402_with_retry_after(monkeypatch):
    attempts = []
    sleeps = []
    body = json.dumps({"error": {"code": 402, "metadata": {"reason": "in_flight_budget_exhausted"}}}).encode()

    def fake_urlopen(req, timeout):
        attempts.append(req)
        if len(attempts) == 1:
            raise urllib.error.HTTPError("http://x", 402, "err", {"Retry-After": "3"}, io.BytesIO(body))
        return _FakeResponse(json.dumps({"ok": True}).encode())

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    assert post_json("http://x", {}, {}, timeout=1, sleep=sleeps.append) == {"ok": True}
    assert sleeps == [3.0]


def test_no_retry_on_402_out_of_credits(monkeypatch):
    attempts = []

    def fake_urlopen(req, timeout):
        attempts.append(req)
        raise _http_error(402)  # no in-flight marker in the body

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ProviderError) as info:
        post_json("http://x", {}, {}, timeout=1, sleep=lambda s: None)
    assert info.value.status == 402 and len(attempts) == 1


def test_honors_retry_after_header(monkeypatch):
    calls = {"n": 0}
    sleeps = []

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(503, {"Retry-After": "7"})
        return _FakeResponse(b"{}")

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    post_json("http://x", {}, {}, timeout=1, sleep=sleeps.append)
    assert sleeps == [7.0]


def test_no_retry_on_400(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        raise _http_error(400)

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ProviderError) as info:
        post_json("http://x", {}, {}, timeout=1, sleep=lambda s: None)
    assert info.value.status == 400
    assert calls["n"] == 1


def test_gives_up_after_max_attempts(monkeypatch):
    def fake_urlopen(req, timeout):
        raise _http_error(500)

    monkeypatch.setattr(clients.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ProviderError) as info:
        post_json("http://x", {}, {}, timeout=1, max_attempts=3, sleep=lambda s: None)
    assert info.value.status == 500


# --- request bodies ---------------------------------------------------------


def _capture(monkeypatch, response):
    captured = {}

    def fake_post(url, headers, body, timeout, **kw):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return response

    monkeypatch.setattr(clients, "post_json", fake_post)
    return captured


OPENAI_RESPONSE = {
    "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 1},
}


def test_openai_uses_max_completion_tokens_and_omits_temperature(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    captured = _capture(monkeypatch, OPENAI_RESPONSE)
    reply = make_client("openai:gpt-x").chat("sys", [{"role": "user", "content": "q"}], max_tokens=50)
    assert reply == Reply("hi", "stop", {"input_tokens": 3, "output_tokens": 1})
    body = captured["body"]
    assert body["max_completion_tokens"] == 50
    assert "max_tokens" not in body
    assert "temperature" not in body
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert captured["url"].startswith("https://api.openai.com/v1")


def test_temperature_sent_when_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    captured = _capture(monkeypatch, OPENAI_RESPONSE)
    make_client("openai:gpt-x", temperature=0.3).chat("sys", [{"role": "user", "content": "q"}], max_tokens=5)
    assert captured["body"]["temperature"] == 0.3


def test_gemini_and_openrouter_use_max_tokens(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    for spec, host in (("gemini:gemini-x", "generativelanguage.googleapis.com"), ("openrouter:a/b:free", "openrouter.ai")):
        captured = _capture(monkeypatch, OPENAI_RESPONSE)
        make_client(spec).chat("sys", [{"role": "user", "content": "q"}], max_tokens=7)
        assert captured["body"]["max_tokens"] == 7
        assert "max_completion_tokens" not in captured["body"]
        assert host in captured["url"]


def test_anthropic_body_shape(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    captured = _capture(
        monkeypatch,
        {"content": [{"type": "text", "text": "hello"}], "stop_reason": "end_turn", "usage": {"input_tokens": 2, "output_tokens": 1}},
    )
    reply = make_client("anthropic:claude-x").chat("sys", [{"role": "user", "content": "q", "extra": 1}], max_tokens=9)
    body = captured["body"]
    assert body["system"] == "sys"
    assert body["max_tokens"] == 9
    assert body["messages"] == [{"role": "user", "content": "q"}]
    assert captured["headers"]["anthropic-version"]
    assert reply.text == "hello" and reply.finish_reason == "end_turn"


def test_empty_reply_raises(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    _capture(monkeypatch, {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]})
    with pytest.raises(EmptyReplyError):
        make_client("openai:o-x").chat("sys", [{"role": "user", "content": "q"}], max_tokens=5)


def test_missing_api_key_fails_fast(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        make_client("openai:gpt-x")


# --- mock -------------------------------------------------------------------


def test_mock_client_answers_scenarios_offline():
    from behaviors import sycophancy, writing_tells

    client = make_client("mock:a")
    reply = client.chat(sycophancy.STRATEGIES["zero_shot"], [{"role": "user", "content": sycophancy.SCENARIOS[0]["question"]}], 10)
    assert "FINAL ANSWER:" in reply.text
    reply = client.chat(writing_tells.STRATEGIES["zero_shot"]["system"], [{"role": "user", "content": writing_tells.SCENARIOS[0]["prompt"]}], 10)
    assert writing_tells.count_words(reply.text) > 100


def test_mock_flaky_raises_on_schedule():
    from pilot.mock import FLAKY_EVERY

    client = make_client("mock:flaky")
    errors = 0
    for _ in range(FLAKY_EVERY * 2):
        try:
            client.chat("sys", [{"role": "user", "content": "anything"}], 10)
        except ProviderError:
            errors += 1
    assert errors == 2


def test_local_provider_spec_parses_and_keeps_the_path():
    from pilot.clients import parse_spec

    assert parse_spec("local:models/v1/adapter") == ("local", "models/v1/adapter")
    assert parse_spec("local:unsloth/Qwen3-1.7B") == ("local", "unsloth/Qwen3-1.7B")
