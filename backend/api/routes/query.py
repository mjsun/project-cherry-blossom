from fastapi import APIRouter
from backend.schema.query_model import QueryModelRequest, QueryModelResponse
from backend.services.query import QueryService

router = APIRouter()

@router.post("/", response_model=QueryModelResponse)
def query(request: QueryModelRequest):
    qs = QueryService()
    result = qs.query(request.query)
    return result



