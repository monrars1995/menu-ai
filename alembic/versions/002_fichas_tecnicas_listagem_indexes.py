"""índices compostos em fichas_tecnicas (empresa + categoria / nome)

Revision ID: 002
Revises: 001
Create Date: 2026-04-29
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_fichas_empresa_categoria",
        "fichas_tecnicas",
        ["empresa_id", "categoria"],
    )
    op.create_index(
        "ix_fichas_empresa_nome",
        "fichas_tecnicas",
        ["empresa_id", "nome"],
    )


def downgrade() -> None:
    op.drop_index("ix_fichas_empresa_nome", table_name="fichas_tecnicas")
    op.drop_index("ix_fichas_empresa_categoria", table_name="fichas_tecnicas")
