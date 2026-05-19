from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional
import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.models import (
    AgentProfile,
    AgentSlotType,
    AgentVersion,
    AgentVersionStatus,
    FlowAgentBinding,
)
from database.schemas import (
    AgentDraftUpdate,
    AgentProfileCreate,
    AgentProfileOut,
    AgentProfileUpdate,
    AgentVersionOut,
    AgentsRuntimeResponse,
    FlowAgentBindingOut,
    RuntimeAgentOption,
)
from pipeline.llm_providers import get_model_label
from pipeline.openrouter_models import (
    assert_llm_model_allowed_for_generation,
    assert_llm_model_allowed_for_review,
)

logger = logging.getLogger("menuai.agent_runtime")

DEFAULT_FLOW_KEY = "gerar"
CORE_SLOT_TYPES = (
    AgentSlotType.CONTRACT_ANALYZER,
    AgentSlotType.GENERATOR,
    AgentSlotType.REVIEWER,
    AgentSlotType.COPILOT,
)

DEFAULT_SLOT_MODELS = {
    AgentSlotType.CONTRACT_ANALYZER: "openai-gpt-5.5",
    AgentSlotType.GENERATOR: "openai-gpt-5.5",
    AgentSlotType.REVIEWER: "queen-3.6",
    AgentSlotType.COPILOT: "openai-gpt-5.5",
}

DEFAULT_SLOT_NAMES = {
    AgentSlotType.CONTRACT_ANALYZER: "Analista de Contrato Padrão",
    AgentSlotType.GENERATOR: "Gerador de Cardápio Padrão",
    AgentSlotType.REVIEWER: "Revisor de Cardápio Padrão",
    AgentSlotType.COPILOT: "Copiloto Operacional Padrão",
}

DEFAULT_SLOT_SLUGS = {
    AgentSlotType.CONTRACT_ANALYZER: "analista-contrato-padrao",
    AgentSlotType.GENERATOR: "gerador-cardapio-padrao",
    AgentSlotType.REVIEWER: "revisor-cardapio-padrao",
    AgentSlotType.COPILOT: "copiloto-operacional-padrao",
}

DEFAULT_SLOT_PROMPTS = {
    AgentSlotType.CONTRACT_ANALYZER: (
        "Voce e o analista de contratos do Menu.AI. "
        "Extraia regras do documento com fidelidade, sem inventar clausulas ausentes. "
        "Quando faltar dado explicito, registre a lacuna e use boas praticas apenas na menor extensao necessaria."
    ),
    AgentSlotType.GENERATOR: (
        "Voce e nutricionista de refeicoes coletivas. "
        "Retorne apenas estruturas validas para o cardapio. "
        "Use exclusivamente itens existentes no catalogo permitido e respeite as regras contratuais."
    ),
    AgentSlotType.REVIEWER: (
        "Voce e um revisor tecnico de cardapios operacionais. "
        "Revise consistencia estrutural, regras contratuais e repeticoes. "
        "Nunca invente pratos fora do catalogo e so proponha correcoes seguras."
    ),
    AgentSlotType.COPILOT: (
        "Voce e o copiloto operacional do Menu.AI. "
        "Use tools quando houver consulta ou acao objetiva. "
        "Nao invente IDs, nao altere regras contratuais sem tool e peca apenas o minimo necessario."
    ),
}

DEFAULT_ALLOWED_TOOLS = {
    AgentSlotType.CONTRACT_ANALYZER: ["buscar_contratos", "analisar_contrato"],
    AgentSlotType.GENERATOR: [
        "buscar_ingredientes",
        "buscar_fichas",
        "buscar_contratos",
        "listar_cardapios",
        "ver_cardapio",
        "gerar_novamente_cardapio",
    ],
    AgentSlotType.REVIEWER: ["ver_cardapio", "listar_cardapios"],
    AgentSlotType.COPILOT: [
        "buscar_ingredientes",
        "criar_ingrediente",
        "editar_ingrediente",
        "buscar_fichas",
        "criar_ficha",
        "editar_ficha",
        "buscar_contratos",
        "analisar_contrato",
        "listar_cardapios",
        "ver_cardapio",
        "aprovar_cardapio",
        "gerar_novamente_cardapio",
        "exportar_cardapio",
    ],
}


@dataclass
class ResolvedAgent:
    profile: AgentProfile
    version: AgentVersion
    allowed_tools: list[str]


def resolved_agent_payload(agent: ResolvedAgent) -> dict[str, object]:
    return {
        "profile_id": str(agent.profile.id),
        "profile_name": agent.profile.name,
        "profile_slug": agent.profile.slug,
        "slot_type": agent.profile.slot_type,
        "version_id": str(agent.version.id),
        "version_number": int(agent.version.version_number or 0),
        "provider_model_id": str(agent.version.provider_model_id),
        "system_prompt": str(agent.version.system_prompt or ""),
        "allowed_tools": list(agent.allowed_tools),
    }


def _available_tool_names() -> set[str]:
    from services.copilot_tools import TOOLS

    return set(TOOLS.keys())


def list_available_tool_names() -> list[str]:
    return sorted(_available_tool_names())


def normalize_allowed_tools(slot_type: str, allowed_tools: Optional[Iterable[str]]) -> list[str]:
    tool_names = _available_tool_names()
    values = [
        str(item).strip()
        for item in (allowed_tools or DEFAULT_ALLOWED_TOOLS.get(slot_type, []))
        if str(item).strip()
    ]
    invalid = sorted({item for item in values if item not in tool_names})
    if invalid:
        raise HTTPException(400, detail=f"Tools invalidas para o agente: {', '.join(invalid)}")
    deduped: list[str] = []
    for item in values:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _assert_model_for_slot(db: Session, slot_type: str, provider_model_id: str) -> None:
    if slot_type == AgentSlotType.REVIEWER:
        assert_llm_model_allowed_for_review(db, provider_model_id)
    else:
        assert_llm_model_allowed_for_generation(db, provider_model_id)


def _profile_to_out(profile: AgentProfile) -> AgentProfileOut:
    draft = None
    published: list[AgentVersionOut] = []
    for version in profile.versions or []:
        data = AgentVersionOut(
            id=str(version.id),
            profile_id=str(version.profile_id),
            version_number=int(version.version_number or 0),
            status=str(version.status),
            provider_model_id=str(version.provider_model_id),
            system_prompt=str(version.system_prompt or ""),
            allowed_tools=list(version.allowed_tools_json or []),
            enabled=bool(version.enabled),
            publish_notes=version.publish_notes,
            created_at=version.created_at,
            updated_at=version.updated_at,
            published_at=version.published_at,
        )
        if version.status == AgentVersionStatus.DRAFT:
            draft = data
        elif version.status == AgentVersionStatus.PUBLISHED:
            published.append(data)
    published.sort(key=lambda item: (item.version_number, item.created_at), reverse=True)
    return AgentProfileOut(
        id=str(profile.id),
        name=profile.name,
        slug=profile.slug,
        description=profile.description,
        slot_type=profile.slot_type,
        enabled=bool(profile.enabled),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        draft_version=draft,
        published_versions=published,
        active_published_version=published[0] if published else None,
    )


def _binding_to_out(binding: FlowAgentBinding) -> FlowAgentBindingOut:
    version = binding.version
    profile = binding.profile or (version.profile if version else None)
    return FlowAgentBindingOut(
        id=str(binding.id),
        flow_key=str(binding.flow_key),
        slot_type=str(binding.slot_type),
        enabled=bool(binding.enabled),
        profile_id=str(profile.id) if profile else None,
        version_id=str(version.id) if version else None,
        profile_name=profile.name if profile else None,
        version_number=int(version.version_number) if version else None,
        updated_at=binding.updated_at,
    )


def _runtime_option_from_version(profile: AgentProfile, version: AgentVersion) -> RuntimeAgentOption:
    return RuntimeAgentOption(
        profile_id=str(profile.id),
        version_id=str(version.id),
        slot_type=str(profile.slot_type),
        name=profile.name,
        slug=profile.slug,
        description=profile.description,
        provider_model_id=str(version.provider_model_id),
        provider_label=get_model_label(version.provider_model_id),
        enabled=bool(profile.enabled and version.enabled),
        allowed_tools=list(version.allowed_tools_json or []),
        version_number=int(version.version_number or 0),
        published_at=version.published_at,
    )


def _latest_published_version(profile: AgentProfile) -> Optional[AgentVersion]:
    published = [version for version in (profile.versions or []) if version.status == AgentVersionStatus.PUBLISHED]
    if not published:
        return None
    published.sort(key=lambda item: (item.version_number or 0, item.published_at or item.created_at), reverse=True)
    return published[0]


def _current_draft(profile: AgentProfile) -> Optional[AgentVersion]:
    drafts = [version for version in (profile.versions or []) if version.status == AgentVersionStatus.DRAFT]
    drafts.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
    return drafts[0] if drafts else None


def ensure_core_agents_bootstrapped(db: Session) -> None:
    for slot_type in CORE_SLOT_TYPES:
        profile = (
            db.query(AgentProfile)
            .filter(AgentProfile.slot_type == slot_type, AgentProfile.slug == DEFAULT_SLOT_SLUGS[slot_type])
            .first()
        )
        if profile:
            if not _current_draft(profile):
                draft = AgentVersion(
                    profile_id=profile.id,
                    version_number=0,
                    status=AgentVersionStatus.DRAFT,
                    provider_model_id=DEFAULT_SLOT_MODELS[slot_type],
                    system_prompt=DEFAULT_SLOT_PROMPTS[slot_type],
                    allowed_tools_json=DEFAULT_ALLOWED_TOOLS[slot_type],
                    enabled=True,
                )
                db.add(draft)
            published = _latest_published_version(profile)
            if not published:
                published = AgentVersion(
                    profile_id=profile.id,
                    version_number=1,
                    status=AgentVersionStatus.PUBLISHED,
                    provider_model_id=DEFAULT_SLOT_MODELS[slot_type],
                    system_prompt=DEFAULT_SLOT_PROMPTS[slot_type],
                    allowed_tools_json=DEFAULT_ALLOWED_TOOLS[slot_type],
                    enabled=True,
                    publish_notes="Bootstrap inicial do sistema.",
                    published_at=datetime.utcnow(),
                )
                db.add(published)
                db.flush()
            binding = (
                db.query(FlowAgentBinding)
                .filter(FlowAgentBinding.flow_key == DEFAULT_FLOW_KEY, FlowAgentBinding.slot_type == slot_type)
                .first()
            )
            if not binding:
                db.add(
                    FlowAgentBinding(
                        flow_key=DEFAULT_FLOW_KEY,
                        slot_type=slot_type,
                        profile_id=profile.id,
                        version_id=published.id,
                        enabled=True,
                    )
                )
            continue

        profile = AgentProfile(
            name=DEFAULT_SLOT_NAMES[slot_type],
            slug=DEFAULT_SLOT_SLUGS[slot_type],
            description=f"Agente padrao do slot {slot_type}.",
            slot_type=slot_type,
            enabled=True,
        )
        db.add(profile)
        db.flush()
        draft = AgentVersion(
            profile_id=profile.id,
            version_number=0,
            status=AgentVersionStatus.DRAFT,
            provider_model_id=DEFAULT_SLOT_MODELS[slot_type],
            system_prompt=DEFAULT_SLOT_PROMPTS[slot_type],
            allowed_tools_json=DEFAULT_ALLOWED_TOOLS[slot_type],
            enabled=True,
        )
        db.add(draft)
        db.flush()
        published = AgentVersion(
            profile_id=profile.id,
            version_number=1,
            status=AgentVersionStatus.PUBLISHED,
            provider_model_id=DEFAULT_SLOT_MODELS[slot_type],
            system_prompt=DEFAULT_SLOT_PROMPTS[slot_type],
            allowed_tools_json=DEFAULT_ALLOWED_TOOLS[slot_type],
            enabled=True,
            publish_notes="Bootstrap inicial do sistema.",
            published_at=datetime.utcnow(),
        )
        db.add(published)
        db.flush()
        db.add(
            FlowAgentBinding(
                flow_key=DEFAULT_FLOW_KEY,
                slot_type=slot_type,
                profile_id=profile.id,
                version_id=published.id,
                enabled=True,
            )
        )
    db.commit()


def list_agent_profiles(db: Session, slot_type: Optional[str] = None) -> list[AgentProfileOut]:
    ensure_core_agents_bootstrapped(db)
    query = db.query(AgentProfile)
    if slot_type:
        query = query.filter(AgentProfile.slot_type == slot_type)
    profiles = query.order_by(AgentProfile.slot_type.asc(), AgentProfile.name.asc()).all()
    return [_profile_to_out(profile) for profile in profiles]


def list_flow_bindings(db: Session, flow_key: str = DEFAULT_FLOW_KEY) -> list[FlowAgentBindingOut]:
    ensure_core_agents_bootstrapped(db)
    rows = (
        db.query(FlowAgentBinding)
        .filter(FlowAgentBinding.flow_key == flow_key)
        .order_by(FlowAgentBinding.slot_type.asc())
        .all()
    )
    return [_binding_to_out(row) for row in rows]


def create_agent_profile(db: Session, body: AgentProfileCreate) -> AgentProfileOut:
    ensure_core_agents_bootstrapped(db)
    if db.query(AgentProfile).filter(AgentProfile.slug == body.slug).first():
        raise HTTPException(409, detail=f"Slug ja existe: {body.slug}")
    _assert_model_for_slot(db, body.slot_type, body.provider_model_id)
    profile = AgentProfile(
        name=body.name.strip(),
        slug=body.slug.strip(),
        description=body.description,
        slot_type=body.slot_type,
        enabled=body.enabled,
    )
    db.add(profile)
    db.flush()
    draft = AgentVersion(
        profile_id=profile.id,
        version_number=0,
        status=AgentVersionStatus.DRAFT,
        provider_model_id=body.provider_model_id,
        system_prompt=body.system_prompt.strip(),
        allowed_tools_json=normalize_allowed_tools(body.slot_type, body.allowed_tools),
        enabled=body.enabled,
        publish_notes=body.publish_notes,
    )
    db.add(draft)
    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


def update_agent_profile(db: Session, profile_id: str, body: AgentProfileUpdate) -> AgentProfileOut:
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, detail="Agent profile nao encontrado.")
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] != profile.slug:
        exists = db.query(AgentProfile).filter(AgentProfile.slug == data["slug"], AgentProfile.id != profile_id).first()
        if exists:
            raise HTTPException(409, detail=f"Slug ja existe: {data['slug']}")
    for key, value in data.items():
        setattr(profile, key, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


def update_agent_draft(db: Session, profile_id: str, body: AgentDraftUpdate) -> AgentProfileOut:
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, detail="Agent profile nao encontrado.")
    draft = _current_draft(profile)
    if not draft:
        draft = AgentVersion(
            profile_id=profile.id,
            version_number=0,
            status=AgentVersionStatus.DRAFT,
            provider_model_id=DEFAULT_SLOT_MODELS[profile.slot_type],
            system_prompt=DEFAULT_SLOT_PROMPTS[profile.slot_type],
            allowed_tools_json=DEFAULT_ALLOWED_TOOLS[profile.slot_type],
            enabled=True,
        )
        db.add(draft)
        db.flush()
    data = body.model_dump(exclude_unset=True)
    provider_model_id = data.get("provider_model_id", draft.provider_model_id)
    _assert_model_for_slot(db, profile.slot_type, provider_model_id)
    if "provider_model_id" in data:
        draft.provider_model_id = provider_model_id
    if "system_prompt" in data and data["system_prompt"] is not None:
        draft.system_prompt = data["system_prompt"].strip()
    if "allowed_tools" in data and data["allowed_tools"] is not None:
        draft.allowed_tools_json = normalize_allowed_tools(profile.slot_type, data["allowed_tools"])
    if "enabled" in data and data["enabled"] is not None:
        draft.enabled = bool(data["enabled"])
    if "publish_notes" in data:
        draft.publish_notes = data["publish_notes"]
    draft.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


def publish_agent_profile(db: Session, profile_id: str, publish_notes: Optional[str] = None) -> AgentProfileOut:
    profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, detail="Agent profile nao encontrado.")
    draft = _current_draft(profile)
    if not draft:
        raise HTTPException(400, detail="Nao existe draft para publicar.")
    _assert_model_for_slot(db, profile.slot_type, draft.provider_model_id)
    latest = _latest_published_version(profile)
    next_version_number = int(latest.version_number if latest else 0) + 1
    published = AgentVersion(
        profile_id=profile.id,
        version_number=next_version_number,
        status=AgentVersionStatus.PUBLISHED,
        provider_model_id=draft.provider_model_id,
        system_prompt=draft.system_prompt,
        allowed_tools_json=normalize_allowed_tools(profile.slot_type, draft.allowed_tools_json),
        enabled=bool(draft.enabled and profile.enabled),
        publish_notes=(publish_notes if publish_notes is not None else draft.publish_notes),
        published_at=datetime.utcnow(),
    )
    db.add(published)
    db.flush()
    binding = (
        db.query(FlowAgentBinding)
        .filter(FlowAgentBinding.flow_key == DEFAULT_FLOW_KEY, FlowAgentBinding.slot_type == profile.slot_type)
        .first()
    )
    if not binding:
        binding = FlowAgentBinding(
            flow_key=DEFAULT_FLOW_KEY,
            slot_type=profile.slot_type,
            profile_id=profile.id,
            version_id=published.id,
            enabled=True,
        )
        db.add(binding)
    elif binding.profile_id == profile.id or binding.version_id is None:
        binding.profile_id = profile.id
        binding.version_id = published.id
        binding.enabled = True
        binding.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


def set_flow_binding(
    db: Session,
    slot_type: str,
    *,
    flow_key: str = DEFAULT_FLOW_KEY,
    profile_id: Optional[str] = None,
    version_id: Optional[str] = None,
    enabled: bool = True,
) -> FlowAgentBindingOut:
    ensure_core_agents_bootstrapped(db)
    binding = (
        db.query(FlowAgentBinding)
        .filter(FlowAgentBinding.flow_key == flow_key, FlowAgentBinding.slot_type == slot_type)
        .first()
    )
    profile: Optional[AgentProfile] = None
    version: Optional[AgentVersion] = None
    if version_id:
        version = db.query(AgentVersion).filter(AgentVersion.id == version_id).first()
        if not version or version.status != AgentVersionStatus.PUBLISHED:
            raise HTTPException(400, detail="Version_id deve apontar para uma versao publicada.")
        profile = version.profile
    elif profile_id:
        profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(404, detail="Agent profile nao encontrado.")
        version = _latest_published_version(profile)
        if not version:
            raise HTTPException(400, detail="Profile sem versao publicada para bind.")
    if profile and profile.slot_type != slot_type:
        raise HTTPException(400, detail="O slot do agente nao corresponde ao slot do binding.")
    if version:
        _assert_model_for_slot(db, slot_type, version.provider_model_id)

    if not binding:
        binding = FlowAgentBinding(
            flow_key=flow_key,
            slot_type=slot_type,
            profile_id=profile.id if profile else None,
            version_id=version.id if version else None,
            enabled=enabled,
        )
        db.add(binding)
    else:
        binding.profile_id = profile.id if profile else None
        binding.version_id = version.id if version else None
        binding.enabled = enabled
        binding.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(binding)
    return _binding_to_out(binding)


def resolve_agent_for_slot(
    db: Session,
    slot_type: str,
    *,
    flow_key: str = DEFAULT_FLOW_KEY,
    profile_id: Optional[str] = None,
) -> ResolvedAgent:
    ensure_core_agents_bootstrapped(db)
    profile: Optional[AgentProfile] = None
    version: Optional[AgentVersion] = None

    if profile_id:
        profile = db.query(AgentProfile).filter(AgentProfile.id == profile_id).first()
        if not profile:
            raise HTTPException(404, detail="Agente selecionado nao encontrado.")
        if not profile.enabled:
            raise HTTPException(400, detail="Agente selecionado esta desativado.")
        if profile.slot_type != slot_type:
            raise HTTPException(400, detail="Agente selecionado nao pertence ao slot esperado.")
        version = _latest_published_version(profile)
        if not version or not version.enabled:
            raise HTTPException(400, detail="Agente selecionado nao possui versao publicada ativa.")
    else:
        binding = (
            db.query(FlowAgentBinding)
            .filter(
                FlowAgentBinding.flow_key == flow_key,
                FlowAgentBinding.slot_type == slot_type,
                FlowAgentBinding.enabled == True,  # noqa: E712
            )
            .first()
        )
        if binding and binding.version and binding.profile and binding.profile.enabled and binding.version.enabled:
            profile = binding.profile
            version = binding.version
        else:
            fallback_profile = (
                db.query(AgentProfile)
                .filter(AgentProfile.slot_type == slot_type, AgentProfile.enabled == True)  # noqa: E712
                .order_by(AgentProfile.updated_at.desc(), AgentProfile.created_at.desc())
                .first()
            )
            if fallback_profile:
                candidate_version = _latest_published_version(fallback_profile)
                if candidate_version and candidate_version.enabled:
                    profile = fallback_profile
                    version = candidate_version

    if not profile or not version:
        raise HTTPException(400, detail=f"Nao existe agente publicado ativo para o slot {slot_type}.")
    _assert_model_for_slot(db, slot_type, version.provider_model_id)
    return ResolvedAgent(
        profile=profile,
        version=version,
        allowed_tools=normalize_allowed_tools(slot_type, version.allowed_tools_json),
    )


def runtime_agents_payload(db: Session, flow_key: str = DEFAULT_FLOW_KEY) -> AgentsRuntimeResponse:
    ensure_core_agents_bootstrapped(db)
    profiles = db.query(AgentProfile).filter(AgentProfile.enabled == True).order_by(AgentProfile.name.asc()).all()  # noqa: E712
    generator_agents: list[RuntimeAgentOption] = []
    reviewer_agents: list[RuntimeAgentOption] = []
    for profile in profiles:
        latest = _latest_published_version(profile)
        if not latest or not latest.enabled:
            continue
        try:
            _assert_model_for_slot(db, profile.slot_type, latest.provider_model_id)
        except HTTPException:
            continue
        option = _runtime_option_from_version(profile, latest)
        if profile.slot_type == AgentSlotType.GENERATOR:
            generator_agents.append(option)
        elif profile.slot_type == AgentSlotType.REVIEWER:
            reviewer_agents.append(option)

    contract_binding = resolve_agent_for_slot(db, AgentSlotType.CONTRACT_ANALYZER, flow_key=flow_key)
    copilot_binding = resolve_agent_for_slot(db, AgentSlotType.COPILOT, flow_key=flow_key)
    return AgentsRuntimeResponse(
        flow_key=flow_key,
        generator_agents=generator_agents,
        reviewer_agents=reviewer_agents,
        contract_analyzer_binding=_runtime_option_from_version(contract_binding.profile, contract_binding.version),
        copilot_binding=_runtime_option_from_version(copilot_binding.profile, copilot_binding.version),
    )
