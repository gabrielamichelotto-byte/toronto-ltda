# -*- coding: utf-8 -*-
"""
gerar_dados.py  —  Toronto LTDA (fictícia)
Importadora e distribuidora de vinhos, espumantes e destilados premium (B2B).

O QUE ESTE SCRIPT FAZ
---------------------
Gera os DADOS CRUS da operação, no formato de uma "exportação de ERP":
tabelas separadas, com sujeira proposital (datas em formatos diferentes,
CNPJ torto, nomes inconsistentes, nulos e duplicatas).
Esses arquivos são a MATÉRIA-PRIMA do ETL (Dia 2). Eles NÃO devem ser
tratados aqui — a limpeza é um passo separado, de propósito.

COMO LER ESTE SCRIPT (você está aprendendo, então leia de cima pra baixo):
  1) CONFIG  -> os "botões" do gerador (quantidades, período, semente)
  2) LISTAS  -> vocabulário usado pra montar nomes realistas
  3) HELPERS -> funções pequenas que "sujam" os dados de forma controlada
  4) GERAÇÃO -> cada dimensão e cada fato, um de cada vez
  5) SAÍDA   -> grava os CSVs numa pasta

Regra do projeto: dados crus nunca são alterados depois. O tratamento
(Dia 2) sempre roda sobre CÓPIA.
"""

import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

# =====================================================================
# 1) CONFIG  — mexa só aqui pra mudar a escala da empresa
# =====================================================================
SEMENTE        = 42        # fixa a aleatoriedade -> resultado reproduzível
N_VENDEDORES   = 8
N_CLIENTES     = 400
N_PRODUTOS     = 120
MESES          = 24        # histórico de pedidos (em meses, até hoje)
PASTA_SAIDA    = "dados_crus"

# "sujeira moderada": proporções pequenas, suficientes pra ter o que tratar
PCT_NULOS      = 0.04      # ~4% de células nulas em campos não-críticos
PCT_DUPLICATAS = 0.02      # ~2% de linhas duplicadas
PCT_INADIMPL   = 0.12      # ~12% dos títulos vencidos seguem sem pagamento

random.seed(SEMENTE)
np.random.seed(SEMENTE)

HOJE = date(2026, 6, 2)
INICIO = date(HOJE.year, HOJE.month, 1) - timedelta(days=MESES * 31)
INICIO = date(INICIO.year, INICIO.month, 1)

# =====================================================================
# 2) LISTAS  — vocabulário pra nomes realistas
# =====================================================================
NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela",
         "Henrique", "Isabela", "João", "Larissa", "Marcos", "Natália",
         "Otávio", "Paula", "Rafael", "Sofia", "Thiago", "Vanessa", "William"]
SOBRENOMES = ["Almeida", "Barbosa", "Costa", "Dias", "Ferreira", "Gomes",
              "Lima", "Martins", "Nunes", "Oliveira", "Pereira", "Ribeiro",
              "Santos", "Souza", "Teixeira", "Vieira"]

# (cidade, UF, região) — praças de atuação
PRACAS = [
    ("São Paulo", "SP", "Sudeste"), ("Campinas", "SP", "Sudeste"),
    ("Rio de Janeiro", "RJ", "Sudeste"), ("Belo Horizonte", "MG", "Sudeste"),
    ("Curitiba", "PR", "Sul"), ("Porto Alegre", "RS", "Sul"),
    ("Florianópolis", "SC", "Sul"), ("Salvador", "BA", "Nordeste"),
    ("Recife", "PE", "Nordeste"), ("Fortaleza", "CE", "Nordeste"),
    ("Brasília", "DF", "Centro-Oeste"), ("Goiânia", "GO", "Centro-Oeste"),
    ("Cuiabá", "MT", "Centro-Oeste"),
]
SEGMENTOS = ["Restaurante", "Bar", "Adega", "Hotel", "Mercado", "Distribuidor"]

# produtos: (categoria, [varietais/tipos], [países de origem])
CATALOGO = {
    "Vinho Tinto":   (["Malbec", "Cabernet Sauvignon", "Merlot", "Carménère",
                       "Tannat", "Pinot Noir", "Syrah"],
                      ["Argentina", "Chile", "Portugal", "Itália", "Uruguai", "Brasil"]),
    "Vinho Branco":  (["Chardonnay", "Sauvignon Blanc", "Riesling", "Pinot Grigio"],
                      ["Chile", "França", "Itália", "Portugal"]),
    "Rosé":          (["Rosé Provence", "Rosé Malbec"],
                      ["França", "Argentina"]),
    "Espumante":     (["Brut", "Prosecco", "Moscatel", "Champagne"],
                      ["Brasil", "Itália", "França", "Espanha"]),
    "Destilado":     (["Whisky 12 anos", "Gin London Dry", "Vodka Premium",
                       "Rum Reserva", "Tequila Reposado", "Cognac VS"],
                      ["Escócia", "Inglaterra", "França", "México"]),
}
LINHAS = ["Reserva", "Gran Reserva", "Clássico", "Premium", "Selección", "Edição Limitada"]
FORNECEDORES = ["Bodega Andina", "Vinícola Douro", "Casa Toscana", "Maison Bordeaux",
                "Cava Ibérica", "Highland Spirits", "Destilaria do Norte"]

# =====================================================================
# 3) HELPERS  — funções que SUJAM os dados de forma controlada
# =====================================================================
def talvez_nulo(valor, prob=PCT_NULOS):
    """Devolve None com certa probabilidade (simula campo vazio no ERP)."""
    return None if random.random() < prob else valor

def cnpj_sujo():
    """CNPJ em formatos misturados: com máscara, sem máscara e alguns inválidos."""
    base = "".join(random.choice("0123456789") for _ in range(14))
    estilo = random.random()
    if estilo < 0.45:                                   # mascarado correto
        return f"{base[:2]}.{base[2:5]}.{base[5:8]}/{base[8:12]}-{base[12:]}"
    elif estilo < 0.85:                                 # só dígitos
        return base
    else:                                               # comprimento errado
        return base[:random.choice([11, 13, 15])]

def nome_sujo(nome):
    """Aplica caixa e espaços inconsistentes (UPPER, lower, espaço duplo, etc.)."""
    estilo = random.random()
    if estilo < 0.25:   return nome.upper()
    if estilo < 0.45:   return nome.lower()
    if estilo < 0.60:   return f"  {nome} "          # espaços nas pontas
    if estilo < 0.72:   return nome.replace(" ", "  ")  # espaço duplo
    return nome

def data_suja(d):
    """Mesma data em formatos diferentes (o ETL terá que normalizar)."""
    estilo = random.random()
    if estilo < 0.55:   return d.strftime("%d/%m/%Y")
    if estilo < 0.85:   return d.strftime("%Y-%m-%d")
    return d.strftime("%d-%m-%y")

def valor_br(v):
    """Parte dos valores no padrão brasileiro string '1.234,56' (mistura proposital)."""
    if random.random() < 0.4:
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return round(v, 2)

def injeta_duplicatas(df, prob=PCT_DUPLICATAS):
    """Reinsere algumas linhas idênticas (registros duplicados no ERP)."""
    n = max(1, int(len(df) * prob))
    extras = df.sample(n=n, replace=True, random_state=SEMENTE)
    return pd.concat([df, extras], ignore_index=True)

# =====================================================================
# 4) GERAÇÃO
# =====================================================================
# ---- dim_vendedores -------------------------------------------------
regioes = ["Sudeste", "Sul", "Nordeste", "Centro-Oeste"]
vendedores = []
for i in range(1, N_VENDEDORES + 1):
    adm = HOJE - timedelta(days=random.randint(120, 2200))
    vendedores.append({
        "id_vendedor": i,
        "nome": f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}",
        "equipe": random.choice(["Equipe A", "Equipe B"]),
        "regiao": regioes[(i - 1) % len(regioes)],
        "data_admissao": adm.strftime("%d/%m/%Y"),
        "meta_mensal": int(round(random.uniform(130_000, 340_000) / 5_000) * 5_000),
    })
df_vend = pd.DataFrame(vendedores)

# ---- dim_clientes ---------------------------------------------------
# Pesos Dirichlet (alpha=0.6) criam carteiras desiguais — uns vendedores
# ficam com muito mais clientes, gerando dispersão real no faturamento.
_vend_weights = np.random.dirichlet(np.ones(N_VENDEDORES) * 1.8)

# vendedores com mais clientes (rank alto no Dirichlet) são mais agressivos em desconto
_sorted_by_weight = sorted(range(N_VENDEDORES), key=lambda i: _vend_weights[i], reverse=True)
_vend_agressividade = {}
for _rank, _idx in enumerate(_sorted_by_weight):
    _vid = _idx + 1
    if _rank < 2:
        _vend_agressividade[_vid] = 2   # top 2: desconto agressivo
    elif _rank >= N_VENDEDORES - 2:
        _vend_agressividade[_vid] = 0   # bottom 2: desconto conservador
    else:
        _vend_agressividade[_vid] = 1   # normal

SEG_TAXA_ATIVO = {
    "Restaurante": 0.92, "Bar": 0.88, "Adega": 0.85,
    "Hotel": 0.80, "Mercado": 0.78, "Distribuidor": 0.70,
}
SEG_DESC_PERFIL = {
    "Adega":        [0, 0, 0, 0,  5, 10],
    "Hotel":        [0, 0, 0, 5,  5, 10],
    "Restaurante":  [0, 0, 0, 5, 10, 15],
    "Bar":          [0, 0, 0, 5, 10, 15],
    "Mercado":      [0, 0, 5, 10, 10, 15],
    "Distribuidor": [0, 0, 5, 10, 15, 15],
}

clientes = []
for i in range(1, N_CLIENTES + 1):
    cidade, uf, regiao = random.choice(PRACAS)
    seg = random.choice(SEGMENTOS)
    fantasia = f"{seg} {random.choice(SOBRENOMES)}"
    cad = INICIO + timedelta(days=random.randint(0, MESES * 30))
    if cad > HOJE:
        cad = HOJE - timedelta(days=random.randint(0, 60))
    clientes.append({
        "id_cliente": i,
        "cnpj": cnpj_sujo(),
        "razao_social": nome_sujo(f"{fantasia} Comercio LTDA"),
        "nome_fantasia": talvez_nulo(fantasia),
        "segmento": seg,
        "cidade": talvez_nulo(cidade),
        "uf": uf,
        "regiao": regiao,
        "data_cadastro": data_suja(cad),
        "id_vendedor": int(np.random.choice(range(1, N_VENDEDORES + 1), p=_vend_weights)),
        "status": random.choices(["Ativo", "Inativo"], weights=[SEG_TAXA_ATIVO.get(seg, 0.85), 1 - SEG_TAXA_ATIVO.get(seg, 0.85)])[0],
    })
df_cli = pd.DataFrame(clientes)

# ---- dim_produtos ---------------------------------------------------
produtos = []
pid = 1
while pid <= N_PRODUTOS:
    categoria = random.choice(list(CATALOGO.keys()))
    tipos, paises = CATALOGO[categoria]
    tipo = random.choice(tipos)
    pais = random.choice(paises)
    custo = round(random.uniform(18, 320), 2)
    markup = random.uniform(1.45, 2.30)            # margem embutida
    produtos.append({
        "id_produto": pid,
        "sku": f"TOR-{categoria[:3].upper()}-{pid:04d}",
        "nome": f"{tipo} {random.choice(LINHAS)} 750ml",
        "categoria": categoria,
        "pais_origem": pais,
        "fornecedor": random.choice(FORNECEDORES),
        "custo_unit": custo,
        "preco_tabela": round(custo * markup, 2),
    })
    pid += 1
df_prod = pd.DataFrame(produtos)

# ---- fato_pedidos (nível item) -------------------------------------
# Sazonalidade: nov/dez vendem mais (festas). Nem todo cliente compra todo mês.
peso_mes = {1:0.8, 2:0.7, 3:0.9, 4:0.9, 5:1.0, 6:1.0,
            7:1.0, 8:1.0, 9:1.05, 10:1.1, 11:1.4, 12:1.6}
pedidos = []
id_pedido = 1000
id_item = 1
data_mes = INICIO
while data_mes <= HOJE:
    fator = peso_mes[data_mes.month]
    ativos = df_cli[df_cli["status"] == "Ativo"].sample(
        frac=min(0.65 * fator, 0.95), random_state=id_pedido)
    for _, cli in ativos.iterrows():
        _base = SEG_DESC_PERFIL.get(cli["segmento"], [0, 0, 0, 5, 10, 15])
        _agr  = _vend_agressividade.get(int(cli["id_vendedor"]), 1)
        if _agr == 2:
            perfil_desc = [v for v in _base if v > 0] + [10]   # mais agressivo
        elif _agr == 0:
            perfil_desc = [0, 0, 0] + _base                    # mais conservador
        else:
            perfil_desc = _base
        n_pedidos_mes = np.random.poisson(1.2 * fator) or 1
        for _ in range(n_pedidos_mes):
            id_pedido += 1
            dia = min(28, random.randint(1, 28))
            d = date(data_mes.year, data_mes.month, dia)
            status_ped = random.choices(
                ["Faturado", "Cancelado", "Devolvido"], weights=[0.9, 0.06, 0.04])[0]
            for _ in range(random.randint(1, 5)):       # itens do pedido
                prod = df_prod.sample(1, random_state=id_item).iloc[0]
                qtd = random.choice([6, 12, 12, 24, 24, 48])
                desc = random.choice(perfil_desc)
                pedidos.append({
                    "id_pedido": id_pedido,
                    "id_item": id_item,
                    "data_pedido": data_suja(d),
                    "id_cliente": int(cli["id_cliente"]),
                    "id_vendedor": int(cli["id_vendedor"]),
                    "id_produto": int(prod["id_produto"]),
                    "quantidade": qtd,
                    "preco_unit": float(prod["preco_tabela"]),
                    "desconto_pct": desc,
                    # valor líquido NÃO é calculado aqui de propósito:
                    # é exercício do ETL (qtd * preco * (1 - desc/100)).
                    "status_pedido": status_ped,
                })
                id_item += 1
    # avança um mês
    if data_mes.month == 12:
        data_mes = date(data_mes.year + 1, 1, 1)
    else:
        data_mes = date(data_mes.year, data_mes.month + 1, 1)
df_ped = pd.DataFrame(pedidos)

# ---- fato_financeiro (títulos a receber) ---------------------------
# Um título por pedido faturado. Vencimento ~30 dias. Parte fica inadimplente.
titulos = []
id_titulo = 5000
faturados = df_ped[df_ped["status_pedido"] == "Faturado"].drop_duplicates("id_pedido")
for _, p in faturados.iterrows():
    id_titulo += 1
    emissao = HOJE - timedelta(days=random.randint(5, MESES * 30))
    venc = emissao + timedelta(days=random.choice([28, 30, 45]))
    valor = round(random.uniform(800, 9000), 2)
    if venc < HOJE and random.random() < PCT_INADIMPL:
        pagamento = None                                  # vencido e não pago
    elif venc < HOJE:
        pagamento = venc + timedelta(days=random.randint(-3, 12))
    else:
        pagamento = None if random.random() < 0.5 else venc - timedelta(days=random.randint(0, 5))
    titulos.append({
        "id_titulo": id_titulo,
        "id_pedido": int(p["id_pedido"]),
        "id_cliente": int(p["id_cliente"]),
        "data_emissao": data_suja(emissao),
        "data_vencimento": data_suja(venc),
        "data_pagamento": data_suja(pagamento) if pagamento else None,
        "valor": valor_br(valor),                         # mistura número e string BR
        # status e dias de atraso ficam pro ETL calcular.
    })
df_tit = pd.DataFrame(titulos)

# ---- fato_estoque (movimentação) -----------------------------------
# Modelo realista: entrada mensal de reposição (lote grande) + saída menor de consumo.
# ~85% dos produtos ficam com saldo positivo; ~5–10% chegam próximos de zero (falta real).
estoque = []
for _, prod in df_prod.iterrows():
    d = INICIO
    while d <= HOJE:
        # entrada de reposição — ocorre em ~50% dos meses, lote moderado
        if random.random() < 0.50:
            estoque.append({
                "data_mov": data_suja(date(d.year, d.month, random.randint(1, 10))),
                "id_produto": int(prod["id_produto"]),
                "tipo_mov": "Entrada",
                "quantidade": random.choice([72, 96, 120, 144, 168]),
            })
        # saída de consumo — ocorre em ~55% dos meses, consumo próximo da entrada
        if random.random() < 0.55:
            estoque.append({
                "data_mov": data_suja(date(d.year, d.month, random.randint(10, 28))),
                "id_produto": int(prod["id_produto"]),
                "tipo_mov": "Saida",
                "quantidade": random.choice([48, 60, 72, 84]),
                # saldo é derivado no ETL (entradas - saídas acumuladas).
            })
        d = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
df_est = pd.DataFrame(estoque)

# ---- fato_atividades (visitas / positivação) -----------------------
atividades = []
id_ativ = 9000
for _ in range(int(N_CLIENTES * 4)):
    id_ativ += 1
    cli = df_cli.sample(1).iloc[0]
    d = INICIO + timedelta(days=random.randint(0, MESES * 30))
    if d > HOJE:
        d = HOJE
    atividades.append({
        "id_atividade": id_ativ,
        "data_atividade": data_suja(d),
        "id_vendedor": int(cli["id_vendedor"]),
        "id_cliente": int(cli["id_cliente"]),
        "tipo": random.choice(["Visita", "Ligação", "Positivação"]),
        "resultado": random.choices(
            ["Pedido", "Sem pedido", "Reagendado"], weights=[0.45, 0.4, 0.15])[0],
    })
df_ativ = pd.DataFrame(atividades)

# ---- fato_funil (oportunidades) ------------------------------------
funil = []
id_op = 7000
for _ in range(int(N_CLIENTES * 1.5)):
    id_op += 1
    cli = df_cli.sample(1).iloc[0]
    abertura = INICIO + timedelta(days=random.randint(0, MESES * 30))
    if abertura > HOJE:
        abertura = HOJE
    etapa = random.choices(
        ["Lead", "Qualificado", "Proposta", "Negociação", "Ganho", "Perdido"],
        weights=[0.18, 0.18, 0.18, 0.14, 0.20, 0.12])[0]
    funil.append({
        "id_oportunidade": id_op,
        "id_cliente": int(cli["id_cliente"]),
        "id_vendedor": int(cli["id_vendedor"]),
        "data_abertura": data_suja(abertura),
        "etapa": etapa,
        "valor_estimado": round(random.uniform(2000, 40000), 2),
    })
df_fun = pd.DataFrame(funil)

# =====================================================================
#   Injeta duplicatas em algumas tabelas (mais sujeira pro ETL)
# =====================================================================
df_cli = injeta_duplicatas(df_cli)
df_ped = injeta_duplicatas(df_ped)

# =====================================================================
# 5) SAÍDA  — grava os CSVs
# =====================================================================
os.makedirs(PASTA_SAIDA, exist_ok=True)
arquivos = {
    "dim_vendedores.csv":  df_vend,
    "dim_clientes.csv":    df_cli,
    "dim_produtos.csv":    df_prod,
    "fato_pedidos.csv":    df_ped,
    "fato_financeiro.csv": df_tit,
    "fato_estoque.csv":    df_est,
    "fato_atividades.csv": df_ativ,
    "fato_funil.csv":      df_fun,
}
for nome, df in arquivos.items():
    df.to_csv(os.path.join(PASTA_SAIDA, nome), index=False, encoding="utf-8")

print("Toronto LTDA — dados crus gerados em:", PASTA_SAIDA)
for nome, df in arquivos.items():
    print(f"  {nome:22s} {len(df):>7,} linhas  x {df.shape[1]} colunas")
