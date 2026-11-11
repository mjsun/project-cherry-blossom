import re

from backend.ai_module.app.llm import embed

SERIES_RE = re.compile(r"\b(\d{4}-[A-Z0-9]*[A-Z][A-Z0-9]*)\b", re.IGNORECASE)

class Retriever:
    def __init__(
        self,
        collection,
        top_k: int = 25,
    ):
        self.collection = collection
        self.top_k = top_k

    def embed(self, text: str):
        return embed(text)

    def retrieve(self, question: str):
        embedding = self.embed(question)

        # If the question names a deal series (e.g. "2024-5C7"), search only that deal.
        match = SERIES_RE.search(question)
        if match:
            result = self.collection.query(
                query_embeddings=[embedding],
                n_results=self.top_k,
                where={"series": match.group(1).upper()},
            )
            hits = list(zip(result["documents"][0], result["metadatas"][0]))
            print(f"DEBUG retrieve: series filter {match.group(1).upper()!r} -> {len(hits)} hits")
            # Fall back to an unfiltered search if the named series doesn't
            # match any stored metadata exactly (e.g. extraction formatted
            # it differently) -- better a possibly-wrong-deal answer than
            # silently returning nothing.
            if hits:
                return hits

        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=self.top_k,
        )

        return list(
            zip(
                result["documents"][0],
                result["metadatas"][0],
            )
        )

    def positions_from_hits(self, hits):
        positions = []
        seen = set()

        for _, metadata in hits:
            position = (
                metadata["deal_id"],
                metadata["index"],
            )

            if position not in seen:
                seen.add(position)
                positions.append(position)

        return positions

    def fallback_text_from_hits(self, hits):
        """
        Chroma's own stored document text per (deal_id, index), to fall back
        on when a position isn't in chunks_by_file -- e.g. a deal ingested
        straight into the vector DB (file_ingestion) rather than loaded from
        a local labeled .tsv file.
        """
        fallback = {}

        for document, metadata in hits:
            position = (
                metadata["deal_id"],
                metadata["index"],
            )

            if position not in fallback:
                fallback[position] = document

        return fallback