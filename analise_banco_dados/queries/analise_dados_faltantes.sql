-- Queries usadas na análise de dados faltantes no banco sptrans_data.db
-- Autor: Cline
-- Data: 29/09/2025
-- Nota: Para .tables e .schema, execute diretamente no sqlite3 CLI. As queries abaixo são SELECTs para replicação.

-- 1. Listar tabelas (CLI): sqlite3 data/sptrans_data.db ".tables"

-- 2. Obter schema (CLI): sqlite3 data/sptrans_data.db ".schema"

-- 3. Contagem de registros por tabela
SELECT 'posicoes' as table_name, COUNT(*) as row_count FROM posicoes
UNION ALL
SELECT 'previsoes', COUNT(*) FROM previsoes
UNION ALL
SELECT 'resultados_analise', COUNT(*) FROM resultados_analise;

-- 4. Contagem de NULLs em campos nulos (todas as tabelas)
-- posicoes
SELECT 'posicoes_total' as metric, COUNT(*) as value FROM posicoes
UNION ALL
SELECT 'posicoes_letreiro_linha_null', COUNT(*) FROM posicoes WHERE letreiro_linha IS NULL
UNION ALL
SELECT 'posicoes_timestamp_posicao_null', COUNT(*) FROM posicoes WHERE timestamp_posicao IS NULL
-- previsoes
UNION ALL
SELECT 'previsoes_total', COUNT(*) FROM previsoes
UNION ALL
SELECT 'previsoes_id_parada_null', COUNT(*) FROM previsoes WHERE id_parada IS NULL
UNION ALL
SELECT 'previsoes_horario_previsao_null', COUNT(*) FROM previsoes WHERE horario_previsao IS NULL
-- resultados_analise
UNION ALL
SELECT 'resultados_analise_total', COUNT(*) FROM resultados_analise
UNION ALL
SELECT 'resultados_analise_letreiro_linha_null', COUNT(*) FROM resultados_analise WHERE letreiro_linha IS NULL
UNION ALL
SELECT 'resultados_analise_posicao_atual_lat_null', COUNT(*) FROM resultados_analise WHERE posicao_atual_lat IS NULL
UNION ALL
SELECT 'resultados_analise_posicao_atual_lon_null', COUNT(*) FROM resultados_analise WHERE posicao_atual_lon IS NULL
UNION ALL
SELECT 'resultados_analise_horario_posicao_null', COUNT(*) FROM resultados_analise WHERE horario_posicao IS NULL
UNION ALL
SELECT 'resultados_analise_proximo_ponto_previsto_null', COUNT(*) FROM resultados_analise WHERE proximo_ponto_previsto IS NULL
UNION ALL
SELECT 'resultados_analise_horario_previsto_chegada_null', COUNT(*) FROM resultados_analise WHERE horario_previsto_chegada IS NULL;

-- 5. Amostra de registros com previsões preenchidas (resultados_analise)
SELECT timestamp_analise, id_onibus, letreiro_linha, proximo_ponto_previsto, horario_previsto_chegada
FROM resultados_analise WHERE proximo_ponto_previsto IS NOT NULL
LIMIT 10;

-- 6. Padrões de previsões por linha de ônibus (top 20 por volume)
SELECT letreiro_linha, COUNT(*) as total,
       SUM(CASE WHEN proximo_ponto_previsto IS NOT NULL THEN 1 ELSE 0 END) as com_previsao
FROM resultados_analise
GROUP BY letreiro_linha
ORDER BY total DESC
LIMIT 20;
