"""
Menu.AI — Router de Empresas
CRUD completo para gestão de empresas clientes.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Empresa
from database.schemas import EmpresaCreate, EmpresaOut, EmpresaUpdate
from routers.auth_supabase import exigir_role, get_usuario_atual

router = APIRouter(prefix="/api/empresas", tags=["Empresas"])


@router.get("/", response_model=List[EmpresaOut], summary="Listar empresas")
def listar(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    busca: Optional[str] = Query(None, description="Busca por nome ou CNPJ"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin")),
):
    """Lista todas as empresas. Apenas super_admin e admin."""
    q = db.query(Empresa)
    if ativo is not None:
        q = q.filter(Empresa.ativo == ativo)
    if busca:
        like = f"%{busca}%"
        q = q.filter(Empresa.nome.ilike(like) | Empresa.cnpj.ilike(like))
    return q.order_by(Empresa.nome).offset(skip).limit(limit).all()


@router.post("/", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED,
             summary="Criar empresa")
def criar(
    body: EmpresaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin")),
):
    """Cria nova empresa. Apenas super_admin."""
    if body.cnpj and db.query(Empresa).filter(Empresa.cnpj == body.cnpj).first():
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado.")

    empresa = Empresa(**body.model_dump())
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return EmpresaOut.model_validate(empresa)


@router.get("/{empresa_id}", response_model=EmpresaOut, summary="Buscar empresa por ID")
def buscar(
    empresa_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Retorna empresa pelo ID. Usuário só pode ver a própria empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    # Restrição: usuário não-super_admin só acessa a própria empresa
    if usuario.role != "super_admin" and usuario.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    return EmpresaOut.model_validate(empresa)


@router.patch("/{empresa_id}", response_model=EmpresaOut, summary="Atualizar empresa")
def atualizar(
    empresa_id: str,
    body: EmpresaUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin")),
):
    """Atualiza dados da empresa. Admin só pode editar a própria empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    if usuario.role == "admin" and usuario.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    dados = body.model_dump(exclude_unset=True)
    for campo, valor in dados.items():
        setattr(empresa, campo, valor)

    db.commit()
    db.refresh(empresa)
    return EmpresaOut.model_validate(empresa)


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desativar empresa")
def desativar(
    empresa_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin")),
):
    """Desativa empresa (soft delete). Apenas super_admin."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    empresa.ativo = False
    db.commit()
