from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.schemas import (
    AgentDraftUpdate,
    AgentProfileCreate,
    AgentProfileUpdate,
    AgentPublishRequest,
    FlowAgentBindingUpdate,
)
from routers.auth import exigir_role
from services.agent_runtime import (
    DEFAULT_FLOW_KEY,
    create_agent_profile,
    list_available_tool_names,
    list_agent_profiles,
    list_flow_bindings,
    publish_agent_profile,
    set_flow_binding,
    update_agent_draft,
    update_agent_profile,
)

router = APIRouter(prefix="/api/admin/agents", tags=["Admin - Agents"])


@router.get("/meta")
def agent_meta(
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return {
        "flow_key": DEFAULT_FLOW_KEY,
        "slot_types": ["contract_analyzer", "generator", "reviewer", "copilot"],
        "tool_names": list_available_tool_names(),
    }


@router.get("/profiles")
def listar_profiles(
    slot_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return {"items": [item.model_dump(mode="json") for item in list_agent_profiles(db, slot_type=slot_type)]}


@router.post("/profiles")
def criar_profile(
    body: AgentProfileCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return create_agent_profile(db, body).model_dump(mode="json")


@router.patch("/profiles/{profile_id}")
def atualizar_profile(
    profile_id: str,
    body: AgentProfileUpdate,
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return update_agent_profile(db, profile_id, body).model_dump(mode="json")


@router.patch("/profiles/{profile_id}/draft")
def atualizar_draft(
    profile_id: str,
    body: AgentDraftUpdate,
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return update_agent_draft(db, profile_id, body).model_dump(mode="json")


@router.post("/profiles/{profile_id}/publish")
def publicar_profile(
    profile_id: str,
    body: AgentPublishRequest,
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return publish_agent_profile(db, profile_id, body.publish_notes).model_dump(mode="json")


@router.get("/bindings")
def listar_bindings(
    flow_key: str = Query(default=DEFAULT_FLOW_KEY),
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return {"items": [item.model_dump(mode="json") for item in list_flow_bindings(db, flow_key=flow_key)]}


@router.put("/bindings/{slot_type}")
def atualizar_binding(
    slot_type: str,
    body: FlowAgentBindingUpdate,
    flow_key: str = Query(default=DEFAULT_FLOW_KEY),
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return set_flow_binding(
        db,
        slot_type,
        flow_key=flow_key,
        profile_id=body.profile_id,
        version_id=body.version_id,
        enabled=body.enabled,
    ).model_dump(mode="json")
