class ContextBuilder:
    def __init__(self, chunks_by_file):
        self.chunks_by_file = chunks_by_file

    def source_texts(self, positions, fallback_docs=None):
        """
        Each position's own chunk text (not a windowed/merged context), for
        displaying as a citation in the UI and for citing by id in the
        answer-generation prompt.
        """
        fallback_docs = fallback_docs or {}
        sources = []

        for deal_id, index in positions:
            chunks = self.chunks_by_file.get(deal_id, [])

            if index < len(chunks):
                sources.append({
                    "deal_id": deal_id,
                    "chunk_index": index,
                    "text": chunks[index].text(),
                })
                continue

            document = fallback_docs.get((deal_id, index))
            if document is not None:
                sources.append({
                    "deal_id": deal_id,
                    "chunk_index": index,
                    "text": document,
                })

        return sources

    def labeled_sources(self, positions, fallback_docs=None):
        """source_texts(), each tagged with a short citation id ("C0", "C1", ...)."""
        sources = self.source_texts(positions, fallback_docs=fallback_docs)

        for i, source in enumerate(sources):
            source["id"] = f"C{i}"

        return sources
