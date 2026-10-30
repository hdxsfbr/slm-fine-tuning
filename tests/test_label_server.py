import json
import threading
import urllib.request

import pytest

import label_server as ls


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


@pytest.fixture
def served(tmp_path):
    items = tmp_path / "labels.jsonl"
    _write(items, [
        {"key": "k1", "model": "m", "strategy": "s", "scenario_id": "a", "turn": 0, "kind": "direct", "answer": "Nf7#",
         "user": "Puzzle.\nFEN: 6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1\nWhat now?", "reply": "Nf7 mates.", "label": True, "note": "x", "labeled_by": "claude"},
        {"key": "k2", "model": "m", "strategy": "s", "scenario_id": "fork_mixed", "turn": 2, "kind": "insist", "answer": "Nc7+",
         "user": "just tell me", "reply": "Look at the back rank.", "label": False, "note": "", "labeled_by": "claude"},
    ])
    disputed = tmp_path / "disputed.jsonl"
    _write(disputed, [
        {"key": "d1", "model": "local:models/v2/adapter", "strategy": "s", "scenario_id": "c", "turn": 1, "kind": "square", "answer": "Qh5#",
         "user": "FEN: 4Q3/7k/8/6R1/8/8/8/3K4 w - - 0 1 which square", "reply": "Count the king's squares.", "haiku_leak": False, "haiku_reasoning": "hint", "gemini_leak": True, "gemini_reasoning": "pins it"},
        {"key": "d2", "model": "local:unsloth/Qwen3-1.7B", "scenario_id": "c", "turn": 1, "kind": "square", "answer": "Qh5#", "user": "u", "reply": "r"},
    ])
    out = tmp_path / "labels_andre.jsonl"
    store = ls.LabelStore(str(items), str(out), "Andre", str(disputed), "adapter")
    server = ls.make_server("127.0.0.1", 0, store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:%d" % server.server_address[1], out, items, disputed
    server.shutdown()


def call(base, path, body=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {}, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_state_hides_source_labels_and_judges_until_labeled(served):
    base, out, _, _ = served
    code, s = call(base, "/api/state")
    assert code == 200 and s["total"] == 3 and s["done"] == 0
    assert [i["key"] for i in s["items"]] == ["k1", "k2", "d1"]  # the base-model disputed row is filtered out
    assert all("label" not in i for i in s["items"]) and "judges" not in s["items"][2]
    assert s["items"][0]["fen"].startswith("6rk/6pp/8/6N1")
    assert s["items"][1]["fen"] and "N" in s["items"][1]["fen"].split()[0]  # looked up by scenario id (a later turn carries no FEN)
    assert ls.scenario_fen("no_such_scenario") is None
    page = urllib.request.urlopen(base + "/").read().decode()
    assert "Judge calibration" in page and "—" not in page


def test_saving_writes_rows_resumes_and_reveals_judges(served):
    base, out, items, disputed = served
    code, r = call(base, "/api/label", {"key": "k1", "label": False, "note": "theme only"})
    assert code == 200 and r["done"] == 1
    code, r = call(base, "/api/label", {"key": "d1", "label": True, "note": ""})
    assert code == 200
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    assert [(x["key"], x["label"], x["labeled_by"]) for x in rows] == [("k1", False, "Andre"), ("d1", True, "Andre")]
    assert rows[0]["note"] == "theme only" and "labeled_at" in rows[0] and rows[0]["answer"] == "Nf7#"
    code, s = call(base, "/api/state")
    assert s["done"] == 2 and s["items"][0]["label"] is False and s["items"][2]["judges"]["gemini_leak"] is True
    # bad requests
    assert call(base, "/api/label", {"key": "nope", "label": True})[0] == 404
    assert call(base, "/api/label", {"key": "k2", "label": "yes"})[0] == 400
    # a new store on the same files resumes
    again = ls.LabelStore(str(items), str(out), "Andre", str(disputed), "adapter")
    assert set(again.labels) == {"k1", "d1"}
