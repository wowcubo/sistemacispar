from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.usuario import LoginRequest, TokenResposta, UsuarioResposta
from app.services.auth import autenticar_usuario, criar_token, obter_usuario_por_token
from app.models.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    usuario = obter_usuario_por_token(db, token)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    return usuario


def get_current_user_page(request: Request, db: Session = Depends(get_db)) -> Usuario:
    """Para rotas HTML — redireciona para /login em vez de retornar JSON 401."""
    token = request.cookies.get("access_token")
    if not token:
        from fastapi.responses import RedirectResponse
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="redirect:/login")
    usuario = obter_usuario_por_token(db, token)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="redirect:/login")
    return usuario


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Usuario | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    return obter_usuario_por_token(db, token)


@router.post("/login", response_model=TokenResposta)
def login(dados: LoginRequest, response: Response, db: Session = Depends(get_db)):
    usuario = autenticar_usuario(db, dados.email, dados.senha)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha inválidos")
    token = criar_token({"sub": str(usuario.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return TokenResposta(
        access_token=token,
        usuario=UsuarioResposta.model_validate(usuario),
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me", response_model=UsuarioResposta)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario
