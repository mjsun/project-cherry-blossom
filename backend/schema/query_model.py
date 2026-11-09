from pydantic import BaseModel

class QueryModelRequest(BaseModel):
    query: str

class QueryModelResponse(BaseModel):
    answer: str
    # route: str
