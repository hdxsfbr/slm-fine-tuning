import json
import os

import pytest

from behaviors import chess_coach as c
from pilot import judge as j
from pilot.runner import RunConfig, run_pilot

QUIET = lambda s: None  # noqa: E731


# --- parsing -----------------------------------------------------------------


@pytest.mark.parametrize(
    "text, leak, reasoning",
    [
        ('{"leak": true, "reasoning": "names f7"}', True, "names f7"),
        ('```json\n{"leak": false, "reasoning": "theme only"}\n```', False, "theme only"),
        ('Verdict:\n{"leak": true,\n "reasoning": "describes the capture"}\nDone.', True, "describes the capture"),
        ('{"leak": true, "reasoning": "unterminated', True, "unterminated"),
    ],
)
def test_parse_verdict(text, leak, reasoning):
    v = j.parse_verdict(text)
    assert v["leak"] is leak and v["reasoning"] == reasoning


def test_parse_verdict_rejects_garbage():
    with pytest.raises(ValueError):
        j.parse_verdict("I think it leaks.")
    with pytest.raises(ValueError):
        j.parse_verdict('{"leak": "yes"}')


# --- items, prompt, aggregate ------------------------------------------------


def _record(sid="fork_mixed", replies=None):
    s = next(x for x in c.SCENARIOS if x["id"] == sid)
    replies = replies or [t["example"] if t["kind"] == "normal" else c._MOCK_HINT for t in s["turns"]]
    messages = []
    for t, r in zip(s["turns"], replies):
        messages.append({"role": "user", "content": t["user"]})
        messages.append({"role": "assistant", "content": r})
    return {
        "model": "mock:a", "behavior": "chess_coach", "strategy": "zero_shot", "scenario_id": sid, "repeat": 0,
        "group": s["split"], "messages": messages, "score": c.score_conversation(s, replies), "error": None,
    }


def test_judge_items_cover_hint_turns_only():
    rec = _record()
    items = c.judge_items(rec)
    s = next(x for x in c.SCENARIOS if x["id"] == "fork_mixed")
    assert [it["turn"] for it in items] == [i for i, t in enumerate(s["turns"]) if t["kind"] != "normal"]
    assert all(it["answer"] == "Nc7+" and "knight d5" in it["position"] and it["position"].startswith("FEN:") for it in items)
    assert "What should I play?" not in items[0]["position"]
    system, user = c.judge_prompt(items[0])
    assert "JSON" in system and c.SPEC in user and "Nc7+" in user and items[0]["reply"] in user
    assert '{"leak": true or false' in user


def test_judge_aggregate_states():
    rec = _record()
    assert c.judge_aggregate(rec, {}, "mock:j") is None
    clean = c.judge_aggregate(rec, {0: {"leak": False, "reasoning": "", "error": None}}, "mock:j")
    assert clean["leak_free"] is True and clean["final_pass"] is True and clean["errors"] == 0
    assert clean["turns"][0]["leak"] is False and clean["turns"][1] is None
    leaked = c.judge_aggregate(rec, {0: {"leak": False, "reasoning": "", "error": None}, 2: {"leak": True, "reasoning": "describes it", "error": None}}, "mock:j")
    assert leaked["leak_free"] is False and leaked["final_pass"] is False
    errored = c.judge_aggregate(rec, {0: {"leak": None, "reasoning": "", "error": "HTTP 500"}}, "mock:j")
    assert errored["leak_free"] is None and errored["final_pass"] is False and errored["errors"] == 1


def test_aggregate_and_failures_use_the_judge():
    rec = _record()
    assert c.aggregate([rec])["final"] == (1, 1) and c.aggregate([rec])["judge_leak_free"] == (0, 0)
    rec["judge"] = c.judge_aggregate(rec, {2: {"leak": True, "reasoning": "says which piece captures what", "error": None}}, "mock:j")
    agg = c.aggregate([rec])
    assert agg["overall"] == (1, 1) and agg["judge_leak_free"] == (0, 1) and agg["final"] == (0, 1)
    desc = c.describe_failure(rec)
    assert "turn 3 (disguise) judged a leak: says which piece captures what" in desc
    modes = "\n".join(c.failure_modes([rec]))
    assert "identify the move by description: 1 of 1 judged" in modes and "disguise 1" in modes


# --- end to end with the mock provider --------------------------------------


def test_mock_judge_run_is_incremental(tmp_path):
    out = str(tmp_path)
    run_pilot(RunConfig(models=["mock:a"], behaviors=["chess_coach"], strategies=["zero_shot"], limit=3, out_dir=out), log=QUIET)
    first = j.judge_run(out, "mock:judge", workers=2, log=QUIET)
    n_items = first["meta"]["judge"]["items"]
    assert n_items > 0 and first["judged_now"] == n_items and first["errors"] == 0
    assert first["meta"]["judge"]["records_judged"] == 3
    with open(os.path.join(out, "judge.jsonl"), encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    assert len(rows) == n_items and all(r["rubric"] == c.JUDGE_RUBRIC_VERSION for r in rows)
    with open(os.path.join(out, "transcripts.jsonl"), encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh]
    assert all(r["judge"] and r["judge"]["model"] == "mock:judge" for r in records)
    assert any(r["judge"]["leak_free"] is False for r in records) or all(r["judge"]["leak_free"] for r in records)
    text = open(os.path.join(out, "results.md"), encoding="utf-8").read()
    assert "- Judge: mock:judge" in text and "No described leaks (judge)" in text

    second = j.judge_run(out, "mock:judge", workers=2, log=QUIET)
    assert second["judged_now"] == 0
    with open(os.path.join(out, "judge.jsonl"), encoding="utf-8") as fh:
        assert len(fh.readlines()) == n_items


def test_sample_and_agreement(tmp_path):
    out = str(tmp_path)
    run_pilot(RunConfig(models=["mock:a", "mock:b"], behaviors=["chess_coach"], limit=4, out_dir=out), log=QUIET)
    rows = j.sample_items(out, 12, seed=0)
    assert len(rows) == 12 and len({r["key"] for r in rows}) == 12
    assert len({r["kind"] for r in rows}) >= 6
    assert rows == j.sample_items(out, 12, seed=0)
    assert all(r["label"] is None for r in rows)

    j.judge_run(out, "mock:judge", workers=2, log=QUIET)
    judgments = j.load_judgments(out)
    for i, r in enumerate(rows):
        r["label"] = bool(judgments[r["key"]]["leak"])
        if i == 0:
            r["label"] = not r["label"]
            r["note"] = "flipped on purpose"
    rows[1]["label"] = None  # unlabeled rows are skipped
    labels = os.path.join(out, "labels.jsonl")
    j.write_labels_template(rows, labels)
    result = j.agreement(out, labels)
    assert result["labeled"] == 11 and result["compared"] == 11 and result["agree"] == 10
    assert len(result["disagreements"]) == 1 and result["disagreements"][0]["note"] == "flipped on purpose"
    assert "agreement 91% (10 of 11)" in j.render_agreement(result)


def test_verdicts_are_kept_per_judge(tmp_path):
    out = str(tmp_path)
    run_pilot(RunConfig(models=["mock:a"], behaviors=["chess_coach"], strategies=["zero_shot"], limit=2, out_dir=out), log=QUIET)
    first = j.judge_run(out, "mock:judge_one", workers=2, log=QUIET)
    n = first["meta"]["judge"]["items"]
    second = j.judge_run(out, "mock:judge_two", workers=2, log=QUIET)
    assert second["judged_now"] == n  # a new judge starts from zero
    assert len(j.load_judgments(out, "mock:judge_one")) == n
    assert len(j.load_judgments(out, "mock:judge_two")) == n
    assert len(j.load_judgments(out)) == n  # later lines replace earlier ones per key
    assert j.current_judge(out) == "mock:judge_two"
    with open(os.path.join(out, "transcripts.jsonl"), encoding="utf-8") as fh:
        assert all(json.loads(line)["judge"]["model"] == "mock:judge_two" for line in fh)


def test_rubric_change_rejudges_everything(tmp_path, monkeypatch):
    out = str(tmp_path)
    run_pilot(RunConfig(models=["mock:a"], behaviors=["chess_coach"], strategies=["zero_shot"], limit=2, out_dir=out), log=QUIET)
    first = j.judge_run(out, "mock:judge", workers=2, log=QUIET)
    n = first["meta"]["judge"]["items"]
    monkeypatch.setattr(c, "JUDGE_RUBRIC_VERSION", "chess_coach_leak_test_v9")
    assert j.load_judgments(out, "mock:judge") == {}
    assert len(j.load_judgments(out, "mock:judge", current_rubric=False)) == n
    second = j.judge_run(out, "mock:judge", workers=2, log=QUIET)
    assert second["judged_now"] == n and second["meta"]["judge"]["rubrics"] == ["chess_coach_leak_test_v9"]


# --- empty replies -----------------------------------------------------------


class _FlakyJudge:
    """Raises EmptyReplyError for the first `empty` calls, then answers; a
    small max_tokens keeps failing so the fallback path can be exercised."""

    provider = "openrouter"

    def __init__(self, empty, min_tokens=0):
        self.empty = empty
        self.min_tokens = min_tokens
        self.calls = []

    def chat(self, system, messages, max_tokens):
        from pilot.clients import EmptyReplyError, Reply

        self.calls.append(max_tokens)
        if len(self.calls) <= self.empty or max_tokens < self.min_tokens:
            raise EmptyReplyError("empty reply (finish_reason=length)")
        return Reply(text='{"leak": false, "reasoning": "theme only"}', usage={"input_tokens": 1, "output_tokens": 1})


def test_judge_item_retries_an_empty_reply_with_a_larger_budget():
    item = c.judge_items(_record())[0]
    client = _FlakyJudge(empty=1)
    verdict = j.judge_item(client, c, item, "k")
    assert verdict["leak"] is False and verdict["retry"] == "max_tokens %d" % j.RETRY_MAX_TOKENS
    assert client.calls == [j.MAX_TOKENS, j.RETRY_MAX_TOKENS]
    # a clean first answer records no retry
    verdict = j.judge_item(_FlakyJudge(empty=0), c, item, "k")
    assert "retry" not in verdict


def test_judge_item_falls_back_to_the_reasoning_off_client():
    from pilot.clients import EmptyReplyError

    item = c.judge_items(_record())[0]
    always_empty = _FlakyJudge(empty=99)
    fallback = _FlakyJudge(empty=0)
    verdict = j.judge_item(always_empty, c, item, "k", fallback=fallback)
    assert verdict["retry"] == "reasoning off" and fallback.calls == [j.MAX_TOKENS]
    assert always_empty.calls == [j.MAX_TOKENS, j.RETRY_MAX_TOKENS]
    with pytest.raises(EmptyReplyError):
        j.judge_item(_FlakyJudge(empty=99), c, item, "k")
