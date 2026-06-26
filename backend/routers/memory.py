"""
Memory Router — /api/memory
Exposes short-term and long-term memory for the UI.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/short-term/{session_id}")
async def get_short_term(session_id: str, request: Request):
    stm = request.app.state.short_term_memory
    return stm.get_raw(session_id)


@router.get("/long-term")
async def get_long_term(request: Request):
    ltm = request.app.state.long_term_memory
    return {"memories": ltm.get_all()}


@router.delete("/long-term")
async def clear_long_term(request: Request):
    ltm = request.app.state.long_term_memory
    ltm.clear()
    return {"status": "cleared"}


class MemoryStoreRequest(BaseModel):
    content:     str
    memory_type: Optional[str] = "fact"
    topic:       Optional[str] = ""


@router.post("/long-term")
async def store_memory(req: MemoryStoreRequest, request: Request):
    ltm = request.app.state.long_term_memory
    entry = ltm.store(req.content, req.memory_type, req.topic)
    return entry
