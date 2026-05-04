#!/usr/bin/env python3
"""
Repara bancos SQLite de desenvolvimento criados por versões antigas do ORM.

Algumas bases locais foram criadas com colunas UUID usando afinidade NUMERIC no
SQLite. Quando o seed inicial entrava antes da normalização, a empresa de teste
podia ficar como id inteiro `1`, enquanto a aplicação usa o UUID fixo abaixo.
Este script preserva os dados e realinha as FKs para o UUID esperado.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from database.connection import IS_SQLITE, engine

TEST_EMPRESA_ID = os.getenv(
    "DEFAULT_EMPRESA_ID", "00000000-0000-0000-0000-000000000001"
).strip()


def _table_exists(conn, table: str) -> bool:
    return (
        conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        ).fetchone()
        is not None
    )


def main() -> int:
    if not IS_SQLITE:
        print("Nada a fazer: DATABASE_URL não é SQLite.")
        return 0

    empresa_tables = [
        "usuarios",
        "contratos",
        "fichas_tecnicas",
        "cardapios",
        "jobs_agente",
    ]

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))

        empresas = conn.execute(text("SELECT id, nome FROM empresas")).fetchall()
        legacy_ids = [row.id for row in empresas if str(row.id) != TEST_EMPRESA_ID]

        if not empresas:
            conn.execute(
                text(
                    "INSERT INTO empresas (id, nome, ativo, created_at, updated_at) "
                    "VALUES (:id, 'Empresa Teste', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {"id": TEST_EMPRESA_ID},
            )
            print(f"Empresa de teste criada: {TEST_EMPRESA_ID}")
        elif not conn.execute(
            text("SELECT 1 FROM empresas WHERE id = :id"), {"id": TEST_EMPRESA_ID}
        ).fetchone():
            primary = legacy_ids[0]
            conn.execute(
                text("UPDATE empresas SET id = :new_id WHERE id = :old_id"),
                {"new_id": TEST_EMPRESA_ID, "old_id": primary},
            )
            print(f"Empresa principal normalizada: {primary!r} -> {TEST_EMPRESA_ID}")

        for old_id in legacy_ids:
            if str(old_id) == TEST_EMPRESA_ID:
                continue
            for table in empresa_tables:
                if not _table_exists(conn, table):
                    continue
                conn.execute(
                    text(f"UPDATE {table} SET empresa_id = :new_id WHERE empresa_id = :old_id"),
                    {"new_id": TEST_EMPRESA_ID, "old_id": old_id},
                )

        conn.execute(text("PRAGMA foreign_keys=ON"))

    print("SQLite de desenvolvimento normalizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
