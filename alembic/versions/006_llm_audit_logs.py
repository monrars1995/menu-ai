"""add_llm_audit_logs_table

Revision ID: 006_llm_audit
Revises: 1fe99845703a
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_llm_audit'
down_revision: Union[str, None] = '1fe99845703a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('job_id', sa.String(50), nullable=True, index=True),
        sa.Column('empresa_id', sa.String(36), nullable=True, index=True),
        # Modelo e provedor
        sa.Column('model_requested', sa.String(200), nullable=False),
        sa.Column('model_used', sa.String(200), nullable=False),
        sa.Column('provider', sa.String(100), nullable=True),
        sa.Column('is_fallback', sa.Boolean(), default=False),
        # Etapa do pipeline
        sa.Column('step_label', sa.String(200), nullable=True),
        sa.Column('step_index', sa.Integer(), nullable=True),
        # Métricas
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_prompt', sa.Integer(), nullable=True),
        sa.Column('tokens_completion', sa.Integer(), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        # Resultado
        sa.Column('success', sa.Boolean(), default=True, nullable=False),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_llm_audit_job_step', 'llm_audit_logs', ['job_id', 'step_index'])
    op.create_index('ix_llm_audit_created', 'llm_audit_logs', ['created_at'])
    op.create_index('ix_llm_audit_model', 'llm_audit_logs', ['model_used'])


def downgrade() -> None:
    op.drop_index('ix_llm_audit_model', table_name='llm_audit_logs')
    op.drop_index('ix_llm_audit_created', table_name='llm_audit_logs')
    op.drop_index('ix_llm_audit_job_step', table_name='llm_audit_logs')
    op.drop_table('llm_audit_logs')
