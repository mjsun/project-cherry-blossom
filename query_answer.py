"""
Given a question, retrieve the top-N relevant chunks from Chroma and ask
the grounding LLM (Qwen 2.5 7B via Ollama) to answer using only that
context.

Two retrieval paths, picked per question:
  - named-loan path: if the question mentions a known property name (e.g.
    "What is the Block at Orange loan?"), skip semantic search entirely --
    pull every chunk tagged with that loan directly. Exact, and avoids the
    problem where a generic-sounding question gets outcompeted by the huge
    number of near-identical loan-table rows in semantic search.
  - semantic path: no named loan recognized -- fall back to embedding
    similarity search as before.

Loads the already-built Chroma collection -- run embed_and_store.py once
first to populate it, this script doesn't re-embed anything. Rebuilds
chunks_by_file (and the loan metadata needed for name-matching) by
reprocessing the labeled .tsv files directly -- fast, no embedding calls.
"""

import os
import glob
import chromadb
import ollama

from chunk_filing import (
    process_file,
    get_local_context,
    _build_alias_table,
    _keys_from_names,
)

EMBED_MODEL = "nomic-embed-text"
ANSWER_MODEL = "qwen2.5:7b"
DB_DIR = "./chroma_db"
COLLECTION_NAME = "cmbs_filings"
LABELED_DIR = "./labeled_data"
TOP_K = 10


def embed(text: str):
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


def load_all(folder: str):
    """
    Rebuild {deal_id: [chunks]} AND a loans dict merged across every deal
    (needed to recognize a property name mentioned in a question).
    """
    chunks_by_file = {}
    all_loans = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.tsv"))):
        deal_id, rows, loans, chunks = process_file(path)
        chunks_by_file[deal_id] = chunks
        all_loans.update(loans)
    return chunks_by_file, all_loans


def build_loan_index(chunks_by_file):
    """loan_key -> [(deal_id, index), ...] -- exact lookup, no embedding needed."""
    index = {}
    for deal_id, chunks in chunks_by_file.items():
        for chunk in chunks:
            for key in chunk.loan_keys:
                index.setdefault(key, []).append((chunk.deal_id, chunk.index))
    return index


# --- retrieval -----------------------------------------------------------

def retrieve(collection, query: str, top_k: int = TOP_K):
    """Semantic path: top-k chunks by embedding similarity to the query."""
    q_emb = embed(query)
    result = collection.query(query_embeddings=[q_emb], n_results=top_k)
    return list(zip(result["documents"][0], result["metadatas"][0]))


def positions_from_hits(hits):
    """(deal_id, index) pairs from semantic-search hits, deduped."""
    seen = set()
    positions = []
    for _, meta in hits:
        key = (meta["deal_id"], meta["index"])
        if key not in seen:
            seen.add(key)
            positions.append(key)
    return positions


def resolve_keys_to_positions(loan_index, loan_keys):
    """Named-loan path: (deal_id, index) pairs for every chunk tagged with these keys."""
    positions = []
    for key in loan_keys:
        positions.extend(loan_index.get(key, []))
    seen = set()
    return [p for p in positions if not (p in seen or seen.add(p))]


def build_context(chunks_by_file, positions, before: int = 1, after: int = 1):
    """Local window (chunk + neighbors) for each position, concatenated."""
    blocks = []
    for deal_id, index in positions:
        chunks = chunks_by_file.get(deal_id, [])
        if index >= len(chunks):
            continue
        chunk = chunks[index]
        window = get_local_context(chunks, index, before=before, after=after)
        blocks.append(f"[{deal_id} lines {chunk.start_line}-{chunk.end_line}]\n{window}")
    return "\n\n---\n\n".join(blocks)


def answer_question(collection, chunks_by_file, loan_index, aliases,
                     question: str, top_k: int = TOP_K):
    named_keys = _keys_from_names(question, aliases)

    if named_keys:
        print(f"  [named-loan match: {named_keys}]")
        positions = resolve_keys_to_positions(loan_index, named_keys)
    else:
        hits = retrieve(collection, question, top_k=top_k)
        positions = positions_from_hits(hits)

    context = build_context(chunks_by_file, positions)

    prompt = (
        "Answer the question using ONLY the context below. "
        "If the context doesn't contain the answer, say so -- don't guess.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )

    response = ollama.chat(model=ANSWER_MODEL, messages=[
        {"role": "user", "content": prompt},
    ])
    return response["message"]["content"]


if __name__ == "__main__":
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    chunks_by_file, all_loans = load_all(LABELED_DIR)
    loan_index = build_loan_index(chunks_by_file)
    aliases = _build_alias_table(all_loans)

    question = "What is the Block at Orange loan?"
    print(f"Q: {question}\n")
    print(answer_question(collection, chunks_by_file, loan_index, aliases, question))