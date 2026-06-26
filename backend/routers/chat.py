"""
Chat Router — POST /api/chat
Handles single-turn and multi-turn chat with full agent pipeline.
"""

import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger("aria.routers.chat")
router = APIRouter()


class ChatRequest(BaseModel):
    message:        str
    session_id:     str
    use_web_search: bool = True
    use_rag:        bool = True


@router.post("")
async def chat(req: ChatRequest, request: Request):
    stm          = request.app.state.short_term_memory
    ltm          = request.app.state.long_term_memory
    orchestrator = request.app.state.orchestrator

    # Add user message to short-term memory
    stm.add_message(req.session_id, "user", req.message)

    # Get conversation history (for multi-turn context)
    history = stm.get_messages(req.session_id)
    # Exclude the very last user message (we pass it as query)
    history_ctx = history[:-1] if history else []

    # Get relevant long-term memory
    long_term_ctx = ltm.get_relevant_context(req.message)

    logger.info(f"Chat | session={req.session_id[:8]} | web={req.use_web_search} | rag={req.use_rag}")

    result = await orchestrator.run_chat(
        query=req.message,
        session_id=req.session_id,
        history=history_ctx,
        long_term_ctx=long_term_ctx,
        use_web_search=req.use_web_search,
        use_rag=req.use_rag,
    )

    # Add assistant answer to memory
    stm.add_message(req.session_id, "assistant", result["answer"])

    # Auto-store a long-term memory fact if answer is substantive
    if len(result["answer"]) > 200:
        ltm.store(
            content=result["answer"][:300],
            memory_type="fact",
            topic=req.message[:80],
        )

    return result
