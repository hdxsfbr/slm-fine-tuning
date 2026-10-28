"""Behavior registry.

Each behavior is one module that exposes the following contract:

    NAME            short name used on the CLI and in transcripts
    GROUP_FIELD     scenario key used to split results (e.g. "tier" or "split")
    SCENARIOS       list of JSON-serializable dicts, each with a unique "id"
    STRATEGIES      dict of strategy name -> system prompt (or prompt bundle)
    MAX_TOKENS      generation budget passed to the client for each turn
    run(client, strategy, scenario) -> {"system", "messages", "score", "meta"}
    score_*(...)    pure scoring functions over text, reusable by eval.py
    score_messages(scenario, messages) -> score   the score of a recorded
                    conversation, so rescore.py can apply scorer fixes to
                    finished runs
    mock_reply(system, messages, salt) -> str | None   deterministic offline reply
    COLUMNS         [(metric key, column label, "pct" | "int")] for results.md
    HEADLINE        metric key the ceiling decision rule reads
    aggregate(records) -> dict of metric values for one model x strategy cell
    describe_failure(record) -> str | None, one line per failed conversation
    failure_modes(records) -> list[str], a tally of what still fails

Optional LLM-judge hooks, used by pilot/judge.py when present:

    JUDGE_RUBRIC_VERSION   string recorded with every verdict
    judge_items(record) -> list of dicts with at least "turn" and "kind"
    judge_prompt(item) -> (system, user) for one judge call
    judge_aggregate(record, verdicts, judge_spec) -> the record's "judge"
                    field (or None), where verdicts maps turn index to
                    {"leak", "reasoning", "error"}
    aggregate() and describe_failure() read record["judge"] when it exists.

The scorers never touch a client, and the scenarios are plain dicts, so the
same modules can later be driven by a local Hugging Face model and by scenario
sets loaded from JSONL files.
"""
from __future__ import annotations

from . import chess_coach, sycophancy, writing_tells

BEHAVIORS = {
    sycophancy.NAME: sycophancy,
    writing_tells.NAME: writing_tells,
    chess_coach.NAME: chess_coach,
}

__all__ = ["BEHAVIORS", "chess_coach", "sycophancy", "writing_tells"]
