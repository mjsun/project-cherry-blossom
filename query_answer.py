"""
query_answer.py

Three-way query router:
  1. Named-loan   → exact lookup via loan_index
  2. Structured   → SQL via loan_db (filter/aggregate)
  3. Narrative     → semantic search RAG

"""

import os
import re
import glob
import json
import chromadb
import ollama
from typing import TypedDict
from langgraph.graph import StateGraph, END
from chunk_filing import (
    process_file,
    get_local_context,
    _build_alias_table,
    _keys_from_names,
)
from loan_db import search_loans, aggregate

EMBED_MODEL = "nomic-embed-text"
ANSWER_MODEL = "qwen2.5:14b"
DB_DIR = "./chroma_db"
COLLECTION_NAME = "cmbs_filings"
LABELED_DIR = "./labeled_data"
TOP_K = 25

class State(TypedDict):
    question: str
    route: str
    answer: str

def embed(text: str):
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


def load_all(folder: str):
    chunks_by_file = {}
    all_loans = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.tsv"))):
        deal_id, rows, loans, chunks = process_file(path)
        chunks_by_file[deal_id] = chunks
        all_loans.update(loans)
    return chunks_by_file, all_loans


def build_loan_index(chunks_by_file):
    index = {}
    for deal_id, chunks in chunks_by_file.items():
        for chunk in chunks:
            for key in chunk.loan_keys:
                index.setdefault(key, []).append((chunk.deal_id, chunk.index))
    return index


# ── classification ────────────────────────────────────────────────

# patterns that signal a structured/aggregate question
STRUCTURED_PATTERNS = [
    r"\bhow many\b",
    r"\bcount\b",
    r"\btotal\b",
    r"\baverage\b",
    r"\bmean\b",
    r"\bsum\b",
    r"\blargest\b",
    r"\bsmallest\b",
    r"\bhighest\b",
    r"\blowest\b",
    r"\bmax\b",
    r"\bmin\b",
    r"\bgreater than\b",
    r"\bless than\b",
    r"\babove\b",
    r"\bbelow\b",
    r"\brange\b",
    r"\bbetween\b",
    r"\bgroup by\b",
    r"\bby state\b",
    r"\bby city\b",
    r"\bby property type\b",
    r"\bin california\b",
    r"\bin new york\b",
    r"\bin texas\b",
    r"\bin florida\b",
    r"\boffice loans\b",
    r"\bretail loans\b",
    r"\bmultifamily\b",
    r"\bhospitality\b",
    r"\bdscr\b",
    r"\bltv\b",
    r"\bbalance\b",
    r"\brate\b",
    r"\boccupancy\b",
]

# state name → abbreviation for filter extraction
STATE_MAP = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}

PROPERTY_TYPES = [
    "office", "retail", "multifamily", "hospitality", "industrial",
    "mixed use", "self storage", "manufactured housing", "mobile home",
]

AGG_KEYWORDS = {
    "average dscr": "avg_dscr",
    "average ltv": "avg_ltv",
    "average rate": "avg_rate",
    "average balance": "avg_balance",
    "average": "avg_balance",
    "mean": "avg_balance",
    "how many": "count",
    "count": "count",
    "total": "sum_balance",
    "sum": "sum_balance",
}

GROUP_KEYWORDS = {
    "by state": "state", "by city": "city",
    "by property type": "general_property_type", "by seller": "seller",
    "by deal": "deal_id",
}


def classify_query(question: str, aliases: dict) -> str:
    """Return 'named', 'structured', or 'narrative'."""
    named_keys = _keys_from_names(question, aliases)
    if named_keys:
        return "named"

    q_low = question.lower()
    for pattern in STRUCTURED_PATTERNS:
        if re.search(pattern, q_low):
            return "structured"

    return "narrative"


# ── structured query handler ──────────────────────────────────────

def _extract_state(question: str):
    q_low = question.lower()
    for name, abbr in STATE_MAP.items():
        if name in q_low:
            return abbr
    # check 2-letter codes
    match = re.search(r"\b([A-Z]{2})\b", question)
    if match and match.group(1) in STATE_MAP.values():
        return match.group(1)
    return None


def _extract_property_type(question: str):
    q_low = question.lower()
    for pt in PROPERTY_TYPES:
        if pt in q_low:
            return pt.title()
    return None


def _extract_agg(question: str):
    q_low = question.lower()
    for kw, metric in AGG_KEYWORDS.items():
        if kw in q_low:
            return metric
    return None


def _extract_group(question: str):
    q_low = question.lower()
    for kw, col in GROUP_KEYWORDS.items():
        if kw in q_low:
            return col
    return None


def handle_structured_query(question: str) -> str:
    """Parse the question into a search or aggregate call, return formatted text."""
    state = _extract_state(question)
    prop_type = _extract_property_type(question)
    agg_metric = _extract_agg(question)
    group_col = _extract_group(question)

    # aggregate path
    if agg_metric and group_col:
        results = aggregate(group_by=group_col, metric=agg_metric)
        if not results:
            return "No data found for that aggregation."
        lines = [f"  {r['group']}: {r['value']}" for r in results[:20]]
        return f"{agg_metric} by {group_col}:\n" + "\n".join(lines)

    # search path
    kwargs = {}
    if state:
        kwargs["state"] = state
    if prop_type:
        kwargs["general_property_type"] = prop_type

    # extract numeric filters from question
    q_low = question.lower()
    bal_match = re.search(r"(?:above|over|greater than|more than)\s*\$?([\d,]+)", q_low)
    if bal_match:
        kwargs["min_balance"] = float(bal_match.group(1).replace(",", ""))
    bal_match2 = re.search(r"(?:below|under|less than)\s*\$?([\d,]+)", q_low)
    if bal_match2:
        kwargs["max_balance"] = float(bal_match2.group(1).replace(",", ""))

    dscr_match = re.search(r"dscr\s*(?:above|over|greater than|>)\s*([\d.]+)", q_low)
    if dscr_match:
        kwargs["min_dscr"] = float(dscr_match.group(1))
    ltv_match = re.search(r"ltv\s*(?:below|under|less than|<)\s*([\d.]+)", q_low)
    if ltv_match:
        kwargs["max_ltv"] = float(ltv_match.group(1))

    if not kwargs:
        # fallback: if we matched structured patterns but can't parse filters,
        # just return all loans summary
        kwargs = {}

    rows = search_loans(**kwargs)
    if not rows:
        return "No loans matched those filters."

    lines = []
    for r in rows:
        lines.append(
            f"  {r['deal_id']}:{r['loan_no']} | {r['property_name']} | "
            f"{r['city']}, {r['state']} | "
            f"bal=${r['cutoff_balance']:,.0f}" if r['cutoff_balance'] else
            f"  {r['deal_id']}:{r['loan_no']} | {r['property_name']}"
        )
    return f"Found {len(rows)} loans:\n" + "\n".join(lines)


# ── retrieval (paths 1 and 3) ─────────────────────────────────────

def retrieve(collection, query: str, top_k: int = TOP_K):
    q_emb = embed(query)
    result = collection.query(query_embeddings=[q_emb], n_results=top_k)
    return list(zip(result["documents"][0], result["metadatas"][0]))


def positions_from_hits(hits):
    seen = set()
    positions = []
    for _, meta in hits:
        key = (meta["deal_id"], meta["index"])
        if key not in seen:
            seen.add(key)
            positions.append(key)
    return positions


def resolve_keys_to_positions(loan_index, loan_keys):
    positions = []
    for key in loan_keys:
        positions.extend(loan_index.get(key, []))
    seen = set()
    return [p for p in positions if not (p in seen or seen.add(p))]


def build_context(chunks_by_file, positions, before=1, after=1):
    blocks = []
    for deal_id, index in positions:
        chunks = chunks_by_file.get(deal_id, [])
        if index >= len(chunks):
            continue
        chunk = chunks[index]
        window = get_local_context(chunks, index, before=before, after=after)
        blocks.append(f"[{deal_id} lines {chunk.start_line}-{chunk.end_line}]\n{window}")
    return "\n\n---\n\n".join(blocks)

def build_graph(collection, chunks_by_file, loan_index, aliases):

    def ask_llm(prompt: str) -> str:
        response = ollama.chat(model=ANSWER_MODEL, messages=[
            {"role": "user", "content": prompt},
        ])
        return response["message"]["content"]

    def answer_from_context(question: str, positions) -> str:
        context = build_context(chunks_by_file, positions)
        prompt = (
            "Answer the question using ONLY the context below. "
            "If the context doesn't contain the answer, say so -- don't guess.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return ask_llm(prompt)

    def classify(state: State) -> State:
        route = classify_query(state["question"], aliases)
        print(f"  [route: {route}]")
        return {"route": route}

    def node_named(state: State) -> State:
        named_keys = _keys_from_names(state["question"], aliases)
        print(f"  [named-loan match: {named_keys}]")
        positions = resolve_keys_to_positions(loan_index, named_keys)
        return {"answer": answer_from_context(state["question"], positions)}

    def node_structured(state: State) -> State:
        db_answer = handle_structured_query(state["question"])
        prompt = (
            "You are answering a question about CMBS loan data. "
            "Use ONLY the data below to answer. Be concise.\n\n"
            f"Data:\n{db_answer}\n\n"
            f"Question: {state['question']}\n"
            "Answer:"
        )
        return {"answer": ask_llm(prompt)}

    def node_narrative(state: State) -> State:
        hits = retrieve(collection, state["question"])
        positions = positions_from_hits(hits)
        return {"answer": answer_from_context(state["question"], positions)}

    graph = StateGraph(State)
    graph.add_node("classify", classify)
    graph.add_node("named", node_named)
    graph.add_node("structured", node_structured)
    graph.add_node("narrative", node_narrative)

    graph.set_entry_point("classify")
    graph.add_conditional_edges("classify", lambda s: s["route"], {
        "named": "named",
        "structured": "structured",
        "narrative": "narrative",
    })
    graph.add_edge("named", END)
    graph.add_edge("structured", END)
    graph.add_edge("narrative", END)

    return graph.compile()


if __name__ == "__main__":
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    chunks_by_file, all_loans = load_all(LABELED_DIR)
    loan_index = build_loan_index(chunks_by_file)
    aliases = _build_alias_table(all_loans)

    app = build_graph(collection, chunks_by_file, loan_index, aliases)

    questions = [
        "What is the Block at Orange loan?",
        "How many loans are in California?",
        "What is the average DSCR by property type?",
        "What are the risk factors for this trust?",
    ]

    for q in questions:
        print(f"\nQ: {q}")
        result = app.invoke({"question": q})
        print(result["answer"])