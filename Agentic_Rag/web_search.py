"""
tools/web_search.py
-------------------
Live web search via the Tavily API.
Returns top-3 result snippets with URL and publication date.
"""

import os
from tavily import TavilyClient


def run(query: str, max_results: int = 3) -> dict:
    """
    Search the live web for recent information.

    Args:
        query:       Short search query (under 10 words).
        max_results: Number of results to return (default 3).

    Returns:
        {
            "results": [
                {
                    "title":            str,
                    "url":              str,
                    "snippet":          str,
                    "published_date":   str   # ISO date string or empty
                },
                ...
            ],
            "query":          str,
            "total_returned": int
        }
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {
            "error":          "TAVILY_API_KEY not set in environment.",
            "results":        [],
            "query":          query,
            "total_returned": 0,
        }

    try:
        client   = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results, search_depth="basic")

        results = [
            {
                "title":          r.get("title", ""),
                "url":            r.get("url", ""),
                "snippet":        r.get("content", "")[:400],
                "published_date": r.get("published_date", ""),
            }
            for r in response.get("results", [])
        ]

        return {
            "results":        results,
            "query":          query,
            "total_returned": len(results),
        }

    except Exception as exc:
        return {
            "error":          str(exc),
            "results":        [],
            "query":          query,
            "total_returned": 0,
        }
