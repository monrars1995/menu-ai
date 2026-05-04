"""make_usuario_senha_hash_nullable

Revision ID: 1fe99845703a
Revises: 004
Create Date: 2026-04-30 23:19:30.831483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1fe99845703a'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('usuarios', 'senha_hash',
                    existing_type=sa.String(length=200),
                    nullable=True)


def downgrade() -> None:
    op.alter_column('usuarios', 'senha_hash',
                    existing_type=sa.String(length=200),
                    nullable=False)
