"""Prompt templates. Kept in one place so they are easy to review and version."""

EXTRACT_SYSTEM = (
    "You are a senior QA engineer. Extract every distinct, testable behavior from the "
    "product specification. One behavior per item, written as a short plain-English "
    "statement of expected system behavior. Include error handling and edge cases. "
    'Respond with JSON only: {"behaviors": ["...", "..."]}'
)

VERIFY_SYSTEM = (
    "You are a strict test reviewer. Decide whether the candidate tests verify the given "
    "behavior. 'covered' means a test exercises the behavior AND asserts the expected "
    "outcome. 'partial' means a test touches the behavior but misses an important case or "
    "assertion. 'uncovered' means no candidate test verifies it. Judge only from the code "
    "shown; do not assume tests that are not listed. "
    'Respond with JSON only: {"status": "covered|partial|uncovered", "rationale": "one sentence"}'
)

GENERATE_SYSTEM = (
    "You are a senior SDET. Write one focused pytest test function for the uncovered "
    "behavior, using the public API shown in the module source. Use clear arrange/act/assert, "
    "test the expected outcome precisely, and use pytest.raises for error cases. "
    'Respond with JSON only: {"test_code": "<python code>"}'
)


def verify_user(behavior_id: str, behavior: str, score: float, candidates: list[tuple[str, str]]) -> str:
    blocks = "\n\n".join(f"### {tid}\n```python\n{code}\n```" for tid, code in candidates) or "(none)"
    return (
        f"BEHAVIOR_ID: {behavior_id}\nBEHAVIOR: {behavior}\nRETRIEVAL_SCORE: {score:.3f}\n\n"
        f"CANDIDATE TESTS:\n{blocks}"
    )


def generate_user(behavior_id: str, behavior: str, module_source: str) -> str:
    return (
        f"BEHAVIOR_ID: {behavior_id}\nBEHAVIOR: {behavior}\n\n"
        f"MODULE UNDER TEST:\n```python\n{module_source}\n```"
    )
