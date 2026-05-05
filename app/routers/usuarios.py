from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario, Papel
from app.schemas.usuario import UsuarioCriar, UsuarioAtualizar, UsuarioResposta
from app.services.auth import hash_senha
from app.routers.auth import get_current_user

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def require_gestor(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    if usuario.papel != Papel.gestor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a gestores")
    return usuario


@router.get("/", response_model=list[UsuarioResposta])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(require_gestor)):
    return db.query(Usuario).order_by(Usuario.nome).all()


@router.post("/", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def criar(dados: UsuarioCriar, db: Session = Depends(get_db), _: Usuario = Depends(require_gestor)):
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        papel=dados.papel,
        setor=dados.setor,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.put("/{id}", response_model=UsuarioResposta)
def atualizar(id: int, dados: UsuarioAtualizar, db: Session = Depends(get_db), _: Usuario = Depends(require_gestor)):
    usuario = db.get(Usuario, id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for campo, valor in dados.model_dump(exclude_none=True).items():
        if campo == "senha":
            setattr(usuario, "senha_hash", hash_senha(valor))
        else:
            setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar(id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_gestor)):
    usuario = db.get(Usuario, id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    usuario.ativo = False
    db.commit()
