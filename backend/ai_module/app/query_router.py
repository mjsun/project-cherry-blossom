class QueryRouter:
    def __init__(
        self,
        classifier,
        structured_handler,
        loan_index,
        retriever,
        context_builder,
        answer_generator,
    ):
        self.classifier = classifier
        self.structured_handler = structured_handler
        self.loan_index = loan_index
        self.retriever = retriever
        self.context_builder = context_builder
        self.answer_generator = answer_generator

    def answer(self, question: str) -> dict:
        route = self.classifier.classify(question)

        if route == "named":
            return self._answer_named(question)

        if route == "structured":
            return self._answer_structured(question)

        return self._answer_narrative(question)

    def _answer_named(self, question: str):
        loan_keys = self.classifier.find_named_keys(question)
        positions = self.loan_index.resolve(loan_keys)

        sources = self.context_builder.labeled_sources(positions)
        result = self.answer_generator.answer_from_context(question, sources)

        return {
            "answer": result["answer"],
            "route": "named",
            "sources": self._cited_sources(sources, result["citations"]),
        }

    def _answer_structured(self, question: str):
        database_result = self.structured_handler.handle(question)

        answer = self.answer_generator.answer_from_database(
            question,
            database_result,
        )

        return {
            "answer": answer,
            "route": "structured",
            "sources": [],
        }

    def _answer_narrative(self, question: str):
        hits = self.retriever.retrieve(question)
        positions = self.retriever.positions_from_hits(hits)
        fallback_docs = self.retriever.fallback_text_from_hits(hits)

        sources = self.context_builder.labeled_sources(positions, fallback_docs=fallback_docs)
        result = self.answer_generator.answer_from_context(question, sources)

        return {
            "answer": result["answer"],
            "route": "narrative",
            "sources": self._cited_sources(sources, result["citations"]),
        }

    @staticmethod
    def _cited_sources(sources, citations):
        """Only the chunks the model actually cited, each with its quoted
        snippet attached so the UI can highlight just that part."""
        by_id = {source["id"]: source for source in sources}
        quotes = {
            citation.get("id"): citation.get("quote")
            for citation in citations
            if isinstance(citation, dict)
        }

        print(f"DEBUG _cited_sources: {len(sources)} sources, ids={list(by_id.keys())}")
        print(f"DEBUG _cited_sources: raw citations={citations!r}")

        cited = []
        for source_id, quote in quotes.items():
            source = by_id.get(source_id)
            if source is None:
                continue

            cited.append({
                "deal_id": source["deal_id"],
                "chunk_index": source["chunk_index"],
                "text": source["text"],
                "highlight": quote,
            })

        return cited
