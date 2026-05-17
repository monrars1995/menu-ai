"""
Menu.AI — Router de Fichas Técnicas
CRUD completo com cálculo automático de custos e valores nutricionais.
"""
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import FichaTecnica, FichaIngrediente, Ingrediente
from database.schemas import (
    FichaTecnicaCreate, FichaTecnicaDetalhada, FichaTecnicaOut, FichaTecnicaUpdate,
    FichaIngredienteCreate, FichaIngredienteOut,
)
from routers.auth_supabase import exigir_role, get_usuario_atual
from services.knowledge_base import sync_ficha_document
from services.knowledge_hooks import sync_knowledge_safe

router = APIRouter(prefix="/api/fichas-tecnicas", tags=["Fichas Técnicas"])


# ============================================================
# Funções auxiliares
# ============================================================

def _calcular_ficha(ficha: FichaTecnica, db: Session) -> None:
    """
    Recalcula custo total, custo por porção e valores nutricionais da ficha
    a partir dos ingredientes cadastrados.
    """
    custo_total      = 0.0
    calorias         = 0.0
    proteina         = 0.0
    carboidrato      = 0.0
    gordura          = 0.0
    sodio            = 0.0

    for item in ficha.ingredientes_ficha:
        ing = item.ingrediente
        if not ing:
            continue

        # Fator de correção: usa o do item se definido, senão o do ingrediente
        fc = item.fator_correcao if item.fator_correcao > 1.0 else ing.fator_correcao

        # Quantidade líquida (após FC)
        qtd_liquida = item.quantidade_bruta_g / fc
        item.quantidade_liquida_g = round(qtd_liquida, 4)

        # Custo calculado = (quantidade_bruta / 1000) × custo_unitário
        # Assume unidade_medida=kg; adaptar para outros se necessário
        custo_item = (item.quantidade_bruta_g / 1000.0) * ing.custo_unitario
        item.custo_calculado = round(custo_item, 4)
        custo_total += custo_item

        # Nutrição por porção (qtd_liquida em g, tabela TACO é por 100g)
        fator_nutri = qtd_liquida / 100.0
        if ing.calorias_100g:    calorias    += ing.calorias_100g    * fator_nutri
        if ing.proteina_100g:    proteina    += ing.proteina_100g    * fator_nutri
        if ing.carboidrato_100g: carboidrato += ing.carboidrato_100g * fator_nutri
        if ing.gordura_100g:     gordura     += ing.gordura_100g     * fator_nutri
        if ing.sodio_100g:       sodio       += ing.sodio_100g       * fator_nutri

    porcoes = max(ficha.rendimento_porcoes, 1)
    ficha.custo_total    = round(custo_total, 4)
    ficha.custo_porcao   = round(custo_total / porcoes, 4)

    # Nutrição por porção
    ficha.calorias_porcao     = round(calorias    / porcoes, 2) if calorias    else None
    ficha.proteina_porcao     = round(proteina    / porcoes, 2) if proteina    else None
    ficha.carboidrato_porcao  = round(carboidrato / porcoes, 2) if carboidrato else None
    ficha.gordura_porcao      = round(gordura     / porcoes, 2) if gordura     else None
    ficha.sodio_porcao        = round(sodio       / porcoes, 2) if sodio       else None


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


# ============================================================
# Endpoints
# ============================================================

@router.get("/", summary="Listar fichas técnicas")
def listar(
    empresa_id: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    busca: Optional[str] = Query(None),
    vegana: Optional[bool] = Query(None),
    vegetariana: Optional[bool] = Query(None),
    sem_gluten: Optional[bool] = Query(None),
    custo_max: Optional[float] = Query(None, description="Custo máximo por porção (R$)"),
    ativo: Optional[bool] = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Lista fichas técnicas com filtros avançados."""
    q = db.query(FichaTecnica)

    eid = _resolve_empresa_context(usuario, empresa_id)
    q = q.filter(FichaTecnica.empresa_id == eid)

    if categoria:
        q = q.filter(FichaTecnica.categoria.ilike(f"%{categoria}%"))
    if busca:
        q = q.filter(FichaTecnica.nome.ilike(f"%{busca}%"))
    if vegana is not None:
        q = q.filter(FichaTecnica.vegana == vegana)
    if vegetariana is not None:
        q = q.filter(FichaTecnica.vegetariana == vegetariana)
    if sem_gluten:
        q = q.filter(FichaTecnica.contem_gluten == False)
    if custo_max is not None:
        q = q.filter(FichaTecnica.custo_porcao <= custo_max)
    if ativo is not None:
        q = q.filter(FichaTecnica.ativo == ativo)

    total = q.count()
    items = q.order_by(FichaTecnica.categoria, FichaTecnica.nome).offset(skip).limit(limit).all()
    return {
        "items": [FichaTecnicaOut.model_validate(f) for f in items],
        "total": total,
        "page": (skip // limit) + 1 if limit else 1,
        "per_page": limit,
        "pages": math.ceil(total / limit) if limit else 0,
    }


@router.post("/", response_model=FichaTecnicaDetalhada, status_code=status.HTTP_201_CREATED,
             summary="Criar ficha técnica")
def criar(
    body: FichaTecnicaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """
    Cria nova ficha técnica com lista de ingredientes.
    Calcula automaticamente custos e valores nutricionais.
    """
    empresa_id = body.empresa_id if usuario.role == "super_admin" else usuario.empresa_id

    # Verifica código único por empresa
    if db.query(FichaTecnica).filter(
        FichaTecnica.empresa_id == empresa_id,
        FichaTecnica.codigo == body.codigo
    ).first():
        raise HTTPException(status_code=400, detail=f"Código '{body.codigo}' já existe para esta empresa.")

    # Cria ficha
    dados = body.model_dump(exclude={"ingredientes", "empresa_id"})
    ficha = FichaTecnica(**dados, empresa_id=empresa_id)
    db.add(ficha)
    db.flush()  # gera ID sem commit

    # Adiciona ingredientes
    for i, item in enumerate(body.ingredientes):
        ing = db.query(Ingrediente).filter(Ingrediente.id == item.ingrediente_id).first()
        if not ing:
            raise HTTPException(status_code=404,
                                detail=f"Ingrediente '{item.ingrediente_id}' não encontrado.")

        fi = FichaIngrediente(
            ficha_tecnica_id=ficha.id,
            ingrediente_id=item.ingrediente_id,
            quantidade_bruta_g=item.quantidade_bruta_g,
            fator_correcao=item.fator_correcao,
            ordem=item.ordem if item.ordem else i,
            observacao=item.observacao,
        )
        db.add(fi)

    db.flush()
    db.refresh(ficha)

    # Calcula custos e nutrição
    _calcular_ficha(ficha, db)
    db.commit()
    db.refresh(ficha)
    sync_knowledge_safe(sync_ficha_document, db, ficha)
    db.commit()

    return FichaTecnicaDetalhada.model_validate(ficha)


@router.get("/{ficha_id}", response_model=FichaTecnicaDetalhada, summary="Buscar ficha técnica")
def buscar(
    ficha_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Retorna ficha técnica completa com todos os ingredientes."""
    ficha = db.query(FichaTecnica).filter(FichaTecnica.id == ficha_id).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")

    if usuario.role != "super_admin" and ficha.empresa_id != usuario.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    return FichaTecnicaDetalhada.model_validate(ficha)


@router.patch("/{ficha_id}", response_model=FichaTecnicaDetalhada, summary="Atualizar ficha técnica")
def atualizar(
    ficha_id: str,
    body: FichaTecnicaUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """
    Atualiza ficha técnica. Se `ingredientes` for fornecido,
    substitui toda a lista de ingredientes e recalcula custos.
    """
    ficha = db.query(FichaTecnica).filter(FichaTecnica.id == ficha_id).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")

    if usuario.role != "super_admin" and ficha.empresa_id != usuario.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    dados = body.model_dump(exclude_unset=True, exclude={"ingredientes"})
    for campo, valor in dados.items():
        setattr(ficha, campo, valor)

    # Atualiza ingredientes se fornecidos
    if body.ingredientes is not None:
        # Remove ingredientes anteriores
        db.query(FichaIngrediente).filter(
            FichaIngrediente.ficha_tecnica_id == ficha_id
        ).delete()

        # Adiciona novos
        for i, item in enumerate(body.ingredientes):
            ing = db.query(Ingrediente).filter(Ingrediente.id == item.ingrediente_id).first()
            if not ing:
                raise HTTPException(status_code=404,
                                    detail=f"Ingrediente '{item.ingrediente_id}' não encontrado.")
            fi = FichaIngrediente(
                ficha_tecnica_id=ficha.id,
                ingrediente_id=item.ingrediente_id,
                quantidade_bruta_g=item.quantidade_bruta_g,
                fator_correcao=item.fator_correcao,
                ordem=item.ordem if item.ordem else i,
                observacao=item.observacao,
            )
            db.add(fi)

        db.flush()
        db.refresh(ficha)
        _calcular_ficha(ficha, db)

    db.commit()
    db.refresh(ficha)
    sync_knowledge_safe(sync_ficha_document, db, ficha)
    db.commit()
    return FichaTecnicaDetalhada.model_validate(ficha)


@router.post("/{ficha_id}/recalcular", response_model=FichaTecnicaOut,
             summary="Recalcular custos da ficha")
def recalcular(
    ficha_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    """
    Força o recálculo de custos e nutrição da ficha
    (útil após atualizar preços dos ingredientes).
    """
    ficha = db.query(FichaTecnica).filter(FichaTecnica.id == ficha_id).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")

    _calcular_ficha(ficha, db)
    db.commit()
    db.refresh(ficha)
    sync_knowledge_safe(sync_ficha_document, db, ficha)
    db.commit()
    return FichaTecnicaOut.model_validate(ficha)


@router.post("/recalcular-todas", summary="Recalcular todas as fichas da empresa")
def recalcular_todas(
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin")),
):
    """
    Recalcula custos e nutrição de TODAS as fichas técnicas ativas da empresa.
    Útil após atualização em massa de preços de ingredientes ou importação.
    """
    from services.cascata import recalcular_todas_fichas_empresa

    empresa_id = usuario.empresa_id
    total = recalcular_todas_fichas_empresa(db, empresa_id)
    db.commit()
    return {
        "ok": True,
        "fichas_recalculadas": total,
        "empresa_id": empresa_id,
        "mensagem": f"{total} ficha(s) técnica(s) recalculada(s) com sucesso.",
    }


@router.delete("/{ficha_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Desativar ficha técnica")
def desativar(
    ficha_id: str,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    ficha = db.query(FichaTecnica).filter(FichaTecnica.id == ficha_id).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha técnica não encontrada.")
    ficha.ativo = False
    db.commit()
    db.refresh(ficha)
    sync_knowledge_safe(sync_ficha_document, db, ficha)
    db.commit()


@router.get("/categorias/lista", summary="Categorias de fichas técnicas")
def listar_categorias():
    """Retorna as categorias padrão compatíveis com a base de receitas."""
    return {
        "categorias": [
            "PRATO PROTEICO",
            "GUARNICAO",
            "SALADAS CRUA",
            "SALADA COZIDA",
            "SALADA ELABORADA",
            "ACOMPANHAMENTO",
            "ARROZ",
            "FEIJAO",
            "SOBREMESA",
            "FRUTAS",
        ]
    }


def _parse_gramatura(valor: str) -> Optional[float]:
    """Extrai número em gramas de string como '120g' ou '120'."""
    if not valor:
        return None
    import re
    m = re.match(r"([\d.]+)", str(valor))
    return float(m.group(1)) if m else None


@router.get("/conferencia-gramatura", summary="Conferência de gramatura vs contrato")
def conferir_gramatura(
    contrato_id: str = Query(..., description="ID do contrato com gramaturas extraídas"),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    """Compara peso_porcao_g de cada ficha técnica com a gramatura exigida pelo contrato."""
    from database.models import Contrato

    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    if usuario.role != "super_admin" and usuario.empresa_id != contrato.empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    gramaturas_raw = contrato.gramaturas_json or {}
    if not gramaturas_raw:
        return {"contrato_id": contrato_id, "status": "sem_gramaturas", "itens": [], "mensagem": "Contrato sem gramaturas definidas. Execute a análise do contrato primeiro."}

    # Normalizar gramaturas: categoria → float em gramas
    gramaturas: dict[str, float] = {}
    for cat, val in gramaturas_raw.items():
        g = _parse_gramatura(val)
        if g and g > 0:
            gramaturas[cat.upper()] = g

    if not gramaturas:
        return {"contrato_id": contrato_id, "status": "sem_gramaturas", "itens": [], "mensagem": "Gramaturas do contrato não possuem valores numéricos válidos."}

    fichas = (
        db.query(FichaTecnica)
        .filter(FichaTecnica.empresa_id == contrato.empresa_id, FichaTecnica.ativo == True)
        .all()
    )

    itens = []
    for f in fichas:
        cat_norm = (f.categoria or "").upper()
        gramatura_contrato = gramaturas.get(cat_norm)
        peso_ficha = f.peso_porcao_g

        if gramatura_contrato is None or peso_ficha is None:
            itens.append({
                "ficha_id": f.id,
                "nome": f.nome,
                "categoria": f.categoria,
                "peso_ficha_g": peso_ficha,
                "gramatura_contrato_g": gramatura_contrato,
                "diferenca_g": None,
                "diferenca_pct": None,
                "status": "sem_dado",
            })
            continue

        diff = round(peso_ficha - gramatura_contrato, 1)
        diff_pct = round((diff / gramatura_contrato) * 100, 1) if gramatura_contrato > 0 else None

        if abs(diff_pct or 0) <= 10:
            st = "ok"
        elif diff < 0:
            st = "abaixo"
        else:
            st = "acima"

        itens.append({
            "ficha_id": f.id,
            "nome": f.nome,
            "categoria": f.categoria,
            "peso_ficha_g": peso_ficha,
            "gramatura_contrato_g": gramatura_contrato,
            "diferenca_g": diff,
            "diferenca_pct": diff_pct,
            "status": st,
        })

    ok = sum(1 for i in itens if i["status"] == "ok")
    sem = sum(1 for i in itens if i["status"] == "sem_dado")
    fora = len(itens) - ok - sem

    return {
        "contrato_id": contrato_id,
        "status": "conferido",
        "total": len(itens),
        "conformes": ok,
        "nao_conformes": fora,
        "sem_dado": sem,
        "itens": itens,
    }
