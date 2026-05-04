"""Tabela llm_model_config (activar/desactivar modelos no catálogo)

Revision ID: 003
Revises: 002
Create Date: 2026-04-29
"""
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_model_config",
        sa.Column("model_id", sa.String(64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    now = datetime.utcnow()
    llm_model_config = sa.table(
        "llm_model_config",
        sa.column("model_id", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(
        llm_model_config,
        [
            {"model_id": "queen-3.6", "enabled": True, "updated_at": now},
            {"model_id": "glm-5-1", "enabled": True, "updated_at": now},
            {"model_id": "kimi-k2.5", "enabled": True, "updated_at": now},
        ],
    )


def downgrade() -> None:
    op.drop_table("llm_model_config")
