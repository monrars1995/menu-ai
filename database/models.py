"""
Menu.AI — Models SQLAlchemy (ORM)

Tabelas:
  1.  empresas              — clientes/empresas contratantes
  2.  usuarios              — usuários com roles por empresa
  3.  contratos             — contratos de fornecimento de refeições
  4.  ingredientes          — insumos com custo real e fator de correção
  5.  fichas_tecnicas       — receitas com modo de preparo e dados nutricionais
  6.  ficha_ingredientes    — ingredientes por receita (tabela junction)
  7.  cardapios             — cardápios gerados (por empresa e período)
  8.  cardapio_dias         — dias individuais de um cardápio
  9.  cardapio_refeicoes    — pratos de cada dia
  10. aprovacoes_cardapio   — workflow de aprovação
  11. jobs_agente           — rastreamento de jobs dos agentes IA
"""
import os
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float,
    ForeignKey, Integer, String, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from database.connection import Base, IS_SQLITE

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # noqa: BLE001
    Vector = None


# ============================================================
# Helpers
# ============================================================
def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.utcnow()


_EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1536"))


def _vector_column(nullable: bool = True):
    if Vector is not None and not IS_SQLITE:
        return Column(Vector(_EMBEDDING_DIMENSION), nullable=nullable)
    return Column(JSON, nullable=nullable)


# ============================================================
# 1. EMPRESAS
# ============================================================
class Empresa(Base):
    __tablename__ = "empresas"

    id         = Column(String(36), primary_key=True, default=_uuid)
    nome       = Column(String(200), nullable=False, index=True)
    cnpj       = Column(String(18), unique=True, nullable=True)          # XX.XXX.XXX/XXXX-XX
    email      = Column(String(200), nullable=True)
    telefone   = Column(String(20), nullable=True)
    endereco   = Column(Text, nullable=True)
    logo_url   = Column(String(500), nullable=True)
    segmento   = Column(String(100), nullable=True)                      # industria, hospital, escola...
    num_comensais = Column(Integer, nullable=True)                        # número de refeições/dia
    ativo      = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    usuarios         = relationship("Usuario",        back_populates="empresa", cascade="all, delete-orphan")
    contratos        = relationship("Contrato",       back_populates="empresa", cascade="all, delete-orphan")
    ingredientes     = relationship("Ingrediente",    back_populates="empresa")
    fichas_tecnicas  = relationship("FichaTecnica",   back_populates="empresa", cascade="all, delete-orphan")
    cardapios        = relationship("Cardapio",       back_populates="empresa", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Empresa {self.nome}>"


# ============================================================
# 2. USUÁRIOS
# ============================================================
class RoleEnum:
    SUPER_ADMIN  = "super_admin"    # acesso total (Anthropic/plataforma)
    ADMIN        = "admin"           # admin da empresa
    NUTRICIONISTA = "nutricionista" # cria e edita cardápios/fichas
    GESTOR       = "gestor"          # aprova cardápios, vê relatórios
    VISUALIZADOR = "visualizador"    # somente leitura


class Usuario(Base):
    __tablename__ = "usuarios"

    id          = Column(String(36), primary_key=True, default=_uuid)
    empresa_id  = Column(String(36), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    nome        = Column(String(200), nullable=False)
    email       = Column(String(200), unique=True, nullable=False, index=True)
    senha_hash  = Column(String(200), nullable=True)
    role        = Column(
        Enum("super_admin", "admin", "nutricionista", "gestor", "visualizador", name="role_enum"),
        default="nutricionista",
        nullable=False
    )
    ativo       = Column(Boolean, default=True, nullable=False)
    ultimo_login = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=_now, nullable=False)
    updated_at  = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    empresa              = relationship("Empresa",    back_populates="usuarios")
    cardapios_criados    = relationship("Cardapio",   back_populates="criado_por", foreign_keys="Cardapio.criado_por_id")
    aprovacoes           = relationship("AprovacaoCardapio", back_populates="aprovado_por")

    def __repr__(self):
        return f"<Usuario {self.email} [{self.role}]>"


# ============================================================
# 3. CONTRATOS
# ============================================================
class Contrato(Base):
    __tablename__ = "contratos"

    id                    = Column(String(36), primary_key=True, default=_uuid)
    empresa_id            = Column(String(36), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    nome                  = Column(String(200), nullable=False)
    numero_contrato       = Column(String(100), nullable=True)
    arquivo_path          = Column(String(500), nullable=True)           # caminho do PDF/XLSX
    arquivo_hash          = Column(String(64), nullable=True, index=True)  # SHA256 para deduplicação
    regras_json           = Column(JSON, nullable=True)                  # regras extraídas pelos agentes
    data_inicio           = Column(Date, nullable=True)
    data_fim              = Column(Date, nullable=True)

    # Targets financeiros padrão do contrato
    custo_total_max       = Column(Float, default=10.00, nullable=False)
    custo_proteico_max    = Column(Float, default=3.50, nullable=False)

    # Estrutura padrão do cardápio
    num_refeicoes_dia     = Column(Integer, default=1, nullable=False)   # 1=almoço, 2=almoço+jantar
    estrutura_refeicao    = Column(JSON, nullable=True)                  # {proteico:1, opcao:1, guarnicao:2, salada:3}
    gramaturas_json       = Column(JSON, nullable=True)                  # {proteico:"120g", guarnicao:"80g"}

    # Regras de incidência e proibições
    incidencias_json      = Column(JSON, nullable=True)                  # {carne_bovina:"3x/semana"}
    proibicoes_json       = Column(JSON, nullable=True)                  # ["carne_suina", "frutos_do_mar"]
    observacoes           = Column(Text, nullable=True)

    ativo                 = Column(Boolean, default=True, nullable=False)
    created_at            = Column(DateTime, default=_now, nullable=False)
    updated_at            = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    empresa    = relationship("Empresa",  back_populates="contratos")
    cardapios  = relationship("Cardapio", back_populates="contrato")

    def __repr__(self):
        return f"<Contrato {self.nome}>"


# ============================================================
# 4. INGREDIENTES
# ============================================================
class CategoriaIngrediente:
    PROTEINA    = "PROTEINA"
    CARBOIDRATO = "CARBOIDRATO"
    HORTALICA   = "HORTALICA"
    FRUTA       = "FRUTA"
    LATICINIOS  = "LATICINIOS"
    GORDURA     = "GORDURA"
    CONDIMENTO  = "CONDIMENTO"
    BEBIDA      = "BEBIDA"
    OUTRO       = "OUTRO"


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id               = Column(String(36), primary_key=True, default=_uuid)
    empresa_id       = Column(String(36), ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    # nullable=True → ingredientes globais (empresa_id=None) compartilhados entre empresas

    codigo           = Column(String(50), nullable=True)
    nome             = Column(String(200), nullable=False, index=True)
    nome_cientifico  = Column(String(200), nullable=True)
    unidade_medida   = Column(
        Enum("kg", "g", "L", "ml", "un", "cx", "pct", name="unidade_enum"),
        default="kg", nullable=False
    )
    custo_unitario   = Column(Float, nullable=False, default=0.0)        # custo por unidade de medida
    fornecedor       = Column(String(200), nullable=True)

    # Fator de Correção (FC) — perda no pré-preparo (casca, osso, evaporação)
    # FC = Peso Bruto / Peso Líquido. Ex: cebola FC=1.25 (25% de perda)
    fator_correcao   = Column(Float, default=1.0, nullable=False)

    # Informação Nutricional (por 100g/ml)
    calorias_100g    = Column(Float, nullable=True)
    proteina_100g    = Column(Float, nullable=True)
    carboidrato_100g = Column(Float, nullable=True)
    gordura_100g     = Column(Float, nullable=True)
    fibra_100g       = Column(Float, nullable=True)
    sodio_100g       = Column(Float, nullable=True)

    # Alergênicos (RDC 26/2015 ANVISA)
    alergeno         = Column(Boolean, default=False, nullable=False)
    tipo_alergeno    = Column(String(200), nullable=True)                # "gluten, lactose"

    # Sazonalidade
    meses_safra      = Column(JSON, nullable=True)                       # [1,2,3] = jan,fev,mar

    categoria        = Column(
        Enum("PROTEINA","CARBOIDRATO","HORTALICA","FRUTA","LATICINIOS",
             "GORDURA","CONDIMENTO","BEBIDA","OUTRO", name="cat_ingrediente_enum"),
        default="OUTRO", nullable=False
    )
    ativo            = Column(Boolean, default=True, nullable=False)
    created_at       = Column(DateTime, default=_now, nullable=False)
    updated_at       = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    empresa          = relationship("Empresa", back_populates="ingredientes")
    ficha_items      = relationship("FichaIngrediente", back_populates="ingrediente")

    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_ingrediente_empresa_codigo"),
        Index("ix_ingrediente_nome", "nome"),
    )

    def __repr__(self):
        return f"<Ingrediente {self.nome}>"


# ============================================================
# 5. FICHAS TÉCNICAS (Receitas)
# ============================================================
class FichaTecnica(Base):
    __tablename__ = "fichas_tecnicas"

    id                  = Column(String(36), primary_key=True, default=_uuid)
    empresa_id          = Column(String(36), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)

    codigo              = Column(String(50), nullable=False)
    nome                = Column(String(300), nullable=False, index=True)
    categoria           = Column(String(100), nullable=False)            # PRATO PROTEICO, GUARNICAO, etc.

    # Rendimento
    rendimento_porcoes  = Column(Integer, default=1, nullable=False)
    peso_porcao_g       = Column(Float, nullable=True)                   # peso da porção em gramas

    # Preparo
    tempo_preparo_min   = Column(Integer, nullable=True)
    modo_preparo        = Column(Text, nullable=True)
    equipamento         = Column(String(200), nullable=True)             # forno combinado, caldeirão, etc.
    dificuldade         = Column(
        Enum("facil", "medio", "dificil", name="dificuldade_enum"),
        default="medio", nullable=False
    )
    temperatura_servico = Column(String(50), nullable=True)              # quente, frio, ambiente

    # Custos (calculados automaticamente a partir dos ingredientes)
    custo_total         = Column(Float, default=0.0, nullable=False)     # custo total da receita
    custo_porcao        = Column(Float, default=0.0, nullable=False)     # custo por porção

    # Valor Nutricional por porção (calculado)
    calorias_porcao     = Column(Float, nullable=True)
    proteina_porcao     = Column(Float, nullable=True)
    carboidrato_porcao  = Column(Float, nullable=True)
    gordura_porcao      = Column(Float, nullable=True)
    sodio_porcao        = Column(Float, nullable=True)

    # Restrições
    contem_gluten       = Column(Boolean, default=False)
    contem_lactose      = Column(Boolean, default=False)
    vegana              = Column(Boolean, default=False)
    vegetariana         = Column(Boolean, default=False)

    # Controle
    observacoes         = Column(Text, nullable=True)
    foto_url            = Column(String(500), nullable=True)
    ativo               = Column(Boolean, default=True, nullable=False)
    created_at          = Column(DateTime, default=_now, nullable=False)
    updated_at          = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    empresa             = relationship("Empresa",          back_populates="fichas_tecnicas")
    ingredientes_ficha  = relationship("FichaIngrediente", back_populates="ficha_tecnica",
                                       cascade="all, delete-orphan", order_by="FichaIngrediente.ordem")
    refeicoes           = relationship("CardapioRefeicao", back_populates="ficha_tecnica")

    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo", name="uq_ficha_empresa_codigo"),
        Index("ix_fichas_empresa_categoria", "empresa_id", "categoria"),
        Index("ix_fichas_empresa_nome", "empresa_id", "nome"),
    )

    def __repr__(self):
        return f"<FichaTecnica {self.codigo} - {self.nome}>"


# ============================================================
# 6. FICHA TÉCNICA × INGREDIENTES (Junction Table)
# ============================================================
class FichaIngrediente(Base):
    __tablename__ = "ficha_ingredientes"

    id                  = Column(String(36), primary_key=True, default=_uuid)
    ficha_tecnica_id    = Column(String(36), ForeignKey("fichas_tecnicas.id", ondelete="CASCADE"), nullable=False)
    ingrediente_id      = Column(String(36), ForeignKey("ingredientes.id", ondelete="RESTRICT"), nullable=False)

    # Quantidades
    quantidade_bruta_g  = Column(Float, nullable=False)                  # peso bruto (antes do FC)
    fator_correcao      = Column(Float, default=1.0, nullable=False)     # pode sobrescrever o do ingrediente
    quantidade_liquida_g = Column(Float, nullable=True)                  # calculado: bruta / FC

    # Custo calculado = (quantidade_bruta / 1000) × custo_unitario do ingrediente
    custo_calculado     = Column(Float, default=0.0, nullable=False)

    # Apresentação
    ordem               = Column(Integer, default=0, nullable=False)
    observacao          = Column(String(200), nullable=True)             # "tempero a gosto", "opcional"

    # Relacionamentos
    ficha_tecnica       = relationship("FichaTecnica",  back_populates="ingredientes_ficha")
    ingrediente         = relationship("Ingrediente",   back_populates="ficha_items")

    def __repr__(self):
        return f"<FichaIngrediente ficha={self.ficha_tecnica_id} ing={self.ingrediente_id}>"


# ============================================================
# 7. CARDÁPIOS
# ============================================================
class StatusCardapio:
    RASCUNHO        = "rascunho"
    EM_REVISAO      = "em_revisao"
    AGUARDANDO      = "aguardando_aprovacao"
    APROVADO        = "aprovado"
    PUBLICADO       = "publicado"
    ARQUIVADO       = "arquivado"


class Cardapio(Base):
    __tablename__ = "cardapios"

    id              = Column(String(36), primary_key=True, default=_uuid)
    empresa_id      = Column(String(36), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    contrato_id     = Column(String(36), ForeignKey("contratos.id", ondelete="SET NULL"), nullable=True)
    criado_por_id   = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    nome            = Column(String(200), nullable=False)
    periodo_inicio  = Column(Date, nullable=True)
    periodo_fim     = Column(Date, nullable=True)

    status          = Column(
        Enum("rascunho","em_revisao","aguardando_aprovacao","aprovado","publicado","arquivado",
             name="status_cardapio_enum"),
        default="rascunho", nullable=False
    )

    # Métricas
    custo_medio_dia = Column(Float, nullable=True)
    num_dias        = Column(Integer, nullable=True)

    # Output dos agentes
    resultado_raw   = Column(Text, nullable=True)                        # markdown da crew
    parametros_json = Column(JSON, nullable=True)                        # parâmetros usados na geração
    job_id          = Column(String(50), nullable=True, index=True)      # referência ao job da crew

    observacoes     = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=_now, nullable=False)
    updated_at      = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    empresa         = relationship("Empresa",           back_populates="cardapios")
    contrato        = relationship("Contrato",          back_populates="cardapios")
    criado_por      = relationship("Usuario",           back_populates="cardapios_criados",
                                   foreign_keys=[criado_por_id])
    dias            = relationship("CardapioDia",       back_populates="cardapio",
                                   cascade="all, delete-orphan", order_by="CardapioDia.data")
    aprovacoes      = relationship("AprovacaoCardapio", back_populates="cardapio",
                                   cascade="all, delete-orphan")
    jobs            = relationship("JobAgente",         back_populates="cardapio")

    def __repr__(self):
        return f"<Cardapio {self.nome} [{self.status}]>"


# ============================================================
# 8. CARDÁPIO × DIAS
# ============================================================
class CardapioDia(Base):
    __tablename__ = "cardapio_dias"

    id          = Column(String(36), primary_key=True, default=_uuid)
    cardapio_id = Column(String(36), ForeignKey("cardapios.id", ondelete="CASCADE"), nullable=False)
    data        = Column(Date, nullable=True)
    numero_dia  = Column(Integer, nullable=False)                        # 1, 2, 3... (útil quando sem data fixa)
    dia_semana  = Column(Integer, nullable=True)                         # 0=Seg, 6=Dom
    custo_total = Column(Float, default=0.0, nullable=False)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    cardapio    = relationship("Cardapio",          back_populates="dias")
    refeicoes   = relationship("CardapioRefeicao",  back_populates="dia",
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CardapioDia dia={self.numero_dia}>"


# ============================================================
# 9. CARDÁPIO × REFEIÇÕES (Pratos por dia)
# ============================================================
class TipoRefeicao:
    CAFE_MANHA  = "cafe_manha"
    LANCHE_MANHA = "lanche_manha"
    ALMOCO      = "almoco"
    LANCHE_TARDE = "lanche_tarde"
    JANTAR      = "jantar"
    CEIA        = "ceia"


class CardapioRefeicao(Base):
    __tablename__ = "cardapio_refeicoes"

    id               = Column(String(36), primary_key=True, default=_uuid)
    dia_id           = Column(String(36), ForeignKey("cardapio_dias.id", ondelete="CASCADE"), nullable=False)
    ficha_tecnica_id = Column(String(36), ForeignKey("fichas_tecnicas.id", ondelete="SET NULL"), nullable=True)

    tipo_refeicao    = Column(
        Enum("cafe_manha","lanche_manha","almoco","lanche_tarde","jantar","ceia",
             name="tipo_refeicao_enum"),
        default="almoco", nullable=False
    )
    categoria        = Column(String(100), nullable=True)                # PRATO PROTEICO, GUARNICAO...
    codigo_prato     = Column(String(50), nullable=True)                 # código da ficha / referência interna
    nome_prato       = Column(String(300), nullable=False)
    custo_porcao     = Column(Float, default=0.0, nullable=False)
    observacoes      = Column(String(500), nullable=True)
    ordem            = Column(Integer, default=0, nullable=False)

    # Relacionamentos
    dia              = relationship("CardapioDia",  back_populates="refeicoes")
    ficha_tecnica    = relationship("FichaTecnica", back_populates="refeicoes")

    def __repr__(self):
        return f"<CardapioRefeicao {self.nome_prato}>"


# ============================================================
# 10. APROVAÇÕES DO CARDÁPIO (Workflow)
# ============================================================
class AprovacaoCardapio(Base):
    __tablename__ = "aprovacoes_cardapio"

    id             = Column(String(36), primary_key=True, default=_uuid)
    cardapio_id    = Column(String(36), ForeignKey("cardapios.id", ondelete="CASCADE"), nullable=False)
    aprovado_por_id = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    status         = Column(
        Enum("aprovado", "reprovado", "solicitado_revisao", name="status_aprovacao_enum"),
        nullable=False
    )
    comentario     = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=_now, nullable=False)

    # Relacionamentos
    cardapio       = relationship("Cardapio", back_populates="aprovacoes")
    aprovado_por   = relationship("Usuario",  back_populates="aprovacoes")

    def __repr__(self):
        return f"<Aprovacao cardapio={self.cardapio_id} status={self.status}>"


# ============================================================
# 11. JOBS DOS AGENTES IA
# ============================================================
class JobAgente(Base):
    __tablename__ = "jobs_agente"

    id              = Column(String(36), primary_key=True, default=_uuid)
    empresa_id      = Column(String(36), ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True)
    cardapio_id     = Column(String(36), ForeignKey("cardapios.id", ondelete="SET NULL"), nullable=True)
    criado_por_id   = Column(String(36), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    job_id          = Column(String(50), unique=True, nullable=False, index=True)
    status          = Column(
        Enum("iniciando","executando","concluido","erro", name="status_job_enum"),
        default="iniciando", nullable=False
    )
    progresso       = Column(Integer, default=0, nullable=False)         # 0-100

    # Parâmetros e resultado
    parametros_json = Column(JSON, nullable=True)
    resultado_raw   = Column(Text, nullable=True)
    logs_json       = Column(JSON, nullable=True)                        # lista de eventos
    erro            = Column(Text, nullable=True)

    # Timestamps
    iniciado_em     = Column(DateTime, default=_now, nullable=False)
    concluido_em    = Column(DateTime, nullable=True)
    updated_at      = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    empresa         = relationship("Empresa",  foreign_keys=[empresa_id])
    cardapio        = relationship("Cardapio", back_populates="jobs")

    def __repr__(self):
        return f"<JobAgente {self.job_id} [{self.status}]>"


# ============================================================
# 12. CONFIGURAÇÃO DE MODELOS LLM (activar/desactivar na BD)
# ============================================================
class LlmModelConfig(Base):
    """Um registo por id interno do catálogo (queen-3.6, glm-5-1, …)."""

    __tablename__ = "llm_model_config"

    model_id   = Column(String(64), primary_key=True)
    enabled    = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    def __repr__(self):
        return f"<LlmModelConfig {self.model_id} enabled={self.enabled}>"


# ============================================================
# 13. BASE DE CONHECIMENTO / VETORES
# ============================================================
class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=_uuid)
    empresa_id = Column(String(36), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=True)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(36), nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    chunks = relationship(
        "KnowledgeChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KnowledgeChunk.chunk_index",
    )
    empresa = relationship("Empresa", foreign_keys=[empresa_id])

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_knowledge_source"),
        Index("ix_knowledge_documents_empresa_source", "empresa_id", "source_type"),
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    empresa_id = Column(String(36), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=True)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(36), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_hash = Column(String(64), nullable=False, index=True)
    token_count = Column(Integer, nullable=True)
    embedding = _vector_column(nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")
    empresa = relationship("Empresa", foreign_keys=[empresa_id])

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_doc_chunk"),
        Index("ix_knowledge_chunks_empresa_source", "empresa_id", "source_type", "source_id"),
    )


# ============================================================
# 14. AUDITORIA DE CHAMADAS LLM
# ============================================================
class LLMAuditLog(Base):
    """Rastreia cada tentativa de chamada a um modelo LLM (sucesso ou falha)."""

    __tablename__ = "llm_audit_logs"

    id              = Column(String(36), primary_key=True, default=_uuid)
    job_id          = Column(String(50), nullable=True, index=True)
    empresa_id      = Column(String(36), nullable=True, index=True)

    # Modelo e provedor
    model_requested = Column(String(200), nullable=False)       # modelo pedido pelo usuário/config
    model_used      = Column(String(200), nullable=False)       # modelo efetivamente usado (pode ser fallback)
    provider        = Column(String(100), nullable=True)        # openrouter, anthropic, openai, etc.
    is_fallback     = Column(Boolean, default=False)            # True se usou modelo de fallback

    # Etapa do pipeline
    step_label      = Column(String(200), nullable=True)        # "Analista de Contratos", etc.
    step_index      = Column(Integer, nullable=True)

    # Métricas
    latency_ms      = Column(Integer, nullable=True)            # latência total em ms
    tokens_prompt   = Column(Integer, nullable=True)
    tokens_completion = Column(Integer, nullable=True)
    tokens_total    = Column(Integer, nullable=True)
    cost_usd        = Column(Float, nullable=True)              # custo estimado em USD

    # Resultado
    success         = Column(Boolean, default=True, nullable=False)
    error_type      = Column(String(100), nullable=True)        # timeout, rate_limit, auth, etc.
    error_message   = Column(Text, nullable=True)
    http_status     = Column(Integer, nullable=True)

    # Timestamps
    created_at      = Column(DateTime, default=_now, nullable=False)

    __table_args__ = (
        Index("ix_llm_audit_job_step", "job_id", "step_index"),
        Index("ix_llm_audit_created", "created_at"),
        Index("ix_llm_audit_model", "model_used"),
    )

    def __repr__(self):
        return f"<LLMAuditLog {self.model_used} success={self.success}>"


# ============================================================
# 15. CHAT CONVERSACIONAL (HITL & Sessões)
# ============================================================
class SessaoChat(Base):
    """
    Sessão de chat para persistir contexto de interações (HITL) de um usuário,
    opcionalmente atrelada a um job de geração.
    """
    __tablename__ = "sessoes_chat"

    id              = Column(String(36), primary_key=True, default=_uuid)
    usuario_id      = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    job_id          = Column(String(50), ForeignKey("jobs_agente.job_id", ondelete="SET NULL"), nullable=True, index=True)
    
    titulo          = Column(String(200), nullable=True)
    contexto_json   = Column(JSON, nullable=True)  # Armazena estado parcial/final como ContratoAnalise
    status          = Column(
        Enum("ativa", "concluida", "arquivada", name="status_sessao_chat_enum"),
        default="ativa", nullable=False
    )
    
    created_at      = Column(DateTime, default=_now, nullable=False)
    updated_at      = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relacionamentos
    usuario         = relationship("Usuario", foreign_keys=[usuario_id])
    # Como job_id na SessaoChat referencia jobs_agente.job_id (que não é PK mas é unique), 
    # declaramos com primaryjoin
    job             = relationship("JobAgente", foreign_keys=[job_id], primaryjoin="SessaoChat.job_id == JobAgente.job_id")
    mensagens       = relationship("MensagemChat", back_populates="sessao", cascade="all, delete-orphan", order_by="MensagemChat.created_at")

    def __repr__(self):
        return f"<SessaoChat {self.id} usuario={self.usuario_id}>"


class MensagemChat(Base):
    """
    Mensagens individuais dentro de uma sessão de chat.
    Suporta roles do formato OpenAI e metadata para registrar 'thoughts'.
    """
    __tablename__ = "mensagens_chat"

    id              = Column(String(36), primary_key=True, default=_uuid)
    sessao_id       = Column(String(36), ForeignKey("sessoes_chat.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role            = Column(
        Enum("user", "assistant", "system", "tool", name="role_mensagem_chat_enum"),
        nullable=False
    )
    content         = Column(Text, nullable=False)
    
    # Suporte a Tool Calling no histórico
    tool_calls      = Column(JSON, nullable=True) 
    tool_call_id    = Column(String(100), nullable=True)
    
    # Metadata para armazenar thoughts, latency, tokens
    metadata_json   = Column(JSON, nullable=True) 
    
    created_at      = Column(DateTime, default=_now, nullable=False)

    # Relacionamentos
    sessao          = relationship("SessaoChat", back_populates="mensagens")

    def __repr__(self):
        return f"<MensagemChat {self.id[:8]} role={self.role}>"

