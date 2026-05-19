"""
Menu.AI — Router de Contratos
Gestão de contratos de fornecimento de refeições por empresa.
"""
import json
import math
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Contrato, Empresa
from database.schemas import ContratoCreate, ContratoOut, ContratoUpdate
from routers.auth_supabase import exigir_role, get_usuario_atual
from services.contract_parser import (
    SUPPORTED_CONTRACT_EXTENSIONS,
    analysis_looks_invalid,
    build_contract_extraction_error,
    extract_contract_text,
)
from services.knowledge_base import sync_contrato_document
from services.knowledge_hooks import sync_knowledge_safe

router = APIRouter(prefix="/api/contratos", tags=["Contratos"])

UPLOAD_DIR = Path("data/uploads/contratos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ContratoAnalyzeRequest(BaseModel):
    llm_model: Optional[str] = None
    force: bool = False


def _resolve_empresa_context(usuario, empresa_id: Optional[str]) -> str:
    requested = str(empresa_id).strip() if empresa_id else None
    user_empresa = str(usuario.empresa_id).strip() if getattr(usuario, "empresa_id", None) else None

    if usuario.role == "super_admin":
        resolved = requested or user_empresa
        if not resolved:
            raise HTTPException(
                status_code=400,
                detail="Super admin sem empresa no contexto. Informe empresa_id.",
            )
        return resolved

    if requested and requested != user_empresa:
        raise HTTPException(status_code=403, detail="empresa_id não corresponde ao utilizador autenticado.")
    if not user_empresa:
        raise HTTPException(status_code=400, detail="Utilizador sem empresa associada.")
    return user_empresa


def _contrato_analise_payload(contrato: Contrato, regras: dict) -> dict:
    return {
        "contrato_id": contrato.id,
        "status": "analisado",
        "nome_contrato": contrato.nome,
        "numero_contrato": contrato.numero_contrato,
        "necessidades": {
            "estrutura_refeicao": contrato.estrutura_refeicao,
            "num_refeicoes_dia": contrato.num_refeicoes_dia,
            "observacoes": regras.get("observacoes", contrato.observacoes),
        },
        "servicos": {
            "num_refeicoes_dia": contrato.num_refeicoes_dia,
            "estrutura": regras.get("estrutura", contrato.estrutura_refeicao),
        },
        "incidencias": regras.get("incidencias", contrato.incidencias_json or {}),
        "gramaturas": regras.get("gramaturas", contrato.gramaturas_json or {}),
        "proibicoes": regras.get("proibicoes", contrato.proibicoes_json or []),
        "restricoes_alergenos": regras.get("restricoes_alergenos", []),
        "dietas_especiais": regras.get("dietas_especiais", []),
        "sazonalidade": regras.get("sazonalidade_obrigatoria", []),
    }


@router.get("/", summary="Listar contratos")
def listar(
    empresa_id: Optional[str] = Query(None),
    ativo: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Lista contratos. Usuário só vê contratos da própria empresa (exceto super_admin)."""
    q = db.query(Contrato)

    eid = _resolve_empresa_context(usuario, empresa_id)
    q = q.filter(Contrato.empresa_id == eid)

    if ativo is not None:
        q = q.filter(Contrato.ativo == ativo)

    total = q.count()
    items = q.order_by(Contrato.nome).offset(skip).limit(limit).all()
    return {
        "items": [ContratoOut.model_validate(c) for c in items],
        "total": total,
        "page": (skip // limit) + 1 if limit else 1,
        "per_page": limit,
        "pages": math.ceil(total / limit) if limit else 0,
    }


@router.post("/", response_model=ContratoOut, status_code=status.HTTP_201_CREATED,
             summary="Criar contrato")
def criar(
    body: ContratoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """Cria novo contrato para uma empresa."""
    # Verifica empresa
    empresa = db.query(Empresa).filter(Empresa.id == body.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    # Restrição: admin/nutricionista só criam para a própria empresa
    if usuario.role not in ("super_admin",) and usuario.empresa_id != body.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    contrato = Contrato(**body.model_dump())
    db.add(contrato)
    db.commit()
    db.refresh(contrato)
    sync_knowledge_safe(sync_contrato_document, db, contrato)
    db.commit()
    return ContratoOut.model_validate(contrato)


@router.get("/{contrato_id}", response_model=ContratoOut, summary="Buscar contrato por ID")
def buscar(
    contrato_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    if usuario.role != "super_admin" and usuario.empresa_id != contrato.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    return ContratoOut.model_validate(contrato)


@router.patch("/{contrato_id}", response_model=ContratoOut, summary="Atualizar contrato")
def atualizar(
    contrato_id: str,
    body: ContratoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    if usuario.role != "super_admin" and usuario.empresa_id != contrato.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(contrato, campo, valor)

    db.commit()
    db.refresh(contrato)
    sync_knowledge_safe(sync_contrato_document, db, contrato)
    db.commit()
    return ContratoOut.model_validate(contrato)


@router.post("/{contrato_id}/upload", summary="Fazer upload do arquivo do contrato")
async def upload_arquivo(
    contrato_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """Upload do documento contratual (PDF/XLSX/DOCX/TXT/MD/RTF)."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_CONTRACT_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato '{ext}' não suportado.")

    content = await file.read()
    dest = UPLOAD_DIR / f"{contrato_id}{ext}"
    dest.write_bytes(content)

    # Salva referência no banco
    contrato.arquivo_path = str(dest)
    db.commit()
    db.refresh(contrato)
    sync_knowledge_safe(sync_contrato_document, db, contrato)
    db.commit()

    return {
        "success": True,
        "arquivo_path": str(dest),
        "tamanho_kb": round(len(content) / 1024, 1),
    }


@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desativar contrato")
def desativar(
    contrato_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin")),
):
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    contrato.ativo = False
    db.commit()
    db.refresh(contrato)
    sync_knowledge_safe(sync_contrato_document, db, contrato)
    db.commit()


@router.get("/{contrato_id}/analise", summary="Análise extraída do contrato")
def obter_analise(
    contrato_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Retorna as regras extraídas pelo agente Analista de Contratos."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    if usuario.role != "super_admin" and usuario.empresa_id != contrato.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    # 1. Regras persistidas no DB
    regras = contrato.regras_json

    # 2. Fallback: arquivo por contrato
    if not regras:
        regras_path = UPLOAD_DIR / f"{contrato_id}_regras.json"
        if regras_path.exists():
            try:
                regras = json.loads(regras_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    if not regras or analysis_looks_invalid(regras):
        return {"contrato_id": contrato_id, "status": "nao_analisado", "mensagem": "Nenhuma análise encontrada. Execute a geração de cardápio para que o agente Analista extraia as regras."}

    return _contrato_analise_payload(contrato, regras)


@router.post("/{contrato_id}/analisar", summary="Executar análise do contrato")
def analisar_contrato(
    contrato_id: str,
    body: ContratoAnalyzeRequest = Body(default_factory=ContratoAnalyzeRequest),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Executa o Analista de Contratos, persiste regras extraídas e retorna o resumo estruturado."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    if usuario.role != "super_admin" and usuario.empresa_id != contrato.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    if not contrato.arquivo_path:
        raise HTTPException(status_code=400, detail="Contrato sem arquivo carregado.")
    extraction = extract_contract_text(contrato.arquivo_path)
    if not extraction.ok or extraction.total_chars < 300:
        raise HTTPException(status_code=422, detail=build_contract_extraction_error(extraction))

    if contrato.regras_json and not body.force and not analysis_looks_invalid(contrato.regras_json):
        return _contrato_analise_payload(contrato, contrato.regras_json)

    resolved_analyzer_agent = None
    effective_llm_model = body.llm_model
    step_system_overrides = None

    try:
        from database.models import AgentSlotType
        from services.agent_runtime import resolve_agent_for_slot

        resolved_analyzer_agent = resolve_agent_for_slot(db, AgentSlotType.CONTRACT_ANALYZER)
        effective_llm_model = body.llm_model or resolved_analyzer_agent.version.provider_model_id
        if resolved_analyzer_agent.version.system_prompt:
            step_system_overrides = {0: resolved_analyzer_agent.version.system_prompt}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        from pipeline.orchestrator import MenuOrchestrator

        crew = MenuOrchestrator(
            contrato_path=contrato.arquivo_path,
            dias=30,
            target_custo_total=contrato.custo_total_max or 10.00,
            target_custo_proteico=contrato.custo_proteico_max or 3.50,
            restricoes_usuario="",
            refeicoes=None,
            empresa_id=str(contrato.empresa_id),
            contrato_id=str(contrato.id),
            db_disponivel=True,
            llm_model_id=effective_llm_model,
            step_system_overrides=step_system_overrides,
        )
        regras = crew.analisar_contrato_apenas()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao analisar contrato: {exc}")

    if not isinstance(regras, dict):
        regras = {"texto": str(regras)}
    if regras.get("erro"):
        raise HTTPException(status_code=502, detail=f"Falha ao analisar contrato: {regras.get('erro')}")
    if analysis_looks_invalid(regras):
        raise HTTPException(
            status_code=422,
            detail=(
                "A análise retornou conteúdo sem base documental. "
                "Reenvie o arquivo e execute a análise novamente."
            ),
        )

    contrato.regras_json = regras
    contrato.gramaturas_json = regras.get("gramaturas", contrato.gramaturas_json)
    contrato.incidencias_json = regras.get("incidencias", contrato.incidencias_json)
    contrato.proibicoes_json = regras.get("proibicoes", contrato.proibicoes_json)
    contrato.estrutura_refeicao = regras.get("estrutura", contrato.estrutura_refeicao)
    contrato.observacoes = regras.get("observacoes", contrato.observacoes)
    db.commit()
    db.refresh(contrato)
    sync_knowledge_safe(sync_contrato_document, db, contrato)
    db.commit()

    return _contrato_analise_payload(contrato, regras)
