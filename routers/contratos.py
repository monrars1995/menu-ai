"""
Menu.AI — Router de Contratos
Gestão de contratos de fornecimento de refeições por empresa.
"""
import json
import math
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Contrato, Empresa
from database.schemas import ContratoCreate, ContratoOut, ContratoUpdate
from routers.auth_supabase import exigir_role, get_usuario_atual
from services.knowledge_base import sync_contrato_document
from services.knowledge_hooks import sync_knowledge_safe

router = APIRouter(prefix="/api/contratos", tags=["Contratos"])

UPLOAD_DIR = Path("data/uploads/contratos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

    # Restrição por empresa
    if usuario.role != "super_admin":
        q = q.filter(Contrato.empresa_id == usuario.empresa_id)
    elif empresa_id:
        q = q.filter(Contrato.empresa_id == empresa_id)

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
    """Upload do PDF ou XLSX do contrato."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".xlsx", ".xls"):
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

    # 3. Fallback: arquivo global da última análise
    if not regras:
        regras_global = Path("data/uploads/_regras_contrato.json")
        if regras_global.exists():
            try:
                regras = json.loads(regras_global.read_text(encoding="utf-8"))
            except Exception:
                pass

    if not regras:
        return {"contrato_id": contrato_id, "status": "nao_analisado", "mensagem": "Nenhuma análise encontrada. Execute a geração de cardápio para que o agente Analista extraia as regras."}

    return {
        "contrato_id": contrato_id,
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
        "incidencias": regras.get("incidencias", contrato.incidencias_json or []),
        "gramaturas": regras.get("gramaturas", contrato.gramaturas_json or {}),
        "proibicoes": regras.get("proibicoes", contrato.proibicoes_json or []),
        "restricoes_alergenos": regras.get("restricoes_alergenos", []),
        "dietas_especiais": regras.get("dietas_especiais", []),
        "sazonalidade": regras.get("sazonalidade_obrigatoria", []),
    }
