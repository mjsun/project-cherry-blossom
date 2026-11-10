import re
import ollama

SERIES_RE = re.compile(r"\b(\d{4}-[A-Z0-9]*[A-Z][A-Z0-9]*)\b", re.IGNORECASE)

class Retriever:
    def __init__(
        self,
        collection,
        embedding_model: str,
        top_k: int = 25,
    ):
        self.collection = collection
        self.embedding_model = embedding_model
        self.top_k = top_k

    def embed(self, text: str):
        result = ollama.embeddings(
            model=self.embedding_model,
            prompt=text,
        )

        return result["embedding"]

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
            # Deal named but not ingested -> no hits, rather than other deals.
            return list(zip(result["documents"][0], result["metadatas"][0]))

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