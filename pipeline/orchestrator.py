"""
Menu.AI — Pipeline de geração de cardápios v3.0

Sete etapas sequenciais (Analista de Contratos → … → Exportador) com ferramentas
reais (banco de fichas técnicas) e LiteLLM — orquestrador LangChain/LiteLLM.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from pipeline.protocolo import SharedContext


class MenuOrchestrator:
    """
    Orquestrador de geração de cardápios: ferramentas + pipeline sequencial (LiteLLM).
    """

    def __init__(
        self,
        contrato_path: Optional[str] = None,
        dias: int = 30,
        target_custo_total: float = 10.00,
        target_custo_proteico: float = 3.50,
        restricoes_usuario: str = "",
        refeicoes: Optional[List[str]] = None,
        empresa_id: Optional[str] = None,
        contrato_id: Optional[str] = None,
        task_callback: Optional[Callable] = None,
        step_callback: Optional[Callable] = None,
        db_disponivel: bool = False,
        llm_model_id: Optional[str] = None,
    ):
        self.contrato_path = contrato_path
        self.dias = dias
        self.target_custo_total = target_custo_total
        self.target_custo_proteico = target_custo_proteico
        self.restricoes_usuario = restricoes_usuario
        self.empresa_id = empresa_id
        self.contrato_id = contrato_id
        self.task_callback = task_callback
        self.step_callback = step_callback
        self.db_disponivel = db_disponivel
        self.llm_model_id = llm_model_id
        self.llm_model_label = None
        self.llm = None  # legado: execução via pipeline.llm_litellm

        from pipeline.llm_litellm import get_litellm_config

        cfg = get_litellm_config(model_override=llm_model_id)  # valida .env e imprime modelo
        self.llm_model_id = cfg.model_id or llm_model_id
        self.llm_model_label = cfg.model_label or self.llm_model_id

        self.ctx = SharedContext()
        self.ctx.dias = dias
        self.ctx.target_custo_total = target_custo_total
        self.ctx.target_custo_proteico = target_custo_proteico
        self.ctx.restricoes_usuario = restricoes_usuario
        self.ctx.refeicoes = refeicoes
        self.ctx.empresa_id = empresa_id
        self.ctx.contrato_id = contrato_id

    def _configurar_tools(self) -> None:
        """Injeta configurações globais em todas as ferramentas."""
        import tools.cardapio_tools as ct
        ct.CONTRATO_PATH = self.contrato_path
        ct.DIAS = self.dias
        ct.TARGET_CUSTO_TOTAL = self.target_custo_total
        ct.TARGET_CUSTO_PROTEICO = self.target_custo_proteico
        ct.RESTRICOES_USUARIO = self.restricoes_usuario
        ct._ctx = self.ctx

        if self.db_disponivel:
            import tools.db_tools as dt
            dt.EMPRESA_ID = self.empresa_id
            dt.CONTRATO_ID = self.contrato_id
            dt.DB_AVAILABLE = True

    def _get_tools_base(self):
        """Ferramentas da base de receitas (sempre disponíveis)."""
        import tools.cardapio_tools as ct
        return {
            "listar_pratos": ct.listar_pratos_por_categoria,
            "buscar_pratos": ct.buscar_pratos,
            "calcular_custo": ct.calcular_custo_prato,
            "ler_contrato": ct.ler_regras_contrato,
            "salvar_regras": ct.salvar_regras_extraidas,
            "recuperar_regras": ct.recuperar_regras_contrato,
            "sazonalidade": ct.verificar_sazonalidade,
            "validar_nutri": ct.validar_nutricional,
            "enviar_msg": ct.enviar_relatorio_coordenador,
            "ler_contexto": ct.ler_contexto_atual,
        }

    def _get_tools_db(self):
        """Ferramentas do banco (condicionais ao DB_AVAILABLE)."""
        if not self.db_disponivel:
            return {}
        try:
            import tools.db_tools as dt
            return {
                "fichas_banco": dt.consultar_fichas_tecnicas,
                "detalhe_ficha": dt.detalhe_ficha_tecnica,
                "contrato_banco": dt.consultar_contrato_banco,
                "contexto_semantico": dt.buscar_contexto_semantico,
                "historico": dt.historico_cardapios,
                "lista_compras": dt.gerar_lista_compras,
            }
        except Exception as e:
            print(f"⚠️  Tools do banco indisponíveis: {e}")
            return {}

    def analisar_contrato_apenas(self) -> dict:
        """
        Executa APENAS a etapa 1 (análise do contrato) e retorna as regras extraídas.
        Usado no fluxo human-in-the-loop para permitir revisão antes de continuar.
        """
        from pipeline.litellm_runner import run_lite_pipeline_step

        self._configurar_tools()
        tools_all = {**self._get_tools_base(), **self._get_tools_db()}

        try:
            resultado = run_lite_pipeline_step(
                orchestrator=self,
                step_index=0,  # Etapa 1: Analista de Contratos
                tools=tools_all,
            )
            # Retorna as regras extraídas do contexto
            return self.ctx.regras_contrato or {"texto": str(resultado)[:2000]}
        except Exception as e:
            return {"erro": str(e)}

    def aplicar_ajustes_usuario(self, ajustes: str) -> None:
        """
        Aplica ajustes textuais do usuário ao contexto compartilhado.
        Chamado após confirmação human-in-the-loop.
        """
        if ajustes:
            # Adiciona restrições do usuário ao contexto
            if self.ctx.restricoes_usuario:
                self.ctx.restricoes_usuario += f"\n\n=== AJUSTES DO CLIENTE (pós-análise) ===\n{ajustes}"
            else:
                self.ctx.restricoes_usuario = f"=== AJUSTES DO CLIENTE ===\n{ajustes}"
            self.restricoes_usuario = self.ctx.restricoes_usuario

    def run(self) -> str:
        """Executa o pipeline sequencial e retorna o cardápio final consolidado."""
        from pipeline.litellm_runner import run_lite_pipeline

        return run_lite_pipeline(self)
