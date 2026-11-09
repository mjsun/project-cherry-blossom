from backend.ai_module.app.app import build_application

class QueryService:
    def __init__(self):
        self.app = build_application()

    def query(self, query):
        return self.app.answer(query)

