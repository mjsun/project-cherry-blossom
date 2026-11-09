from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb

from query_answer import (
    build_graph, load_all, build_loan_index, _build_alias_table,
    DB_DIR, COLLECTION_NAME, LABELED_DIR,
)

app = FastAPI()


# loaded once at startup, reused across requests
client = chromadb.PersistentClient(path=DB_DIR)
collection = client.get_collection(COLLECTION_NAME)
chunks_by_file, all_loans = load_all(LABELED_DIR)
loan_index = build_loan_index(chunks_by_file)
aliases = _build_alias_table(all_loans)
graph = build_graph(collection, chunks_by_file, loan_index, aliases)


class QueryRequest(BaseModel):
    query: str


class FileRequest(BaseModel):
    link: str
    filename: str

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/home/")
def home():
    return "This is a bot for CMBS"


@app.post("/query/")
def query(request: QueryRequest):
    result = graph.invoke({"question": request.query})
    return {"answer": result["answer"], "route": result["route"]}


@app.post("/file/")
def ingest_file(request: FileRequest):
    parsed = urlparse(request.link)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Not a valid link")

    headers = {"User-Agent": "CMBS-QA bot (contact: mingjiesun1984@gmail.com)"}
    try:
        response = httpx.get(request.link, headers=headers, follow_redirects=True, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch link: {exc}")

    prospectus = response.text
    return {"success": True, "content": prospectus}
