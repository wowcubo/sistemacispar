"""
Script de autorização única do Google Drive via OAuth2.

Execute no servidor APÓS colocar o oauth_client.json em /opt/cispar/credentials/:

    cd /opt/cispar
    venv/bin/python deploy/autorizar_drive.py

Ele vai gerar uma URL — abra no navegador, faça login com a conta Google da empresa
e cole o código de autorização aqui. O token será salvo em credentials/oauth_token.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]
CLIENT_FILE = Path("credentials/oauth_client.json")
TOKEN_FILE = Path("credentials/oauth_token.json")

if not CLIENT_FILE.exists():
    print(f"ERRO: {CLIENT_FILE} não encontrado.")
    print("Baixe o arquivo OAuth no Google Cloud Console e coloque em credentials/oauth_client.json")
    sys.exit(1)

print("=== Autorização do Google Drive para CISPAR ===")
print()
print("Iniciando fluxo OAuth2...")

flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)

# Gera URL para autorização manual (sem abrir browser no servidor)
flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
auth_url, _ = flow.authorization_url(
    access_type="offline",
    prompt="consent",
    include_granted_scopes="true",
)

print("Abra este link no seu navegador:")
print()
print(auth_url)
print()
code = input("Cole aqui o código de autorização: ").strip()

flow.fetch_token(code=code)
creds = flow.credentials

token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
}

TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
TOKEN_FILE.chmod(0o600)

print()
print(f"Token salvo em {TOKEN_FILE}")
print("Autorização concluída! O sistema agora pode fazer uploads para o Drive.")
