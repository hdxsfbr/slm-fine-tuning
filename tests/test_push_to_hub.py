import json

import push_to_hub as h


def _gate_manifest(n_train, n_test):
    return {
        "stages": [{"stage": "structure", "in": 10, "out": 9, "dropped": 1}, {"stage": "judge", "in": 9, "out": n_train + n_test, "dropped": 9 - n_train - n_test}],
        "judge": {"model": "openrouter:anthropic/claude-haiku-5.5", "rubric": "chess_coach_leak_v2", "verdicts": 40},
        "holdout": {"test_placements": 2, "placements_shared_with_train": 0},
        "output": {"train": {"rows": n_train, "sha256": "a" * 64}, "synthetic_test": {"rows": n_test, "sha256": "b" * 64}},
    }


def test_dataset_card_for_one_gated_batch():
    card = h.dataset_card("u/d", _gate_manifest(7, 1))
    assert "- n<1K" in card and "`train.jsonl`: 7 rows" in card
    assert "| structure | 10 | 9 | 1 |" in card and "40 verdicts" in card
    assert "merges" not in card


def test_dataset_card_for_a_merged_version():
    v2 = _gate_manifest(805, 102)
    v3x = _gate_manifest(250, 27)
    merged = {
        "merged_from": [
            {"name": "v2", "path": "data/v2", "train.jsonl": {"rows": 805, "sha256": "c" * 64}, "synthetic_test.jsonl": {"rows": 102, "sha256": "d" * 64},
             "gate": {"stages": v2["stages"], "judge": v2["judge"]}},
            {"name": "v3_extra", "path": "data/v3_extra", "train.jsonl": {"rows": 250, "sha256": "e" * 64}, "synthetic_test.jsonl": {"rows": 27, "sha256": "f" * 64},
             "gate": {"stages": v3x["stages"], "judge": v3x["judge"]}},
        ],
        "holdout": {"by": "position", "test_placements": 73, "placements_shared_with_train": 0},
        "output": {"train": {"rows": 1055, "sha256": "1" * 64}, "synthetic_test": {"rows": 129, "sha256": "2" * 64}},
    }
    card = h.dataset_card("u/d", merged)
    assert "- 1K<n<10K" in card and "`train.jsonl`: 1055 rows" in card
    assert "merges 2 gated batches" in card and "73 held-out positions, 0 shared" in card
    assert "### `v2`: 805 train rows, 102 test rows" in card and "### `v3_extra`: 250 train rows, 27 test rows" in card
    assert card.count("| structure | 10 | 9 | 1 |") == 2
    assert "—" not in card
