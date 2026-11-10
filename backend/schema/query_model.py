from pydantic import BaseModel
from typing import Optional

class QueryModelRequest(BaseModel):
    query: str

class QuerySource(BaseModel):
    deal_id: str
    chunk_index: int
    text: str
    highlight: Optional[str] = None

class QueryModelResponse(BaseModel):
    answer: str
    route: str
    sources: list[QuerySource]
