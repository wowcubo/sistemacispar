from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models.usuario import Usuario, Papel
from app.models.checklist import (
    Checklist, ItemChecklist, RegistroChecklist, RespostaItem, StatusRegistro
)
from app.models.pendencia import Pendencia, Criticidade, StatusPendencia
from app.schemas.checklist import (
    ChecklistCriar, ChecklistResposta, RegistroCriar, RegistroResposta
)
from app.routers.auth import get_current_user

router = APIRouter(prefix="/checklists", tags=["checklists"])


@router.get("/", response_model=list[ChecklistResposta])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    return (
        db.query(Checklist)
        .options(selectinload(Checklist.itens))
        .filter(Checklist.ativo == True)
        .order_by(Checklist.nome)
        .all()
    )


@router.post("/", response_model=ChecklistResposta, status_code=201)
def criar(
    dados: ChecklistCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    if usuario.papel == Papel.operador:
        raise HTTPException(status_code=403, detail="Somente supervisores e gestores podem criar checklists")

    checklist = Checklist(
        nome=dados.nome,
        setor=dados.setor,
        descricao=dados.descricao,
        frequencia=dados.frequencia,
    )
    db.add(checklist)
    db.flush()

    for i, item_data in enumerate(dados.itens):
        item = ItemChecklist(
            checklist_id=checklist.id,
            descricao=item_data.descricao,
            tipo=item_data.tipo,
            ordem=item_data.ordem or i,
            critico=item_data.critico,
        )
        db.add(item)

    db.commit()
    db.refresh(checklist)
    return checklist


@router.get("/{id}", response_model=ChecklistResposta)
def detalhe(id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    c = db.query(Checklist).options(selectinload(Checklist.itens)).filter(Checklist.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")
    return c


# ── Registros (execuções) ─────────────────────────────────────────────────────

@router.post("/registros", response_model=RegistroResposta, status_code=201)
def criar_registro(
    dados: RegistroCriar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    checklist = db.query(Checklist).options(selectinload(Checklist.itens)).filter(
        Checklist.id == dados.checklist_id, Checklist.ativo == True
    ).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist não encontrado")

    registro = RegistroChecklist(
        checklist_id=dados.checklist_id,
        operador_id=usuario.id,
        data=dados.data,
        turno=dados.turno,
    )
    db.add(registro)
    db.flush()

    itens_por_id = {i.id: i for i in checklist.itens}

    for resp_data in dados.respostas:
        item = itens_por_id.get(resp_data.item_id)
        if not item:
            continue
        resposta = RespostaItem(
            registro_id=registro.id,
            item_id=resp_data.item_id,
            resposta=resp_data.resposta,
            conforme=resp_data.conforme,
            observacao=resp_data.observacao,
        )
        db.add(resposta)

        if resp_data.conforme is False and item.critico:
            _criar_pendencia_automatica(db, usuario, registro, item, checklist.setor)

    registro.status = StatusRegistro.concluido
    db.commit()
    db.refresh(registro)
    return registro


def _criar_pendencia_automatica(
    db: Session,
    usuario: Usuario,
    registro: RegistroChecklist,
    item: ItemChecklist,
    setor: str,
):
    pendencia = Pendencia(
        titulo=f"[AUTO] {item.descricao}",
        descricao=f"Item crítico não conforme no checklist do dia {registro.data} turno {registro.turno.value}.",
        setor=setor,
        criticidade=Criticidade.maior,
        operador_id=usuario.id,
        registro_id=registro.id,
        status=StatusPendencia.aberta,
    )
    db.add(pendencia)


@router.get("/registros/{id}", response_model=RegistroResposta)
def detalhe_registro(id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    r = db.get(RegistroChecklist, id)
    if not r:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return r
