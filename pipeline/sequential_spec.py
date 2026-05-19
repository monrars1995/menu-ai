"""
Especificação das 7 etapas sequenciais (substitui Crew.kickoff).
Mantém os textos de tarefa alinhados a _build_tasks; sistema curto + descrição detalhada.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class PipelineStep:
    label: str
    system: str
    user: str
    tools: List[Any]  # LangChain tools ou invocáveis


def _fonte(crew) -> str:
    db = {}
    if hasattr(crew, "_get_tools_db"):
        try:
            db = crew._get_tools_db() or {}
        except Exception:
            db = {}
    tem_banco = bool(getattr(crew, "db_disponivel", False)) and bool(db)
    if tem_banco:
        return (
            "Priorize 'Consultar Fichas Técnicas do Banco' (custo real). "
            "Se não encontrar, use 'Listar Pratos por Categoria' como fallback."
        )
    return "Use 'Listar Pratos por Categoria' e 'Buscar Pratos por Palavra-Chave'."


def _build_tool_lists(crew) -> List[List[Any]]:
    t = crew._get_tools_base()
    db = crew._get_tools_db() or {}
    # Analista
    tools_analista = [t["ler_contrato"], t["salvar_regras"], t["recuperar_regras"], t["ler_contexto"], t["enviar_msg"]]
    if db.get("contrato_banco"):
        tools_analista.insert(0, db["contrato_banco"])
    if db.get("contexto_semantico"):
        tools_analista.insert(0, db["contexto_semantico"])
    # Gestor
    tools_gestor = [t["ler_contexto"], t["listar_pratos"], t["buscar_pratos"]]
    if db.get("fichas_banco"):
        tools_gestor = [db["fichas_banco"], db.get("detalhe_ficha"), db.get("contexto_semantico"), t["ler_contexto"], t["listar_pratos"], t["buscar_pratos"]]
        tools_gestor = [x for x in tools_gestor if x]
    if db.get("historico"):
        tools_gestor.append(db["historico"])
    # Nutri
    tools_nutri = [t["recuperar_regras"], t["ler_contexto"], t["listar_pratos"], t["buscar_pratos"], t["calcular_custo"], t["sazonalidade"], t["enviar_msg"]]
    if db.get("fichas_banco"):
        tools_nutri.insert(0, db["fichas_banco"])
    if db.get("contexto_semantico"):
        tools_nutri.insert(1 if db.get("fichas_banco") else 0, db["contexto_semantico"])
    # Analista nutricional
    tools_an = [t["validar_nutri"], t["recuperar_regras"], t["ler_contexto"], t["enviar_msg"]]
    if db.get("fichas_banco"):
        tools_an.insert(0, db["fichas_banco"])
    # Controller
    tools_fin = [t["calcular_custo"], t["recuperar_regras"], t["ler_contexto"], t["enviar_msg"]]
    if db.get("fichas_banco"):
        tools_fin.insert(0, db["fichas_banco"])
    # Compras
    tools_compras = [t["ler_contexto"], t["enviar_msg"]]
    if db.get("lista_compras"):
        tools_compras.insert(0, db["lista_compras"])
    return [tools_analista, tools_gestor, tools_nutri, tools_an, tools_fin, tools_compras, []]


# Rótulos estáticos alinhados ao fluxo de 7 etapas (única lista para build_steps + meta admin).
_PIPELINE_STEP_LABELS: tuple[str, ...] = (
    "Analista de Contratos e Regras de Negócio",
    "Gestor de Fichas Técnicas e Repertório de Pratos",
    "Nutricionista Planejadora de Cardápios Coletivos",
    "Analista Nutricional e de Conformidade Regulatória",
    "Controller Financeiro de Custos de Alimentação",
    "Agente de Compras e Gestão de Insumos",
    "Exportador e Consolidador de Cardápios",
)


def pipeline_step_meta_labels() -> List[dict]:
    """Passos do pipeline (ordem + label), sem prompts nem ferramentas."""
    return [{"ordem": i + 1, "label": lab} for i, lab in enumerate(_PIPELINE_STEP_LABELS)]


def _refeicoes_block(crew) -> str:
    """Gera bloco de texto com as refeições selecionadas para o cardápio."""
    refeicoes = getattr(crew, "ctx", None) and getattr(crew.ctx, "refeicoes", None)
    if not refeicoes:
        return "Refeições: almoço (padrão)."
    nomes = {
        "cafe_manha": "café da manhã",
        "lanche_manha": "lanche da manhã",
        "almoco": "almoço",
        "lanche_tarde": "lanche da tarde",
        "jantar": "jantar",
        "ceia": "ceia",
    }
    lista = [nomes.get(r, r) for r in refeicoes]
    return f"Refeições a planejar: {', '.join(lista)}."


def _system_short(label: str, d: int, tc: float, tcp: float, fonte: str, ref_block: str = "") -> str:
    return (
        f"{label}\n\n"
        f"Contexto: cardápio de {d} dias, custo-alvo total R${tc:.2f}, proteína R${tcp:.2f}.\n"
        f"{ref_block}\n"
        f"Fonte de dados de pratos: {fonte}\n"
        "Regras: use apenas as ferramentas disponíveis; não invente códigos ou custos. "
        "Cite o resultado das ferramentas quando aplicável."
    )


def build_steps(crew) -> List[PipelineStep]:
    """Monta 7 passos; crew deve ter _configurar_tools já chamado."""
    d = crew.dias
    tc = crew.target_custo_total
    tcp = crew.target_custo_proteico
    ctx_r = crew.ctx.resumo_para_agente
    toolsets = _build_tool_lists(crew)
    fonte = _fonte(crew)
    ref_block = _refeicoes_block(crew)
    refeicoes = getattr(crew, "ctx", None) and getattr(crew.ctx, "refeicoes", None)
    ref_lista = refeicoes if refeicoes else ["almoco"]

    # 1
    ref_rules = (
        "   - Regras específicas por refeição (café da manhã, almoço, jantar, etc.) se houver\n"
        if len(ref_lista) > 1 else ""
    )
    u1 = (
        f"{ctx_r('Analista de Contratos')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Leia o documento do cliente (contrato, proposta tecnica/comercial ou edital de licitacao) e extraia TODAS as regras de cardápio. {ref_block}\n\n"
        "PASSOS OBRIGATÓRIOS — execute TODOS na ordem:\n"
        "1. Chame 'Ler Contrato (Arquivo PDF/XLSX/DOCX/TXT)' para obter o texto completo.\n"
        "2. Leia o documento INTEIRO com atenção a:\n"
        "   - Frequência de cada proteína por semana (bovina, suína, frango, peixe, ovo, etc.)\n"
        "   - Ingredientes proibidos ou vetados\n"
        "   - Estrutura da bandeja (quantas proteínas, guarnições, saladas, sobremesas)\n"
        "   - Gramaturas por categoria (g)\n"
        "   - Alergênicos a evitar (ANVISA RDC 26/2015)\n"
        "   - Dietas especiais (vegetariano, vegano, sem glúten, diabéticos)\n"
        "   - Sazonalidade ou exigências de ingredientes regionais/orgânicos\n"
        f"{ref_rules}"
        "   - Qualquer outra regra operacional (dias de cardápio, horários, etc.)\n"
        "3. Se a ferramenta retornar '[ERRO_CONTRATO_SEM_TEXTO]', interrompa a analise e solicite reenvio do arquivo. NUNCA invente defaults nesse caso.\n"
        "4. Se alguma regra pontual nao estiver explicita, aplique boas praticas do setor apenas nessa lacuna.\n"
        f"5. Monte o JSON completo (veja formato abaixo) para {d} dias de cardápio.\n"
        "6. Chame 'Salvar Regras Extraídas do Contrato' com o JSON.\n"
        "7. Confirme o salvamento com 'Recuperar Regras do Contrato'.\n"
        "8. Envie relatório ao Coordenador via 'Enviar Relatório ao Coordenador'.\n\n"
        "FORMATO DO JSON (preencha todos os campos, adicione outros se necessário):\n"
        "```json\n"
        "{\n"
        '  "incidencias": {"carne_bovina": "3x/semana", "frango": "2x/semana", "peixe": "1x/semana"},\n'
        '  "proibicoes": ["carne_suina", "frutos_do_mar"],\n'
        '  "estrutura": {"prato_proteico": 1, "opcao_proteica": 1, "guarnicao": 2, "salada": 2, "sobremesa": 0},\n'
        '  "gramaturas": {"proteico": "120g", "guarnicao": "80g", "salada": "60g"},\n'
        '  "restricoes_alergenos": [],\n'
        '  "dietas_especiais": [],\n'
        '  "sazonalidade_obrigatoria": false,\n'
        '  "observacoes": "outras regras do contrato"\n'
        "}\n"
        "```\n\n"
        "IMPORTANTE: O JSON deve refletir o que está NO CONTRATO, não defaults genéricos.\n"
        "Quanto mais fiel ao documento, melhor será o cardápio gerado."
    )
    u2 = (
        f"{ctx_r('Gestor de Fichas')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Mapeie o repertório de pratos disponíveis para este cardápio. {ref_block}\n\n"
        "PASSOS:\n"
        "1. Leia o contexto para conhecer as restrições do contrato.\n"
        "2. Consulte as fichas técnicas disponíveis (banco ou base legada).\n"
        "2.1 Quando a busca exata não for suficiente, recupere repertório com busca semântica.\n"
        "3. Filtre os pratos que atendem as restrições (proibições, alergênicos).\n"
        "4. Verifique o histórico de cardápios para identificar pratos recentes.\n"
        "5. Entregue um catálogo organizado por categoria com código, nome e custo.\n\n"
        "ORGANIZE A SAÍDA EM SEÇÕES:\n"
        "  PROTEÍNAS DISPONÍVEIS (com custo por porção)\n"
        "  GUARNIÇÕES DISPONÍVEIS\n"
        "  SALADAS DISPONÍVEIS\n"
        "  SOBREMESAS/FRUTAS (se aplicável)\n\n"
        "Sinalize quais pratos foram usados recentemente (para o Nutricionista evitar)."
    )
    # Nutricionista — formato de saída adapta conforme número de refeições
    fmt_cols = "| Dia | Refeição | Categoria | Código | Prato | Custo (R$) |" if len(ref_lista) > 1 else "| Dia | Categoria | Código | Prato | Custo (R$) |"
    custo_msg = (
        f"7. O Preço Unitário (PU) ALVO total da refeição é RIGOROSAMENTE R${tc:.2f} e proteico R${tcp:.2f} POR REFEIÇÃO.\n"
        "   Se não for possível atingir o PU exato com as fichas disponíveis, componha o cardápio mais próximo possível desse valor e gere uma justificativa clara detalhando o motivo (ex: custo base dos ingredientes indisponível nesse preço).\n"
        if len(ref_lista) > 1 else
        f"7. O Preço Unitário (PU) ALVO total da refeição é RIGOROSAMENTE R${tc:.2f} e proteico R${tcp:.2f}.\n"
        "   Se não for possível atingir o PU exato com as fichas disponíveis, componha o cardápio mais próximo possível desse valor e gere uma justificativa clara detalhando o motivo (ex: custo base dos ingredientes indisponível nesse preço).\n"
    )
    u3 = (
        f"{ctx_r('Nutricionista')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Monte o cardápio completo de {d} dias. {ref_block}\n\n"
        "PASSOS:\n"
        "1. Leia o contexto para verificar se há feedbacks de iterações anteriores.\n"
        "2. Recupere as regras do contrato.\n"
        "2.1 Use busca semântica para recuperar fichas, regras e cardápios similares quando houver ambiguidade.\n"
        "3. Use o catálogo fornecido pelo Gestor de Fichas.\n"
        "4. Para CADA dia e CADA refeição selecionada, selecione os pratos conforme a estrutura do contrato.\n"
        "   • Exemplo: se o contrato prevê café da manhã + almoço + jantar, monte as 3 refeições para cada dia.\n"
        "   • A estrutura da bandeja (proteico, guarnição, salada) aplica-se principalmente ao almoço/jantar.\n"
        "   • Para café da manhã/lanches/ceia, adapte a estrutura (pães, frutas, laticínios, cereais).\n"
        "5. Verifique sazonalidade dos ingredientes quando relevante.\n"
        "6. Calcule o custo estimado de cada prato antes de incluir. "
        "Passe 'gramatura_alvo_g' ao buscar custos se o contrato especificar gramatura diferente do padrão da ficha.\n"
        f"{custo_msg}"
        "ATENÇÃO ESPECIAL:\n"
        "  • Se for iteração de correção, corrija APENAS os dias sinalizados pelo Controller.\n"
        "  • Varie proteínas: bovina, suína, frango, peixe, ovos, leguminosas.\n"
        "  • Considere a técnica de preparo na variação (grelhado ≠ ensopado).\n"
        "  • Evite repetir o mesmo prato em dias consecutivos para a MESMA refeição.\n\n"
        "FORMATO DE SAÍDA:\n"
        f"{fmt_cols}"
    )
    u4 = (
        f"{ctx_r('Analista Nutricional')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Valide a conformidade nutricional do cardápio proposto. {ref_block}\n\n"
        "PASSOS:\n"
        "1. Analise o cardápio da Nutricionista (no contexto abaixo).\n"
        "2. Para cada refeição, valide o VET e o equilíbrio nutricional.\n"
        "3. Para fichas com dados nutricionais: calcule o VET de cada refeição.\n"
        "4. Use 'Validar Conformidade Nutricional' para os principais dias.\n"
        "5. Verifique variedade de grupos alimentares ao longo da semana POR REFEIÇÃO.\n"
        "6. Verifique conformidade com alergênicos do contrato.\n\n"
        "RESULTADO:\n"
        "  Se APROVADO → resumo. Se REPROVADO → o que o Nutricionista deve corrigir (dia + refeição)."
    )
    u5 = (
        f"{ctx_r('Controller Financeiro')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Valide os custos do cardápio proposto (veja o contexto). {ref_block}\n\n"
        f"COMPARE RIGOROSAMENTE com o Preço Unitário (PU) Alvo: total de R${tc:.2f} | proteico de R${tcp:.2f} POR REFEIÇÃO.\n"
        "O PU não é apenas uma estimativa, é um limite rígido. Verifique se as justificativas do Nutricionista detalham claramente o motivo (ex: custo base) caso o PU não seja atingido exatamente.\n"
        "Documente aprovação ou aponte dias/refeições problema, exigindo correções ou substituições específicas para cravar o PU alvo."
    )
    u6 = (
        f"{ctx_r('Agente de Compras')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Gere a lista de compras para o cardápio aprovado. {ref_block} Use ferramentas do banco se houver."
    )
    u7 = (
        f"{ctx_r('Exportador')}\n\n"
        "=== SUA TAREFA ===\n"
        f"Consolide o documento final em markdown: cardápio tabela (com coluna Refeição), resumo executivo, análise nutricional, lista de compras, decisões. {ref_block}"
    )
    users = [u1, u2, u3, u4, u5, u6, u7]
    labels = list(_PIPELINE_STEP_LABELS)
    system_overrides = getattr(crew, "step_system_overrides", {}) or {}
    steps: List[PipelineStep] = []
    for idx, (lab, user, tols) in enumerate(zip(labels, users, toolsets, strict=True)):
        system = system_overrides.get(idx) or _system_short(lab, d, tc, tcp, fonte, ref_block)
        steps.append(
            PipelineStep(
                label=lab,
                system=system,
                user=user,
                tools=tols,
            )
        )
    return steps
