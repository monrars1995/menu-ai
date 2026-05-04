"""
Menu.AI — Ferramentas integradas ao banco de dados PostgreSQL.

Estas ferramentas permitem que os agentes consultem dados reais:
fichas técnicas cadastradas, contratos do banco, custos reais
de ingredientes e histórico de cardápios anteriores.

Ativadas automaticamente quando DATABASE_URL está configurado.
Quando o banco está indisponível, retornam mensagem informativa;
as outras ferramentas (fichas em SQL) não têm *fallback* para Excel.
"""
import json
import os
from typing import Optional

from tools.compat import tool

# ============================================================
# Configuração — preenchida pelo CardapioCrew antes de rodar
# ============================================================
EMPRESA_ID:   Optional[str] = None
CONTRATO_ID:  Optional[str] = None
DB_AVAILABLE: bool = False

_db_session = None  # injetada pelo crew


def _get_db():
    """Retorna sessão do banco ou None se indisponível."""
    if not DB_AVAILABLE:
        return None
    try:
        from database.connection import SessionLocal
        return SessionLocal()
    except Exception:
        return None


def _close(db):
    if db:
        try:
            db.close()
        except Exception:
            pass


# ============================================================
# FERRAMENTAS DO BANCO
# ============================================================

@tool("Consultar Fichas Técnicas do Banco")
def consultar_fichas_tecnicas(
    categoria: str = "",
    busca: str = "",
    custo_max: float = 0.0,
    gramatura_alvo_g: float = 0.0,
) -> str:
    """
    Busca fichas técnicas cadastradas no banco da empresa.
    Retorna pratos com custo REAL (calculado a partir dos ingredientes e FC).

    Parâmetros:
        categoria  — filtra por categoria (ex: 'PRATO PROTEICO', 'GUARNICAO')
        busca      — filtra por nome do prato (ex: 'frango', 'bovino')
        custo_max  — filtra por custo máximo por porção em R$ (0 = sem limite)

    Use esta ferramenta em primeiro lugar para pratos e custos da empresa.
    Fichas do banco têm custos reais e informação nutricional.
    """
    db = _get_db()
    if not db:
        return (
            "[BANCO INDISPONÍVEL] Fichas técnicas do banco não acessíveis. "
            "Só após o PostgreSQL/SQLite estar acessível é possível listar pratos reais."
        )

    try:
        from database.models import FichaTecnica

        q = db.query(FichaTecnica).filter(
            FichaTecnica.empresa_id == EMPRESA_ID,
            FichaTecnica.ativo == True,
        )

        if categoria.strip():
            q = q.filter(FichaTecnica.categoria.ilike(f"%{categoria.strip()}%"))
        if busca.strip():
            q = q.filter(FichaTecnica.nome.ilike(f"%{busca.strip()}%"))
        if custo_max > 0:
            q = q.filter(FichaTecnica.custo_porcao <= custo_max)

        fichas = q.order_by(FichaTecnica.custo_porcao).limit(80).all()

        if not fichas:
            return f"Nenhuma ficha técnica encontrada para categoria='{categoria}' busca='{busca}'."

        linhas = [f"=== FICHAS TÉCNICAS (banco) — {len(fichas)} encontradas ==="]
        for f in fichas:
            fator = 1.0
            if gramatura_alvo_g > 0 and f.peso_porcao_g and f.peso_porcao_g > 0:
                fator = gramatura_alvo_g / float(f.peso_porcao_g)
                
            custo_final = f.custo_porcao * fator
            
            nutri = ""
            if f.calorias_porcao:
                nutri = f" | {f.calorias_porcao * fator:.0f}kcal | P:{f.proteina_porcao * fator:.1f}g"
                
            peso_info = ""
            if gramatura_alvo_g > 0:
                peso_info = f" ({gramatura_alvo_g}g)"
            elif f.peso_porcao_g:
                peso_info = f" ({f.peso_porcao_g}g)"
                
            flags = []
            if f.vegana:        flags.append("VEGANA")
            if f.vegetariana:   flags.append("VEG")
            if f.contem_gluten: flags.append("GLUTEN")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            linhas.append(
                f"{f.codigo:>8} | {f.categoria:<22} | {f.nome:<40} "
                f"| R$ {custo_final:.2f}{peso_info}{nutri}{flag_str}"
            )

        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO ao consultar fichas técnicas: {e}"
    finally:
        _close(db)


@tool("Consultar Detalhe de Ficha Técnica")
def detalhe_ficha_tecnica(codigo_ou_id: str, gramatura_alvo_g: float = 0.0) -> str:
    """
    Retorna ficha técnica completa: ingredientes, FC, modo de preparo,
    custo detalhado por ingrediente e informação nutricional completa.

    Use para confirmar detalhes antes de incluir um prato no cardápio.
    Informe o código (ex: 'PROT-042') ou ID (UUID).
    """
    db = _get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Detalhes de fichas técnicas não acessíveis."

    try:
        from database.models import FichaTecnica

        ficha = db.query(FichaTecnica).filter(
            (FichaTecnica.codigo == codigo_ou_id) |
            (FichaTecnica.id == codigo_ou_id)
        ).filter(FichaTecnica.empresa_id == EMPRESA_ID).first()

        if not ficha:
            return f"Ficha técnica '{codigo_ou_id}' não encontrada."

        fator = 1.0
        if gramatura_alvo_g > 0 and ficha.peso_porcao_g and ficha.peso_porcao_g > 0:
            fator = gramatura_alvo_g / float(ficha.peso_porcao_g)
            
        custo_total = ficha.custo_total * fator
        custo_porcao = ficha.custo_porcao * fator
        peso_porcao = gramatura_alvo_g if gramatura_alvo_g > 0 else ficha.peso_porcao_g

        linhas = [
            f"=== FICHA TÉCNICA: {ficha.nome} ===",
            f"Código: {ficha.codigo}  |  Categoria: {ficha.categoria}",
            f"Rendimento: {ficha.rendimento_porcoes} porções  |  Peso/porção: {peso_porcao or '?'}g" + (" (ajustado)" if gramatura_alvo_g > 0 else ""),
            f"Tempo preparo: {ficha.tempo_preparo_min or '?'} min  |  Dificuldade: {ficha.dificuldade}",
            f"Equipamento: {ficha.equipamento or 'Padrão'}",
            "",
            f"CUSTO TOTAL: R$ {custo_total:.4f}  |  CUSTO/PORÇÃO: R$ {custo_porcao:.4f}",
            "",
        ]

        if ficha.ingredientes_ficha:
            linhas.append("INGREDIENTES:")
            linhas.append(f"  {'Ingrediente':<35} {'Bruto(g)':>8} {'FC':>5} {'Líquido(g)':>10} {'Custo(R$)':>10}")
            linhas.append("  " + "-" * 70)
            for item in ficha.ingredientes_ficha:
                ing = item.ingrediente
                nome_ing = ing.nome if ing else item.ingrediente_id
                linhas.append(
                    f"  {nome_ing:<35} {item.quantidade_bruta_g * fator:>8.1f} "
                    f"{item.fator_correcao:>5.2f} "
                    f"{(item.quantidade_liquida_g or 0) * fator:>10.1f} "
                    f"{item.custo_calculado * fator:>10.4f}"
                )

        if ficha.calorias_porcao:
            linhas += [
                "",
                "VALOR NUTRICIONAL (por porção" + (" ajustada):" if gramatura_alvo_g > 0 else "):"),
                f"  Calorias: {ficha.calorias_porcao * fator:.0f} kcal",
                f"  Proteína: {ficha.proteina_porcao * fator:.1f}g  |  Carboidrato: {ficha.carboidrato_porcao * fator:.1f}g  |  Gordura: {ficha.gordura_porcao * fator:.1f}g",
            ]
            if ficha.sodio_porcao:
                linhas.append(f"  Sódio: {ficha.sodio_porcao * fator:.0f}mg")

        flags = []
        if ficha.vegana:        flags.append("Vegana")
        if ficha.vegetariana:   flags.append("Vegetariana")
        if ficha.contem_gluten: flags.append("Contém Glúten")
        if ficha.contem_lactose: flags.append("Contém Lactose")
        if flags:
            linhas += ["", f"RESTRIÇÕES: {', '.join(flags)}"]

        if ficha.modo_preparo:
            linhas += ["", "MODO DE PREPARO:", ficha.modo_preparo[:800]]

        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO ao buscar detalhe da ficha: {e}"
    finally:
        _close(db)


@tool("Consultar Regras do Contrato no Banco")
def consultar_contrato_banco(contrato_id: str = "") -> str:
    """
    Retorna as regras do contrato diretamente do banco de dados.
    Inclui targets de custo, estrutura da refeição, incidências,
    proibições, gramaturas e observações.

    Use esta ferramenta quando o Analista de Contratos precisar
    das regras já extraídas de um contrato cadastrado.
    """
    db = _get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Regras do contrato não acessíveis via banco."

    try:
        from database.models import Contrato

        cid = contrato_id.strip() or CONTRATO_ID
        if not cid:
            # Pega o contrato ativo da empresa
            contrato = db.query(Contrato).filter(
                Contrato.empresa_id == EMPRESA_ID,
                Contrato.ativo == True,
            ).order_by(Contrato.created_at.desc()).first()
        else:
            contrato = db.query(Contrato).filter(Contrato.id == cid).first()

        if not contrato:
            return "[Nenhum contrato ativo encontrado para esta empresa no banco]"

        dados = {
            "nome": contrato.nome,
            "numero": contrato.numero_contrato,
            "vigencia": f"{contrato.data_inicio} a {contrato.data_fim}",
            "custo_total_max": contrato.custo_total_max,
            "custo_proteico_max": contrato.custo_proteico_max,
            "num_refeicoes_dia": contrato.num_refeicoes_dia,
            "estrutura_refeicao": contrato.estrutura_refeicao,
            "gramaturas": contrato.gramaturas_json,
            "incidencias": contrato.incidencias_json,
            "proibicoes": contrato.proibicoes_json,
            "regras_extraidas": contrato.regras_json,
            "observacoes": contrato.observacoes,
        }

        return (
            f"=== CONTRATO: {contrato.nome} ===\n"
            + json.dumps(dados, ensure_ascii=False, indent=2, default=str)
        )

    except Exception as e:
        return f"ERRO ao consultar contrato: {e}"
    finally:
        _close(db)


@tool("Buscar Contexto Semântico")
def buscar_contexto_semantico(
    consulta: str,
    tipo_fonte: str = "",
    limite: int = 5,
) -> str:
    """
    Busca contexto semântico na base vetorial da empresa.

    Parâmetros:
        consulta    — pergunta ou contexto livre
        tipo_fonte  — "contrato", "ficha", "cardapio" ou vazio para todas
        limite      — quantidade máxima de trechos

    Use esta ferramenta para recuperar regras, fichas e cardápios parecidos
    mesmo quando a busca exata por nome/código não for suficiente.
    """
    db = _get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Busca semântica indisponível."

    try:
        from services.knowledge_base import semantic_search

        source_types = []
        tipo = (tipo_fonte or "").strip().lower()
        if tipo:
            source_types = [tipo]
        rows = semantic_search(
            db,
            query=consulta,
            empresa_id=EMPRESA_ID,
            source_types=source_types,
            limit=max(1, min(int(limite or 5), 12)),
        )
        if not rows:
            return "Nenhum contexto semântico encontrado para a consulta."

        linhas = [f"=== CONTEXTO SEMÂNTICO ({len(rows)} trechos) ==="]
        for idx, row in enumerate(rows, start=1):
            trecho = str(row.get("chunk_text") or "").strip().replace("\n", " ")
            linhas.append(
                f"{idx}. [{row.get('source_type')}] {row.get('title')} "
                f"(similaridade={float(row.get('similarity') or 0):.3f})"
            )
            if row.get("source_id"):
                linhas.append(f"   source_id={row.get('source_id')}")
            if trecho:
                linhas.append(f"   {trecho[:420]}")
        return "\n".join(linhas)
    except Exception as e:
        return f"ERRO na busca semântica: {e}"
    finally:
        _close(db)


@tool("Verificar Histórico de Cardápios Anteriores")
def historico_cardapios(num_meses: int = 3) -> str:
    """
    Consulta os últimos N meses de cardápios aprovados da empresa.
    Use para evitar repetição de pratos entre períodos.

    Retorna os pratos mais frequentes nos últimos cardápios,
    permitindo ao Nutricionista garantir variedade.
    """
    db = _get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Histórico de cardápios não acessível."

    try:
        from datetime import datetime, timedelta
        from database.models import Cardapio, CardapioDia, CardapioRefeicao
        from sqlalchemy import func

        data_limite = datetime.utcnow() - timedelta(days=num_meses * 30)

        # Pratos mais usados nos últimos meses
        pratos = (
            db.query(
                CardapioRefeicao.nome_prato,
                CardapioRefeicao.categoria,
                func.count(CardapioRefeicao.id).label("frequencia"),
            )
            .join(CardapioDia, CardapioDia.id == CardapioRefeicao.dia_id)
            .join(Cardapio, Cardapio.id == CardapioDia.cardapio_id)
            .filter(
                Cardapio.empresa_id == EMPRESA_ID,
                Cardapio.status.in_(["aprovado", "publicado"]),
                Cardapio.created_at >= data_limite,
            )
            .group_by(CardapioRefeicao.nome_prato, CardapioRefeicao.categoria)
            .order_by(func.count(CardapioRefeicao.id).desc())
            .limit(40)
            .all()
        )

        if not pratos:
            return f"Nenhum cardápio aprovado nos últimos {num_meses} meses. Sem restrições de repetição."

        linhas = [f"=== PRATOS MAIS USADOS (últimos {num_meses} meses) ===",
                  "Evite repetir os pratos com frequência alta:",
                  ""]
        for p in pratos:
            linhas.append(f"  {p.frequencia:>3}x | {p.categoria:<22} | {p.nome_prato}")

        linhas += [
            "",
            "⚠️ Dê preferência a pratos que NÃO aparecem nesta lista para garantir variedade."
        ]
        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO ao consultar histórico: {e}"
    finally:
        _close(db)


@tool("Gerar Lista de Compras")
def gerar_lista_compras(cardapio_json: str = "", num_comensais: int = 100) -> str:
    """
    Gera lista de compras consolidada a partir de um cardápio.

    Parâmetros:
        cardapio_json  — JSON com lista de fichas técnicas e dias de uso
        num_comensais  — número de pessoas para dimensionar as quantidades

    Agrupa ingredientes, soma quantidades brutas (incluindo FC)
    e calcula custo total estimado de compras.

    Formato do cardapio_json:
    {
      "fichas": [
        {"codigo": "PROT-001", "dias": [1, 3, 5]},
        {"codigo": "GUARD-002", "dias": [1, 2, 3, 4, 5]}
      ]
    }
    """
    db = _get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Geração de lista de compras requer banco de dados."

    try:
        from database.models import FichaTecnica, FichaIngrediente, Ingrediente
        from collections import defaultdict

        # Parse do JSON de entrada
        try:
            dados = json.loads(cardapio_json) if cardapio_json.strip() else {}
            fichas_uso = dados.get("fichas", [])
        except json.JSONDecodeError:
            return "❌ cardapio_json inválido. Envie um JSON com chave 'fichas'."

        if not fichas_uso:
            return "Nenhuma ficha informada para gerar lista de compras."

        # Acumula ingredientes
        compras: dict = defaultdict(lambda: {
            "nome": "", "unidade": "kg", "quantidade_bruta_kg": 0.0,
            "custo_unitario": 0.0, "custo_total": 0.0, "categoria": ""
        })

        fichas_nao_encontradas = []
        for item in fichas_uso:
            codigo = item.get("codigo", "")
            num_dias = len(item.get("dias", [1]))

            ficha = db.query(FichaTecnica).filter(
                FichaTecnica.codigo == codigo,
                FichaTecnica.empresa_id == EMPRESA_ID,
            ).first()

            if not ficha:
                fichas_nao_encontradas.append(codigo)
                continue

            # Fator de escala: porções × comensais × dias
            escala = (ficha.rendimento_porcoes or 1)
            repeticoes = (num_comensais * num_dias) / escala

            for fi in ficha.ingredientes_ficha:
                ing = fi.ingrediente
                if not ing:
                    continue
                ing_id = fi.ingrediente_id
                qtd_bruta_kg = (fi.quantidade_bruta_g / 1000.0) * repeticoes

                compras[ing_id]["nome"]             = ing.nome
                compras[ing_id]["unidade"]           = ing.unidade_medida
                compras[ing_id]["categoria"]         = ing.categoria
                compras[ing_id]["custo_unitario"]    = ing.custo_unitario
                compras[ing_id]["quantidade_bruta_kg"] += qtd_bruta_kg
                compras[ing_id]["custo_total"]       += qtd_bruta_kg * ing.custo_unitario

        if not compras:
            return "Nenhum ingrediente encontrado para as fichas informadas."

        # Organiza por categoria
        por_categoria: dict = defaultdict(list)
        total_geral = 0.0
        for ing_id, dados_ing in compras.items():
            por_categoria[dados_ing["categoria"]].append(dados_ing)
            total_geral += dados_ing["custo_total"]

        linhas = [
            f"=== LISTA DE COMPRAS — {num_comensais} comensais ===",
            f"Fichas processadas: {len(fichas_uso) - len(fichas_nao_encontradas)}",
            "",
        ]

        for cat, items in sorted(por_categoria.items()):
            linhas.append(f"▌ {cat}")
            for it in sorted(items, key=lambda x: -x["custo_total"]):
                linhas.append(
                    f"  {it['nome']:<40} "
                    f"{it['quantidade_bruta_kg']:>8.2f} kg  "
                    f"R$ {it['custo_unitario']:.2f}/kg  =  R$ {it['custo_total']:.2f}"
                )
            linhas.append("")

        linhas += [
            "─" * 60,
            f"CUSTO TOTAL DE COMPRAS: R$ {total_geral:.2f}",
            f"Custo por comensal: R$ {total_geral / num_comensais:.2f}",
        ]

        if fichas_nao_encontradas:
            linhas += ["", f"⚠️ Fichas não encontradas: {fichas_nao_encontradas}"]

        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO ao gerar lista de compras: {e}"
    finally:
        _close(db)
