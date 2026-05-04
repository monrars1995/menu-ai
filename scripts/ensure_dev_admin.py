#!/usr/bin/env python3
"""
Garante empresa de teste + utilizador super_admin para desenvolvimento local.

Corre apenas com DEBUG=true (ou MENUAI_ENSURE_DEV_ADMIN=true explicitamente).
Não usar em produção.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "").lower() == "true"
FORCE = os.getenv("MENUAI_ENSURE_DEV_ADMIN", "").lower() == "true"
if not DEBUG and not FORCE:
    print("ensure_dev_admin: ignorado (defina DEBUG=true ou MENUAI_ENSURE_DEV_ADMIN=true)")
    sys.exit(0)

DEFAULT_EMPRESA_ID = os.getenv("DEFAULT_EMPRESA_ID", "00000000-0000-0000-0000-000000000001").strip()
EMAIL = os.getenv("MENUAI_DEV_ADMIN_EMAIL", "admin-dev@menuai.local").strip().lower()
PASSWORD = os.getenv("MENUAI_DEV_ADMIN_PASSWORD", "MenuAI_dev_2026")
NOME = os.getenv("MENUAI_DEV_ADMIN_NOME", "Admin Dev")

from database.connection import SessionLocal, verificar_conexao  # noqa: E402
from database.models import Empresa, Usuario  # noqa: E402
from routers.auth import hash_senha  # noqa: E402


def main() -> int:
    if not verificar_conexao():
        print("ensure_dev_admin: BD indisponível — verifique DATABASE_URL")
        return 1

    db = SessionLocal()
    try:
        emp = db.query(Empresa).filter(Empresa.id == DEFAULT_EMPRESA_ID).first()
        if not emp:
            emp = Empresa(
                id=DEFAULT_EMPRESA_ID,
                nome="Empresa Dev (admin)",
                ativo=True,
            )
            db.add(emp)
            db.commit()
            print(f"ensure_dev_admin: empresa de teste criada ({DEFAULT_EMPRESA_ID})")
        else:
            print("ensure_dev_admin: empresa de teste já existe")

        u = db.query(Usuario).filter(Usuario.email == EMAIL).first()
        h = hash_senha(PASSWORD)
        if u:
            u.role = "super_admin"
            u.senha_hash = h
            u.ativo = True
            u.empresa_id = DEFAULT_EMPRESA_ID
            db.commit()
            print(f"ensure_dev_admin: utilizador actualizado → {EMAIL} (super_admin)")
        else:
            import uuid

            novo = Usuario(
                id=str(uuid.uuid4()),
                empresa_id=DEFAULT_EMPRESA_ID,
                nome=NOME,
                email=EMAIL,
                senha_hash=h,
                role="super_admin",
                ativo=True,
            )
            db.add(novo)
            db.commit()
            print(f"ensure_dev_admin: utilizador criado → {EMAIL} (super_admin)")
        print()
        print("  Login no admin: POST /api/auth/login")
        print(f"    email:    {EMAIL}")
        print(f"    senha:    {PASSWORD}")
        print()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
