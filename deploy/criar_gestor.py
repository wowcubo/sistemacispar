"""
Cria o primeiro usuário gestor no banco de dados.
Execute no servidor: python deploy/criar_gestor.py

Uso:
  python deploy/criar_gestor.py --nome "Ricardo" --email "admin@empresa.com" --senha "senha123"
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, Base
from app.models import *  # noqa
from app.models.usuario import Usuario, Papel, Setor
from app.services.auth import hash_senha

Base.metadata.create_all(bind=engine)

parser = argparse.ArgumentParser()
parser.add_argument("--nome", required=True)
parser.add_argument("--email", required=True)
parser.add_argument("--senha", required=True)
args = parser.parse_args()

db = SessionLocal()
try:
    existe = db.query(Usuario).filter(Usuario.email == args.email).first()
    if existe:
        print(f"Usuário {args.email} já existe.")
        sys.exit(0)

    usuario = Usuario(
        nome=args.nome,
        email=args.email,
        senha_hash=hash_senha(args.senha),
        papel=Papel.gestor,
        setor=Setor.geral,
        ativo=True,
    )
    db.add(usuario)
    db.commit()
    print(f"Gestor criado com sucesso: {args.nome} ({args.email})")
finally:
    db.close()
