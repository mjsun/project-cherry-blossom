from pydantic import BaseModel
from typing import Optional

class FileIngestionRequest(BaseModel):
    url: str
    filename: str

class FileIngestionStartResponse(BaseModel):
    job_id: str

class FileIngestionStatusResponse(BaseModel):
    status: str
    completed_steps: list[int]
    error: Optional[str] = None
    total_batches: int = 0
    completed_batches: int = 0
    total_chunks: int = 0
    completed_chunks: int = 0
