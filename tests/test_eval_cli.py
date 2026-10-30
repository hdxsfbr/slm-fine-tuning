"""eval.py: one command for base vs tuned, judged, on the mock provider."""
import json
import os

import eval as evalcli
from pilot import local_client


def test_normalize_spec_and_revision():
    assert evalcli.normalize_spec("andrebatista/qwen3-chess-coach") == "local:andrebatista/qwen3-chess-coach"
    assert evalcli.normalize_spec("models/v1/adapter") == "local:models/v1/adapter"
    assert evalcli.normalize_spec("openrouter:anthropic/claude-haiku-5.5") == "openrouter:anthropic/claude-haiku-5.5"
    assert evalcli.normalize_spec("mock:x") == "mock:x"
    assert evalcli.with_revision("local:org/repo", "abc123") == "local:org/repo@abc123"
    assert evalcli.with_revision("local:org/repo@def", "abc123") == "local:org/repo@def"
    assert evalcli.with_revision("mock:x", "abc123") == "mock:x"


def test_split_revision_and_local_adapter_config(tmp_path):
    assert local_client.split_revision("org/repo@abc") == ("org/repo", "abc")
    assert local_client.split_revision("org/repo") == ("org/repo", None)
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": "unsloth/Qwen3-1.7B"}))
    assert local_client.split_revision(str(adapter)) == (str(adapter), None)
    assert local_client.adapter_config(str(adapter))["base_model_name_or_path"] == "unsloth/Qwen3-1.7B"
    assert local_client.adapter_config(str(tmp_path)) is None


def test_eval_one_command_with_baseline_and_judge(tmp_path):
    out = str(tmp_path / "eval")
    rc = evalcli.main(["--model", "mock:tuned", "--baseline", "mock:base", "--eval-set", "challenge", "--limit", "3", "--judge", "mock:judge", "--out", out])
    assert rc == 0
    meta = json.load(open(os.path.join(out, "run.json")))
    assert meta["config"]["models"] == ["mock:base", "mock:tuned"]
    assert meta["eval"]["baseline"] == "mock:base" and meta["eval"]["model"] == "mock:tuned"
    assert meta["judge"]["model"] == "mock:judge" and meta["judge"]["records_judged"] == 6
    text = open(os.path.join(out, "results.md")).read()
    assert text.startswith("# Evaluation: challenge")
    assert "### Base vs tuned" in text and "Tuned minus base" in text and "Ceiling read" not in text
    assert "Spec adherence (turns)" in text and "Robustness (Final)" in text
    recs = [json.loads(l) for l in open(os.path.join(out, "transcripts.jsonl"))]
    assert len(recs) == 6 and all(r.get("judge") for r in recs)
    assert os.path.exists(os.path.join(out, "judge.jsonl"))


def test_export_judgments_writes_one_line_per_judged_turn(tmp_path):
    from pilot.judge import export_judgments

    out = str(tmp_path / "eval")
    assert evalcli.main(["--model", "mock:tuned", "--eval-set", "challenge", "--limit", "2", "--judge", "mock:judge", "--out", out]) == 0
    path = str(tmp_path / "judged.jsonl")
    n = export_judgments(out, path)
    rows = [json.loads(l) for l in open(path)]
    assert n == len(rows) > 0
    assert set(rows[0]) >= {"model", "scenario_id", "turn", "kind", "user", "reply", "leak", "reasoning", "judge", "rubric"}
    assert all(r["kind"] != "normal" and r["reply"] and r["user"] for r in rows)
    assert all(isinstance(r["leak"], bool) for r in rows)


# --- the brief's literal command --------------------------------------------------


def test_defaults_make_the_literal_command_complete(monkeypatch):
    import datetime as dt

    args = evalcli.resolve_defaults(evalcli.parse_args(["--model", "hdxsfbr/qwen3-1.7b-chess-coach-hints@5f3bb80", "--eval-set", "challenge"]))
    assert args.baseline == evalcli.DEFAULT_BASELINE and args.judge == evalcli.DEFAULT_JUDGE
    assert args.out == "results/eval_qwen3-1-7b-chess-coach-hints_%s" % dt.date.today().isoformat()
    args = evalcli.resolve_defaults(evalcli.parse_args(["--model", "models/v3c/adapter", "--no-baseline", "--no-judge", "--out", "x"]))
    assert args.baseline is None and args.judge is None and args.out == "x"
    # provider specs get no defaults, so mock runs stay offline
    args = evalcli.resolve_defaults(evalcli.parse_args(["--model", "mock:tuned", "--out", "y"]))
    assert args.baseline is None and args.judge is None
    # a missing judge key stops the run before any model loads
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert evalcli.missing_judge_key(evalcli.DEFAULT_JUDGE) == "OPENROUTER_API_KEY"
    assert evalcli.missing_judge_key("mock:judge") is None
    assert evalcli.main(["--model", "hdxsfbr/qwen3-1.7b-chess-coach-hints", "--eval-set", "challenge"]) == 2
