"""
Orchestrator Agent — The brain of ARIA.
Uses LangGraph to coordinate the full research pipeline:
  Researcher → Summariser → Retriever → Writer

Also handles the simpler "chat with RAG" flow when no new research is needed.
"""

import os
import logging
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from agents.researcher import ResearcherAgent
from agents.summariser import SummariserAgent
from agents.retriever  import RetrieverAgent
from agents.writer     import WriterAgent

logger = logging.getLogger("aria.agents.orchestrator")

COLLECTION  = "aria_knowledge"
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
VECTOR_DIM  = 384  # all-MiniLM-L6-v2 output dim
QDRANT_URL  = os.getenv("QDRANT_URL", "")
QDRANT_KEY  = os.getenv("QDRANT_API_KEY", "")


# ── LangGraph state schema ─────────────────────────────────
class ResearchState(TypedDict):
    query:            str
    session_id:       str
    use_web_search:   bool
    use_rag:          bool
    history:          List[Dict[str, str]]
    long_term_ctx:    str
    raw_sources:      List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    retrieved_context: str
    answer:           str
    citations:        List[Dict[str, str]]
    agent_trace:      List[Dict[str, str]]
    error:            Optional[str]


class OrchestratorAgent:
    """
    Initialises all sub-agents and builds the LangGraph pipeline.
    Exposes:
      - run_chat(query, session_id, history, long_term_ctx, use_web_search, use_rag)
      - run_research(topic, depth, session_id)
    """

    def __init__(self):
        logger.info("Initialising embedding model...")
        self.embed_model = SentenceTransformer(EMBED_MODEL)
        logger.info(f"Embedding model loaded: {EMBED_MODEL}")

        # Qdrant: persistent if URL provided, else in-memory
        if QDRANT_URL:
            self.qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY or None)
            logger.info(f"Qdrant connected: {QDRANT_URL}")
        else:
            self.qdrant = QdrantClient(":memory:")
            logger.info("Qdrant running in-memory (dev mode)")

        self._ensure_collection()

        # Sub-agents
        self.researcher = ResearcherAgent()
        self.summariser = SummariserAgent(self.embed_model, self.qdrant, COLLECTION)
        self.retriever  = RetrieverAgent(self.embed_model, self.qdrant, COLLECTION)
        self.writer     = WriterAgent()

        # Document registry (for /api/vectordb/documents endpoint)
        self._doc_registry: List[Dict] = []

        # Build LangGraph
        self._graph = self._build_graph()
        logger.info("OrchestratorAgent ready ✅")

    def _ensure_collection(self):
        existing = [c.name for c in self.qdrant.get_collections().collections]
        if COLLECTION not in existing:
            self.qdrant.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {COLLECTION}")

    # ── LangGraph nodes ────────────────────────────────────
    def _build_graph(self) -> Any:
        builder = StateGraph(ResearchState)

        builder.add_node("researcher", self._node_researcher)
        builder.add_node("summariser", self._node_summariser)
        builder.add_node("retriever",  self._node_retriever)
        builder.add_node("writer",     self._node_writer)

        # Edges
        builder.set_entry_point("researcher")
        builder.add_edge("researcher", "summariser")
        builder.add_edge("summariser", "retriever")
        builder.add_edge("retriever",  "writer")
        builder.add_edge("writer",     END)

        return builder.compile()

    async def _node_researcher(self, state: ResearchState) -> ResearchState:
        if not state["use_web_search"]:
            state["raw_sources"] = []
            state["agent_trace"].append({"agent": "researcher", "action": "Skipped (web search disabled)"})
            return state
        result = await self.researcher.run(state["query"])
        state["raw_sources"]  = result["sources"]
        state["agent_trace"] += result["trace"]
        return state

    async def _node_summariser(self, state: ResearchState) -> ResearchState:
        if not state["raw_sources"]:
            state["agent_trace"].append({"agent": "summariser", "action": "Skipped (no sources to index)"})
            return state
        result = await self.summariser.run(state["raw_sources"], topic=state["query"])
        state["agent_trace"] += result["trace"]
        # Update doc registry
        self._doc_registry = (result["documents"] + self._doc_registry)[:200]
        return state

    async def _node_retriever(self, state: ResearchState) -> ResearchState:
        if not state["use_rag"]:
            state["retrieved_chunks"]  = []
            state["retrieved_context"] = ""
            state["agent_trace"].append({"agent": "retriever", "action": "Skipped (RAG disabled)"})
            return state
        result = await self.retriever.run(state["query"])
        state["retrieved_chunks"]  = result["results"]
        state["retrieved_context"] = result["context"]
        state["agent_trace"]      += result["trace"]
        return state

    async def _node_writer(self, state: ResearchState) -> ResearchState:
        # Merge sources: raw + retrieved
        all_sources = state.get("raw_sources", []) + [
            {"title": r["title"], "url": r["url"]} for r in state.get("retrieved_chunks", [])
        ]
        result = await self.writer.run(
            query=state["query"],
            context=state.get("retrieved_context", ""),
            conversation_history=state["history"],
            long_term_context=state.get("long_term_ctx", ""),
            sources=all_sources,
        )
        state["answer"]      = result["answer"]
        state["citations"]   = result["citations"]
        state["agent_trace"] += result["trace"]
        return state

    # ── Public API ─────────────────────────────────────────
    async def run_chat(
        self,
        query: str,
        session_id: str,
        history: List[Dict[str, str]],
        long_term_ctx: str = "",
        use_web_search: bool = True,
        use_rag: bool = True,
    ) -> Dict[str, Any]:
        """Full agentic chat pipeline."""
        initial_state: ResearchState = {
            "query":             query,
            "session_id":        session_id,
            "use_web_search":    use_web_search,
            "use_rag":           use_rag,
            "history":           history,
            "long_term_ctx":     long_term_ctx,
            "raw_sources":       [],
            "retrieved_chunks":  [],
            "retrieved_context": "",
            "answer":            "",
            "citations":         [],
            "agent_trace":       [{"agent": "orchestrator", "action": f"Received query: '{query}'"}],
            "error":             None,
        }
        final_state = await self._graph.ainvoke(initial_state)
        return {
            "answer":      final_state["answer"],
            "citations":   final_state["citations"],
            "agent_trace": final_state["agent_trace"],
            "sources_indexed": len(self._doc_registry),
        }

    async def run_research(self, topic: str, depth: str = "standard") -> Dict[str, Any]:
        """Deep research: always uses web search, indexes everything."""
        max_results = {"quick": 3, "standard": 8, "deep": 15}.get(depth, 8)
        raw = await self.researcher.run(topic, max_results=max_results)
        idx = await self.summariser.run(raw["sources"], topic=topic)

        # After indexing, retrieve and write summary
        retrieval = await self.retriever.run(topic, top_k=6)
        summary   = await self.writer.run(
            query=f"Write a comprehensive summary of: {topic}",
            context=retrieval["context"],
            conversation_history=[],
            sources=raw["sources"],
        )

        trace = raw["trace"] + idx["trace"] + retrieval["trace"] + summary["trace"]
        return {
            "answer":          summary["answer"],
            "citations":       summary["citations"],
            "agent_trace":     trace,
            "sources_indexed": idx["total_chunks"],
        }

    # ── Stats for UI ───────────────────────────────────────
    def get_vector_stats(self) -> Dict[str, Any]:
        try:
            info   = self.qdrant.get_collection(COLLECTION)
            topics = list({d.get("topic", "") for d in self._doc_registry if d.get("topic")})
            return {
                "total_documents": len(self._doc_registry),
                "total_chunks":    info.points_count or 0,
                "unique_topics":   len(topics),
                "collection":      COLLECTION,
                "vector_size":     VECTOR_DIM,
            }
        except Exception as e:
            return {"total_documents": 0, "total_chunks": 0, "unique_topics": 0, "error": str(e)}

    def get_documents(self) -> List[Dict]:
        return self._doc_registry[:50]

    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        result = await self.retriever.run(query, top_k=top_k)
        return result["results"]
