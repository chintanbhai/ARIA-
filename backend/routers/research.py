"""
Research Router — /api/research
Triggers deep research sessions and retrieves history.
"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("aria.routers.research")
router = APIRouter()


class ResearchRequest(BaseModel):
    topic:      str
    depth:      str = "standard"   # quick | standard | deep
    session_id: Optional[str] = None


@router.post("/start")
async def start_research(req: ResearchRequest, request: Request):
    ltm          = request.app.state.long_term_memory
    orchestrator = request.app.state.orchestrator

    logger.info(f"Research | topic='{req.topic}' | depth={req.depth}")
    result = await orchestrator.run_research(req.topic, req.depth)

    # Store research summary in long-term memory
    urls = [c["url"] for c in result.get("citations", []) if c.get("url")]
    ltm.store_research_summary(req.topic, result["answer"][:400], urls)

    # Add to short-term if session provided
    if req.session_id:
        stm = request.app.state.short_term_memory
        stm.add_message(req.session_id, "user", f"Research: {req.topic}", topic=req.topic)
        stm.add_message(req.session_id, "assistant", result["answer"], topic=req.topic)

    return result


@router.get("/history")
async def get_history(request: Request):
    stm = request.app.state.short_term_memory
    return {"sessions": stm.get_all_sessions()}
