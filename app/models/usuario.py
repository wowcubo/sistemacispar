import enum
from datetime import datetime
from sqlalchemy import String, Boolean, Enum, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Papel(str, enum.Enum):
    operador = "operador"
    supervisor = "supervisor"
    gestor = "gestor"


class Setor(str, enum.Enum):
    producao = "Produção"
    manutencao = "Manutenção"
    qualidade = "Qualidade"
    almoxarifado = "Almoxarifado"
    administrativo = "Administrativo"
    geral = "Geral"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    papel: Mapped[Papel] = mapped_column(Enum(Papel), default=Papel.operador)
    setor: Mapped[Setor] = mapped_column(Enum(Setor), default=Setor.geral)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    responsavel_padrao_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    registros_checklist: Mapped[list["RegistroChecklist"]] = relationship(back_populates="operador")
    pendencias_abertas: Mapped[list["Pendencia"]] = relationship(
        back_populates="operador", foreign_keys="Pendencia.operador_id"
    )
    pendencias_responsavel: Mapped[list["Pendencia"]] = relationship(
        back_populates="responsavel", foreign_keys="Pendencia.responsavel_id"
    )
    etapas: Mapped[list["EtapaVerificacao"]] = relationship(back_populates="usuario")
    midias: Mapped[list["ArquivoMidia"]] = relationship(back_populates="enviado_por")
    responsavel_padrao: Mapped["Usuario | None"] = relationship(
        foreign_keys=[responsavel_padrao_id], remote_side="Usuario.id"
    )
