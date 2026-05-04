"""
Menu.AI — Supabase Auth Router
Endpoints: /api/auth/login, /api/auth/registro, /api/auth/me, /api/auth/refresh
Validação: Supabase JWKS (ES256) → service_role → /auth/v1/user → legacy HS256
"""
import os
from datetime import datetime
from typing import Optional

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from supabase import create_client, Client

from database.connection import get_db
from database.models import Usuario
from database.schemas import LoginRequest, TokenResponse, UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])

# ============================================================
# Configuração Supabase
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Chave pública ES256 (cache do JWKS)
_JWKS_PUBKEY: Optional[str] = None

_LEGACY_SECRET = os.getenv("SECRET_KEY", "menuai-secret-key-change-in-production-2026")
security = HTTPBearer(auto_error=False)


def _get_supabase() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"⚠️  Supabase client init failed: {e}")
        return None


# ============================================================
# JWKS — busca chave pública ES256 do Supabase
# ============================================================
def _fetch_jwks_public_key() -> Optional[str]:
    """Busca pubkey ES256 de {SUPABASE_URL}/.well-known/jwks.json e converte para PEM."""
    global _JWKS_PUBKEY
    if not SUPABASE_URL:
        return None
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(f"{SUPABASE_URL}/.well-known/jwks.json")
            if res.status_code != 200:
                return None
            jwks = res.json()
            for k in jwks.get("keys", []):
                if k.get("use") == "sig" and "x5c" in k:
                    cert_pem = f"-----BEGIN CERTIFICATE-----\n{k['x5c'][0]}\n-----END CERTIFICATE-----"
                    cert = load_pem_x509_certificate(cert_pem.encode())
                    _JWKS_PUBKEY = cert.public_key().public_bytes(
                        serialization.Encoding.PEM,
                        serialization.PublicFormat.SubjectPublicKeyInfo,
                    ).decode()
                    return _JWKS_PUBKEY
    except Exception as e:
        print(f"⚠️  JWKS fetch failed: {e}")
    return None


def _get_es256_pubkey() -> Optional[str]:
    """Retorna pubkey ES256 cached ou faz fetch."""
    global _JWKS_PUBKEY
    return _JWKS_PUBKEY or _fetch_jwks_public_key()


# ============================================================
# Validação de token (Supabase ES256 via JWKS → remoto → legacy)
# ============================================================
def decodificar_token(token: str) -> Optional[dict]:
    """Decodifica token Supabase (ES256 via JWKS) ou legacy HS256."""
    # 1) Supabase ES256 via JWKS pubkey
    pub = _get_es256_pubkey()
    if pub:
        try:
            return jwt.decode(token, pub, algorithms=["ES256"], audience="authenticated")
        except JWTError:
            pass
    # 2) Fallback legado (tokens HS256 gerados por nós)
    try:
        return jwt.decode(token, _LEGACY_SECRET, algorithms=["HS256"])
    except JWTError:
        return None


# ============================================================
# Validação remota via Supabase API (fallback)
# ============================================================
async def _validar_token_supabase(token: str) -> Optional[dict]:
    """Valida token via endpoint /auth/v1/user do Supabase (service_role)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
        return None
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_SERVICE_ROLE,
                },
                timeout=10.0,
            )
            if res.status_code == 200:
                data = res.json()
                return {"sub": data.get("id"), "email": data.get("email")}
    except Exception as e:
        print(f"⚠️  Remote Supabase token validation failed: {e}")
    return None


# ============================================================
# Dependency — usuário autenticado
# ============================================================
async def get_usuario_atual(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido. Use: Authorization: Bearer <token>",
        )

    # 1) Decodificar localmente (JWKS ES256 ou legacy)
    payload = decodificar_token(credentials.credentials)

    # 2) Se falhou, validar remotamente via Supabase
    if not payload:
        payload = await _validar_token_supabase(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem sub.",
        )

    usuario = db.query(Usuario).filter(
        Usuario.id == user_id,
        Usuario.ativo == True,
    ).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return usuario


def exigir_role(*roles: str):
    def _check(usuario: Usuario = Depends(get_usuario_atual)) -> Usuario:
        if usuario.role not in roles and usuario.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão negada. Roles permitidos: {list(roles)}",
            )
        return usuario
    return _check


# ============================================================
# Endpoints
# ============================================================

@router.post("/login", response_model=TokenResponse, summary="Login via Supabase Auth")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Autentica via Supabase Auth e retorna JWT + dados do usuário."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.")

    try:
        res = supabase.auth.sign_in_with_password(
            {"email": body.email.lower().strip(), "password": body.senha}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"E-mail ou senha incorretos. ({e})")

    session = getattr(res, "session", None)
    if not session:
        raise HTTPException(status_code=401, detail="Autenticação falhou.")

    access_token = session.access_token
    user_meta = session.user

    usuario = db.query(Usuario).filter(
        Usuario.email == user_meta.email.lower().strip()
    ).first()

    if not usuario:
        usuario = Usuario(
            id=user_meta.id,
            email=user_meta.email.lower().strip(),
            nome=user_meta.user_metadata.get("nome") if user_meta.user_metadata else user_meta.email,
            role=user_meta.user_metadata.get("role", "user") if user_meta.user_metadata else "user",
            ativo=True,
        )
        db.add(usuario)
    else:
        usuario.ultimo_login = datetime.utcnow()
        if str(usuario.id) != str(user_meta.id):
            usuario.id = user_meta.id

    db.commit()
    db.refresh(usuario)

    return TokenResponse(
        access_token=access_token,
        usuario=UsuarioOut.model_validate(usuario),
    )


@router.post("/registro", response_model=UsuarioOut, summary="Registrar via Supabase Auth",
             status_code=status.HTTP_201_CREATED)
def registrar(body: UsuarioCreate, db: Session = Depends(get_db)):
    """Cria conta no Supabase Auth e sincroniza usuário local."""
    if not (os.getenv("ALLOW_OPEN_REGISTRO", "false").lower() == "true"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registo público desativado. Contacte o administrador ou defina ALLOW_OPEN_REGISTRO.",
        )

    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.")

    try:
        res = supabase.auth.sign_up(
            {
                "email": body.email.lower().strip(),
                "password": body.senha,
                "options": {
                    "data": {
                        "nome": body.nome,
                        "role": body.role,
                    }
                },
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha no registro: {e}")

    user_meta = getattr(res, "user", None)
    if not user_meta:
        raise HTTPException(status_code=400, detail="Falha ao criar usuário no Supabase.")

    novo = Usuario(
        id=user_meta.id,
        empresa_id=body.empresa_id,
        nome=body.nome,
        email=user_meta.email.lower().strip(),
        role=body.role,
        ativo=True,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return UsuarioOut.model_validate(novo)


@router.get("/me", response_model=UsuarioOut, summary="Dados do usuário logado")
def me(usuario: Usuario = Depends(get_usuario_atual)):
    """Retorna dados do usuário autenticado (token Supabase ou legado)."""
    return UsuarioOut.model_validate(usuario)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh token Supabase")
def refresh(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Renova token de acesso via refresh token Supabase."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token não fornecido.")

    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Serviço de autenticação indisponível.")

    try:
        res = supabase.auth.refresh_session(credentials.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh falhou: {e}")

    session = getattr(res, "session", None)
    if not session:
        raise HTTPException(status_code=401, detail="Refresh falhou.")

    return TokenResponse(access_token=session.access_token)
