import enum
from datetime import datetime
from sqlalchemy import String, Enum, DateTime, Integer, BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TipoMidia(str, enum.Enum):
    foto = "foto"
    video = "video"


class EntidadeTipo(str, enum.Enum):
    pendencia = "pendencia"
    etapa = "etapa"
    resposta = "resposta"


class ArquivoMidia(Base):
    __tablename__ = "arquivos_midia"

    id: Mapped[int] = mapped_column(primary_key=True)
    entidade_tipo: Mapped[EntidadeTipo] = mapped_column(Enum(EntidadeTipo))
    entidade_id: Mapped[int] = mapped_column(Integer)

    drive_file_id: Mapped[str] = mapped_column(String(200))
    drive_url: Mapped[str] = mapped_column(String(500))
    drive_thumb_url: Mapped[str | None] = mapped_column(String(500))

    tipo: Mapped[TipoMidia] = mapped_column(Enum(TipoMidia))
    nome_original: Mapped[str] = mapped_column(String(255))
    tamanho_bytes: Mapped[int | None] = mapped_column(BigInteger)

    enviado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    enviado_por: Mapped["Usuario"] = relationship(back_populates="midias")
