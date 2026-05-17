"""
Menu.AI — Router de Ingredientes
CRUD para insumos com custo real, FC e dados nutricionais.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Ingrediente
from database.schemas import IngredienteCreate, IngredienteOut, IngredienteUpdate
from routers.auth_supabase import exigir_role, get_usuario_atual

router = APIRouter(prefix="/api/ingredientes", tags=["Ingredientes"])


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


@router.get("/", summary="Listar ingredientes")
def listar(
    empresa_id: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    busca: Optional[str] = Query(None, description="Busca por nome"),
    incluir_globais: bool = Query(True, description="Incluir ingredientes globais (empresa_id=None)"),
    ativo: Optional[bool] = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """
    Lista ingredientes da empresa + ingredientes globais compartilhados.
    Ingredientes globais (empresa_id=None) estão disponíveis para todas as empresas.
    """
    q = db.query(Ingrediente)

    eid = _resolve_empresa_context(usuario, empresa_id)
    if incluir_globais:
        q = q.filter(
            (Ingrediente.empresa_id == eid) | (Ingrediente.empresa_id == None)
        )
    else:
        q = q.filter(Ingrediente.empresa_id == eid)

    if categoria:
        q = q.filter(Ingrediente.categoria == categoria.upper())
    if busca:
        q = q.filter(Ingrediente.nome.ilike(f"%{busca}%"))
    if ativo is not None:
        q = q.filter(Ingrediente.ativo == ativo)

    total = q.count()
    items = q.order_by(Ingrediente.nome).offset(skip).limit(limit).all()
    return {
        "items": [IngredienteOut.model_validate(i) for i in items],
        "total": total,
        "page": (skip // limit) + 1 if limit else 1,
        "per_page": limit,
        "pages": math.ceil(total / limit) if limit else 0,
    }


@router.post("/", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED,
             summary="Cadastrar ingrediente")
def criar(
    body: IngredienteCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """Cadastra novo ingrediente. empresa_id=None cria ingrediente global (apenas super_admin)."""
    if body.empresa_id is None and usuario.role != "super_admin":
        raise HTTPException(status_code=403,
                            detail="Apenas super_admin pode criar ingredientes globais.")

    # Garante empresa correta para usuários não-super_admin
    empresa_id = body.empresa_id
    if usuario.role != "super_admin":
        empresa_id = usuario.empresa_id

    ingrediente = Ingrediente(**{**body.model_dump(), "empresa_id": empresa_id})
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return IngredienteOut.model_validate(ingrediente)


@router.get("/{ingrediente_id}", response_model=IngredienteOut, summary="Buscar ingrediente")
def buscar(
    ingrediente_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    ing = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    return IngredienteOut.model_validate(ing)


@router.patch("/{ingrediente_id}", response_model=IngredienteOut, summary="Atualizar ingrediente")
def atualizar(
    ingrediente_id: str,
    body: IngredienteUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """Atualiza ingrediente. Nutricionista só edita os da própria empresa."""
    ing = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")

    if usuario.role != "super_admin" and ing.empresa_id != usuario.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    campos_alterados = set(body.model_dump(exclude_unset=True).keys())
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(ing, campo, valor)

    db.commit()
    db.refresh(ing)

    # Recálculo em cascata: se custo ou FC mudou, recalcula todas as fichas que usam este ingrediente
    campos_custo = {"custo_unitario", "fator_correcao"}
    if campos_custo & campos_alterados:
        from services.cascata import recalcular_fichas_por_ingrediente
        fichas_ids = recalcular_fichas_por_ingrediente(db, ingrediente_id)
        if fichas_ids:
            db.commit()

    return IngredienteOut.model_validate(ing)


@router.delete("/{ingrediente_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desativar ingrediente")
def desativar(
    ingrediente_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin")),
):
    ing = db.query(Ingrediente).filter(Ingrediente.id == ingrediente_id).first()
    if not ing:
        raise HTTPException(status_code=404, detail="Ingrediente não encontrado.")
    ing.ativo = False
    db.commit()


@router.get("/categorias/lista", summary="Listar categorias disponíveis")
def listar_categorias():
    """Retorna as categorias de ingredientes disponíveis."""
    return {
        "categorias": [
            "PROTEINA", "CARBOIDRATO", "HORTALICA", "FRUTA",
            "LATICINIOS", "GORDURA", "CONDIMENTO", "BEBIDA", "OUTRO"
        ]
    }
