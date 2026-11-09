from pydantic import BaseModel

class FileIngestionRequest(BaseModel):
    url: str
    filename: str

class FileIngestionResponse(BaseModel):
    content: str
    success: bool

