"""
Retriever Agent — Semantic search over the Qdrant vector database.
Converts query to embedding, finds top-K most similar chunks.
"""

import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("aria.agents.retriever")

TOP_K = int(os.getenv("TOP_K_RETRIEVAL", 5))


class RetrieverAgent:
    """
    Given a user query, this agent:
    1. Generates a query embedding
    2. Performs cosine similarity search in Qdrant
    3. Returns top-K chunks with metadata and scores
    """

    def __init__(self, embedding_model, qdrant_client, collection_name: str):
        self.embed_model     = embedding_model
        self.qdrant          = qdrant_client
        self.collection_name = collection_name

    async def run(self, query: str, top_k: int = TOP_K) -> Dict[str, Any]:
        logger.info(f"[RETRIEVER] Semantic search for: '{query}' (top_k={top_k})")
        trace = [{"agent": "retriever", "action": f"Embedding query: '{query}'"}]

        # Generate query embedding
        query_vector = self.embed_model.encode([query], show_progress_bar=False)[0].tolist()

        # Search Qdrant
        try:
            hits = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception as e:
            logger.warning(f"[RETRIEVER] Qdrant search failed: {e} — returning empty")
            return {"query": query, "results": [], "context": "", "trace": trace}

        results = []
        seen_texts = set()
        for hit in hits:
            text = hit.payload.get("text", "")
            # Deduplicate near-identical chunks
            key = text[:80]
            if key in seen_texts:
                continue
            seen_texts.add(key)
            results.append({
                "score":  round(hit.score, 4),
                "text":   text,
                "title":  hit.payload.get("title", ""),
                "url":    hit.payload.get("url", ""),
                "source": hit.payload.get("source", ""),
                "topic":  hit.payload.get("topic", ""),
            })

        # Build context string for injection into LLM prompt
        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(
                f"[Source {i+1}: {r['title'] or r['url']}]\n{r['text']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        trace.append({"agent": "retriever", "action": f"Retrieved {len(results)} relevant chunks (score ≥ {min(r['score'] for r in results) if results else 0:.2f})"})
        logger.info(f"[RETRIEVER] Found {len(results)} results")

        return {
            "query":   query,
            "results": results,
            "context": context,
            "trace":   trace,
        }
