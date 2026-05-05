import enum
from datetime import datetime, date
from sqlalchemy import String, Enum, DateTime, Date, Integer, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Criticidade(str, enum.Enum):
    critica = "critica"
    maior = "maior"
    menor = "menor"


class StatusPendencia(str, enum.Enum):
    aberta = "aberta"
    em_andamento = "em_andamento"
    aguardando_aprovacao = "aguardando_aprovacao"
    resolvida = "resolvida"
    cancelada = "cancelada"


class ResultadoEtapa(str, enum.Enum):
    conforme = "conforme"
    nao_conforme = "nao_conforme"
    parcial = "parcial"


class Pendencia(Base):
    __tablename__ = "pendencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    setor: Mapped[str] = mapped_column(String(50))
    criticidade: Mapped[Criticidade] = mapped_column(Enum(Criticidade))
    status: Mapped[StatusPendencia] = mapped_column(
        Enum(StatusPendencia), default=StatusPendencia.aberta
    )
    data_abertura: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    data_limite: Mapped[date | None] = mapped_column(Date)
    data_resolucao: Mapped[date | None] = mapped_column(Date)

    operador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    responsavel_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    registro_id: Mapped[int | None] = mapped_column(ForeignKey("registros_checklist.id"))

    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    operador: Mapped["Usuario"] = relationship(
        back_populates="pendencias_abertas", foreign_keys=[operador_id]
    )
    supervisor: Mapped["Usuario | None"] = relationship(foreign_keys=[supervisor_id])
    responsavel: Mapped["Usuario | None"] = relationship(
        foreign_keys=[responsavel_id], back_populates="pendencias_responsavel"
    )
    registro: Mapped["RegistroChecklist | None"] = relationship()
    etapas: Mapped[list["EtapaVerificacao"]] = relationship(
        back_populates="pendencia", order_by="EtapaVerificacao.numero", cascade="all, delete-orphan"
    )
    midias: Mapped[list["ArquivoMidia"]] = relationship(
        "ArquivoMidia",
        primaryjoin="and_(ArquivoMidia.entidade_tipo=='pendencia', foreign(ArquivoMidia.entidade_id)==Pendencia.id)",
        viewonly=True,
    )


class EtapaVerificacao(Base):
    __tablename__ = "etapas_verificacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    pendencia_id: Mapped[int] = mapped_column(ForeignKey("pendencias.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(Integer)
    descricao_acao: Mapped[str] = mapped_column(Text)
    resultado: Mapped[ResultadoEtapa | None] = mapped_column(Enum(ResultadoEtapa))
    observacoes: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    data: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pendencia: Mapped["Pendencia"] = relationship(back_populates="etapas")
    usuario: Mapped["Usuario"] = relationship(back_populates="etapas")
    midias: Mapped[list["ArquivoMidia"]] = relationship(
        "ArquivoMidia",
        primaryjoin="and_(ArquivoMidia.entidade_tipo=='etapa', foreign(ArquivoMidia.entidade_id)==EtapaVerificacao.id)",
        viewonly=True,
    )
