"""judge_check.py: a second judge on a copy of a run, compared item by item."""
import json
import os

import pytest

import eval as evalcli
import judge_check


def _build(tmp_path, with_baseline=True):
    src = str(tmp_path / "eval")
    argv = ["--model", "mock:tuned", "--eval-set", "challenge", "--limit", "3", "--judge", "mock:judge", "--out", src]
    if with_baseline:
        argv += ["--baseline", "mock:base"]
    assert evalcli.main(argv) == 0
    return src


def test_judge_check_copies_rejudges_and_compares(tmp_path):
    src = _build(tmp_path)
    before = open(os.path.join(src, "judge.jsonl")).read()
    out = str(tmp_path / "check")
    assert judge_check.main([src, "--judge", "mock:judge2", "--out", out]) == 0
    # the source run is untouched
    assert open(os.path.join(src, "judge.jsonl")).read() == before
    assert json.load(open(os.path.join(src, "run.json")))["judge"]["model"] == "mock:judge"
    # the copy holds both judges' verdicts and reports under the second
    rows = [json.loads(l) for l in open(os.path.join(out, "judge.jsonl"))]
    assert {r["judge"] for r in rows} == {"mock:judge", "mock:judge2"}
    meta = json.load(open(os.path.join(out, "run.json")))
    assert meta["judge"]["model"] == "mock:judge2"
    assert meta["judge_check"]["source"] == src and meta["judge_check"]["first_judge"] == "mock:judge"
    result = json.load(open(os.path.join(out, "judge_check.json")))
    assert result["judge_a"] == "mock:judge" and result["judge_b"] == "mock:judge2"
    assert result["items_common"] == result["items_a"] == result["items_b"] > 0
    c = result["confusion"]
    assert c["both_leak"] + c["a_only"] + c["b_only"] + c["neither"] == result["items_common"]
    assert result["agree"] == c["both_leak"] + c["neither"]
    assert len(result["disagreements"]) == c["a_only"] + c["b_only"]
    assert sum(d["n"] for d in result["by_kind"].values()) == result["items_common"]
    assert set(result["cells"]) == {"mock:base / zero_shot", "mock:tuned / zero_shot"}
    assert all(set(v) == {"mock:judge", "mock:judge2"} for v in result["cells"].values())
    assert all(v[s]["final"][1] == 3 for v in result["cells"].values() for s in v)
    text = open(os.path.join(out, "judge_check.md")).read()
    assert text.startswith("# Second-family judge check") and "Cohen's kappa" in text and "mock:judge2" in text
    assert "## Per model and strategy" in text and "## Disagreements" in text


def test_judge_check_cell_filter_and_labels(tmp_path):
    src = _build(tmp_path)
    from pilot.judge import sample_items, write_labels_template

    rows = sample_items(src, 4, 0)
    for row in rows:
        row["label"] = True
    labels = str(tmp_path / "labels.jsonl")
    write_labels_template(rows, labels)
    out = str(tmp_path / "check")
    assert judge_check.main([src, "--judge", "mock:judge2", "--out", out, "--cell", "mock:tuned", "zero_shot", "--labels", labels]) == 0
    recs = [json.loads(l) for l in open(os.path.join(out, "transcripts.jsonl"))]
    assert {r["model"] for r in recs} == {"mock:tuned"} and len(recs) == 3
    rows = [json.loads(l) for l in open(os.path.join(out, "judge.jsonl"))]
    assert {r["model"] for r in rows} == {"mock:tuned"}
    meta = json.load(open(os.path.join(out, "run.json")))
    assert meta["config"]["models"] == ["mock:tuned"] and meta["judge_check"]["cells"] == [["mock:tuned", "zero_shot"]]
    result = json.load(open(os.path.join(out, "judge_check.json")))
    assert set(result["cells"]) == {"mock:tuned / zero_shot"}
    assert set(result["labels"]) == {"path", "mock:judge", "mock:judge2"}
    text = open(os.path.join(out, "judge_check.md")).read()
    assert "## Against the hand labels" in text and "### mock:judge2" in text


def test_judge_check_refuses_the_same_judge_and_empty_cells(tmp_path):
    src = _build(tmp_path, with_baseline=False)
    with pytest.raises(SystemExit):
        judge_check.main([src, "--judge", "mock:judge", "--out", str(tmp_path / "x")])
    with pytest.raises(SystemExit):
        judge_check.main([src, "--judge", "mock:judge2", "--out", str(tmp_path / "y"), "--cell", "mock:nobody", "zero_shot"])


def test_kappa():
    assert judge_check.kappa(10, 0, 0, 10) == 1.0
    assert judge_check.kappa(0, 0, 0, 0) is None
    assert abs(judge_check.kappa(5, 5, 5, 5)) < 1e-9


def test_calibrate_fresh_tags_the_verdicts_file(tmp_path):
    import run_judge
    from pilot.judge import sample_items, write_labels_template

    src = _build(tmp_path, with_baseline=False)
    rows = sample_items(src, 3, 0)
    for row in rows:
        row["label"] = False
    labels = str(tmp_path / "labels.jsonl")
    write_labels_template(rows, labels)
    before = open(os.path.join(src, "judge.jsonl")).read()
    assert run_judge.main(["calibrate", src, "--labels", labels, "--judge", "mock:judge2", "--fresh", "--tag", "second"]) == 0
    assert run_judge.main(["calibrate", src, "--labels", labels, "--judge", "mock:judge2", "--fresh"]) == 0
    assert open(os.path.join(src, "judge.jsonl")).read() == before
    tagged = [json.loads(l) for l in open(labels + ".second.jsonl")]
    default = [json.loads(l) for l in open(labels + ".default.jsonl")]
    assert len(tagged) == len(default) == 3
    assert {r["judge"] for r in tagged} == {"mock:judge2"} and {r["key"] for r in tagged} == {r["key"] for r in rows}
