# Toronto LTDA — Portfolio de Dados

> Pipeline completo de dados — geração, ETL, SQL analytics e dashboard interativo —
> sobre uma importadora fictícia de vinhos premium B2B.

**[▶ Ver dashboard ao vivo](https://gabrielamichelotto-byte.github.io/toronto-ltda)**

---

## Visão geral

| | |
|---|---|
| **Empresa** | Toronto LTDA — importadora de vinhos, espumantes e destilados (fictícia) |
| **Modelo** | B2B — restaurantes, bares, hotéis, mercados, distribuidores |
| **Período** | 26 meses de histórico |
| **Volume** | 400 clientes · 120 produtos · 8 vendedores · ~27 mil itens de pedido |
| **Stack** | Python · Pandas · SQLite · Chart.js · HTML/CSS/JS |

---

## Dashboard interativo

Arquivo único (`index.html`, ~200 KB), tema escuro, sem servidor, sem internet —
abre direto no navegador.

**10 cards clicáveis, 11 módulos analíticos, cada um com modal de drill-down:**

| # | Módulo | O que mostra |
|---|---|---|
| 1 | **Faturamento Total** | Evolução mensal · por categoria · por região |
| 2 | **Ticket Médio / Pedido** | Tendência mensal por status (Faturado / Cancelado / Devolvido) |
| 3 | **Clientes Ativos** | Mix por segmento e região · evolução mensal · top inativos para recuperação |
| 4 | **Taxa de Inadimplência** | Evolução 26 meses · semáforo por segmento |
| 5 | **Margem Bruta** | Composição receita × custo por categoria e por vendedor |
| 6 | **Desconto Médio** | Frequência · eficiência (produtivo/neutro/improdutivo) · scatter desc × ticket |
| 7 | **Metas de Vendas** | Atingimento mensal/bimestral/anual · consistência · projeção 2026 |
| 8 | **Giro do Estoque** | Cobertura em dias com semáforo · índice de rotatividade · movimento mensal |
| 9 | **Pulso da Carteira** | Matriz de quadrantes (Campeões / Em Risco / Dormentes) · histograma de recência · ranking de ticket |
| 10 | **Inadimplência × Conversão** | Clientes que inadimpliram: voltaram a comprar? · por segmento · evolução dual-axis |
| 11 | **Recuperação de Carteira — Curva ABC** | Pareto de inativos · A/B/C por segmento, região e vendedor |

---

## Estrutura do projeto

```
toronto-ltda/
├── gerar_dados.py          # Geração dos dados crus (sujeira proposital — simula exportação de ERP)
├── etl_pipeline.py         # ETL: limpeza, normalização, campos derivados → SQLite
├── auditoria.py            # Validação empírica do banco (falha com exit-code se regredir)
├── auditoria_completa.py   # Auditoria end-to-end: 18 checks DB × HTML
├── gerar_dashboard.py      # Geração do dashboard HTML (Chart.js inline, sem CDN)
├── gerar_excel.py          # Relatório Excel com 8 abas analíticas
├── queries.sql             # 12 queries de Business Intelligence
├── requirements.txt        # pandas · numpy · openpyxl
├── chartjs.min.js          # Chart.js v4.4.4 (offline)
├── index.html              # Dashboard — artefato final para o GitHub Pages
├── dashboard.html          # Idem (cópia local)
└── Toronto_LTDA_Relatorio.xlsx  # Relatório Excel gerado
```

---

## Como reproduzir

```bash
pip install -r requirements.txt

python gerar_dados.py       # Gera CSVs crus em dados_crus/
python etl_pipeline.py      # Limpa, deriva campos, grava toronto_ltda.db
python auditoria.py         # Valida qualidade do banco
python gerar_dashboard.py   # Gera dashboard.html / index.html
python gerar_excel.py       # Gera Toronto_LTDA_Relatorio.xlsx

# Abrir o dashboard
start index.html            # Windows
open index.html             # macOS
```

---

## Camadas técnicas

### 1 · Geração de dados (`gerar_dados.py`)

Simula exportação de ERP com sujeira controlada e reproduzível (semente fixa):

- **Datas** em 3 formatos misturados — `dd/mm/yyyy`, `yyyy-mm-dd`, `dd-mm-yy`
- **CNPJs** com máscara inconsistente ou comprimento errado
- **Nomes** em caixa alta, baixa, com espaços duplos
- **Valores** formato BR (`1.234,56`) misturados com floats
- **~2%** de linhas duplicadas · **~4%** de nulos em campos não-críticos
- Sazonalidade real: peso nov/dez de 1,4× / 1,6× nos pedidos
- Perfil de desconto por segmento + agressividade por vendedor (Dirichlet)

### 2 · ETL (`etl_pipeline.py`)

| Problema | Solução |
|---|---|
| 3 formatos de data | `parse_data()` — tenta cada formato, normaliza para ISO |
| CNPJ inconsistente | Remove máscara, valida comprimento (14 dígitos) |
| Nomes sujos | `strip()` + colapso de espaços + `title()` |
| Valores formato BR | Regex `^\d{1,3}(\.\d{3})*,\d{1,2}$` → float |
| Linhas duplicadas | `drop_duplicates()` por chave primária |
| Nulos em cidade | Imputação por UF (coerência geográfica mantida) |

Campos derivados:

| Tabela | Campo | Cálculo |
|---|---|---|
| `fato_pedidos` | `valor_liquido` | `qtd × preco × (1 − desconto/100)` |
| `fato_financeiro` | `status_titulo` | Pago / Vencido / A Vencer |
| `fato_financeiro` | `dias_atraso` | `HOJE − vencimento` (se Vencido) |
| `fato_estoque` | `saldo_acumulado` | Running sum entradas − saídas por produto |

### 3 · Dashboard (`gerar_dashboard.py`)

Gerador Python que serializa todas as queries como JSON e injeta num template
HTML com Chart.js. Nenhuma dependência em runtime — um arquivo funciona em
qualquer navegador, offline.

Padrões de UI estabelecidos:
- Modal drill-down em todos os KPIs clicáveis
- Semáforo de inadimplência (verde < 10% · laranja 10–15% · vermelho ≥ 15%)
- Delta mês a mês nos cards (`▲ +N` verde / `▼ −N` vermelho)
- Pareto com eixo Y secundário (curva ABC)
- Scatter de quadrantes com corte na mediana (Campeões / Em Risco / Dormentes)

### 4 · Analytics SQL (`queries.sql`)

12 queries de negócio para SQLite / DBeaver / BI:
faturamento mensal · top produtos · vendedores vs. meta · inadimplência por segmento ·
lifetime value · margem por produto · conversão no funil · aging de títulos ·
novos vs. recorrentes · giro de estoque · curva ABC · positivação por vendedor.

### 5 · Relatório Excel (`gerar_excel.py`)

8 abas com tema escuro, KPIs e formatação condicional:
Carteira ABC · Giro Financeiro · Margem por Produto · Cross-sell ·
Taxa de Conversão · Pedidos não Faturados · Top Produtos · Produtos em Queda.

---

## Schema dimensional

```
dim_vendedores ──┐
dim_clientes   ──┼──▶ fato_pedidos
dim_produtos   ──┘         │
                           ├──▶ fato_financeiro
                           ├──▶ fato_estoque
                           ├──▶ fato_atividades
                           └──▶ fato_funil
```

---

## Tecnologias

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?logo=pandas&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?logo=chart.js&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)

---

*Dados 100% fictícios. Semente aleatória fixa — resultados reproduzíveis.*
