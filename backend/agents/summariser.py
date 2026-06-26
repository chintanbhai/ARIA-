"""
Summariser Agent — Chunks source documents, generates embeddings,
and upserts them into the Qdrant vector database.
"""

import os
import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("aria.agents.summariser")

CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", 400))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 80))


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by word count."""
    words  = text.split()
    chunks = []
    start  = 0
    while start < len(words):
        end = start + size
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


class SummariserAgent:
    """
    Given raw source documents from the Researcher, this agent:
    1. Chunks each document
    2. Generates sentence-transformer embeddings
    3. Upserts into Qdrant with metadata
    Returns the count of indexed chunks.
    """

    def __init__(self, embedding_model, qdrant_client, collection_name: str):
        self.embed_model     = embedding_model
        self.qdrant          = qdrant_client
        self.collection_name = collection_name

    async def run(self, sources: List[Dict[str, Any]], topic: str = "") -> Dict[str, Any]:
        logger.info(f"[SUMMARISER] Indexing {len(sources)} sources for topic '{topic}'")
        trace         = []
        total_chunks  = 0
        doc_records   = []

        for src in sources:
            content = src.get("content", "")
            if not content.strip():
                continue

            chunks = chunk_text(content)
            if not chunks:
                continue

            # Generate embeddings in batch
            embeddings = self.embed_model.encode(chunks, show_progress_bar=False).tolist()

            doc_id  = str(uuid.uuid4())
            points  = []
            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid.uuid4())
                points.append({
                    "id":     point_id,
                    "vector": vector,
                    "payload": {
                        "doc_id":     doc_id,
                        "title":      src.get("title", ""),
                        "url":        src.get("url", ""),
                        "source":     src.get("source", "web"),
                        "topic":      topic,
                        "chunk_index": i,
                        "text":       chunk,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                })

            # Upsert into Qdrant
            from qdrant_client.models import PointStruct
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                    for p in points
                ],
            )

            total_chunks += len(chunks)
            doc_records.append({
                "doc_id":     doc_id,
                "title":      src.get("title", "Untitled"),
                "url":        src.get("url", ""),
                "source":     src.get("source", "web"),
                "chunks":     len(chunks),
                "created_at": datetime.utcnow().isoformat(),
            })

            trace.append({
                "agent":  "summariser",
                "action": f"Indexed '{src.get('title', 'doc')}' → {len(chunks)} chunks",
            })
            logger.info(f"[SUMMARISER] Indexed {len(chunks)} chunks for '{src.get('title', '')}'")

        logger.info(f"[SUMMARISER] Total chunks indexed: {total_chunks}")
        return {
            "total_chunks": total_chunks,
            "documents":    doc_records,
            "trace":        trace,
        }
