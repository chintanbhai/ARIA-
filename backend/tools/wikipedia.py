"""
Wikipedia Tool — Fetch summaries from Wikipedia REST API.
No API key required.
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("aria.tools.wikipedia")

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"


async def wikipedia_search(topic: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a Wikipedia summary for a topic.
    Returns: { title, extract, url } or None
    """
    slug = topic.strip().replace(" ", "_")
    url  = WIKI_API + slug

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, follow_redirects=True)
            if r.status_code != 200:
                logger.warning(f"Wikipedia: no article for '{topic}' (status {r.status_code})")
                return None
            data = r.json()
            return {
                "title":   data.get("title", topic),
                "extract": data.get("extract", ""),
                "url":     data.get("content_urls", {}).get("desktop", {}).get("page", url),
            }
    except Exception as e:
        logger.error(f"Wikipedia fetch failed: {e}")
        return None
