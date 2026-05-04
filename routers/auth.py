"""
Menu.AI — Router de Autenticação
Endpoints: /api/auth/login, /api/auth/me, /api/auth/refresh
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Usuario
from database.schemas import LoginRequest, TokenResponse, UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])

# ============================================================
# Configuração JWT e Hash de senhas
# ============================================================
SECRET_KEY      = os.getenv("SECRET_KEY", "menuai-secret-key-change-in-production-2026")
ALGORITHM       = "HS256"
TOKEN_EXPIRE_H  = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security    = HTTPBearer(auto_error=False)


# ============================================================
# Funções utilitárias
# ============================================================
def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash_: str) -> bool:
    return pwd_context.verify(senha, hash_)


def criar_token(dados: dict, expira_horas: int = TOKEN_EXPIRE_H) -> str:
    payload = dados.copy()
    if expira_horas > 0:
        payload["exp"] = datetime.utcnow() + timedelta(hours=expira_horas)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ============================================================
# Dependency — usuário autenticado
# ============================================================
def get_usuario_atual(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Extrai e valida o JWT do header Authorization.
    Retorna o usuário autenticado ou lança 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido. Use: Authorization: Bearer <token>",
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
    return usuario


def exigir_role(*roles: str):
    """
    Dependency factory — exige que o usuário tenha um dos roles especificados.

    Uso:
        @router.post("/...")
        def endpoint(usuario = Depends(exigir_role("admin", "nutricionista"))):
    """
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

@router.post("/login", response_model=TokenResponse, summary="Login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Autentica usuário e retorna JWT."""
    usuario = db.query(Usuario).filter(
        Usuario.email == body.email.lower().strip(),
        Usuario.ativo == True,
    ).first()

    if not usuario or not verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )

    # Atualiza último login
    usuario.ultimo_login = datetime.utcnow()
    db.commit()
    db.refresh(usuario)

    token = criar_token({
        "sub": usuario.id,
        "email": usuario.email,
        "role": usuario.role,
        "empresa_id": usuario.empresa_id,
    })

    return TokenResponse(
        access_token=token,
        usuario=UsuarioOut.model_validate(usuario),
    )


@router.get("/me", response_model=UsuarioOut, summary="Dados do usuário logado")
def me(usuario: Usuario = Depends(get_usuario_atual)):
    """Retorna os dados do usuário autenticado."""
    return UsuarioOut.model_validate(usuario)


@router.post("/registro", response_model=UsuarioOut, summary="Registrar novo usuário",
             status_code=status.HTTP_201_CREATED)
def registrar(body: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Cria novo usuário. Em produção fica desativado a menos que ALLOW_OPEN_REGISTRO=true.
    """
    if not (os.getenv("ALLOW_OPEN_REGISTRO", "false").lower() == "true"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registo público desativado. Contacte o administrador ou defina ALLOW_OPEN_REGISTRO no servidor.",
        )
    # Verifica duplicidade de email
    if db.query(Usuario).filter(Usuario.email == body.email.lower()).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    novo = Usuario(
        empresa_id=body.empresa_id,
        nome=body.nome,
        email=body.email.lower().strip(),
        senha_hash=hash_senha(body.senha),
        role=body.role,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return UsuarioOut.model_validate(novo)
