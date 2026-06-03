# -*- coding: utf-8 -*-
"""
gerar_dashboard.py — Toronto LTDA  (v1 corrigido — visao geral, Chart.js inline)
"""
import json, sqlite3
import pandas as pd

DB  = "toronto_ltda.db"
OUT = "dashboard.html"


def main():
    conn = sqlite3.connect(DB)

    # ── agregacoes ────────────────────────────────────────────────────────────────

    df_mens = pd.read_sql("""
        SELECT strftime('%Y-%m', data_pedido) AS mes,
               ROUND(SUM(valor_liquido),2)    AS fat,
               COUNT(DISTINCT id_pedido)      AS pedidos
        FROM fato_pedidos WHERE status_pedido='Faturado'
        GROUP BY mes ORDER BY mes
    """, conn)

    df_cat = pd.read_sql("""
        SELECT p.categoria, ROUND(SUM(fp.valor_liquido),2) AS receita
        FROM fato_pedidos fp JOIN dim_produtos p ON fp.id_produto=p.id_produto
        WHERE fp.status_pedido='Faturado'
        GROUP BY p.categoria ORDER BY receita DESC
    """, conn)

    df_reg = pd.read_sql("""
        SELECT c.regiao, ROUND(SUM(fp.valor_liquido),2) AS receita
        FROM fato_pedidos fp JOIN dim_clientes c ON fp.id_cliente=c.id_cliente
        WHERE fp.status_pedido='Faturado'
        GROUP BY c.regiao ORDER BY receita DESC
    """, conn)

    df_top10 = pd.read_sql("""
        SELECT p.nome, ROUND(SUM(fp.valor_liquido),2) AS receita
        FROM fato_pedidos fp JOIN dim_produtos p ON fp.id_produto=p.id_produto
        WHERE fp.status_pedido='Faturado'
        GROUP BY p.id_produto, p.nome ORDER BY receita DESC LIMIT 10
    """, conn)

    df_vend = pd.read_sql("""
        SELECT v.nome, v.meta_mensal,
               ROUND(SUM(fp.valor_liquido)/24.0,2) AS media
        FROM fato_pedidos fp JOIN dim_vendedores v ON fp.id_vendedor=v.id_vendedor
        WHERE fp.status_pedido='Faturado'
        GROUP BY v.id_vendedor, v.nome, v.meta_mensal ORDER BY media DESC
    """, conn)

    df_funil = pd.read_sql("""
        SELECT etapa, COUNT(*) AS qtd, ROUND(SUM(valor_estimado),2) AS valor
        FROM fato_funil GROUP BY etapa
    """, conn)
    ordem = {"Lead":1,"Qualificado":2,"Proposta":3,"Negociação":4,"Ganho":5,"Perdido":6}
    df_funil["ord"] = df_funil["etapa"].map(ordem).fillna(7)
    df_funil = df_funil.sort_values("ord")

    df_inad = pd.read_sql("""
        SELECT c.segmento,
               ROUND(100.0*SUM(CASE WHEN ff.status_titulo='Vencido' THEN 1 ELSE 0 END)/COUNT(*),1) AS taxa
        FROM fato_financeiro ff JOIN dim_clientes c ON ff.id_cliente=c.id_cliente
        GROUP BY c.segmento ORDER BY taxa DESC
    """, conn)

    df_seg = pd.read_sql("""
        SELECT segmento, COUNT(*) AS qtd FROM dim_clientes
        WHERE status='Ativo' GROUP BY segmento ORDER BY qtd DESC
    """, conn)

    # ticket_detalhe: ticket médio por mês × status (agregado ao nível de pedido)
    df_all_ped = pd.read_sql(
        "SELECT substr(data_pedido,1,7) AS mes, status_pedido AS status, id_pedido, valor_liquido FROM fato_pedidos",
        conn
    )
    df_ped_tot = (df_all_ped
                  .groupby(["mes", "status", "id_pedido"])["valor_liquido"].sum()
                  .reset_index().rename(columns={"valor_liquido": "valor"}))
    df_td = (df_ped_tot
             .groupby(["mes", "status"])
             .agg(n_pedidos=("id_pedido", "count"), ticket=("valor", "mean"), total=("valor", "sum"))
             .reset_index())
    df_td["ticket"] = df_td["ticket"].round(0).astype(int)
    df_td["total"]  = df_td["total"].round(2)
    ticket_detalhe  = df_td.to_dict("records")

    # inad_detalhe: evolução mensal + por segmento com contagens
    df_inad_ff = pd.read_sql(
        "SELECT substr(data_emissao,1,7) AS mes, status_titulo FROM fato_financeiro", conn
    )
    df_im = (df_inad_ff
             .groupby("mes")
             .agg(total=("status_titulo","count"),
                  vencidos=("status_titulo", lambda s: (s=="Vencido").sum()))
             .reset_index())
    df_im["taxa"] = (df_im["vencidos"] / df_im["total"] * 100).round(1)
    df_im = df_im.sort_values("mes")

    df_inad_seg = pd.read_sql("""
        SELECT c.segmento,
               COUNT(*) AS total,
               SUM(CASE WHEN ff.status_titulo='Vencido' THEN 1 ELSE 0 END) AS vencidos,
               ROUND(100.0*SUM(CASE WHEN ff.status_titulo='Vencido' THEN 1 ELSE 0 END)/COUNT(*),1) AS taxa
        FROM fato_financeiro ff JOIN dim_clientes c ON ff.id_cliente=c.id_cliente
        GROUP BY c.segmento ORDER BY taxa DESC
    """, conn)

    inad_detalhe = {
        "mensal":    df_im[["mes","total","vencidos","taxa"]].to_dict("records"),
        "segmentos": df_inad_seg.to_dict("records"),
    }

    # fat_detalhe: faturamento por mês × categoria e por mês × região
    df_fat_cat = pd.read_sql("""
        SELECT substr(fp.data_pedido,1,7) AS mes, p.categoria,
               ROUND(SUM(fp.valor_liquido),2) AS fat
        FROM fato_pedidos fp JOIN dim_produtos p ON fp.id_produto=p.id_produto
        WHERE fp.status_pedido='Faturado'
        GROUP BY mes, p.categoria ORDER BY mes, fat DESC
    """, conn)
    df_fat_reg = pd.read_sql("""
        SELECT substr(fp.data_pedido,1,7) AS mes, c.regiao,
               ROUND(SUM(fp.valor_liquido),2) AS fat
        FROM fato_pedidos fp JOIN dim_clientes c ON fp.id_cliente=c.id_cliente
        WHERE fp.status_pedido='Faturado'
        GROUP BY mes, c.regiao ORDER BY mes, fat DESC
    """, conn)
    fat_detalhe = {
        "categorias": df_fat_cat.to_dict("records"),
        "regioes":    df_fat_reg.to_dict("records"),
    }

    # margem_detalhe: composição receita × custo × margem por categoria e por vendedor
    df_mg_cat = pd.read_sql("""
        SELECT p.categoria,
               ROUND(SUM(fp.valor_liquido),2)             AS receita,
               ROUND(SUM(p.custo_unit * fp.quantidade),2)  AS custo,
               ROUND(SUM(fp.valor_liquido) - SUM(p.custo_unit * fp.quantidade),2) AS margem_rs
        FROM fato_pedidos fp JOIN dim_produtos p ON fp.id_produto=p.id_produto
        WHERE fp.status_pedido='Faturado'
        GROUP BY p.categoria ORDER BY receita DESC
    """, conn)
    df_mg_cat["margem_pct"] = (df_mg_cat["margem_rs"] / df_mg_cat["receita"] * 100).round(1)

    df_mg_vend = pd.read_sql("""
        SELECT v.nome,
               ROUND(SUM(fp.valor_liquido),2)             AS receita,
               ROUND(SUM(p.custo_unit * fp.quantidade),2)  AS custo,
               ROUND(SUM(fp.valor_liquido) - SUM(p.custo_unit * fp.quantidade),2) AS margem_rs
        FROM fato_pedidos fp
        JOIN dim_produtos p   ON fp.id_produto=p.id_produto
        JOIN dim_vendedores v ON fp.id_vendedor=v.id_vendedor
        WHERE fp.status_pedido='Faturado'
        GROUP BY v.nome ORDER BY receita DESC
    """, conn)
    df_mg_vend["margem_pct"] = (df_mg_vend["margem_rs"] / df_mg_vend["receita"] * 100).round(1)

    margem_detalhe = {
        "categorias": df_mg_cat.to_dict("records"),
        "vendedores": df_mg_vend.to_dict("records"),
    }

    # cli_detalhe: ativos/inativos por segmento e região, evolução mensal, top inativos
    df_cli_seg = pd.read_sql("""
        SELECT segmento,
               SUM(CASE WHEN status='Ativo'   THEN 1 ELSE 0 END) AS ativos,
               SUM(CASE WHEN status='Inativo' THEN 1 ELSE 0 END) AS inativos,
               COUNT(*) AS total
        FROM dim_clientes GROUP BY segmento ORDER BY total DESC
    """, conn)
    df_cli_seg["pct_ativo"] = (df_cli_seg["ativos"] / df_cli_seg["total"] * 100).round(1)

    df_cli_reg = pd.read_sql("""
        SELECT regiao,
               SUM(CASE WHEN status='Ativo'   THEN 1 ELSE 0 END) AS ativos,
               SUM(CASE WHEN status='Inativo' THEN 1 ELSE 0 END) AS inativos,
               COUNT(*) AS total
        FROM dim_clientes GROUP BY regiao ORDER BY total DESC
    """, conn)
    df_cli_reg["pct_ativo"] = (df_cli_reg["ativos"] / df_cli_reg["total"] * 100).round(1)

    df_ativos_mes = pd.read_sql("""
        SELECT substr(data_pedido,1,7) AS mes,
               COUNT(DISTINCT id_cliente) AS ativos_mes
        FROM fato_pedidos WHERE status_pedido='Faturado'
        GROUP BY mes ORDER BY mes
    """, conn)

    df_novos_mes = pd.read_sql("""
        SELECT substr(primeira_compra,1,7) AS mes, COUNT(*) AS novos
        FROM (
            SELECT id_cliente, MIN(data_pedido) AS primeira_compra
            FROM fato_pedidos WHERE status_pedido='Faturado'
            GROUP BY id_cliente
        ) GROUP BY mes ORDER BY mes
    """, conn)

    # clientes que compraram mas estão sem pedido faturado há +6 meses (comportamental)
    df_top_inativos = pd.read_sql("""
        SELECT c.nome_fantasia, c.segmento, c.regiao,
               ROUND(SUM(fp.valor_liquido),2) AS receita_total,
               MAX(substr(fp.data_pedido,1,7)) AS ultimo_pedido
        FROM dim_clientes c
        JOIN fato_pedidos fp ON c.id_cliente=fp.id_cliente
        WHERE fp.status_pedido='Faturado'
        GROUP BY c.id_cliente, c.nome_fantasia, c.segmento, c.regiao
        HAVING MAX(fp.data_pedido) < (
            SELECT date(MAX(data_pedido), '-4 months')
            FROM fato_pedidos WHERE status_pedido='Faturado'
        )
        ORDER BY receita_total DESC LIMIT 10
    """, conn)

    _ord = df_ativos_mes.sort_values("mes")
    delta_cli = int(_ord.iloc[-1]["ativos_mes"]) - int(_ord.iloc[-2]["ativos_mes"]) if len(_ord) >= 2 else 0
    mes_ant_cli = str(_ord.iloc[-2]["mes"]) if len(_ord) >= 2 else ""

    # abc_detalhe: curva ABC de clientes inativos comportamentais
    df_abc_raw = pd.read_sql("""
        SELECT c.id_cliente, c.nome_fantasia, c.segmento, c.regiao, v.nome AS vendedor,
               ROUND(SUM(fp.valor_liquido), 2) AS receita_total,
               MAX(substr(fp.data_pedido,1,7)) AS ultimo_pedido
        FROM dim_clientes c
        JOIN fato_pedidos fp ON c.id_cliente = fp.id_cliente
        JOIN dim_vendedores v ON c.id_vendedor = v.id_vendedor
        WHERE fp.status_pedido = 'Faturado'
        GROUP BY c.id_cliente, c.nome_fantasia, c.segmento, c.regiao, v.nome
        HAVING MAX(fp.data_pedido) < (
            SELECT date(MAX(data_pedido), '-4 months')
            FROM fato_pedidos WHERE status_pedido='Faturado'
        )
        ORDER BY receita_total DESC
    """, conn)

    _total_abc = float(df_abc_raw["receita_total"].sum()) if len(df_abc_raw) > 0 else 1.0
    df_abc_raw = df_abc_raw.copy()
    df_abc_raw["cumul_rec"] = df_abc_raw["receita_total"].cumsum()
    df_abc_raw["cumul_pct"] = (df_abc_raw["cumul_rec"] / _total_abc * 100).round(1)
    df_abc_raw["indiv_pct"] = (df_abc_raw["receita_total"] / _total_abc * 100).round(2)
    df_abc_raw["classe"] = df_abc_raw["cumul_pct"].apply(
        lambda p: "A" if p <= 80 else ("B" if p <= 95 else "C")
    )
    n_abc_total = len(df_abc_raw)
    n_abc_a     = int((df_abc_raw["classe"] == "A").sum())
    rec_em_risco = round(_total_abc, 2)

    df_abc_seg  = (df_abc_raw.groupby(["segmento", "classe"])
                   .agg(n=("id_cliente","count"), receita=("receita_total","sum"))
                   .reset_index())
    df_abc_seg["receita"] = df_abc_seg["receita"].round(2)

    df_abc_reg  = (df_abc_raw.groupby(["regiao", "classe"])
                   .agg(n=("id_cliente","count"), receita=("receita_total","sum"))
                   .reset_index())
    df_abc_reg["receita"] = df_abc_reg["receita"].round(2)

    df_abc_vend = (df_abc_raw.groupby(["vendedor", "classe"])
                   .agg(n=("id_cliente","count"), receita=("receita_total","sum"))
                   .reset_index())
    df_abc_vend["receita"] = df_abc_vend["receita"].round(2)

    # giro_detalhe: recência, frequência e ticket médio por cliente
    df_giro_raw = pd.read_sql("""
        WITH base AS (
            SELECT fp.id_cliente,
                   c.nome_fantasia, c.segmento, c.regiao, v.nome AS vendedor,
                   COUNT(DISTINCT fp.id_pedido)                         AS n_pedidos,
                   ROUND(SUM(fp.valor_liquido), 2)                      AS receita_total,
                   MIN(fp.data_pedido)                                  AS primeiro_pedido,
                   MAX(fp.data_pedido)                                  AS ultimo_pedido
            FROM fato_pedidos fp
            JOIN dim_clientes c   ON fp.id_cliente  = c.id_cliente
            JOIN dim_vendedores v ON fp.id_vendedor = v.id_vendedor
            WHERE fp.status_pedido = 'Faturado'
            GROUP BY fp.id_cliente, c.nome_fantasia, c.segmento, c.regiao, v.nome
            HAVING COUNT(DISTINCT fp.id_pedido) >= 1
        )
        SELECT *,
               ROUND(receita_total / n_pedidos, 2) AS ticket_medio
        FROM base
    """, conn)

    _hoje_str = "2026-06-02"
    df_giro_raw["recencia_dias"] = (
        pd.to_datetime(_hoje_str) - pd.to_datetime(df_giro_raw["ultimo_pedido"])
    ).dt.days.clip(lower=0)   # ordens no mesmo mês podem cair em dias > hoje

    # intervalo médio entre pedidos (span / n_pedidos-1); 1 pedido → NaN
    df_giro_raw["span_dias"] = (
        pd.to_datetime(df_giro_raw["ultimo_pedido"]) -
        pd.to_datetime(df_giro_raw["primeiro_pedido"])
    ).dt.days
    df_giro_raw["intervalo_medio"] = (
        df_giro_raw["span_dias"] / (df_giro_raw["n_pedidos"] - 1)
    ).where(df_giro_raw["n_pedidos"] > 1).round(0)

    # Quadrantes: mediana de recência e frequência como ponto de corte
    _med_rec  = float(df_giro_raw["recencia_dias"].median())
    _med_freq = float(df_giro_raw["intervalo_medio"].dropna().median())

    def _quadrante(row):
        rec  = row["recencia_dias"]
        freq = row["intervalo_medio"]
        if pd.isna(freq):
            return "Novatos"           # só 1 pedido
        if rec <= _med_rec and freq <= _med_freq:
            return "Campeões"          # comprou recente + compra com frequência
        if rec <= _med_rec and freq > _med_freq:
            return "Em Desenvolvimento"  # recente mas espaçado
        if rec > _med_rec and freq <= _med_freq:
            return "Em Risco"          # frequente mas sumiu
        return "Dormentes"             # sumiu + espaçado

    df_giro_raw["quadrante"] = df_giro_raw.apply(_quadrante, axis=1)

    # histograma de recência em faixas de 30 dias
    _bins = [-1, 30, 60, 90, 120, 180, 365, 9999]   # -1 garante que 0 cai na 1ª faixa
    _labels_rec = ["0–30d","31–60d","61–90d","91–120d","121–180d","181–365d","365d+"]
    df_giro_raw["faixa_rec"] = pd.cut(
        df_giro_raw["recencia_dias"], bins=_bins, labels=_labels_rec, right=True
    )
    df_hist_rec = (df_giro_raw.groupby("faixa_rec", observed=True)
                   .size().reset_index(name="n"))

    # por segmento: médias de recência, intervalo e ticket
    df_giro_seg = (df_giro_raw.groupby("segmento")
                   .agg(
                       n_clientes      =("id_cliente","count"),
                       rec_media       =("recencia_dias","mean"),
                       intervalo_medio =("intervalo_medio","mean"),
                       ticket_medio    =("ticket_medio","mean"),
                   ).reset_index())
    df_giro_seg["rec_media"]        = df_giro_seg["rec_media"].round(0)
    df_giro_seg["intervalo_medio"]  = df_giro_seg["intervalo_medio"].round(0)
    df_giro_seg["ticket_medio"]     = df_giro_seg["ticket_medio"].round(0)

    # scatter: top 120 clientes (evitar peso excessivo no HTML)
    df_giro_scatter = (df_giro_raw[["nome_fantasia","segmento","recencia_dias",
                                     "intervalo_medio","ticket_medio","n_pedidos",
                                     "receita_total","quadrante"]]
                       .dropna(subset=["intervalo_medio"])
                       .sort_values("receita_total", ascending=False)
                       .head(120))

    _rec_med_card  = int(df_giro_raw["recencia_dias"].mean().round(0))
    _freq_med_card = int(df_giro_raw["intervalo_medio"].dropna().mean().round(0))
    _tick_med_card = round(float(df_giro_raw["ticket_medio"].mean()), 2)

    # estoque_detalhe: giro, cobertura e movimento por produto
    df_est_mov = pd.read_sql("""
        SELECT e.id_produto, p.nome, p.categoria,
               SUM(CASE WHEN e.tipo_mov='Entrada' THEN e.quantidade ELSE 0 END) AS entradas,
               SUM(CASE WHEN e.tipo_mov='Saida'   THEN e.quantidade ELSE 0 END) AS saidas,
               (SUM(CASE WHEN e.tipo_mov='Entrada' THEN e.quantidade ELSE 0 END)
              - SUM(CASE WHEN e.tipo_mov='Saida'   THEN e.quantidade ELSE 0 END)) AS saldo
        FROM fato_estoque e JOIN dim_produtos p ON e.id_produto=p.id_produto
        GROUP BY e.id_produto, p.nome, p.categoria
        ORDER BY saldo DESC
    """, conn)

    # vendas mensais por produto (saída real via pedidos faturados)
    df_vendas_prod = pd.read_sql("""
        SELECT id_produto,
               ROUND(SUM(quantidade) * 1.0 / COUNT(DISTINCT substr(data_pedido,1,7)), 1) AS saida_media_mensal
        FROM fato_pedidos WHERE status_pedido='Faturado'
        GROUP BY id_produto
    """, conn)

    df_est_full = df_est_mov.merge(df_vendas_prod, on="id_produto", how="left")
    df_est_full["saida_media_mensal"] = df_est_full["saida_media_mensal"].fillna(0)
    # cobertura em dias: saldo / (saída_media_mensal / 30); evita div/0
    df_est_full["cobertura_dias"] = (
        df_est_full["saldo"] /
        (df_est_full["saida_media_mensal"] / 30).replace(0, float("nan"))
    ).round(0).fillna(9999).clip(lower=0)

    # giro: saídas / ((entradas + saldo) / 2) — índice de rotatividade
    df_est_full["estoque_medio"] = ((df_est_full["entradas"] + df_est_full["saldo"]) / 2).clip(lower=1)
    df_est_full["giro"] = (df_est_full["saidas"] / df_est_full["estoque_medio"]).round(2)

    # semáforo
    def _sem_cob(d):
        if d < 30:   return "Crítico"
        if d < 90:   return "Atenção"
        if d < 9999: return "Ok"
        return "Parado"

    df_est_full["status"] = df_est_full["cobertura_dias"].apply(_sem_cob)

    # por categoria
    df_est_cat = (df_est_full.groupby("categoria")
                  .agg(n_produtos=("id_produto","count"),
                       saldo_total=("saldo","sum"),
                       cobertura_media=("cobertura_dias", lambda x: round(float(x[x<9999].mean()),0) if (x<9999).any() else 9999),
                       giro_medio=("giro","mean"))
                  .reset_index())
    df_est_cat["giro_medio"] = df_est_cat["giro_medio"].round(2)

    # movimento mensal agregado (entradas vs saídas pelo fato_estoque)
    df_est_mes = pd.read_sql("""
        SELECT substr(data_mov,1,7) AS mes,
               SUM(CASE WHEN tipo_mov='Entrada' THEN quantidade ELSE 0 END) AS entradas,
               SUM(CASE WHEN tipo_mov='Saida'   THEN quantidade ELSE 0 END) AS saidas
        FROM fato_estoque
        GROUP BY mes ORDER BY mes
    """, conn)

    _n_critico = int((df_est_full["status"] == "Crítico").sum())
    _n_parado  = int((df_est_full["status"] == "Parado").sum())
    _cob_media = round(float(df_est_full.loc[df_est_full["cobertura_dias"] < 9999, "cobertura_dias"].mean()), 0)

    # conv_detalhe: inadimplência × impacto na conversão de pedidos
    df_conv_perfil = pd.read_sql("""
        WITH inadimpl AS (
            SELECT id_cliente, MIN(data_vencimento) AS primeiro_vencido
            FROM fato_financeiro WHERE status_titulo='Vencido'
            GROUP BY id_cliente
        ),
        recompra AS (
            SELECT fp.id_cliente
            FROM fato_pedidos fp
            JOIN inadimpl i ON fp.id_cliente=i.id_cliente
            WHERE fp.status_pedido='Faturado' AND fp.data_pedido > i.primeiro_vencido
            GROUP BY fp.id_cliente
        )
        SELECT
            CASE WHEN r.id_cliente IS NULL THEN 'Parou' ELSE 'Continuou' END AS perfil,
            COUNT(*) AS n
        FROM inadimpl i LEFT JOIN recompra r ON i.id_cliente=r.id_cliente
        GROUP BY perfil
    """, conn)

    df_conv_seg = pd.read_sql("""
        WITH inadimpl AS (
            SELECT id_cliente, MIN(data_vencimento) AS primeiro_vencido
            FROM fato_financeiro WHERE status_titulo='Vencido'
            GROUP BY id_cliente
        ),
        recompra AS (
            SELECT fp.id_cliente
            FROM fato_pedidos fp
            JOIN inadimpl i ON fp.id_cliente=i.id_cliente
            WHERE fp.status_pedido='Faturado' AND fp.data_pedido > i.primeiro_vencido
            GROUP BY fp.id_cliente
        )
        SELECT c.segmento,
               CASE WHEN r.id_cliente IS NULL THEN 'Parou' ELSE 'Continuou' END AS perfil,
               COUNT(*) AS n
        FROM inadimpl i
        JOIN dim_clientes c ON i.id_cliente=c.id_cliente
        LEFT JOIN recompra r ON i.id_cliente=r.id_cliente
        GROUP BY c.segmento, perfil
        ORDER BY c.segmento, perfil
    """, conn)

    df_conv_inad_mes = pd.read_sql("""
        SELECT substr(data_vencimento,1,7) AS mes,
               ROUND(100.0*SUM(CASE WHEN status_titulo='Vencido' THEN 1 ELSE 0 END)/COUNT(*),1) AS taxa_inad
        FROM fato_financeiro
        WHERE data_vencimento IS NOT NULL
        GROUP BY mes ORDER BY mes
    """, conn)

    df_conv_ped_mes = pd.read_sql("""
        SELECT substr(data_pedido,1,7) AS mes,
               COUNT(DISTINCT id_cliente) AS compradores
        FROM fato_pedidos WHERE status_pedido='Faturado'
        GROUP BY mes ORDER BY mes
    """, conn)

    df_conv_evo = df_conv_inad_mes.merge(df_conv_ped_mes, on="mes", how="inner").sort_values("mes")

    _n_inad   = int(df_conv_perfil["n"].sum()) if len(df_conv_perfil) > 0 else 0
    _n_parou  = int(df_conv_perfil.loc[df_conv_perfil["perfil"]=="Parou","n"].sum()) if len(df_conv_perfil) > 0 else 0
    _pct_parou = round(_n_parou / _n_inad * 100, 1) if _n_inad > 0 else 0.0

    # desc_detalhe: desconto por vendedor, segmento e evolução mensal
    df_desc_vend = pd.read_sql("""
        WITH ped_tot AS (
            SELECT id_pedido, id_vendedor,
                   AVG(desconto_pct)  AS desc_ped,
                   SUM(valor_liquido) AS ticket
            FROM fato_pedidos WHERE status_pedido='Faturado'
            GROUP BY id_pedido, id_vendedor
        )
        SELECT v.nome,
               COUNT(*)  AS n_pedidos,
               ROUND(AVG(desc_ped),1)  AS desc_medio,
               ROUND(100.0*SUM(CASE WHEN desc_ped>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS freq_desc,
               ROUND(AVG(ticket),0)    AS ticket_medio,
               ROUND(AVG(CASE WHEN desc_ped=0 THEN ticket END),0)  AS ticket_sem_desc,
               ROUND(AVG(CASE WHEN desc_ped>0 THEN ticket END),0)  AS ticket_com_desc
        FROM ped_tot pt JOIN dim_vendedores v ON pt.id_vendedor=v.id_vendedor
        GROUP BY v.id_vendedor, v.nome
        ORDER BY desc_medio DESC
    """, conn)
    df_desc_vend["eficiencia"] = (
        df_desc_vend["ticket_com_desc"].fillna(0) /
        df_desc_vend["ticket_sem_desc"].replace(0, float("nan"))
    ).round(2).fillna(0)

    df_desc_seg = pd.read_sql("""
        SELECT c.segmento,
               ROUND(AVG(fp.desconto_pct),1) AS desc_medio,
               ROUND(100.0*SUM(CASE WHEN fp.desconto_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS freq_desc
        FROM fato_pedidos fp JOIN dim_clientes c ON fp.id_cliente=c.id_cliente
        WHERE fp.status_pedido='Faturado'
        GROUP BY c.segmento ORDER BY desc_medio DESC
    """, conn)

    df_desc_mes = pd.read_sql("""
        SELECT substr(data_pedido,1,7) AS mes,
               ROUND(AVG(desconto_pct),1) AS desc_medio,
               ROUND(100.0*SUM(CASE WHEN desconto_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) AS freq_desc
        FROM fato_pedidos WHERE status_pedido='Faturado'
        GROUP BY mes ORDER BY mes
    """, conn)

    df_margem_impacto = pd.read_sql("""
        SELECT
            ROUND(AVG(CASE WHEN fp.desconto_pct=0
                THEN 100.0*(fp.valor_liquido - p.custo_unit*fp.quantidade)/fp.valor_liquido END),1) AS margem_sem_desc,
            ROUND(AVG(CASE WHEN fp.desconto_pct>0
                THEN 100.0*(fp.valor_liquido - p.custo_unit*fp.quantidade)/fp.valor_liquido END),1) AS margem_com_desc
        FROM fato_pedidos fp JOIN dim_produtos p ON fp.id_produto=p.id_produto
        WHERE fp.status_pedido='Faturado'
    """, conn)

    desc_global  = round(float(pd.read_sql(
        "SELECT AVG(desconto_pct) AS d FROM fato_pedidos WHERE status_pedido='Faturado'", conn
    ).iloc[0]["d"]), 1)
    freq_global  = round(float(pd.read_sql(
        "SELECT 100.0*SUM(CASE WHEN desconto_pct>0 THEN 1 ELSE 0 END)/COUNT(*) AS f FROM fato_pedidos WHERE status_pedido='Faturado'", conn
    ).iloc[0]["f"]), 1)

    # metas_detalhe: atingimento mensal/bimestral/anual/consistência por vendedor
    df_vm = pd.read_sql("""
        SELECT v.nome, v.meta_mensal,
               substr(fp.data_pedido,1,7) AS mes,
               ROUND(SUM(fp.valor_liquido),2) AS fat
        FROM fato_pedidos fp JOIN dim_vendedores v ON fp.id_vendedor=v.id_vendedor
        WHERE fp.status_pedido='Faturado'
        GROUP BY v.id_vendedor, v.nome, v.meta_mensal, mes
        ORDER BY v.nome, mes
    """, conn)

    _pm  = {1:0.8,2:0.7,3:0.9,4:0.9,5:1.0,6:1.0,7:1.0,8:1.0,9:1.05,10:1.1,11:1.4,12:1.6}
    _pn  = {k: v / sum(_pm.values()) * 12 for k, v in _pm.items()}
    _bn  = {1:"Jan-Fev",2:"Jan-Fev",3:"Mar-Abr",4:"Mar-Abr",
            5:"Mai-Jun",6:"Mai-Jun",7:"Jul-Ago",8:"Jul-Ago",
            9:"Set-Out",10:"Set-Out",11:"Nov-Dez",12:"Nov-Dez"}

    df_vm["mes_num"]      = df_vm["mes"].apply(lambda m: int(m[5:7]))
    df_vm["meta_sazonal"] = (df_vm["meta_mensal"] * df_vm["mes_num"].map(_pn)).round(0)
    df_vm["ating_pct"]    = (df_vm["fat"] / df_vm["meta_sazonal"] * 100).round(1)
    df_vm["ano"]          = df_vm["mes"].str[:4]
    df_vm["bim"]          = df_vm.apply(lambda r: f"{_bn[r['mes_num']]}/{r['ano'][2:]}", axis=1)
    df_vm["bim_sort"]     = df_vm.apply(lambda r: r["ano"] + str((r["mes_num"]-1)//2), axis=1)

    mensal_avg = (df_vm.groupby("nome")
                  .agg(fat_total=("fat","sum"), meta_total=("meta_sazonal","sum"),
                       n_meses=("mes","count"))
                  .reset_index())
    mensal_avg["ating_pct"] = (mensal_avg["fat_total"] / mensal_avg["meta_total"] * 100).round(1)
    mensal_avg = mensal_avg.sort_values("ating_pct", ascending=False)

    last6_mes = sorted(df_vm["mes"].unique())[-6:]
    last6_df  = df_vm[df_vm["mes"].isin(last6_mes)][["nome","mes","fat","meta_sazonal","ating_pct"]]

    bim_total = (df_vm.groupby(["bim","bim_sort"])
                 .agg(fat=("fat","sum"), meta=("meta_sazonal","sum"))
                 .reset_index().sort_values("bim_sort"))
    bim_total["ating_pct"] = (bim_total["fat"] / bim_total["meta"] * 100).round(1)

    anual_df = (df_vm.groupby(["nome","ano"])
                .agg(fat=("fat","sum"), meta=("meta_sazonal","sum"))
                .reset_index())
    anual_df["ating_pct"] = (anual_df["fat"] / anual_df["meta"] * 100).round(1)
    anual_df = anual_df.sort_values(["ano","nome"])

    cons = (df_vm.groupby("nome")
            .apply(lambda g: pd.Series({
                "n_acima":  int((g["ating_pct"]>=100).sum()),
                "n_total":  int(len(g)),
                "pct_cons": round(float((g["ating_pct"]>=100).mean()*100), 1)
            }))
            .reset_index()
            .sort_values("pct_cons", ascending=False))

    ytd_g = df_vm[df_vm["ano"]=="2026"]
    ytd_a = (ytd_g.groupby(["nome","meta_mensal"])
             .agg(ytd_fat=("fat","sum"), ytd_meta=("meta_sazonal","sum"))
             .reset_index())
    ytd_a["meta_anual"] = (ytd_a["meta_mensal"] * 12).astype(int)
    ytd_a["proj_anual"] = (ytd_a["ytd_fat"] / ytd_a["ytd_meta"] * ytd_a["meta_anual"]).round(0).astype(int)
    ytd_a["proj_ating"] = (ytd_a["proj_anual"] / ytd_a["meta_anual"] * 100).round(1)
    cons_proj = cons.merge(ytd_a[["nome","meta_anual","proj_anual","proj_ating"]], on="nome", how="left")

    fat_total   = round(float(df_mens["fat"].sum()), 2)
    n_meses     = max(len(df_mens), 1)
    # ticket correto: valor total por pedido (sum de itens), depois média entre pedidos faturados
    ticket      = round(float(
        df_ped_tot[df_ped_tot["status"] == "Faturado"]["valor"].mean()
    ), 2)
    pedidos_tot = int(df_ped_tot[df_ped_tot["status"] == "Faturado"]["id_pedido"].nunique())
    cli_ativos  = int(pd.read_sql(
        "SELECT COUNT(*) AS n FROM dim_clientes WHERE status='Ativo'",conn
    ).iloc[0]["n"])
    taxa_inad   = float(pd.read_sql("""
        SELECT ROUND(100.0*SUM(CASE WHEN status_titulo='Vencido' THEN 1 ELSE 0 END)/COUNT(*),1) AS t
        FROM fato_financeiro
    """,conn).iloc[0]["t"])
    margem      = float(pd.read_sql("""
        SELECT ROUND(100.0*(1-SUM(p.custo_unit*fp.quantidade)/SUM(fp.valor_liquido)),1) AS m
        FROM fato_pedidos fp JOIN dim_produtos p ON fp.id_produto=p.id_produto
        WHERE fp.status_pedido='Faturado'
    """,conn).iloc[0]["m"])

    conn.close()

    data = {
        "kpis": {
            "fat_total":    fat_total,
            "media_mensal": round(fat_total / n_meses, 2),
            "ticket":       ticket,
            "pedidos":      pedidos_tot,
            "clientes":     cli_ativos,
            "inadimplencia":taxa_inad,
            "margem":       margem,
            "desc_medio":   desc_global,
            "freq_desc":    freq_global,
        },
        "fat_mensal":    {"labels": df_mens["mes"].tolist(),      "fat": df_mens["fat"].tolist(),        "pedidos": df_mens["pedidos"].tolist()},
        "categorias":    {"labels": df_cat["categoria"].tolist(), "valores": df_cat["receita"].tolist()},
        "regioes":       {"labels": df_reg["regiao"].tolist(),    "valores": df_reg["receita"].tolist()},
        "top10":         {"labels": [n[:32] for n in df_top10["nome"].tolist()], "valores": df_top10["receita"].tolist()},
        "vendedores":    {"labels": df_vend["nome"].tolist(),     "real": df_vend["media"].tolist(),     "meta": df_vend["meta_mensal"].tolist()},
        "funil":         {"etapas": df_funil["etapa"].tolist(),   "qtd": df_funil["qtd"].tolist(),       "valor": df_funil["valor"].tolist()},
        "inadimplencia": {"labels": df_inad["segmento"].tolist(), "taxa": df_inad["taxa"].tolist()},
        "segmentos":     {"labels": df_seg["segmento"].tolist(),  "qtd": df_seg["qtd"].tolist()},
        "ticket_detalhe": ticket_detalhe,
        "inad_detalhe":   inad_detalhe,
        "fat_detalhe":    fat_detalhe,
        "margem_detalhe": margem_detalhe,
        "cli_detalhe": {
            "segmentos":    df_cli_seg.to_dict("records"),
            "regioes":      df_cli_reg.to_dict("records"),
            "ativos_mes":   df_ativos_mes.to_dict("records"),
            "novos_mes":    df_novos_mes.to_dict("records"),
            "top_inativos": df_top_inativos.to_dict("records"),
            "delta":        delta_cli,
            "mes_ant":      mes_ant_cli,
        },
        "desc_detalhe": {
            "vendedores":      df_desc_vend.to_dict("records"),
            "segmentos":       df_desc_seg.to_dict("records"),
            "mensal":          df_desc_mes.to_dict("records"),
            "margem_sem_desc": float(df_margem_impacto.iloc[0]["margem_sem_desc"]),
            "margem_com_desc": float(df_margem_impacto.iloc[0]["margem_com_desc"]),
        },
        "metas_detalhe": {
            "mensal_avg":   mensal_avg[["nome","fat_total","meta_total","ating_pct","n_meses"]].to_dict("records"),
            "mensal_last6": last6_df.sort_values(["mes","nome"]).to_dict("records"),
            "bimestral":    bim_total[["bim","fat","meta","ating_pct"]].to_dict("records"),
            "anual":        anual_df[["nome","ano","fat","meta","ating_pct"]].to_dict("records"),
            "consistencia": cons_proj[["nome","n_acima","n_total","pct_cons","meta_anual","proj_anual","proj_ating"]].fillna(0).to_dict("records"),
        },
        "abc_detalhe": {
            "curva":        df_abc_raw[["nome_fantasia","segmento","regiao","vendedor",
                                        "receita_total","indiv_pct","cumul_pct","classe",
                                        "ultimo_pedido"]].head(50).to_dict("records"),
            "por_segmento": df_abc_seg.to_dict("records"),
            "por_regiao":   df_abc_reg.to_dict("records"),
            "por_vendedor": df_abc_vend.to_dict("records"),
            "n_total":      n_abc_total,
            "n_classe_a":   n_abc_a,
            "rec_risco":    rec_em_risco,
        },
        "estoque_detalhe": {
            "produtos":     df_est_full[["nome","categoria","entradas","saidas","saldo",
                                         "cobertura_dias","giro","status"]].to_dict("records"),
            "categorias":   df_est_cat.to_dict("records"),
            "movimento":    df_est_mes.to_dict("records"),
            "n_critico":    _n_critico,
            "n_parado":     _n_parado,
            "cob_media":    _cob_media,
        },
        "giro_detalhe": {
            "scatter":      df_giro_scatter.fillna(0).to_dict("records"),
            "hist_rec":     df_hist_rec.to_dict("records"),
            "segmentos":    df_giro_seg.to_dict("records"),
            "med_rec":      _rec_med_card,
            "med_freq":     _freq_med_card,
            "med_ticket":   _tick_med_card,
            "corte_rec":    round(_med_rec, 0),
            "corte_freq":   round(_med_freq, 0),
        },
        "conv_detalhe": {
            "perfil":     df_conv_perfil.to_dict("records"),
            "segmentos":  df_conv_seg.to_dict("records"),
            "evolucao":   df_conv_evo[["mes","taxa_inad","compradores"]].to_dict("records"),
            "n_inadimpl": _n_inad,
            "pct_parou":  _pct_parou,
        },
    }

    # ── HTML ──────────────────────────────────────────────────────────────────────
    HTML = """<!DOCTYPE html>
    <html lang="pt-BR">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Toronto LTDA — Painel Executivo</title>
    <script src="chartjs.min.js"></script>
    <style>
    :root{
      --bg:#0d0f14;--card:#161923;--border:#252a37;
      --gold:#c9a227;--gold2:#e8c04a;--text:#e2e8f0;
      --muted:#8892a4;--red:#e05252;--green:#4caf84;
      --blue:#4a9eed;--purple:#9b7fe8;--r:12px;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,sans-serif}

    header{background:linear-gradient(135deg,#1a1228,#0d0f14);border-bottom:1px solid var(--border);padding:16px 28px;display:flex;align-items:center;justify-content:space-between}
    .logo{display:flex;align-items:center;gap:12px}
    .logo-icon{width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,var(--gold),#7a3f0e);display:flex;align-items:center;justify-content:center;font-size:20px}
    .logo h1{font-size:1.1rem;font-weight:700}
    .logo span{font-size:.7rem;color:var(--muted);display:block;margin-top:2px}
    .hd-meta{text-align:right;font-size:.72rem;color:var(--muted)}
    .hd-meta strong{color:var(--gold)}

    main{padding:24px 28px;max-width:1400px;margin:0 auto}

    .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:22px}
    .kpi{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:18px;position:relative;overflow:hidden}
    .kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,var(--gold))}
    .kpi-icon{font-size:1.3rem;margin-bottom:8px}
    .kpi-label{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
    .kpi-value{font-size:1.4rem;font-weight:700;margin:4px 0 2px}
    .kpi-sub{font-size:.68rem;color:var(--muted)}

    .grid{display:grid;gap:18px;margin-bottom:18px}
    .g1{grid-template-columns:1fr}
    .g2{grid-template-columns:1fr 1fr}
    .g3{grid-template-columns:1fr 1fr 1fr}

    .card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:20px}
    .card-title{font-size:.65rem;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin-bottom:14px;display:flex;align-items:center;gap:7px}
    .card-title em{color:var(--gold);font-style:normal;font-size:.8rem}
    .ch{position:relative}

    footer{border-top:1px solid var(--border);padding:14px 28px;display:flex;justify-content:space-between}
    footer p{font-size:.7rem;color:var(--muted)}

    .kpi-clickable{cursor:pointer;transition:border-color .2s,transform .15s}
    .kpi-clickable:hover{border-color:var(--gold);transform:translateY(-2px)}
    .kpi-hint{font-size:.58rem;color:var(--gold);margin-top:5px;opacity:.75}

    .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:100;display:flex;align-items:center;justify-content:center}
    .modal-box{background:var(--card);border:1px solid var(--border);border-radius:var(--r);width:min(860px,94vw);max-height:90vh;overflow-y:auto;padding:24px}
    .modal-hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
    .modal-hd h2{font-size:.85rem;font-weight:700;letter-spacing:.5px}
    .modal-close{background:none;border:none;color:var(--muted);font-size:1.4rem;cursor:pointer;padding:2px 8px;border-radius:4px;line-height:1}
    .modal-close:hover{color:var(--text);background:var(--border)}
    .modal-filters{display:flex;gap:8px;margin-bottom:16px}
    .flt{border:1px solid var(--border);background:transparent;color:var(--muted);padding:5px 16px;border-radius:20px;font-size:.72rem;cursor:pointer;transition:all .15s}
    .flt.active{background:var(--ac-flt,var(--green));border-color:var(--ac-flt,var(--green));color:#0d0f14;font-weight:700}
    .modal-tbl{width:100%;border-collapse:collapse;font-size:.72rem;margin-top:16px}
    .modal-tbl th{color:var(--muted);text-transform:uppercase;letter-spacing:.8px;padding:6px 10px;border-bottom:1px solid var(--border);text-align:right}
    .modal-tbl th:first-child{text-align:left}
    .modal-tbl td{padding:6px 10px;border-bottom:1px solid #1e2232;text-align:right}
    .modal-tbl td:first-child{text-align:left;color:var(--muted)}
    .modal-tbl tr:last-child td{border-bottom:none}
    </style>
    </head>
    <body>

    <header>
      <div class="logo">
        <div class="logo-icon">&#127863;</div>
        <div>
          <h1>Toronto LTDA</h1>
          <span>Importadora &amp; Distribuidora de Vinhos Premium &mdash; Painel Executivo</span>
        </div>
      </div>
      <div class="hd-meta">
        <div>Periodo: <strong>24 meses</strong></div>
        <div id="dt"></div>
      </div>
    </header>

    <main>

      <div class="kpis">
        <div class="kpi kpi-clickable" id="kpi-fat" style="--ac:#c9a227">
          <div class="kpi-icon">&#128176;</div>
          <div class="kpi-label">Faturamento Total</div>
          <div class="kpi-value" id="k-fat"></div>
          <div class="kpi-sub" id="k-fat-sub"></div>
          <div class="kpi-hint">clique para detalhar &#8599;</div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-ticket" style="--ac:#4caf84">
          <div class="kpi-icon">&#128203;</div>
          <div class="kpi-label">Ticket Medio / Pedido</div>
          <div class="kpi-value" id="k-ticket"></div>
          <div class="kpi-sub" id="k-ped"></div>
          <div class="kpi-hint">clique para detalhar &#8599;</div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-cli" style="--ac:#4a9eed">
          <div class="kpi-icon">&#128101;</div>
          <div class="kpi-label">Clientes Ativos</div>
          <div class="kpi-value" id="k-cli"></div>
          <div class="kpi-sub" id="k-cli-sub">base ativa cadastrada</div>
          <div class="kpi-hint" style="color:#4a9eed">clique para detalhar &#8599;</div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-inad" style="--ac:#e05252">
          <div class="kpi-icon">&#9888;</div>
          <div class="kpi-label">Taxa Inadimplencia</div>
          <div class="kpi-value" id="k-inad"></div>
          <div class="kpi-sub">titulos vencidos / total</div>
          <div class="kpi-hint" style="color:var(--red)">clique para detalhar &#8599;</div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-margem" style="--ac:#9b7fe8">
          <div class="kpi-icon">&#128200;</div>
          <div class="kpi-label">Margem Bruta</div>
          <div class="kpi-value" id="k-margem"></div>
          <div class="kpi-sub">tabela vs custo unitario</div>
          <div class="kpi-hint" style="color:#9b7fe8">clique para detalhar &#8599;</div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-desc" style="--ac:#f0853a">
          <div class="kpi-icon">&#127991;</div>
          <div class="kpi-label">Desconto M&eacute;dio</div>
          <div class="kpi-value" id="k-desc"></div>
          <div class="kpi-sub" id="k-desc-sub">dos itens faturados</div>
          <div class="kpi-hint" style="color:#f0853a">clique para detalhar &#8599;</div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-estoque" style="--ac:#a3e635;grid-column:1/-1">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap">
            <div>
              <div class="kpi-icon">&#128230;</div>
              <div class="kpi-label">Giro do Estoque &mdash; Cobertura por Produto</div>
              <div style="font-size:.68rem;color:var(--muted);margin-top:4px">rotatividade · cobertura em dias · produtos em risco</div>
              <div class="kpi-hint" style="color:#a3e635;margin-top:6px">clique para detalhar &#8599;</div>
            </div>
            <div style="display:flex;gap:36px;align-items:flex-start;justify-content:flex-end;flex-wrap:wrap">
              <div>
                <div class="kpi-label">Cobertura M&eacute;dia</div>
                <div class="kpi-value" id="k-est-cob" style="color:#a3e635"></div>
                <div class="kpi-sub">dias de estoque dispon&iacute;vel</div>
              </div>
              <div>
                <div class="kpi-label">Produtos Cr&iacute;ticos</div>
                <div class="kpi-value" id="k-est-crit" style="color:#e05252"></div>
                <div class="kpi-sub">cobertura abaixo de 30 dias</div>
              </div>
              <div>
                <div class="kpi-label">Produtos Parados</div>
                <div class="kpi-value" id="k-est-par" style="color:var(--muted)"></div>
                <div class="kpi-sub">sem sa&iacute;da registrada</div>
              </div>
            </div>
          </div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-giro" style="--ac:#7ec8e3;grid-column:1/-1">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap">
            <div>
              <div class="kpi-icon">&#128260;</div>
              <div class="kpi-label">Pulso da Carteira &mdash; Giro por Cliente</div>
              <div style="font-size:.68rem;color:var(--muted);margin-top:4px">recência · frequência · valor médio por cliente ativo</div>
              <div class="kpi-hint" style="color:#7ec8e3;margin-top:6px">clique para detalhar &#8599;</div>
            </div>
            <div style="display:flex;gap:36px;align-items:flex-start;justify-content:flex-end;flex-wrap:wrap">
              <div>
                <div class="kpi-label">Recência Média</div>
                <div class="kpi-value" id="k-giro-rec" style="color:#7ec8e3"></div>
                <div class="kpi-sub">dias desde &uacute;ltimo pedido</div>
              </div>
              <div>
                <div class="kpi-label">Intervalo M&eacute;dio</div>
                <div class="kpi-value" id="k-giro-freq" style="color:#c9a227"></div>
                <div class="kpi-sub">dias entre pedidos</div>
              </div>
              <div>
                <div class="kpi-label">Ticket M&eacute;dio / Cliente</div>
                <div class="kpi-value" id="k-giro-ticket" style="color:#4caf84"></div>
                <div class="kpi-sub">m&eacute;dia dos pedidos faturados</div>
              </div>
            </div>
          </div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-conv" style="--ac:#d45f8a;grid-column:1/-1">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap">
            <div>
              <div class="kpi-icon">&#128308;</div>
              <div class="kpi-label">Inadimpl&ecirc;ncia &times; Convers&atilde;o de Pedidos</div>
              <div style="font-size:.68rem;color:var(--muted);margin-top:4px">clientes que inadimpliram &mdash; quantos voltaram a comprar?</div>
              <div class="kpi-hint" style="color:#d45f8a;margin-top:6px">clique para detalhar &#8599;</div>
            </div>
            <div style="display:flex;gap:36px;align-items:flex-start;justify-content:flex-end;flex-wrap:wrap">
              <div>
                <div class="kpi-label">Pararam de Comprar</div>
                <div class="kpi-value" id="k-conv-pct" style="color:#d45f8a"></div>
                <div class="kpi-sub">dos inadimplentes</div>
              </div>
              <div>
                <div class="kpi-label">Continuaram Comprando</div>
                <div class="kpi-value" id="k-conv-cont" style="color:#4caf84"></div>
                <div class="kpi-sub">reativados ap&oacute;s inadimpl&ecirc;ncia</div>
              </div>
              <div>
                <div class="kpi-label">Clientes Inadimplentes</div>
                <div class="kpi-value" id="k-conv-n" style="color:var(--text)"></div>
                <div class="kpi-sub">total com t&iacute;tulo vencido</div>
              </div>
            </div>
          </div>
        </div>
        <div class="kpi kpi-clickable" id="kpi-abc" style="--ac:#2abfbf;grid-column:1/-1">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:24px;flex-wrap:wrap">
            <div>
              <div class="kpi-icon">&#9201;</div>
              <div class="kpi-label">Recupera&ccedil;&atilde;o de Carteira &mdash; Curva ABC</div>
              <div style="font-size:.68rem;color:var(--muted);margin-top:4px">clientes que j&aacute; compraram mas est&atilde;o inativos h&aacute; +4 meses</div>
              <div class="kpi-hint" style="color:#2abfbf;margin-top:6px">clique para detalhar &#8599;</div>
            </div>
            <div style="display:flex;gap:36px;align-items:flex-start;justify-content:flex-end;flex-wrap:wrap">
              <div>
                <div class="kpi-label">Inativos Comportamentais</div>
                <div class="kpi-value" id="k-abc-n" style="color:var(--text)"></div>
                <div class="kpi-sub">clientes sem pedido recente</div>
              </div>
              <div>
                <div class="kpi-label">Receita Hist&oacute;rica em Risco</div>
                <div class="kpi-value" id="k-abc-rec" style="color:#2abfbf"></div>
                <div class="kpi-sub">soma das compras anteriores</div>
              </div>
              <div>
                <div class="kpi-label">Classe A &mdash; priorit&aacute;rios</div>
                <div class="kpi-value" id="k-abc-a" style="color:var(--gold)"></div>
                <div class="kpi-sub">80% da receita em risco</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid g1">
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Evolucao do Faturamento Mensal</div>
          <div class="ch" style="height:230px"><canvas id="c1"></canvas></div>
        </div>
      </div>

      <div class="grid g3">
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Receita por Categoria</div>
          <div class="ch" style="height:220px"><canvas id="c2"></canvas></div>
        </div>
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Receita por Regiao</div>
          <div class="ch" style="height:220px"><canvas id="c3"></canvas></div>
        </div>
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Mix de Clientes</div>
          <div class="ch" style="height:220px"><canvas id="c4"></canvas></div>
        </div>
      </div>

      <div class="grid g1">
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Top 10 Produtos por Receita Liquida</div>
          <div class="ch" style="height:255px"><canvas id="c5"></canvas></div>
        </div>
      </div>

      <div class="grid g2">
        <div class="card" id="card-metas" style="cursor:pointer" title="Clique para analisar metas">
          <div class="card-title"><em>&#9679;</em> Vendedores: M&eacute;dia Mensal vs Meta <span style="color:var(--gold);font-size:.6rem;margin-left:8px">detalhar &#8599;</span></div>
          <div class="ch" style="height:250px"><canvas id="c6"></canvas></div>
        </div>
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Funil de Vendas</div>
          <div class="ch" style="height:250px"><canvas id="c7"></canvas></div>
        </div>
      </div>

      <div class="grid g1">
        <div class="card">
          <div class="card-title"><em>&#9679;</em> Taxa de Inadimplencia por Segmento (%)</div>
          <div class="ch" style="height:190px"><canvas id="c8"></canvas></div>
        </div>
      </div>

    </main>

    <div id="modal-margem" class="modal-overlay" style="display:none">
      <div class="modal-box">
        <div class="modal-hd">
          <h2>&#128200;&nbsp; Margem Bruta &mdash; Composi&ccedil;&atilde;o</h2>
          <button class="modal-close" id="margem-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="categoria" style="--ac-flt:#9b7fe8">Por Categoria</button>
          <button class="flt" data-v="vendedor" style="--ac-flt:#4caf84">Por Vendedor</button>
        </div>
        <div class="ch" style="height:240px"><canvas id="c-margem"></canvas></div>
        <table class="modal-tbl" style="margin-top:16px">
          <thead><tr><th id="mg-col1">Categoria</th><th>Receita</th><th>Custo</th><th>Margem R$</th><th>Margem %</th></tr></thead>
          <tbody id="margem-tbody"></tbody>
        </table>
        <div style="margin-top:18px;padding:14px 16px;background:#0d0f14;border:1px solid #252a37;border-left:3px solid #9b7fe8;border-radius:8px;font-size:.7rem;line-height:1.7;color:#8892a4">
          <div style="color:#9b7fe8;font-weight:700;font-size:.72rem;margin-bottom:6px">&#128712;&nbsp; Como ler esta margem</div>
          <b style="color:#e2e8f0">Receita L&iacute;quida</b> &mdash; valor do pedido j&aacute; com desconto aplicado (pre&ccedil;o de tabela &times; qtd &times; (1 &minus; desconto%)).<br>
          <b style="color:#e2e8f0">Custo</b> &mdash; custo unit&aacute;rio do produto &times; quantidade vendida. Representa o valor pago ao fornecedor por aquele lote.<br>
          <b style="color:#e2e8f0">Margem Bruta R$</b> &mdash; Receita &minus; Custo. &Eacute; o lucro antes de descontar despesas operacionais, log&iacute;stica e impostos.<br>
          <b style="color:#e2e8f0">Margem Bruta %</b> &mdash; Margem R$ &divide; Receita &times; 100. Indica quanto de cada real faturado sobra ap&oacute;s cobrir o custo de compra.<br>
          <span style="color:#555f6e">&#9888; Esta &eacute; uma margem bruta comercial simplificada &mdash; n&atilde;o inclui fretes, impostos, devolu&ccedil;&otilde;es nem custos fixos.</span>
        </div>
      </div>
    </div>

    <div id="modal-fat" class="modal-overlay" style="display:none">
      <div class="modal-box">
        <div class="modal-hd">
          <h2>&#128176;&nbsp; Faturamento &mdash; Detalhamento</h2>
          <button class="modal-close" id="fat-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="total">Total</button>
          <button class="flt" data-v="categoria" style="--ac-flt:#9b7fe8">Por Categoria</button>
          <button class="flt" data-v="regiao" style="--ac-flt:#4a9eed">Por Regi&atilde;o</button>
        </div>
        <div class="ch" style="height:220px"><canvas id="c-fat"></canvas></div>
        <table class="modal-tbl" style="margin-top:16px">
          <thead id="fat-thead"></thead>
          <tbody id="fat-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="modal-inad" class="modal-overlay" style="display:none">
      <div class="modal-box">
        <div class="modal-hd">
          <h2>&#9888;&nbsp; Inadimpl&ecirc;ncia &mdash; Evolu&ccedil;&atilde;o e Detalhamento</h2>
          <button class="modal-close" id="inad-close">&times;</button>
        </div>
        <div class="ch" style="height:210px"><canvas id="c-inad"></canvas></div>
        <p style="font-size:.62rem;color:var(--muted);margin:6px 0 14px;text-align:right">
          * M&ecirc;s corrente subestimado &mdash; t&iacute;tulos recentes ainda n&atilde;o vencidos
        </p>
        <table class="modal-tbl">
          <thead><tr><th>Segmento</th><th>T&iacute;tulos</th><th>Vencidos</th><th>Taxa %</th></tr></thead>
          <tbody id="inad-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="modal-ticket" class="modal-overlay" style="display:none">
      <div class="modal-box">
        <div class="modal-hd">
          <h2>&#128203;&nbsp; Ticket M&eacute;dio &mdash; Evolu&ccedil;&atilde;o por Status</h2>
          <button class="modal-close" id="tm-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-s="Faturado" style="--ac-flt:#4caf84">Faturado</button>
          <button class="flt" data-s="Cancelado" style="--ac-flt:#e05252">Cancelado</button>
          <button class="flt" data-s="Devolvido" style="--ac-flt:#f0853a">Devolvido</button>
        </div>
        <div class="ch" style="height:220px"><canvas id="c-tm"></canvas></div>
        <table class="modal-tbl">
          <thead><tr><th>M&ecirc;s</th><th>Pedidos</th><th>Ticket M&eacute;dio</th><th>Total</th></tr></thead>
          <tbody id="tm-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="modal-metas" class="modal-overlay" style="display:none">
      <div class="modal-box" style="width:min(980px,94vw)">
        <div class="modal-hd">
          <h2>&#127919;&nbsp; Metas &mdash; Atingimento por Granularidade</h2>
          <button class="modal-close" id="metas-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="mensal"      style="--ac-flt:#c9a227">Mensal</button>
          <button class="flt" data-v="bimestral" style="--ac-flt:#4caf84">Bimestral</button>
          <button class="flt" data-v="anual"     style="--ac-flt:#4a9eed">Anual</button>
          <button class="flt" data-v="consist"   style="--ac-flt:#9b7fe8">Consist&ecirc;ncia</button>
        </div>
        <div class="ch" style="height:240px"><canvas id="c-metas"></canvas></div>
        <table class="modal-tbl" style="margin-top:14px">
          <thead id="metas-thead"></thead>
          <tbody id="metas-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="modal-desc" class="modal-overlay" style="display:none">
      <div class="modal-box" style="width:min(960px,94vw)">
        <div class="modal-hd">
          <h2>&#127991;&nbsp; Desconto &mdash; Distribui&ccedil;&atilde;o, Efici&ecirc;ncia e Tend&ecirc;ncia</h2>
          <button class="modal-close" id="desc-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="vendedor" style="--ac-flt:#f0853a">Por Vendedor</button>
          <button class="flt" data-v="scatter"  style="--ac-flt:#4a9eed">Desc &times; Ticket</button>
          <button class="flt" data-v="segmento" style="--ac-flt:#9b7fe8">Por Segmento</button>
          <button class="flt" data-v="evolucao" style="--ac-flt:#4caf84">Evolu&ccedil;&atilde;o</button>
        </div>
        <div class="ch" style="height:240px"><canvas id="c-desc"></canvas></div>
        <div id="desc-sec-tabela">
          <table class="modal-tbl" style="margin-top:14px">
            <thead id="desc-thead"></thead>
            <tbody  id="desc-tbody"></tbody>
          </table>
        </div>
        <div id="desc-sec-margem" style="margin-top:18px;padding:14px 16px;background:#0d0f14;border:1px solid #252a37;border-left:3px solid #f0853a;border-radius:8px;font-size:.7rem;line-height:1.8;color:#8892a4">
          <div style="color:#f0853a;font-weight:700;font-size:.72rem;margin-bottom:6px">&#128200;&nbsp; Impacto do desconto na margem bruta</div>
          <span id="desc-margem-txt"></span>
        </div>
      </div>
    </div>

    <div id="modal-cli" class="modal-overlay" style="display:none">
      <div class="modal-box">
        <div class="modal-hd">
          <h2>&#128101;&nbsp; Clientes &mdash; Atividade e Recupera&ccedil;&atilde;o</h2>
          <button class="modal-close" id="cli-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="segmento" style="--ac-flt:#4a9eed">Por Segmento</button>
          <button class="flt" data-v="regiao" style="--ac-flt:#4caf84">Por Regi&atilde;o</button>
          <button class="flt" data-v="evolucao" style="--ac-flt:#9b7fe8">Evolu&ccedil;&atilde;o Mensal</button>
        </div>
        <div class="ch" style="height:240px"><canvas id="c-cli"></canvas></div>
        <div id="cli-sec-breakdown">
          <table class="modal-tbl" style="margin-top:14px">
            <thead><tr>
              <th id="cli-col1">Segmento</th>
              <th style="color:#4caf84">Ativos</th>
              <th style="color:#e05252">Inativos</th>
              <th>Total</th>
              <th>% Ativo</th>
            </tr></thead>
            <tbody id="cli-tbody"></tbody>
          </table>
        </div>
        <div id="cli-sec-inativos" style="display:none">
          <div style="margin-top:20px;padding:10px 14px;background:#0d0f14;border-left:3px solid #9b7fe8;border-radius:6px;font-size:.68rem;color:#9b7fe8;font-weight:700;text-transform:uppercase;letter-spacing:1px">
            &#127919;&nbsp; Sem pedido h&aacute; +4 meses &mdash; maiores receitas hist&oacute;ricas &mdash; potencial de recupera&ccedil;&atilde;o
          </div>
          <table class="modal-tbl" style="margin-top:10px">
            <thead><tr>
              <th style="text-align:left">Cliente</th>
              <th style="text-align:left">Segmento</th>
              <th style="text-align:left">Regi&atilde;o</th>
              <th>Receita Hist&oacute;rica</th>
              <th>&Uacute;lt. Pedido</th>
            </tr></thead>
            <tbody id="cli-inativos-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="modal-estoque" class="modal-overlay" style="display:none">
      <div class="modal-box" style="width:min(980px,94vw)">
        <div class="modal-hd">
          <h2>&#128230;&nbsp; Giro do Estoque &mdash; Cobertura e Rotatividade</h2>
          <button class="modal-close" id="est-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="cobertura" style="--ac-flt:#a3e635">Cobertura</button>
          <button class="flt" data-v="giro"      style="--ac-flt:#c9a227">Giro</button>
          <button class="flt" data-v="movimento" style="--ac-flt:#4a9eed">Movimento</button>
          <button class="flt" data-v="categoria" style="--ac-flt:#9b7fe8">Por Categoria</button>
        </div>
        <div class="ch" style="height:280px"><canvas id="c-est"></canvas></div>
        <div id="est-legenda" style="display:flex;gap:20px;margin:8px 0 4px;font-size:.68rem">
          <span style="color:#e05252">&#9632; Cr&iacute;tico &lt;30d</span>
          <span style="color:#f0853a">&#9632; Aten&ccedil;&atilde;o 30&ndash;90d</span>
          <span style="color:#a3e635">&#9632; Ok &gt;90d</span>
          <span style="color:#555f6e">&#9632; Parado (sem sa&iacute;da)</span>
        </div>
        <table class="modal-tbl" style="margin-top:10px">
          <thead id="est-thead"></thead>
          <tbody id="est-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="modal-giro" class="modal-overlay" style="display:none">
      <div class="modal-box" style="width:min(980px,94vw)">
        <div class="modal-hd">
          <h2>&#128260;&nbsp; Pulso da Carteira &mdash; Giro por Cliente</h2>
          <button class="modal-close" id="giro-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="quadrantes" style="--ac-flt:#7ec8e3">Quadrantes</button>
          <button class="flt" data-v="recencia"   style="--ac-flt:#c9a227">Recência</button>
          <button class="flt" data-v="segmento"   style="--ac-flt:#9b7fe8">Por Segmento</button>
          <button class="flt" data-v="ranking"    style="--ac-flt:#4caf84">Ranking</button>
        </div>
        <div id="giro-legenda-quad" style="display:flex;gap:20px;margin-bottom:8px;font-size:.68rem;flex-wrap:wrap"></div>
        <div class="ch" style="height:300px"><canvas id="c-giro"></canvas></div>
        <div id="giro-nota" style="margin-top:12px;padding:12px 14px;background:#0d0f14;border:1px solid #252a37;border-left:3px solid #7ec8e3;border-radius:8px;font-size:.7rem;line-height:1.7;color:#8892a4;display:none"></div>
        <table class="modal-tbl" style="margin-top:12px">
          <thead id="giro-thead"></thead>
          <tbody id="giro-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="modal-conv" class="modal-overlay" style="display:none">
      <div class="modal-box" style="width:min(920px,94vw)">
        <div class="modal-hd">
          <h2>&#128308;&nbsp; Inadimpl&ecirc;ncia &times; Convers&atilde;o &mdash; Impacto no Comportamento de Compra</h2>
          <button class="modal-close" id="conv-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="recompra"  style="--ac-flt:#d45f8a">Recompra</button>
          <button class="flt" data-v="segmento" style="--ac-flt:#9b7fe8">Por Segmento</button>
          <button class="flt" data-v="evolucao"  style="--ac-flt:#4a9eed">Evolu&ccedil;&atilde;o</button>
        </div>
        <div class="ch" style="height:250px"><canvas id="c-conv"></canvas></div>
        <table class="modal-tbl" style="margin-top:14px">
          <thead id="conv-thead"></thead>
          <tbody id="conv-tbody"></tbody>
        </table>
        <div id="conv-nota" style="margin-top:14px;padding:12px 14px;background:#0d0f14;border:1px solid #252a37;border-left:3px solid #d45f8a;border-radius:8px;font-size:.7rem;line-height:1.7;color:#8892a4;display:none"></div>
      </div>
    </div>

    <div id="modal-abc" class="modal-overlay" style="display:none">
      <div class="modal-box" style="width:min(1000px,94vw)">
        <div class="modal-hd">
          <h2>&#9201;&nbsp; Recupera&ccedil;&atilde;o de Carteira &mdash; Curva ABC</h2>
          <button class="modal-close" id="abc-close">&times;</button>
        </div>
        <div class="modal-filters">
          <button class="flt active" data-v="abc"      style="--ac-flt:#2abfbf">Curva ABC</button>
          <button class="flt" data-v="segmento" style="--ac-flt:#9b7fe8">Por Segmento</button>
          <button class="flt" data-v="regiao"   style="--ac-flt:#4a9eed">Por Regi&atilde;o</button>
          <button class="flt" data-v="vendedor" style="--ac-flt:#4caf84">Por Vendedor</button>
        </div>
        <div class="ch" style="height:260px"><canvas id="c-abc"></canvas></div>
        <div id="abc-legenda" style="display:flex;gap:20px;margin:10px 0 4px;font-size:.68rem">
          <span style="color:#2abfbf">&#9632; Classe A &mdash; top 80% da receita</span>
          <span style="color:#f0853a">&#9632; Classe B &mdash; 80&ndash;95%</span>
          <span style="color:#555f6e">&#9632; Classe C &mdash; cauda</span>
        </div>
        <table class="modal-tbl" style="margin-top:10px">
          <thead id="abc-thead"></thead>
          <tbody id="abc-tbody"></tbody>
        </table>
      </div>
    </div>

    <footer>
      <p>Toronto LTDA &mdash; dados ficticios gerados para portfolio</p>
      <p>Python &middot; Pandas &middot; SQLite &middot; Chart.js 4</p>
    </footer>

    <script>
    const D = DATA_PLACEHOLDER;

    document.getElementById('dt').innerHTML = 'Atualizado em <strong>' + new Date().toLocaleDateString('pt-BR') + '</strong>';

    const brl = v => 'R$ ' + Number(v).toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:0});
    const pct = v => Number(v).toFixed(1) + '%';
    const num = v => Number(v).toLocaleString('pt-BR');

    document.getElementById('k-fat').textContent     = brl(D.kpis.fat_total);
    document.getElementById('k-fat-sub').textContent = 'Media: ' + brl(D.kpis.media_mensal) + '/mes';
    document.getElementById('k-ticket').textContent  = brl(D.kpis.ticket);
    document.getElementById('k-ped').textContent     = num(D.kpis.pedidos) + ' pedidos faturados';
    document.getElementById('k-cli').textContent     = num(D.kpis.clientes);
    document.getElementById('k-inad').textContent    = pct(D.kpis.inadimplencia);
    document.getElementById('k-margem').textContent  = pct(D.kpis.margem);

    (function() {
      const d = D.cli_detalhe.delta;
      const sinal = d >= 0 ? '▲ +' : '▼ ';
      const cor   = d >= 0 ? 'var(--green)' : 'var(--red)';
      document.getElementById('k-cli-sub').innerHTML =
        'base ativa &nbsp;<span style="color:' + cor + ';font-weight:700">' + sinal + Math.abs(d) + '</span> vs ' + D.cli_detalhe.mes_ant;
    })();

    document.getElementById('k-desc').textContent = D.kpis.desc_medio.toFixed(1) + '%';
    document.getElementById('k-desc-sub').textContent = D.kpis.freq_desc.toFixed(1) + '% dos itens com desconto';

    document.getElementById('k-abc-n').textContent   = num(D.abc_detalhe.n_total);
    document.getElementById('k-abc-rec').textContent = brl(D.abc_detalhe.rec_risco);
    document.getElementById('k-abc-a').textContent   = num(D.abc_detalhe.n_classe_a) + ' clientes';

    document.getElementById('k-est-cob').textContent  = num(D.estoque_detalhe.cob_media) + ' dias';
    document.getElementById('k-est-crit').textContent = num(D.estoque_detalhe.n_critico) + ' produtos';
    document.getElementById('k-est-par').textContent  = num(D.estoque_detalhe.n_parado)  + ' produtos';

    document.getElementById('k-giro-rec').textContent    = num(D.giro_detalhe.med_rec) + ' dias';
    document.getElementById('k-giro-freq').textContent   = num(D.giro_detalhe.med_freq) + ' dias';
    document.getElementById('k-giro-ticket').textContent = brl(D.giro_detalhe.med_ticket);

    (function() {
      const pp = D.conv_detalhe.pct_parou;
      const pc = (100 - pp).toFixed(1);
      document.getElementById('k-conv-pct').textContent  = pp.toFixed(1) + '%';
      document.getElementById('k-conv-cont').textContent = pc + '%';
      document.getElementById('k-conv-n').textContent    = num(D.conv_detalhe.n_inadimpl);
    })();

    Chart.defaults.color       = '#e2e8f0';
    Chart.defaults.borderColor = '#252a37';
    Chart.defaults.font.family = 'system-ui,-apple-system,sans-serif';

    const tip = {backgroundColor:'#1a1d27',borderColor:'#252a37',borderWidth:1};
    const sx  = {grid:{color:'#1e2232'},ticks:{color:'#8892a4'}};
    const sy  = {grid:{color:'#1e2232'},ticks:{color:'#8892a4'}};
    const G   = '#c9a227';
    const CATS= ['#c9a227','#4caf84','#4a9eed','#e05252','#9b7fe8','#f0853a'];

    // 1 - Faturamento mensal
    new Chart('c1',{type:'line',data:{
      labels:D.fat_mensal.labels,
      datasets:[{data:D.fat_mensal.fat,borderColor:G,backgroundColor:'rgba(201,162,39,.1)',
        borderWidth:2.5,pointRadius:3,fill:true,tension:.35,label:'Faturamento'}]
    },options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:c=>' '+brl(c.parsed.y)}}},
      scales:{x:{...sx,ticks:{color:'#8892a4',maxTicksLimit:12}},y:{...sy,ticks:{color:'#8892a4',callback:v=>brl(v)}}}}});

    // 2 - Categorias
    new Chart('c2',{type:'doughnut',data:{
      labels:D.categorias.labels,
      datasets:[{data:D.categorias.valores,backgroundColor:CATS,borderWidth:2,borderColor:'#161923'}]
    },options:{responsive:true,maintainAspectRatio:false,cutout:'60%',
      plugins:{legend:{position:'right',labels:{color:'#8892a4',boxWidth:11,padding:10,font:{size:10}}},
        tooltip:{...tip,callbacks:{label:c=>' '+brl(c.parsed)}}}}});

    // 3 - Regioes
    new Chart('c3',{type:'bar',data:{
      labels:D.regioes.labels,
      datasets:[{data:D.regioes.valores,backgroundColor:['#4a9eed','#6ab3f5','#3080d0','#1a60b0'],borderRadius:6}]
    },options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:c=>' '+brl(c.parsed.y)}}},
      scales:{x:{...sx},y:{...sy,ticks:{color:'#8892a4',callback:v=>brl(v)}}}}});

    // 4 - Segmentos
    new Chart('c4',{type:'doughnut',data:{
      labels:D.segmentos.labels,
      datasets:[{data:D.segmentos.qtd,backgroundColor:[...CATS].reverse(),borderWidth:2,borderColor:'#161923'}]
    },options:{responsive:true,maintainAspectRatio:false,cutout:'60%',
      plugins:{legend:{position:'right',labels:{color:'#8892a4',boxWidth:11,padding:10,font:{size:10}}}}}});

    // 5 - Top 10 produtos
    new Chart('c5',{type:'bar',data:{
      labels:D.top10.labels,
      datasets:[{data:D.top10.valores,backgroundColor:'rgba(201,162,39,.75)',
        borderColor:G,borderWidth:1,borderRadius:5,label:'Receita'}]
    },options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:c=>' '+brl(c.parsed.x)}}},
      scales:{x:{...sx,ticks:{color:'#8892a4',callback:v=>brl(v)}},y:{...sy,ticks:{color:'#8892a4',font:{size:10}}}}}});

    // 6 - Vendedores vs meta
    new Chart('c6',{type:'bar',data:{
      labels:D.vendedores.labels,
      datasets:[
        {label:'Real (media mensal)',data:D.vendedores.real,backgroundColor:'rgba(201,162,39,.85)',borderRadius:5},
        {label:'Meta',data:D.vendedores.meta,backgroundColor:'rgba(232,192,74,.2)',
          borderColor:'#e8c04a',borderWidth:1.5,borderRadius:5}
      ]
    },options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'top',labels:{color:'#8892a4',boxWidth:11}},
        tooltip:{...tip,callbacks:{label:c=>' '+brl(c.parsed.y)}}},
      scales:{x:{...sx,ticks:{color:'#8892a4',font:{size:10}}},y:{...sy,ticks:{color:'#8892a4',callback:v=>brl(v)}}}}});

    // 7 - Funil
    new Chart('c7',{type:'bar',data:{
      labels:D.funil.etapas,
      datasets:[{data:D.funil.qtd,borderRadius:5,label:'Oportunidades',
        backgroundColor:D.funil.etapas.map(e=>e==='Ganho'?'#4caf84':e==='Perdido'?'#e05252':'rgba(74,158,237,.7)')}]
    },options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:(c)=>{
        const i=c.dataIndex;return[' '+c.parsed.x+' oportunidades',' Valor: '+brl(D.funil.valor[i])];
      }}}},
      scales:{x:{...sx},y:{...sy}}}});

    // 8 - Inadimplencia
    new Chart('c8',{type:'bar',data:{
      labels:D.inadimplencia.labels,
      datasets:[{data:D.inadimplencia.taxa,borderRadius:5,label:'Taxa %',
        backgroundColor:D.inadimplencia.taxa.map(t=>t>=15?'#e05252':t>=10?'#f0853a':'#4caf84')}]
    },options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:c=>' '+c.parsed.y.toFixed(1)+'%'}}},
      scales:{x:{...sx},y:{...sy,ticks:{color:'#8892a4',callback:v=>v+'%'}}}}});

    // ── Modal Ticket Médio ────────────────────────────────────────────────────────
    const ST_COLOR = {Faturado:'#4caf84', Cancelado:'#e05252', Devolvido:'#f0853a'};
    let tmChart = null;

    function buildTicketModal(status) {
      const rows = D.ticket_detalhe
        .filter(r => r.status === status)
        .sort((a,b) => a.mes.localeCompare(b.mes));
      const color = ST_COLOR[status] || G;

      if (tmChart) { tmChart.destroy(); tmChart = null; }
      tmChart = new Chart('c-tm', {
        type: 'line',
        data: {
          labels: rows.map(r => r.mes),
          datasets: [{
            data: rows.map(r => r.ticket),
            borderColor: color,
            backgroundColor: color + '22',
            borderWidth: 2.5, pointRadius: 4, fill: true, tension: .35, label: 'Ticket'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {display: false},
            tooltip: {...tip, callbacks: {label: c => ' ' + brl(c.parsed.y)}}
          },
          scales: {
            x: {...sx, ticks: {color:'#8892a4', maxTicksLimit:12}},
            y: {...sy, ticks: {color:'#8892a4', callback: v => brl(v)}}
          }
        }
      });

      document.getElementById('tm-tbody').innerHTML =
        [...rows].reverse().map(r =>
          `<tr>
            <td>${r.mes}</td>
            <td>${Number(r.n_pedidos).toLocaleString('pt-BR')}</td>
            <td style="color:${color};font-weight:600">${brl(r.ticket)}</td>
            <td>${brl(r.total)}</td>
          </tr>`
        ).join('');
    }

    const modalEl = document.getElementById('modal-ticket');

    document.getElementById('kpi-ticket').addEventListener('click', () => {
      modalEl.style.display = 'flex';
      const activeBtn = document.querySelector('#modal-ticket .flt.active');
      buildTicketModal(activeBtn ? activeBtn.dataset.s : 'Faturado');
    });

    document.getElementById('tm-close').addEventListener('click', () => {
      modalEl.style.display = 'none';
    });

    modalEl.addEventListener('click', e => {
      if (e.target === modalEl) modalEl.style.display = 'none';
    });

    document.querySelectorAll('#modal-ticket .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-ticket .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildTicketModal(btn.dataset.s);
      });
    });

    // ── Modal Margem Bruta ────────────────────────────────────────────────────────
    const margemModalEl = document.getElementById('modal-margem');
    let margemChart = null;

    function buildMargemModal(view) {
      if (margemChart) { margemChart.destroy(); margemChart = null; }
      const rows = view === 'categoria' ? D.margem_detalhe.categorias : D.margem_detalhe.vendedores;
      const labels = rows.map(r => view === 'categoria' ? r.categoria : r.nome);
      const purple = '#9b7fe8', green = '#4caf84', gray = 'rgba(136,146,164,.35)';

      margemChart = new Chart('c-margem', {
        type: 'bar',
        data: {
          labels,
          datasets: [
            {label:'Custo',   data: rows.map(r=>r.custo),     backgroundColor: gray,   borderRadius:4, stack:'s'},
            {label:'Margem',  data: rows.map(r=>r.margem_rs), backgroundColor: view==='categoria'?purple:green, borderRadius:4, stack:'s'}
          ]
        },
        options: {
          indexAxis: 'y', responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {position:'top', labels:{color:'#8892a4', boxWidth:11, font:{size:10}}},
            tooltip: {...tip, callbacks: {
              label: c => ' ' + c.dataset.label + ': ' + brl(c.parsed.x)
            }}
          },
          scales: {
            x: {...sx, stacked:true, ticks:{color:'#8892a4', callback:v=>brl(v)}},
            y: {...sy, stacked:true, ticks:{color:'#8892a4', font:{size:10}}}
          }
        }
      });

      document.getElementById('mg-col1').textContent = view === 'categoria' ? 'Categoria' : 'Vendedor';
      document.getElementById('margem-tbody').innerHTML = rows.map((r,i) => {
        const cor = view==='categoria' ? CATS[i] : green;
        return `<tr>
          <td style="color:${cor}">${view==='categoria' ? r.categoria : r.nome}</td>
          <td>${brl(r.receita)}</td>
          <td style="color:var(--muted)">${brl(r.custo)}</td>
          <td style="color:${cor};font-weight:600">${brl(r.margem_rs)}</td>
          <td style="color:${cor};font-weight:600">${r.margem_pct.toFixed(1)}%</td>
        </tr>`;
      }).join('');
    }

    document.getElementById('kpi-margem').addEventListener('click', () => {
      margemModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-margem .flt.active');
      buildMargemModal(active ? active.dataset.v : 'categoria');
    });
    document.getElementById('margem-close').addEventListener('click', () => { margemModalEl.style.display = 'none'; });
    margemModalEl.addEventListener('click', e => { if (e.target === margemModalEl) margemModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-margem .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-margem .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildMargemModal(btn.dataset.v);
      });
    });

    // ── Modal Faturamento ─────────────────────────────────────────────────────────
    const fatModalEl = document.getElementById('modal-fat');
    let fatChart = null;
    const REG_COLORS = {'Sudeste':'#4a9eed','Sul':'#4caf84','Nordeste':'#f0853a','Centro-Oeste':'#9b7fe8'};

    function buildFatModal(view) {
      if (fatChart) { fatChart.destroy(); fatChart = null; }
      const labels = D.fat_mensal.labels;
      let datasets, thead, tbody;

      if (view === 'total') {
        datasets = [{
          data: D.fat_mensal.fat, borderColor: G, backgroundColor: 'rgba(201,162,39,.1)',
          borderWidth: 2.5, pointRadius: 3, fill: true, tension: .35, label: 'Faturamento'
        }];
        thead = '<tr><th>M&ecirc;s</th><th>Pedidos</th><th>Faturamento</th></tr>';
        tbody = [...labels].map((m,i) => `<tr>
          <td>${m}</td><td>${D.fat_mensal.pedidos[i].toLocaleString('pt-BR')}</td>
          <td style="font-weight:600">${brl(D.fat_mensal.fat[i])}</td></tr>`)
          .reverse().join('');

      } else if (view === 'categoria') {
        const cats = [...new Set(D.fat_detalhe.categorias.map(r => r.categoria))];
        datasets = cats.map((cat, i) => ({
          label: cat,
          data: labels.map(mes => { const r = D.fat_detalhe.categorias.find(x => x.mes===mes && x.categoria===cat); return r ? r.fat : 0; }),
          borderColor: CATS[i], backgroundColor: CATS[i]+'18',
          borderWidth: 2, pointRadius: 2, fill: false, tension: .35
        }));
        const totCat = cats.map(cat => ({
          cat, val: D.fat_detalhe.categorias.filter(r => r.categoria===cat).reduce((s,r)=>s+r.fat,0)
        })).sort((a,b)=>b.val-a.val);
        thead = '<tr><th>Categoria</th><th>Faturamento Total</th><th>% do Total</th></tr>';
        const grand = totCat.reduce((s,r)=>s+r.val,0);
        tbody = totCat.map((r,i) => `<tr>
          <td style="color:${CATS[i]}">${r.cat}</td>
          <td style="font-weight:600">${brl(r.val)}</td>
          <td>${(r.val/grand*100).toFixed(1)}%</td></tr>`).join('');

      } else {
        const regs = [...new Set(D.fat_detalhe.regioes.map(r => r.regiao))];
        datasets = regs.map(reg => ({
          label: reg,
          data: labels.map(mes => { const r = D.fat_detalhe.regioes.find(x => x.mes===mes && x.regiao===reg); return r ? r.fat : 0; }),
          borderColor: REG_COLORS[reg]||'#aaa', backgroundColor: (REG_COLORS[reg]||'#aaa')+'18',
          borderWidth: 2, pointRadius: 2, fill: false, tension: .35
        }));
        const totReg = regs.map(reg => ({
          reg, val: D.fat_detalhe.regioes.filter(r => r.regiao===reg).reduce((s,r)=>s+r.fat,0)
        })).sort((a,b)=>b.val-a.val);
        thead = '<tr><th>Regi&atilde;o</th><th>Faturamento Total</th><th>% do Total</th></tr>';
        const grand = totReg.reduce((s,r)=>s+r.val,0);
        tbody = totReg.map(r => `<tr>
          <td style="color:${REG_COLORS[r.reg]||'#aaa'}">${r.reg}</td>
          <td style="font-weight:600">${brl(r.val)}</td>
          <td>${(r.val/grand*100).toFixed(1)}%</td></tr>`).join('');
      }

      fatChart = new Chart('c-fat', {
        type: 'line', data: {labels, datasets},
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {display: view!=='total', position:'top', labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
            tooltip: {...tip, callbacks: {label: c => ' '+brl(c.parsed.y)}}
          },
          scales: {
            x: {...sx, ticks:{color:'#8892a4', maxTicksLimit:12}},
            y: {...sy, ticks:{color:'#8892a4', callback: v=>brl(v)}}
          }
        }
      });
      document.getElementById('fat-thead').innerHTML = thead;
      document.getElementById('fat-tbody').innerHTML = tbody;
    }

    document.getElementById('kpi-fat').addEventListener('click', () => {
      fatModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-fat .flt.active');
      buildFatModal(active ? active.dataset.v : 'total');
    });
    document.getElementById('fat-close').addEventListener('click', () => { fatModalEl.style.display = 'none'; });
    fatModalEl.addEventListener('click', e => { if (e.target === fatModalEl) fatModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-fat .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-fat .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildFatModal(btn.dataset.v);
      });
    });

    // ── Modal Inadimplência ───────────────────────────────────────────────────────
    const inadModalEl = document.getElementById('modal-inad');
    let inadChart = null;

    function openInadModal() {
      inadModalEl.style.display = 'flex';

      if (inadChart) { inadChart.destroy(); inadChart = null; }
      const rows = D.inad_detalhe.mensal;
      inadChart = new Chart('c-inad', {
        type: 'line',
        data: {
          labels: rows.map(r => r.mes),
          datasets: [{
            data: rows.map(r => r.taxa),
            borderColor: '#e05252',
            backgroundColor: 'rgba(224,82,82,.12)',
            borderWidth: 2.5, pointRadius: 4, fill: true, tension: .35, label: 'Inadimpl.'
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {display: false},
            tooltip: {...tip, callbacks: {
              label: c => ' ' + c.parsed.y.toFixed(1) + '%',
              afterLabel: c => '  ' + rows[c.dataIndex].vencidos + ' vencidos / ' + rows[c.dataIndex].total + ' títulos'
            }}
          },
          scales: {
            x: {...sx, ticks: {color:'#8892a4', maxTicksLimit:12}},
            y: {...sy, ticks: {color:'#8892a4', callback: v => v + '%'}, suggestedMin: 0}
          }
        }
      });

      document.getElementById('inad-tbody').innerHTML =
        D.inad_detalhe.segmentos.map(r => {
          const cor = r.taxa >= 15 ? '#e05252' : r.taxa >= 10 ? '#f0853a' : '#4caf84';
          return `<tr>
            <td>${r.segmento}</td>
            <td>${Number(r.total).toLocaleString('pt-BR')}</td>
            <td>${Number(r.vencidos).toLocaleString('pt-BR')}</td>
            <td style="color:${cor};font-weight:600">${r.taxa.toFixed(1)}%</td>
          </tr>`;
        }).join('');
    }

    document.getElementById('kpi-inad').addEventListener('click', openInadModal);
    document.getElementById('inad-close').addEventListener('click', () => { inadModalEl.style.display = 'none'; });
    inadModalEl.addEventListener('click', e => { if (e.target === inadModalEl) inadModalEl.style.display = 'none'; });

    // ── Modal Metas ───────────────────────────────────────────────────────────────
    const metasModalEl = document.getElementById('modal-metas');
    let metasChart = null;

    function semColor(v, t1, t2) { return v >= t1 ? '#4caf84' : v >= t2 ? '#f0853a' : '#e05252'; }

    function buildMetasModal(view) {
      if (metasChart) { metasChart.destroy(); metasChart = null; }
      const thead = document.getElementById('metas-thead');
      const tbody = document.getElementById('metas-tbody');

      if (view === 'mensal') {
        const rows = D.metas_detalhe.mensal_avg;
        metasChart = new Chart('c-metas', {
          type: 'bar',
          data: {
            labels: rows.map(r => r.nome.split(' ')[0]),
            datasets: [{
              data: rows.map(r => r.ating_pct),
              backgroundColor: rows.map(r => semColor(r.ating_pct, 100, 80) + 'cc'),
              borderRadius: 4, label: 'Ating. %'
            }]
          },
          options: {
            indexAxis:'y', responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{display:false},
              tooltip:{...tip,callbacks:{label:c=>[' Atingimento: '+c.parsed.x.toFixed(1)+'%',' '+rows[c.dataIndex].n_meses+' meses']}}
            },
            scales:{x:{...sx,ticks:{color:'#8892a4',callback:v=>v+'%'},suggestedMax:120},y:{...sy,ticks:{color:'#8892a4'}}}
          }
        });
        const meses = [...new Set(D.metas_detalhe.mensal_last6.map(r=>r.mes))].sort();
        const vends = [...new Set(D.metas_detalhe.mensal_last6.map(r=>r.nome))];
        thead.innerHTML = '<tr><th>Vendedor</th>'+meses.map(m=>'<th>'+m+'</th>').join('')+'</tr>';
        tbody.innerHTML = vends.map(v=>{
          const cells = meses.map(m=>{
            const r=D.metas_detalhe.mensal_last6.find(x=>x.nome===v&&x.mes===m);
            if(!r) return '<td>—</td>';
            return '<td style="color:'+semColor(r.ating_pct,100,80)+';font-weight:600">'+r.ating_pct.toFixed(0)+'%</td>';
          });
          return '<tr><td>'+v+'</td>'+cells.join('')+'</tr>';
        }).join('');

      } else if (view === 'bimestral') {
        const rows = D.metas_detalhe.bimestral;
        metasChart = new Chart('c-metas', {
          type:'bar',
          data:{
            labels:rows.map(r=>r.bim),
            datasets:[{
              data:rows.map(r=>r.ating_pct),
              backgroundColor:rows.map(r=>semColor(r.ating_pct,100,80)+'cc'),
              borderRadius:4, label:'Ating. %'
            }]
          },
          options:{
            responsive:true,maintainAspectRatio:false,
            plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:c=>[' Ating: '+c.parsed.y.toFixed(1)+'%',' Fat: '+brl(rows[c.dataIndex].fat),' Meta: '+brl(rows[c.dataIndex].meta)]}}},
            scales:{x:{...sx,ticks:{color:'#8892a4',font:{size:9}}},y:{...sy,ticks:{color:'#8892a4',callback:v=>v+'%'},suggestedMin:0}}
          }
        });
        thead.innerHTML='<tr><th>Bimestre</th><th>Realizado</th><th>Meta</th><th>Atingimento</th></tr>';
        tbody.innerHTML=rows.map(r=>'<tr><td>'+r.bim+'</td><td>'+brl(r.fat)+'</td><td style="color:var(--muted)">'+brl(r.meta)+'</td><td style="color:'+semColor(r.ating_pct,100,80)+';font-weight:600">'+r.ating_pct.toFixed(1)+'%</td></tr>').join('');

      } else if (view === 'anual') {
        const anos = [...new Set(D.metas_detalhe.anual.map(r=>r.ano))].sort();
        const vends = [...new Set(D.metas_detalhe.anual.map(r=>r.nome))];
        const aCols = [G,'#4caf84','#4a9eed'];
        metasChart = new Chart('c-metas', {
          type:'bar',
          data:{
            labels:vends.map(v=>v.split(' ')[0]),
            datasets:anos.map((ano,i)=>({
              label:ano,
              data:vends.map(v=>{const r=D.metas_detalhe.anual.find(x=>x.nome===v&&x.ano===ano);return r?r.ating_pct:null;}),
              backgroundColor:aCols[i]||'#aaa', borderRadius:4
            }))
          },
          options:{
            indexAxis:'y',responsive:true,maintainAspectRatio:false,
            plugins:{legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.x.toFixed(1)+'%'}}},
            scales:{x:{...sx,ticks:{color:'#8892a4',callback:v=>v+'%'}},y:{...sy,ticks:{color:'#8892a4'}}}
          }
        });
        thead.innerHTML='<tr><th>Vendedor</th>'+anos.map(a=>'<th>'+a+'</th>').join('')+'<th>Fat. Total</th></tr>';
        tbody.innerHTML=vends.map(v=>{
          const cells=anos.map(ano=>{
            const r=D.metas_detalhe.anual.find(x=>x.nome===v&&x.ano===ano);
            if(!r) return '<td>—</td>';
            return '<td style="color:'+semColor(r.ating_pct,100,80)+';font-weight:600">'+r.ating_pct.toFixed(1)+'%</td>';
          });
          const tot=D.metas_detalhe.anual.filter(r=>r.nome===v).reduce((s,r)=>s+r.fat,0);
          return '<tr><td>'+v+'</td>'+cells.join('')+'<td>'+brl(tot)+'</td></tr>';
        }).join('');

      } else {
        const rows = D.metas_detalhe.consistencia;
        metasChart = new Chart('c-metas', {
          type:'bar',
          data:{
            labels:rows.map(r=>r.nome.split(' ')[0]),
            datasets:[{
              data:rows.map(r=>r.pct_cons),
              backgroundColor:rows.map(r=>semColor(r.pct_cons,70,50)+'cc'),
              borderRadius:4, label:'% Meses acima da meta'
            }]
          },
          options:{
            indexAxis:'y',responsive:true,maintainAspectRatio:false,
            plugins:{legend:{display:false},
              tooltip:{...tip,callbacks:{label:c=>[' Consistência: '+c.parsed.x.toFixed(1)+'%',' '+rows[c.dataIndex].n_acima+' de '+rows[c.dataIndex].n_total+' meses']}}},
            scales:{x:{...sx,ticks:{color:'#8892a4',callback:v=>v+'%'},min:0,max:100},y:{...sy,ticks:{color:'#8892a4'}}}
          }
        });
        thead.innerHTML='<tr><th>Vendedor</th><th>Meses Acima</th><th>Consistência</th><th>Meta Anual 2026</th><th>Projeção 2026</th><th>% Proj.</th></tr>';
        tbody.innerHTML=rows.map(r=>{
          const corP=r.proj_ating?semColor(r.proj_ating,100,80):'#8892a4';
          return '<tr><td style="color:#e2e8f0">'+r.nome+'</td>'
            +'<td>'+r.n_acima+'/'+r.n_total+'</td>'
            +'<td style="color:'+semColor(r.pct_cons,70,50)+';font-weight:600">'+r.pct_cons.toFixed(1)+'%</td>'
            +'<td style="color:var(--muted)">'+brl(r.meta_anual)+'</td>'
            +'<td>'+brl(r.proj_anual)+'</td>'
            +'<td style="color:'+corP+';font-weight:600">'+(r.proj_ating?r.proj_ating.toFixed(1)+'%':'—')+'</td></tr>';
        }).join('');
      }
    }

    document.getElementById('card-metas').addEventListener('click', () => {
      metasModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-metas .flt.active');
      buildMetasModal(active ? active.dataset.v : 'mensal');
    });
    document.getElementById('metas-close').addEventListener('click', () => { metasModalEl.style.display = 'none'; });
    metasModalEl.addEventListener('click', e => { if (e.target === metasModalEl) metasModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-metas .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-metas .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildMetasModal(btn.dataset.v);
      });
    });

    // ── Modal Desconto ────────────────────────────────────────────────────────────
    const descModalEl = document.getElementById('modal-desc');
    let descChart = null;
    const ORANGE = '#f0853a';

    function buildDescModal(view) {
      if (descChart) { descChart.destroy(); descChart = null; }
      const secTabela = document.getElementById('desc-sec-tabela');
      const secMargem = document.getElementById('desc-sec-margem');
      const vends = D.desc_detalhe.vendedores;

      if (view === 'vendedor') {
        secTabela.style.display = 'block';
        secMargem.style.display = 'block';
        const labels = vends.map(v => v.nome.split(' ')[0]);
        descChart = new Chart('c-desc', {
          type: 'bar',
          data: {
            labels,
            datasets: [
              {label:'Desc. Médio %', data: vends.map(v=>v.desc_medio),
               backgroundColor:'rgba(240,133,58,.8)', borderRadius:4, yAxisID:'yD'},
              {label:'Freq. c/ Desc. %', data: vends.map(v=>v.freq_desc),
               backgroundColor:'rgba(74,158,237,.6)', borderRadius:4, yAxisID:'yD'}
            ]
          },
          options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.y.toFixed(1)+'%'}}
            },
            scales:{
              x:{...sx,ticks:{color:'#8892a4',font:{size:10}}},
              yD:{...sy,ticks:{color:'#8892a4',callback:v=>v+'%'}}
            }
          }
        });
        document.getElementById('desc-thead').innerHTML =
          '<tr><th>Vendedor</th><th>Pedidos</th><th>Desc. Médio</th><th>Freq. Desc.</th><th>Ticket s/desc</th><th>Ticket c/desc</th><th>Eficiência</th></tr>';
        document.getElementById('desc-tbody').innerHTML = vends.map(v => {
          const ef = v.eficiencia || 0;
          const efLabel = ef >= 1.2 ? '<span style="color:#4caf84">▲ Produtivo</span>'
                        : ef >= 0.9 ? '<span style="color:#f0853a">▶ Neutro</span>'
                        : '<span style="color:#e05252">▼ Improdutivo</span>';
          return '<tr>'
            + '<td style="color:#e2e8f0">' + v.nome + '</td>'
            + '<td>' + v.n_pedidos + '</td>'
            + '<td style="color:' + ORANGE + ';font-weight:600">' + v.desc_medio.toFixed(1) + '%</td>'
            + '<td>' + v.freq_desc.toFixed(1) + '%</td>'
            + '<td>' + (v.ticket_sem_desc ? brl(v.ticket_sem_desc) : '—') + '</td>'
            + '<td>' + (v.ticket_com_desc ? brl(v.ticket_com_desc) : '—') + '</td>'
            + '<td>' + efLabel + '</td>'
            + '</tr>';
        }).join('');
        const ms = D.desc_detalhe.margem_sem_desc.toFixed(1);
        const mc = D.desc_detalhe.margem_com_desc.toFixed(1);
        const diff = (D.desc_detalhe.margem_com_desc - D.desc_detalhe.margem_sem_desc).toFixed(1);
        const corDiff = diff < 0 ? '#e05252' : '#4caf84';
        document.getElementById('desc-margem-txt').innerHTML =
          'Pedidos <b style="color:#e2e8f0">sem desconto</b>: margem bruta média de <b style="color:#4caf84">' + ms + '%</b> &nbsp;|&nbsp; '
          + 'Pedidos <b style="color:#e2e8f0">com desconto</b>: margem bruta média de <b style="color:' + ORANGE + '">' + mc + '%</b><br>'
          + 'Impacto: <b style="color:' + corDiff + '">' + (diff > 0 ? '+' : '') + diff + ' pp</b> de margem ao conceder desconto.';

      } else if (view === 'scatter') {
        secTabela.style.display = 'none';
        secMargem.style.display = 'block';
        const pts = vends.map(v => ({x: v.desc_medio, y: v.ticket_medio, nome: v.nome, n: v.n_pedidos}));
        descChart = new Chart('c-desc', {
          type: 'scatter',
          data: {
            datasets: pts.map((p, i) => ({
              label: p.nome,
              data: [p],
              backgroundColor: CATS[i % CATS.length],
              pointRadius: 9, pointHoverRadius: 12
            }))
          },
          options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{position:'right',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{
                label: c => [' '+c.dataset.label, ' Desc: '+c.raw.x.toFixed(1)+'%', ' Ticket médio: '+brl(c.raw.y), ' Pedidos: '+c.raw.n]
              }}
            },
            scales:{
              x:{...sx,title:{display:true,text:'Desconto Médio (%)',color:'#8892a4'},ticks:{color:'#8892a4',callback:v=>v+'%'}},
              y:{...sy,title:{display:true,text:'Ticket Médio (R$)',color:'#8892a4'},ticks:{color:'#8892a4',callback:v=>brl(v)}}
            }
          }
        });
        const ms = D.desc_detalhe.margem_sem_desc.toFixed(1);
        const mc = D.desc_detalhe.margem_com_desc.toFixed(1);
        document.getElementById('desc-margem-txt').innerHTML =
          'Cada ponto é um vendedor. Posição à <b style="color:#e2e8f0">direita</b> = mais desconto médio. '
          + 'Posição <b style="color:#e2e8f0">acima</b> = ticket maior. '
          + 'Vendedores no quadrante superior-esquerdo usam desconto de forma <b style="color:#4caf84">produtiva</b>; '
          + 'inferior-direito indica desconto <b style="color:#e05252">improdutivo</b>.<br>'
          + 'Margem s/desc: <b style="color:#4caf84">' + ms + '%</b> &nbsp;|&nbsp; Margem c/desc: <b style="color:' + ORANGE + '">' + mc + '%</b>';

      } else if (view === 'segmento') {
        secTabela.style.display = 'block';
        secMargem.style.display = 'none';
        const segs = D.desc_detalhe.segmentos;
        descChart = new Chart('c-desc', {
          type: 'bar',
          data: {
            labels: segs.map(s => s.segmento),
            datasets: [
              {label:'Desc. Médio %', data:segs.map(s=>s.desc_medio), backgroundColor:CATS, borderRadius:4},
            ]
          },
          options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{display:false},
              tooltip:{...tip,callbacks:{label:c=>' Desc. Médio: '+c.parsed.y.toFixed(1)+'%'}}
            },
            scales:{
              x:{...sx,ticks:{color:'#8892a4'}},
              y:{...sy,ticks:{color:'#8892a4',callback:v=>v+'%'}}
            }
          }
        });
        document.getElementById('desc-thead').innerHTML =
          '<tr><th>Segmento</th><th>Desc. Médio</th><th>Freq. c/ Desc.</th></tr>';
        document.getElementById('desc-tbody').innerHTML = segs.map((s, i) =>
          '<tr><td style="color:' + CATS[i] + '">' + s.segmento + '</td>'
          + '<td style="color:' + ORANGE + ';font-weight:600">' + s.desc_medio.toFixed(1) + '%</td>'
          + '<td>' + s.freq_desc.toFixed(1) + '%</td></tr>'
        ).join('');

      } else {
        secTabela.style.display = 'none';
        secMargem.style.display = 'none';
        const rows = D.desc_detalhe.mensal;
        descChart = new Chart('c-desc', {
          type: 'line',
          data: {
            labels: rows.map(r=>r.mes),
            datasets: [
              {label:'Desc. Médio %', data:rows.map(r=>r.desc_medio),
               borderColor:ORANGE, backgroundColor:'rgba(240,133,58,.1)',
               borderWidth:2.5, pointRadius:3, fill:true, tension:.35},
              {label:'Freq. c/ Desc. %', data:rows.map(r=>r.freq_desc),
               borderColor:'#4a9eed', backgroundColor:'transparent',
               borderWidth:2, pointRadius:3, fill:false, tension:.35}
            ]
          },
          options:{
            responsive:true,maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.y.toFixed(1)+'%'}}
            },
            scales:{
              x:{...sx,ticks:{color:'#8892a4',maxTicksLimit:12}},
              y:{...sy,ticks:{color:'#8892a4',callback:v=>v+'%'},suggestedMin:0}
            }
          }
        });
      }
    }

    document.getElementById('kpi-desc').addEventListener('click', () => {
      descModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-desc .flt.active');
      buildDescModal(active ? active.dataset.v : 'vendedor');
    });
    document.getElementById('desc-close').addEventListener('click', () => { descModalEl.style.display = 'none'; });
    descModalEl.addEventListener('click', e => { if (e.target === descModalEl) descModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-desc .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-desc .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildDescModal(btn.dataset.v);
      });
    });

    // ── Modal Clientes Ativos ─────────────────────────────────────────────────────
    const cliModalEl = document.getElementById('modal-cli');
    let cliChart = null;

    function buildCliModal(view) {
      if (cliChart) { cliChart.destroy(); cliChart = null; }
      const breakdown = document.getElementById('cli-sec-breakdown');
      const inativos  = document.getElementById('cli-sec-inativos');

      if (view === 'segmento' || view === 'regiao') {
        const rows = view === 'segmento' ? D.cli_detalhe.segmentos : D.cli_detalhe.regioes;
        const key  = view === 'segmento' ? 'segmento' : 'regiao';
        breakdown.style.display = 'block';
        inativos.style.display  = 'none';

        cliChart = new Chart('c-cli', {
          type: 'bar',
          data: {
            labels: rows.map(r => r[key]),
            datasets: [
              {label:'Ativos',   data: rows.map(r => r.ativos),   backgroundColor:'rgba(76,175,132,.8)',  borderRadius:4, stack:'s'},
              {label:'Inativos', data: rows.map(r => r.inativos), backgroundColor:'rgba(224,82,82,.75)', borderRadius:4, stack:'s'}
            ]
          },
          options: {
            indexAxis:'y', responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.x}}
            },
            scales:{
              x:{...sx,stacked:true},
              y:{...sy,stacked:true,ticks:{color:'#8892a4',font:{size:10}}}
            }
          }
        });

        document.getElementById('cli-col1').textContent = view === 'segmento' ? 'Segmento' : 'Região';
        document.getElementById('cli-tbody').innerHTML = rows.map(r => {
          const cp = r.pct_ativo >= 85 ? '#4caf84' : r.pct_ativo >= 75 ? '#f0853a' : '#e05252';
          return '<tr>'
            + '<td>' + r[key] + '</td>'
            + '<td style="color:#4caf84;font-weight:600">' + r.ativos + '</td>'
            + '<td style="color:#e05252">' + r.inativos + '</td>'
            + '<td>' + r.total + '</td>'
            + '<td style="color:' + cp + ';font-weight:600">' + r.pct_ativo.toFixed(1) + '%</td>'
            + '</tr>';
        }).join('');

      } else {
        breakdown.style.display = 'none';
        inativos.style.display  = 'block';

        const ativMes = D.cli_detalhe.ativos_mes;
        const novosByMes = {};
        D.cli_detalhe.novos_mes.forEach(r => novosByMes[r.mes] = r.novos);

        cliChart = new Chart('c-cli', {
          type:'line',
          data:{
            labels: ativMes.map(r => r.mes),
            datasets:[
              {label:'Compradores no mês', data:ativMes.map(r=>r.ativos_mes),
               borderColor:'#4caf84',backgroundColor:'rgba(76,175,132,.1)',
               borderWidth:2.5,pointRadius:3,fill:true,tension:.35},
              {label:'Novos compradores', data:ativMes.map(r=>novosByMes[r.mes]||0),
               borderColor:'#4a9eed',backgroundColor:'transparent',
               borderWidth:2,pointRadius:3,fill:false,tension:.35}
            ]
          },
          options:{
            responsive:true,maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.y}}
            },
            scales:{
              x:{...sx,ticks:{color:'#8892a4',maxTicksLimit:12}},
              y:{...sy,suggestedMin:0}
            }
          }
        });

        document.getElementById('cli-inativos-tbody').innerHTML =
          D.cli_detalhe.top_inativos.map(r =>
            '<tr>'
            + '<td style="color:#e2e8f0;text-align:left">' + (r.nome_fantasia || '—') + '</td>'
            + '<td style="text-align:left">' + r.segmento + '</td>'
            + '<td style="text-align:left">' + r.regiao + '</td>'
            + '<td style="color:#e05252;font-weight:600">' + brl(r.receita_total) + '</td>'
            + '<td style="color:var(--muted)">' + r.ultimo_pedido + '</td>'
            + '</tr>'
          ).join('');
      }
    }

    document.getElementById('kpi-cli').addEventListener('click', () => {
      cliModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-cli .flt.active');
      buildCliModal(active ? active.dataset.v : 'segmento');
    });
    document.getElementById('cli-close').addEventListener('click', () => { cliModalEl.style.display = 'none'; });
    cliModalEl.addEventListener('click', e => { if (e.target === cliModalEl) cliModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-cli .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-cli .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildCliModal(btn.dataset.v);
      });
    });

    // ── Modal Giro do Estoque ─────────────────────────────────────────────────────
    const estModalEl = document.getElementById('modal-estoque');
    let estChart = null;
    const LIME = '#a3e635';
    const ST_COR = {Crítico:'#e05252', Atenção:'#f0853a', Ok:LIME, Parado:'#3d4558'};

    function cobLabel(d) {
      return d >= 9999 ? 'Parado' : d + 'd';
    }

    function buildEstoqueModal(view) {
      if (estChart) { estChart.destroy(); estChart = null; }
      const thead  = document.getElementById('est-thead');
      const tbody  = document.getElementById('est-tbody');
      const legEnd = document.getElementById('est-legenda');
      legEnd.style.display = view === 'cobertura' ? 'flex' : 'none';

      const prods = D.estoque_detalhe.produtos;

      if (view === 'cobertura') {
        const sorted = prods.slice().sort((a,b) => a.cobertura_dias - b.cobertura_dias).slice(0, 30);
        estChart = new Chart('c-est', {
          type: 'bar',
          data: {
            labels: sorted.map(r => r.nome.substring(0, 28)),
            datasets: [{
              label: 'Cobertura (dias)',
              data: sorted.map(r => Math.min(r.cobertura_dias, 365)),
              backgroundColor: sorted.map(r => ST_COR[r.status] + 'cc'),
              borderColor:     sorted.map(r => ST_COR[r.status]),
              borderWidth: 1, borderRadius: 3
            }]
          },
          options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: {display: false},
              tooltip: {...tip, callbacks: {
                label: c => [
                  ' Cobertura: ' + cobLabel(sorted[c.dataIndex].cobertura_dias),
                  ' Status: ' + sorted[c.dataIndex].status,
                  ' Saldo: ' + num(sorted[c.dataIndex].saldo) + ' un.'
                ]
              }}
            },
            scales: {
              x: {...sx, ticks:{color:'#8892a4', callback:v=>v+'d'}, max:370},
              y: {...sy, ticks:{color:'#8892a4', font:{size:9}}}
            }
          }
        });
        thead.innerHTML = '<tr><th>Produto</th><th>Categoria</th><th>Saldo</th><th>Cobertura</th><th>Status</th></tr>';
        tbody.innerHTML = prods.slice().sort((a,b)=>a.cobertura_dias-b.cobertura_dias).map(r =>
          '<tr>'
          + '<td style="color:#e2e8f0;text-align:left">' + r.nome + '</td>'
          + '<td style="text-align:left">' + r.categoria + '</td>'
          + '<td>' + num(r.saldo) + '</td>'
          + '<td style="font-weight:600;color:' + ST_COR[r.status] + '">' + cobLabel(r.cobertura_dias) + '</td>'
          + '<td style="color:' + ST_COR[r.status] + '">' + r.status + '</td>'
          + '</tr>'
        ).join('');

      } else if (view === 'giro') {
        const sorted = prods.slice().sort((a,b)=>b.giro-a.giro).slice(0,25);
        estChart = new Chart('c-est', {
          type: 'bar',
          data: {
            labels: sorted.map(r=>r.nome.substring(0,28)),
            datasets: [{
              label: 'Índice de Giro',
              data: sorted.map(r=>r.giro),
              backgroundColor: sorted.map(r => {
                if (r.giro >= 2)  return '#4caf84cc';
                if (r.giro >= 1)  return LIME + 'cc';
                if (r.giro >= 0.5) return '#f0853acc';
                return '#e05252cc';
              }),
              borderRadius: 3
            }]
          },
          options: {
            indexAxis:'y', responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{display:false},
              tooltip:{...tip, callbacks:{label:c=>[' Giro: '+c.parsed.x.toFixed(2)+'x',' Saídas: '+num(sorted[c.dataIndex].saidas),' Entradas: '+num(sorted[c.dataIndex].entradas)]}}
            },
            scales:{x:{...sx,ticks:{color:'#8892a4',callback:v=>v+'x'}},y:{...sy,ticks:{color:'#8892a4',font:{size:9}}}}
          }
        });
        thead.innerHTML = '<tr><th>Produto</th><th>Categoria</th><th>Entradas</th><th>Saídas</th><th>Saldo</th><th style="color:' + LIME + '">Giro</th></tr>';
        tbody.innerHTML = prods.slice().sort((a,b)=>b.giro-a.giro).map(r => {
          const cor = r.giro>=2?'#4caf84':r.giro>=1?LIME:r.giro>=0.5?'#f0853a':'#e05252';
          return '<tr>'
            + '<td style="color:#e2e8f0;text-align:left">' + r.nome + '</td>'
            + '<td style="text-align:left">' + r.categoria + '</td>'
            + '<td>' + num(r.entradas) + '</td>'
            + '<td>' + num(r.saidas) + '</td>'
            + '<td>' + num(r.saldo) + '</td>'
            + '<td style="color:' + cor + ';font-weight:600">' + r.giro.toFixed(2) + 'x</td>'
            + '</tr>';
        }).join('');

      } else if (view === 'movimento') {
        const rows = D.estoque_detalhe.movimento;
        estChart = new Chart('c-est', {
          type: 'line',
          data: {
            labels: rows.map(r=>r.mes),
            datasets: [
              {label:'Entradas', data:rows.map(r=>r.entradas),
               borderColor:'#4caf84',backgroundColor:'rgba(76,175,132,.1)',
               borderWidth:2.5,pointRadius:3,fill:true,tension:.35},
              {label:'Saídas',   data:rows.map(r=>r.saidas),
               borderColor:'#e05252',backgroundColor:'rgba(224,82,82,.07)',
               borderWidth:2.5,pointRadius:3,fill:true,tension:.35}
            ]
          },
          options:{
            responsive:true,maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+num(c.parsed.y)+' un.'}}
            },
            scales:{
              x:{...sx,ticks:{color:'#8892a4',maxTicksLimit:12}},
              y:{...sy,ticks:{color:'#8892a4',callback:v=>num(v)}}
            }
          }
        });
        thead.innerHTML = '<tr><th>Mês</th><th style="color:#4caf84">Entradas</th><th style="color:#e05252">Saídas</th><th>Saldo Período</th></tr>';
        tbody.innerHTML = [...rows].reverse().map(r =>
          '<tr><td>' + r.mes + '</td>'
          + '<td style="color:#4caf84">' + num(r.entradas) + '</td>'
          + '<td style="color:#e05252">' + num(r.saidas) + '</td>'
          + '<td style="color:' + (r.entradas>=r.saidas?'#4caf84':'#e05252') + ';font-weight:600">'
          + (r.entradas>=r.saidas?'+':'') + num(r.entradas-r.saidas) + '</td>'
          + '</tr>'
        ).join('');

      } else {
        const cats = D.estoque_detalhe.categorias;
        estChart = new Chart('c-est', {
          type:'bar',
          data:{
            labels:cats.map(c=>c.categoria),
            datasets:[
              {label:'Cobertura média (dias)', data:cats.map(c=>Math.min(c.cobertura_media,365)),
               backgroundColor:LIME+'cc', borderRadius:3},
              {label:'Giro médio (x)',          data:cats.map(c=>c.giro_medio*30),
               backgroundColor:'#c9a227cc', borderRadius:3}
            ]
          },
          options:{
            responsive:true,maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>c.datasetIndex===0?' Cobertura: '+cats[c.dataIndex].cobertura_media+'d':' Giro: '+cats[c.dataIndex].giro_medio.toFixed(2)+'x'}}
            },
            scales:{x:{...sx,ticks:{color:'#8892a4',font:{size:10}}},y:{...sy,ticks:{color:'#8892a4'}}}
          }
        });
        thead.innerHTML = '<tr><th>Categoria</th><th>Produtos</th><th>Saldo Total</th><th style="color:' + LIME + '">Cobertura Média</th><th style="color:#c9a227">Giro Médio</th></tr>';
        tbody.innerHTML = cats.map((c,i) =>
          '<tr>'
          + '<td style="color:' + CATS[i%CATS.length] + ';text-align:left">' + c.categoria + '</td>'
          + '<td>' + c.n_produtos + '</td>'
          + '<td>' + num(c.saldo_total) + '</td>'
          + '<td style="color:' + LIME + ';font-weight:600">' + (c.cobertura_media>=9999?'Parado':c.cobertura_media+'d') + '</td>'
          + '<td style="color:#c9a227;font-weight:600">' + c.giro_medio.toFixed(2) + 'x</td>'
          + '</tr>'
        ).join('');
      }
    }

    document.getElementById('kpi-estoque').addEventListener('click', () => {
      estModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-estoque .flt.active');
      buildEstoqueModal(active ? active.dataset.v : 'cobertura');
    });
    document.getElementById('est-close').addEventListener('click', () => { estModalEl.style.display = 'none'; });
    estModalEl.addEventListener('click', e => { if (e.target === estModalEl) estModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-estoque .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-estoque .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildEstoqueModal(btn.dataset.v);
      });
    });

    // ── Modal Pulso da Carteira — Giro por Cliente ───────────────────────────────
    const giroModalEl = document.getElementById('modal-giro');
    let giroChart = null;
    const QUAD_COR  = {'Campeões':'#4caf84','Em Desenvolvimento':'#c9a227','Em Risco':'#f0853a','Dormentes':'#e05252','Novatos':'#7ec8e3'};
    const QUAD_ICON = {'Campeões':'★','Em Desenvolvimento':'◆','Em Risco':'▲','Dormentes':'●','Novatos':'✦'};
    const LBLUE = '#7ec8e3';

    function buildGiroModal(view) {
      if (giroChart) { giroChart.destroy(); giroChart = null; }
      const thead = document.getElementById('giro-thead');
      const tbody = document.getElementById('giro-tbody');
      const nota  = document.getElementById('giro-nota');
      const legQ  = document.getElementById('giro-legenda-quad');
      nota.style.display = 'none';
      legQ.style.display = 'none';

      if (view === 'quadrantes') {
        legQ.style.display = 'flex';
        legQ.innerHTML = Object.entries(QUAD_COR).map(([q,c]) =>
          '<span style="color:' + c + '">' + QUAD_ICON[q] + ' ' + q + '</span>'
        ).join('');

        const quads = [...new Set(Object.keys(QUAD_COR))];
        const scatter = D.giro_detalhe.scatter;

        giroChart = new Chart('c-giro', {
          type: 'scatter',
          data: {
            datasets: quads.map(q => {
              const pts = scatter.filter(r => r.quadrante === q);
              return {
                label: q,
                data: pts.map(r => ({
                  x: r.intervalo_medio,
                  y: r.recencia_dias,
                  nome: r.nome_fantasia,
                  seg: r.segmento,
                  ticket: r.ticket_medio,
                  n: r.n_pedidos
                })),
                backgroundColor: QUAD_COR[q] + '99',
                borderColor:     QUAD_COR[q],
                pointRadius: pts.map(r => Math.max(4, Math.min(14, Math.sqrt(r.ticket_medio / 800)))),
                pointHoverRadius: 12
              };
            })
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: {position:'right', labels:{color:'#8892a4', boxWidth:12, padding:10, font:{size:10}}},
              tooltip: {...tip, callbacks: {
                label: c => [
                  ' ' + (c.raw.nome || '?'),
                  ' Segmento: ' + c.raw.seg,
                  ' Recência: ' + c.raw.y + ' dias',
                  ' Intervalo médio: ' + c.raw.x + ' dias',
                  ' Ticket médio: ' + brl(c.raw.ticket),
                  ' Pedidos: ' + c.raw.n
                ]
              }}
            },
            scales: {
              x: {...sx,
                title:{display:true,text:'Intervalo médio entre pedidos (dias)',color:'#8892a4'},
                ticks:{color:'#8892a4'}
              },
              y: {...sy,
                title:{display:true,text:'Recência — dias desde último pedido',color:'#8892a4'},
                ticks:{color:'#8892a4'}
              }
            }
          }
        });

        nota.style.display = 'block';
        nota.innerHTML = '<b style="color:#7ec8e3">&#128260;&nbsp; Como ler os quadrantes</b> &mdash; '
          + 'corte: mediana de recência (' + D.giro_detalhe.corte_rec + ' dias) e intervalo médio (' + D.giro_detalhe.corte_freq + ' dias). '
          + '<b style="color:#4caf84">Campeões</b>: recente + frequente. '
          + '<b style="color:#c9a227">Em Desenvolvimento</b>: recente mas espaçado. '
          + '<b style="color:#f0853a">Em Risco</b>: frequente mas sumiu. '
          + '<b style="color:#e05252">Dormentes</b>: sumiu + espaçado. '
          + '<b style="color:#7ec8e3">Novatos</b>: apenas 1 pedido. '
          + 'Tamanho do ponto proporcional ao ticket médio.';

        const contQ = quads.map(q => ({q, n: scatter.filter(r=>r.quadrante===q).length}));
        thead.innerHTML = '<tr><th>Quadrante</th><th>Clientes</th><th>%</th></tr>';
        const totQ = scatter.length;
        tbody.innerHTML = contQ.map(r => '<tr>'
          + '<td style="color:' + QUAD_COR[r.q] + ';text-align:left;font-weight:600">' + QUAD_ICON[r.q] + ' ' + r.q + '</td>'
          + '<td>' + r.n + '</td>'
          + '<td style="color:' + QUAD_COR[r.q] + '">' + (r.n/totQ*100).toFixed(1) + '%</td>'
          + '</tr>').join('');

      } else if (view === 'recencia') {
        const rows = D.giro_detalhe.hist_rec;
        const maxN = Math.max(...rows.map(r=>r.n));
        giroChart = new Chart('c-giro', {
          type: 'bar',
          data: {
            labels: rows.map(r => r.faixa_rec),
            datasets: [{
              label: 'Clientes',
              data: rows.map(r => r.n),
              backgroundColor: rows.map(r => {
                const pct = r.n / maxN;
                if (r.faixa_rec === '0–30d')  return '#4caf84cc';
                if (r.faixa_rec === '31–60d')  return '#7ec8e3cc';
                if (r.faixa_rec === '61–90d')  return '#c9a227cc';
                if (r.faixa_rec === '91–120d') return '#f0853acc';
                return '#e05252cc';
              }),
              borderRadius: 5
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend:{display:false},
              tooltip:{...tip, callbacks:{label:c=>' '+c.parsed.y+' clientes'}}
            },
            scales:{x:{...sx},y:{...sy,ticks:{color:'#8892a4'}}}
          }
        });
        thead.innerHTML = '<tr><th>Faixa de Recência</th><th>Clientes</th><th>%</th><th>Status</th></tr>';
        const totH = rows.reduce((s,r)=>s+r.n,0);
        tbody.innerHTML = rows.map(r => {
          const label = r.faixa_rec==='0–30d'?'<span style="color:#4caf84">Quente</span>'
                      : r.faixa_rec==='31–60d'?'<span style="color:#7ec8e3">Morno</span>'
                      : r.faixa_rec==='61–90d'?'<span style="color:#c9a227">Esfriando</span>'
                      : r.faixa_rec==='91–120d'?'<span style="color:#f0853a">Em Risco</span>'
                      : '<span style="color:#e05252">Frio</span>';
          return '<tr><td style="text-align:left">' + r.faixa_rec + '</td>'
            + '<td>' + r.n + '</td>'
            + '<td>' + (r.n/totH*100).toFixed(1) + '%</td>'
            + '<td>' + label + '</td></tr>';
        }).join('');

      } else if (view === 'segmento') {
        const segs = D.giro_detalhe.segmentos;
        giroChart = new Chart('c-giro', {
          type: 'bar',
          data: {
            labels: segs.map(s=>s.segmento),
            datasets: [
              {label:'Recência (dias)',       data:segs.map(s=>s.rec_media),       backgroundColor:'#7ec8e3cc', borderRadius:3},
              {label:'Intervalo médio (dias)', data:segs.map(s=>s.intervalo_medio), backgroundColor:'#c9a227cc', borderRadius:3},
            ]
          },
          options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{position:'top',labels:{color:'#8892a4',boxWidth:11,font:{size:10}}},
              tooltip:{...tip,callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.y+' dias'}}
            },
            scales:{x:{...sx,ticks:{color:'#8892a4'}},y:{...sy,ticks:{color:'#8892a4',callback:v=>v+'d'}}}
          }
        });
        thead.innerHTML = '<tr><th>Segmento</th><th>Clientes</th><th style="color:#7ec8e3">Recência Média</th><th style="color:#c9a227">Intervalo Médio</th><th style="color:#4caf84">Ticket Médio</th></tr>';
        tbody.innerHTML = segs.map(s => '<tr>'
          + '<td style="color:#e2e8f0;text-align:left">' + s.segmento + '</td>'
          + '<td>' + s.n_clientes + '</td>'
          + '<td style="color:#7ec8e3;font-weight:600">' + s.rec_media + ' dias</td>'
          + '<td style="color:#c9a227;font-weight:600">' + (s.intervalo_medio||'—') + (s.intervalo_medio?' dias':'') + '</td>'
          + '<td style="color:#4caf84;font-weight:600">' + brl(s.ticket_medio) + '</td>'
          + '</tr>').join('');

      } else {
        const top = D.giro_detalhe.scatter
          .slice().sort((a,b)=>b.ticket_medio-a.ticket_medio).slice(0,20);
        giroChart = new Chart('c-giro', {
          type: 'bar',
          data: {
            labels: top.map(r => (r.nome_fantasia||'?').substring(0,22)),
            datasets: [{
              label: 'Ticket Médio',
              data: top.map(r=>r.ticket_medio),
              backgroundColor: top.map(r=>QUAD_COR[r.quadrante]+'cc'),
              borderColor:     top.map(r=>QUAD_COR[r.quadrante]),
              borderWidth: 1, borderRadius: 4
            }]
          },
          options: {
            indexAxis:'y', responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{display:false},
              tooltip:{...tip,callbacks:{label:c=>[' Ticket: '+brl(c.parsed.x),' Quadrante: '+top[c.dataIndex].quadrante,' Segmento: '+top[c.dataIndex].segmento]}}
            },
            scales:{x:{...sx,ticks:{color:'#8892a4',callback:v=>brl(v)}},y:{...sy,ticks:{color:'#8892a4',font:{size:9}}}}
          }
        });
        thead.innerHTML = '<tr><th>Cliente</th><th>Segmento</th><th>Pedidos</th><th style="color:#7ec8e3">Recência</th><th style="color:#c9a227">Intervalo</th><th style="color:#4caf84">Ticket Médio</th><th>Quadrante</th></tr>';
        tbody.innerHTML = top.map(r => '<tr>'
          + '<td style="color:#e2e8f0;text-align:left">' + (r.nome_fantasia||'—') + '</td>'
          + '<td style="text-align:left">' + r.segmento + '</td>'
          + '<td>' + r.n_pedidos + '</td>'
          + '<td style="color:#7ec8e3">' + r.recencia_dias + 'd</td>'
          + '<td style="color:#c9a227">' + (r.intervalo_medio||'—') + (r.intervalo_medio?'d':'') + '</td>'
          + '<td style="color:#4caf84;font-weight:600">' + brl(r.ticket_medio) + '</td>'
          + '<td style="color:' + QUAD_COR[r.quadrante] + ';font-weight:600">' + QUAD_ICON[r.quadrante] + ' ' + r.quadrante + '</td>'
          + '</tr>').join('');
      }
    }

    document.getElementById('kpi-giro').addEventListener('click', () => {
      giroModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-giro .flt.active');
      buildGiroModal(active ? active.dataset.v : 'quadrantes');
    });
    document.getElementById('giro-close').addEventListener('click', () => { giroModalEl.style.display = 'none'; });
    giroModalEl.addEventListener('click', e => { if (e.target === giroModalEl) giroModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-giro .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-giro .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildGiroModal(btn.dataset.v);
      });
    });

    // ── Modal Inadimplência × Conversão ──────────────────────────────────────────
    const convModalEl = document.getElementById('modal-conv');
    let convChart = null;
    const PINK = '#d45f8a';

    function buildConvModal(view) {
      if (convChart) { convChart.destroy(); convChart = null; }
      const thead = document.getElementById('conv-thead');
      const tbody = document.getElementById('conv-tbody');
      const nota  = document.getElementById('conv-nota');
      nota.style.display = 'none';

      if (view === 'recompra') {
        const rows = D.conv_detalhe.perfil;
        const total = rows.reduce((s,r) => s + r.n, 0);
        const parou = (rows.find(r => r.perfil === 'Parou') || {n:0}).n;
        const cont  = (rows.find(r => r.perfil === 'Continuou') || {n:0}).n;
        convChart = new Chart('c-conv', {
          type: 'doughnut',
          data: {
            labels: ['Pararam de comprar', 'Continuaram comprando'],
            datasets: [{
              data: [parou, cont],
              backgroundColor: [PINK + 'cc', '#4caf84cc'],
              borderColor:     [PINK,        '#4caf84'],
              borderWidth: 2
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false, cutout: '62%',
            plugins: {
              legend: {position:'right', labels:{color:'#8892a4', boxWidth:12, padding:12, font:{size:11}}},
              tooltip: {...tip, callbacks: {
                label: c => ' ' + c.label + ': ' + c.parsed + ' (' + (c.parsed/total*100).toFixed(1) + '%)'
              }}
            }
          }
        });
        thead.innerHTML = '<tr><th>Perfil</th><th>Clientes</th><th>%</th></tr>';
        tbody.innerHTML = [
          {perfil:'Pararam de comprar', n:parou, cor:PINK},
          {perfil:'Continuaram comprando', n:cont, cor:'#4caf84'}
        ].map(r => '<tr>'
          + '<td style="color:' + r.cor + ';font-weight:600;text-align:left">' + r.perfil + '</td>'
          + '<td>' + r.n + '</td>'
          + '<td style="color:' + r.cor + ';font-weight:600">' + (r.n/total*100).toFixed(1) + '%</td>'
          + '</tr>').join('');
        nota.style.display = 'block';
        nota.innerHTML = '<b style="color:#d45f8a">&#128161;&nbsp; Como interpretar</b><br>'
          + 'Um cliente &eacute; classificado como <b style="color:#d45f8a">Parou</b> se nunca gerou um pedido faturado '
          + '<em>ap&oacute;s</em> a data do seu primeiro t&iacute;tulo vencido. '
          + 'Isso n&atilde;o significa necessariamente que a inadimpl&ecirc;ncia causou o churn &mdash; pode haver '
          + 'correla&ccedil;&atilde;o com outros fatores &mdash; mas indica clientes que inadimpliram <em>e</em> n&atilde;o voltaram.';

      } else if (view === 'segmento') {
        const src  = D.conv_detalhe.segmentos;
        const segs = [...new Set(src.map(r => r.segmento))];
        convChart = new Chart('c-conv', {
          type: 'bar',
          data: {
            labels: segs,
            datasets: [
              {label:'Pararam', data:segs.map(s=>{const r=src.find(x=>x.segmento===s&&x.perfil==='Parou');return r?r.n:0;}),
               backgroundColor:PINK+'cc', borderColor:PINK, borderWidth:1, borderRadius:3, stack:'s'},
              {label:'Continuaram', data:segs.map(s=>{const r=src.find(x=>x.segmento===s&&x.perfil==='Continuou');return r?r.n:0;}),
               backgroundColor:'#4caf84cc', borderColor:'#4caf84', borderWidth:1, borderRadius:3, stack:'s'}
            ]
          },
          options: {
            indexAxis:'y', responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{position:'top', labels:{color:'#8892a4', boxWidth:11, font:{size:10}}},
              tooltip:{...tip, callbacks:{label:c=>' '+c.dataset.label+': '+c.parsed.x+' clientes'}}
            },
            scales:{x:{...sx,stacked:true},y:{...sy,stacked:true,ticks:{color:'#8892a4'}}}
          }
        });
        thead.innerHTML = '<tr><th>Segmento</th><th style="color:' + PINK + '">Pararam</th><th style="color:#4caf84">Continuaram</th><th>Total</th><th style="color:' + PINK + '">% Parou</th></tr>';
        tbody.innerHTML = segs.map(s => {
          const p = (src.find(x=>x.segmento===s&&x.perfil==='Parou')||{n:0}).n;
          const c = (src.find(x=>x.segmento===s&&x.perfil==='Continuou')||{n:0}).n;
          const t = p + c;
          const pct = t > 0 ? (p/t*100).toFixed(1) : '0.0';
          const cor = parseFloat(pct) >= 50 ? PINK : '#4caf84';
          return '<tr>'
            + '<td style="color:#e2e8f0;text-align:left">' + s + '</td>'
            + '<td style="color:' + PINK + '">' + p + '</td>'
            + '<td style="color:#4caf84">' + c + '</td>'
            + '<td>' + t + '</td>'
            + '<td style="color:' + cor + ';font-weight:600">' + pct + '%</td>'
            + '</tr>';
        }).join('');

      } else {
        const rows = D.conv_detalhe.evolucao;
        convChart = new Chart('c-conv', {
          type: 'line',
          data: {
            labels: rows.map(r => r.mes),
            datasets: [
              {label:'Inadimpl. %', data:rows.map(r=>r.taxa_inad),
               borderColor:PINK, backgroundColor:PINK+'18',
               borderWidth:2.5, pointRadius:3, fill:true, tension:.35, yAxisID:'yI'},
              {label:'Compradores ativos', data:rows.map(r=>r.compradores),
               borderColor:'#4a9eed', backgroundColor:'transparent',
               borderWidth:2, pointRadius:3, fill:false, tension:.35, yAxisID:'yC'}
            ]
          },
          options: {
            responsive:true, maintainAspectRatio:false,
            plugins:{
              legend:{position:'top', labels:{color:'#8892a4', boxWidth:11, font:{size:10}}},
              tooltip:{...tip, callbacks:{
                label:c => c.datasetIndex===0
                  ? ' Inadimpl.: ' + c.parsed.y.toFixed(1) + '%'
                  : ' Compradores: ' + c.parsed.y
              }}
            },
            scales:{
              x:{...sx, ticks:{color:'#8892a4', maxTicksLimit:12}},
              yI:{...sy, position:'left',  ticks:{color:PINK,      callback:v=>v+'%'}, title:{display:true,text:'Inadimpl. %',color:PINK}},
              yC:{type:'linear', position:'right', grid:{display:false}, ticks:{color:'#4a9eed', callback:v=>v}, title:{display:true,text:'Compradores',color:'#4a9eed'}}
            }
          }
        });
        thead.innerHTML = '<tr><th>M&ecirc;s</th><th style="color:' + PINK + '">Inadimpl. %</th><th style="color:#4a9eed">Compradores</th></tr>';
        tbody.innerHTML = [...rows].reverse().map(r =>
          '<tr>'
          + '<td>' + r.mes + '</td>'
          + '<td style="color:' + PINK + ';font-weight:600">' + r.taxa_inad.toFixed(1) + '%</td>'
          + '<td style="color:#4a9eed">' + r.compradores + '</td>'
          + '</tr>'
        ).join('');
        nota.style.display = 'block';
        nota.innerHTML = '<b style="color:#4a9eed">&#128200;&nbsp; Como ler este gr&aacute;fico</b><br>'
          + 'Eixo esquerdo (rosa): taxa de inadimpl&ecirc;ncia mensal &mdash; t&iacute;tulos vencidos emitidos naquele m&ecirc;s. '
          + 'Eixo direito (azul): n&uacute;mero de clientes compradores no m&ecirc;s. '
          + 'Observe se picos de inadimpl&ecirc;ncia precedem quedas de compradores nos meses seguintes.';
      }
    }

    document.getElementById('kpi-conv').addEventListener('click', () => {
      convModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-conv .flt.active');
      buildConvModal(active ? active.dataset.v : 'recompra');
    });
    document.getElementById('conv-close').addEventListener('click', () => { convModalEl.style.display = 'none'; });
    convModalEl.addEventListener('click', e => { if (e.target === convModalEl) convModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-conv .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-conv .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildConvModal(btn.dataset.v);
      });
    });

    // ── Modal Recuperação de Carteira — Curva ABC ─────────────────────────────────
    const abcModalEl = document.getElementById('modal-abc');
    let abcChart = null;
    const ABC_COR = {A:'#2abfbf', B:'#f0853a', C:'#3d4558'};
    const TEAL = '#2abfbf';

    function buildAbcModal(view) {
      if (abcChart) { abcChart.destroy(); abcChart = null; }
      document.getElementById('abc-legenda').style.display = view === 'abc' ? 'flex' : 'none';
      const thead = document.getElementById('abc-thead');
      const tbody = document.getElementById('abc-tbody');

      if (view === 'abc') {
        const rows = D.abc_detalhe.curva.slice(0, 30);
        abcChart = new Chart('c-abc', {
          type: 'bar',
          data: {
            labels: rows.map(r => (r.nome_fantasia || r.segmento || '?').substring(0, 22)),
            datasets: [
              {
                type: 'bar', label: 'Receita Hist.',
                data: rows.map(r => r.receita_total),
                backgroundColor: rows.map(r => ABC_COR[r.classe] + 'cc'),
                borderColor:     rows.map(r => ABC_COR[r.classe]),
                borderWidth: 1, borderRadius: 3, yAxisID: 'y'
              },
              {
                type: 'line', label: 'Acum. %',
                data: rows.map(r => r.cumul_pct),
                borderColor: '#c9a227', borderWidth: 2,
                pointRadius: 0, fill: false, tension: 0, yAxisID: 'y2'
              }
            ]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: {position:'top', labels:{color:'#8892a4', boxWidth:11, font:{size:10}}},
              tooltip: {...tip, callbacks: {
                label: c => c.datasetIndex === 0
                  ? [' Receita: ' + brl(c.parsed.y), ' Classe ' + rows[c.dataIndex].classe + ' (' + rows[c.dataIndex].indiv_pct.toFixed(1) + '%)']
                  : ' Acum.: ' + c.parsed.y.toFixed(1) + '%'
              }}
            },
            scales: {
              x: {...sx, ticks:{color:'#8892a4', font:{size:9}, maxRotation:40}},
              y: {...sy, ticks:{color:'#8892a4', callback: v => brl(v)}},
              y2: {
                type:'linear', position:'right', min:0, max:100,
                grid:{display:false},
                ticks:{color:'#c9a227', callback: v => v + '%'}
              }
            }
          }
        });
        thead.innerHTML = '<tr><th>Cliente</th><th>Segmento</th><th>Regi&atilde;o</th><th>Vendedor</th><th>&Uacute;lt. Pedido</th><th>Receita Hist.</th><th>% Individual</th><th>% Acum.</th><th>Classe</th></tr>';
        tbody.innerHTML = D.abc_detalhe.curva.map(r => {
          const cor = ABC_COR[r.classe];
          return '<tr>'
            + '<td style="color:#e2e8f0;text-align:left">' + (r.nome_fantasia || '—') + '</td>'
            + '<td style="text-align:left">' + r.segmento + '</td>'
            + '<td style="text-align:left">' + r.regiao + '</td>'
            + '<td style="text-align:left">' + (r.vendedor || '—') + '</td>'
            + '<td style="color:var(--muted)">' + r.ultimo_pedido + '</td>'
            + '<td style="font-weight:600">' + brl(r.receita_total) + '</td>'
            + '<td>' + r.indiv_pct.toFixed(1) + '%</td>'
            + '<td style="color:#c9a227">' + r.cumul_pct.toFixed(1) + '%</td>'
            + '<td style="color:' + cor + ';font-weight:700">' + r.classe + '</td>'
            + '</tr>';
        }).join('');

      } else {
        const isVend = view === 'vendedor';
        const isReg  = view === 'regiao';
        const srcMap = {segmento: D.abc_detalhe.por_segmento, regiao: D.abc_detalhe.por_regiao, vendedor: D.abc_detalhe.por_vendedor};
        const src = srcMap[view];
        const dimKey = isVend ? 'vendedor' : isReg ? 'regiao' : 'segmento';
        const dims = [...new Set(src.map(r => r[dimKey]))];
        const classes = ['A','B','C'];

        abcChart = new Chart('c-abc', {
          type: 'bar',
          data: {
            labels: dims,
            datasets: classes.map(cls => ({
              label: 'Classe ' + cls,
              data: dims.map(d => { const r = src.find(x => x[dimKey]===d && x.classe===cls); return r ? r.n : 0; }),
              backgroundColor: ABC_COR[cls] + 'cc',
              borderColor: ABC_COR[cls],
              borderWidth: 1, borderRadius: 3, stack: 's'
            }))
          },
          options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: {
              legend: {position:'top', labels:{color:'#8892a4', boxWidth:11, font:{size:10}}},
              tooltip: {...tip, callbacks: {
                label: c => {
                  const cls = classes[c.datasetIndex];
                  const d = dims[c.dataIndex];
                  const r = src.find(x => x[dimKey]===d && x.classe===cls);
                  return r ? [' Classe ' + cls + ': ' + r.n + ' clientes', ' Receita: ' + brl(r.receita)] : ' 0';
                }
              }}
            },
            scales: {
              x: {...sx, stacked:true},
              y: {...sy, stacked:true, ticks:{color:'#8892a4'}}
            }
          }
        });

        const colLabel = isVend ? 'Vendedor' : isReg ? 'Regi&atilde;o' : 'Segmento';
        thead.innerHTML = '<tr><th>' + colLabel + '</th>'
          + classes.map(c => '<th style="color:' + ABC_COR[c] + '">Classe ' + c + ' (n)</th><th style="color:' + ABC_COR[c] + '">Receita</th>').join('')
          + '<th>Total Clientes</th><th>Receita Total</th></tr>';
        tbody.innerHTML = dims.map(d => {
          const cells = classes.map(cls => {
            const r = src.find(x => x[dimKey]===d && x.classe===cls);
            const cor = ABC_COR[cls];
            return '<td style="color:' + cor + '">' + (r ? r.n : 0) + '</td>'
                 + '<td style="color:' + cor + ';font-weight:600">' + (r ? brl(r.receita) : '—') + '</td>';
          });
          const tot   = src.filter(x => x[dimKey]===d).reduce((s,r)=>s+r.n,0);
          const totR  = src.filter(x => x[dimKey]===d).reduce((s,r)=>s+r.receita,0);
          return '<tr><td style="color:#e2e8f0;text-align:left">' + d + '</td>' + cells.join('') + '<td>' + tot + '</td><td>' + brl(totR) + '</td></tr>';
        }).join('');
      }
    }

    document.getElementById('kpi-abc').addEventListener('click', () => {
      abcModalEl.style.display = 'flex';
      const active = document.querySelector('#modal-abc .flt.active');
      buildAbcModal(active ? active.dataset.v : 'abc');
    });
    document.getElementById('abc-close').addEventListener('click', () => { abcModalEl.style.display = 'none'; });
    abcModalEl.addEventListener('click', e => { if (e.target === abcModalEl) abcModalEl.style.display = 'none'; });
    document.querySelectorAll('#modal-abc .flt').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#modal-abc .flt').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        buildAbcModal(btn.dataset.v);
      });
    });
    </script>
    </body>
    </html>"""

    data_json = json.dumps(data, ensure_ascii=False)

    html = HTML.replace("DATA_PLACEHOLDER", data_json)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard gerado: {OUT} ({len(html.encode())//1024} KB)")
    print(f"  {len(df_mens)} meses | {len(df_top10)} produtos | {len(df_vend)} vendedores")


if __name__ == "__main__":
    main()
