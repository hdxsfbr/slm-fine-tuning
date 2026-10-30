"""demo_server.py: the web demo on mock clients, no GPU or network."""
import json
import threading
import urllib.error
import urllib.request

import pytest

import demo_server

FEN = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"


@pytest.fixture(scope="module")
def served():
    state = demo_server.build_state("mock:tuned", "mock:base")
    server = demo_server.make_server("127.0.0.1", 0, state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_address[1], state
    finally:
        server.shutdown()
        server.server_close()


def call(base_url, path, body=None, method=None, session=None):
    """(status, decoded JSON or text) for one request; HTTP errors are
    returned, not raised. `session` sets the X-Session header."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(base_url + path, data=data, method=method or ("POST" if data else "GET"))
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if session is not None:
        req.add_header("X-Session", session)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw, status, ctype = resp.read(), resp.status, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        raw, status, ctype = e.read(), e.code, e.headers.get("Content-Type", "")
    text = raw.decode("utf-8")
    return status, (json.loads(text) if ctype.startswith("application/json") else text)


def test_health_lists_both_models_and_no_turns(served):
    url, state = served
    state.reset()
    status, health = call(url, "/api/health")
    assert status == 200
    assert health["base"]["spec"] == "mock:base" and health["tuned"]["spec"] == "mock:tuned"
    for name in ("base", "tuned"):
        assert set(health[name]) == {"spec", "revision", "base", "base_revision"}
        assert health[name]["revision"] is None  # mock clients carry no revision
    assert health["turns"] == 0


def test_opening_from_fen_and_bad_fen(served):
    url, _ = served
    status, body = call(url, "/api/opening?fen=" + urllib.request.quote(FEN))
    assert status == 200
    assert body["text"].startswith("Here is my game.")
    assert "FEN: " + FEN in body["text"]
    assert "White: king g1, rook d1, pawns f2 g2 h2." in body["text"]
    assert body["text"].endswith("What should I play?")
    status, body = call(url, "/api/opening?fen=garbage")
    assert status == 400 and "error" in body
    status, body = call(url, "/api/opening")
    assert status == 400 and "error" in body


def test_turn_for_each_model_grows_the_histories(served):
    url, state = served
    state.reset()
    opening = call(url, "/api/opening?fen=" + urllib.request.quote(FEN))[1]["text"]
    for name in ("base", "tuned"):
        status, body = call(url, "/api/turn", {"model": name, "text": opening})
        assert status == 200, body
        assert isinstance(body["text"], str) and body["text"].strip()
        assert isinstance(body["seconds"], (int, float)) and body["seconds"] >= 0
    assert call(url, "/api/health")[1]["turns"] == 1
    for name in ("base", "tuned"):
        history = state.histories[name]
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": opening}
        assert history[1]["role"] == "assistant" and history[1]["content"].strip()


def test_history_keeps_fen_and_opening_across_reset(served):
    url, state = served
    state.reset()
    opening = call(url, "/api/opening?fen=" + urllib.request.quote(FEN))[1]["text"]
    for name in ("base", "tuned"):
        assert call(url, "/api/turn", {"model": name, "text": opening})[0] == 200
    status, history = call(url, "/api/history")
    assert status == 200
    assert history["fen"] == FEN and history["opening"] == opening
    for name in ("base", "tuned"):
        assert [m["role"] for m in history[name]] == ["user", "assistant"]
        assert history[name][0]["content"] == opening and history[name][1]["content"].strip()
    assert call(url, "/api/health")[1]["fen"] == FEN
    assert call(url, "/api/reset", method="POST")[1] == {"ok": True}
    history = call(url, "/api/history")[1]
    assert history["base"] == [] and history["tuned"] == []
    assert history["fen"] == FEN and history["opening"] == opening


def test_bad_turn_bodies_are_400(served):
    url, state = served
    state.reset()
    for body in ({"model": "base"}, {"model": "base", "text": ""}, {"model": "base", "text": 3}, {"model": "other", "text": "hi"}, {"text": "hi"}):
        status, out = call(url, "/api/turn", body)
        assert status == 400 and out["error"], body
    req = urllib.request.Request(url + "/api/turn", data=b"not json", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=30)
    assert e.value.code == 400
    assert call(url, "/api/turn", method="POST")[0] == 400
    assert state.histories["base"] == [] and state.histories["tuned"] == []


def test_reset_empties_the_histories(served):
    url, state = served
    assert call(url, "/api/turn", {"model": "tuned", "text": "How does castling work?"})[0] == 200
    assert len(state.histories["tuned"]) == 2
    status, body = call(url, "/api/reset", method="POST")
    assert status == 200 and body == {"ok": True}
    assert state.histories["base"] == [] and state.histories["tuned"] == []
    assert call(url, "/api/health")[1]["turns"] == 0


def test_index_and_unknown_paths(served):
    url, _ = served
    status, html = call(url, "/")
    assert status == 200
    assert "Hint-only chess coach" in html
    for marker in ('id="fen"', 'id="load"', 'id="prompt"', 'id="send"', 'id="reset"', 'data-model="base"', 'data-model="tuned"', 'class="quick"'):
        assert marker in html, marker
    assert chr(0x2014) not in html  # the UI text uses commas and colons, never dashes
    assert call(url, "/nope")[0] == 404
    assert call(url, "/api/nope")[0] == 404
    assert call(url, "/api/health", method="POST")[0] == 404


def test_sessions_keep_their_own_conversations(served):
    url, state = served
    a, b = "visitor-a", "visitor-b"
    for sid in (a, b):
        assert call(url, "/api/reset", method="POST", session=sid)[0] == 200
    assert call(url, "/api/opening?fen=" + urllib.request.quote(FEN), session=a)[0] == 200
    assert call(url, "/api/turn", {"model": "tuned", "text": "What should I play?"}, session=a)[0] == 200
    assert call(url, "/api/turn", {"model": "tuned", "text": "How does castling work?"}, session=b)[0] == 200
    ha, hb = call(url, "/api/history", session=a)[1], call(url, "/api/history", session=b)[1]
    assert ha["fen"] == FEN and hb["fen"] is None
    assert ha["tuned"][0]["content"] == "What should I play?" and hb["tuned"][0]["content"] == "How does castling work?"
    assert ha["base"] == [] and hb["base"] == []
    assert call(url, "/api/health", session=b)[1]["turns"] == 1
    # the default session (no header) is untouched by either visitor
    assert call(url, "/api/history")[1]["tuned"] == state.histories["tuned"]
    assert call(url, "/api/history", session="bad id!")[0] == 400


def test_caps_on_text_fen_and_turns(served, monkeypatch):
    url, state = served
    sid = "capped"
    status, body = call(url, "/api/turn", {"model": "base", "text": "x" * (demo_server.MAX_TEXT_CHARS + 1)}, session=sid)
    assert status == 400 and "characters" in body["error"]
    assert call(url, "/api/opening?fen=" + "8/" * 60, session=sid)[0] == 400
    monkeypatch.setattr(demo_server, "MAX_USER_TURNS", 2)
    for i in range(2):
        assert call(url, "/api/turn", {"model": "base", "text": "turn %d" % i}, session=sid)[0] == 200
    status, body = call(url, "/api/turn", {"model": "base", "text": "one more"}, session=sid)
    assert status == 400 and "limit" in body["error"]
    assert len(call(url, "/api/history", session=sid)[1]["base"]) == 4
    assert call(url, "/api/reset", method="POST", session=sid)[0] == 200
    assert call(url, "/api/turn", {"model": "base", "text": "after reset"}, session=sid)[0] == 200


def test_rate_limit_answers_429(served, monkeypatch):
    url, state = served
    monkeypatch.setattr(demo_server, "RATE_LIMIT", (2, 60.0))
    state.turn_times.clear()
    for i in range(2):
        assert call(url, "/api/turn", {"model": "tuned", "text": "q%d" % i}, session="rate-%d" % i)[0] == 200
    status, body = call(url, "/api/turn", {"model": "tuned", "text": "q2"}, session="rate-2")
    assert status == 429 and "busy" in body["error"]
    state.turn_times.clear()
    assert call(url, "/api/turn", {"model": "tuned", "text": "q3"}, session="rate-3")[0] == 200


def test_sessions_are_evicted_least_recently_used(served, monkeypatch):
    url, state = served
    monkeypatch.setattr(demo_server, "MAX_SESSIONS", 3)
    with state.lock:
        state.sessions.clear()
    for sid in ("e1", "e2", "e3"):
        assert call(url, "/api/health", session=sid)[0] == 200
    assert call(url, "/api/health", session="e1")[0] == 200  # e1 becomes the most recent
    assert call(url, "/api/health", session="e4")[0] == 200  # e2 is the oldest and goes
    assert set(state.sessions) == {"e1", "e3", "e4"}
