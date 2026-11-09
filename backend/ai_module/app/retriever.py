import ollama


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