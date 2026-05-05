from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from app.models.pendencia import Criticidade, StatusPendencia, ResultadoEtapa
from app.schemas.midia import MidiaResposta


class PendenciaCriar(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    setor: str
    criticidade: Criticidade
    data_limite: Optional[date] = None
    supervisor_id: Optional[int] = None
    responsavel_id: Optional[int] = None
    registro_id: Optional[int] = None


class PendenciaAtualizar(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    criticidade: Optional[Criticidade] = None
    status: Optional[StatusPendencia] = None
    data_limite: Optional[date] = None
    supervisor_id: Optional[int] = None
    responsavel_id: Optional[int] = None


class PendenciaResposta(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str]
    setor: str
    criticidade: Criticidade
    status: StatusPendencia
    data_abertura: date
    data_limite: Optional[date]
    data_resolucao: Optional[date]
    operador_id: int
    operador_nome: Optional[str] = None
    supervisor_id: Optional[int]
    responsavel_id: Optional[int]
    responsavel_nome: Optional[str] = None
    registro_id: Optional[int]
    criado_em: datetime
    total_etapas: int = 0
    midias: list[MidiaResposta] = []

    model_config = {"from_attributes": True}


class EtapaCriar(BaseModel):
    descricao_acao: str
    resultado: Optional[ResultadoEtapa] = None
    observacoes: Optional[str] = None


class EtapaAprovar(BaseModel):
    resultado: ResultadoEtapa
    observacoes: Optional[str] = None


class EtapaResposta(BaseModel):
    id: int
    pendencia_id: int
    numero: int
    descricao_acao: str
    resultado: Optional[ResultadoEtapa]
    observacoes: Optional[str]
    usuario_id: int
    usuario_nome: Optional[str] = None
    data: datetime
    midias: list[MidiaResposta] = []

    model_config = {"from_attributes": True}
