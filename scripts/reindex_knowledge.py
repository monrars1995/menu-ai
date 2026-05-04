#!/usr/bin/env python3
"""
Reindexa a base de conhecimento no Supabase/PostgreSQL em lotes pequenos.

Uso:
  python scripts/reindex_knowledge.py --empresa-id 00000000-0000-0000-0000-000000000001 --force
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid

from dotenv import load_dotenv
from sqlalchemy.orm import selectinload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"), override=True)

from database.connection import SessionLocal  # noqa: E402
from database.models import (  # noqa: E402
    Cardapio,
    Contrato,
    FichaIngrediente,
    FichaTecnica,
    KnowledgeChunk,
    KnowledgeDocument,
)
from services.knowledge_base import (  # noqa: E402
    SOURCE_CARDAPIO,
    SOURCE_CONTRATO,
    SOURCE_FICHA,
    _chunk_text,
    _hash_text,
    build_ficha_document,
    knowledge_stats,
    sync_cardapio_document,
    sync_contrato_document,
)
from services.embeddings import embeddings_enabled, generate_embeddings  # noqa: E402


def _delete_source(empresa_id: str | None, source_type: str) -> int:
    db = SessionLocal()
    try:
        q = db.query(KnowledgeDocument).filter(KnowledgeDocument.source_type == source_type)
        if empresa_id:
            q = q.filter(KnowledgeDocument.empresa_id == empresa_id)
        count = q.count()
        q.delete(synchronize_session=False)
        db.commit()
        return int(count or 0)
    finally:
        db.close()


def _process_fichas(empresa_id: str | None, batch_size: int) -> int:
    offset = 0
    processed = 0
    while True:
        db = SessionLocal()
        try:
            q = (
                db.query(FichaTecnica)
                .options(
                    selectinload(FichaTecnica.ingredientes_ficha).selectinload(
                        FichaIngrediente.ingrediente
                    )
                )
                .order_by(FichaTecnica.id)
            )
            if empresa_id:
                q = q.filter(FichaTecnica.empresa_id == empresa_id)
            rows = q.offset(offset).limit(batch_size).all()
            if not rows:
                return processed
            chunk_jobs: list[tuple[KnowledgeDocument, int, str, dict]] = []
            for row in rows:
                existing = (
                    db.query(KnowledgeDocument)
                    .filter(
                        KnowledgeDocument.source_type == SOURCE_FICHA,
                        KnowledgeDocument.source_id == str(row.id),
                    )
                    .first()
                )
                if existing:
                    continue
                title, content, metadata = build_ficha_document(row)
                document = KnowledgeDocument(
                    id=str(uuid.uuid4()),
                    empresa_id=str(row.empresa_id),
                    source_type=SOURCE_FICHA,
                    source_id=str(row.id),
                    title=title,
                    content=content,
                    content_hash=_hash_text(content),
                    metadata_json=metadata,
                    active=bool(row.ativo),
                )
                db.add(document)
                db.flush()
                for chunk_index, chunk in enumerate(_chunk_text(content)):
                    chunk_jobs.append((document, chunk_index, chunk, metadata))

            embeddings = []
            if embeddings_enabled() and chunk_jobs:
                embeddings = generate_embeddings([job[2] for job in chunk_jobs])

            for idx, (document, chunk_index, chunk, metadata) in enumerate(chunk_jobs):
                embedding = embeddings[idx] if idx < len(embeddings) else None
                db.add(
                    KnowledgeChunk(
                        id=str(uuid.uuid4()),
                        document_id=document.id,
                        empresa_id=document.empresa_id,
                        source_type=document.source_type,
                        source_id=document.source_id,
                        chunk_index=chunk_index,
                        chunk_text=chunk,
                        chunk_hash=_hash_text(chunk),
                        token_count=len(chunk.split()),
                        embedding=embedding,
                        metadata_json=metadata,
                    )
                )
            db.commit()
            processed += len(rows)
            offset += len(rows)
            print(f"ficha: {processed}", flush=True)
        finally:
            db.close()


def _process_simple(empresa_id: str | None, source_type: str, batch_size: int) -> int:
    model, sync_fn = {
        SOURCE_CONTRATO: (Contrato, sync_contrato_document),
        SOURCE_CARDAPIO: (Cardapio, sync_cardapio_document),
    }[source_type]
    offset = 0
    processed = 0
    while True:
        db = SessionLocal()
        try:
            q = db.query(model).order_by(model.id)
            if empresa_id:
                q = q.filter(model.empresa_id == empresa_id)
            rows = q.offset(offset).limit(batch_size).all()
            if not rows:
                return processed
            for row in rows:
                sync_fn(db, row)
            db.commit()
            processed += len(rows)
            offset += len(rows)
            print(f"{source_type}: {processed}", flush=True)
        finally:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--empresa-id", default=os.getenv("DEFAULT_EMPRESA_ID"))
    parser.add_argument("--source", choices=("all", "contrato", "ficha", "cardapio"), default="all")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    sources = [SOURCE_CONTRATO, SOURCE_FICHA, SOURCE_CARDAPIO] if args.source == "all" else [args.source]
    print(
        {
            "empresa_id": args.empresa_id,
            "sources": sources,
            "batch_size": args.batch_size,
            "force": args.force,
            "embeddings_enabled": embeddings_enabled(),
        },
        flush=True,
    )

    if args.force:
        for source in sources:
            deleted = _delete_source(args.empresa_id, source)
            print(f"deleted {source}: {deleted}", flush=True)

    totals: dict[str, int] = {}
    for source in sources:
        if source == SOURCE_FICHA:
            totals[source] = _process_fichas(args.empresa_id, args.batch_size)
        else:
            totals[source] = _process_simple(args.empresa_id, source, args.batch_size)

    db = SessionLocal()
    try:
        print({"processed": totals, "stats": knowledge_stats(db, empresa_id=args.empresa_id)}, flush=True)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
