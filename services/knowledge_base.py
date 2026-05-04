"""
Indexação e busca semântica sobre Supabase pgvector.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database.connection import DB_PROVIDER, IS_SQLITE
from database.models import (
    Cardapio,
    Contrato,
    FichaTecnica,
    KnowledgeChunk,
    KnowledgeDocument,
)
from services.embeddings import embeddings_enabled, generate_embedding, generate_embeddings


SOURCE_CONTRATO = "contrato"
SOURCE_FICHA = "ficha"
SOURCE_CARDAPIO = "cardapio"
VALID_SOURCE_TYPES = {SOURCE_CONTRATO, SOURCE_FICHA, SOURCE_CARDAPIO}


@dataclass
class ReindexResult:
    source_type: str
    processed: int = 0
    updated: int = 0
    skipped: int = 0


def vector_store_enabled() -> bool:
    return (not IS_SQLITE) and DB_PROVIDER in {"supabase", "postgresql"}


def semantic_search_enabled() -> bool:
    return vector_store_enabled() and embeddings_enabled()


def _norm(text_value: object) -> str:
    if text_value is None:
        return ""
    return re.sub(r"\s+", " ", str(text_value)).strip()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _serialize_json(value: object) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def _chunk_text(value: str, chunk_size: int = 1200, overlap: int = 160) -> list[str]:
    text_value = _norm(value)
    if not text_value:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text_value):
        end = min(len(text_value), start + chunk_size)
        chunk = text_value[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text_value):
            break
        start = max(0, end - overlap)
    return chunks


def _vector_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


def build_contrato_document(contrato: Contrato) -> tuple[str, str, dict]:
    title = f"Contrato {contrato.nome}"
    content = "\n".join(
        [
            f"Contrato: {contrato.nome}",
            f"Número: {contrato.numero_contrato or ''}",
            f"Custo total máximo: {contrato.custo_total_max}",
            f"Custo proteico máximo: {contrato.custo_proteico_max}",
            f"Refeições por dia: {contrato.num_refeicoes_dia}",
            f"Estrutura: {_serialize_json(contrato.estrutura_refeicao)}",
            f"Gramaturas: {_serialize_json(contrato.gramaturas_json)}",
            f"Incidências: {_serialize_json(contrato.incidencias_json)}",
            f"Proibições: {_serialize_json(contrato.proibicoes_json)}",
            f"Regras extraídas: {_serialize_json(contrato.regras_json)}",
            f"Observações: {_norm(contrato.observacoes)}",
        ]
    ).strip()
    metadata = {
        "numero_contrato": contrato.numero_contrato,
        "data_inicio": str(contrato.data_inicio) if contrato.data_inicio else None,
        "data_fim": str(contrato.data_fim) if contrato.data_fim else None,
    }
    return title, content, metadata


def build_ficha_document(ficha: FichaTecnica) -> tuple[str, str, dict]:
    ingredientes = []
    for item in ficha.ingredientes_ficha or []:
        nome = item.ingrediente.nome if item.ingrediente else item.ingrediente_id
        ingredientes.append(
            f"{nome}: bruto={item.quantidade_bruta_g}g fc={item.fator_correcao} custo={item.custo_calculado}"
        )
    title = f"Ficha {ficha.codigo} - {ficha.nome}"
    content = "\n".join(
        [
            f"Código: {ficha.codigo}",
            f"Nome: {ficha.nome}",
            f"Categoria: {ficha.categoria}",
            f"Custo por porção: {ficha.custo_porcao}",
            f"Custo total: {ficha.custo_total}",
            f"Peso porção: {ficha.peso_porcao_g or ''}",
            f"Proteína por porção: {ficha.proteina_porcao or ''}",
            f"Calorias por porção: {ficha.calorias_porcao or ''}",
            f"Modo de preparo: {_norm(ficha.modo_preparo)}",
            f"Observações: {_norm(ficha.observacoes)}",
            "Ingredientes:",
            "\n".join(ingredientes),
        ]
    ).strip()
    metadata = {
        "codigo": ficha.codigo,
        "categoria": ficha.categoria,
        "vegana": ficha.vegana,
        "vegetariana": ficha.vegetariana,
        "contem_gluten": ficha.contem_gluten,
        "contem_lactose": ficha.contem_lactose,
    }
    return title, content, metadata


def build_cardapio_document(cardapio: Cardapio) -> tuple[str, str, dict]:
    title = f"Cardápio {cardapio.nome}"
    content = "\n".join(
        [
            f"Nome: {cardapio.nome}",
            f"Status: {cardapio.status}",
            f"Período: {cardapio.periodo_inicio or ''} até {cardapio.periodo_fim or ''}",
            f"Dias: {cardapio.num_dias or ''}",
            f"Custo médio por dia: {cardapio.custo_medio_dia or ''}",
            f"Parâmetros: {_serialize_json(cardapio.parametros_json)}",
            f"Resultado: {_norm(cardapio.resultado_raw)}",
        ]
    ).strip()
    metadata = {
        "status": cardapio.status,
        "job_id": cardapio.job_id,
        "contrato_id": cardapio.contrato_id,
    }
    return title, content, metadata


def _upsert_document(
    db: Session,
    *,
    empresa_id: Optional[str],
    source_type: str,
    source_id: str,
    title: str,
    content: str,
    metadata: dict,
    active: bool = True,
) -> tuple[KnowledgeDocument, bool]:
    content = _norm(content)
    doc_hash = _hash_text(content)
    document = (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.source_type == source_type, KnowledgeDocument.source_id == source_id)
        .first()
    )
    changed = True
    if document is None:
        document = KnowledgeDocument(
            id=str(uuid.uuid4()),
            empresa_id=empresa_id,
            source_type=source_type,
            source_id=source_id,
        )
        db.add(document)
    else:
        changed = document.content_hash != doc_hash

    document.title = title
    document.content = content
    document.content_hash = doc_hash
    document.metadata_json = metadata
    document.active = active
    document.empresa_id = empresa_id
    db.flush()
    return document, changed


def _replace_chunks(db: Session, document: KnowledgeDocument, chunks: list[str], metadata: dict) -> int:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document.id).delete()
    embeddings = []
    if embeddings_enabled() and chunks:
        embeddings = generate_embeddings(chunks)
    inserted = 0
    for idx, chunk in enumerate(chunks):
        emb = embeddings[idx] if idx < len(embeddings) else None
        db.add(
            KnowledgeChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                empresa_id=document.empresa_id,
                source_type=document.source_type,
                source_id=document.source_id,
                chunk_index=idx,
                chunk_text=chunk,
                chunk_hash=_hash_text(chunk),
                token_count=len(chunk.split()),
                embedding=emb,
                metadata_json=metadata,
            )
        )
        inserted += 1
    db.flush()
    return inserted


def sync_contrato_document(db: Session, contrato: Contrato) -> dict:
    title, content, metadata = build_contrato_document(contrato)
    document, changed = _upsert_document(
        db,
        empresa_id=str(contrato.empresa_id) if contrato.empresa_id else None,
        source_type=SOURCE_CONTRATO,
        source_id=str(contrato.id),
        title=title,
        content=content,
        metadata=metadata,
        active=bool(contrato.ativo),
    )
    chunk_count = 0
    if changed or not document.chunks:
        chunk_count = _replace_chunks(db, document, _chunk_text(content), metadata)
    return {"document_id": document.id, "changed": changed, "chunks": chunk_count}


def sync_ficha_document(db: Session, ficha: FichaTecnica) -> dict:
    title, content, metadata = build_ficha_document(ficha)
    document, changed = _upsert_document(
        db,
        empresa_id=str(ficha.empresa_id),
        source_type=SOURCE_FICHA,
        source_id=str(ficha.id),
        title=title,
        content=content,
        metadata=metadata,
        active=bool(ficha.ativo),
    )
    chunk_count = 0
    if changed or not document.chunks:
        chunk_count = _replace_chunks(db, document, _chunk_text(content), metadata)
    return {"document_id": document.id, "changed": changed, "chunks": chunk_count}


def sync_cardapio_document(db: Session, cardapio: Cardapio) -> dict:
    title, content, metadata = build_cardapio_document(cardapio)
    document, changed = _upsert_document(
        db,
        empresa_id=str(cardapio.empresa_id),
        source_type=SOURCE_CARDAPIO,
        source_id=str(cardapio.id),
        title=title,
        content=content,
        metadata=metadata,
        active=(cardapio.status != "arquivado"),
    )
    chunk_count = 0
    if changed or not document.chunks:
        chunk_count = _replace_chunks(db, document, _chunk_text(content), metadata)
    return {"document_id": document.id, "changed": changed, "chunks": chunk_count}


def reindex_knowledge_base(
    db: Session,
    *,
    empresa_id: Optional[str] = None,
    source_type: str = "all",
) -> dict:
    requested = VALID_SOURCE_TYPES if source_type == "all" else {source_type}
    results: dict[str, dict] = {}

    if SOURCE_CONTRATO in requested:
        res = ReindexResult(source_type=SOURCE_CONTRATO)
        query = db.query(Contrato)
        if empresa_id:
            query = query.filter(Contrato.empresa_id == empresa_id)
        for row in query.all():
            outcome = sync_contrato_document(db, row)
            res.processed += 1
            res.updated += 1 if outcome["changed"] else 0
            res.skipped += 0 if outcome["changed"] else 1
        results[SOURCE_CONTRATO] = res.__dict__

    if SOURCE_FICHA in requested:
        res = ReindexResult(source_type=SOURCE_FICHA)
        query = db.query(FichaTecnica)
        if empresa_id:
            query = query.filter(FichaTecnica.empresa_id == empresa_id)
        for row in query.all():
            outcome = sync_ficha_document(db, row)
            res.processed += 1
            res.updated += 1 if outcome["changed"] else 0
            res.skipped += 0 if outcome["changed"] else 1
        results[SOURCE_FICHA] = res.__dict__

    if SOURCE_CARDAPIO in requested:
        res = ReindexResult(source_type=SOURCE_CARDAPIO)
        query = db.query(Cardapio)
        if empresa_id:
            query = query.filter(Cardapio.empresa_id == empresa_id)
        for row in query.all():
            outcome = sync_cardapio_document(db, row)
            res.processed += 1
            res.updated += 1 if outcome["changed"] else 0
            res.skipped += 0 if outcome["changed"] else 1
        results[SOURCE_CARDAPIO] = res.__dict__

    db.flush()
    return results


def semantic_search(
    db: Session,
    *,
    query: str,
    empresa_id: Optional[str],
    source_types: Optional[list[str]] = None,
    limit: int = 5,
) -> list[dict]:
    if not vector_store_enabled():
        raise RuntimeError("Base vetorial indisponível fora de PostgreSQL/Supabase.")
    if not embeddings_enabled():
        raise RuntimeError("Embeddings não configurados. Defina EMBEDDING_API_KEY.")

    query_embedding = generate_embedding(query)
    literal = _vector_literal(query_embedding)
    source_types = [s for s in (source_types or []) if s in VALID_SOURCE_TYPES]
    if not source_types:
        source_types = [None]

    rows: list[dict] = []
    stmt = text(
        """
        SELECT * FROM match_knowledge_chunks(
          CAST(:query_embedding AS extensions.vector),
          :match_count,
          :filter_empresa_id,
          :filter_source_type
        )
        """
    )
    for stype in source_types:
        result = db.execute(
            stmt,
            {
                "query_embedding": literal,
                "match_count": limit,
                "filter_empresa_id": empresa_id,
                "filter_source_type": stype,
            },
        )
        rows.extend([dict(row._mapping) for row in result])

    rows.sort(key=lambda item: item.get("similarity", 0), reverse=True)
    return rows[:limit]


def knowledge_stats(db: Session, *, empresa_id: Optional[str] = None) -> dict:
    docs_q = db.query(KnowledgeDocument).filter(KnowledgeDocument.active == True)
    chunks_q = db.query(KnowledgeChunk)
    if empresa_id:
        docs_q = docs_q.filter(KnowledgeDocument.empresa_id == empresa_id)
        chunks_q = chunks_q.filter(KnowledgeChunk.empresa_id == empresa_id)
    chunks_embedded = 0
    if vector_store_enabled():
        chunks_embedded = int(chunks_q.filter(KnowledgeChunk.embedding.isnot(None)).count() or 0)
    return {
        "documents": int(docs_q.count() or 0),
        "chunks": int(chunks_q.count() or 0),
        "chunks_embedded": chunks_embedded,
        "source_breakdown": [
            {"source_type": source_type, "count": count}
            for source_type, count in (
                docs_q.with_entities(KnowledgeDocument.source_type, func.count(KnowledgeDocument.id))
                .group_by(KnowledgeDocument.source_type)
                .all()
            )
        ],
        "vector_store_enabled": vector_store_enabled(),
        "embeddings_enabled": embeddings_enabled(),
        "semantic_search_enabled": semantic_search_enabled(),
        "db_provider": DB_PROVIDER,
        "empresa_id": empresa_id,
    }
