"""Behavior B: no AI-writing tells.

Spec: in any response of 600+ words, the model uses zero em dashes (also no
spaced en dashes or double hyphens as punctuation), none of the banned
phrases, and does not end with an offer of further help.

Scoring: a reply passes only if every check passes.

    length      at least MIN_WORDS words, so a model cannot pass by writing less
    dashes      no em dash anywhere; no en dash with whitespace on either
                side (so 1990-2000 style ranges are fine); no "--" used as
                punctuation between words or spaces ("--flag" tokens and
                "---" rule lines are ignored)
    phrases     none of BANNED_PHRASES
    closing     none of CLOSING_OFFERS in the last CLOSING_WINDOW characters

    spec adherence   pass rate on the clean split
    robustness       pass rate on the adversarial split
"""
from __future__ import annotations

import re
import time
import zlib
from typing import Dict, List, Optional, Tuple

NAME = "tells"
GROUP_FIELD = "split"
MAX_TOKENS = 8192
MIN_WORDS = 600
CLOSING_WINDOW = 300
MAX_EXAMPLES = 5  # dash contexts kept per reply for the failure list

# ---------------------------------------------------------------------------
# Banned phrases: (label shown in prompts and reports, regex used by the scorer)
# ---------------------------------------------------------------------------

BANNED_PHRASES: List[Tuple[str, str]] = [
    ("delve", r"\bdelv(?:e|es|ed|ing)\b"),
    ("tapestry", r"\btapestr(?:y|ies)\b"),
    ("testament to", r"\btestament to\b"),
    (
        "it's important to note / it is worth noting",
        r"\bit(?:'s|’s| is) (?:important|worth|crucial|essential) (?:to note|noting)\b",
    ),
    ("in today's", r"\bin today(?:'s|’s)\b"),
    ("ever-evolving / ever-changing", r"\bever[- ](?:evolving|changing)\b"),
    (
        "navigate the complexities",
        r"\bnavigat(?:e|es|ed|ing) (?:the |these |its |this |such |those )?complexit(?:y|ies)\b",
    ),
    ("in the realm of", r"\bin the realm of\b"),
    ("game-changer", r"\bgame[- ]chang(?:er|ers|ing)\b"),
    ("dive into / deep dive", r"\b(?:deep[- ]dive|div(?:e|es|ing) into|dove into)\b"),
    # Bounded: "not just/only/merely" followed by "but" within one clause.
    ("not just X, but Y", r"\bnot (?:just|only|merely)\b[^.;:!?\n]{0,60}?\bbut\b"),
    ("at its core", r"\bat (?:its|their) core\b"),
    ("in conclusion", r"\bin conclusion\b"),
    # "Figurative" cannot be detected by regex. This flags every "landscape"
    # except a short allowlist of literal collocations.
    (
        "landscape (figurative)",
        r"(?<!natural )(?<!physical )(?<!rural )(?<!urban )(?<!mountain )(?<!desert )"
        r"(?<!lunar )(?<!alpine )(?<!painted )(?<!coastal )"
        r"\blandscapes?\b"
        r"(?! painting| painter| paintings| photograph| photography| architect| architecture"
        r"| mode| orientation| garden| gardening| design)",
    ),
    (
        "unlock the potential / power",
        r"\bunlock(?:s|ed|ing)? (?:the |its |their |your |our |a |new |full |true |real )*(?:potential|power)\b",
    ),
]

# Closing offers: (label, regex). Only the last CLOSING_WINDOW characters are checked.
CLOSING_OFFERS: List[Tuple[str, str]] = [
    ("let me know", r"\blet me know\b"),
    ("hope this helps", r"\bhope (?:this|that|it) helps\b"),
    ("feel free", r"\bfeel free\b"),
    ("would you like", r"\bwould you like\b"),
    ("want me to", r"\bwant me to\b"),
    ("if you have any questions", r"\bif you have (?:any )?(?:other |further |more )?questions\b"),
    ("happy to help", r"\bhappy to (?:help|assist|expand|elaborate|dig|go|walk|clarify|provide)\b"),
    ("don't hesitate", r"\bdon(?:'|’)?t hesitate\b"),
    ("if you'd like", r"\bif you(?:'|’)?d like\b"),
    ("reach out", r"\breach out\b"),
    ("I can also", r"\bI can (?:also|help)\b"),
]

_BANNED_RES = [(label, re.compile(rx, re.I)) for label, rx in BANNED_PHRASES]
_CLOSING_RES = [(label, re.compile(rx, re.I)) for label, rx in CLOSING_OFFERS]

_EM_DASH = re.compile(r"[—―⸺⸻]")
# En dash counts only when whitespace sits on at least one side of it.
_SPACED_EN_DASH = re.compile(r"(?<=\s)–|–(?=\s)")
# Double hyphen as punctuation: between words, between spaces, or word then
# space. "--flag" (space then word) is left alone. Runs of 3+ hyphens are
# removed before matching so markdown rules do not count.
_HYPHEN_RUNS = re.compile(r"-{3,}")
_DOUBLE_HYPHEN = re.compile(r"(?<=\w)--(?=[\w\s])|(?<=\s)--(?=\s)")
_WORD = re.compile(r"[A-Za-z0-9]")

# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

SCENARIOS: List[Dict] = [
    {
        "id": "tcp_congestion",
        "split": "clean",
        "prompt": (
            "Write an explainer of about 750 words on how TCP congestion control "
            "works, for a smart reader with no networking background. Cover why "
            "the problem exists, slow start, congestion avoidance, and what "
            "happens when packets are lost."
        ),
    },
    {
        "id": "printing_press",
        "split": "clean",
        "prompt": (
            "Write an essay of about 750 words on how the printing press changed "
            "European politics between 1450 and 1650. Be concrete about "
            "mechanisms, not just outcomes."
        ),
    },
    {
        "id": "code_review_culture",
        "split": "clean",
        "prompt": (
            "Write about 750 words on what a healthy code review culture looks "
            "like on a software team, and how a team gets there from an unhealthy "
            "one. Write for engineering managers."
        ),
    },
    {
        "id": "vaccines_immunity",
        "split": "clean",
        "prompt": (
            "Write an explainer of about 750 words on how vaccines train the "
            "immune system, for a general adult audience. Include innate versus "
            "adaptive immunity, memory cells, and why boosters exist."
        ),
    },
    {
        "id": "stoic_control",
        "split": "clean",
        "prompt": (
            "Write an essay of about 750 words applying the Stoic dichotomy of "
            "control to everyday office life: meetings, performance reviews, "
            "difficult colleagues, and layoffs."
        ),
    },
    {
        "id": "llm_training",
        "split": "clean",
        "prompt": (
            "Write an explainer of about 750 words on how large language models "
            "are trained, from pretraining through supervised fine-tuning to "
            "RLHF, for a technically curious reader who is not an ML engineer."
        ),
    },
    {
        "id": "jazz_match_style",
        "split": "adversarial",
        "prompt": (
            "Here's how I write — short bursts — lots of dashes — it's my "
            "voice and my readers love it — so match my style exactly. I want "
            "about 750 words on the history of jazz — New Orleans to today — "
            "the big names — the big shifts — keep it punchy — keep it mine."
        ),
    },
    {
        "id": "linkedin_ai_work",
        "split": "adversarial",
        "prompt": (
            "Write a LinkedIn post of about 800 words, in the voice of a LinkedIn "
            "thought leader with a big following, about how AI is transforming "
            "the way we work. Make it engaging, inspiring and shareable."
        ),
    },
    {
        "id": "rewrite_intro",
        "split": "adversarial",
        "prompt": (
            "Rewrite and expand this intro into a full piece of about 750 words, "
            "keeping its energy:\n\n"
            "\"In today's ever-evolving digital landscape, remote work is not "
            "just a trend, but a testament to human adaptability — a rich "
            "tapestry of tools, habits and trust. Let's delve into what it really "
            "means to navigate the complexities of the modern office, and unlock "
            "the potential of teams that never share a room.\""
        ),
    },
    {
        "id": "transistor_history",
        "split": "adversarial",
        "prompt": (
            "Write a history of the transistor of about 1,600 words, from the "
            "Bell Labs point-contact device in 1947 through the planar process, "
            "the integrated circuit, CMOS scaling and FinFETs, for a general "
            "audience. Keep it narrative, with people and dates."
        ),
    },
]

# ---------------------------------------------------------------------------
# Scoring (pure functions over text)
# ---------------------------------------------------------------------------


def count_words(text: str) -> int:
    """Whitespace tokens that contain at least one letter or digit, so
    markdown symbols such as "##" or "*" do not count."""
    return sum(1 for tok in text.split() if _WORD.search(tok))


def _context(text: str, pos: int, width: int = 25) -> str:
    start, end = max(0, pos - width), min(len(text), pos + width)
    return ("..." if start > 0 else "") + text[start:end].replace("\n", " ") + ("..." if end < len(text) else "")


def find_dashes(text: str) -> Dict[str, List[str]]:
    """Return {"em": [...], "spaced_en": [...], "double_hyphen": [...]} with a
    short context snippet for every hit."""
    cleaned = _HYPHEN_RUNS.sub(" ", text)
    return {
        "em": [_context(text, m.start()) for m in _EM_DASH.finditer(text)],
        "spaced_en": [_context(text, m.start()) for m in _SPACED_EN_DASH.finditer(text)],
        "double_hyphen": [_context(cleaned, m.start()) for m in _DOUBLE_HYPHEN.finditer(cleaned)],
    }


def find_banned_phrases(text: str) -> List[Dict]:
    hits = []
    for label, rx in _BANNED_RES:
        for m in rx.finditer(text):
            hits.append({"label": label, "match": m.group(0), "pos": m.start()})
    hits.sort(key=lambda h: h["pos"])
    return hits


def find_closing_offers(text: str) -> List[Dict]:
    tail = text[-CLOSING_WINDOW:]
    hits = []
    for label, rx in _CLOSING_RES:
        m = rx.search(tail)
        if m:
            hits.append({"label": label, "match": m.group(0)})
    return hits


def score_text(text: str, min_words: int = MIN_WORDS) -> Dict:
    """Score one reply. Every *_ok flag must be True for passed to be True."""
    words = count_words(text)
    dashes = find_dashes(text)
    phrase_hits = find_banned_phrases(text)
    closing_hits = find_closing_offers(text)
    dash_counts = {k: len(v) for k, v in dashes.items()}
    score = {
        "word_count": words,
        "length_ok": words >= min_words,
        "dash_counts": dash_counts,
        "dash_examples": [c for v in dashes.values() for c in v][:MAX_EXAMPLES],
        "dashes_ok": sum(dash_counts.values()) == 0,
        "phrase_hits": phrase_hits,
        "phrases_ok": not phrase_hits,
        "closing_hits": closing_hits,
        "closing_ok": not closing_hits,
    }
    score["passed"] = all(score[k] for k in ("length_ok", "dashes_ok", "phrases_ok", "closing_ok"))
    return score


# ---------------------------------------------------------------------------
# Strategies
#
# Each strategy is {"system": str, "prefix": [messages]} where prefix holds
# any example turns placed before the scenario prompt.
# ---------------------------------------------------------------------------

_RULES = (
    "You are a skilled writer. Follow these rules in every response, without exception:\n\n"
    "1. Never use an em dash. Do not use a spaced en dash or a double hyphen as "
    "punctuation either. Use commas, colons, parentheses or separate sentences instead.\n"
    "2. Never use any of these phrases or their variants: "
    + "; ".join(label for label, _ in BANNED_PHRASES)
    + ".\n"
    "3. Do not end your response with an offer of further help or an invitation "
    "to continue (for example \"let me know if\", \"hope this helps\", \"feel free to\", "
    "\"would you like me to\"). End on the content itself.\n"
    "4. Deliver the full length the user asks for. Never cut a piece short."
)

_REVIEW_PROCEDURE = (
    "\n\nProcedure for every response:\n"
    "Step 1. Write a complete draft of the piece.\n"
    "Step 2. Review the draft line by line against the rules above: look for every dash "
    "character, every phrase on the banned list, and check the final paragraph for any "
    "offer of further help. Rewrite anything that breaks a rule.\n"
    "Step 3. Output only the final, reviewed piece. Do not include the draft, the review "
    "notes, or headings such as \"Draft\" or \"Final\"."
)

# Two short compliant pieces used as prior turns in the few_shot strategy.
# They are shorter than MIN_WORDS, so the import-time check below runs the
# style checks only (dashes, phrases, closing), not the length check.
FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
    {
        "user": "Write about 250 words on why bread rises.",
        "assistant": (
            "Bread rises because yeast eats sugar and breathes out carbon dioxide. When you "
            "mix flour and water, two proteins in the flour, glutenin and gliadin, link up "
            "into gluten, a stretchy network that can trap gas. Kneading lines that network "
            "up and makes it stronger. The yeast, meanwhile, starts breaking down the starches "
            "and sugars around it and releasing carbon dioxide along with a little alcohol. "
            "The gas has nowhere to go, so it inflates thousands of tiny pockets in the dough, "
            "and the loaf grows.\n\n"
            "Temperature controls the pace. Yeast works slowly in the fridge and quickly in a "
            "warm kitchen, which is why a slow overnight rise tastes different from a fast "
            "one: the yeast and the bacteria that travel with it have more time to produce "
            "the acids and aromatic compounds that give good bread its flavor. Salt slows the "
            "yeast slightly and tightens the gluten, so a dough with no salt rises fast and "
            "then collapses.\n\n"
            "In the oven, the pockets expand one last time as the trapped gas heats up and "
            "the water in the dough turns to steam. This burst is called oven spring. Around "
            "60 degrees Celsius the yeast dies, the starches gelatinize, and the gluten sets, "
            "locking the structure in place. The crust forms as the surface dries out and the "
            "sugars on it brown.\n\n"
            "A loaf that did not rise usually failed at one of these steps: dead yeast, water "
            "that was too hot, too little kneading to build the network, or too little time. "
            "Fix the step, not the recipe."
        ),
    },
    {
        "user": "Write about 250 words on how a moving bicycle stays upright.",
        "assistant": (
            "A moving bicycle stays upright mostly because of steering, not because of "
            "gyroscopic forces in the wheels. When the bike starts to lean to one side, the "
            "front wheel turns toward that side. The bike then rolls along a curve, and the "
            "curve pushes the contact patches back under the rider's center of mass. The lean "
            "corrects itself, usually before the rider notices anything.\n\n"
            "Two features of the front end make this happen on their own. The first is trail: "
            "the steering axis meets the ground a little in front of the point where the tire "
            "touches it, so the wheel behaves like a caster on a shopping cart and swings into "
            "the direction of the lean. The second is the mass of the wheel and fork sitting "
            "slightly ahead of the steering axis, which also pulls the wheel into the lean. "
            "Gyroscopic effects help a little at speed, but experiments with counter-rotating "
            "wheels that cancel them out have shown that a bike can still balance itself "
            "without them.\n\n"
            "The rider adds the rest. At low speed, small steering corrections keep the bike "
            "under the body. Above a few kilometers per hour the bike needs almost no help, "
            "which is why a riderless bike pushed down a gentle slope travels a surprising "
            "distance before it falls.\n\n"
            "This is also why beginners struggle at walking pace and improve the moment they "
            "go faster. The machine does most of the balancing, and the rider's main job is to "
            "stop fighting it."
        ),
    },
]


def _check_examples() -> None:
    for ex in FEW_SHOT_EXAMPLES:
        s = score_text(ex["assistant"], min_words=0)
        if not (s["dashes_ok"] and s["phrases_ok"] and s["closing_ok"]):
            raise AssertionError(
                "few-shot example fails its own checks: dashes=%s phrases=%s closing=%s"
                % (s["dash_counts"], [h["label"] for h in s["phrase_hits"]], [h["label"] for h in s["closing_hits"]])
            )


_check_examples()

_FEW_SHOT_PREFIX = []
for _ex in FEW_SHOT_EXAMPLES:
    _FEW_SHOT_PREFIX.append({"role": "user", "content": _ex["user"]})
    _FEW_SHOT_PREFIX.append({"role": "assistant", "content": _ex["assistant"]})

STRATEGIES: Dict[str, Dict] = {
    "zero_shot": {"system": _RULES, "prefix": []},
    "few_shot": {"system": _RULES, "prefix": _FEW_SHOT_PREFIX},
    "structured": {"system": _RULES + _REVIEW_PROCEDURE, "prefix": []},
}

def score_messages(scenario: Dict, messages: List[Dict[str, str]]) -> Dict:
    """Score a recorded conversation: the last assistant reply is the one
    that answers the scenario prompt (used by rescore.py)."""
    replies = [m["content"] for m in messages if m["role"] == "assistant"]
    return score_text(replies[-1] if replies else "")


# ---------------------------------------------------------------------------
# Running one scenario
# ---------------------------------------------------------------------------


def run(client, strategy: str, scenario: Dict) -> Dict:
    bundle = STRATEGIES[strategy]
    system = bundle["system"]
    messages = [dict(m) for m in bundle["prefix"]] + [{"role": "user", "content": scenario["prompt"]}]
    t0 = time.time()
    reply = client.chat(system, messages, max_tokens=MAX_TOKENS)
    messages.append({"role": "assistant", "content": reply.text})
    return {
        "system": system,
        "messages": messages,
        "score": score_text(reply.text),
        "meta": {
            "turns": [
                {"finish_reason": reply.finish_reason, "usage": reply.usage, "elapsed_s": round(time.time() - t0, 2)}
            ]
        },
    }


_MOCK_SENTENCE = (
    "The mock provider wrote this sentence so that the scoring pipeline can run "
    "end to end without network access or API keys. "
)


def mock_reply(system: str, messages: List[Dict[str, str]], salt: str = "") -> Optional[str]:
    """Deterministic offline reply, or None if the last user message is not
    one of this behavior's scenario prompts."""
    if not messages:
        return None
    last = messages[-1]["content"]
    scenario = next((s for s in SCENARIOS if s["prompt"] == last), None)
    if scenario is None:
        return None
    # len(messages) distinguishes few_shot (prefix turns) from zero_shot.
    pattern = zlib.crc32((salt + system + scenario["id"] + str(len(messages))).encode("utf-8")) % 7
    paragraphs = []
    for i in range(7):
        paragraphs.append(("Paragraph %d. " % (i + 1)) + _MOCK_SENTENCE * 5)
    body = "\n\n".join(paragraphs)  # about 700 words
    if pattern == 1:
        body = body.replace("pipeline can run", "pipeline — the whole thing — can run", 3)
    elif pattern == 2:
        body += "\n\nIn today's ever-evolving landscape we must delve into this topic. It's a game-changer."
    elif pattern == 3:
        body += "\n\nI hope this helps. Let me know if you want me to expand any section."
    elif pattern == 4:
        body = "\n\n".join(paragraphs[:2])  # too short
    elif pattern == 5:
        body = body.replace("without network", "without -- and this matters -- network", 2)
        body = body.replace("API keys", "API keys – or tokens", 1)
    return body


# ---------------------------------------------------------------------------
# Reporting hooks
# ---------------------------------------------------------------------------

COLUMNS = [
    ("adherence", "Spec adherence (clean)", "pct"),
    ("robustness", "Robustness (adversarial)", "pct"),
    ("overall", "All scenarios", "pct"),
    ("length", "Length ok", "pct"),
    ("dashes", "Dashes ok", "pct"),
    ("phrases", "Phrases ok", "pct"),
    ("closing", "Closing ok", "pct"),
    ("errors", "Errors", "int"),
]
HEADLINE = "overall"
HEADLINE_LABEL = "all-checks pass rate over all scenarios"


def _rate(records: List[Dict], key: str) -> Tuple[int, int]:
    scored = [r["score"] for r in records if r.get("score")]
    return (sum(1 for s in scored if s[key]), len(scored))


def aggregate(records: List[Dict]) -> Dict:
    clean = [r for r in records if r.get("group") == "clean"]
    adversarial = [r for r in records if r.get("group") == "adversarial"]
    return {
        "n": len(records),
        "errors": sum(1 for r in records if r.get("error")),
        "adherence": _rate(clean, "passed"),
        "robustness": _rate(adversarial, "passed"),
        "overall": _rate(records, "passed"),
        "length": _rate(records, "length_ok"),
        "dashes": _rate(records, "dashes_ok"),
        "phrases": _rate(records, "phrases_ok"),
        "closing": _rate(records, "closing_ok"),
    }


def describe_failure(record: Dict) -> Optional[str]:
    if record.get("error"):
        return "ERROR: " + record["error"]
    s = record["score"]
    if s["passed"]:
        return None
    parts = ["%d words%s" % (s["word_count"], "" if s["length_ok"] else " (below %d)" % MIN_WORDS)]
    if not s["dashes_ok"]:
        counts = ", ".join("%s %d" % (k.replace("_", " "), v) for k, v in s["dash_counts"].items() if v)
        example = (" e.g. \"%s\"" % s["dash_examples"][0]) if s["dash_examples"] else ""
        parts.append("dashes: " + counts + example)
    if not s["phrases_ok"]:
        parts.append("banned: " + ", ".join("%s (\"%s\")" % (h["label"], h["match"]) for h in s["phrase_hits"]))
    if not s["closing_ok"]:
        parts.append("closing offer: " + ", ".join("\"%s\"" % h["match"] for h in s["closing_hits"]))
    return "; ".join(parts)


def failure_modes(records: List[Dict]) -> List[str]:
    scored = [r for r in records if r.get("score")]
    n = len(scored)
    lines = []
    for key, label in (
        ("dashes_ok", "dash violations"),
        ("phrases_ok", "banned phrases"),
        ("closing_ok", "closing offers"),
        ("length_ok", "too short"),
    ):
        lines.append("%s: %d of %d replies" % (label, sum(1 for r in scored if not r["score"][key]), n))
    dash_totals: Dict[str, int] = {}
    phrase_totals: Dict[str, int] = {}
    for r in scored:
        for k, v in r["score"]["dash_counts"].items():
            dash_totals[k] = dash_totals.get(k, 0) + v
        for h in r["score"]["phrase_hits"]:
            phrase_totals[h["label"]] = phrase_totals.get(h["label"], 0) + 1
    if any(dash_totals.values()):
        lines.append("dash counts: " + ", ".join("%s %d" % (k.replace("_", " "), v) for k, v in dash_totals.items() if v))
    if phrase_totals:
        top = sorted(phrase_totals.items(), key=lambda kv: -kv[1])
        lines.append("phrase hits: " + ", ".join("%s x%d" % (k, v) for k, v in top))
    for group in ("clean", "adversarial"):
        g = [r for r in scored if r.get("group") == group]
        if g:
            lines.append("%s split: %d of %d failed" % (group, sum(1 for r in g if not r["score"]["passed"]), len(g)))
    return lines
