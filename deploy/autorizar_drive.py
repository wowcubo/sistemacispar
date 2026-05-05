"""
Script de autorização única do Google Drive via OAuth2.

Passo 1 — gerar a URL:
    cd /opt/cispar
    venv/bin/python deploy/autorizar_drive.py

Passo 2 — após autorizar no browser, passar o código:
    venv/bin/python deploy/autorizar_drive.py --codigo SEU_CODIGO_AQUI
"""
import json
import sys
import argparse
import requests
from pathlib import Path

CLIENT_FILE = Path("credentials/oauth_client.json")
TOKEN_FILE  = Path("credentials/oauth_token.json")
REDIRECT    = "urn:ietf:wg:oauth:2.0:oob"
SCOPE       = "https://www.googleapis.com/auth/drive"

if not CLIENT_FILE.exists():
    print(f"ERRO: {CLIENT_FILE} não encontrado.")
    sys.exit(1)

with open(CLIENT_FILE) as f:
    info = json.load(f).get("installed") or json.load(open(CLIENT_FILE)).get("web")

CLIENT_ID     = info["client_id"]
CLIENT_SECRET = info["client_secret"]
AUTH_URI      = info.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
TOKEN_URI     = info.get("token_uri", "https://oauth2.googleapis.com/token")

parser = argparse.ArgumentParser()
parser.add_argument("--codigo", help="Código retornado pelo Google após autorizar")
args = parser.parse_args()

if not args.codigo:
    # Passo 1: mostrar URL
    url = (
        f"{AUTH_URI}?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT}"
        f"&scope={SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    print("=== Autorização do Google Drive para CISPAR ===")
    print()
    print("Abra este link no navegador (conta Google da empresa):")
    print()
    print(url)
    print()
    print("Após autorizar, copie o código e rode:")
    print(f"  venv/bin/python deploy/autorizar_drive.py --codigo SEU_CODIGO")
    sys.exit(0)

# Passo 2: trocar código por token
print("Trocando código por token...")
resp = requests.post(TOKEN_URI, data={
    "code":          args.codigo,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT,
    "grant_type":    "authorization_code",
})

if not resp.ok:
    print("ERRO:", resp.text)
    sys.exit(1)

data = resp.json()
if "refresh_token" not in data:
    print("ERRO: refresh_token não retornado. Tente revogar o acesso no Google e repetir.")
    print(data)
    sys.exit(1)

token_data = {
    "token":         data.get("access_token"),
    "refresh_token": data["refresh_token"],
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
TOKEN_FILE.chmod(0o600)
print(f"Token salvo em {TOKEN_FILE}")
print("Autorização concluída! O sistema pode fazer uploads para o Drive.")
