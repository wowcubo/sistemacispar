from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from pathlib import Path

from app.config import get_settings
from app.database import engine, get_db, Base
from app.models import *  # noqa — registra todos os modelos no metadata
from app.routers import auth, usuarios, pendencias, checklists, uploads, relatorios
from app.routers.auth import get_current_user_optional, get_current_user
from app.models.usuario import Usuario, Papel
from app.models.pendencia import Pendencia, StatusPendencia, Criticidade
from app.models.checklist import Checklist, RegistroChecklist
from app.models.midia import ArquivoMidia, EntidadeTipo

settings = get_settings()

app = FastAPI(title=settings.app_name, docs_url="/api/docs" if settings.debug else None)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Redireciona para /login se 401 e a requisição vem de browser (não API)."""
    if exc.status_code == 401:
        accept = request.headers.get("accept", "")
        # Requisições de browser aceitam HTML; APIs enviam application/json
        if "text/html" in accept:
            return RedirectResponse(url="/login", status_code=303)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Criar tabelas (em produção usar Alembic)
Base.metadata.create_all(bind=engine)

# Static files e templates
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# API routers
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(pendencias.router)
app.include_router(checklists.router)
app.include_router(uploads.router)
app.include_router(relatorios.router)


# ── Páginas HTML ───────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
def pagina_login(request: Request, usuario=Depends(get_current_user_optional)):
    if usuario:
        return RedirectResponse("/")
    return templates.TemplateResponse("login.html", {"request": request, "settings": settings})


@app.post("/login-form")
async def login_form(request: Request, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from app.schemas.usuario import LoginRequest
    form = await request.form()
    email = form.get("email", "")
    senha = form.get("senha", "")
    from app.services.auth import autenticar_usuario, criar_token
    usuario = autenticar_usuario(db, email, senha)
    if not usuario:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "settings": settings, "erro": "Email ou senha inválidos"},
            status_code=401,
        )
    token = criar_token({"sub": str(usuario.id)})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=60 * 60 * 8)
    return response


@app.get("/logout")
def logout_page():
    response = RedirectResponse("/login")
    response.delete_cookie("access_token")
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), usuario: Usuario = Depends(get_current_user)):
    total_pendencias = db.query(Pendencia).count()
    abertas = db.query(Pendencia).filter(Pendencia.status == StatusPendencia.aberta).count()
    em_andamento = db.query(Pendencia).filter(Pendencia.status == StatusPendencia.em_andamento).count()
    resolvidas = db.query(Pendencia).filter(Pendencia.status == StatusPendencia.resolvida).count()
    criticas = db.query(Pendencia).filter(
        Pendencia.criticidade == Criticidade.critica,
        Pendencia.status.in_([StatusPendencia.aberta, StatusPendencia.em_andamento])
    ).count()

    ultimas_pendencias = (
        db.query(Pendencia)
        .order_by(Pendencia.criado_em.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "usuario": usuario,
        "settings": settings,
        "stats": {
            "total": total_pendencias,
            "abertas": abertas,
            "em_andamento": em_andamento,
            "resolvidas": resolvidas,
            "criticas": criticas,
        },
        "ultimas_pendencias": ultimas_pendencias,
    })


@app.get("/pendencias-page", response_class=HTMLResponse)
def pagina_pendencias(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    status: str = "",
    setor: str = "",
    criticidade: str = "",
    responsavel_id: str = "",
    minha: str = "",
    pagina: int = 1,
):
    POR_PAGINA = 10
    q = db.query(Pendencia)

    # Por padrão, operadores veem apenas as suas pendências
    if usuario.papel == Papel.operador:
        q = q.filter(Pendencia.operador_id == usuario.id)
    # Para supervisores/gestores, se "minha" está ativo filtra as do usuário
    elif minha == "1":
        q = q.filter(
            (Pendencia.responsavel_id == usuario.id) | (Pendencia.operador_id == usuario.id)
        )

    if status:
        q = q.filter(Pendencia.status == status)
    else:
        # Por padrão mostra apenas não resolvidas/canceladas
        q = q.filter(Pendencia.status.notin_([StatusPendencia.resolvida, StatusPendencia.cancelada]))
    if setor:
        q = q.filter(Pendencia.setor == setor)
    if criticidade:
        q = q.filter(Pendencia.criticidade == criticidade)
    if responsavel_id:
        q = q.filter(Pendencia.responsavel_id == int(responsavel_id))

    total = q.count()
    total_paginas = max(1, (total + POR_PAGINA - 1) // POR_PAGINA)
    pagina = max(1, min(pagina, total_paginas))
    pendencias_list = q.order_by(Pendencia.criado_em.desc()).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

    from app.models.pendencia import EtapaVerificacao

    # Enriquece com nome do operador, responsável e etapas aguardando aprovação
    def enrich(p):
        op = db.get(Usuario, p.operador_id)
        resp = db.get(Usuario, p.responsavel_id) if p.responsavel_id else None
        pendente = db.query(EtapaVerificacao).filter(
            EtapaVerificacao.pendencia_id == p.id,
            EtapaVerificacao.resultado == None,
        ).count() > 0
        return {
            "pendencia": p,
            "operador_nome": op.nome if op else "—",
            "responsavel_nome": resp.nome if resp else "—",
            "pendente_aprovacao": pendente,
        }

    responsaveis = (
        db.query(Usuario)
        .filter(Usuario.papel.in_([Papel.supervisor, Papel.gestor]), Usuario.ativo == True)
        .order_by(Usuario.nome)
        .all()
    )

    return templates.TemplateResponse("pendencias/list.html", {
        "request": request,
        "usuario": usuario,
        "settings": settings,
        "pendencias": [enrich(p) for p in pendencias_list],
        "filtros": {"status": status, "setor": setor, "criticidade": criticidade, "responsavel_id": responsavel_id, "minha": minha},
        "pagina": pagina,
        "total_paginas": total_paginas,
        "total": total,
        "responsaveis": responsaveis,
    })


@app.get("/pendencias-page/nova", response_class=HTMLResponse)
def pagina_nova_pendencia(request: Request, usuario: Usuario = Depends(get_current_user)):
    return templates.TemplateResponse("pendencias/nova.html", {
        "request": request, "usuario": usuario, "settings": settings,
    })


@app.get("/pendencias-page/{id}", response_class=HTMLResponse)
def pagina_detalhe_pendencia(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    p = (
        db.query(Pendencia)
        .options(selectinload(Pendencia.etapas))
        .filter(Pendencia.id == id)
        .first()
    )
    if not p:
        return RedirectResponse("/pendencias-page")

    midias_pendencia = db.query(ArquivoMidia).filter(
        ArquivoMidia.entidade_tipo == EntidadeTipo.pendencia,
        ArquivoMidia.entidade_id == id,
    ).all()

    def midia_dict(m):
        return {
            "tipo": m.tipo.value,
            "drive_url": m.drive_url,
            "drive_thumb_url": m.drive_thumb_url,
        }

    def nome_usuario(uid):
        u = db.get(Usuario, uid)
        return u.nome if u else "—"

    etapas_com_midia = []
    for e in sorted(p.etapas, key=lambda x: x.numero):
        midias_etapa = db.query(ArquivoMidia).filter(
            ArquivoMidia.entidade_tipo == EntidadeTipo.etapa,
            ArquivoMidia.entidade_id == e.id,
        ).all()
        etapas_com_midia.append({
            "etapa": e,
            "midias": midias_etapa,
            "midias_json": [midia_dict(m) for m in midias_etapa],
            "usuario_nome": nome_usuario(e.usuario_id),
        })

    operador = db.get(Usuario, p.operador_id)
    responsavel = db.get(Usuario, p.responsavel_id) if p.responsavel_id else None

    return templates.TemplateResponse("pendencias/detalhe.html", {
        "request": request,
        "usuario": usuario,
        "settings": settings,
        "pendencia": p,
        "midias": midias_pendencia,
        "midias_json": [midia_dict(m) for m in midias_pendencia],
        "etapas": etapas_com_midia,
        "operador_nome": operador.nome if operador else "—",
        "responsavel_nome": responsavel.nome if responsavel else None,
    })


@app.get("/checklists-page", response_class=HTMLResponse)
def pagina_checklists(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    checklists_list = (
        db.query(Checklist)
        .options(selectinload(Checklist.itens))
        .filter(Checklist.ativo == True)
        .order_by(Checklist.nome)
        .all()
    )
    return templates.TemplateResponse("checklists/list.html", {
        "request": request, "usuario": usuario, "settings": settings,
        "checklists": checklists_list,
    })


@app.get("/checklists-page/{id}/preencher", response_class=HTMLResponse)
def pagina_preencher(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    c = (
        db.query(Checklist)
        .options(selectinload(Checklist.itens))
        .filter(Checklist.id == id, Checklist.ativo == True)
        .first()
    )
    if not c:
        return RedirectResponse("/checklists-page")
    return templates.TemplateResponse("checklists/preencher.html", {
        "request": request, "usuario": usuario, "settings": settings, "checklist": c,
    })


@app.get("/admin/usuarios", response_class=HTMLResponse)
def pagina_admin_usuarios(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    if usuario.papel != Papel.gestor:
        return RedirectResponse("/")
    users = db.query(Usuario).order_by(Usuario.nome).all()
    return templates.TemplateResponse("admin/usuarios.html", {
        "request": request, "usuario": usuario, "settings": settings, "usuarios": users,
    })
