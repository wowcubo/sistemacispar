"""
Migração segura: adiciona colunas novas sem perder dados existentes.
Executar na VPS:
    cd /opt/cispar && venv/bin/python deploy/migrar_banco.py
"""
import sys
sys.path.insert(0, ".")

from app.database import engine
from sqlalchemy import text

migrações = [
    # Torna descricao opcional na tabela pendencias
    "ALTER TABLE pendencias ALTER COLUMN descricao DROP NOT NULL",

    # Adiciona responsavel_id em pendencias (FK para usuarios)
    """
    DO $$ BEGIN
        ALTER TABLE pendencias ADD COLUMN responsavel_id INTEGER REFERENCES usuarios(id);
    EXCEPTION WHEN duplicate_column THEN NULL;
    END $$
    """,

    # Adiciona responsavel_padrao_id em usuarios (auto-referência)
    """
    DO $$ BEGIN
        ALTER TABLE usuarios ADD COLUMN responsavel_padrao_id INTEGER REFERENCES usuarios(id);
    EXCEPTION WHEN duplicate_column THEN NULL;
    END $$
    """,
]

with engine.begin() as conn:
    for sql in migrações:
        try:
            conn.execute(text(sql.strip()))
            print(f"OK: {sql.strip()[:60]}...")
        except Exception as e:
            print(f"AVISO: {e}")

print("\nMigração concluída.")
