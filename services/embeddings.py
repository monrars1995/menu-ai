"""
Geração de embeddings via endpoint compatível com OpenAI.

Usado para indexar conhecimento no Supabase/pgvector.
"""
from __future__ import annotations

import os
from typing import Iterable, List

from openai import OpenAI


def embedding_dimension() -> int:
    return int(os.getenv("EMBEDDING_DIMENSION", "1536"))


def embedding_model() -> str:
    return (os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small").strip()


def embedding_base_url() -> str | None:
    val = (os.getenv("EMBEDDING_BASE_URL") or "").strip()
    return val or None


def embedding_api_key() -> str:
    key = (os.getenv("EMBEDDING_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("Configure EMBEDDING_API_KEY para usar a base vetorial.")
    return key


def embeddings_enabled() -> bool:
    return bool((os.getenv("EMBEDDING_API_KEY") or "").strip())


def _client() -> OpenAI:
    kwargs = {"api_key": embedding_api_key()}
    base_url = embedding_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    timeout_raw = (os.getenv("EMBEDDING_REQUEST_TIMEOUT_SECONDS") or "12").strip()
    try:
        kwargs["timeout"] = max(3.0, float(timeout_raw))
    except ValueError:
        kwargs["timeout"] = 12.0
    return OpenAI(**kwargs)


def generate_embeddings(texts: Iterable[str]) -> List[list[float]]:
    payload = [str(text or "").strip() for text in texts]
    if not payload:
        return []
    client = _client()
    resp = client.embeddings.create(
        model=embedding_model(),
        input=payload,
    )
    return [list(item.embedding) for item in resp.data]


def generate_embedding(text: str) -> list[float]:
    rows = generate_embeddings([text])
    return rows[0] if rows else []
