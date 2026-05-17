"""
Menu.AI — Schemas Pydantic para validação de API

Padrão de nomes:
  XxxBase     — campos comuns (leitura + escrita)
  XxxCreate   — campos obrigatórios para criação (POST)
  XxxUpdate   — campos opcionais para atualização (PATCH)
  XxxOut      — resposta da API (inclui id, timestamps)
  XxxDetalhado — resposta expandida com relacionamentos
"""
from datetime import datetime, date
from typing import Optional, List, Any, Dict, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator, model_validator


# ============================================================
# EMPRESA
# ============================================================
class EmpresaBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    cnpj: Optional[str] = Field(None, pattern=r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$")
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    logo_url: Optional[str] = None
    segmento: Optional[str] = None
    num_comensais: Optional[int] = Field(None, ge=1)


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    cnpj: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    logo_url: Optional[str] = None
    segmento: Optional[str] = None
    num_comensais: Optional[int] = None
    ativo: Optional[bool] = None


class EmpresaOut(EmpresaBase):
    id: str
    ativo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# USUÁRIO
# ============================================================
class UsuarioBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    role: str = Field(default="nutricionista",
                      pattern=r"^(super_admin|admin|nutricionista|gestor|visualizador)$")


class UsuarioCreate(UsuarioBase):
    empresa_id: str
    senha: str = Field(..., min_length=6)


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    senha: Optional[str] = Field(None, min_length=6)
    ativo: Optional[bool] = None


class UsuarioOut(UsuarioBase):
    id: str
    empresa_id: str
    ativo: bool
    ultimo_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# AUTH
# ============================================================
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ============================================================
# CONTRATO
# ============================================================
class EstruturaRefeicao(BaseModel):
    proteico: int = 1
    opcao: int = 1
    guarnicao: int = 2
    salada: int = 3
    sobremesa: int = 0
    fruta: int = 0


class ContratoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    numero_contrato: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    custo_total_max: float = Field(default=10.00, ge=0)
    custo_proteico_max: float = Field(default=3.50, ge=0)
    num_refeicoes_dia: int = Field(default=1, ge=1, le=6)
    estrutura_refeicao: Optional[Dict[str, Any]] = None
    gramaturas_json: Optional[Dict[str, Any]] = None
    incidencias_json: Optional[Dict[str, Any]] = None
    proibicoes_json: Optional[List[str]] = None
    observacoes: Optional[str] = None


class ContratoCreate(ContratoBase):
    empresa_id: str


class ContratoUpdate(BaseModel):
    nome: Optional[str] = None
    numero_contrato: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    custo_total_max: Optional[float] = None
    custo_proteico_max: Optional[float] = None
    num_refeicoes_dia: Optional[int] = None
    estrutura_refeicao: Optional[Dict[str, Any]] = None
    gramaturas_json: Optional[Dict[str, Any]] = None
    incidencias_json: Optional[Dict[str, Any]] = None
    proibicoes_json: Optional[List[str]] = None
    observacoes: Optional[str] = None
    regras_json: Optional[Dict[str, Any]] = None
    ativo: Optional[bool] = None


class ContratoOut(ContratoBase):
    id: str
    empresa_id: str
    arquivo_path: Optional[str] = None
    regras_json: Optional[Dict[str, Any]] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# INGREDIENTE
# ============================================================
class IngredienteBase(BaseModel):
    codigo: Optional[str] = None
    nome: str = Field(..., min_length=2, max_length=200)
    nome_cientifico: Optional[str] = None
    unidade_medida: str = Field(default="kg",
                                 pattern=r"^(kg|g|L|ml|un|cx|pct)$")
    custo_unitario: float = Field(..., ge=0)
    fornecedor: Optional[str] = None
    fator_correcao: float = Field(default=1.0, ge=1.0)
    calorias_100g: Optional[float] = Field(None, ge=0)
    proteina_100g: Optional[float] = Field(None, ge=0)
    carboidrato_100g: Optional[float] = Field(None, ge=0)
    gordura_100g: Optional[float] = Field(None, ge=0)
    fibra_100g: Optional[float] = Field(None, ge=0)
    sodio_100g: Optional[float] = Field(None, ge=0)
    alergeno: bool = False
    tipo_alergeno: Optional[str] = None
    meses_safra: Optional[List[int]] = None
    categoria: str = Field(default="OUTRO",
                            pattern=r"^(PROTEINA|CARBOIDRATO|HORTALICA|FRUTA|LATICINIOS|GORDURA|CONDIMENTO|BEBIDA|OUTRO)$")


class IngredienteCreate(IngredienteBase):
    empresa_id: Optional[str] = None   # None = ingrediente global


class IngredienteUpdate(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    unidade_medida: Optional[str] = None
    custo_unitario: Optional[float] = None
    fornecedor: Optional[str] = None
    fator_correcao: Optional[float] = None
    calorias_100g: Optional[float] = None
    proteina_100g: Optional[float] = None
    carboidrato_100g: Optional[float] = None
    gordura_100g: Optional[float] = None
    alergeno: Optional[bool] = None
    tipo_alergeno: Optional[str] = None
    meses_safra: Optional[List[int]] = None
    categoria: Optional[str] = None
    custo_unitario: Optional[float] = None
    ativo: Optional[bool] = None


class IngredienteOut(IngredienteBase):
    id: str
    empresa_id: Optional[str] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# FICHA TÉCNICA — INGREDIENTE (item da ficha)
# ============================================================
class FichaIngredienteBase(BaseModel):
    ingrediente_id: str
    quantidade_bruta_g: float = Field(..., gt=0)
    fator_correcao: float = Field(default=1.0, ge=1.0)
    ordem: int = Field(default=0, ge=0)
    observacao: Optional[str] = None


class FichaIngredienteCreate(FichaIngredienteBase):
    pass


class FichaIngredienteOut(FichaIngredienteBase):
    id: str
    ficha_tecnica_id: str
    quantidade_liquida_g: Optional[float] = None
    custo_calculado: float
    ingrediente: Optional[IngredienteOut] = None

    class Config:
        from_attributes = True


# ============================================================
# FICHA TÉCNICA
# ============================================================
class FichaTecnicaBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    nome: str = Field(..., min_length=2, max_length=300)
    categoria: str = Field(..., min_length=2, max_length=100)
    rendimento_porcoes: int = Field(..., ge=1)
    peso_porcao_g: Optional[float] = Field(None, ge=0)
    tempo_preparo_min: Optional[int] = Field(None, ge=0)
    modo_preparo: Optional[str] = None
    equipamento: Optional[str] = None
    dificuldade: str = Field(default="medio", pattern=r"^(facil|medio|dificil)$")
    temperatura_servico: Optional[str] = None
    contem_gluten: bool = False
    contem_lactose: bool = False
    vegana: bool = False
    vegetariana: bool = False
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None


class FichaTecnicaCreate(FichaTecnicaBase):
    empresa_id: str
    ingredientes: List[FichaIngredienteCreate] = []


class FichaTecnicaUpdate(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    rendimento_porcoes: Optional[int] = None
    peso_porcao_g: Optional[float] = None
    tempo_preparo_min: Optional[int] = None
    modo_preparo: Optional[str] = None
    equipamento: Optional[str] = None
    dificuldade: Optional[str] = None
    temperatura_servico: Optional[str] = None
    contem_gluten: Optional[bool] = None
    contem_lactose: Optional[bool] = None
    vegana: Optional[bool] = None
    vegetariana: Optional[bool] = None
    observacoes: Optional[str] = None
    foto_url: Optional[str] = None
    ativo: Optional[bool] = None
    ingredientes: Optional[List[FichaIngredienteCreate]] = None


class FichaTecnicaOut(FichaTecnicaBase):
    id: str
    empresa_id: str
    custo_total: float
    custo_porcao: float
    calorias_porcao: Optional[float] = None
    proteina_porcao: Optional[float] = None
    carboidrato_porcao: Optional[float] = None
    gordura_porcao: Optional[float] = None
    sodio_porcao: Optional[float] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FichaTecnicaDetalhada(FichaTecnicaOut):
    ingredientes_ficha: List[FichaIngredienteOut] = []

    class Config:
        from_attributes = True


# ============================================================
# CARDÁPIO
# ============================================================
class CardapioRefeicaoCreate(BaseModel):
    tipo_refeicao: str = Field(default="almoco",
                                pattern=r"^(cafe_manha|lanche_manha|almoco|lanche_tarde|jantar|ceia)$")
    categoria: Optional[str] = None
    codigo_prato: Optional[str] = None
    nome_prato: str
    custo_porcao: float = Field(default=0.0, ge=0)
    ficha_tecnica_id: Optional[str] = None
    observacoes: Optional[str] = None
    ordem: int = 0


class CardapioRefeicaoOut(CardapioRefeicaoCreate):
    id: str
    dia_id: str

    class Config:
        from_attributes = True


class CardapioDiaCreate(BaseModel):
    numero_dia: int = Field(..., ge=1)
    data: Optional[date] = None
    dia_semana: Optional[int] = Field(None, ge=0, le=6)
    observacoes: Optional[str] = None
    refeicoes: List[CardapioRefeicaoCreate] = []


class CardapioDiaOut(CardapioDiaCreate):
    id: str
    cardapio_id: str
    custo_total: float
    refeicoes: List[CardapioRefeicaoOut] = []

    class Config:
        from_attributes = True


class CardapioBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    observacoes: Optional[str] = None


class CardapioCreate(CardapioBase):
    empresa_id: str
    contrato_id: Optional[str] = None
    parametros_json: Optional[Dict[str, Any]] = None


class CardapioUpdate(BaseModel):
    nome: Optional[str] = None
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None
    resultado_raw: Optional[str] = None
    custo_medio_dia: Optional[float] = None


class CardapioOut(CardapioBase):
    id: str
    empresa_id: str
    contrato_id: Optional[str] = None
    criado_por_id: Optional[str] = None
    status: str
    custo_medio_dia: Optional[float] = None
    num_dias: Optional[int] = None
    job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CardapioDetalhado(CardapioOut):
    dias: List[CardapioDiaOut] = []

    class Config:
        from_attributes = True


# ============================================================
# APROVAÇÃO
# ============================================================
class AprovacaoCreate(BaseModel):
    cardapio_id: str
    status: str = Field(..., pattern=r"^(aprovado|reprovado|solicitado_revisao)$")
    comentario: Optional[str] = None


class AprovacaoOut(AprovacaoCreate):
    id: str
    aprovado_por_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# JOB AGENTE
# ============================================================
LlmModelId = Literal[
    "openai-gpt-5.5",
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "queen-3.6",
    "glm-5-1",
    "kimi-k2.5",
]


class GerarCardapioRequest(BaseModel):
    """Request para geração via agentes IA."""
    empresa_id: Optional[str] = Field(
        default=None,
        description="Opcional no JSON: o servidor preenche a partir do JWT (utilizador.empresa_id) se omitido.",
    )
    contrato_id: Optional[str] = None
    dias: int = Field(default=30, ge=1, le=366)
    target_custo_total: float = Field(default=10.00, ge=0)
    target_custo_proteico: float = Field(default=3.50, ge=0)
    restricoes_usuario: str = ""
    refeicoes: Optional[List[str]] = Field(
        default=None,
        description="Lista de refeições a incluir: cafe_manha, lanche_manha, almoco, lanche_tarde, jantar, ceia",
    )
    nome_cardapio: Optional[str] = None
    llm_model: Optional[LlmModelId] = Field(
        default=None,
        description="Modelo LLM (id interno). Omitir usa MENUAI_DEFAULT_LLM_MODEL ou openai-gpt-5.5.",
    )
    contrato_analise_confirmada: bool = Field(
        default=False,
        description="True quando a análise do contrato já foi revisada/confirmada antes de iniciar a geração.",
    )


class JobAgenteOut(BaseModel):
    id: str
    job_id: str
    status: str
    progresso: int
    empresa_id: Optional[str] = None
    cardapio_id: Optional[str] = None
    parametros_json: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None
    iniciado_em: datetime
    concluido_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# RESPOSTAS PAGINADAS
# ============================================================
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int

# ============================================================
# CHAT CONVERSACIONAL (HITL)
# ============================================================
class MensagemChatBase(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|system|tool)$")
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class MensagemChatCreate(MensagemChatBase):
    sessao_id: str


class MensagemChatOut(MensagemChatBase):
    id: str
    sessao_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessaoChatBase(BaseModel):
    titulo: Optional[str] = None
    status: str = Field(default="ativa", pattern=r"^(ativa|concluida|arquivada)$")


class SessaoChatCreate(SessaoChatBase):
    job_id: Optional[str] = None
    contexto_json: Optional[Dict[str, Any]] = None


class SessaoChatOut(SessaoChatBase):
    id: str
    usuario_id: str
    job_id: Optional[str] = None
    contexto_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessaoChatDetalhada(SessaoChatOut):
    mensagens: List[MensagemChatOut] = []

    class Config:
        from_attributes = True


class NovaMensagemRequest(BaseModel):
    content: str
    metadata_json: Optional[Dict[str, Any]] = None
