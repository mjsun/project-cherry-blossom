"""
Embed all chunks and load them into a local Chroma vector DB.

Run chunk_filing.py's pipeline first (import it), then:
  1. embed each chunk's embedding_text() via Ollama (nomic-embed-text)
  2. store it in Chroma, metadata = deal_id/index/label/start_line/end_line
  3. build a plain loan_index: loan_key -> [chunk ids] for EXACT lookup

Long chunks are split before embedding (RecursiveCharacterTextSplitter)
instead of truncated, so nothing becomes unsearchable -- grounding still
uses the full original chunk via get_local_context(), independent of how
many pieces it got split into here.

Why loan_index is a plain dict, not a Chroma `where` filter: Chroma
metadata values must be a single string/int/float/bool -- not a list --
so a chunk tagged with several loan_keys can't be stored as a filterable
list field. The exact-match half of the hybrid design lives in this dict
instead; Chroma only does the similarity-search half.
"""

import os
import glob
import chromadb
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter

from chunk_filing import process_file, get_local_context

EMBED_MODEL = "nomic-embed-text"
DB_DIR = "./chroma_db"
COLLECTION_NAME = "cmbs_filings"

MAX_EMBED_CHARS = 3000

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_EMBED_CHARS,
    chunk_overlap=200,   # keeps a little context across split boundaries
)


def _split_for_embedding(text: str):
    if len(text) <= MAX_EMBED_CHARS:
        return [text]
    return _splitter.split_text(text)


def embed(text: str):
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


def load_folder(folder: str):
    """
    Process every .tsv, embed every chunk, load into Chroma.
    Returns (collection, chunks_by_file, loan_index) for later retrieval.
    """
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    chunks_by_file = {}   # deal_id -> ordered chunk list (for local context)
    loan_index = {}        # loan_key -> [chunk_id, ...]      (exact match)

    for path in sorted(glob.glob(os.path.join(folder, "*.tsv"))):
        deal_id, rows, loans, chunks = process_file(path)
        chunks_by_file[deal_id] = chunks

        ids, docs, metas, embeddings = [], [], [], []
        for chunk in chunks:
            text = chunk.embedding_text()
            pieces = _split_for_embedding(text)

            for piece_i, piece in enumerate(pieces):
                chunk_id = f"{chunk.deal_id}:{chunk.index}:{piece_i}"
                ids.append(chunk_id)
                docs.append(piece)
                metas.append({
                    "deal_id": chunk.deal_id,
                    "index": chunk.index,
                    "label": chunk.label,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "loan_keys_csv": ",".join(chunk.loan_keys),  # display only
                })
                embeddings.append(embed(piece))

                for key in chunk.loan_keys:
                    loan_index.setdefault(key, []).append(chunk_id)

        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas,
                               embeddings=embeddings)
        print(f"{deal_id}: embedded {len(ids)} pieces ({len(chunks)} chunks)")

    return collection, chunks_by_file, loan_index


# --- retrieval ---------------------------------------------------------

def semantic_search(collection, query: str, n_results: int = 5):
    """Plain similarity search -- no loan filter."""
    q_emb = embed(query)
    return collection.query(query_embeddings=[q_emb], n_results=n_results)


def lookup_by_loan(collection, loan_index, loan_key: str):
    """Exact match -- every chunk tagged with this loan, no embedding call."""
    ids = loan_index.get(loan_key, [])
    if not ids:
        return None
    return collection.get(ids=ids)


def ground(chunks_by_file, deal_id: str, index: int, before: int = 1, after: int = 1):
    """The text to actually hand the LLM: chunk + its neighbors."""
    chunks = chunks_by_file.get(deal_id, [])
    return get_local_context(chunks, index, before=before, after=after)


if __name__ == "__main__":
    collection, chunks_by_file, loan_index = load_folder("./labeled_data")

    print()
    print("semantic search: 'servicing of non-serviced loans'")
    result = semantic_search(collection, "servicing of non-serviced loans", n_results=3)
    for doc, meta in zip(result["documents"][0], result["metadatas"][0]):
        print(f"  [{meta['deal_id']}:{meta['index']}] {doc[:70]}...")

    print()
    print("exact lookup: file1:1")
    hit = lookup_by_loan(collection, loan_index, "file1:1")
    if hit:
        print(f"  {len(hit['ids'])} chunks tagged file1:1")
        meta = hit["metadatas"][0]
        print("  grounding window for first hit:")
        print(ground(chunks_by_file, meta["deal_id"], meta["index"])[:300])