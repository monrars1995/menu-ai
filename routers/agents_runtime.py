from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from routers.auth_supabase import get_usuario_atual
from services.agent_runtime import DEFAULT_FLOW_KEY, runtime_agents_payload

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("/runtime")
def agents_runtime(
    flow: str = Query(default=DEFAULT_FLOW_KEY),
    db: Session = Depends(get_db),
    _usuario=Depends(get_usuario_atual),
):
    return runtime_agents_payload(db, flow_key=flow).model_dump(mode="json")
