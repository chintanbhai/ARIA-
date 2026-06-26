"""
Short-Term Memory — Conversation context manager.
Stores messages per session in memory (dict).
Implements a sliding window to stay within token limits.
"""

from typing import List, Dict, Any
from datetime import datetime


class ShortTermMemory:
    """
    Manages conversation histories keyed by session_id.
    - Stores raw message dicts: {"role": "user"|"assistant", "content": str}
    - Applies a sliding window (max_messages) to avoid exceeding context limits
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        # { session_id: { "messages": [...], "created_at": str, "topic": str } }
        self._store: Dict[str, Dict[str, Any]] = {}

    def add_message(self, session_id: str, role: str, content: str, topic: str = "") -> None:
        if session_id not in self._store:
            self._store[session_id] = {
                "messages": [],
                "created_at": datetime.utcnow().isoformat(),
                "topic": topic,
            }
        session = self._store[session_id]
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Update topic if provided
        if topic:
            session["topic"] = topic

        # Sliding window: keep last max_messages
        if len(session["messages"]) > self.max_messages:
            session["messages"] = session["messages"][-self.max_messages:]

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Return messages in Claude API format (role + content only)."""
        session = self._store.get(session_id, {})
        return [
            {"role": m["role"], "content": m["content"]}
            for m in session.get("messages", [])
        ]

    def get_raw(self, session_id: str) -> Dict[str, Any]:
        """Return full session data including timestamps."""
        return self._store.get(session_id, {"messages": [], "created_at": None, "topic": ""})

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Return summary of all sessions for history view."""
        result = []
        for sid, data in self._store.items():
            msgs = data.get("messages", [])
            preview = msgs[-1]["content"][:160] if msgs else ""
            result.append({
                "id": sid,
                "topic": data.get("topic") or (msgs[0]["content"][:60] if msgs else sid),
                "created_at": data.get("created_at"),
                "message_count": len(msgs),
                "preview": preview,
            })
        # Sort newest first
        result.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return result

    def clear_session(self, session_id: str) -> None:
        self._store.pop(session_id, None)
