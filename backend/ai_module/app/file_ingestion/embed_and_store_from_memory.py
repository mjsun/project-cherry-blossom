"""
Embed chunks and load them into a local Chroma vector DB.

Takes an already-built list of chunks (e.g. from ChunkFilingFromMemory) and:
  1. embeds each chunk's embedding_text() via the configured LLM provider
     (see ai_module/app/llm -- Ollama or OpenAI, picked by LLM_PROVIDER)
  2. stores it in Chroma, metadata = deal_id/series/index/label/start_line/end_line
  3. builds a plain loan_index: loan_key -> [chunk ids] for EXACT lookup

Long chunks are split before embedding (RecursiveCharacterTextSplitter)
instead of truncated, so nothing becomes unsearchable -- grounding still
uses the full original chunk independent of how many pieces it got split
into here.

`series` (e.g. "2024-5C7") is read from the cover page and stored on every
piece, so a question naming a deal can be searched within that deal only.
"""

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.ai_module.app.chroma_client import get_collection
from backend.ai_module.app.llm import embed

MAX_EMBED_CHARS = 3000

# Deal series code like "2024-5C7", "2026-B42", "2018-C2". Requires a letter
# so registration numbers like "280224-01" don't match.
SERIES_RE = re.compile(r"\b(\d{4}-[A-Z0-9]*[A-Z][A-Z0-9]*)\b", re.IGNORECASE)


def find_series(text: str) -> str:
    m = SERIES_RE.search(text)
    return m.group(1).upper() if m else ""


class EmbedAndStoreFromMemory:
    """Embed a list of chunks and upsert them into the Chroma collection."""

    def __init__(self, chunks):
        self.chunks = chunks
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=MAX_EMBED_CHARS,
            chunk_overlap=200,   # keeps a little context across split boundaries
        )

    @staticmethod
    def _embed(text: str):
        return embed(text)

    def _split_for_embedding(self, text: str):
        if len(text) <= MAX_EMBED_CHARS:
            return [text]
        return self._splitter.split_text(text)

    def store(self, on_total_chunks=None, on_chunk_done=None):
        """
        Embed every chunk, upsert into Chroma.
        Returns (collection, loan_index) for later retrieval.
        """
        collection = get_collection()

        # the cover page (one of the first few chunks) names the series
        series = ""
        for chunk in self.chunks[:5]:
            series = find_series(chunk.text())
            if series:
                break

        loan_index = {}   # loan_key -> [chunk_id, ...]   (exact match)
        ids, docs, metas, embeddings = [], [], [], []

        if on_total_chunks:
            on_total_chunks(len(self.chunks))

        for chunk in self.chunks:
            text = chunk.embedding_text()
            pieces = self._split_for_embedding(text)

            for piece_i, piece in enumerate(pieces):
                chunk_id = f"{chunk.deal_id}:{chunk.index}:{piece_i}"
                ids.append(chunk_id)
                docs.append(piece)
                metas.append({
                    "deal_id": chunk.deal_id,
                    "series": series,
                    "index": chunk.index,
                    "label": chunk.label,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "loan_keys_csv": ",".join(chunk.loan_keys),  # display only
                })
                embeddings.append(self._embed(piece))

                for key in chunk.loan_keys:
                    loan_index.setdefault(key, []).append(chunk_id)

            if on_chunk_done:
                on_chunk_done()

        if ids:
            collection.upsert(ids=ids, documents=docs, metadatas=metas,
                               embeddings=embeddings)

        print(f"embedded {len(ids)} pieces ({len(self.chunks)} chunks), series={series or '?'}")

        return collection, loan_index