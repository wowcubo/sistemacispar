from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models.usuario import Papel, Setor


class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr
    papel: Papel = Papel.operador
    setor: Setor = Setor.geral


class UsuarioCriar(UsuarioBase):
    senha: str
    responsavel_padrao_id: Optional[int] = None


class UsuarioAtualizar(BaseModel):
    nome: Optional[str] = None
    papel: Optional[Papel] = None
    setor: Optional[Setor] = None
    ativo: Optional[bool] = None
    senha: Optional[str] = None
    responsavel_padrao_id: Optional[int] = None


class UsuarioResposta(UsuarioBase):
    id: int
    ativo: bool
    responsavel_padrao_id: Optional[int] = None
    criado_em: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResposta
