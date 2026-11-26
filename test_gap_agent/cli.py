"""Command-line entry point: `tga analyze ...`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .llm import get_client
from .pipeline import analyze
from .report import to_json, to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tga", description="AI test gap analyzer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="find behaviors in a spec that the tests do not cover")
    a.add_argument("--spec", required=True, help="Markdown/text spec or user stories")
    a.add_argument("--tests", required=True, help="pytest file or directory")
    a.add_argument("--module", help="source file under test (enables test generation)")
    a.add_argument("--provider", default="mock", choices=["anthropic", "openai", "mock"])
    a.add_argument("--model", help="model name, e.g. claude-sonnet-4-5 or gpt-4o-mini")
    a.add_argument("--generate", action="store_true", help="draft pytest tests for gaps")
    a.add_argument("--format", default="md", choices=["md", "json"])
    a.add_argument("--out", help="write the report to this file")

    args = parser.parse_args(argv)
    llm = get_client(args.provider, args.model)
    module_source = Path(args.module).read_text(encoding="utf-8") if args.module else None
    report = analyze(
        llm,
        tests_dir=args.tests,
        spec_text=Path(args.spec).read_text(encoding="utf-8"),
        module_source=module_source,
        generate=args.generate,
    )
    text = to_markdown(report) if args.format == "md" else to_json(report)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
