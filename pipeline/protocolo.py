"""
Menu.AI — Protocolo de Comunicação entre Agentes

Define a linguagem estruturada que os agentes usam para se comunicar
com o Coordenador e entre si. Cada mensagem tem tipo, remetente,
conteúdo e um flag indicando se requer decisão do Coordenador.

Fluxo:
  Agente → emit_message() → SharedContext.inbox → Coordenador lê → decide próximo passo
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================
# Tipos de Mensagem
# ============================================================

class TipoMensagem(str, Enum):
    # Agente concluiu sua tarefa com sucesso
    RELATORIO      = "relatorio"
    # Agente encontrou um problema e precisa de instrução
    ALERTA         = "alerta"
    # Agente pede ao Coordenador que redistribua uma tarefa
    SOLICITACAO    = "solicitacao"
    # Agente aprova o trabalho de outro
    APROVACAO      = "aprovacao"
    # Agente reprova e devolve com instrução
    REPROVACAO     = "reprovacao"
    # Agente pede mais contexto ou dados
    CONSULTA       = "consulta"
    # Coordenador emite uma instrução direta a um agente
    INSTRUCAO      = "instrucao"


class StatusTarefa(str, Enum):
    PENDENTE       = "pendente"
    EM_ANDAMENTO   = "em_andamento"
    CONCLUIDA      = "concluida"
    REPROVADA      = "reprovada"
    BLOQUEADA      = "bloqueada"


# ============================================================
# Estrutura de Mensagem
# ============================================================

@dataclass
class AgentMessage:
    """
    Mensagem estruturada trocada entre agentes.

    Exemplo:
        msg = AgentMessage(
            de="Nutricionista",
            para="Coordenador",
            tipo=TipoMensagem.ALERTA,
            conteudo="3 dias do cardápio ultrapassaram o custo-alvo.",
            dados={"dias_problema": [5, 12, 18]},
            requer_decisao=True,
        )
    """
    de:              str
    para:            str
    tipo:            TipoMensagem
    conteudo:        str
    dados:           Dict[str, Any] = field(default_factory=dict)
    requer_decisao:  bool = False
    iteracao:        int  = 1
    timestamp:       str  = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_prompt(self) -> str:
        """Serializa a mensagem em formato legível para o LLM."""
        linhas = [
            f"[MENSAGEM DE {self.de.upper()} → {self.para.upper()}]",
            f"Tipo: {self.tipo.value.upper()}",
            f"Iteração: {self.iteracao}",
            f"",
            self.conteudo,
        ]
        if self.dados:
            linhas += ["", "Dados estruturados:", json.dumps(self.dados, ensure_ascii=False, indent=2)]
        if self.requer_decisao:
            linhas += ["", "⚠️ REQUER DECISÃO DO COORDENADOR"]
        return "\n".join(linhas)

    @classmethod
    def from_json(cls, raw: str) -> "AgentMessage":
        d = json.loads(raw)
        d["tipo"] = TipoMensagem(d["tipo"])
        return cls(**d)


# ============================================================
# Contexto Compartilhado entre Agentes
# ============================================================

class SharedContext:
    """
    Memória compartilhada que persiste durante toda a execução da crew.
    O Coordenador lê e escreve neste contexto para tomar decisões.
    Cada agente pode consultar o contexto antes de agir.
    """

    def __init__(self):
        # Parâmetros da sessão
        self.dias: int = 30
        self.target_custo_total: float = 10.00
        self.target_custo_proteico: float = 3.50
        self.restricoes_usuario: str = ""
        self.refeicoes: Optional[List[str]] = None
        self.empresa_id: Optional[str] = None
        self.contrato_id: Optional[str] = None

        # Estado das etapas
        self.etapa_atual: str = "inicializando"
        self.iteracao: int = 1
        self.max_iteracoes: int = 3   # máximo de tentativas de ajuste

        # Dados extraídos e gerados
        self.regras_contrato:   Dict[str, Any] = {}   # saída do Analista
        self.fichas_disponiveis: List[Dict] = []       # saída do Gestor de Fichas
        self.cardapio_proposto:  str = ""              # saída do Nutricionista
        self.validacao_nutricional: Dict = {}          # saída do Analista Nutricional
        self.validacao_financeira:  Dict = {}          # saída do Controller
        self.lista_compras:         Dict = {}          # saída do Agente de Compras
        self.cardapio_final:        str = ""           # saída do Exportador

        # Inbox de mensagens (fila para o Coordenador)
        self._inbox: List[AgentMessage] = []
        self._historico: List[AgentMessage] = []

        # Decisões do Coordenador
        self.decisoes_coordenador: List[Dict] = []

        # Flags de controle
        self.cardapio_aprovado: bool = False
        self.financeiro_ok:     bool = False
        self.nutricional_ok:    bool = False
        self.erros:             List[str] = []
        self.alertas:           List[str] = []

    # ----------------------------------------------------------
    def emit(self, msg: AgentMessage) -> None:
        """Agente envia mensagem para a caixa de entrada."""
        msg.iteracao = self.iteracao
        self._inbox.append(msg)
        self._historico.append(msg)

    def ler_inbox(self) -> List[AgentMessage]:
        """Coordenador lê e esvazia a caixa de entrada."""
        msgs = list(self._inbox)
        self._inbox.clear()
        return msgs

    def decisao(self, instrucao: str, para: str, dados: Dict = None) -> AgentMessage:
        """Coordenador emite instrução para um agente."""
        msg = AgentMessage(
            de="Coordenador",
            para=para,
            tipo=TipoMensagem.INSTRUCAO,
            conteudo=instrucao,
            dados=dados or {},
            iteracao=self.iteracao,
        )
        self._historico.append(msg)
        self.decisoes_coordenador.append({"para": para, "instrucao": instrucao, "iteracao": self.iteracao})
        return msg

    # ----------------------------------------------------------
    def resumo_para_agente(self, nome_agente: str) -> str:
        """
        Gera um bloco de contexto resumido para o agente ler antes de agir.
        Inclui apenas o que é relevante para cada agente.
        """
        linhas = [
            f"=== CONTEXTO COMPARTILHADO (Iteração {self.iteracao}/{self.max_iteracoes}) ===",
            f"Período: {self.dias} dias",
            f"Custo-alvo total: R$ {self.target_custo_total:.2f}/pessoa",
            f"Custo-alvo proteico: R$ {self.target_custo_proteico:.2f}/pessoa",
            f"Etapa atual: {self.etapa_atual}",
        ]

        if self.restricoes_usuario:
            linhas += ["", f"Restrições do cliente: {self.restricoes_usuario}"]

        if self.refeicoes:
            linhas += ["", f"Refeições a planejar: {', '.join(self.refeicoes)}"]

        if self.regras_contrato and nome_agente in (
            "Nutricionista", "Analista Nutricional", "Controller Financeiro", "Exportador"
        ):
            linhas += ["", "Regras do contrato já extraídas:", json.dumps(self.regras_contrato, ensure_ascii=False, indent=2)]

        if self.validacao_financeira and nome_agente == "Nutricionista" and not self.financeiro_ok:
            linhas += ["", "⚠️ FEEDBACK DO CONTROLLER FINANCEIRO (corrija antes de reenviar):"]
            linhas += [json.dumps(self.validacao_financeira, ensure_ascii=False, indent=2)]

        if self.validacao_nutricional and nome_agente == "Nutricionista" and not self.nutricional_ok:
            linhas += ["", "⚠️ FEEDBACK DO ANALISTA NUTRICIONAL:"]
            linhas += [json.dumps(self.validacao_nutricional, ensure_ascii=False, indent=2)]

        if self.alertas:
            linhas += ["", "⚠️ Alertas ativos: " + " | ".join(self.alertas)]

        # Mensagens dirigidas a este agente
        msgs_para_mim = [m for m in self._historico if m.para == nome_agente]
        if msgs_para_mim:
            ultima = msgs_para_mim[-1]
            linhas += ["", "--- Última instrução do Coordenador ---", ultima.to_prompt()]

        return "\n".join(linhas)

    def to_dict(self) -> Dict:
        """Serializa o contexto para salvar no banco."""
        return {
            "dias": self.dias,
            "target_custo_total": self.target_custo_total,
            "target_custo_proteico": self.target_custo_proteico,
            "etapa_atual": self.etapa_atual,
            "iteracao": self.iteracao,
            "regras_contrato": self.regras_contrato,
            "cardapio_aprovado": self.cardapio_aprovado,
            "financeiro_ok": self.financeiro_ok,
            "nutricional_ok": self.nutricional_ok,
            "erros": self.erros,
            "alertas": self.alertas,
            "num_decisoes_coordenador": len(self.decisoes_coordenador),
            "num_mensagens_trocadas": len(self._historico),
        }


# ============================================================
# Helpers para parsear saídas dos agentes
# ============================================================

def extrair_json_da_saida(texto: str) -> Optional[Dict]:
    """
    Tenta extrair um bloco JSON da saída de um agente.
    Agentes são instruídos a envolver JSON em ```json ... ```.
    """
    import re
    # Tenta bloco de código JSON
    match = re.search(r"```json\s*([\s\S]*?)\s*```", texto, re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Tenta JSON direto (primeiro { ... } do texto)
    match = re.search(r"\{[\s\S]*\}", texto)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def extrair_aprovacao(texto: str) -> bool:
    """Detecta se o agente aprovou (True) ou reprovou (False)."""
    texto_lower = texto.lower()
    aprovado_markers   = ["aprovado", "✅", "aprovada", "dentro do limite", "ok", "aceito"]
    reprovado_markers  = ["reprovado", "❌", "reprovada", "ultrapassou", "excedeu", "acima do limite"]

    score_ap = sum(1 for m in aprovado_markers  if m in texto_lower)
    score_rp = sum(1 for m in reprovado_markers if m in texto_lower)

    return score_ap >= score_rp


def formatar_instrucao_coordenador(contexto: SharedContext, para: str, motivo: str) -> str:
    """
    Gera instrução clara do Coordenador para um agente específico,
    incluindo contexto relevante e o que precisa ser corrigido.
    """
    base = contexto.resumo_para_agente(para)
    return f"{base}\n\n=== INSTRUÇÃO DO COORDENADOR ===\n{motivo}\n\nIteração atual: {contexto.iteracao}/{contexto.max_iteracoes}"
