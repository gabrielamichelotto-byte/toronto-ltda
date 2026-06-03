-- ============================================================
-- queries.sql — Toronto LTDA  |  Business Intelligence
-- Banco: toronto_ltda.db (SQLite)
-- Gerado após ETL (etl_pipeline.py)
-- ============================================================

-- ── 1. Faturamento total e ticket médio por mês ───────────────────────────
-- Mostra sazonalidade: picos em nov/dez (festas de fim de ano)
SELECT
    strftime('%Y-%m', data_pedido)          AS ano_mes,
    COUNT(DISTINCT id_pedido)               AS pedidos,
    SUM(valor_liquido)                      AS faturamento,
    ROUND(AVG(valor_liquido), 2)            AS ticket_medio_item,
    ROUND(SUM(valor_liquido) /
          COUNT(DISTINCT id_pedido), 2)     AS ticket_medio_pedido
FROM fato_pedidos
WHERE status_pedido = 'Faturado'
GROUP BY ano_mes
ORDER BY ano_mes;


-- ── 2. Top 10 produtos por receita líquida ───────────────────────────────
SELECT
    p.nome                              AS produto,
    p.categoria,
    p.pais_origem,
    SUM(fp.valor_liquido)               AS receita_liquida,
    SUM(fp.quantidade)                  AS unidades_vendidas,
    ROUND(AVG(fp.desconto_pct), 1)      AS desconto_medio_pct
FROM fato_pedidos fp
JOIN dim_produtos p ON fp.id_produto = p.id_produto
WHERE fp.status_pedido = 'Faturado'
GROUP BY p.id_produto, p.nome, p.categoria, p.pais_origem
ORDER BY receita_liquida DESC
LIMIT 10;


-- ── 3. Performance de vendedores vs. meta ────────────────────────────────
-- Compara média mensal real com a meta mensal definida
SELECT
    v.nome                                          AS vendedor,
    v.equipe,
    v.regiao,
    v.meta_mensal,
    ROUND(SUM(fp.valor_liquido) / 24.0, 2)          AS media_mensal_real,
    ROUND(100.0 * (SUM(fp.valor_liquido) / 24.0)
          / v.meta_mensal, 1)                       AS pct_atingimento,
    SUM(fp.valor_liquido)                           AS total_24_meses,
    COUNT(DISTINCT fp.id_pedido)                    AS total_pedidos
FROM fato_pedidos fp
JOIN dim_vendedores v ON fp.id_vendedor = v.id_vendedor
WHERE fp.status_pedido = 'Faturado'
GROUP BY v.id_vendedor, v.nome, v.equipe, v.regiao, v.meta_mensal
ORDER BY pct_atingimento DESC;


-- ── 4. Inadimplência: taxa e valor em aberto por segmento ────────────────
SELECT
    c.segmento,
    COUNT(*)                                            AS total_titulos,
    SUM(CASE WHEN ff.status_titulo = 'Vencido'
             THEN 1 ELSE 0 END)                         AS inadimplentes,
    ROUND(100.0 * SUM(CASE WHEN ff.status_titulo = 'Vencido'
                           THEN 1 ELSE 0 END)
          / COUNT(*), 1)                                AS taxa_inadimplencia_pct,
    ROUND(SUM(CASE WHEN ff.status_titulo = 'Vencido'
                   THEN ff.valor ELSE 0 END), 2)        AS valor_em_aberto
FROM fato_financeiro ff
JOIN dim_clientes c ON ff.id_cliente = c.id_cliente
GROUP BY c.segmento
ORDER BY taxa_inadimplencia_pct DESC;


-- ── 5. Clientes mais valiosos (lifetime value) ───────────────────────────
SELECT
    c.nome_fantasia                         AS cliente,
    c.segmento,
    c.cidade,
    c.uf,
    COUNT(DISTINCT fp.id_pedido)            AS total_pedidos,
    SUM(fp.valor_liquido)                   AS lifetime_value,
    ROUND(AVG(fp.valor_liquido), 2)         AS ticket_medio,
    MAX(fp.data_pedido)                     AS ultimo_pedido
FROM fato_pedidos fp
JOIN dim_clientes c ON fp.id_cliente = c.id_cliente
WHERE fp.status_pedido = 'Faturado'
GROUP BY c.id_cliente, c.nome_fantasia, c.segmento, c.cidade, c.uf
ORDER BY lifetime_value DESC
LIMIT 20;


-- ── 6. Faturamento por categoria e país de origem ────────────────────────
SELECT
    p.categoria,
    p.pais_origem,
    SUM(fp.valor_liquido)               AS receita,
    ROUND(100.0 * SUM(fp.valor_liquido)
          / SUM(SUM(fp.valor_liquido)) OVER (), 1) AS share_pct,
    COUNT(DISTINCT fp.id_pedido)        AS pedidos
FROM fato_pedidos fp
JOIN dim_produtos p ON fp.id_produto = p.id_produto
WHERE fp.status_pedido = 'Faturado'
GROUP BY p.categoria, p.pais_origem
ORDER BY receita DESC;


-- ── 7. Margem bruta por produto (preço tabela vs. custo) ─────────────────
SELECT
    p.nome,
    p.categoria,
    p.fornecedor,
    p.custo_unit,
    p.preco_tabela,
    ROUND(p.preco_tabela - p.custo_unit, 2)             AS margem_unit,
    ROUND(100.0 * (p.preco_tabela - p.custo_unit)
          / p.preco_tabela, 1)                          AS margem_pct,
    COALESCE(SUM(fp.quantidade), 0)                     AS unid_vendidas,
    COALESCE(ROUND(SUM(fp.valor_liquido), 2), 0)        AS receita_liquida,
    COALESCE(ROUND(SUM(fp.quantidade) *
             (p.preco_tabela - p.custo_unit), 2), 0)    AS lucro_bruto_estimado
FROM dim_produtos p
LEFT JOIN fato_pedidos fp
    ON p.id_produto = fp.id_produto AND fp.status_pedido = 'Faturado'
GROUP BY p.id_produto, p.nome, p.categoria, p.fornecedor,
         p.custo_unit, p.preco_tabela
ORDER BY lucro_bruto_estimado DESC
LIMIT 20;


-- ── 8. Conversão no funil de vendas ──────────────────────────────────────
WITH funil_ord AS (
    SELECT etapa,
           COUNT(*) AS qtd,
           ROUND(SUM(valor_estimado), 2) AS valor_total,
           ROW_NUMBER() OVER (ORDER BY
               CASE etapa
                   WHEN 'Lead'        THEN 1
                   WHEN 'Qualificado' THEN 2
                   WHEN 'Proposta'    THEN 3
                   WHEN 'Negociação'  THEN 4
                   WHEN 'Ganho'       THEN 5
                   WHEN 'Perdido'     THEN 6
               END) AS ord
    FROM fato_funil
    GROUP BY etapa
)
SELECT
    etapa,
    qtd,
    valor_total,
    ROUND(100.0 * qtd / SUM(qtd) OVER (), 1)    AS share_pct,
    ROUND(100.0 * qtd /
          FIRST_VALUE(qtd) OVER (ORDER BY ord), 1) AS conv_sobre_topo_pct
FROM funil_ord
ORDER BY ord;


-- ── 9. Taxa de positivação por vendedor ──────────────────────────────────
-- Positivação = visita/ligação que resultou em pedido
SELECT
    v.nome                                          AS vendedor,
    COUNT(*)                                        AS total_atividades,
    SUM(CASE WHEN a.resultado = 'Pedido' THEN 1 ELSE 0 END) AS com_pedido,
    ROUND(100.0 * SUM(CASE WHEN a.resultado = 'Pedido'
                           THEN 1 ELSE 0 END) / COUNT(*), 1) AS taxa_positivacao_pct
FROM fato_atividades a
JOIN dim_vendedores v ON a.id_vendedor = v.id_vendedor
GROUP BY v.id_vendedor, v.nome
ORDER BY taxa_positivacao_pct DESC;


-- ── 10. Saldo de estoque atual por produto ────────────────────────────────
-- Último saldo acumulado = posição atual do estoque
SELECT
    p.sku,
    p.nome                              AS produto,
    p.categoria,
    p.fornecedor,
    fe.saldo_acumulado                  AS saldo_atual,
    CASE WHEN fe.saldo_acumulado < 0
         THEN 'NEGATIVO — verificar'
         WHEN fe.saldo_acumulado < 24
         THEN 'Baixo'
         ELSE 'OK'
    END                                 AS alerta_estoque
FROM (
    SELECT id_produto,
           saldo_acumulado,
           ROW_NUMBER() OVER (
               PARTITION BY id_produto ORDER BY data_mov DESC
           ) AS rn
    FROM fato_estoque
) fe
JOIN dim_produtos p ON fe.id_produto = p.id_produto
WHERE fe.rn = 1
ORDER BY fe.saldo_acumulado ASC;


-- ── 11. Aging de inadimplência (faixas de atraso) ────────────────────────
SELECT
    CASE
        WHEN dias_atraso BETWEEN 1  AND 30  THEN '01–30 dias'
        WHEN dias_atraso BETWEEN 31 AND 60  THEN '31–60 dias'
        WHEN dias_atraso BETWEEN 61 AND 90  THEN '61–90 dias'
        WHEN dias_atraso > 90               THEN '> 90 dias'
    END                         AS faixa_atraso,
    COUNT(*)                    AS titulos,
    ROUND(SUM(valor), 2)        AS valor_total,
    ROUND(AVG(dias_atraso), 0)  AS atraso_medio_dias
FROM fato_financeiro
WHERE status_titulo = 'Vencido'
GROUP BY faixa_atraso
ORDER BY MIN(dias_atraso);


-- ── 12. Novos clientes vs. recorrentes por mês ───────────────────────────
-- Distingue receita de novos clientes da base recorrente
WITH primeira_compra AS (
    SELECT id_cliente, MIN(data_pedido) AS primeiro_pedido
    FROM fato_pedidos
    WHERE status_pedido = 'Faturado'
    GROUP BY id_cliente
)
SELECT
    strftime('%Y-%m', fp.data_pedido)   AS ano_mes,
    COUNT(DISTINCT CASE
        WHEN fp.data_pedido = pc.primeiro_pedido THEN fp.id_cliente
    END)                                AS novos_clientes,
    COUNT(DISTINCT CASE
        WHEN fp.data_pedido > pc.primeiro_pedido THEN fp.id_cliente
    END)                                AS clientes_recorrentes,
    ROUND(SUM(CASE
        WHEN fp.data_pedido = pc.primeiro_pedido THEN fp.valor_liquido
    END), 2)                            AS receita_novos,
    ROUND(SUM(CASE
        WHEN fp.data_pedido > pc.primeiro_pedido THEN fp.valor_liquido
    END), 2)                            AS receita_recorrentes
FROM fato_pedidos fp
JOIN primeira_compra pc ON fp.id_cliente = pc.id_cliente
WHERE fp.status_pedido = 'Faturado'
GROUP BY ano_mes
ORDER BY ano_mes;
