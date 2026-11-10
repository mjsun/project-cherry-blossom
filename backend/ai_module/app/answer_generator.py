import json

from backend.ai_module.app.llm import chat


class AnswerGenerator:
    def ask(self, prompt: str):
        return chat(prompt)

    def answer_from_context(self, question, labeled_sources):
        """
        labeled_sources: [{"id": "C0", "deal_id": ..., "chunk_index": ..., "text": ...}, ...]
        Returns {"answer": str, "citations": [{"id": str, "quote": str}]}.
        """
        context = "\n\n---\n\n".join(
            f"[{source['id']}]\n{source['text']}" for source in labeled_sources
        )

        prompt = (
            "Answer the question using ONLY the context below. Each block is "
            "labeled with an id like [C0].\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Respond with ONLY a JSON object (no other text), in this exact shape:\n"
            '{"answer": "<your answer>", '
            '"citations": [{"id": "<block id you drew the answer from>", '
            '"quote": "<the exact short sentence or phrase, copied verbatim '
            'from that block, that supports the answer>"}]}\n'
            "Include one citation per block you actually used to answer -- "
            "do not cite a block you didn't use. If the context doesn't "
            'contain the answer, say so in "answer" and return "citations": [].'
        )

        return self._parse_cited_response(self.ask(prompt))

    def answer_from_database(self, question, database_result):
        prompt = (
            "You are answering a question about CMBS loan data. "
            "Use ONLY the data below.\n\n"
            f"Data:\n{database_result}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        return self.ask(prompt)

    @staticmethod
    def _parse_cited_response(raw: str):
        start, end = raw.find("{"), raw.rfind("}")

        if start == -1 or end == -1:
            return {"answer": raw.strip(), "citations": []}

        try:
            parsed = json.loads(raw[start:end + 1])
        except ValueError:
            return {"answer": raw.strip(), "citations": []}

        answer = parsed.get("answer")
        citations = parsed.get("citations")

        if not isinstance(answer, str):
            answer = raw.strip()

        if not isinstance(citations, list):
            citations = []

        return {"answer": answer, "citations": citations}
