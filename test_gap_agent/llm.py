"""LLM provider layer.

Every provider exposes the same `complete_json` call, so the pipeline and the
eval harness can swap models without changing any other code. A deterministic
offline `mock` provider makes the test suite and CI run without API keys.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Protocol

from .models import Usage

# USD per 1M tokens (input, output). Edit to match current provider pricing.
PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "mock": (0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICING.get(model, (0.0, 0.0))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def parse_json(text: str) -> dict:
    """Parse a JSON object from model output, tolerating code fences and prose."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


class LLMClient(Protocol):
    provider: str
    model: str

    def complete_json(self, system: str, user: str, task: str) -> tuple[dict, Usage]:
        """Return a parsed JSON object and the usage for this call.

        `task` names the pipeline step (extract / verify / generate). Real
        providers ignore it; the mock provider uses it to pick a behavior.
        """
        ...


@dataclass
class AnthropicClient:
    model: str = "claude-sonnet-4-5"
    max_tokens: int = 1500
    provider: str = "anthropic"

    def complete_json(self, system: str, user: str, task: str) -> tuple[dict, Usage]:
        import anthropic  # optional dependency

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        start = time.perf_counter()
        resp = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        latency = time.perf_counter() - start
        text = "".join(block.text for block in resp.content if block.type == "text")
        usage = Usage(
            calls=1,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_s=latency,
            cost_usd=estimate_cost(self.model, resp.usage.input_tokens, resp.usage.output_tokens),
        )
        return parse_json(text), usage


@dataclass
class OpenAIClient:
    model: str = "gpt-4o-mini"
    max_tokens: int = 1500
    base_url: str | None = None  # any OpenAI-compatible endpoint works
    provider: str = "openai"

    def complete_json(self, system: str, user: str, task: str) -> tuple[dict, Usage]:
        from openai import OpenAI  # optional dependency

        client = OpenAI(base_url=self.base_url or os.environ.get("OPENAI_BASE_URL"))
        start = time.perf_counter()
        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        latency = time.perf_counter() - start
        text = resp.choices[0].message.content or "{}"
        usage = Usage(
            calls=1,
            input_tokens=resp.usage.prompt_tokens,
            output_tokens=resp.usage.completion_tokens,
            latency_s=latency,
            cost_usd=estimate_cost(self.model, resp.usage.prompt_tokens, resp.usage.completion_tokens),
        )
        return parse_json(text), usage


@dataclass
class MockClient:
    """Deterministic offline provider used for tests, CI and dry runs.

    It reads the structured hints the pipeline puts in each prompt, so the
    whole pipeline can be exercised end to end with no network access.
    """

    model: str = "mock"
    provider: str = "mock"

    def complete_json(self, system: str, user: str, task: str) -> tuple[dict, Usage]:
        usage = Usage(calls=1, input_tokens=len(user) // 4, output_tokens=50)
        if task == "extract":
            lines = [
                re.sub(r"^[-*\d.)\s]+", "", line).strip()
                for line in user.splitlines()
                if re.match(r"^\s*([-*]|\d+[.)])\s+", line)
            ]
            return {"behaviors": [ln for ln in lines if ln]}, usage
        if task == "verify":
            score = float(re.search(r"RETRIEVAL_SCORE:\s*([\d.]+)", user).group(1))
            if score >= 0.45:
                status = "covered"
            elif score >= 0.25:
                status = "partial"
            else:
                status = "uncovered"
            return {"status": status, "rationale": f"mock decision from retrieval score {score:.2f}"}, usage
        if task == "generate":
            name = re.search(r"BEHAVIOR_ID:\s*(\S+)", user).group(1).lower().replace("-", "_")
            code = f"def test_{name}():\n    # TODO: arrange, act, assert\n    assert True\n"
            return {"test_code": code}, usage
        raise ValueError(f"unknown task {task!r}")


def get_client(provider: str, model: str | None = None) -> LLMClient:
    provider = provider.lower()
    if provider == "anthropic":
        return AnthropicClient(model=model or "claude-sonnet-4-5")
    if provider == "openai":
        return OpenAIClient(model=model or "gpt-4o-mini")
    if provider == "mock":
        return MockClient()
    raise ValueError(f"unknown provider {provider!r}; use anthropic, openai or mock")
