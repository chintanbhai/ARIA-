"""
ARIA — AI Research Intelligence Assistant
FastAPI Backend Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import chat, research, memory, vectordb, agents
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from agents.orchestrator import OrchestratorAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("aria")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("🚀 ARIA starting up...")

    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)

    # Initialize shared services and attach to app state
    app.state.short_term_memory = ShortTermMemory()
    app.state.long_term_memory  = LongTermMemory()
    app.state.orchestrator      = OrchestratorAgent()
    app.state.agent_logs        = []

    logger.info("✅ All services initialized")
    yield
    logger.info("👋 ARIA shutting down")


app = FastAPI(
    title="ARIA — AI Research Intelligence Assistant",
    description="Multi-agent RAG system with vector DB and memory",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend (any origin in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(chat.router,     prefix="/api/chat",     tags=["Chat"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(memory.router,   prefix="/api/memory",   tags=["Memory"])
app.include_router(vectordb.router, prefix="/api/vectordb", tags=["VectorDB"])
app.include_router(agents.router,   prefix="/api/agents",   tags=["Agents"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ARIA"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
