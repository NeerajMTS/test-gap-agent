# Test Gap Analyzer Agent

An LLM agent that reads a product spec, compares it against an existing pytest suite, and tells you **which behaviors are not really tested**, then drafts the missing tests.

It ships with a hand-labelled benchmark and an eval harness, so you can **swap models (Claude, GPT, any OpenAI-compatible endpoint) and compare accuracy, tokens, latency and cost on identical tasks.**

```
spec.md ──► [1. Extract behaviors] ──► behaviors
                    (LLM)                  │
tests/  ──► [2. Index tests] ──► [3. Retrieve top-k candidate tests] (TF-IDF)
                (AST)                      │
                                [4. Verify coverage] (LLM judge)
                                           │
                     covered / partial / uncovered + rationale
                                           │
                                [5. Draft tests for gaps] (LLM, optional)
```

## Why the LLM judge matters

Retrieval alone is not enough. A test called `test_add_task_with_empty_title_raises` looks very similar to the behavior *"a title longer than 100 characters raises an error"*, but it does not test it.

The eval includes a **retrieval-only baseline** (the offline `mock` provider) to make this measurable. On the bundled benchmark it reports **8 of the 10 real gaps as covered**:

| Model | Accuracy | Gap precision | Gap recall | Missed gaps | LLM calls | Tokens | Cost (USD) |
|---|---|---|---|---|---|---|---|
| retrieval-only baseline (mock) | 0.44 | 1.00 | 0.20 | 8 | 18 | 4,877 | 0.0000 |
| claude-sonnet-4-5 | *run it* | | | | | | |
| gpt-4o-mini | *run it* | | | | | | |

Run the eval with your own API keys (below) to fill in the model rows.

## Quick start

```bash
pip install -e ".[dev]"          # core has no dependencies
pytest -q                          # 23 tests, fully offline

# Offline dry run (no API key needed)
tga analyze --spec examples/todo_app/spec.md --tests examples/todo_app/tests

# Real model
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=...
tga analyze --provider anthropic --model claude-sonnet-4-5 \
    --spec examples/todo_app/spec.md --tests examples/todo_app/tests \
    --module examples/todo_app/todo.py --generate --out report.md
```

## Benchmarking models

```bash
pip install -e ".[anthropic,openai]"
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
python evals/run_eval.py --models mock anthropic:claude-sonnet-4-5 openai:gpt-4o-mini
```

Every model gets the same behaviors, candidate tests and prompts. Output:

- `evals/results/comparison.md`: side-by-side table
- `evals/results/<model>.json`: metrics, token usage, latency, cost, and every misclassified behavior with the model's rationale

Any OpenAI-compatible endpoint works through `OPENAI_BASE_URL`, so open-weight or self-hosted models can be compared the same way.

**Metrics**
- **Accuracy:** exact match on covered / partial / uncovered
- **Gap precision / recall:** treating partial + uncovered as "gap". *Missed gaps* (a real gap reported as covered) is the costly error and is reported separately.
- **Tokens, latency, cost:** per run, from provider usage data and the `PRICING` table in `test_gap_agent/llm.py`

## Project layout

```
test_gap_agent/
  llm.py         provider layer: Anthropic, OpenAI-compatible, offline mock; token + cost tracking
  prompts.py     all prompts in one place
  indexer.py     AST-based pytest indexer (functions, classes, docstrings)
  retriever.py   dependency-free TF-IDF retriever (swappable for a vector DB)
  pipeline.py    extract -> retrieve -> verify -> generate
  report.py      Markdown / JSON reports
  cli.py         `tga analyze`
evals/
  benchmark.json 18 hand-labelled behaviors for the sample app
  run_eval.py    multi-model benchmark runner
examples/todo_app/  sample system under test, its (incomplete) tests and spec
tests/           unit tests for the agent
```

## Design notes

- **Cost control:** behaviors with no plausible candidate test are marked uncovered without an LLM call.
- **Strict judging:** the verifier must see an assertion on the expected outcome to say "covered"; touching the code path only counts as "partial".
- **Robust parsing:** model output is parsed tolerantly (code fences, surrounding prose), and invalid statuses fall back to "uncovered" rather than over-reporting coverage.
- **Reproducible:** the core has zero dependencies and the whole suite and baseline eval run offline in CI.

## Roadmap

- Embedding retrieval (ChromaDB) alongside TF-IDF
- Playwright test indexing for UI suites
- Agentic loop: run generated tests and keep only those that fail on a mutated build

## License

MIT
