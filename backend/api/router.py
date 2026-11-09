from fastapi import APIRouter
from backend.api.routes import query

api_router = APIRouter()
api_router.include_router(query.router, prefix='/query', tags=['query'])