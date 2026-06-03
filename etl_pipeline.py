# -*- coding: utf-8 -*-
"""
etl_pipeline.py — Toronto LTDA  (Dia 2: Limpeza & Transformação)

Lê os CSVs crus (raiz do projeto), limpa a sujeira proposital e grava:
  • dados_tratados/   — CSVs limpos, prontos para análise
  • toronto_ltda.db   — SQLite com schema dimensional

Regras de limpeza aplicadas
----------------------------
  Datas   : normaliza dd/mm/yyyy, yyyy-mm-dd, dd-mm-yy → yyyy-mm-dd
  CNPJ    : remove máscara → só dígitos; flag cnpj_valido (len == 14)
  Nomes   : strip() + title case (remove caixa alta/baixa inconsistente)
  Valores : '1.234,56' (BR) ou float → float
  Dupl.   : drop_duplicates por chave primária de cada tabela

Campos derivados criados
-------------------------
  fato_pedidos    : valor_bruto, valor_liquido
  fato_financeiro : status_titulo (Pago / Vencido / A Vencer), dias_atraso
  fato_estoque    : qtd_sinal, saldo_acumulado (running sum por produto)
  dim_clientes    : cnpj_limpo, cnpj_valido
"""

import os, re, random, sqlite3
from datetime import date, datetime

import numpy as np
import pandas as pd

# ── config ────────────────────────────────────────────────────────────────────

HOJE     = date(2026, 6, 2)
DIR_CRUS = "dados_crus"
DIR_OUT  = "dados_tratados"
DB_PATH  = "toronto_ltda.db"

# ── helpers de parse ──────────────────────────────────────────────────────────

def parse_data(valor) -> str | None:
    """Aceita dd/mm/yyyy, yyyy-mm-dd, dd-mm-yy → devolve 'yyyy-mm-dd' ou None."""
    if pd.isna(valor) or not str(valor).strip():
        return None
    s = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_valor(v) -> float:
    """Converte '1.234,56' (formato BR) ou float/int para float."""
    if pd.isna(v):
        return np.nan
    s = str(v).strip()
    # Formato brasileiro: decimal com vírgula, milhar com ponto OPCIONAL.
    # Cobre '1.234,56' (com milhar) e '930,74' (sem milhar).
    if re.match(r"^\d{1,3}(\.\d{3})*,\d{1,2}$", s):
        s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return np.nan


def parse_cnpj(cnpj) -> tuple[str | None, bool]:
    """Remove formatação, devolve (dígitos, é_válido)."""
    if pd.isna(cnpj):
        return None, False
    digits = re.sub(r"\D", "", str(cnpj))
    return (digits if digits else None), len(digits) == 14


def limpar_nome(nome) -> str | None:
    """strip() + colapsa espaços duplos + title case."""
    if pd.isna(nome):
        return None
    return " ".join(str(nome).strip().split()).title()


# ── transformações por tabela ─────────────────────────────────────────────────

def tratar_vendedores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates()
    df["nome"]         = df["nome"].apply(limpar_nome)
    df["data_admissao"] = df["data_admissao"].apply(parse_data)
    return df


def tratar_clientes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates(subset=["id_cliente"])
    parsed = df["cnpj"].apply(
        lambda x: pd.Series(parse_cnpj(x), index=["cnpj_limpo", "cnpj_valido"])
    )
    df        = pd.concat([df, parsed], axis=1)
    df["razao_social"]  = df["razao_social"].apply(limpar_nome)
    df["nome_fantasia"] = df["nome_fantasia"].apply(limpar_nome)
    df["data_cadastro"] = df["data_cadastro"].apply(parse_data)

    # ── imputação de lacunas (dados fictícios) ──────────────────────────────
    # nome_fantasia ausente → reconstruído da razão social ("<Fantasia> Comercio Ltda"),
    # garantindo coerência entre os dois campos.
    falta_fant = df["nome_fantasia"].isna()
    df.loc[falta_fant, "nome_fantasia"] = (
        df.loc[falta_fant, "razao_social"]
          .str.replace(r"\s+Comercio Ltda$", "", regex=True)
    )
    # cidade ausente → sorteia uma cidade já existente na MESMA UF (mantém coerência
    # geográfica cidade↔uf↔região). Semente fixa → reprodutível.
    rng = random.Random(42)
    cidades_por_uf = (
        df.loc[df["cidade"].notna()]
          .groupby("uf")["cidade"].agg(lambda s: sorted(set(s))).to_dict()
    )
    def _cidade(row):
        if pd.notna(row["cidade"]):
            return row["cidade"]
        opcoes = cidades_por_uf.get(row["uf"])
        return rng.choice(opcoes) if opcoes else row["cidade"]
    df["cidade"] = df.apply(_cidade, axis=1)
    return df


def tratar_produtos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates()
    df["nome"] = df["nome"].apply(limpar_nome)
    return df


def tratar_pedidos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates(subset=["id_item"])
    df["data_pedido"]   = df["data_pedido"].apply(parse_data)
    df["valor_bruto"]   = (df["quantidade"] * df["preco_unit"]).round(2)
    df["valor_liquido"] = (df["valor_bruto"] * (1 - df["desconto_pct"] / 100)).round(2)
    return df


def tratar_financeiro(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates(subset=["id_titulo"])
    for col in ["data_emissao", "data_vencimento", "data_pagamento"]:
        df[col] = df[col].apply(parse_data)
    df["valor"] = df["valor"].apply(parse_valor)

    def _status(row) -> str:
        # ATENCAO: valor ausente vira NaN (float), e bool(nan) == True.
        # Usar pd.notna em vez de truthiness, senao todo titulo vira "Pago".
        if pd.notna(row["data_pagamento"]):
            return "Pago"
        venc = row["data_vencimento"]
        if pd.notna(venc) and datetime.strptime(venc, "%Y-%m-%d").date() < HOJE:
            return "Vencido"
        return "A Vencer"

    df["status_titulo"] = df.apply(_status, axis=1)
    df["dias_atraso"] = df.apply(
        lambda r: max(
            0,
            (HOJE - datetime.strptime(r["data_vencimento"], "%Y-%m-%d").date()).days
        )
        if r["status_titulo"] == "Vencido" and pd.notna(r["data_vencimento"])
        else 0,
        axis=1,
    )
    return df


def tratar_estoque(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["data_mov"]  = df["data_mov"].apply(parse_data)
    df = df.sort_values(["id_produto", "data_mov"]).reset_index(drop=True)
    df["qtd_sinal"]       = df.apply(
        lambda r: r["quantidade"] if r["tipo_mov"] == "Entrada" else -r["quantidade"],
        axis=1,
    )
    df["saldo_acumulado"] = df.groupby("id_produto")["qtd_sinal"].cumsum()
    return df


def tratar_atividades(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates(subset=["id_atividade"])
    df["data_atividade"] = df["data_atividade"].apply(parse_data)
    return df


def tratar_funil(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().drop_duplicates(subset=["id_oportunidade"])
    df["data_abertura"] = df["data_abertura"].apply(parse_data)
    return df


# ── pipeline principal ────────────────────────────────────────────────────────

JOBS = [
    ("dim_vendedores.csv",  tratar_vendedores),
    ("dim_clientes.csv",    tratar_clientes),
    ("dim_produtos.csv",    tratar_produtos),
    ("fato_pedidos.csv",    tratar_pedidos),
    ("fato_financeiro.csv", tratar_financeiro),
    ("fato_estoque.csv",    tratar_estoque),
    ("fato_atividades.csv", tratar_atividades),
    ("fato_funil.csv",      tratar_funil),
]


def main():
    os.makedirs(DIR_OUT, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    print("Toronto LTDA — ETL Pipeline")
    print(f"{'Arquivo':<24} {'Cru':>8}  {'Tratado':>8}  {'Removidas':>10}")
    print("-" * 58)

    for arquivo, fn in JOBS:
        nome_tabela = arquivo.replace(".csv", "")
        df_raw = pd.read_csv(os.path.join(DIR_CRUS, arquivo))
        df_out = fn(df_raw)

        df_out.to_csv(os.path.join(DIR_OUT, arquivo), index=False, encoding="utf-8")
        df_out.to_sql(nome_tabela, conn, if_exists="replace", index=False)

        removidas = len(df_raw) - len(df_out)
        print(f"  {arquivo:<22} {len(df_raw):>8,}  {len(df_out):>8,}  {removidas:>10,}")

    conn.close()
    print("-" * 58)
    print(f"\nOK  CSVs limpos  ->  {DIR_OUT}/")
    print(f"OK  Banco SQLite ->  {DB_PATH}\n")


if __name__ == "__main__":
    main()
