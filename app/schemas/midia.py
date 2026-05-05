from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.midia import TipoMidia, EntidadeTipo


class MidiaResposta(BaseModel):
    id: int
    entidade_tipo: EntidadeTipo
    entidade_id: int
    drive_file_id: str
    drive_url: str
    drive_thumb_url: Optional[str]
    tipo: TipoMidia
    nome_original: str
    tamanho_bytes: Optional[int]
    enviado_por_id: int
    criado_em: datetime

    model_config = {"from_attributes": True}
