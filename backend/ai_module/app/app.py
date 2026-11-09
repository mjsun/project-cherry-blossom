import chromadb

from chunk_filing import _build_alias_table
from backend.ai_module.app.data_loader import DataLoader
from backend.ai_module.app.loan_index import LoanIndex
from backend.ai_module.app.query_classifier import QueryClassifier
from backend.ai_module.app.structured_query_handler import StructuredQueryHandler
from backend.ai_module.app.retriever import Retriever
from backend.ai_module.app.context_builder import ContextBuilder
from backend.ai_module.app.answer_generator import AnswerGenerator
from backend.ai_module.app.query_router import QueryRouter

import os

EMBED_MODEL = "nomic-embed-text"
ANSWER_MODEL = "qwen2.5:14b"
DB_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
COLLECTION_NAME = "cmbs_filings"
LABELED_DIR = "./data/labeled_data"


def build_application():
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_collection(COLLECTION_NAME)

    loader = DataLoader(LABELED_DIR)
    chunks_by_file, all_loans = loader.load()

    loan_index = LoanIndex(chunks_by_file)
    aliases = _build_alias_table(all_loans)

    classifier = QueryClassifier(aliases)
    structured_handler = StructuredQueryHandler()

    retriever = Retriever(
        collection=collection,
        embedding_model=EMBED_MODEL,
    )

    context_builder = ContextBuilder(chunks_by_file)

    answer_generator = AnswerGenerator(
        answer_model=ANSWER_MODEL,
    )

    return QueryRouter(
        classifier=classifier,
        structured_handler=structured_handler,
        loan_index=loan_index,
        retriever=retriever,
        context_builder=context_builder,
        answer_generator=answer_generator,
    )

