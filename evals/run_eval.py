"""Benchmark the gap analyzer across models on the same labelled tasks.

Usage:
    python evals/run_eval.py --models mock
    python evals/run_eval.py --models anthropic:claude-sonnet-4-5 openai:gpt-4o-mini

Each model sees identical behaviors, tests and prompts, so results are directly
comparable. Outputs a JSON file per model plus a Markdown comparison table.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_gap_agent.llm import get_client  # noqa: E402
from test_gap_agent.models import Behavior, Coverage  # noqa: E402
from test_gap_agent.pipeline import analyze  # noqa: E402

LABELS = [c.value for c in Coverage]


def score(expected: list[str], predicted: list[str]) -> dict:
    n = len(expected)
    accuracy = sum(e == p for e, p in zip(expected, predicted)) / n if n else 0.0
    per_class = {}
    for label in LABELS:
        tp = sum(e == label and p == label for e, p in zip(expected, predicted))
        fp = sum(e != label and p == label for e, p in zip(expected, predicted))
        fn = sum(e == label and p != label for e, p in zip(expected, predicted))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}

    # Gap detection: anything not fully covered is a gap. Missing a real gap
    # (a false "covered") is the costly error, so we report it separately.
    gap_exp = [e != "covered" for e in expected]
    gap_pred = [p != "covered" for p in predicted]
    tp = sum(a and b for a, b in zip(gap_exp, gap_pred))
    fp = sum((not a) and b for a, b in zip(gap_exp, gap_pred))
    fn = sum(a and (not b) for a, b in zip(gap_exp, gap_pred))
    gap_p = tp / (tp + fp) if tp + fp else 0.0
    gap_r = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": round(accuracy, 3),
        "per_class": per_class,
        "gap_detection": {
            "precision": round(gap_p, 3),
            "recall": round(gap_r, 3),
            "missed_gaps": fn,
        },
    }


def run_one(spec: str, bench: dict) -> dict:
    provider, _, model = spec.partition(":")
    llm = get_client(provider, model or None)
    behaviors = [Behavior(id=b["id"], description=b["description"]) for b in bench["behaviors"]]
    started = time.perf_counter()
    report = analyze(llm, tests_dir=ROOT / bench["tests_dir"], behaviors=behaviors)
    wall = time.perf_counter() - started

    expected = [b["expected"] for b in bench["behaviors"]]
    predicted = [r.status.value for r in report.results]
    metrics = score(expected, predicted)
    u = report.usage
    return {
        "model": f"{report.provider}/{report.model}",
        "metrics": metrics,
        "usage": {
            "calls": u.calls,
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "llm_latency_s": round(u.latency_s, 2),
            "wall_time_s": round(wall, 2),
            "cost_usd": round(u.cost_usd, 5),
        },
        "errors": [
            {"id": b["id"], "behavior": b["description"], "expected": e, "predicted": p, "rationale": r.rationale}
            for b, e, p, r in zip(bench["behaviors"], expected, predicted, report.results)
            if e != p
        ],
    }


def markdown_table(results: list[dict]) -> str:
    lines = [
        "| Model | Accuracy | Gap precision | Gap recall | Missed gaps | LLM calls | Tokens | Latency (s) | Cost (USD) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        m, u = r["metrics"], r["usage"]
        g = m["gap_detection"]
        lines.append(
            f"| {r['model']} | {m['accuracy']:.2f} | {g['precision']:.2f} | {g['recall']:.2f} | "
            f"{g['missed_gaps']} | {u['calls']} | {u['input_tokens'] + u['output_tokens']} | "
            f"{u['llm_latency_s']} | {u['cost_usd']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default=str(ROOT / "evals" / "benchmark.json"))
    parser.add_argument("--models", nargs="+", default=["mock"], help="provider[:model] ...")
    parser.add_argument("--out", default=str(ROOT / "evals" / "results"))
    args = parser.parse_args(argv)

    bench = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for spec in args.models:
        res = run_one(spec, bench)
        results.append(res)
        safe = res["model"].replace("/", "_")
        (out / f"{safe}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    table = markdown_table(results)
    (out / "comparison.md").write_text(f"# Results on {bench['name']}\n\n{table}", encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
