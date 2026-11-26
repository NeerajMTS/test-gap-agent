"""Index existing pytest tests so they can be matched against behaviors."""

from __future__ import annotations

import ast
from pathlib import Path

from .models import TestRef


def _humanize(name: str) -> str:
    return name.removeprefix("test_").replace("_", " ")


def index_file(path: Path, root: Path | None = None) -> list[TestRef]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    rel = str(path.relative_to(root)) if root else str(path)
    refs: list[TestRef] = []

    def visit(nodes, prefix: str = "") -> None:
        for node in nodes:
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                visit(node.body, prefix=f"{node.name}::")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                body = ast.get_source_segment(source, node) or ""
                doc = ast.get_docstring(node) or ""
                text = f"{_humanize(node.name)}\n{doc}\n{body}"
                refs.append(TestRef(id=f"{rel}::{prefix}{node.name}", name=node.name, file=rel, text=text))

    visit(tree.body)
    return refs


def index_tests(tests_dir: str | Path) -> list[TestRef]:
    root = Path(tests_dir)
    files = [root] if root.is_file() else sorted(root.rglob("test_*.py"))
    base = root.parent if root.is_file() else root
    refs: list[TestRef] = []
    for f in files:
        refs.extend(index_file(f, base))
    return refs
