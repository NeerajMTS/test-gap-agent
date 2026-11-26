"""Unit tests for the agent. All run offline with the deterministic mock provider."""

from pathlib import Path

import pytest

from test_gap_agent.indexer import index_tests
from test_gap_agent.llm import MockClient, estimate_cost, get_client, parse_json
from test_gap_agent.models import Behavior, Coverage, Usage
from test_gap_agent.pipeline import analyze, extract_behaviors
from test_gap_agent.report import to_json, to_markdown
from test_gap_agent.retriever import TfidfRetriever, tokenize

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "examples" / "todo_app"


# --- llm helpers -----------------------------------------------------------

def test_parse_json_handles_code_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_handles_surrounding_prose():
    assert parse_json('Sure! Here it is: {"status": "covered"} hope that helps') == {"status": "covered"}


def test_parse_json_raises_on_garbage():
    with pytest.raises(ValueError):
        parse_json("no json here")


def test_estimate_cost_uses_pricing_table():
    assert estimate_cost("gpt-4o-mini", 1_000_000, 0) == pytest.approx(0.15)
    assert estimate_cost("unknown-model", 1000, 1000) == 0.0


def test_get_client_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_client("not-a-provider")


# --- indexing and retrieval ------------------------------------------------

def test_indexer_finds_every_test_function():
    refs = index_tests(APP / "tests")
    names = {r.name for r in refs}
    assert "test_add_task_returns_task_with_id" in names
    assert len(refs) == 9
    assert all(r.id.startswith("test_todo.py::") for r in refs)


def test_tokenize_normalizes_synonyms_and_case():
    assert "delete" in tokenize("Removed the item")
    assert "add" in tokenize("createTask")


def test_retriever_ranks_the_relevant_test_first():
    r = TfidfRetriever()
    r.index(index_tests(APP / "tests"))
    top, score = r.search("searching tasks by title text", k=1)[0]
    assert top.name == "test_search_finds_tasks"
    assert score > 0


# --- pipeline --------------------------------------------------------------

def test_extract_behaviors_from_markdown_bullets():
    usage = Usage()
    behaviors = extract_behaviors((APP / "spec.md").read_text(), MockClient(), usage)
    assert len(behaviors) == 18
    assert behaviors[0].id == "B01"
    assert usage.calls == 1


def test_unrelated_behavior_is_uncovered_without_llm_call():
    report = analyze(
        MockClient(),
        tests_dir=APP / "tests",
        behaviors=[Behavior("X1", "Export all invoices to a PDF file over SFTP")],
    )
    assert report.results[0].status is Coverage.UNCOVERED
    assert report.usage.calls == 0


def test_generate_drafts_tests_only_for_gaps():
    report = analyze(
        MockClient(),
        tests_dir=APP / "tests",
        spec_text=(APP / "spec.md").read_text(),
        module_source=(APP / "todo.py").read_text(),
        generate=True,
    )
    for r in report.results:
        if r.status is Coverage.COVERED:
            assert r.suggested_test is None
        else:
            assert r.suggested_test and "def test_" in r.suggested_test


def test_report_renders_markdown_and_json():
    report = analyze(MockClient(), tests_dir=APP / "tests", spec_text=(APP / "spec.md").read_text())
    md = to_markdown(report)
    assert "# Test Gap Report" in md and "B01" in md
    assert '"coverage_pct"' in to_json(report)
    assert 0 <= report.coverage_pct <= 100


def test_bad_status_from_model_falls_back_to_uncovered():
    class WeirdModel(MockClient):
        def complete_json(self, system, user, task):
            return {"status": "maybe?"}, Usage(calls=1)

    report = analyze(WeirdModel(), tests_dir=APP / "tests",
                     behaviors=[Behavior("B1", "Completing a task marks it as done.")])
    assert report.results[0].status is Coverage.UNCOVERED


# --- eval harness ----------------------------------------------------------

def test_eval_scoring_math():
    import sys
    sys.path.insert(0, str(ROOT / "evals"))
    from run_eval import score

    m = score(["covered", "uncovered", "partial"], ["covered", "covered", "partial"])
    assert m["accuracy"] == pytest.approx(0.667, abs=1e-3)
    assert m["gap_detection"]["missed_gaps"] == 1
    assert m["gap_detection"]["precision"] == 1.0
