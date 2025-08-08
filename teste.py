import os

# ✅ Defina a variável de ambiente ANTES de importar controlerotas
os.environ['DATABASE_URL'] = "postgresql://u2rr324om9dgp9:pb11deab3e8d1590ea00eb2f784aca63a2ed6c1e861d22d08a7605caa10a5d58b@cer3tutrbi7n1t.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dg59kb9ng2lpi"

import csv
from controlerotas import app, database
from controlerotas.models import Bairros

# 📍 Caminho do CSV
CAMINHO_CSV = 'bairro.csv'

with app.app_context():
    # (Opcional) Limpa a tabela antes de importar
    database.session.query(Bairros).delete()
    database.session.commit()

    with open(CAMINHO_CSV, mode='r', encoding='latin1') as arquivo:
        leitor = csv.reader(arquivo, delimiter=';')
        next(leitor)  # pula o cabeçalho

        for linha in leitor:
            nome, valor = linha
            nome = nome.strip()
            valor = valor.strip().replace('R$', '').replace(',', '.')

            try:
                valor_float = float(valor)
                bairro = Bairros(nome=nome, valor=valor_float)
                database.session.add(bairro)
            except ValueError:
                print(f"❌ Erro ao converter o valor do bairro '{nome}': '{valor}'")

        database.session.commit()
        print("✅ Bairros importados com sucesso!")
