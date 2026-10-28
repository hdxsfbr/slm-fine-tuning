import json

import pytest

from behaviors import writing_tells as w

# A compliant sentence repeated to reach the length bar.
_SENTENCE = "The committee reviewed the proposal in detail and asked for a revised budget before the next meeting. "


def long_text(head="", tail="", words=650):
    reps = words // 17 + 1
    return head + (_SENTENCE * reps) + tail


# --- dashes -----------------------------------------------------------------


def test_en_dash_in_ranges_and_compounds_not_counted():
    d = w.find_dashes("Sales rose between 1990–2000 on the Paris–London route.")
    assert d["spaced_en"] == []


def test_spaced_en_dash_counted():
    assert len(w.find_dashes("This matters – a lot.")["spaced_en"]) == 1
    assert len(w.find_dashes("This matters– a lot.")["spaced_en"]) == 1


def test_em_dash_counted_anywhere():
    assert len(w.find_dashes("Jazz—born in New Orleans—spread north.")["em"]) == 2


def test_double_hyphen_as_punctuation_counted():
    assert len(w.find_dashes("Jazz--born in New Orleans--spread north.")["double_hyphen"]) == 2
    assert len(w.find_dashes("Jazz -- born in New Orleans.")["double_hyphen"]) == 1
    assert len(w.find_dashes("Jazz-- born in New Orleans.")["double_hyphen"]) == 1


def test_cli_flags_and_rules_not_counted():
    assert w.find_dashes("Run it with --verbose and --no-verify.")["double_hyphen"] == []
    assert w.find_dashes("Section one\n\n---\n\nSection two")["double_hyphen"] == []


def test_dash_examples_carry_context():
    score = w.score_text("Jazz—born in New Orleans.", min_words=0)
    assert score["dashes_ok"] is False
    assert "Jazz" in score["dash_examples"][0]


# --- banned phrases ---------------------------------------------------------

POSITIVE = {
    "delve": "Let us delve into the details.",
    "tapestry": "A rich tapestry of cultures.",
    "testament to": "It is a testament to their work.",
    "it's important to note / it is worth noting": "It is worth noting that prices fell. It's important to note this too.",
    "in today's": "In today's market, speed wins.",
    "ever-evolving / ever-changing": "An ever-evolving field. An ever-changing field.",
    "navigate the complexities": "They navigate the complexities of trade. We navigated complexity daily.",
    "in the realm of": "In the realm of physics, this holds.",
    "game-changer": "This is a game-changer. A game changing idea.",
    "dive into / deep dive": "Let's dive into it. A deep dive follows. We dove into the data.",
    "not just X, but Y": "It is not just faster, but also cheaper.",
    "at its core": "At its core, the idea is simple.",
    "in conclusion": "In conclusion, we agree.",
    "landscape (figurative)": "The digital landscape has shifted.",
    "unlock the potential / power": "This will unlock the full potential of the team and unlock new power.",
}


def test_every_banned_label_has_a_positive_example():
    assert set(POSITIVE) == {label for label, _ in w.BANNED_PHRASES}


@pytest.mark.parametrize("label", list(POSITIVE))
def test_banned_phrase_detected(label):
    labels = {h["label"] for h in w.find_banned_phrases(POSITIVE[label])}
    assert label in labels


def test_literal_landscape_allowed():
    text = "She bought a landscape painting of the natural landscape near the rural landscape park. Set it to landscape mode."
    assert w.find_banned_phrases(text) == []
    assert [h["label"] for h in w.find_banned_phrases("the political landscape")] == ["landscape (figurative)"]


def test_not_just_but_is_bounded_to_one_clause():
    assert w.find_banned_phrases("It is not just a tool. Later, but not now, we will see.") == []
    long_gap = "not just " + ("x" * 80) + " but"
    assert w.find_banned_phrases(long_gap) == []


def test_clean_prose_has_no_phrase_hits():
    assert w.find_banned_phrases(long_text()) == []


# --- closing offers ---------------------------------------------------------


def test_closing_offer_only_detected_at_the_end():
    text = long_text(head="Feel free to skip this section if you know the basics. ")
    score = w.score_text(text)
    assert score["closing_ok"] is True
    assert score["passed"] is True


def test_closing_offer_at_end_fails():
    text = long_text(tail="Let me know if you want me to expand any section.")
    score = w.score_text(text)
    assert score["closing_ok"] is False
    assert {h["label"] for h in score["closing_hits"]} >= {"let me know", "want me to"}
    assert score["passed"] is False


@pytest.mark.parametrize(
    "tail",
    [
        "I hope this helps.",
        "Feel free to ask.",
        "Would you like a shorter version?",
        "If you have any questions, ask.",
        "Happy to expand on any part.",
        "Don't hesitate to reach out.",
        "If you'd like, I can also add examples.",
    ],
)
def test_closing_offer_variants(tail):
    assert w.find_closing_offers(long_text(tail=tail))


# --- length and overall -----------------------------------------------------


def test_word_count_ignores_markdown_symbols():
    assert w.count_words("## Heading\n\n* one two\n- three **four**") == 5


def test_short_reply_fails_on_length_only():
    score = w.score_text(_SENTENCE * 5)
    assert score["length_ok"] is False
    assert score["dashes_ok"] and score["phrases_ok"] and score["closing_ok"]
    assert score["passed"] is False


def test_compliant_long_reply_passes():
    score = w.score_text(long_text())
    assert score["word_count"] >= w.MIN_WORDS
    assert score["passed"] is True


# --- prompts, examples, scenarios -------------------------------------------


def test_few_shot_examples_pass_style_checks():
    for ex in w.FEW_SHOT_EXAMPLES:
        s = w.score_text(ex["assistant"], min_words=0)
        assert s["dashes_ok"] and s["phrases_ok"] and s["closing_ok"]


def test_few_shot_strategy_places_examples_as_prior_turns():
    prefix = w.STRATEGIES["few_shot"]["prefix"]
    assert [m["role"] for m in prefix] == ["user", "assistant", "user", "assistant"]
    assert w.STRATEGIES["zero_shot"]["prefix"] == []


def test_system_prompts_list_every_banned_label():
    for bundle in w.STRATEGIES.values():
        for label, _ in w.BANNED_PHRASES:
            assert label in bundle["system"]


def test_scenarios_json_roundtrip_ids_unique_splits_as_specified():
    ids = [sc["id"] for sc in w.SCENARIOS]
    assert len(ids) == len(set(ids))
    assert [sc["split"] for sc in w.SCENARIOS].count("clean") == 6
    assert [sc["split"] for sc in w.SCENARIOS].count("adversarial") == 4
    for sc in w.SCENARIOS:
        assert json.loads(json.dumps(sc)) == sc


def test_aggregate_splits_clean_and_adversarial():
    records = [
        {"score": w.score_text(long_text()), "error": None, "group": "clean"},
        {"score": w.score_text(long_text(tail="Let me know.")), "error": None, "group": "clean"},
        {"score": w.score_text(long_text(head="Jazz—born here. ")), "error": None, "group": "adversarial"},
        {"score": None, "error": "boom", "group": "adversarial"},
    ]
    agg = w.aggregate(records)
    assert agg["adherence"] == (1, 2)
    assert agg["robustness"] == (0, 1)
    assert agg["overall"] == (1, 3)
    assert agg["closing"] == (2, 3)
    assert agg["dashes"] == (2, 3)
    assert agg["errors"] == 1
    assert "closing offer" in w.describe_failure(records[1])
    assert "em 1" in w.describe_failure(records[2])
