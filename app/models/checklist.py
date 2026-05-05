import enum
from datetime import datetime, date
from sqlalchemy import String, Boolean, Enum, DateTime, Date, Integer, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FrequenciaChecklist(str, enum.Enum):
    diario = "diario"
    semanal = "semanal"
    mensal = "mensal"


class TipoItem(str, enum.Enum):
    sim_nao = "sim_nao"
    texto = "texto"
    numerico = "numerico"
    foto_obrigatoria = "foto_obrigatoria"


class TurnoEnum(str, enum.Enum):
    manha = "manha"
    tarde = "tarde"
    noite = "noite"


class StatusRegistro(str, enum.Enum):
    em_andamento = "em_andamento"
    concluido = "concluido"


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    setor: Mapped[str] = mapped_column(String(50))
    descricao: Mapped[str | None] = mapped_column(Text)
    frequencia: Mapped[FrequenciaChecklist] = mapped_column(
        Enum(FrequenciaChecklist), default=FrequenciaChecklist.diario
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    itens: Mapped[list["ItemChecklist"]] = relationship(
        back_populates="checklist", order_by="ItemChecklist.ordem", cascade="all, delete-orphan"
    )
    registros: Mapped[list["RegistroChecklist"]] = relationship(back_populates="checklist")


class ItemChecklist(Base):
    __tablename__ = "itens_checklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id", ondelete="CASCADE"))
    descricao: Mapped[str] = mapped_column(String(300))
    tipo: Mapped[TipoItem] = mapped_column(Enum(TipoItem), default=TipoItem.sim_nao)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    critico: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    checklist: Mapped["Checklist"] = relationship(back_populates="itens")
    respostas: Mapped[list["RespostaItem"]] = relationship(back_populates="item")


class RegistroChecklist(Base):
    __tablename__ = "registros_checklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"))
    operador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    data: Mapped[date] = mapped_column(Date)
    turno: Mapped[TurnoEnum] = mapped_column(Enum(TurnoEnum))
    status: Mapped[StatusRegistro] = mapped_column(
        Enum(StatusRegistro), default=StatusRegistro.em_andamento
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    checklist: Mapped["Checklist"] = relationship(back_populates="registros")
    operador: Mapped["Usuario"] = relationship(back_populates="registros_checklist")
    respostas: Mapped[list["RespostaItem"]] = relationship(
        back_populates="registro", cascade="all, delete-orphan"
    )


class RespostaItem(Base):
    __tablename__ = "respostas_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    registro_id: Mapped[int] = mapped_column(ForeignKey("registros_checklist.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens_checklist.id"))
    resposta: Mapped[str | None] = mapped_column(String(500))
    conforme: Mapped[bool | None] = mapped_column(Boolean)
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    registro: Mapped["RegistroChecklist"] = relationship(back_populates="respostas")
    item: Mapped["ItemChecklist"] = relationship(back_populates="respostas")
    midias: Mapped[list["ArquivoMidia"]] = relationship(
        "ArquivoMidia",
        primaryjoin="and_(ArquivoMidia.entidade_tipo=='resposta', foreign(ArquivoMidia.entidade_id)==RespostaItem.id)",
        viewonly=True,
    )
