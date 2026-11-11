from fastapi import APIRouter
from backend.api.routes import query, file_ingestion

api_router = APIRouter()
api_router.include_router(query.router, prefix='/query', tags=['query'])
api_router.include_router(file_ingestion.router, prefix='/file_ingestion', tags=['file_ingestion'])