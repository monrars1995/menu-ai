"""Schema inicial Menu.AI — todas as tabelas do sistema

Revision ID: 001
Revises:
Create Date: 2026-04-21

Tabelas criadas:
  - empresas
  - usuarios
  - contratos
  - ingredientes
  - fichas_tecnicas
  - ficha_ingredientes
  - cardapios
  - cardapio_dias
  - cardapio_refeicoes
  - aprovacoes_cardapio
  - jobs_agente
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # ENUMs
    # ============================================================
    role_enum = postgresql.ENUM(
        "super_admin", "admin", "nutricionista", "gestor", "visualizador",
        name="role_enum", create_type=False
    )
    role_enum.create(op.get_bind(), checkfirst=True)

    unidade_enum = postgresql.ENUM(
        "kg", "g", "L", "ml", "un", "cx", "pct",
        name="unidade_enum", create_type=False
    )
    unidade_enum.create(op.get_bind(), checkfirst=True)

    cat_ingrediente_enum = postgresql.ENUM(
        "PROTEINA", "CARBOIDRATO", "HORTALICA", "FRUTA", "LATICINIOS",
        "GORDURA", "CONDIMENTO", "BEBIDA", "OUTRO",
        name="cat_ingrediente_enum", create_type=False
    )
    cat_ingrediente_enum.create(op.get_bind(), checkfirst=True)

    dificuldade_enum = postgresql.ENUM(
        "facil", "medio", "dificil",
        name="dificuldade_enum", create_type=False
    )
    dificuldade_enum.create(op.get_bind(), checkfirst=True)

    status_cardapio_enum = postgresql.ENUM(
        "rascunho", "em_revisao", "aguardando_aprovacao", "aprovado", "publicado", "arquivado",
        name="status_cardapio_enum", create_type=False
    )
    status_cardapio_enum.create(op.get_bind(), checkfirst=True)

    tipo_refeicao_enum = postgresql.ENUM(
        "cafe_manha", "lanche_manha", "almoco", "lanche_tarde", "jantar", "ceia",
        name="tipo_refeicao_enum", create_type=False
    )
    tipo_refeicao_enum.create(op.get_bind(), checkfirst=True)

    status_aprovacao_enum = postgresql.ENUM(
        "aprovado", "reprovado", "solicitado_revisao",
        name="status_aprovacao_enum", create_type=False
    )
    status_aprovacao_enum.create(op.get_bind(), checkfirst=True)

    status_job_enum = postgresql.ENUM(
        "iniciando", "executando", "concluido", "erro",
        name="status_job_enum", create_type=False
    )
    status_job_enum.create(op.get_bind(), checkfirst=True)

    # ============================================================
    # 1. EMPRESAS
    # ============================================================
    op.create_table(
        "empresas",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("nome",           sa.String(200), nullable=False),
        sa.Column("cnpj",           sa.String(18),  unique=True, nullable=True),
        sa.Column("email",          sa.String(200), nullable=True),
        sa.Column("telefone",       sa.String(20),  nullable=True),
        sa.Column("endereco",       sa.Text(),      nullable=True),
        sa.Column("logo_url",       sa.String(500), nullable=True),
        sa.Column("segmento",       sa.String(100), nullable=True),
        sa.Column("num_comensais",  sa.Integer(),   nullable=True),
        sa.Column("ativo",          sa.Boolean(),   default=True, nullable=False),
        sa.Column("created_at",     sa.DateTime(),  nullable=False),
        sa.Column("updated_at",     sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_empresas_nome", "empresas", ["nome"])

    # ============================================================
    # 2. USUÁRIOS
    # ============================================================
    op.create_table(
        "usuarios",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("empresa_id",   sa.String(36),  sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome",         sa.String(200), nullable=False),
        sa.Column("email",        sa.String(200), unique=True, nullable=False),
        sa.Column("senha_hash",   sa.String(200), nullable=False),
        sa.Column("role",         role_enum, server_default="nutricionista", nullable=False),
        sa.Column("ativo",        sa.Boolean(),   default=True, nullable=False),
        sa.Column("ultimo_login", sa.DateTime(),  nullable=True),
        sa.Column("created_at",   sa.DateTime(),  nullable=False),
        sa.Column("updated_at",   sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])

    # ============================================================
    # 3. CONTRATOS
    # ============================================================
    op.create_table(
        "contratos",
        sa.Column("id",                   sa.String(36),  primary_key=True),
        sa.Column("empresa_id",           sa.String(36),  sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome",                 sa.String(200), nullable=False),
        sa.Column("numero_contrato",      sa.String(100), nullable=True),
        sa.Column("arquivo_path",         sa.String(500), nullable=True),
        sa.Column("regras_json",          postgresql.JSON(), nullable=True),
        sa.Column("data_inicio",          sa.Date(),      nullable=True),
        sa.Column("data_fim",             sa.Date(),      nullable=True),
        sa.Column("custo_total_max",      sa.Float(),     default=10.00, nullable=False),
        sa.Column("custo_proteico_max",   sa.Float(),     default=3.50,  nullable=False),
        sa.Column("num_refeicoes_dia",    sa.Integer(),   default=1,     nullable=False),
        sa.Column("estrutura_refeicao",   postgresql.JSON(), nullable=True),
        sa.Column("gramaturas_json",      postgresql.JSON(), nullable=True),
        sa.Column("incidencias_json",     postgresql.JSON(), nullable=True),
        sa.Column("proibicoes_json",      postgresql.JSON(), nullable=True),
        sa.Column("observacoes",          sa.Text(),      nullable=True),
        sa.Column("ativo",                sa.Boolean(),   default=True, nullable=False),
        sa.Column("created_at",           sa.DateTime(),  nullable=False),
        sa.Column("updated_at",           sa.DateTime(),  nullable=False),
    )

    # ============================================================
    # 4. INGREDIENTES
    # ============================================================
    op.create_table(
        "ingredientes",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("empresa_id",       sa.String(36),  sa.ForeignKey("empresas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("codigo",           sa.String(50),  nullable=True),
        sa.Column("nome",             sa.String(200), nullable=False),
        sa.Column("nome_cientifico",  sa.String(200), nullable=True),
        sa.Column("unidade_medida",   unidade_enum, server_default="kg", nullable=False),
        sa.Column("custo_unitario",   sa.Float(),     default=0.0, nullable=False),
        sa.Column("fornecedor",       sa.String(200), nullable=True),
        sa.Column("fator_correcao",   sa.Float(),     default=1.0, nullable=False),
        sa.Column("calorias_100g",    sa.Float(),     nullable=True),
        sa.Column("proteina_100g",    sa.Float(),     nullable=True),
        sa.Column("carboidrato_100g", sa.Float(),     nullable=True),
        sa.Column("gordura_100g",     sa.Float(),     nullable=True),
        sa.Column("fibra_100g",       sa.Float(),     nullable=True),
        sa.Column("sodio_100g",       sa.Float(),     nullable=True),
        sa.Column("alergeno",         sa.Boolean(),   default=False, nullable=False),
        sa.Column("tipo_alergeno",    sa.String(200), nullable=True),
        sa.Column("meses_safra",      postgresql.JSON(), nullable=True),
        sa.Column("categoria",        cat_ingrediente_enum, server_default="OUTRO", nullable=False),
        sa.Column("ativo",            sa.Boolean(),   default=True, nullable=False),
        sa.Column("created_at",       sa.DateTime(),  nullable=False),
        sa.Column("updated_at",       sa.DateTime(),  nullable=False),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_ingrediente_empresa_codigo"),
    )
    op.create_index("ix_ingrediente_nome", "ingredientes", ["nome"])

    # ============================================================
    # 5. FICHAS TÉCNICAS
    # ============================================================
    op.create_table(
        "fichas_tecnicas",
        sa.Column("id",                  sa.String(36),  primary_key=True),
        sa.Column("empresa_id",          sa.String(36),  sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo",              sa.String(50),  nullable=False),
        sa.Column("nome",                sa.String(300), nullable=False),
        sa.Column("categoria",           sa.String(100), nullable=False),
        sa.Column("rendimento_porcoes",  sa.Integer(),   default=1, nullable=False),
        sa.Column("peso_porcao_g",       sa.Float(),     nullable=True),
        sa.Column("tempo_preparo_min",   sa.Integer(),   nullable=True),
        sa.Column("modo_preparo",        sa.Text(),      nullable=True),
        sa.Column("equipamento",         sa.String(200), nullable=True),
        sa.Column("dificuldade",         dificuldade_enum, server_default="medio", nullable=False),
        sa.Column("temperatura_servico", sa.String(50),  nullable=True),
        sa.Column("custo_total",         sa.Float(),     default=0.0, nullable=False),
        sa.Column("custo_porcao",        sa.Float(),     default=0.0, nullable=False),
        sa.Column("calorias_porcao",     sa.Float(),     nullable=True),
        sa.Column("proteina_porcao",     sa.Float(),     nullable=True),
        sa.Column("carboidrato_porcao",  sa.Float(),     nullable=True),
        sa.Column("gordura_porcao",      sa.Float(),     nullable=True),
        sa.Column("sodio_porcao",        sa.Float(),     nullable=True),
        sa.Column("contem_gluten",       sa.Boolean(),   default=False),
        sa.Column("contem_lactose",      sa.Boolean(),   default=False),
        sa.Column("vegana",              sa.Boolean(),   default=False),
        sa.Column("vegetariana",         sa.Boolean(),   default=False),
        sa.Column("observacoes",         sa.Text(),      nullable=True),
        sa.Column("foto_url",            sa.String(500), nullable=True),
        sa.Column("ativo",               sa.Boolean(),   default=True, nullable=False),
        sa.Column("created_at",          sa.DateTime(),  nullable=False),
        sa.Column("updated_at",          sa.DateTime(),  nullable=False),
        sa.UniqueConstraint("empresa_id", "codigo", name="uq_ficha_empresa_codigo"),
    )
    op.create_index("ix_ficha_tecnica_nome", "fichas_tecnicas", ["nome"])

    # ============================================================
    # 6. FICHA × INGREDIENTES
    # ============================================================
    op.create_table(
        "ficha_ingredientes",
        sa.Column("id",                   sa.String(36), primary_key=True),
        sa.Column("ficha_tecnica_id",     sa.String(36), sa.ForeignKey("fichas_tecnicas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingrediente_id",       sa.String(36), sa.ForeignKey("ingredientes.id",    ondelete="RESTRICT"), nullable=False),
        sa.Column("quantidade_bruta_g",   sa.Float(),    nullable=False),
        sa.Column("fator_correcao",       sa.Float(),    default=1.0, nullable=False),
        sa.Column("quantidade_liquida_g", sa.Float(),    nullable=True),
        sa.Column("custo_calculado",      sa.Float(),    default=0.0, nullable=False),
        sa.Column("ordem",                sa.Integer(),  default=0, nullable=False),
        sa.Column("observacao",           sa.String(200), nullable=True),
    )

    # ============================================================
    # 7. CARDÁPIOS
    # ============================================================
    op.create_table(
        "cardapios",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("empresa_id",      sa.String(36),  sa.ForeignKey("empresas.id",  ondelete="CASCADE"),   nullable=False),
        sa.Column("contrato_id",     sa.String(36),  sa.ForeignKey("contratos.id", ondelete="SET NULL"),  nullable=True),
        sa.Column("criado_por_id",   sa.String(36),  sa.ForeignKey("usuarios.id",  ondelete="SET NULL"),  nullable=True),
        sa.Column("nome",            sa.String(200), nullable=False),
        sa.Column("periodo_inicio",  sa.Date(),      nullable=True),
        sa.Column("periodo_fim",     sa.Date(),      nullable=True),
        sa.Column("status",          status_cardapio_enum, server_default="rascunho", nullable=False),
        sa.Column("custo_medio_dia", sa.Float(),     nullable=True),
        sa.Column("num_dias",        sa.Integer(),   nullable=True),
        sa.Column("resultado_raw",   sa.Text(),      nullable=True),
        sa.Column("parametros_json", postgresql.JSON(), nullable=True),
        sa.Column("job_id",          sa.String(50),  nullable=True),
        sa.Column("observacoes",     sa.Text(),      nullable=True),
        sa.Column("created_at",      sa.DateTime(),  nullable=False),
        sa.Column("updated_at",      sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_cardapios_job_id", "cardapios", ["job_id"])

    # ============================================================
    # 8. CARDÁPIO × DIAS
    # ============================================================
    op.create_table(
        "cardapio_dias",
        sa.Column("id",          sa.String(36), primary_key=True),
        sa.Column("cardapio_id", sa.String(36), sa.ForeignKey("cardapios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data",        sa.Date(),     nullable=True),
        sa.Column("numero_dia",  sa.Integer(),  nullable=False),
        sa.Column("dia_semana",  sa.Integer(),  nullable=True),
        sa.Column("custo_total", sa.Float(),    default=0.0, nullable=False),
        sa.Column("observacoes", sa.Text(),     nullable=True),
    )

    # ============================================================
    # 9. CARDÁPIO × REFEIÇÕES
    # ============================================================
    op.create_table(
        "cardapio_refeicoes",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("dia_id",           sa.String(36),  sa.ForeignKey("cardapio_dias.id",   ondelete="CASCADE"),   nullable=False),
        sa.Column("ficha_tecnica_id", sa.String(36),  sa.ForeignKey("fichas_tecnicas.id", ondelete="SET NULL"),  nullable=True),
        sa.Column("tipo_refeicao",    tipo_refeicao_enum, server_default="almoco", nullable=False),
        sa.Column("categoria",        sa.String(100), nullable=True),
        sa.Column("codigo_prato",     sa.String(50),  nullable=True),
        sa.Column("nome_prato",       sa.String(300), nullable=False),
        sa.Column("custo_porcao",     sa.Float(),     default=0.0, nullable=False),
        sa.Column("observacoes",      sa.String(500), nullable=True),
        sa.Column("ordem",            sa.Integer(),   default=0, nullable=False),
    )

    # ============================================================
    # 10. APROVAÇÕES
    # ============================================================
    op.create_table(
        "aprovacoes_cardapio",
        sa.Column("id",               sa.String(36), primary_key=True),
        sa.Column("cardapio_id",      sa.String(36), sa.ForeignKey("cardapios.id", ondelete="CASCADE"),   nullable=False),
        sa.Column("aprovado_por_id",  sa.String(36), sa.ForeignKey("usuarios.id",  ondelete="SET NULL"), nullable=True),
        sa.Column("status",           status_aprovacao_enum, nullable=False),
        sa.Column("comentario",       sa.Text(),     nullable=True),
        sa.Column("created_at",       sa.DateTime(), nullable=False),
    )

    # ============================================================
    # 11. JOBS DOS AGENTES
    # ============================================================
    op.create_table(
        "jobs_agente",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("empresa_id",      sa.String(36),  sa.ForeignKey("empresas.id",  ondelete="SET NULL"), nullable=True),
        sa.Column("cardapio_id",     sa.String(36),  sa.ForeignKey("cardapios.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criado_por_id",   sa.String(36),  sa.ForeignKey("usuarios.id",  ondelete="SET NULL"), nullable=True),
        sa.Column("job_id",          sa.String(50),  unique=True, nullable=False),
        sa.Column("status",          status_job_enum, server_default="iniciando", nullable=False),
        sa.Column("progresso",       sa.Integer(),   default=0, nullable=False),
        sa.Column("parametros_json", postgresql.JSON(), nullable=True),
        sa.Column("resultado_raw",   sa.Text(),      nullable=True),
        sa.Column("logs_json",       postgresql.JSON(), nullable=True),
        sa.Column("erro",            sa.Text(),      nullable=True),
        sa.Column("iniciado_em",     sa.DateTime(),  nullable=False),
        sa.Column("concluido_em",    sa.DateTime(),  nullable=True),
        sa.Column("updated_at",      sa.DateTime(),  nullable=False),
    )
    op.create_index("ix_jobs_agente_job_id", "jobs_agente", ["job_id"])


def downgrade() -> None:
    # Remove tabelas na ordem inversa (respeita FKs)
    op.drop_table("jobs_agente")
    op.drop_table("aprovacoes_cardapio")
    op.drop_table("cardapio_refeicoes")
    op.drop_table("cardapio_dias")
    op.drop_table("cardapios")
    op.drop_table("ficha_ingredientes")
    op.drop_table("fichas_tecnicas")
    op.drop_table("ingredientes")
    op.drop_table("contratos")
    op.drop_table("usuarios")
    op.drop_table("empresas")

    # Remove ENUMs
    for enum_name in [
        "status_job_enum", "status_aprovacao_enum", "tipo_refeicao_enum",
        "status_cardapio_enum", "dificuldade_enum", "cat_ingrediente_enum",
        "unidade_enum", "role_enum"
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
