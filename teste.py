from sqlalchemy import create_engine
import pandas as pd

# Dados de conexão
DATABASE_URL = 'postgresql://neondb_owner:npg_QjBrhdaqP3i4@ep-long-dust-acp3v069-pooler.sa-east-1.aws.neon.tech:5432/neondb?sslmode=require'

# Lendo o CSV
df = pd.read_csv('bairros.csv', sep=';')

# Verificando as colunas
print('Colunas do CSV:', df.columns.tolist())

# Convertendo coluna 'valor' para float (remover R$ e trocar vírgula por ponto, se necessário)
df['valor'] = df['valor'].astype(str).str.replace('R$', '', regex=False).str.replace(',', '.', regex=False).astype(float)

# Conectando ao banco
engine = create_engine(DATABASE_URL)

# Inserindo na tabela 'bairros'
df.to_sql('bairros', engine, if_exists='append', index=False)

print('Dados inseridos com sucesso!')
