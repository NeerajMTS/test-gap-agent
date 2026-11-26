"""Render reports as Markdown or JSON."""

from __future__ import annotations

import json

from .models import Coverage, Report

ICON = {Coverage.COVERED: "✅", Coverage.PARTIAL: "🟡", Coverage.UNCOVERED: "❌"}


def to_markdown(report: Report) -> str:
    c = report.counts
    u = report.usage
    lines = [
        "# Test Gap Report",
        "",
        f"**Model:** {report.provider}/{report.model}  ",
        f"**Behaviors:** {len(report.results)} | covered {c['covered']} | "
        f"partial {c['partial']} | uncovered {c['uncovered']}  ",
        f"**Coverage score:** {report.coverage_pct}%  ",
        f"**LLM usage:** {u.calls} calls, {u.input_tokens + u.output_tokens} tokens, "
        f"{u.latency_s:.1f}s, ${u.cost_usd:.4f}",
        "",
        "| ID | Behavior | Status | Score | Matched tests | Rationale |",
        "|---|---|---|---|---|---|",
    ]
    for r in report.results:
        matched = "<br>".join(r.matched_tests) or "-"
        lines.append(
            f"| {r.behavior.id} | {r.behavior.description} | {ICON[r.status]} {r.status.value} | "
            f"{r.retrieval_score:.2f} | {matched} | {r.rationale} |"
        )
    suggestions = [r for r in report.results if r.suggested_test]
    if suggestions:
        lines += ["", "## Suggested tests for gaps", ""]
        for r in suggestions:
            lines += [f"### {r.behavior.id}: {r.behavior.description}", "```python", r.suggested_test.rstrip(), "```", ""]
    return "\n".join(lines) + "\n"


def to_json(report: Report) -> str:
    return json.dumps(
        {
            "provider": report.provider,
            "model": report.model,
            "counts": report.counts,
            "coverage_pct": report.coverage_pct,
            "usage": vars(report.usage),
            "results": [r.to_dict() for r in report.results],
        },
        indent=2,
        ensure_ascii=False,
    )
