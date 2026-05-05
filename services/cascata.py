"""
Menu.AI — Recálculo em Cascata

Quando o custo ou FC de um Ingrediente muda, todas as FichaTecnica
que usam esse ingrediente precisam ter seus custos e valores
nutricionais recalculados automaticamente.

Fluxo:
  Ingrediente atualizado
    → busca FichaIngrediente.ingrediente_id
      → para cada ficha: recalcula custo_calculado de cada item
        → recalcula custo_total / custo_porcao / nutrição da ficha
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import FichaIngrediente, FichaTecnica, Ingrediente

logger = logging.getLogger("menuai.cascata")


def _recalcular_item(item: FichaIngrediente, ingrediente: Ingrediente) -> None:
    """Recalcula custo e quantidade líquida de um FichaIngrediente."""
    # Fator de correção: usa o do item se > 1.0, senão o do ingrediente
    fc = item.fator_correcao if item.fator_correcao > 1.0 else ingrediente.fator_correcao

    # Quantidade líquida (após FC)
    qtd_liquida = item.quantidade_bruta_g / fc
    item.quantidade_liquida_g = round(qtd_liquida, 4)

    # Custo calculado = (quantidade_bruta / 1000) × custo_unitário
    custo_item = (item.quantidade_bruta_g / 1000.0) * ingrediente.custo_unitario
    item.custo_calculado = round(custo_item, 4)


def _recalcular_ficha_totais(ficha: FichaTecnica) -> None:
    """Recalcula totais da ficha a partir dos itens já atualizados."""
    custo_total = 0.0
    calorias = 0.0
    proteina = 0.0
    carboidrato = 0.0
    gordura = 0.0
    sodio = 0.0

    for item in ficha.ingredientes_ficha:
        ing = item.ingrediente
        if not ing:
            continue

        custo_total += item.custo_calculado or 0.0

        # Nutrição por porção (qtd_liquida em g, tabela TACO é por 100g)
        qtd_liq = item.quantidade_liquida_g or 0.0
        fator_nutri = qtd_liq / 100.0
        if ing.calorias_100g:
            calorias += ing.calorias_100g * fator_nutri
        if ing.proteina_100g:
            proteina += ing.proteina_100g * fator_nutri
        if ing.carboidrato_100g:
            carboidrato += ing.carboidrato_100g * fator_nutri
        if ing.gordura_100g:
            gordura += ing.gordura_100g * fator_nutri
        if ing.sodio_100g:
            sodio += ing.sodio_100g * fator_nutri

    porcoes = max(ficha.rendimento_porcoes, 1)
    ficha.custo_total = round(custo_total, 4)
    ficha.custo_porcao = round(custo_total / porcoes, 4)

    # Nutrição por porção
    ficha.calorias_porcao = round(calorias / porcoes, 2) if calorias else None
    ficha.proteina_porcao = round(proteina / porcoes, 2) if proteina else None
    ficha.carboidrato_porcao = round(carboidrato / porcoes, 2) if carboidrato else None
    ficha.gordura_porcao = round(gordura / porcoes, 2) if gordura else None
    ficha.sodio_porcao = round(sodio / porcoes, 2) if sodio else None


def recalcular_fichas_por_ingrediente(
    db: Session,
    ingrediente_id: str,
) -> List[str]:
    """
    Recalcula todas as fichas técnicas que usam o ingrediente especificado.

    Retorna lista de IDs das fichas recalculadas.
    """
    # Busca o ingrediente atualizado
    ingrediente = db.query(Ingrediente).filter(
        Ingrediente.id == ingrediente_id
    ).first()
    if not ingrediente:
        logger.warning("Cascata: ingrediente %s não encontrado", ingrediente_id)
        return []

    # Busca todos os FichaIngrediente que referenciam este ingrediente
    items = db.query(FichaIngrediente).filter(
        FichaIngrediente.ingrediente_id == ingrediente_id
    ).all()

    if not items:
        return []

    # Agrupa por ficha
    fichas_ids = set()
    for item in items:
        _recalcular_item(item, ingrediente)
        fichas_ids.add(item.ficha_tecnica_id)

    # Recalcula totais de cada ficha afetada
    fichas_recalculadas = []
    for ficha_id in fichas_ids:
        ficha = db.query(FichaTecnica).filter(
            FichaTecnica.id == ficha_id
        ).first()
        if not ficha:
            continue

        _recalcular_ficha_totais(ficha)
        fichas_recalculadas.append(ficha_id)
        logger.info(
            "Cascata: ficha '%s' (%s) recalculada — custo_porcao=R$ %.4f",
            ficha.nome, ficha.codigo, ficha.custo_porcao,
        )

    # Commit é feito pelo chamador (router)
    # Invalida cache de stats
    try:
        from services.fichas_db_stats import clear_fichas_db_stats_cache
        clear_fichas_db_stats_cache()
    except Exception:
        pass

    logger.info(
        "Cascata: ingrediente '%s' atualizado → %d ficha(s) recalculada(s)",
        ingrediente.nome, len(fichas_recalculadas),
    )
    return fichas_recalculadas


def recalcular_ficha_unica(db: Session, ficha_id: str) -> Optional[str]:
    """
    Recalcula uma única ficha técnica. Útil para recálculo manual.
    Retorna o ID da ficha ou None se não encontrada.
    """
    ficha = db.query(FichaTecnica).filter(FichaTecnica.id == ficha_id).first()
    if not ficha:
        return None

    for item in ficha.ingredientes_ficha:
        ing = item.ingrediente
        if not ing:
            continue
        _recalcular_item(item, ing)

    _recalcular_ficha_totais(ficha)

    try:
        from services.fichas_db_stats import clear_fichas_db_stats_cache
        clear_fichas_db_stats_cache()
    except Exception:
        pass

    return ficha_id


def recalcular_todas_fichas_empresa(db: Session, empresa_id: str) -> int:
    """
    Recalcula TODAS as fichas técnicas ativas de uma empresa.
    Útil após importação em massa ou atualização de tabela de preços.
    Retorna o número de fichas recalculadas.
    """
    fichas = db.query(FichaTecnica).filter(
        FichaTecnica.empresa_id == empresa_id,
        FichaTecnica.ativo == True,  # noqa: E712
    ).all()

    count = 0
    for ficha in fichas:
        for item in ficha.ingredientes_ficha:
            ing = item.ingrediente
            if not ing:
                continue
            _recalcular_item(item, ing)
        _recalcular_ficha_totais(ficha)
        count += 1

    try:
        from services.fichas_db_stats import clear_fichas_db_stats_cache
        clear_fichas_db_stats_cache()
    except Exception:
        pass

    logger.info("Cascata em massa: %d fichas recalculadas (empresa=%s)", count, empresa_id)
    return count
