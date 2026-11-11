import re

from backend.ai_module.app.loan_db import search_loans, aggregate
from backend.ai_module.constant import (
    STATE_MAP,
    PROPERTY_TYPES,
    AGG_KEYWORDS,
    GROUP_KEYWORDS,
)


class StructuredQueryHandler:
    def handle(self, question: str) -> str:
        parsed = self._parse_question(question)

        if parsed["aggregation_metric"] and parsed["group_column"]:
            return self._handle_aggregation(parsed)

        return self._handle_search(parsed)

    def _parse_question(self, question: str):
        return {
            "state": self._extract_state(question),
            "property_type": self._extract_property_type(question),
            "aggregation_metric": self._extract_aggregation(question),
            "group_column": self._extract_group(question),
            "filters": self._extract_filters(question),
        }

    def _extract_state(self, question):
        question_lower = question.lower()

        for name, abbreviation in STATE_MAP.items():
            if name in question_lower:
                return abbreviation

        match = re.search(r"\b([A-Z]{2})\b", question)

        if match and match.group(1) in STATE_MAP.values():
            return match.group(1)

        return None

    def _extract_property_type(self, question):
        question_lower = question.lower()

        for property_type in PROPERTY_TYPES:
            if property_type in question_lower:
                return property_type.title()

        return None

    def _extract_aggregation(self, question):
        question_lower = question.lower()

        for keyword, metric in AGG_KEYWORDS.items():
            if keyword in question_lower:
                return metric

        return None

    def _extract_group(self, question):
        question_lower = question.lower()

        for keyword, column in GROUP_KEYWORDS.items():
            if keyword in question_lower:
                return column

        return None

    def _extract_filters(self, question):
        question_lower = question.lower()
        filters = {}

        match = re.search(
            r"(?:above|over|greater than|more than)\s*\$?([\d,]+)",
            question_lower,
        )

        if match:
            filters["min_balance"] = float(
                match.group(1).replace(",", "")
            )

        match = re.search(
            r"(?:below|under|less than)\s*\$?([\d,]+)",
            question_lower,
        )

        if match:
            filters["max_balance"] = float(
                match.group(1).replace(",", "")
            )

        match = re.search(
            r"dscr\s*(?:above|over|greater than|>)\s*([\d.]+)",
            question_lower,
        )

        if match:
            filters["min_dscr"] = float(match.group(1))

        match = re.search(
            r"ltv\s*(?:below|under|less than|<)\s*([\d.]+)",
            question_lower,
        )

        if match:
            filters["max_ltv"] = float(match.group(1))

        return filters

    def _handle_aggregation(self, parsed):
        results = aggregate(
            group_by=parsed["group_column"],
            metric=parsed["aggregation_metric"],
        )

        if not results:
            return "No data found for that aggregation."

        lines = [
            f"  {row['group']}: {row['value']}"
            for row in results[:20]
        ]

        return (
            f"{parsed['aggregation_metric']} "
            f"by {parsed['group_column']}:\n"
            + "\n".join(lines)
        )

    def _handle_search(self, parsed):
        filters = dict(parsed["filters"])

        if parsed["state"]:
            filters["state"] = parsed["state"]

        if parsed["property_type"]:
            filters["general_property_type"] = (
                parsed["property_type"]
            )

        rows = search_loans(**filters)

        if not rows:
            return "No loans matched those filters."

        lines = []

        for row in rows:
            if row["cutoff_balance"]:
                lines.append(
                    f"  {row['deal_id']}:{row['loan_no']} | "
                    f"{row['property_name']} | "
                    f"{row['city']}, {row['state']} | "
                    f"bal=${row['cutoff_balance']:,.0f}"
                )
            else:
                lines.append(
                    f"  {row['deal_id']}:{row['loan_no']} | "
                    f"{row['property_name']}"
                )

        return (
            f"Found {len(rows)} loans:\n"
            + "\n".join(lines)
        )