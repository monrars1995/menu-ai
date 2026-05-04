"""
Autenticação da app admin: JWT com role `super_admin` ou `admin`, ou
`X-Admin-Api-Key` quando `MENUAI_ADMIN_API_KEY` está definida (impersonação de super_admin).
"""
from __future__ import annotations

import hmac
import os
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Usuario
from routers.auth import decodificar_token

security = HTTPBearer(auto_error=False)


def get_usuario_admin(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-Api-Key"),
) -> Usuario:
    expected = (os.getenv("MENUAI_ADMIN_API_KEY") or "").strip()
    if expected and x_admin_api_key:
        if not hmac.compare_digest(x_admin_api_key.strip(), expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Chave admin inválida.",
            )
        uid = (os.getenv("MENUAI_ADMIN_IMPERSONATE_USER_ID") or "").strip()
        if uid:
            u = db.query(Usuario).filter(Usuario.id == uid, Usuario.ativo == True).first()
            if u:
                return u
        u = (
            db.query(Usuario)
            .filter(Usuario.role == "super_admin", Usuario.ativo == True)
            .first()
        )
        if u:
            return u
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Defina MENUAI_ADMIN_IMPERSONATE_USER_ID ou crie um usuário super_admin.",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Use Authorization: Bearer <JWT> (admin/super_admin) ou X-Admin-Api-Key.",
        )
    payload = decodificar_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )
    usuario = db.query(Usuario).filter(
        Usuario.id == payload.get("sub"),
        Usuario.ativo == True,
    ).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    if usuario.role not in ("super_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso reservado a roles admin ou super_admin.",
        )
    return usuario
