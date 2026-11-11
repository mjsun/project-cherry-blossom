import re

from backend.ai_module.constant import STRUCTURED_PATTERNS


def _keys_from_names(text, aliases):
    """Loan keys from property names mentioned without their number."""
    return [key for name, key in aliases
            if re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE)]


class QueryClassifier:
    def __init__(self, aliases):
        self.aliases = aliases

    def classify(self, question: str) -> str:
        named_keys = _keys_from_names(
            question,
            self.aliases,
        )

        if named_keys:
            return "named"

        question_lower = question.lower()

        for pattern in STRUCTURED_PATTERNS:
            if re.search(pattern, question_lower):
                return "structured"

        return "narrative"

    def find_named_keys(self, question: str):
        return _keys_from_names(
            question,
            self.aliases,
        )