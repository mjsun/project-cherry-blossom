from backend.ai_module.app.state import QueryState


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

    def answer(self, question: str) -> str:
        route = self.classifier.classify(question)

        if route == "named":
            return self._answer_named(question)

        if route == "structured":
            return self._answer_structured(question)

        return self._answer_narrative(question)

    def _answer_named(self, question: str):
        loan_keys = self.classifier.find_named_keys(question)
        positions = self.loan_index.resolve(loan_keys)

        context = self.context_builder.build(positions)

        return self.answer_generator.answer_from_context(
            question,
            context,
        )

    def _answer_structured(self, question: str):
        database_result = self.structured_handler.handle(question)

        return self.answer_generator.answer_from_database(
            question,
            database_result,
        )

    def _answer_narrative(self, question: str):
        hits = self.retriever.retrieve(question)
        positions = self.retriever.positions_from_hits(hits)

        context = self.context_builder.build(positions)

        return self.answer_generator.answer_from_context(
            question,
            context,
        )