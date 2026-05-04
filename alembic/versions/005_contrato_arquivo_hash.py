"""adicionar arquivo_hash em contratos

Revision ID: 005
Revises: 1fe99845703a
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "1fe99845703a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contratos",
        sa.Column("arquivo_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_contratos_arquivo_hash", "contratos", ["arquivo_hash"])


def downgrade() -> None:
    op.drop_index("ix_contratos_arquivo_hash", table_name="contratos")
    op.drop_column("contratos", "arquivo_hash")
