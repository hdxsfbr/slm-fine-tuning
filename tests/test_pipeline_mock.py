import json
import os

import pytest

from behaviors import BEHAVIORS
from pilot.runner import RunConfig, resume_pilot, run_pilot

QUIET = lambda s: None  # noqa: E731


def _key(r):
    return (r["model"], r["behavior"], r["strategy"], r["scenario_id"], r["repeat"])


def test_mock_run_end_to_end(tmp_path):
    out = str(tmp_path / "out")
    result = run_pilot(RunConfig(models=["mock:a", "mock:flaky"], limit=2, workers=3, out_dir=out), log=QUIET)
    records = result["records"]
    assert len(records) == 2 * len(BEHAVIORS) * 3 * 2  # models x behaviors x strategies x scenarios

    with open(os.path.join(out, "transcripts.jsonl"), encoding="utf-8") as fh:
        lines = [json.loads(line) for line in fh]
    assert len(lines) == len(records)
    for rec in lines:
        for key in ("behavior", "model", "strategy", "scenario_id", "group", "repeat", "system", "messages", "score", "error"):
            assert key in rec
        assert (rec["score"] is None) == (rec["error"] is not None)

    errors = [r for r in records if r["error"]]
    assert errors and all(r["model"] == "mock:flaky" for r in errors)
    assert any(r["score"] for r in records if r["behavior"] == "sycophancy")
    assert any(r["score"] for r in records if r["behavior"] == "tells")
    assert any(r["score"] for r in records if r["behavior"] == "chess_coach")

    text = open(os.path.join(out, "results.md"), encoding="utf-8").read()
    assert "## Behavior: sycophancy" in text
    assert "## Behavior: tells" in text
    assert "## Behavior: chess_coach" in text
    assert "### Ceiling read" in text
    assert "ERROR:" in text
    meta = json.load(open(os.path.join(out, "run.json"), encoding="utf-8"))
    assert meta["jobs"] == len(records) and meta["errors"] == len(errors)


def test_repeats_and_filters(tmp_path):
    result = run_pilot(
        RunConfig(models=["mock:a"], behaviors=["tells"], strategies=["zero_shot"], limit=1, repeats=2, out_dir=str(tmp_path)),
        log=QUIET,
    )
    records = result["records"]
    assert [(r["strategy"], r["repeat"]) for r in records] == [("zero_shot", 0), ("zero_shot", 1)]
    assert "[repeat 1]" in open(result["results"], encoding="utf-8").read() or all(r["score"]["passed"] for r in records)


def test_resume_reruns_only_the_errors(tmp_path):
    out = str(tmp_path)
    first = run_pilot(RunConfig(models=["mock:flaky"], limit=2, workers=1, out_dir=out), log=QUIET)
    first_by_key = {_key(r): r for r in first["records"]}
    error_keys = {k for k, r in first_by_key.items() if r["error"]}
    assert error_keys

    second = resume_pilot(out, workers=2, log=QUIET)
    records = second["records"]
    assert len(records) == len(first["records"])
    assert [_key(r) for r in records] == [_key(r) for r in first["records"]]
    for r in records:
        if _key(r) in error_keys:
            assert r["started_at"] >= second["meta"]["started_at"]  # actually rerun
        else:
            assert r == first_by_key[_key(r)]  # untouched, same timestamps and scores

    meta = json.load(open(os.path.join(out, "run.json"), encoding="utf-8"))
    assert meta["kept_from_previous_run"] == len(first_by_key) - len(error_keys)
    assert meta["config"]["workers"] == 2 and meta["config"]["limit"] == 2
    with open(os.path.join(out, "transcripts.jsonl"), encoding="utf-8") as fh:
        assert len(fh.readlines()) == len(records)


def test_unknown_strategy_or_behavior_rejected(tmp_path):
    with pytest.raises(ValueError):
        run_pilot(RunConfig(models=["mock:a"], strategies=["cot"], out_dir=str(tmp_path)), log=QUIET)
    with pytest.raises(ValueError):
        run_pilot(RunConfig(models=["mock:a"], behaviors=["nope"], out_dir=str(tmp_path)), log=QUIET)


def test_rescore_is_idempotent_and_rewrites_files(tmp_path):
    from rescore import rescore_run

    out = str(tmp_path)
    first = run_pilot(RunConfig(models=["mock:a", "mock:flaky"], limit=2, workers=2, out_dir=out), log=QUIET)
    before = {_key(r): (r["score"], r["error"]) for r in first["records"]}
    results_before = open(first["results"], encoding="utf-8").read()

    second = rescore_run(out)
    after = {_key(r): (r["score"], r["error"]) for r in second["records"]}
    assert after == before
    assert second["meta"]["rescored_at"] and "rescored_git_sha" in second["meta"]
    meta = json.load(open(os.path.join(out, "run.json"), encoding="utf-8"))
    assert meta["rescored_at"] == second["meta"]["rescored_at"]
    with open(os.path.join(out, "transcripts.jsonl"), encoding="utf-8") as fh:
        assert len(fh.readlines()) == len(first["records"])
    results_after = open(first["results"], encoding="utf-8").read()
    assert "- Rescored: " in results_after and "- Rescored: " not in results_before
    assert results_after.split("Decision rule:")[1] == results_before.split("Decision rule:")[1]


def test_scenarios_flag_selects_ids_in_module_order(tmp_path):
    from behaviors import chess_coach as c

    ids = [c.SCENARIOS[3]["id"], c.SCENARIOS[1]["id"]]
    result = run_pilot(
        RunConfig(models=["mock:a"], behaviors=["chess_coach"], strategies=["zero_shot"], scenarios=ids, out_dir=str(tmp_path)),
        log=QUIET,
    )
    assert [r["scenario_id"] for r in result["records"]] == [c.SCENARIOS[1]["id"], c.SCENARIOS[3]["id"]]
    with pytest.raises(ValueError):
        run_pilot(RunConfig(models=["mock:a"], behaviors=["chess_coach"], scenarios=["nope"], out_dir=str(tmp_path)), log=QUIET)


def test_merge_runs_combines_parts_in_job_order(tmp_path):
    from behaviors import chess_coach as c
    from merge_runs import merge_runs
    from pilot.judge import judge_run

    a = str(tmp_path / "a")
    b = str(tmp_path / "b")
    out = str(tmp_path / "merged")
    run_pilot(RunConfig(models=["mock:a", "mock:b"], behaviors=["chess_coach"], limit=2, out_dir=a), log=QUIET)
    judge_run(a, "mock:judge", workers=2, log=QUIET)
    later = [s["id"] for s in c.SCENARIOS[2:4]]
    run_pilot(RunConfig(models=["mock:a", "mock:b"], behaviors=["chess_coach"], scenarios=later, out_dir=b), log=QUIET)
    judge_run(b, "mock:judge", workers=2, log=QUIET)

    result = merge_runs([a, b], out)
    records = result["records"]
    assert len(records) == 2 * 3 * 4
    assert result["meta"]["config"]["scenarios"] == [s["id"] for s in c.SCENARIOS[:4]]
    # job order: model, strategy, then scenario in module order
    first_model = [r for r in records if r["model"] == "mock:a"]
    assert [r["scenario_id"] for r in first_model[:4]] == [s["id"] for s in c.SCENARIOS[:4]]
    assert all(r["judge"] for r in records)
    assert result["meta"]["judge"]["records_judged"] == len(records)
    text = open(os.path.join(out, "results.md"), encoding="utf-8").read()
    assert "n | " in text and "| mock:a | zero_shot | 4 |" in text
    with open(os.path.join(out, "judge.jsonl"), encoding="utf-8") as fh:
        assert len(fh.readlines()) == result["meta"]["judge"]["items"]
