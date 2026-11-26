"""Lightweight TF-IDF retriever (no external dependencies).

Kept dependency-free on purpose so the project runs anywhere. The interface
(`index` + `search`) is small, so a vector database such as ChromaDB with real
embeddings can be dropped in behind it.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .models import TestRef

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "is", "it", "be", "for", "on", "with",
    "that", "when", "should", "must", "can", "by", "as", "if", "are", "user", "test",
    "assert", "def", "self", "none", "true", "false", "return", "import", "from",
}

SYNONYMS = {
    "remove": "delete", "removed": "delete", "deleted": "delete", "deleting": "delete",
    "create": "add", "created": "add", "adding": "add", "added": "add",
    "done": "complete", "completed": "complete", "completing": "complete", "finish": "complete",
    "find": "search", "searching": "search", "lookup": "search",
    "overdue": "overdue", "late": "overdue", "past": "overdue",
    "error": "raise", "raises": "raise", "invalid": "raise", "reject": "raise", "rejected": "raise",
    "sorted": "sort", "sorting": "sort", "order": "sort", "ordered": "sort",
    "tasks": "task", "titles": "title", "items": "task",
}


def tokenize(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[a-zA-Z]+", text.lower())
    out = []
    for w in words:
        w = SYNONYMS.get(w, w)
        if len(w) > 2 and w not in STOPWORDS:
            out.append(w)
    return out


class TfidfRetriever:
    def __init__(self) -> None:
        self.docs: list[TestRef] = []
        self.vectors: list[dict[str, float]] = []
        self.idf: dict[str, float] = {}

    def index(self, docs: list[TestRef]) -> None:
        self.docs = docs
        tokenized = [tokenize(d.text) for d in docs]
        n = len(docs)
        df: Counter[str] = Counter()
        for toks in tokenized:
            df.update(set(toks))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vectors = [self._vector(toks) for toks in tokenized]

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        vec = {t: c * self.idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, k: int = 3) -> list[tuple[TestRef, float]]:
        q = self._vector(tokenize(query))
        scored = [
            (doc, sum(w * vec.get(t, 0.0) for t, w in q.items()))
            for doc, vec in zip(self.docs, self.vectors)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [(d, round(s, 3)) for d, s in scored[:k]]
