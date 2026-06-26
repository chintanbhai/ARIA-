"""
Researcher Agent — Gathers information from the web and Wikipedia.
Returns a list of raw source documents ready for the Summariser.
"""

import logging
from typing import List, Dict, Any

from tools.web_search import web_search
from tools.wikipedia import wikipedia_search

logger = logging.getLogger("aria.agents.researcher")


class ResearcherAgent:
    """
    Given a query / topic, this agent:
    1. Searches the web via Tavily
    2. Fetches the Wikipedia summary as an authoritative base
    3. Returns cleaned source documents
    """

    async def run(self, query: str, max_results: int = 6) -> Dict[str, Any]:
        logger.info(f"[RESEARCHER] Starting research for: '{query}'")
        sources = []
        trace   = []

        # ── Step 1: Web search ─────────────────────────────
        trace.append({"agent": "researcher", "action": f"Web search: '{query}'"})
        web_results = await web_search(query, max_results=max_results)
        for r in web_results:
            if r.get("content"):
                sources.append({
                    "title":   r["title"],
                    "url":     r["url"],
                    "content": r["content"],
                    "source":  "web",
                })
        trace.append({"agent": "researcher", "action": f"Found {len(web_results)} web results"})

        # ── Step 2: Wikipedia ──────────────────────────────
        wiki = await wikipedia_search(query)
        if wiki and wiki.get("extract"):
            sources.append({
                "title":   wiki["title"],
                "url":     wiki["url"],
                "content": wiki["extract"],
                "source":  "wikipedia",
            })
            trace.append({"agent": "researcher", "action": f"Wikipedia: '{wiki['title']}'"})

        logger.info(f"[RESEARCHER] Collected {len(sources)} source documents")
        return {
            "query":   query,
            "sources": sources,
            "trace":   trace,
        }
