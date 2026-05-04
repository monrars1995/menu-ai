"""Supabase knowledge base com pgvector

Revision ID: 004
Revises: 003
Create Date: 2026-04-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supabase usa schema 'extensions' para pgvector; local Docker pode não ter o schema
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    # Tenta instalar no schema extensions; se já existir, fica no schema original
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("empresa_id", sa.String(length=36), sa.ForeignKey("empresas.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source_type", "source_id", name="uq_knowledge_source"),
    )
    op.create_index("ix_knowledge_documents_empresa_source", "knowledge_documents", ["empresa_id", "source_type"])
    op.create_index("ix_knowledge_documents_content_hash", "knowledge_documents", ["content_hash"])

    op.execute(
        """
        CREATE TABLE knowledge_chunks (
          id varchar(36) PRIMARY KEY,
          document_id varchar(36) NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
          empresa_id varchar(36) NULL REFERENCES empresas(id) ON DELETE CASCADE,
          source_type varchar(50) NOT NULL,
          source_id varchar(36) NOT NULL,
          chunk_index integer NOT NULL,
          chunk_text text NOT NULL,
          chunk_hash varchar(64) NOT NULL,
          token_count integer NULL,
           embedding extensions.vector(1536) NULL,
          metadata_json json NULL,
          created_at timestamp NOT NULL DEFAULT now(),
          updated_at timestamp NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("ix_knowledge_chunks_doc_chunk", "knowledge_chunks", ["document_id", "chunk_index"], unique=True)
    op.create_index("ix_knowledge_chunks_empresa_source", "knowledge_chunks", ["empresa_id", "source_type", "source_id"])
    op.create_index("ix_knowledge_chunks_chunk_hash", "knowledge_chunks", ["chunk_hash"])
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw
        ON knowledge_chunks
        USING hnsw (embedding extensions.vector_cosine_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_fts
        ON knowledge_chunks
        USING gin (to_tsvector('portuguese', chunk_text))
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION match_knowledge_chunks(
          query_embedding extensions.vector(1536),
          match_count int DEFAULT 8,
          filter_empresa_id text DEFAULT NULL,
          filter_source_type text DEFAULT NULL
        )
        RETURNS TABLE (
          chunk_id text,
          document_id text,
          empresa_id text,
          source_type text,
          source_id text,
          title text,
          chunk_text text,
          metadata_json jsonb,
          similarity double precision
        )
        LANGUAGE sql
        STABLE
        SET search_path = public, extensions
        AS $$
          SELECT
            kc.id::text,
            kd.id::text,
            kd.empresa_id::text,
            kd.source_type,
            kd.source_id,
            kd.title,
            kc.chunk_text,
            COALESCE(kc.metadata_json::jsonb, '{}'::jsonb),
            1 - (kc.embedding <=> query_embedding) AS similarity
          FROM knowledge_chunks kc
          JOIN knowledge_documents kd ON kd.id = kc.document_id
          WHERE kd.active = true
            AND kc.embedding IS NOT NULL
            AND (filter_empresa_id IS NULL OR kd.empresa_id = filter_empresa_id)
            AND (filter_source_type IS NULL OR kd.source_type = filter_source_type)
          ORDER BY kc.embedding <=> query_embedding
          LIMIT match_count
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS match_knowledge_chunks(extensions.vector, int, text, text)")
    op.drop_index("ix_knowledge_chunks_fts", table_name="knowledge_chunks")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.drop_index("ix_knowledge_chunks_chunk_hash", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_empresa_source", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_doc_chunk", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_documents_content_hash", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_empresa_source", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
