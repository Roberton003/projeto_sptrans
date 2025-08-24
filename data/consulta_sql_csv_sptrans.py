"""
Script para Consultas SQL no CSV do SPTrans usando DuckDB
-------------------------------------------------------

Este script permite executar consultas SQL diretamente sobre o arquivo CSV gerado a partir da API SPTrans, sem necessidade de importar para banco de dados. Ideal para análises rápidas e flexíveis!

Como usar:
1. Ative o ambiente virtual do projeto.
2. Instale o DuckDB (se necessário):
   pip install duckdb
3. Execute este script:
   python consulta_sql_csv_sptrans.py

Edite a variável CONSULTA_SQL para personalizar sua consulta.
"""

import duckdb

ARQUIVO_CSV = '../posicoes_onibus.csv'  # ajuste o caminho se necessário

# Exemplo de consulta: selecionar todos os ônibus acessíveis
CONSULTA_SQL = """
SELECT * FROM read_csv_auto('{}') WHERE a = true
""".format(ARQUIVO_CSV)

# Executa a consulta
resultado = duckdb.query(CONSULTA_SQL).to_df()

print("Resultado da consulta:")
print(resultado.head())
print(f"Total de registros encontrados: {len(resultado)}")

# Salva o resultado em um novo CSV (opcional)
resultado.to_csv('resultado_consulta.csv', index=False)
print("Resultado salvo em resultado_consulta.csv")
