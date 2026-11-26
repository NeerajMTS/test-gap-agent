"""The agent pipeline: extract -> retrieve -> verify -> (generate)."""

from __future__ import annotations

from pathlib import Path

from . import prompts
from .indexer import index_tests
from .llm import LLMClient
from .models import Behavior, Coverage, GapResult, Report, TestRef, Usage
from .retriever import TfidfRetriever

# Below this retrieval score no candidate is plausible, so we skip the LLM call.
MIN_SCORE_FOR_VERIFY = 0.08


def extract_behaviors(spec_text: str, llm: LLMClient, usage: Usage) -> list[Behavior]:
    data, u = llm.complete_json(prompts.EXTRACT_SYSTEM, spec_text, task="extract")
    usage.add(u)
    return [
        Behavior(id=f"B{i:02d}", description=desc.strip(), source="spec")
        for i, desc in enumerate(data.get("behaviors", []), start=1)
        if desc and desc.strip()
    ]


def classify(
    behavior: Behavior,
    retriever: TfidfRetriever,
    llm: LLMClient,
    usage: Usage,
    k: int = 3,
) -> GapResult:
    hits = retriever.search(behavior.description, k=k)
    top_score = hits[0][1] if hits else 0.0

    if top_score < MIN_SCORE_FOR_VERIFY:
        return GapResult(
            behavior=behavior,
            status=Coverage.UNCOVERED,
            retrieval_score=top_score,
            rationale="No test is semantically close to this behavior (skipped LLM call).",
        )

    candidates: list[tuple[TestRef, float]] = [h for h in hits if h[1] > 0]
    user = prompts.verify_user(
        behavior.id, behavior.description, top_score, [(t.id, t.text) for t, _ in candidates]
    )
    data, u = llm.complete_json(prompts.VERIFY_SYSTEM, user, task="verify")
    usage.add(u)
    try:
        status = Coverage(str(data.get("status", "uncovered")).lower())
    except ValueError:
        status = Coverage.UNCOVERED
    matched = [t.id for t, _ in candidates] if status != Coverage.UNCOVERED else []
    return GapResult(
        behavior=behavior,
        status=status,
        retrieval_score=top_score,
        matched_tests=matched,
        rationale=str(data.get("rationale", "")),
    )


def suggest_test(result: GapResult, module_source: str, llm: LLMClient, usage: Usage) -> str:
    user = prompts.generate_user(result.behavior.id, result.behavior.description, module_source)
    data, u = llm.complete_json(prompts.GENERATE_SYSTEM, user, task="generate")
    usage.add(u)
    return str(data.get("test_code", ""))


def analyze(
    llm: LLMClient,
    tests_dir: str | Path,
    spec_text: str | None = None,
    behaviors: list[Behavior] | None = None,
    module_source: str | None = None,
    generate: bool = False,
) -> Report:
    """Run the full agent. Pass `behaviors` to skip extraction (used by evals)."""
    usage = Usage()
    if behaviors is None:
        if spec_text is None:
            raise ValueError("provide spec_text or behaviors")
        behaviors = extract_behaviors(spec_text, llm, usage)

    retriever = TfidfRetriever()
    retriever.index(index_tests(tests_dir))

    results = [classify(b, retriever, llm, usage) for b in behaviors]

    if generate and module_source:
        for r in results:
            if r.status != Coverage.COVERED:
                r.suggested_test = suggest_test(r, module_source, llm, usage)

    return Report(provider=llm.provider, model=llm.model, results=results, usage=usage)
