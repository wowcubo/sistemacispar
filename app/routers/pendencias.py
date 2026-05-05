from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models.usuario import Usuario, Papel
from app.models.pendencia import Pendencia, EtapaVerificacao, StatusPendencia, ResultadoEtapa
from app.models.midia import ArquivoMidia, EntidadeTipo
from app.schemas.pendencia import (
    PendenciaCriar, PendenciaAtualizar, PendenciaResposta,
    EtapaCriar, EtapaAprovar, EtapaResposta,
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/pendencias", tags=["pendencias"])


def _load_pendencia(db: Session, id: int) -> Pendencia:
    p = (
        db.query(Pendencia)
        .options(selectinload(Pendencia.etapas))
        .filter(Pendencia.id == id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    return p


def _pendencia_to_resp(p: Pendencia, db: Session) -> PendenciaResposta:
    midias = db.query(ArquivoMidia).filter(
        ArquivoMidia.entidade_tipo == EntidadeTipo.pendencia,
        ArquivoMidia.entidade_id == p.id,
    ).all()
    data = PendenciaResposta.model_validate(p)
    data.total_etapas = len(p.etapas)
    data.midias = midias  # type: ignore
    return data


@router.get("/", response_model=list[PendenciaResposta])
def listar(
    setor: str | None = Query(None),
    status: StatusPendencia | None = Query(None),
    criticidade: str | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    q = db.query(Pendencia).options(selectinload(Pendencia.etapas))
    if usuario.papel == Papel.operador:
        q = q.filter(Pendencia.operador_id == usuario.id)
    if setor:
        q = q.filter(Pendencia.setor == setor)
    if status:
        q = q.filter(Pendencia.status == status)
    if criticidade:
        q = q.filter(Pendencia.criticidade == criticidade)
    pendencias = q.order_by(Pendencia.criado_em.desc()).all()
    return [_pendencia_to_resp(p, db) for p in pendencias]


@router.post("/", response_model=PendenciaResposta, status_code=201)
def criar(
    dados: PendenciaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    p = Pendencia(
        titulo=dados.titulo,
        descricao=dados.descricao,
        setor=dados.setor,
        criticidade=dados.criticidade,
        data_limite=dados.data_limite,
        supervisor_id=dados.supervisor_id,
        registro_id=dados.registro_id,
        operador_id=usuario.id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _pendencia_to_resp(p, db)


@router.get("/{id}", response_model=PendenciaResposta)
def detalhe(id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    p = _load_pendencia(db, id)
    return _pendencia_to_resp(p, db)


@router.put("/{id}", response_model=PendenciaResposta)
def atualizar(
    id: int,
    dados: PendenciaAtualizar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    p = _load_pendencia(db, id)
    if usuario.papel == Papel.operador and p.operador_id != usuario.id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    return _pendencia_to_resp(p, db)


# ── Etapas ────────────────────────────────────────────────────────────────────

@router.post("/{id}/etapas", response_model=EtapaResposta, status_code=201)
def criar_etapa(
    id: int,
    dados: EtapaCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    p = _load_pendencia(db, id)
    if p.status in (StatusPendencia.resolvida, StatusPendencia.cancelada):
        raise HTTPException(status_code=400, detail="Pendência já encerrada")

    numero = len(p.etapas) + 1
    etapa = EtapaVerificacao(
        pendencia_id=p.id,
        numero=numero,
        descricao_acao=dados.descricao_acao,
        resultado=dados.resultado,
        observacoes=dados.observacoes,
        usuario_id=usuario.id,
    )
    db.add(etapa)

    if p.status == StatusPendencia.aberta:
        p.status = StatusPendencia.em_andamento

    db.commit()
    db.refresh(etapa)
    return _etapa_to_resp(etapa, db)


@router.put("/{id}/etapas/{etapa_id}/aprovar", response_model=EtapaResposta)
def aprovar_etapa(
    id: int,
    etapa_id: int,
    dados: EtapaAprovar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    if usuario.papel == Papel.operador:
        raise HTTPException(status_code=403, detail="Somente supervisores e gestores podem aprovar etapas")

    p = _load_pendencia(db, id)
    etapa = db.query(EtapaVerificacao).filter(
        EtapaVerificacao.id == etapa_id,
        EtapaVerificacao.pendencia_id == id,
    ).first()
    if not etapa:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")

    etapa.resultado = dados.resultado
    etapa.observacoes = dados.observacoes

    if dados.resultado == ResultadoEtapa.conforme:
        p.status = StatusPendencia.resolvida
        p.data_resolucao = date.today()
    else:
        p.status = StatusPendencia.em_andamento

    db.commit()
    db.refresh(etapa)
    return _etapa_to_resp(etapa, db)


@router.get("/{id}/etapas", response_model=list[EtapaResposta])
def listar_etapas(id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    etapas = db.query(EtapaVerificacao).filter(
        EtapaVerificacao.pendencia_id == id
    ).order_by(EtapaVerificacao.numero).all()
    return [_etapa_to_resp(e, db) for e in etapas]


def _etapa_to_resp(etapa: EtapaVerificacao, db: Session) -> EtapaResposta:
    midias = db.query(ArquivoMidia).filter(
        ArquivoMidia.entidade_tipo == EntidadeTipo.etapa,
        ArquivoMidia.entidade_id == etapa.id,
    ).all()
    data = EtapaResposta.model_validate(etapa)
    data.midias = midias  # type: ignore
    return data
