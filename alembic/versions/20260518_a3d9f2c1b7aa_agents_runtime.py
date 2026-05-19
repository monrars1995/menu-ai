"""agents_runtime

Revision ID: a3d9f2c1b7aa
Revises: 9b15c404aa46
Create Date: 2026-05-18 12:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a3d9f2c1b7aa"
down_revision: Union[str, None] = "9b15c404aa46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


agent_slot_type_enum = postgresql.ENUM(
    "contract_analyzer",
    "generator",
    "reviewer",
    "copilot",
    name="agent_slot_type_enum",
    create_type=False,
)

agent_version_status_enum = postgresql.ENUM(
    "draft",
    "published",
    "archived",
    name="agent_version_status_enum",
    create_type=False,
)


def upgrade() -> None:
    agent_slot_type_enum.create(op.get_bind(), checkfirst=True)
    agent_version_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slot_type", agent_slot_type_enum, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_agent_profiles_slug"),
    )
    op.create_index("ix_agent_profiles_slot_type", "agent_profiles", ["slot_type"], unique=False)

    op.create_table(
        "agent_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", agent_version_status_enum, nullable=False),
        sa.Column("provider_model_id", sa.String(length=120), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("allowed_tools_json", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("publish_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["profile_id"], ["agent_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "version_number", name="uq_agent_profile_version"),
    )
    op.create_index("ix_agent_versions_profile_id", "agent_versions", ["profile_id"], unique=False)
    op.create_index("ix_agent_versions_status", "agent_versions", ["status"], unique=False)

    op.create_table(
        "flow_agent_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("flow_key", sa.String(length=80), nullable=False),
        sa.Column("slot_type", agent_slot_type_enum, nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("version_id", sa.String(length=36), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["agent_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_id"], ["agent_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flow_key", "slot_type", name="uq_flow_agent_binding"),
    )
    op.create_index("ix_flow_agent_bindings_flow_key", "flow_agent_bindings", ["flow_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_flow_agent_bindings_flow_key", table_name="flow_agent_bindings")
    op.drop_table("flow_agent_bindings")

    op.drop_index("ix_agent_versions_status", table_name="agent_versions")
    op.drop_index("ix_agent_versions_profile_id", table_name="agent_versions")
    op.drop_table("agent_versions")

    op.drop_index("ix_agent_profiles_slot_type", table_name="agent_profiles")
    op.drop_table("agent_profiles")

    agent_version_status_enum.drop(op.get_bind(), checkfirst=True)
    agent_slot_type_enum.drop(op.get_bind(), checkfirst=True)
