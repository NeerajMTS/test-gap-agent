"""Test Gap Analyzer Agent: find untested behaviors with LLMs and retrieval."""

from .models import Behavior, Coverage, GapResult, Report, TestRef, Usage
from .pipeline import analyze

__all__ = ["Behavior", "Coverage", "GapResult", "Report", "TestRef", "Usage", "analyze"]
__version__ = "0.1.0"
