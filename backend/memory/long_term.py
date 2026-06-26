"""
Long-Term Memory — Persistent knowledge store.
Saves facts, user preferences and research summaries to a JSON file.
On retrieval, does simple keyword matching (can be upgraded to vector search).
"""

import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("aria.long_term_memory")

MEMORY_FILE = os.getenv("MEMORY_FILE", "./data/long_term_memory.json")


class LongTermMemory:
    """
    Persistent key-value + list memory store backed by a JSON file.
    Memory types:
      - "fact"       : a piece of knowledge extracted from research
      - "preference" : user preference or setting
      - "summary"    : summary of a completed research session
    """

    def __init__(self):
        self._memories: List[Dict[str, Any]] = []
        self._load()

    # ── Persistence ─────────────────────────────────────────
    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    self._memories = json.load(f)
                logger.info(f"Loaded {len(self._memories)} long-term memories")
            except Exception as e:
                logger.warning(f"Could not load memory file: {e}")
                self._memories = []

    def _save(self):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump(self._memories, f, indent=2)

    # ── Write ────────────────────────────────────────────────
    def store(self, content: str, memory_type: str = "fact", topic: str = "", metadata: Optional[Dict] = None) -> Dict:
        entry = {
            "id": f"mem_{len(self._memories)}_{int(datetime.utcnow().timestamp())}",
            "type": memory_type,
            "content": content,
            "topic": topic,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        self._memories.append(entry)
        self._save()
        logger.info(f"Stored long-term memory [{memory_type}]: {content[:60]}...")
        return entry

    def store_research_summary(self, topic: str, summary: str, sources: List[str]) -> Dict:
        return self.store(
            content=summary,
            memory_type="summary",
            topic=topic,
            metadata={"sources": sources},
        )

    # ── Read ─────────────────────────────────────────────────
    def get_all(self) -> List[Dict[str, Any]]:
        return list(reversed(self._memories))  # newest first

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple keyword search over memory content."""
        q_lower = query.lower()
        scored = []
        for mem in self._memories:
            score = 0
            text = (mem.get("content", "") + " " + mem.get("topic", "")).lower()
            for word in q_lower.split():
                if word in text:
                    score += 1
            if score > 0:
                scored.append((score, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def get_relevant_context(self, query: str) -> str:
        """Return a formatted string of relevant memories for injection into prompts."""
        relevant = self.search(query, limit=3)
        if not relevant:
            return ""
        lines = ["[Long-term memory context]"]
        for m in relevant:
            lines.append(f"- [{m['type'].upper()}] {m['content'][:200]}")
        return "\n".join(lines)

    # ── Delete ───────────────────────────────────────────────
    def clear(self):
        self._memories = []
        self._save()
        logger.info("Long-term memory cleared")

    def delete(self, memory_id: str) -> bool:
        before = len(self._memories)
        self._memories = [m for m in self._memories if m["id"] != memory_id]
        if len(self._memories) < before:
            self._save()
            return True
        return False
