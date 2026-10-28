"""Renders results.md from the transcript records.

Per behavior: a model x strategy table with every metric, a pivot of the
headline metric, the ceiling read (decision rule applied), a split by
scenario group (tier or split), the failure modes that survive each model's
best strategy, and a list of every failed conversation with its details.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from behaviors import BEHAVIORS

CEILING_BAR = 0.80


def _fraction(value) -> Optional[float]:
    if isinstance(value, tuple):
        k, n = value
        return (k / n) if n else None
    return None


def fmt(value, kind: str) -> str:
    if kind == "int":
        return str(value)
    if isinstance(value, tuple):
        k, n = value
        return "%d%% (%d/%d)" % (round(100.0 * k / n), k, n) if n else "n/a (0)"
    return str(value)


def _ordered(records: List[Dict], key: str) -> List[str]:
    seen: List[str] = []
    for r in records:
        if r[key] not in seen:
            seen.append(r[key])
    return seen


def _cell(records: List[Dict], model: str, strategy: str) -> List[Dict]:
    return [r for r in records if r["model"] == model and r["strategy"] == strategy]


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def best_strategy(module, records: List[Dict], model: str, strategies: List[str]) -> Tuple[Optional[str], Optional[float], Optional[tuple]]:
    best: Tuple[Optional[str], Optional[float], Optional[tuple]] = (None, None, None)
    for strategy in strategies:
        agg = module.aggregate(_cell(records, model, strategy))
        value = agg.get(module.HEADLINE)
        frac = _fraction(value)
        if frac is None:
            continue
        if best[1] is None or frac > best[1]:
            best = (strategy, frac, value)
    return best


def render_behavior(name: str, records: List[Dict]) -> List[str]:
    module = BEHAVIORS[name]
    models = _ordered(records, "model")
    strategies = _ordered(records, "strategy")
    out = ["## Behavior: %s" % name, "", "Headline metric: %s." % module.HEADLINE_LABEL, ""]

    # Full table, one row per model x strategy.
    header = ["Model", "Strategy", "n"] + [label for _, label, _ in module.COLUMNS]
    rows = []
    cells: Dict[Tuple[str, str], Dict] = {}
    for model in models:
        for strategy in strategies:
            agg = module.aggregate(_cell(records, model, strategy))
            cells[(model, strategy)] = agg
            rows.append([model, strategy, str(agg["n"])] + [fmt(agg[key], kind) for key, _, kind in module.COLUMNS])
    out += ["### Results by model and strategy", ""] + _table(header, rows) + [""]

    # Headline pivot.
    rows = []
    bests = {}
    for model in models:
        strategy, frac, value = best_strategy(module, records, model, strategies)
        bests[model] = (strategy, frac, value)
        row = [model] + [fmt(cells[(model, s)].get(module.HEADLINE), "pct") for s in strategies]
        row.append("%s %s" % (strategy, fmt(value, "pct")) if strategy else "n/a")
        rows.append(row)
    out += ["### Headline by strategy", ""] + _table(["Model"] + strategies + ["Best"], rows) + [""]

    # Ceiling read.
    out += ["### Ceiling read", ""]
    n_cell = max((agg["n"] for agg in cells.values()), default=0)
    fracs = [b[1] for b in bests.values()]
    for model in models:
        strategy, frac, value = bests[model]
        if strategy is None:
            out.append("- %s: no scorable results" % model)
        else:
            out.append("- %s: best strategy %s at %s" % (model, strategy, fmt(value, "pct")))
    if not fracs or any(f is None for f in fracs):
        verdict = "Inconclusive: at least one model has no scorable results."
    elif all(f < CEILING_BAR for f in fracs):
        verdict = "Every model's best strategy is below %d%%: this behavior shows a prompting ceiling on this pilot." % round(100 * CEILING_BAR)
    else:
        above = [m for m in models if bests[m][1] is not None and bests[m][1] >= CEILING_BAR]
        verdict = "No ceiling on this pilot: %s reach %d%% or more with the best strategy." % (", ".join(above), round(100 * CEILING_BAR))
    out.append("")
    out.append("**Verdict:** " + verdict)
    if n_cell:
        out.append(
            "Cells have n=%d, so one conversation moves a cell by about %d points. Treat a best strategy within one conversation of the bar as inconclusive."
            % (n_cell, round(100.0 / n_cell))
        )
    out.append("")

    # Split by group (tier / split).
    groups = [g for g in _ordered(records, "group") if g is not None]
    if len(groups) > 1:
        rows = []
        for model in models:
            for strategy in strategies:
                cell = _cell(records, model, strategy)
                row = [model, strategy]
                for g in groups:
                    agg = module.aggregate([r for r in cell if r["group"] == g])
                    row.append(fmt(agg.get(module.HEADLINE), "pct"))
                rows.append(row)
        out += ["### Headline by %s" % module.GROUP_FIELD, ""] + _table(["Model", "Strategy"] + groups, rows) + [""]

    # Surviving failure modes for each model's best strategy.
    out += ["### Surviving failure modes (best strategy per model)", ""]
    for model in models:
        strategy = bests[model][0]
        if strategy is None:
            continue
        out.append("**%s / %s**" % (model, strategy))
        out.append("")
        for line in module.failure_modes(_cell(records, model, strategy)):
            out.append("- " + line)
        out.append("")

    # Every failure.
    out += ["### Failures", ""]
    any_failure = False
    for model in models:
        for strategy in strategies:
            lines = []
            for r in _cell(records, model, strategy):
                desc = module.describe_failure(r)
                if desc is None:
                    continue
                rep = " [repeat %d]" % r["repeat"] if r["repeat"] else ""
                lines.append("- %s (%s)%s: %s" % (r["scenario_id"], r.get("group"), rep, desc))
            if lines:
                any_failure = True
                out.append("**%s / %s**" % (model, strategy))
                out.append("")
                out += lines
                out.append("")
    if not any_failure:
        out.append("None.")
        out.append("")
    return out


def render(records: List[Dict], meta: Dict) -> str:
    cfg = meta.get("config", {})
    out = ["# Prompt-ceiling pilot results", ""]
    out.append("- Started: %s, finished: %s%s" % (meta.get("started_at"), meta.get("finished_at"), " (interrupted)" if meta.get("interrupted") else ""))
    out.append("- Models: %s" % ", ".join(cfg.get("models", [])))
    out.append(
        "- Behaviors: %s; strategies: %s; limit: %s; repeats: %s; temperature: %s"
        % (
            ", ".join(cfg.get("behaviors", [])),
            ", ".join(cfg.get("strategies") or ["all"]),
            cfg.get("limit") or "none",
            cfg.get("repeats"),
            "unset" if cfg.get("temperature") is None else cfg.get("temperature"),
        )
    )
    out.append("- Conversations: %s of %s completed, %s errors" % (meta.get("completed"), meta.get("jobs"), meta.get("errors")))
    out.append("- Code: %s" % (meta.get("git_sha") or "no git sha"))
    judge = meta.get("judge")
    if judge:
        out.append(
            "- Judge: %s, rubric %s, %s of %s items judged, %s records with a judge field (judged %s)"
            % (judge.get("model"), ", ".join(judge.get("rubrics", [])), judge.get("judged_items"), judge.get("items"), judge.get("records_judged"), judge.get("judged_at"))
        )
    if meta.get("rescored_at"):
        out.append("- Rescored: %s with code %s" % (meta["rescored_at"], meta.get("rescored_git_sha")))
    out.append("")
    out.append(
        "Decision rule: a behavior has a real prompting ceiling when its BEST strategy, on EVERY model, stays clearly below %d%% on the headline metric."
        % round(100 * CEILING_BAR)
    )
    out.append("")
    for name in BEHAVIORS:
        subset = [r for r in records if r["behavior"] == name]
        if subset:
            out += render_behavior(name, subset)
    return "\n".join(out).rstrip() + "\n"


def headline_summary(records: List[Dict]) -> str:
    """Short plain-text summary for the terminal."""
    lines = []
    for name in BEHAVIORS:
        subset = [r for r in records if r["behavior"] == name]
        if not subset:
            continue
        module = BEHAVIORS[name]
        lines.append("%s (%s)" % (name, module.HEADLINE_LABEL))
        for model in _ordered(subset, "model"):
            parts = []
            for strategy in _ordered(subset, "strategy"):
                agg = module.aggregate(_cell(subset, model, strategy))
                parts.append("%s %s" % (strategy, fmt(agg.get(module.HEADLINE), "pct")))
            lines.append("  %-32s %s" % (model, "   ".join(parts)))
    return "\n".join(lines)
