import io
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import get_settings

settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_service():
    from googleapiclient.discovery import build

    if _oauth_disponivel():
        return _service_oauth()

    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _oauth_disponivel() -> bool:
    client_file = Path(settings.google_service_account_file).parent / "oauth_client.json"
    token_file = Path(settings.google_service_account_file).parent / "oauth_token.json"
    return client_file.exists() and token_file.exists()


def _service_oauth():
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_file = Path(settings.google_service_account_file).parent / "oauth_token.json"
    client_file = Path(settings.google_service_account_file).parent / "oauth_client.json"

    with open(client_file) as f:
        client_info = json.load(f)

    installed = client_info.get("installed") or client_info.get("web")

    with open(token_file) as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
        scopes=SCOPES,
    )

    if not creds.valid:
        creds.refresh(Request())
        token_data["token"] = creds.token
        with open(token_file, "w") as f:
            json.dump(token_data, f)

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


def _pasta_destino(service, setor: str, ano_mes: str, entidade_tipo: Optional[str], entidade_id: Optional[int]) -> str:
    """
    Estrutura: root/2026-05/Producao/pendencia_42/
    Se não houver entidade, fica em: root/2026-05/Producao/
    """
    root = settings.google_drive_root_folder_id
    pasta_mes = _obter_ou_criar_pasta(service, ano_mes, root)
    pasta_setor = _obter_ou_criar_pasta(service, setor, pasta_mes)

    if entidade_tipo and entidade_id is not None:
        nome_entidade = f"{entidade_tipo}_{entidade_id}"
        return _obter_ou_criar_pasta(service, nome_entidade, pasta_setor)

    return pasta_setor


def upload_arquivo(
    conteudo: bytes,
    nome_original: str,
    mime_type: str,
    setor: str,
    ano_mes: Optional[str] = None,
    entidade_tipo: Optional[str] = None,
    entidade_id: Optional[int] = None,
) -> dict:
    """Upload para Google Drive. Retorna drive_file_id, drive_url, drive_embed_url, drive_thumb_url."""
    if not settings.google_drive_root_folder_id:
        return _upload_local(conteudo, nome_original, mime_type)

    if not ano_mes:
        ano_mes = datetime.now().strftime("%Y-%m")

    from googleapiclient.http import MediaIoBaseUpload

    service = _get_service()
    pasta_id = _pasta_destino(service, setor, ano_mes, entidade_tipo, entidade_id)

    media = MediaIoBaseUpload(io.BytesIO(conteudo), mimetype=mime_type, resumable=True)
    meta = {"name": nome_original, "parents": [pasta_id]}
    arquivo = service.files().create(body=meta, media_body=media, fields="id").execute()
    file_id = arquivo["id"]

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    drive_url = f"https://drive.google.com/file/d/{file_id}/view"
    embed_url = f"https://drive.google.com/file/d/{file_id}/preview"

    # lh3.googleusercontent.com serve a imagem diretamente sem exigir login Google
    if mime_type.startswith("image"):
        thumb_url = f"https://lh3.googleusercontent.com/d/{file_id}"
    else:
        thumb_url = None

    return {
        "drive_file_id": file_id,
        "drive_url": drive_url,
        "drive_embed_url": embed_url,
        "drive_thumb_url": thumb_url,
    }


def _upload_local(conteudo: bytes, nome_original: str, mime_type: str) -> dict:
    uploads_dir = Path("uploads/dev")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    destino = uploads_dir / nome_original
    destino.write_bytes(conteudo)
    fake_id = f"local_{nome_original}"
    url = f"/uploads/dev/{nome_original}"
    return {
        "drive_file_id": fake_id,
        "drive_url": url,
        "drive_embed_url": url,
        "drive_thumb_url": url if mime_type.startswith("image") else None,
    }
