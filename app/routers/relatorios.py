from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from app.database import get_db
from app.models.usuario import Usuario
from app.services.relatorio import gerar_pdf_pendencias
from app.routers.auth import get_current_user

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


@router.get("/pdf")
def exportar_pdf(
    setor: str | None = Query(None),
    mes: str | None = Query(None, description="AAAA-MM"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    buffer = gerar_pdf_pendencias(db, setor=setor, mes=mes)
    nome = f"cispar_relatorio_{mes or 'geral'}.pdf"
    return StreamingResponse(
        BytesIO(buffer),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
