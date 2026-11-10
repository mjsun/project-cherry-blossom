import json

from backend.ai_module.app.llm import chat


class AnswerGenerator:
    def ask(self, prompt: str, *, json_mode: bool = False):
        return chat(prompt, temperature=0 if json_mode else 0.7, json_mode=json_mode)

    def answer_from_context(self, question, labeled_sources):
        """
        labeled_sources: [{"id": "C0", "deal_id": ..., "chunk_index": ..., "text": ...}, ...]
        Returns {"answer": str, "citations": [{"id": str, "quote": str}]}.
        """
        if not labeled_sources:
            # No retrieved context at all -- never let the model answer from
            # its own general knowledge here; refuse before it's even asked.
            return {
                "answer": "I don't have that filing. It hasn't been ingested yet.",
                "citations": [],
            }

        context = "\n\n---\n\n".join(
            f"[{source['id']}]\n{source['text']}" for source in labeled_sources
        )

        prompt = (
            "Answer the question using ONLY the context below. Do not use any "
            "outside knowledge, even if you recognize the deal or company "
            "named in the question -- if it isn't in the context, you don't "
            "know it. Each block is labeled with an id like [C0].\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Respond with ONLY a JSON object (no other text), in this exact shape:\n"
            '{"answer": "<your answer>", '
            '"citations": [{"id": "<block id you drew the answer from>", '
            '"quote": "<the exact short phrase, copied character-for-character '
            'from that block, that supports the answer -- it must appear '
            'verbatim in the block text>"}]}\n'
            "If your answer draws on a block, you MUST cite that block's id -- "
            "never leave citations empty when the context actually supports the "
            "answer. Only cite a block you truly used. If the context doesn't "
            'contain the answer, say so in "answer" and return "citations": [].'
        )

        result = self._parse_cited_response(self.ask(prompt, json_mode=True))
        result["citations"] = self._verified_citations(result["citations"], labeled_sources)
        return result

    @staticmethod
    def _verified_citations(citations, labeled_sources):
        """Drop any citation whose quote isn't an actual verbatim substring
        of the block it claims to come from -- an unverifiable citation is
        worse than none, since the UI highlights the quote inside the
        source text."""
        texts_by_id = {source["id"]: source["text"] for source in labeled_sources}

        verified = []
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            block_text = texts_by_id.get(citation.get("id"))
            quote = citation.get("quote")
            if block_text and isinstance(quote, str) and quote in block_text:
                verified.append(citation)

        return verified

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
