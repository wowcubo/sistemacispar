import mimetypes
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.models.midia import ArquivoMidia, TipoMidia, EntidadeTipo
from app.schemas.midia import MidiaResposta
from app.services import drive
from app.routers.auth import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

MIME_FOTO = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MIME_VIDEO = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
MAX_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB


@router.post("/", response_model=MidiaResposta, status_code=201)
async def upload(
    arquivo: UploadFile = File(...),
    entidade_tipo: EntidadeTipo = Form(...),
    entidade_id: int = Form(...),
    setor: str = Form("Geral"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    conteudo = await arquivo.read()
    if len(conteudo) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede 200 MB")

    mime = arquivo.content_type or mimetypes.guess_type(arquivo.filename or "")[0] or ""
    if mime in MIME_FOTO:
        tipo = TipoMidia.foto
    elif mime in MIME_VIDEO:
        tipo = TipoMidia.video
    else:
        raise HTTPException(status_code=415, detail=f"Tipo de arquivo não suportado: {mime}")

    resultado = drive.upload_arquivo(
        conteudo=conteudo,
        nome_original=arquivo.filename or "arquivo",
        mime_type=mime,
        setor=setor,
        entidade_tipo=entidade_tipo.value,
        entidade_id=entidade_id,
    )

    midia = ArquivoMidia(
        entidade_tipo=entidade_tipo,
        entidade_id=entidade_id,
        drive_file_id=resultado["drive_file_id"],
        drive_url=resultado["drive_url"],
        drive_thumb_url=resultado.get("drive_thumb_url"),
        tipo=tipo,
        nome_original=arquivo.filename or "arquivo",
        tamanho_bytes=len(conteudo),
        enviado_por_id=usuario.id,
    )
    db.add(midia)
    db.commit()
    db.refresh(midia)
    return midia
