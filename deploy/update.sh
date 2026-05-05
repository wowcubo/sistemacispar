#!/bin/bash
# Atualiza a aplicação no VPS sem downtime significativo
# Execute como root: bash deploy/update.sh

set -e
cd /opt/cispar

echo "Puxando atualizações..."
sudo -u cispar git pull origin main

echo "Atualizando dependências..."
sudo -u cispar /opt/cispar/venv/bin/pip install -r requirements.txt -q

echo "Rodando migrations..."
sudo -u cispar /opt/cispar/venv/bin/alembic upgrade head

echo "Reiniciando serviço..."
systemctl restart cispar

echo "Recarregando nginx..."
nginx -t && systemctl reload nginx

echo "=== Atualização concluída! ==="
systemctl status cispar --no-pager
