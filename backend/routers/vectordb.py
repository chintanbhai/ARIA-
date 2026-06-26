"""
VectorDB Router — /api/vectordb
Exposes vector DB stats, document list, and semantic search.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


@router.get("/stats")
async def get_stats(request: Request):
    orchestrator = request.app.state.orchestrator
    return orchestrator.get_vector_stats()


@router.get("/documents")
async def get_documents(request: Request):
    orchestrator = request.app.state.orchestrator
    return {"documents": orchestrator.get_documents()}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
async def semantic_search(req: SearchRequest, request: Request):
    orchestrator = request.app.state.orchestrator
    results = await orchestrator.semantic_search(req.query, top_k=req.top_k)
    return {"results": results, "query": req.query}
