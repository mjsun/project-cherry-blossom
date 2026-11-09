from dataclasses import dataclass
from typing import Optional

@dataclass
class QueryState:
    question: str
    route: Optional[str] = None
    answer: Optional[str] = None