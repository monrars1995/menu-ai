"""Merge heads

Revision ID: 026d2f56bfbe
Revises: 005, 006_llm_audit
Create Date: 2026-05-05 03:41:42.542640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '026d2f56bfbe'
down_revision: Union[str, None] = ('005', '006_llm_audit')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
