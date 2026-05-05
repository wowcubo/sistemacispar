import os
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from app.config import get_settings

settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_service():
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _obter_ou_criar_pasta(service, nome: str, parent_id: str) -> str:
    query = (
        f"name='{nome}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    result = service.files().list(q=query, fields="files(id)").execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]

    meta = {
        "name": nome,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def _pasta_setor(service, setor: str, ano_mes: str) -> str:
    root = settings.google_drive_root_folder_id
    pasta_mes = _obter_ou_criar_pasta(service, ano_mes, root)
    pasta_setor = _obter_ou_criar_pasta(service, setor, pasta_mes)
    return pasta_setor


def upload_arquivo(
    conteudo: bytes,
    nome_original: str,
    mime_type: str,
    setor: str,
    ano_mes: Optional[str] = None,
) -> dict:
    """
    Faz upload para o Google Drive e retorna dict com drive_file_id, drive_url, drive_thumb_url.
    Se GOOGLE_DRIVE_ROOT_FOLDER_ID não estiver configurado, salva localmente (modo dev).
    """
    if not settings.google_drive_root_folder_id:
        return _upload_local(conteudo, nome_original, mime_type)

    if not ano_mes:
        ano_mes = datetime.now().strftime("%Y-%m")

    service = _get_service()
    pasta_id = _pasta_setor(service, setor, ano_mes)

    media = MediaIoBaseUpload(io.BytesIO(conteudo), mimetype=mime_type, resumable=True)
    meta = {"name": nome_original, "parents": [pasta_id]}
    arquivo = service.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = arquivo["id"]

    # tornar público para leitura
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    drive_url = f"https://drive.google.com/file/d/{file_id}/view"
    thumb_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w400" if mime_type.startswith("image") else None

    return {"drive_file_id": file_id, "drive_url": drive_url, "drive_thumb_url": thumb_url}


def _upload_local(conteudo: bytes, nome_original: str, mime_type: str) -> dict:
    """Fallback para desenvolvimento sem credenciais do Drive."""
    uploads_dir = Path("uploads/dev")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    destino = uploads_dir / nome_original
    destino.write_bytes(conteudo)
    fake_id = f"local_{nome_original}"
    url = f"/uploads/dev/{nome_original}"
    return {"drive_file_id": fake_id, "drive_url": url, "drive_thumb_url": url if mime_type.startswith("image") else None}
