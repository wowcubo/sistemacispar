from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.usuario import Usuario

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload["exp"] = expire
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decodificar_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


def autenticar_usuario(db: Session, email: str, senha: str) -> Optional[Usuario]:
    usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.ativo == True).first()
    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


def obter_usuario_por_token(db: Session, token: str) -> Optional[Usuario]:
    payload = decodificar_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(Usuario).filter(Usuario.id == int(user_id), Usuario.ativo == True).first()
