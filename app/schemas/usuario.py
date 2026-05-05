from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.models.usuario import Papel, Setor


class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    papel: Papel = Papel.operador
    setor: Setor = Setor.geral


class UsuarioCriar(UsuarioBase):
    senha: str


class UsuarioAtualizar(BaseModel):
    nome: str | None = None
    papel: Papel | None = None
    setor: Setor | None = None
    ativo: bool | None = None
    senha: str | None = None


class UsuarioResposta(UsuarioBase):
    id: int
    ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResposta
