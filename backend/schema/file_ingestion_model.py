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
