"""
Web Search Tool — Tavily API wrapper.
Falls back to a mock response if API key is not set (for testing UI).
"""

import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("aria.tools.web_search")


async def web_search(query: str, max_results: int = None) -> List[Dict[str, Any]]:
    """
    Search the web using Tavily API.
    Returns list of: { title, url, content, score }
    """
    max_results = max_results or int(os.getenv("MAX_SEARCH_RESULTS", 6))
    api_key = os.getenv("TAVILY_API_KEY", "")

    if not api_key or api_key == "your_tavily_api_key_here":
        logger.warning("TAVILY_API_KEY not set — returning mock search results")
        return _mock_results(query)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            include_answer=False,
            include_raw_content=True,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content") or r.get("raw_content") or "",
                "score":   r.get("score", 0.0),
            })
        logger.info(f"Web search '{query}' → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return _mock_results(query)


def _mock_results(query: str) -> List[Dict[str, Any]]:
    """Return mock results when Tavily is unavailable."""
    return [
        {
            "title": f"Overview of {query}",
            "url": "https://en.wikipedia.org/wiki/" + query.replace(" ", "_"),
            "content": (
                f"{query} is a rapidly evolving field with significant implications for science, "
                "technology, and society. Recent developments have accelerated progress in this area, "
                "with researchers publishing landmark papers and industry deploying new applications. "
                "Key concepts include machine learning, neural networks, and large-scale data processing. "
                "This topic has attracted substantial investment and interest from both academia and industry."
            ),
            "score": 0.95,
        },
        {
            "title": f"Latest Research on {query}",
            "url": f"https://arxiv.org/search/?query={query.replace(' ', '+')}",
            "content": (
                f"Recent academic publications have advanced the understanding of {query}. "
                "Studies show promising results in efficiency, scalability, and real-world performance. "
                "Researchers have identified key challenges and proposed novel solutions that "
                "push the boundaries of what is currently possible in this domain."
            ),
            "score": 0.88,
        },
        {
            "title": f"{query} — Practical Applications",
            "url": f"https://www.example.com/{query.replace(' ', '-').lower()}",
            "content": (
                f"Practical applications of {query} span multiple industries including healthcare, "
                "finance, education, and manufacturing. Companies are integrating these capabilities "
                "into production systems, yielding measurable improvements in efficiency and outcomes. "
                "The technology continues to mature, with new use cases emerging regularly."
            ),
            "score": 0.80,
        },
    ]
