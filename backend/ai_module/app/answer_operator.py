import ollama


class AnswerGenerator:
    def __init__(self, answer_model: str):
        self.answer_model = answer_model

    def ask(self, prompt: str):
        response = ollama.chat(
            model=self.answer_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"]

    def answer_from_context(self, question, context):
        prompt = (
            "Answer the question using ONLY the context below. "
            "If the context does not contain the answer, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        return self.ask(prompt)

    def answer_from_database(self, question, database_result):
        prompt = (
            "You are answering a question about CMBS loan data. "
            "Use ONLY the data below.\n\n"
            f"Data:\n{database_result}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        return self.ask(prompt)