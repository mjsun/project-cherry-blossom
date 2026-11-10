"""
Single shared Chroma client/collection for the whole process.

Embedded Chroma (PersistentClient) is backed by SQLite and isn't safe when
multiple independent client instances open the same path concurrently --
one instance's writes can leave another's in-memory index out of sync with
what's on disk (surfaces as chromadb.errors.InternalError: Error finding
id). Building the client once here, and having every caller (ingestion,
query) go through get_collection(), means there is only ever one client
talking to the on-disk store.
"""

import os
import chromadb

DB_DIR = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
COLLECTION_NAME = "cmbs_filings"

_client = chromadb.PersistentClient(path=DB_DIR)
_collection = _client.get_or_create_collection(COLLECTION_NAME)


def get_collection():
    return _collection
