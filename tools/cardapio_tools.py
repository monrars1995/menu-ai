"""
Menu.AI — Ferramentas para os Agentes de Cardápio

- Listagem e custo de pratos: fichas técnicas no banco (FichaTecnica), não Excel.
- Contratos, sazonalidade, validação nutricional, contexto.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from services.contract_parser import build_contract_extraction_error, extract_contract_text
from tools.compat import tool

# ============================================================
# Configuração global — actualizada pelo CardapioCrew antes de rodar
# ============================================================
CONTRATO_PATH:         Optional[str] = None
DIAS:                  int   = 30
TARGET_CUSTO_TOTAL:    float = 10.00
TARGET_CUSTO_PROTEICO: float = 3.50
RESTRICOES_USUARIO:    str   = ""

# Contexto compartilhado — injetado pelo crew
_ctx = None  # SharedContext


def _fichas_db_message_prefix() -> str:
    from tools import db_tools as dt
    if not dt.DB_AVAILABLE or not dt.EMPRESA_ID:
        return (
            "[BANCO/EMPRESA] Defina banco e empresa (empresa_id) no job. "
            "A listagem de pratos vem de fichas técnicas no SQL, não de planilhas."
        )
    return ""


# ============================================================
# 1. FICHAS TÉCNICAS (banco) — listagem e custo
# ============================================================

@tool("Listar Pratos por Categoria")
def listar_pratos_por_categoria(categoria: str = "") -> str:
    """
    Lista pratos (fichas técnicas) do banco da empresa, filtrados por categoria.

    Se categoria vazia, mostra resumo: quantas fichas por categoria.
    """
    from tools import db_tools as dt
    from sqlalchemy import func
    from database.models import FichaTecnica

    pre = _fichas_db_message_prefix()
    if pre:
        return pre
    db = dt._get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Não foi possível abrir sessão."
    try:
        if not categoria.strip():
            qrows = (
                db.query(FichaTecnica.categoria, func.count(FichaTecnica.id))
                .filter(
                    FichaTecnica.empresa_id == dt.EMPRESA_ID,
                    FichaTecnica.ativo == True,  # noqa: E712
                )
                .group_by(FichaTecnica.categoria)
                .all()
            )
            if not qrows:
                return "Nenhuma ficha técnica ativa no banco para esta empresa."
            resumo = [f"  • {r[0]}: {r[1]} fichas" for r in sorted(qrows, key=lambda x: -x[1])]
            return "CATEGORIAS (fichas técnicas no banco):\n" + "\n".join(resumo)

        pratos = (
            db.query(FichaTecnica)
            .filter(
                FichaTecnica.empresa_id == dt.EMPRESA_ID,
                FichaTecnica.ativo == True,  # noqa: E712
                FichaTecnica.categoria.ilike(f"%{categoria.strip()}%"),
            )
            .order_by(FichaTecnica.nome)
            .limit(150)
            .all()
        )
        if not pratos:
            return f"Nenhuma ficha com categoria contendo '{categoria}'."

        linhas = [f"=== {categoria.upper()} ({len(pratos)} fichas) ==="]
        for p in pratos:
            linhas.append(f"{p.codigo:>10} | {p.nome}")
        if len(pratos) == 150:
            linhas.append("\n(limite 150 — use busca por palavra-chave)")
        return "\n".join(linhas)
    except Exception as e:
        return f"ERRO: {e}"
    finally:
        dt._close(db)


@tool("Buscar Pratos por Palavra-Chave")
def buscar_pratos(palavra_chave: str, categoria: str = "") -> str:
    """Busca fichas técnicas no banco por nome; opcionalmente filtra categoria (substring)."""
    from tools import db_tools as dt
    from database.models import FichaTecnica

    pre = _fichas_db_message_prefix()
    if pre:
        return pre
    db = dt._get_db()
    if not db:
        return "[BANCO INDISPONÍVEL] Não foi possível abrir sessão."
    try:
        q = db.query(FichaTecnica).filter(
            FichaTecnica.empresa_id == dt.EMPRESA_ID,
            FichaTecnica.ativo == True,  # noqa: E712
        )
        if categoria.strip():
            q = q.filter(FichaTecnica.categoria.ilike(f"%{categoria.strip()}%"))
        if palavra_chave.strip():
            q = q.filter(FichaTecnica.nome.ilike(f"%{palavra_chave.strip()}%"))
        rows = q.order_by(FichaTecnica.nome).limit(100).all()
        if not rows:
            return f"Nenhum prato encontrado (palavra='{palavra_chave}', categoria='{categoria}')."
        linhas = [f"=== Busca: '{palavra_chave}' ({len(rows)} resultados) ==="]
        for r in rows:
            linhas.append(f"{r.codigo:>10} | {r.categoria:<24} | {r.nome}")
        return "\n".join(linhas)
    except Exception as e:
        return f"ERRO: {e}"
    finally:
        dt._close(db)


@tool("Calcular Custo Estimado do Prato")
def calcular_custo_prato(
    codigo_prato: Union[str, int],
    gramatura_alvo_g: float = 0.0,
) -> str:
    """
    Custo e detalhe por código da ficha técnica (ex: PROT-042) ou ID UUID.
    Dados vêm do banco (ingredientes e FC).
    """
    from tools import db_tools as dt

    if not dt.DB_AVAILABLE or not dt.EMPRESA_ID:
        return _fichas_db_message_prefix()
    cod = str(codigo_prato).strip()
    if not cod:
        return "Informe o código da ficha técnica."
    t = dt.detalhe_ficha_tecnica
    if hasattr(t, "invoke"):
        return t.invoke({"codigo_ou_id": cod, "gramatura_alvo_g": gramatura_alvo_g})
    return t(cod, gramatura_alvo_g=gramatura_alvo_g)


# ============================================================
# 2. CONTRATO — Leitura e persistência de regras
# ============================================================

@tool("Ler Contrato (Arquivo PDF/XLSX/DOCX/TXT)")
def ler_regras_contrato(consulta: str = "") -> str:
    """
    Lê o arquivo de contrato/proposta carregado (PDF/XLSX/DOCX/TXT/MD/RTF) e retorna o texto completo,
    priorizando as seções com regras de cardápio, gramaturas, frequências e restrições.

    Use para a análise INICIAL do contrato.
    Para contratos já cadastrados no banco, use 'Consultar Regras do Contrato no Banco'.
    """
    LIMITE_TOTAL = 40000  # ~30 páginas de contrato

    # Palavras-chave que indicam seções relevantes de cardápio/alimentação
    KEYWORDS = [
        "cardápio", "cardapio", "gramatura", "proteína", "proteina",
        "refeição", "refeicao", "frequência", "frequencia", "incidência",
        "incidencia", "proibid", "vedado", "restricao", "restrição",
        "nutricional", "caloria", "almoço", "almoco", "jantar", "desjejum",
        "lanche", "carne", "frango", "peixe", "salada", "guarnição",
        "guarnicao", "sobremesa", "bandeja", "per capita", "per_capita",
        "custo", "alergên", "alergeno", "vegetarian", "vegano", "glúten",
        "gluten", "lactose", "composição", "composicao", "fornecimento",
        "cardápios", "especificação", "especificacao", "técnica", "tecnica",
    ]

    try:
        extraction = extract_contract_text(CONTRATO_PATH)
        texto_bruto = extraction.text

        # Extração inteligente: prioriza parágrafos/seções com palavras-chave
        if len(texto_bruto) > LIMITE_TOTAL:
            linhas = texto_bruto.split("\n")
            relevantes = []
            outros = []

            for linha in linhas:
                linha_lower = linha.lower()
                if any(kw in linha_lower for kw in KEYWORDS):
                    relevantes.append(linha)
                else:
                    outros.append(linha)

            # Monta resultado: seções relevantes primeiro + início do documento
            cabecalho = "\n".join(outros[:80])   # primeiras linhas do documento (identificação)
            corpo_relevante = "\n".join(relevantes)
            resultado = (
                "=== INÍCIO DO DOCUMENTO (identificação) ===\n"
                + cabecalho
                + "\n\n=== SEÇÕES RELEVANTES PARA CARDÁPIO ===\n"
                + corpo_relevante
            )
            resultado = resultado[:LIMITE_TOTAL]
        else:
            resultado = (texto_bruto or "")[:LIMITE_TOTAL]

        if not extraction.ok or not resultado.strip():
            return (
                "[ERRO_CONTRATO_SEM_TEXTO]\n"
                + build_contract_extraction_error(extraction)
                + "\nNao aplique defaults. Solicite reenvio do documento."
            )

        if RESTRICOES_USUARIO.strip():
            resultado += "\n\n=== RESTRIÇÕES TEXTUAIS DO CLIENTE ===\n" + RESTRICOES_USUARIO

        resultado += (
            f"\n\n=== PARÂMETROS DA SESSÃO ==="
            f"\nCusto TOTAL alvo: R$ {TARGET_CUSTO_TOTAL:.2f}/pessoa"
            f"\nCusto PROTEÍCO alvo: R$ {TARGET_CUSTO_PROTEICO:.2f}/pessoa"
            f"\nPeríodo: {DIAS} dias"
            f"\nTotal de caracteres lidos do contrato: {len(texto_bruto):,}"
            f"\nFormato: {extraction.ext or 'desconhecido'}"
            f"\nExtrator: {extraction.parser}"
            f"\nPaginas com texto: {extraction.pages_with_text}/{extraction.pages_total}"
            f"\nAbas (quando planilha): {extraction.sheets_total}"
            f"\nKeywords detectadas: {extraction.keywords_found}"
        )
        if extraction.warning:
            resultado += f"\nAviso de extração: {extraction.warning}"

        return resultado

    except Exception as e:
        return f"ERRO: {e}"


@tool("Salvar Regras Extraídas do Contrato")
def salvar_regras_extraidas(regras_json: str) -> str:
    """
    Persiste as regras estruturadas extraídas do contrato em formato JSON.
    CHAME esta ferramenta após concluir a análise do contrato.

    Formato esperado (campos mínimos):
    {
      "incidencias": {"carne_bovina": "3x/semana", "peixe": "1x/semana"},
      "proibicoes": ["carne_suina", "frutos_do_mar"],
      "estrutura": {
        "prato_proteico": 1, "opcao_proteica": 1,
        "guarnicao": 2, "salada": 2, "sobremesa": 0
      },
      "gramaturas": {"proteico": "120g", "guarnicao": "80g"},
      "restricoes_alergenos": [],
      "dietas_especiais": [],
      "observacoes": "texto livre com outras regras"
    }

    Campos extras são bem-vindos — use quantos campos forem necessários
    para capturar todas as nuances do contrato.
    """
    try:
        if isinstance(regras_json, dict):
            dados = regras_json
        else:
            # Tenta extrair JSON do texto (caso venha com explicação antes)
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", regras_json, re.IGNORECASE)
            json_str = match.group(1) if match else regras_json
            try:
                dados = json.loads(json_str)
            except json.JSONDecodeError:
                import ast
                dados = ast.literal_eval(json_str)

        path = Path("data/uploads/_regras_contrato.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

        # Atualiza o contexto compartilhado se disponível
        if _ctx is not None:
            _ctx.regras_contrato = dados

        campos = list(dados.keys())
        return (
            f"✅ Regras salvas com sucesso.\n"
            f"Campos capturados: {campos}\n"
            f"Incidências: {dados.get('incidencias', {})}\n"
            f"Proibições: {dados.get('proibicoes', [])}\n"
            f"Estrutura: {dados.get('estrutura', {})}"
        )

    except json.JSONDecodeError as e:
        return (
            f"❌ JSON inválido: {e}\n"
            "Certifique-se de que o JSON está dentro de ```json ... ``` ou é JSON puro."
        )
    except Exception as e:
        return f"ERRO: {e}"


@tool("Recuperar Regras do Contrato")
def recuperar_regras_contrato() -> str:
    """
    Retorna as regras do contrato previamente extraídas e salvas.
    Use antes de montar o cardápio ou validar custos.

    Se as regras não estiverem salvas, retorna uma mensagem orientando
    a executar o Analista de Contratos primeiro.
    """
    try:
        # Tenta primeiro o contexto em memória
        if _ctx is not None and _ctx.regras_contrato:
            return (
                "=== REGRAS DO CONTRATO (contexto em memória) ===\n"
                + json.dumps(_ctx.regras_contrato, ensure_ascii=False, indent=2)
            )

        # Fallback: arquivo em disco
        path = Path("data/uploads/_regras_contrato.json")
        if not path.exists():
            return (
                "[Regras não encontradas]\n"
                "O Analista de Contratos ainda não salvou as regras.\n"
                "Execute a tarefa de análise de contratos primeiro."
            )
        conteudo = path.read_text(encoding="utf-8")
        return "=== REGRAS DO CONTRATO (arquivo) ===\n" + conteudo

    except Exception as e:
        return f"ERRO: {e}"


# ============================================================
# 3. SAZONALIDADE
# ============================================================

# Calendário de safra simplificado (CEAGESP/CONAB)
# Chave: nome do ingrediente (lowercase), valor: meses em safra [1-12]
CALENDARIO_SAFRA = {
    "abobrinha":       [10, 11, 12, 1, 2, 3],
    "abóbora":         [2, 3, 4, 5, 6],
    "acelga":          [4, 5, 6, 7, 8, 9],
    "alface":          [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # ano todo
    "batata":          [1, 2, 3, 4, 5, 9, 10, 11, 12],
    "batata-doce":     [3, 4, 5, 6, 7, 8],
    "berinjela":       [10, 11, 12, 1, 2, 3],
    "beterraba":       [4, 5, 6, 7, 8, 9],
    "brócolis":        [4, 5, 6, 7, 8, 9],
    "cebola":          [10, 11, 12, 1, 2],
    "cenoura":         [1, 2, 3, 4, 5, 6, 7, 8],
    "chuchu":          [10, 11, 12, 1, 2, 3, 4],
    "couve":           [4, 5, 6, 7, 8, 9],
    "couve-flor":      [5, 6, 7, 8, 9],
    "espinafre":       [4, 5, 6, 7, 8, 9],
    "feijão-vagem":    [10, 11, 12, 1, 2],
    "jiló":            [10, 11, 12, 1, 2, 3],
    "mandioca":        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "mandioquinha":    [4, 5, 6, 7, 8, 9, 10],
    "maxixe":          [10, 11, 12, 1, 2, 3],
    "milho":           [10, 11, 12, 1, 2],
    "pepino":          [10, 11, 12, 1, 2, 3],
    "pimentão":        [11, 12, 1, 2, 3, 4],
    "quiabo":          [10, 11, 12, 1, 2, 3],
    "repolho":         [4, 5, 6, 7, 8, 9],
    "tomate":          [12, 1, 2, 3, 4],
    "vagem":           [10, 11, 12, 1, 2],
    # Frutas
    "abacaxi":         [10, 11, 12, 1, 2],
    "banana":          [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "goiaba":          [3, 4, 5, 6, 7, 8],
    "laranja":         [5, 6, 7, 8, 9, 10],
    "limão":           [4, 5, 6, 7, 8, 9],
    "mamão":           [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "manga":           [11, 12, 1, 2, 3],
    "maracujá":        [1, 2, 3, 9, 10, 11],
    "melancia":        [11, 12, 1, 2, 3],
    "melão":           [11, 12, 1, 2],
    "morango":         [5, 6, 7, 8, 9],
    "pera":            [12, 1, 2, 3],
    "uva":             [12, 1, 2, 3],
}

NOMES_MESES = [
    "", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez"
]


@tool("Verificar Sazonalidade de Ingredientes")
def verificar_sazonalidade(ingredientes: str, mes_referencia: int = 0) -> str:
    """
    Verifica quais ingredientes estão na safra no mês de referência.
    Ingredientes na safra têm menor custo e maior qualidade.

    Parâmetros:
        ingredientes    — lista separada por vírgula (ex: "tomate, cenoura, batata")
        mes_referencia  — mês de 1 a 12 (0 = mês atual)

    Retorna: quais estão em safra, quais estão fora, e alternativas sazonais.
    """
    try:
        mes = mes_referencia if 1 <= mes_referencia <= 12 else datetime.now().month
        nome_mes = NOMES_MESES[mes]

        lista = [i.strip().lower() for i in ingredientes.split(",") if i.strip()]
        if not lista:
            return "Informe pelo menos um ingrediente."

        em_safra    = []
        fora_safra  = []
        desconhecido = []

        for ing in lista:
            # Busca correspondência parcial
            found = None
            for chave in CALENDARIO_SAFRA:
                if chave in ing or ing in chave:
                    found = chave
                    break

            if found is None:
                desconhecido.append(ing)
            elif mes in CALENDARIO_SAFRA[found]:
                em_safra.append(ing)
            else:
                fora_safra.append(ing)

        # Sugestões de alternativas sazonais
        alternativas = [
            k for k, meses in CALENDARIO_SAFRA.items()
            if mes in meses and k not in lista
        ]

        linhas = [
            f"=== SAZONALIDADE — {nome_mes} ===",
            "",
            f"✅ EM SAFRA ({len(em_safra)}): {', '.join(em_safra) or 'nenhum'}",
            f"❌ FORA DE SAFRA ({len(fora_safra)}): {', '.join(fora_safra) or 'nenhum'}",
            f"❓ Sem dados ({len(desconhecido)}): {', '.join(desconhecido) or 'nenhum'}",
            "",
            f"🌿 Alternativas sazonais disponíveis em {nome_mes}:",
            "   " + ", ".join(alternativas[:15]),
            "",
            "💡 Prefira ingredientes EM SAFRA para reduzir custos e aumentar qualidade.",
        ]
        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO: {e}"


# ============================================================
# 4. VALIDAÇÃO NUTRICIONAL (CFN / ANVISA)
# ============================================================

# Referências nutricionais por tipo de unidade de alimentação (UAN)
# Fonte: CFN Resolução 465/2010, PNAE, RDC ANVISA
REFERENCIAS_NUTRICIONAIS = {
    "industrial": {
        "descricao": "Restaurante Industrial / Empresas",
        "calorias_min": 600,
        "calorias_max": 800,
        "proteina_min_pct": 10,   # % do VET
        "proteina_max_pct": 15,
        "carboidrato_min_pct": 55,
        "carboidrato_max_pct": 75,
        "gordura_min_pct": 15,
        "gordura_max_pct": 30,
        "sodio_max_mg": 800,
        "fibra_min_g": 7,
    },
    "hospitalar": {
        "descricao": "Alimentação Hospitalar",
        "calorias_min": 400,
        "calorias_max": 700,
        "proteina_min_pct": 15,
        "proteina_max_pct": 20,
        "carboidrato_min_pct": 45,
        "carboidrato_max_pct": 60,
        "gordura_min_pct": 25,
        "gordura_max_pct": 35,
        "sodio_max_mg": 600,
        "fibra_min_g": 5,
    },
    "escolar": {
        "descricao": "Alimentação Escolar (PNAE)",
        "calorias_min": 350,
        "calorias_max": 500,
        "proteina_min_pct": 10,
        "proteina_max_pct": 15,
        "carboidrato_min_pct": 55,
        "carboidrato_max_pct": 75,
        "gordura_min_pct": 15,
        "gordura_max_pct": 30,
        "sodio_max_mg": 500,
        "fibra_min_g": 4,
    },
}


@tool("Validar Conformidade Nutricional")
def validar_nutricional(
    calorias: float,
    proteina_g: float,
    carboidrato_g: float,
    gordura_g: float,
    sodio_mg: float = 0.0,
    tipo_uan: str = "industrial",
) -> str:
    """
    Valida se os valores nutricionais de uma refeição estão dentro
    dos parâmetros do CFN (Conselho Federal de Nutricionistas) e ANVISA.

    Parâmetros:
        calorias     — kcal por porção
        proteina_g   — gramas de proteína por porção
        carboidrato_g — gramas de carboidrato por porção
        gordura_g    — gramas de gordura por porção
        sodio_mg     — miligramas de sódio (opcional)
        tipo_uan     — tipo de UAN: 'industrial', 'hospitalar', 'escolar'

    Retorna: avaliação detalhada com status de cada macronutriente.
    """
    try:
        ref = REFERENCIAS_NUTRICIONAIS.get(tipo_uan.lower(), REFERENCIAS_NUTRICIONAIS["industrial"])

        # Calcula VET real
        vet = (proteina_g * 4) + (carboidrato_g * 4) + (gordura_g * 9)
        if vet == 0:
            vet = calorias or 1  # evita divisão por zero

        pct_prot = (proteina_g * 4 / vet) * 100
        pct_carb = (carboidrato_g * 4 / vet) * 100
        pct_gord = (gordura_g * 9 / vet) * 100

        resultados = []
        aprovado = True

        # Calorias
        cal_ok = ref["calorias_min"] <= calorias <= ref["calorias_max"]
        if not cal_ok: aprovado = False
        resultados.append({
            "indicador": "Calorias",
            "valor": f"{calorias:.0f} kcal",
            "referencia": f"{ref['calorias_min']}–{ref['calorias_max']} kcal",
            "status": "✅ OK" if cal_ok else "❌ FORA",
        })

        # Proteína
        prot_ok = ref["proteina_min_pct"] <= pct_prot <= ref["proteina_max_pct"]
        if not prot_ok: aprovado = False
        resultados.append({
            "indicador": "Proteína",
            "valor": f"{proteina_g:.1f}g ({pct_prot:.1f}% VET)",
            "referencia": f"{ref['proteina_min_pct']}–{ref['proteina_max_pct']}% VET",
            "status": "✅ OK" if prot_ok else "❌ FORA",
        })

        # Carboidrato
        carb_ok = ref["carboidrato_min_pct"] <= pct_carb <= ref["carboidrato_max_pct"]
        if not carb_ok: aprovado = False
        resultados.append({
            "indicador": "Carboidrato",
            "valor": f"{carboidrato_g:.1f}g ({pct_carb:.1f}% VET)",
            "referencia": f"{ref['carboidrato_min_pct']}–{ref['carboidrato_max_pct']}% VET",
            "status": "✅ OK" if carb_ok else "❌ FORA",
        })

        # Gordura
        gord_ok = ref["gordura_min_pct"] <= pct_gord <= ref["gordura_max_pct"]
        if not gord_ok: aprovado = False
        resultados.append({
            "indicador": "Gordura",
            "valor": f"{gordura_g:.1f}g ({pct_gord:.1f}% VET)",
            "referencia": f"{ref['gordura_min_pct']}–{ref['gordura_max_pct']}% VET",
            "status": "✅ OK" if gord_ok else "❌ FORA",
        })

        # Sódio (se informado)
        if sodio_mg > 0:
            sod_ok = sodio_mg <= ref["sodio_max_mg"]
            if not sod_ok: aprovado = False
            resultados.append({
                "indicador": "Sódio",
                "valor": f"{sodio_mg:.0f}mg",
                "referencia": f"≤ {ref['sodio_max_mg']}mg",
                "status": "✅ OK" if sod_ok else "❌ FORA",
            })

        # Monta saída
        linhas = [
            f"=== VALIDAÇÃO NUTRICIONAL ({ref['descricao']}) ===",
            f"Resultado: {'✅ APROVADO' if aprovado else '❌ REPROVADO — AJUSTES NECESSÁRIOS'}",
            "",
        ]
        for r in resultados:
            linhas.append(
                f"  {r['status']}  {r['indicador']:<15} {r['valor']:<25} (ref: {r['referencia']})"
            )

        if not aprovado:
            linhas += [
                "",
                "💡 RECOMENDAÇÕES:",
                "  • Calorias baixas → adicione acompanhamento ou aumente gramatura",
                "  • Proteína baixa → reforce com leguminosas ou opção proteica",
                "  • Carboidrato alto → reduza arroz/pão, adicione vegetais",
                "  • Sódio alto → evite embutidos, reduza sal no preparo",
            ]

        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO: {e}"


# ============================================================
# 5. COMUNICAÇÃO COM O COORDENADOR
# ============================================================

@tool("Enviar Relatório ao Coordenador")
def enviar_relatorio_coordenador(
    agente_remetente: str,
    tipo_mensagem: str,
    conteudo: str,
    dados_json: str = "{}",
    requer_decisao: bool = False,
) -> str:
    """
    Envia uma mensagem estruturada ao Coordenador.

    Use esta ferramenta para comunicar:
      - 'relatorio'   → tarefa concluída com sucesso
      - 'alerta'      → problema encontrado que precisa de atenção
      - 'solicitacao' → pedido de redistribuição de tarefa
      - 'aprovacao'   → aprovação do trabalho de outro agente
      - 'reprovacao'  → reprovação com instruções de correção
      - 'consulta'    → pedido de contexto adicional

    Parâmetros:
        agente_remetente — seu nome (ex: 'Nutricionista')
        tipo_mensagem    — um dos tipos acima
        conteudo         — descrição em linguagem natural
        dados_json       — dados estruturados em JSON (opcional)
        requer_decisao   — True se o Coordenador precisa agir antes de continuar
    """
    try:
        from pipeline.protocolo import AgentMessage, TipoMensagem, SharedContext

        # Parse do tipo
        tipo_map = {
            "relatorio": TipoMensagem.RELATORIO,
            "alerta": TipoMensagem.ALERTA,
            "solicitacao": TipoMensagem.SOLICITACAO,
            "aprovacao": TipoMensagem.APROVACAO,
            "reprovacao": TipoMensagem.REPROVACAO,
            "consulta": TipoMensagem.CONSULTA,
        }
        tipo = tipo_map.get(tipo_mensagem.lower(), TipoMensagem.RELATORIO)

        # Parse dos dados
        try:
            dados = json.loads(dados_json) if dados_json.strip() and dados_json != "{}" else {}
        except json.JSONDecodeError:
            dados = {"raw": dados_json}

        msg = AgentMessage(
            de=agente_remetente,
            para="Coordenador",
            tipo=tipo,
            conteudo=conteudo,
            dados=dados,
            requer_decisao=requer_decisao,
        )

        # Emite para o contexto compartilhado se disponível
        if _ctx is not None:
            _ctx.emit(msg)
            return (
                f"✅ Mensagem enviada ao Coordenador.\n"
                f"Tipo: {tipo.value} | Requer decisão: {requer_decisao}\n"
                f"Conteúdo: {conteudo[:200]}"
            )

        # Fallback: salva em arquivo para o Coordenador ler
        path = Path("data/uploads/_inbox_coordenador.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(msg.to_json() + "\n")

        return (
            f"✅ Mensagem registrada para o Coordenador.\n"
            f"Tipo: {tipo.value} | Requer decisão: {requer_decisao}\n"
            f"Conteúdo: {conteudo[:200]}"
        )

    except Exception as e:
        return f"ERRO ao enviar mensagem: {e}"


@tool("Ler Contexto Compartilhado")
def ler_contexto_atual() -> str:
    """
    Retorna o estado atual do contexto compartilhado da sessão.
    Use para verificar:
      - Em qual iteração estamos
      - Quais etapas já foram concluídas
      - Alertas e feedbacks do Coordenador
      - Regras do contrato já extraídas

    Chame esta ferramenta no INÍCIO de cada tarefa para se atualizar.
    """
    try:
        if _ctx is None:
            return (
                "[Contexto não disponível]\n"
                "Use 'Recuperar Regras do Contrato' para acessar as regras extraídas."
            )

        import json
        estado = _ctx.to_dict()
        linhas = [
            "=== CONTEXTO ATUAL DA SESSÃO ===",
            f"Etapa: {estado['etapa_atual']}",
            f"Iteração: {estado['iteracao']}/{_ctx.max_iteracoes}",
            f"Período: {estado['dias']} dias",
            f"Custo-alvo: R$ {estado['target_custo_total']:.2f} (proteico: R$ {estado['target_custo_proteico']:.2f})",
            "",
            f"Cardápio aprovado: {'✅ Sim' if estado['cardapio_aprovado'] else '❌ Ainda não'}",
            f"Financeiro OK: {'✅' if estado['financeiro_ok'] else '❌'}",
            f"Nutricional OK: {'✅' if estado['nutricional_ok'] else '❌'}",
        ]
        if estado["alertas"]:
            linhas += ["", f"⚠️ Alertas: {' | '.join(estado['alertas'])}"]
        if estado["erros"]:
            linhas += ["", f"❌ Erros: {' | '.join(estado['erros'])}"]
        if _ctx.regras_contrato:
            linhas += ["", "Regras do contrato: JÁ EXTRAÍDAS ✅"]

        return "\n".join(linhas)

    except Exception as e:
        return f"ERRO: {e}"
