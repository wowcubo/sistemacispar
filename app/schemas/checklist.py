from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from app.models.checklist import FrequenciaChecklist, TipoItem, TurnoEnum, StatusRegistro


class ItemChecklistCriar(BaseModel):
    descricao: str
    tipo: TipoItem = TipoItem.sim_nao
    ordem: int = 0
    critico: bool = False


class ItemChecklistResposta(ItemChecklistCriar):
    id: int
    checklist_id: int
    ativo: bool

    model_config = {"from_attributes": True}


class ChecklistCriar(BaseModel):
    nome: str
    setor: str
    descricao: Optional[str] = None
    frequencia: FrequenciaChecklist = FrequenciaChecklist.diario
    itens: list[ItemChecklistCriar] = []


class ChecklistResposta(BaseModel):
    id: int
    nome: str
    setor: str
    descricao: Optional[str]
    frequencia: FrequenciaChecklist
    ativo: bool
    criado_em: datetime
    itens: list[ItemChecklistResposta] = []

    model_config = {"from_attributes": True}


class RespostaItemCriar(BaseModel):
    item_id: int
    resposta: Optional[str] = None
    conforme: Optional[bool] = None
    observacao: Optional[str] = None


class RegistroCriar(BaseModel):
    checklist_id: int
    data: date
    turno: TurnoEnum
    respostas: list[RespostaItemCriar] = []


class RegistroResposta(BaseModel):
    id: int
    checklist_id: int
    operador_id: int
    data: date
    turno: TurnoEnum
    status: StatusRegistro
    criado_em: datetime

    model_config = {"from_attributes": True}
