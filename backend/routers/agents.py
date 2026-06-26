"""
Agents Router — /api/agents
Exposes agent logs for the UI.
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/logs")
async def get_logs(request: Request):
    logs = getattr(request.app.state, "agent_logs", [])
    return {"logs": logs}
