from fastapi import APIRouter
from backend.schema.file_ingestion_model import FileIngestionRequest, FileIngestionResponse
from backend.services.file_ingestion import FileIngestionService
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException

router = APIRouter()

@router.post("/", response_model=FileIngestionResponse)
def query(request: FileIngestionRequest):
    fi = FileIngestionService()
    parsed = urlparse(request.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Not a valid link")
    try:
        response = fi.loadFileByUrl(request.url)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch link: {exc}")
    
    return {"success": True, "content": response}


