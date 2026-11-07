from fastapi import FastAPI
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