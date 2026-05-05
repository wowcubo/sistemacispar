#!/bin/bash
# Script de setup do VPS para o sistema CISPAR
# Execute como root: bash setup_vps.sh
# Testado em Ubuntu 22.04 LTS

set -e

echo "=== CISPAR VPS Setup ==="

# ── 1. Dependências do sistema ─────────────────────────────────────────────────
apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip \
    postgresql postgresql-contrib nginx certbot python3-certbot-nginx \
    git curl

# ── 2. PostgreSQL ──────────────────────────────────────────────────────────────
echo "Configurando PostgreSQL..."
sudo -u postgres psql -c "CREATE USER cispar WITH PASSWORD 'TROQUE_SENHA_PRODUCAO';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE cispar OWNER cispar;" 2>/dev/null || true

# ── 3. Usuário e diretório da aplicação ───────────────────────────────────────
echo "Criando usuário cispar..."
id cispar &>/dev/null || useradd --system --shell /bin/bash --home /opt/cispar --create-home cispar

# ── 4. Clonar o repositório ───────────────────────────────────────────────────
echo "Clonando repositório..."
cd /opt
if [ -d "/opt/cispar/.git" ]; then
    cd cispar && git pull
else
    git clone https://github.com/wowcubo/sistemacispar.git /opt/cispar
fi
chown -R cispar:cispar /opt/cispar

# ── 5. Ambiente virtual Python ────────────────────────────────────────────────
echo "Criando ambiente virtual..."
sudo -u cispar python3.11 -m venv /opt/cispar/venv
sudo -u cispar /opt/cispar/venv/bin/pip install --upgrade pip -q
sudo -u cispar /opt/cispar/venv/bin/pip install -r /opt/cispar/requirements.txt -q

# ── 6. Arquivo .env de produção ───────────────────────────────────────────────
if [ ! -f /opt/cispar/.env ]; then
    echo "Criando .env de produção..."
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > /opt/cispar/.env <<EOF
DATABASE_URL=postgresql://cispar:TROQUE_SENHA_PRODUCAO@localhost:5432/cispar
SECRET_KEY=${SECRET}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
GOOGLE_SERVICE_ACCOUNT_FILE=/opt/cispar/credentials/service_account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=PREENCHA_AQUI
APP_NAME=CISPAR - Sistema de Rotinas SISBI
APP_URL=https://cispar.torresminhocaseiro.com.br
DEBUG=false
EOF
    chown cispar:cispar /opt/cispar/.env
    chmod 600 /opt/cispar/.env
    echo "ATENÇÃO: edite /opt/cispar/.env e preencha GOOGLE_DRIVE_ROOT_FOLDER_ID"
fi

# Diretório de credenciais Google
mkdir -p /opt/cispar/credentials
chown -R cispar:cispar /opt/cispar/credentials
chmod 700 /opt/cispar/credentials

# ── 7. Migrations Alembic ─────────────────────────────────────────────────────
echo "Rodando migrations..."
cd /opt/cispar
sudo -u cispar /opt/cispar/venv/bin/alembic upgrade head || \
    sudo -u cispar /opt/cispar/venv/bin/python -c "
from app.database import engine, Base
from app.models import *
Base.metadata.create_all(bind=engine)
print('Tabelas criadas via SQLAlchemy')
"

# ── 8. Systemd ────────────────────────────────────────────────────────────────
echo "Configurando systemd..."
cp /opt/cispar/deploy/cispar.service /etc/systemd/system/cispar.service
systemctl daemon-reload
systemctl enable cispar
systemctl restart cispar

# ── 9. nginx ──────────────────────────────────────────────────────────────────
echo "Configurando nginx..."
cp /opt/cispar/deploy/nginx.conf /etc/nginx/sites-available/cispar
ln -sf /etc/nginx/sites-available/cispar /etc/nginx/sites-enabled/cispar
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── 10. SSL Let's Encrypt ─────────────────────────────────────────────────────
echo "Obtendo certificado SSL..."
certbot --nginx -d cispar.torresminhocaseiro.com.br --non-interactive --agree-tos \
    -m admin@torresminhocaseiro.com.br --redirect || echo "Certbot falhou - configure DNS primeiro"

echo ""
echo "=== Setup concluído! ==="
echo "Próximos passos:"
echo "  1. Copie o service_account.json do Google Drive para /opt/cispar/credentials/"
echo "  2. Edite /opt/cispar/.env e preencha GOOGLE_DRIVE_ROOT_FOLDER_ID"
echo "  3. Reinicie: systemctl restart cispar"
echo "  4. Crie o primeiro usuário gestor: ver deploy/criar_gestor.py"
echo ""
echo "Status: systemctl status cispar"
echo "Logs:   journalctl -u cispar -f"
