# -*- coding: utf-8 -*-
"""
auditoria.py — Toronto LTDA
Valida empiricamente a qualidade do banco tratado (toronto_ltda.db).
Rodar SEMPRE ao final do ETL, antes de gerar dashboard/Excel.
Sai com codigo != 0 se algum check falhar.
"""
import sqlite3, sys
import pandas as pd

DB = "toronto_ltda.db"

def main():
    falhas = []

    c = sqlite3.connect(DB)
    cur = c.cursor()
    print("=== AUDITORIA DE QUALIDADE — toronto_ltda.db ===\n")

    # [1] Datas em ISO yyyy-mm-dd
    print("[1] Datas fora do padrao ISO:")
    date_checks = {
        "dim_clientes.data_cadastro": "data_cadastro",
        "fato_pedidos.data_pedido": "data_pedido",
        "fato_financeiro.data_vencimento": "data_vencimento",
        "fato_financeiro.data_emissao": "data_emissao",
    }
    for nome, col in date_checks.items():
        tbl = nome.split(".")[0]
        q = (f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NOT NULL "
             f"AND {col} NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'")
        n = cur.execute(q).fetchone()[0]
        print(f"    {nome:34s} -> {n}")
        if n: falhas.append(f"{nome}: {n} datas fora do padrao")

    # [2] Duplicatas por PK
    print("\n[2] Duplicatas por chave primaria:")
    for tbl, pk in [("dim_clientes","id_cliente"),("dim_produtos","id_produto"),
                    ("dim_vendedores","id_vendedor"),("fato_pedidos","id_item"),
                    ("fato_financeiro","id_titulo"),("fato_atividades","id_atividade"),
                    ("fato_funil","id_oportunidade")]:
        d = cur.execute(f"SELECT COUNT(*)-COUNT(DISTINCT {pk}) FROM {tbl}").fetchone()[0]
        print(f"    {tbl:18s} ({pk}) -> {d}")
        if d: falhas.append(f"{tbl}: {d} duplicatas")

    # [3] Lacunas inesperadas (data_pagamento e nulo de negocio: permitido)
    print("\n[3] Lacunas por coluna (data_pagamento e o unico nulo legitimo):")
    permitidos = {("fato_financeiro","data_pagamento")}
    for t in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        df = pd.read_sql(f"SELECT * FROM {t}", c)
        for col in df.columns:
            falt = df[col].isna().sum()
            if df[col].dtype == object:
                falt += (df[col].astype(str).str.strip() == "").sum()
            if falt:
                ok = (t, col) in permitidos
                tag = "(ok, negocio)" if ok else "*** INESPERADO ***"
                print(f"    {t}.{col:18s} -> {falt} {tag}")
                if not ok: falhas.append(f"{t}.{col}: {falt} lacunas inesperadas")

    # [4] Valor financeiro 100% numerico
    print("\n[4] fato_financeiro.valor — tipos:")
    tipos = cur.execute("SELECT typeof(valor), COUNT(*) FROM fato_financeiro GROUP BY typeof(valor)").fetchall()
    print(f"    {tipos}")
    if any(t[0] not in ("real","integer") for t in tipos):
        falhas.append("fato_financeiro.valor tem tipo nao-numerico")

    # [5] Coerencia status_titulo
    print("\n[5] Coerencia financeira:")
    dist = cur.execute("SELECT status_titulo, COUNT(*) FROM fato_financeiro GROUP BY status_titulo").fetchall()
    print(f"    distribuicao: {dict(dist)}")
    err = cur.execute("SELECT COUNT(*) FROM fato_financeiro WHERE data_pagamento IS NULL AND status_titulo='Pago'").fetchone()[0]
    print(f"    'Pago' sem data_pagamento -> {err} (deve ser 0)")
    if err: falhas.append(f"{err} titulos 'Pago' sem pagamento")
    if len(dist) < 2: falhas.append("status_titulo sem variacao (so 1 valor)")

    # [6] Campos derivados
    print("\n[6] Campos derivados presentes:")
    cols_ped = [r[1] for r in cur.execute("PRAGMA table_info(fato_pedidos)").fetchall()]
    cols_fin = [r[1] for r in cur.execute("PRAGMA table_info(fato_financeiro)").fetchall()]
    cols_est = [r[1] for r in cur.execute("PRAGMA table_info(fato_estoque)").fetchall()]
    for nome, ok in [("fato_pedidos.valor_liquido","valor_liquido" in cols_ped),
                     ("fato_financeiro.status_titulo","status_titulo" in cols_fin),
                     ("fato_financeiro.dias_atraso","dias_atraso" in cols_fin),
                     ("fato_estoque.saldo_acumulado","saldo_acumulado" in cols_est)]:
        print(f"    {nome:34s} -> {ok}")
        if not ok: falhas.append(f"{nome} ausente")

    c.close()

    print("\n" + "="*50)
    if falhas:
        print(f"AUDITORIA FALHOU — {len(falhas)} problema(s):")
        for f in falhas:
            print(f"   - {f}")
        sys.exit(1)
    print("AUDITORIA OK — todos os checks passaram.")


if __name__ == "__main__":
    main()
