from backend.ai_module.app.chroma_client import get_collection
from backend.ai_module.app.data_loader import DataLoader
from backend.ai_module.app.loan_index import LoanIndex
from backend.ai_module.app.query_classifier import QueryClassifier
from backend.ai_module.app.structured_query_handler import StructuredQueryHandler
from backend.ai_module.app.retriever import Retriever
from backend.ai_module.app.context_builder import ContextBuilder
from backend.ai_module.app.answer_generator import AnswerGenerator
from backend.ai_module.app.query_router import QueryRouter

import os

LABELED_DIR = os.path.join(os.path.dirname(__file__), "data", "labeled_data")


def _build_alias_table(loans):
    """
    Property name -> loan key, longest names first so a specific name wins
    over a shorter one contained inside it. Short names are skipped: they
    collide with ordinary prose.
    """
    aliases = [(rec["property_name"], key) for key, rec in loans.items()
               if rec["property_name"] and len(rec["property_name"]) >= 12]
    return sorted(aliases, key=lambda pair: -len(pair[0]))


def build_application():
    collection = get_collection()

    loader = DataLoader(LABELED_DIR)
    chunks_by_file, all_loans = loader.load()

    loan_index = LoanIndex(chunks_by_file)
    aliases = _build_alias_table(all_loans)

    classifier = QueryClassifier(aliases)
    structured_handler = StructuredQueryHandler()

    retriever = Retriever(collection=collection)

    context_builder = ContextBuilder(chunks_by_file)

    answer_generator = AnswerGenerator()

    return QueryRouter(
        classifier=classifier,
        structured_handler=structured_handler,
        loan_index=loan_index,
        retriever=retriever,
        context_builder=context_builder,
        answer_generator=answer_generator,
    )

