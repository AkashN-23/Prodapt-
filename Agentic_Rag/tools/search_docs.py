"""
tools/search_docs.py
--------------------
Semantic search over indexed annual report PDFs.
Uses a local FAISS or Chroma vector store — no cloud DB required.
"""

import os
from typing import Optional

# Swap Chroma for FAISS if preferred — interface is identical for our use case
try:
    import chromadb
    _USE_CHROMA = True
except ImportError:
    _USE_CHROMA = False

_collection = None   # lazy-loaded on first call

def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    persist_path = os.getenv("VECTOR_STORE_PATH", "./data/chroma_store")
    client = chromadb.PersistentClient(path=persist_path)
    _collection = client.get_collection("annual_reports")
    return _collection


def run(query: str, top_k: int = 3) -> dict:
    """
    Perform semantic similarity search against the indexed annual report chunks.

    Args:
        query:  Natural language query string.
        top_k:  Number of chunks to return (default 3).

    Returns:
        {
            "results": [
                {
                    "chunk_text": str,
                    "source_file": str,    # e.g. "infosys_ar_fy24.pdf"
                    "page_number": int,
                    "score": float         # cosine similarity, higher = more relevant
                },
                ...
            ],
            "query": str,
            "total_returned": int
        }
    """
    try:
        collection = _get_collection()
        results    = collection.query(query_texts=[query], n_results=top_k)

        chunks = []
        for i in range(len(results["documents"][0])):
            meta = results["metadatas"][0][i]
            chunks.append({
                "chunk_text":  results["documents"][0][i],
                "source_file": meta.get("source_file", "unknown"),
                "page_number": meta.get("page_number", 0),
                "score":       round(1 - results["distances"][0][i], 4),
            })

        return {
            "results":        chunks,
            "query":          query,
            "total_returned": len(chunks),
        }

    except Exception as exc:
        return {"error": str(exc), "results": [], "query": query, "total_returned": 0}
