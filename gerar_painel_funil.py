# -*- coding: utf-8 -*-
"""
gerar_painel_funil.py — Toronto LTDA (v2 — light theme + sidebar + abas)
"""
import json, sqlite3
import pandas as pd

DB  = "toronto_ltda.db"
OUT = "painel_funil.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toronto LTDA — Funil de Vendas</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="chartjs.min.js"></script>
<style>
:root{--accent:#6b7fd4}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;font-family:'Inter',system-ui,-apple-system,sans-serif;background:#f5f0e8;color:#0f172a}
.app{display:flex;height:100vh;width:100%;overflow:hidden}

/* ── Sidebar ── */
.sidebar{width:210px;flex-shrink:0;background:#fff;display:flex;flex-direction:column;overflow-y:auto;border-right:1px solid #e8e4dc}
.sb-logo-top{padding:22px 14px 18px;text-align:center;border-bottom:1px solid #e8e4dc;flex-shrink:0}
.sb-logo-big{height:96px;width:auto;border-radius:10px;background:#f5f0e8;padding:6px 16px;display:block;margin:0 auto}
.sb-sec{font-size:.57rem;font-weight:700;letter-spacing:1.6px;color:#a09880;padding:14px 14px 5px;text-transform:uppercase;flex-shrink:0}
.sb-nav{padding:0 8px 6px;flex-shrink:0}
.sb-nav a{display:flex;align-items:center;gap:9px;padding:8px 10px;font-size:.74rem;color:#64748b;text-decoration:none;border-left:3px solid transparent;border-radius:0 6px 6px 0;transition:all .15s;margin-bottom:2px}
.sb-nav a:hover{background:#f5f0e8;color:#0f172a}
.sb-nav a.active{background:#ede8df;border-left-color:var(--accent);color:#3d2e1e;font-weight:600}
.sb-footer{padding:10px 14px;border-top:1px solid #e8e4dc;font-size:.58rem;color:#b0a890;flex-shrink:0;line-height:1.6;margin-top:auto}

/* ── Main ── */
.main{flex:1;min-width:0;display:flex;flex-direction:column;overflow:hidden}
.topbar{background:#fff;border-bottom:1px solid #e8e4dc;padding:14px 24px;display:flex;align-items:center;gap:16px;flex-shrink:0}
.page-title{font-size:1rem;font-weight:700;color:#0f172a;display:flex;align-items:center;gap:10px}
.page-title-badge{font-size:.65rem;background:#ede8df;color:#64748b;padding:3px 10px;border-radius:10px;font-weight:500}
.content{flex:1;overflow-y:auto;padding:16px 20px;background:#f5f0e8}

/* ── KPIs ── */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}
.kpi{background:#fff;border:1px solid #e8e4dc;border-radius:10px;padding:16px;position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--ac,var(--accent))}
.kpi-icon{font-size:1.1rem;margin-bottom:7px}
.kpi-label{font-size:.6rem;color:#a09880;text-transform:uppercase;letter-spacing:1px}
.kpi-value{font-size:1.4rem;font-weight:700;margin:4px 0 2px;color:#0f172a}
.kpi-sub{font-size:.65rem;color:#8a7560}
.kpi-badge{display:inline-block;font-size:.62rem;padding:2px 9px;border-radius:10px;margin-top:6px;font-weight:700}

/* ── Main-tabs ── */
.main-tabs{display:flex;border-bottom:2px solid #e8e4dc;background:#fff;border-radius:10px 10px 0 0;padding:0 6px}
.main-tab{border:none;border-bottom:2px solid transparent;padding:12px 20px;font-size:.8rem;margin-bottom:-2px;cursor:pointer;background:transparent;color:#8a7560;font-family:inherit;transition:all .15s}
.main-tab:hover{color:#0f172a}
.main-tab.active{color:#2c1e0f;font-weight:700;border-bottom-color:var(--accent)}

/* ── Section ── */
.section{background:#fff;border:1px solid #e8e4dc;border-radius:0 0 10px 10px;padding:20px}
.section-hd{font-size:.64rem;text-transform:uppercase;letter-spacing:1.2px;color:#a09880;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.section-hd em{color:var(--accent);font-style:normal;font-size:.85rem}

/* ── Sub-tabs ── */
.tabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.tab{border:1px solid #e8e4dc;background:transparent;color:#8a7560;padding:5px 16px;border-radius:20px;font-size:.71rem;cursor:pointer;transition:all .15s;font-family:inherit}
.tab.active{background:#2c1e0f;border-color:#2c1e0f;color:#fff;font-weight:600}

.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}
.ch{position:relative}

table{width:100%;border-collapse:collapse;font-size:.72rem;margin-top:14px}
th{color:#a09880;text-transform:uppercase;letter-spacing:.8px;padding:7px 10px;border-bottom:1px solid #e8e4dc;text-align:right;font-size:.64rem}
th:first-child{text-align:left}
td{padding:7px 10px;border-bottom:1px solid #f5f0e8;text-align:right}
td:first-child{text-align:left}
tr:last-child td{border-bottom:none}
.td-name{color:#0f172a;font-weight:600}

.insight{margin-top:16px;padding:12px 15px;background:#faf8f5;border:1px solid #e8e4dc;border-left:3px solid var(--accent);border-radius:8px;font-size:.71rem;line-height:1.75;color:#64748b}
.insight strong{color:#0f172a}

.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:middle}

@media(max-width:960px){.sidebar{display:none}.kpis{grid-template-columns:1fr 1fr}}
@media(max-width:480px){.kpis{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="app">

<aside class="sidebar">
  <div class="sb-logo-top">
    <img src="toronto_logo.png" alt="Toronto LTDA" class="sb-logo-big">
  </div>
  <div class="sb-sec">P&aacute;ginas</div>
  <nav class="sb-nav">
    <a href="painel_funil.html" class="active">&#128202; Funil de Vendas</a>
    <a href="painel_conversao.html">&#128222; Convers&atilde;o</a>
    <a href="painel_cancelamentos.html">&#9888; Cancelamentos</a>
    <a href="painel_mix.html">&#127863; Mix de Produtos</a>
  </nav>
  <div class="sb-footer">Toronto LTDA &mdash; Dados fict&iacute;cios<br>Portf&oacute;lio de An&aacute;lise de Dados</div>
</aside>

<div class="main">
  <div class="topbar">
    <div class="page-title">&#128202; Funil de Vendas <span class="page-title-badge">An&aacute;lise de Pipeline</span></div>
  </div>
  <div class="content">

    <div class="kpis">
      <div class="kpi" style="--ac:var(--accent)">
        <div class="kpi-icon">&#128202;</div>
        <div class="kpi-label">Pipeline Ativo</div>
        <div class="kpi-value" id="kv-pipe"></div>
        <div class="kpi-sub" id="ks-pipe"></div>
      </div>
      <div class="kpi" style="--ac:#16a34a">
        <div class="kpi-icon">&#9989;</div>
        <div class="kpi-label">Contratos Ganhos</div>
        <div class="kpi-value" id="kv-ganho"></div>
        <div class="kpi-sub" id="ks-ganho"></div>
      </div>
      <div class="kpi" style="--ac:#d97706">
        <div class="kpi-icon">&#127919;</div>
        <div class="kpi-label">Taxa de Convers&atilde;o</div>
        <div class="kpi-value" id="kv-taxa"></div>
        <div class="kpi-sub">ganho / (ganho + perdido)</div>
        <span class="kpi-badge" id="kb-taxa"></span>
      </div>
      <div class="kpi" style="--ac:#f0853a">
        <div class="kpi-icon">&#127991;</div>
        <div class="kpi-label">Ticket M&eacute;dio</div>
        <div class="kpi-value" id="kv-ticket"></div>
        <div class="kpi-sub">valor m&eacute;dio por oportunidade</div>
      </div>
    </div>

    <div class="main-tabs">
      <button class="main-tab active" data-section="funil">&#128202; Funil por Etapa</button>
      <button class="main-tab" data-section="vend">&#128100; Por Vendedor</button>
      <button class="main-tab" data-section="tend">&#128197; Tend&ecirc;ncia Mensal</button>
    </div>

    <!-- Seção 1: Funil por Etapa -->
    <div class="section" id="sec-funil">
      <div class="section-hd"><em>&#9679;</em> Funil por Etapa &mdash; Pipeline Ativo</div>
      <div class="tabs" id="tabs-funil">
        <button class="tab active" data-v="qtd">Quantidade</button>
        <button class="tab" data-v="val">Valor (R$)</button>
      </div>
      <div class="g2">
        <div><div class="ch" style="height:210px"><canvas id="c-funil"></canvas></div></div>
        <div><div class="ch" style="height:210px"><canvas id="c-outcome"></canvas></div></div>
      </div>
      <table>
        <thead>
          <tr><th>Etapa</th><th>Oport.</th><th>Valor Total</th><th>Ticket M&eacute;dio</th><th>% do Pipeline</th></tr>
        </thead>
        <tbody id="funil-tbody"></tbody>
      </table>
      <div class="insight" id="insight-funil"></div>
    </div>

    <!-- Seção 2: Por Vendedor -->
    <div class="section" id="sec-vend">
      <div class="section-hd"><em>&#9679;</em> Performance por Vendedor</div>
      <div class="ch" style="height:260px"><canvas id="c-vend"></canvas></div>
      <table>
        <thead>
          <tr><th>Vendedor</th><th>Em Andamento</th><th>Ganhos</th><th>Perdidos</th><th>Taxa Conv.</th><th>Valor Ganho</th></tr>
        </thead>
        <tbody id="vend-tbody"></tbody>
      </table>
      <div class="insight" id="insight-vend"></div>
    </div>

    <!-- Seção 3: Tendência Mensal -->
    <div class="section" id="sec-tend">
      <div class="section-hd"><em>&#9679;</em> Tend&ecirc;ncia de Abertura &mdash; Novas Oportunidades por M&ecirc;s</div>
      <div class="tabs" id="tabs-tend">
        <button class="tab active" data-v="qtd">Quantidade</button>
        <button class="tab" data-v="val">Valor Estimado (R$)</button>
      </div>
      <div class="ch" style="height:220px"><canvas id="c-tend"></canvas></div>
      <div class="insight" id="insight-tend"></div>
    </div>

  </div>
</div>
</div>

<script>
const D = __DATA__;

// ── Helpers ────────────────────────────────────────────────────────────────────
function brl(v) {
  if (v >= 1e6) return 'R$ ' + (v / 1e6).toFixed(2).replace('.', ',') + 'M';
  if (v >= 1e3) return 'R$ ' + Math.round(v / 1e3) + 'K';
  return 'R$ ' + v.toLocaleString('pt-BR');
}
function pct(v) { return v.toFixed(1) + '%'; }

const tip = {mode:'index',intersect:false,backgroundColor:'#fff',borderColor:'#e8e4dc',borderWidth:1,titleColor:'#8a7560',bodyColor:'#0f172a',padding:10};
const sx  = {grid:{color:'#f0ebe0'},ticks:{color:'#64748b',font:{size:10}}};
const sy  = {grid:{color:'#f0ebe0'},ticks:{color:'#64748b'}};
const LEG = {color:'#374151',boxWidth:12,padding:12};

const COR = {
  'Lead':'#6b7fd4','Qualificado':'#4a9eed','Proposta':'#f0853a',
  'Negociação':'#d97706','Ganho':'#16a34a','Perdido':'#dc2626'
};

// ── KPIs ───────────────────────────────────────────────────────────────────────
const K = D.kpis;
document.getElementById('kv-pipe').textContent   = brl(K.pipeline_ativo_val);
document.getElementById('ks-pipe').textContent   = K.pipeline_ativo_qtd + ' oportunidades em aberto';
document.getElementById('kv-ganho').textContent  = brl(K.ganho_val);
document.getElementById('ks-ganho').textContent  = K.ganho_qtd + ' oportunidades convertidas';
document.getElementById('kv-taxa').textContent   = pct(K.taxa_conv);
document.getElementById('kv-ticket').textContent = brl(K.ticket_medio);

const taxaBadge = document.getElementById('kb-taxa');
const altaTaxa = K.taxa_conv >= 60;
taxaBadge.textContent  = altaTaxa ? '▲ Alta performance' : '▼ Abaixo da meta';
taxaBadge.style.background = altaTaxa ? '#dcfce7' : '#fee2e2';
taxaBadge.style.color      = altaTaxa ? '#16a34a'  : '#dc2626';

// ── Tabs (main) ────────────────────────────────────────────────────────────────
let activeSection = 'funil';
function switchTab(sec) {
  document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
  document.getElementById('sec-' + sec).style.display = 'block';
  document.querySelectorAll('.main-tab').forEach(t => t.classList.toggle('active', t.dataset.section === sec));
  activeSection = sec;
}
document.querySelectorAll('.main-tab').forEach(btn =>
  btn.addEventListener('click', () => switchTab(btn.dataset.section))
);

// ── Funil Chart ────────────────────────────────────────────────────────────────
let funilChart = null;

function buildFunil(mode) {
  const labels  = D.funil.labels;
  const vals    = mode === 'qtd' ? D.funil.qtd : D.funil.val;
  const spacers = mode === 'qtd' ? D.funil.spacers_qtd : D.funil.spacers_val;
  const colors  = labels.map(l => COR[l] || '#6b7fd4');

  if (funilChart) { funilChart.destroy(); funilChart = null; }
  funilChart = new Chart('c-funil', {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { data: spacers, backgroundColor: 'transparent', borderWidth: 0, label: '' },
        { data: vals, backgroundColor: colors, borderRadius: 5, label: mode === 'qtd' ? 'Oportunidades' : 'Valor' }
      ]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { ...tip, filter: item => item.datasetIndex === 1,
          callbacks: { label: c => mode === 'qtd' ? ' ' + c.parsed.x + ' oportunidades' : ' ' + brl(c.parsed.x) }
        }
      },
      scales: {
        x: { ...sx, stacked: true, ticks: { ...sx.ticks, callback: v => mode === 'qtd' ? v : brl(v) } },
        y: { ...sy, stacked: true }
      }
    }
  });

  const total = vals.reduce((s, v) => s + v, 0);
  document.getElementById('funil-tbody').innerHTML = labels.map((l, i) => {
    const v = vals[i];
    return `<tr>
      <td class="td-name"><span class="dot" style="background:${COR[l]}"></span>${l}</td>
      <td>${mode === 'qtd' ? v : D.funil.qtd[i]}</td>
      <td style="color:#0f172a;font-weight:600">${brl(mode === 'qtd' ? D.funil.val[i] : v)}</td>
      <td>${brl(D.funil.med[i])}</td>
      <td>${(v / total * 100).toFixed(1)}%</td>
    </tr>`;
  }).join('');
}
buildFunil('qtd');

document.querySelectorAll('#tabs-funil .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-funil .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    buildFunil(btn.dataset.v);
  });
});

// ── Donut Ganho × Perdido ──────────────────────────────────────────────────────
new Chart('c-outcome', {
  type: 'doughnut',
  data: {
    labels: ['Ganho', 'Perdido'],
    datasets: [{ data: [K.ganho_qtd, K.perdido_qtd], backgroundColor: ['#16a34a', '#dc2626'], borderWidth: 0, hoverOffset: 6 }]
  },
  options: {
    responsive: true, maintainAspectRatio: false, cutout: '66%',
    plugins: {
      legend: { position: 'bottom', labels: { ...LEG, padding: 14 } },
      tooltip: { ...tip, callbacks: { label: c => ` ${c.label}: ${c.parsed} oport.` } }
    }
  }
});

document.getElementById('insight-funil').innerHTML =
  `<strong>&#128270; Destaques do funil</strong><br>
  Pipeline ativo: <strong>${brl(K.pipeline_ativo_val)}</strong> em <strong>${K.pipeline_ativo_qtd}</strong> oportunidades.
  A etapa <strong>Proposta</strong> concentra o maior volume de valor retido &mdash; oportunidades aguardando aprovação.
  Taxa de conversão global: <strong>${pct(K.taxa_conv)}</strong> (${K.ganho_qtd} contratos ganhos vs. ${K.perdido_qtd} perdidos).`;

// ── Por Vendedor ───────────────────────────────────────────────────────────────
const vends = D.por_vendedor;
new Chart('c-vend', {
  type: 'bar',
  data: {
    labels: vends.map(v => v.nome),
    datasets: [
      { label: 'Ganho',        data: vends.map(v => v.ganho_qtd),     backgroundColor: '#16a34a', borderRadius: 4 },
      { label: 'Em Andamento', data: vends.map(v => v.andamento_qtd), backgroundColor: 'rgba(107,127,212,.7)', borderRadius: 4 },
      { label: 'Perdido',      data: vends.map(v => v.perdido_qtd),   backgroundColor: '#dc2626', borderRadius: 4 }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: LEG },
      tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${c.parsed.y} oport.` } }
    },
    scales: { x: { ...sx }, y: { ...sy } }
  }
});

document.getElementById('vend-tbody').innerHTML = vends.map(v => {
  const cor = v.taxa_conv >= 60 ? '#16a34a' : v.taxa_conv >= 40 ? '#d97706' : '#dc2626';
  return `<tr>
    <td class="td-name">${v.nome}</td>
    <td>${v.andamento_qtd}</td>
    <td>${v.ganho_qtd}</td>
    <td>${v.perdido_qtd}</td>
    <td style="color:${cor};font-weight:700">${pct(v.taxa_conv)}</td>
    <td style="color:#16a34a;font-weight:600">${brl(v.ganho_val)}</td>
  </tr>`;
}).join('');

const bv = vends.reduce((a, b) => b.ganho_val > a.ganho_val ? b : a, vends[0]);
const mv = vends.reduce((a, b) => b.taxa_conv > a.taxa_conv ? b : a, vends[0]);
document.getElementById('insight-vend').innerHTML =
  `<strong>&#127942; Destaque em valor:</strong> <strong>${bv.nome}</strong> lidera com
  <strong>${brl(bv.ganho_val)}</strong> em contratos ganhos &mdash; ${bv.ganho_qtd} oportunidades convertidas.
  &nbsp;&#183;&nbsp;
  <strong>&#127919; Melhor conversão:</strong> <strong>${mv.nome}</strong> com <strong>${pct(mv.taxa_conv)}</strong>.`;

// ── Tendência Mensal ───────────────────────────────────────────────────────────
let tendChart = null;

function buildTend(mode) {
  const vals  = mode === 'qtd' ? D.mensal.qtd : D.mensal.valor;
  const color = mode === 'qtd' ? '#6b7fd4' : '#f0853a';

  if (tendChart) { tendChart.destroy(); tendChart = null; }
  tendChart = new Chart('c-tend', {
    type: 'line',
    data: {
      labels: D.mensal.meses,
      datasets: [{ data: vals, borderColor: color, backgroundColor: color + '22',
        borderWidth: 2.5, pointRadius: 3, fill: true, tension: .35,
        label: mode === 'qtd' ? 'Novas oportunidades' : 'Valor estimado' }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { ...tip, callbacks: { label: c => mode === 'qtd' ? ` ${c.parsed.y} oport.` : ` ${brl(c.parsed.y)}` } }
      },
      scales: {
        x: { ...sx, ticks: { ...sx.ticks, maxRotation: 45 } },
        y: { ...sy, ticks: { ...sy.ticks, callback: v => mode === 'qtd' ? v : brl(v) } }
      }
    }
  });

  const qtdArr = D.mensal.qtd;
  const avg  = (qtdArr.reduce((s, v) => s + v, 0) / qtdArr.length).toFixed(1);
  const last3 = qtdArr.slice(-3).reduce((s, v) => s + v, 0);
  const prev3 = qtdArr.slice(-6, -3).reduce((s, v) => s + v, 0);
  const tendDir = last3 >= prev3 ? '&#9650; crescendo' : '&#9660; recuando';
  const tendCor = last3 >= prev3 ? '#16a34a' : '#dc2626';
  document.getElementById('insight-tend').innerHTML =
    `<strong>&#128337; Ritmo de prospecção</strong><br>
    Média de <strong>${avg}</strong> novas oportunidades/mês no período.
    Os últimos 3 meses somam <strong>${last3}</strong> aberturas vs <strong>${prev3}</strong> nos 3 anteriores
    &mdash; pipeline <strong style="color:${tendCor}">${tendDir}</strong>.`;
}
buildTend('qtd');

document.querySelectorAll('#tabs-tend .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-tend .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    buildTend(btn.dataset.v);
  });
});

// Ocultar seções não-ativas (após todos os charts renderizados)
document.getElementById('sec-vend').style.display = 'none';
document.getElementById('sec-tend').style.display = 'none';
</script>
</body>
</html>"""


# ── Queries e processamento de dados ─────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB)

    # 1. Por etapa
    df_etapa = pd.read_sql("""
        SELECT etapa, COUNT(*) AS qtd,
               ROUND(SUM(valor_estimado), 0) AS valor_total,
               ROUND(AVG(valor_estimado), 0)  AS valor_medio
        FROM fato_funil GROUP BY etapa
    """, conn)
    ordem = {"Lead": 1, "Qualificado": 2, "Proposta": 3, "Negociação": 4, "Ganho": 5, "Perdido": 6}
    df_etapa["ord"] = df_etapa["etapa"].map(ordem).fillna(7)
    df_etapa = df_etapa.sort_values("ord").reset_index(drop=True)

    etapas_ativas = ["Lead", "Qualificado", "Proposta", "Negociação"]
    df_ativas = df_etapa[df_etapa["etapa"].isin(etapas_ativas)].copy()

    # 2. Por vendedor × etapa
    df_vend = pd.read_sql("""
        SELECT v.nome, f.etapa, COUNT(*) AS qtd,
               ROUND(SUM(f.valor_estimado), 0) AS valor
        FROM fato_funil f
        JOIN dim_vendedores v ON f.id_vendedor = v.id_vendedor
        GROUP BY v.nome, f.etapa ORDER BY v.nome
    """, conn)

    vend_names = sorted(df_vend["nome"].unique().tolist())
    por_vendedor = []
    for nome in vend_names:
        sub = df_vend[df_vend["nome"] == nome]
        ganho_qtd   = int(sub.loc[sub["etapa"] == "Ganho",   "qtd"].sum())
        perdido_qtd = int(sub.loc[sub["etapa"] == "Perdido", "qtd"].sum())
        and_qtd     = int(sub.loc[sub["etapa"].isin(etapas_ativas), "qtd"].sum())
        ganho_val   = int(sub.loc[sub["etapa"] == "Ganho",   "valor"].sum())
        total_fech  = ganho_qtd + perdido_qtd
        taxa        = round(ganho_qtd / total_fech * 100, 1) if total_fech else 0.0
        por_vendedor.append({
            "nome": nome, "ganho_qtd": ganho_qtd, "perdido_qtd": perdido_qtd,
            "andamento_qtd": and_qtd, "ganho_val": ganho_val, "taxa_conv": taxa,
        })
    por_vendedor.sort(key=lambda x: -x["ganho_val"])

    # 3. Tendência mensal
    df_mensal = pd.read_sql("""
        SELECT substr(data_abertura, 1, 7) AS mes, COUNT(*) AS qtd,
               ROUND(SUM(valor_estimado), 0) AS valor
        FROM fato_funil GROUP BY mes ORDER BY mes
    """, conn)

    conn.close()

    # KPIs
    pipeline_ativo_val = int(df_ativas["valor_total"].sum())
    pipeline_ativo_qtd = int(df_ativas["qtd"].sum())
    ganho_qtd_total    = int(df_etapa.loc[df_etapa["etapa"] == "Ganho",   "qtd"].sum())
    ganho_val_total    = int(df_etapa.loc[df_etapa["etapa"] == "Ganho",   "valor_total"].sum())
    perdido_qtd_total  = int(df_etapa.loc[df_etapa["etapa"] == "Perdido", "qtd"].sum())
    perdido_val_total  = int(df_etapa.loc[df_etapa["etapa"] == "Perdido", "valor_total"].sum())
    taxa_conv          = round(ganho_qtd_total / (ganho_qtd_total + perdido_qtd_total) * 100, 1)
    ticket_medio       = int(round(df_etapa["valor_total"].sum() / df_etapa["qtd"].sum()))

    funil_labels = df_ativas["etapa"].tolist()
    funil_qtd    = [int(x) for x in df_ativas["qtd"]]
    funil_val    = [int(x) for x in df_ativas["valor_total"]]
    funil_med    = [int(x) for x in df_ativas["valor_medio"]]
    max_qtd      = max(funil_qtd)
    max_val      = max(funil_val)

    D = {
        "kpis": {
            "pipeline_ativo_val": pipeline_ativo_val,
            "pipeline_ativo_qtd": pipeline_ativo_qtd,
            "ganho_val":          ganho_val_total,
            "ganho_qtd":          ganho_qtd_total,
            "perdido_val":        perdido_val_total,
            "perdido_qtd":        perdido_qtd_total,
            "taxa_conv":          taxa_conv,
            "ticket_medio":       ticket_medio,
        },
        "funil": {
            "labels":      funil_labels,
            "qtd":         funil_qtd,
            "val":         funil_val,
            "med":         funil_med,
            "spacers_qtd": [round((max_qtd - v) / 2, 1) for v in funil_qtd],
            "spacers_val": [round((max_val - v) / 2, 1) for v in funil_val],
        },
        "por_vendedor": por_vendedor,
        "mensal": {
            "meses": df_mensal["mes"].tolist(),
            "qtd":   [int(x) for x in df_mensal["qtd"]],
            "valor": [int(x) for x in df_mensal["valor"]],
        },
    }

    data_json = json.dumps(D, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA__", data_json)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK Gerado: {OUT}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
