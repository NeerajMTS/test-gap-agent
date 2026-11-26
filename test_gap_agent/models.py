"""Core data models shared across the pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Coverage(str, Enum):
    COVERED = "covered"
    PARTIAL = "partial"
    UNCOVERED = "uncovered"


@dataclass(frozen=True)
class Behavior:
    """A single expected behavior of the system, written in plain language."""

    id: str
    description: str
    source: str = ""


@dataclass(frozen=True)
class TestRef:
    """An existing automated test, indexed from source code."""

    id: str
    name: str
    file: str
    text: str


@dataclass
class Usage:
    """Token, latency and cost accounting for LLM calls."""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.latency_s += other.latency_s
        self.cost_usd += other.cost_usd


@dataclass
class GapResult:
    behavior: Behavior
    status: Coverage
    retrieval_score: float
    matched_tests: list[str] = field(default_factory=list)
    rationale: str = ""
    suggested_test: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class Report:
    provider: str
    model: str
    results: list[GapResult]
    usage: Usage

    @property
    def counts(self) -> dict[str, int]:
        out = {c.value: 0 for c in Coverage}
        for r in self.results:
            out[r.status.value] += 1
        return out

    @property
    def coverage_pct(self) -> float:
        """Covered = 1, partial = 0.5, uncovered = 0."""
        if not self.results:
            return 0.0
        weights = {Coverage.COVERED: 1.0, Coverage.PARTIAL: 0.5, Coverage.UNCOVERED: 0.0}
        return round(100 * sum(weights[r.status] for r in self.results) / len(self.results), 1)
