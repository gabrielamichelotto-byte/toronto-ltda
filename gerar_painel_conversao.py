# -*- coding: utf-8 -*-
"""
gerar_painel_conversao.py — Toronto LTDA (v2 — light theme + sidebar + abas)
"""
import json, sqlite3
import pandas as pd

DB  = "toronto_ltda.db"
OUT = "painel_conversao.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toronto LTDA — Conversão de Atividades</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="chartjs.min.js"></script>
<style>
:root{--accent:#2abfbf}
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
.canal-chip{display:inline-block;font-size:.62rem;padding:1px 8px;border-radius:10px;font-weight:600}

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
    <a href="painel_funil.html">&#128202; Funil de Vendas</a>
    <a href="painel_conversao.html" class="active">&#128222; Convers&atilde;o</a>
    <a href="painel_cancelamentos.html">&#9888; Cancelamentos</a>
    <a href="painel_mix.html">&#127863; Mix de Produtos</a>
  </nav>
  <div class="sb-footer">Toronto LTDA &mdash; Dados fict&iacute;cios<br>Portf&oacute;lio de An&aacute;lise de Dados</div>
</aside>

<div class="main">
  <div class="topbar">
    <div class="page-title">&#128222; Convers&atilde;o de Atividades <span class="page-title-badge">Efici&ecirc;ncia Comercial</span></div>
  </div>
  <div class="content">

    <div class="kpis">
      <div class="kpi" style="--ac:var(--accent)">
        <div class="kpi-icon">&#128222;</div>
        <div class="kpi-label">Total de Atividades</div>
        <div class="kpi-value" id="kv-total"></div>
        <div class="kpi-sub" id="ks-total"></div>
      </div>
      <div class="kpi" style="--ac:#16a34a">
        <div class="kpi-icon">&#9989;</div>
        <div class="kpi-label">Taxa de Convers&atilde;o</div>
        <div class="kpi-value" id="kv-taxa"></div>
        <div class="kpi-sub">atividades que geraram pedido</div>
        <span class="kpi-badge" id="kb-taxa"></span>
      </div>
      <div class="kpi" style="--ac:#f0853a">
        <div class="kpi-icon">&#127942;</div>
        <div class="kpi-label">Melhor Canal</div>
        <div class="kpi-value" id="kv-canal"></div>
        <div class="kpi-sub" id="ks-canal"></div>
      </div>
      <div class="kpi" style="--ac:#9b7fe8">
        <div class="kpi-icon">&#128260;</div>
        <div class="kpi-label">Atividades / Pedido</div>
        <div class="kpi-value" id="kv-ratio"></div>
        <div class="kpi-sub">m&eacute;dia de abordagens por venda</div>
      </div>
    </div>

    <div class="main-tabs">
      <button class="main-tab active" data-section="canal">&#128222; Por Canal</button>
      <button class="main-tab" data-section="vend">&#128100; Por Vendedor</button>
      <button class="main-tab" data-section="mes">&#128197; Evolu&ccedil;&atilde;o Mensal</button>
    </div>

    <!-- Seção 1: Por Canal -->
    <div class="section" id="sec-canal">
      <div class="section-hd"><em>&#9679;</em> Resultado por Tipo de Atividade</div>
      <div class="tabs" id="tabs-tipo">
        <button class="tab active" data-v="qtd">Volume</button>
        <button class="tab" data-v="taxa">Taxa de Convers&atilde;o</button>
      </div>
      <div class="g2">
        <div><div class="ch" style="height:220px"><canvas id="c-tipo"></canvas></div></div>
        <div><div class="ch" style="height:220px"><canvas id="c-tipo-taxa"></canvas></div></div>
      </div>
      <table>
        <thead>
          <tr><th>Canal</th><th>Pedidos</th><th>Reagendados</th><th>Sem Pedido</th><th>Total</th><th>Taxa Conv.</th></tr>
        </thead>
        <tbody id="tipo-tbody"></tbody>
      </table>
      <div class="insight" id="insight-tipo"></div>
    </div>

    <!-- Seção 2: Por Vendedor -->
    <div class="section" id="sec-vend">
      <div class="section-hd"><em>&#9679;</em> Efici&ecirc;ncia por Vendedor</div>
      <div class="tabs" id="tabs-vend">
        <button class="tab active" data-v="qtd">Volume</button>
        <button class="tab" data-v="taxa">Taxa de Convers&atilde;o</button>
      </div>
      <div class="ch" style="height:260px"><canvas id="c-vend"></canvas></div>
      <table>
        <thead>
          <tr><th>Vendedor</th><th>Total Ativ.</th><th>Pedidos</th><th>Taxa Conv.</th><th>Melhor Canal</th><th>Ativ./Pedido</th></tr>
        </thead>
        <tbody id="vend-tbody"></tbody>
      </table>
      <div class="insight" id="insight-vend"></div>
    </div>

    <!-- Seção 3: Evolução Mensal -->
    <div class="section" id="sec-mes">
      <div class="section-hd"><em>&#9679;</em> Evolu&ccedil;&atilde;o Mensal da Taxa de Convers&atilde;o</div>
      <div class="tabs" id="tabs-mes">
        <button class="tab active" data-v="taxa">Taxa de Convers&atilde;o (%)</button>
        <button class="tab" data-v="vol">Volume de Atividades</button>
      </div>
      <div class="ch" style="height:220px"><canvas id="c-mes"></canvas></div>
      <div class="insight" id="insight-mes"></div>
    </div>

  </div>
</div>
</div>

<script>
const D = __DATA__;

// ── Helpers ────────────────────────────────────────────────────────────────────
function pct(v)  { return v.toFixed(1) + '%'; }
function num(v)  { return v.toLocaleString('pt-BR'); }

const tip = {mode:'index',intersect:false,backgroundColor:'#fff',borderColor:'#e8e4dc',borderWidth:1,titleColor:'#8a7560',bodyColor:'#0f172a',padding:10};
const sx  = {grid:{color:'#f0ebe0'},ticks:{color:'#64748b',font:{size:10}}};
const sy  = {grid:{color:'#f0ebe0'},ticks:{color:'#64748b'}};
const LEG = {color:'#374151',boxWidth:12,padding:12};

const COR_CANAL = {Ligação:'#4a9eed', Positivação:'#2abfbf', Visita:'#9b7fe8'};

// ── KPIs ───────────────────────────────────────────────────────────────────────
const K = D.kpis;
document.getElementById('kv-total').textContent = num(K.total_atividades);
document.getElementById('ks-total').textContent = K.pedidos_total + ' pedidos gerados';
document.getElementById('kv-taxa').textContent  = pct(K.taxa_conv_geral);
document.getElementById('kv-canal').textContent = K.melhor_canal;
document.getElementById('ks-canal').textContent = pct(K.taxa_melhor_canal) + ' de conversão';
document.getElementById('kv-ratio').textContent = K.ativ_por_pedido.toFixed(1) + 'x';

const taxaBadge = document.getElementById('kb-taxa');
taxaBadge.textContent  = K.taxa_conv_geral >= 45 ? '▲ Acima da média' : K.taxa_conv_geral >= 40 ? '◆ Na média' : '▼ Abaixo da média';
taxaBadge.style.background = K.taxa_conv_geral >= 45 ? '#dcfce7' : K.taxa_conv_geral >= 40 ? '#fef9c3' : '#fee2e2';
taxaBadge.style.color      = K.taxa_conv_geral >= 45 ? '#16a34a' : K.taxa_conv_geral >= 40 ? '#d97706' : '#dc2626';

// ── Main-tabs ──────────────────────────────────────────────────────────────────
let activeSection = 'canal';
function switchTab(sec) {
  document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
  document.getElementById('sec-' + sec).style.display = 'block';
  document.querySelectorAll('.main-tab').forEach(t => t.classList.toggle('active', t.dataset.section === sec));
  activeSection = sec;
}
document.querySelectorAll('.main-tab').forEach(btn =>
  btn.addEventListener('click', () => switchTab(btn.dataset.section))
);

// ── Por Tipo de Atividade ──────────────────────────────────────────────────────
const tipos = D.por_tipo;
let tipoChart = null;

function buildTipo(mode) {
  if (tipoChart) { tipoChart.destroy(); tipoChart = null; }
  if (mode === 'qtd') {
    tipoChart = new Chart('c-tipo', {
      type: 'bar',
      data: {
        labels: tipos.map(t => t.tipo),
        datasets: [
          { label: 'Pedido',     data: tipos.map(t => t.pedido),     backgroundColor: '#16a34a', borderRadius: 4 },
          { label: 'Reagendado', data: tipos.map(t => t.reagendado), backgroundColor: '#f0853a', borderRadius: 4 },
          { label: 'Sem pedido', data: tipos.map(t => t.sem_pedido), backgroundColor: '#dc2626', borderRadius: 4 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: LEG }, tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${c.parsed.y}` } } },
        scales: { x: { ...sx }, y: { ...sy } }
      }
    });
  } else {
    tipoChart = new Chart('c-tipo', {
      type: 'bar',
      data: {
        labels: tipos.map(t => t.tipo),
        datasets: [{ label: 'Taxa (%)', data: tipos.map(t => t.taxa_conv), backgroundColor: tipos.map(t => COR_CANAL[t.tipo] || '#2abfbf'), borderRadius: 6 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { ...tip, callbacks: { label: c => ` Taxa: ${c.parsed.y.toFixed(1)}%` } } },
        scales: { x: { ...sx }, y: { ...sy, min: 0, max: 60, ticks: { ...sy.ticks, callback: v => v + '%' } } }
      }
    });
  }
}
buildTipo('qtd');

document.querySelectorAll('#tabs-tipo .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-tipo .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    buildTipo(btn.dataset.v);
  });
});

// Donut taxa por canal (estático à direita)
new Chart('c-tipo-taxa', {
  type: 'bar',
  data: {
    labels: tipos.map(t => t.tipo),
    datasets: [{ label: 'Taxa de Conversão (%)', data: tipos.map(t => t.taxa_conv), backgroundColor: tipos.map(t => COR_CANAL[t.tipo] || '#2abfbf'), borderRadius: 6 }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { ...tip, callbacks: { label: c => ` Taxa: ${c.parsed.y.toFixed(1)}%` } } },
    scales: { x: { ...sx }, y: { ...sy, min: 0, max: 60, ticks: { ...sy.ticks, callback: v => v + '%' } } }
  }
});

document.getElementById('tipo-tbody').innerHTML = tipos.map(t => {
  const cor = COR_CANAL[t.tipo] || '#2abfbf';
  const taxaCor = t.taxa_conv >= 45 ? '#16a34a' : t.taxa_conv >= 40 ? '#d97706' : '#f0853a';
  return `<tr>
    <td class="td-name"><span class="dot" style="background:${cor}"></span>${t.tipo}</td>
    <td style="color:#16a34a">${t.pedido}</td>
    <td style="color:#f0853a">${t.reagendado}</td>
    <td style="color:#dc2626">${t.sem_pedido}</td>
    <td>${t.total}</td>
    <td style="color:${taxaCor};font-weight:700">${pct(t.taxa_conv)}</td>
  </tr>`;
}).join('');

const melhorTipo = tipos.reduce((a, b) => b.taxa_conv > a.taxa_conv ? b : a, tipos[0]);
const piorTipo   = tipos.reduce((a, b) => b.taxa_conv < a.taxa_conv ? b : a, tipos[0]);
document.getElementById('insight-tipo').innerHTML =
  `<strong>&#128270; Canal mais eficiente:</strong> <strong>${melhorTipo.tipo}</strong> lidera com <strong>${pct(melhorTipo.taxa_conv)}</strong> de conversão
  (${melhorTipo.pedido} pedidos em ${melhorTipo.total} abordagens).
  &nbsp;&#183;&nbsp;
  <strong>${piorTipo.tipo}</strong> apresenta menor taxa (<strong>${pct(piorTipo.taxa_conv)}</strong>), oportunidade de qualificação nesse canal.`;

// ── Por Vendedor ───────────────────────────────────────────────────────────────
const vends = D.por_vendedor;
let vendChart = null;

function buildVend(mode) {
  if (vendChart) { vendChart.destroy(); vendChart = null; }
  if (mode === 'qtd') {
    vendChart = new Chart('c-vend', {
      type: 'bar',
      data: {
        labels: vends.map(v => v.nome),
        datasets: [
          { label: 'Pedido',     data: vends.map(v => v.pedido),     backgroundColor: '#16a34a', borderRadius: 4 },
          { label: 'Reagendado', data: vends.map(v => v.reagendado), backgroundColor: '#f0853a', borderRadius: 4 },
          { label: 'Sem pedido', data: vends.map(v => v.sem_pedido), backgroundColor: '#dc2626', borderRadius: 4 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: LEG }, tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${c.parsed.y}` } } },
        scales: { x: { ...sx }, y: { ...sy } }
      }
    });
  } else {
    vendChart = new Chart('c-vend', {
      type: 'bar',
      data: {
        labels: vends.map(v => v.nome),
        datasets: [{ label: 'Taxa de Conversão (%)', data: vends.map(v => v.taxa_conv),
          backgroundColor: vends.map(v => v.taxa_conv >= 45 ? '#16a34a' : v.taxa_conv >= 40 ? '#2abfbf' : '#f0853a'), borderRadius: 6 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { ...tip, callbacks: { label: c => ` Taxa: ${c.parsed.y.toFixed(1)}%` } } },
        scales: { x: { ...sx }, y: { ...sy, min: 0, max: 60, ticks: { ...sy.ticks, callback: v => v + '%' } } }
      }
    });
  }
}
buildVend('qtd');

document.querySelectorAll('#tabs-vend .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-vend .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    buildVend(btn.dataset.v);
  });
});

const CANAL_COR_MAP = {Positivação:'#2abfbf', Ligação:'#4a9eed', Visita:'#9b7fe8'};
document.getElementById('vend-tbody').innerHTML = vends.map(v => {
  const taxaCor  = v.taxa_conv >= 45 ? '#16a34a' : v.taxa_conv >= 40 ? '#2abfbf' : '#f0853a';
  const canalCor = CANAL_COR_MAP[v.melhor_canal] || '#8a7560';
  return `<tr>
    <td class="td-name">${v.nome}</td>
    <td>${v.total}</td>
    <td style="color:#16a34a">${v.pedido}</td>
    <td style="color:${taxaCor};font-weight:700">${pct(v.taxa_conv)}</td>
    <td><span class="canal-chip" style="background:${canalCor}22;color:${canalCor}">${v.melhor_canal}</span></td>
    <td>${v.ativ_por_pedido.toFixed(1)}x</td>
  </tr>`;
}).join('');

const bv = vends.reduce((a, b) => b.taxa_conv > a.taxa_conv ? b : a, vends[0]);
const hv = vends.reduce((a, b) => b.pedido > a.pedido ? b : a, vends[0]);
document.getElementById('insight-vend').innerHTML =
  `<strong>&#127942; Maior taxa de conversão:</strong> <strong>${bv.nome}</strong> — <strong>${pct(bv.taxa_conv)}</strong>
  (${bv.pedido} pedidos em ${bv.total} atividades), melhor desempenho em <strong>${bv.melhor_canal}</strong>.
  &nbsp;&#183;&nbsp;
  <strong>&#128200; Maior volume:</strong> <strong>${hv.nome}</strong> com <strong>${hv.pedido}</strong> pedidos gerados.`;

// ── Evolução Mensal ────────────────────────────────────────────────────────────
let mesChart = null;

function buildMes(mode) {
  if (mesChart) { mesChart.destroy(); mesChart = null; }
  const meses = D.mensal.map(m => m.mes);

  if (mode === 'taxa') {
    const taxas = D.mensal.map(m => m.taxa_conv);
    mesChart = new Chart('c-mes', {
      type: 'line',
      data: {
        labels: meses,
        datasets: [{ label: 'Taxa de Conversão (%)', data: taxas,
          borderColor: '#2abfbf', backgroundColor: '#2abfbf22',
          borderWidth: 2.5, pointRadius: 3, fill: true, tension: .35 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { ...tip, callbacks: { label: c => ` Taxa: ${c.parsed.y.toFixed(1)}%` } } },
        scales: { x: { ...sx, ticks: { ...sx.ticks, maxRotation: 45 } }, y: { ...sy, ticks: { ...sy.ticks, callback: v => v + '%' } } }
      }
    });
    const avg = (taxas.reduce((s, v) => s + v, 0) / taxas.length).toFixed(1);
    const melhor = Math.max(...taxas);
    const mesMelhor = meses[taxas.indexOf(melhor)];
    document.getElementById('insight-mes').innerHTML =
      `<strong>&#128337; Desempenho ao longo do período</strong><br>
      Taxa média de <strong>${avg}%</strong> de conversão nos ${taxas.length} meses.
      Melhor mês: <strong>${mesMelhor}</strong> com <strong>${melhor.toFixed(1)}%</strong>.
      Amplitude entre melhor e pior mês: <strong>${(melhor - Math.min(...taxas)).toFixed(1)} p.p.</strong>`;
  } else {
    mesChart = new Chart('c-mes', {
      type: 'bar',
      data: {
        labels: meses,
        datasets: [
          { label: 'Pedido',     data: D.mensal.map(m => m.pedido),     backgroundColor: '#16a34a', borderRadius: 3 },
          { label: 'Reagendado', data: D.mensal.map(m => m.reagendado), backgroundColor: '#f0853a', borderRadius: 3 },
          { label: 'Sem pedido', data: D.mensal.map(m => m.sem_pedido), backgroundColor: '#dc2626', borderRadius: 3 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: LEG }, tooltip: { ...tip } },
        scales: { x: { ...sx, ticks: { ...sx.ticks, maxRotation: 45 } }, y: { ...sy } }
      }
    });
    document.getElementById('insight-mes').innerHTML = '';
  }
}
buildMes('taxa');

document.querySelectorAll('#tabs-mes .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-mes .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    buildMes(btn.dataset.v);
  });
});

// Ocultar seções não-ativas (após todos os charts renderizados)
document.getElementById('sec-vend').style.display = 'none';
document.getElementById('sec-mes').style.display  = 'none';
</script>
</body>
</html>"""


# ── Queries e processamento ───────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB)

    # Por tipo × resultado
    df_tipo = pd.read_sql("""
        SELECT tipo, resultado, COUNT(*) AS qtd
        FROM fato_atividades GROUP BY tipo, resultado
    """, conn)

    # Por vendedor × resultado
    df_vend = pd.read_sql("""
        SELECT v.nome, a.resultado, COUNT(*) AS qtd
        FROM fato_atividades a JOIN dim_vendedores v ON a.id_vendedor=v.id_vendedor
        GROUP BY v.nome, a.resultado
    """, conn)

    # Tipo × vendedor (para melhor canal por vendedor)
    df_tv = pd.read_sql("""
        SELECT v.nome, a.tipo, a.resultado, COUNT(*) AS qtd
        FROM fato_atividades a JOIN dim_vendedores v ON a.id_vendedor=v.id_vendedor
        GROUP BY v.nome, a.tipo, a.resultado
    """, conn)

    # Mensal
    df_mes = pd.read_sql("""
        SELECT substr(data_atividade,1,7) AS mes, resultado, COUNT(*) AS qtd
        FROM fato_atividades GROUP BY mes, resultado ORDER BY mes, resultado
    """, conn)
    conn.close()

    # ── Por tipo ─────────────────────────────────────────────────────────────
    por_tipo = []
    for tipo in ["Ligação", "Positivação", "Visita"]:
        sub = df_tipo[df_tipo["tipo"] == tipo]
        pedido  = int(sub.loc[sub["resultado"] == "Pedido",     "qtd"].sum())
        reagend = int(sub.loc[sub["resultado"] == "Reagendado", "qtd"].sum())
        sem     = int(sub.loc[sub["resultado"] == "Sem pedido", "qtd"].sum())
        total   = pedido + reagend + sem
        taxa    = round(pedido / total * 100, 1) if total else 0.0
        por_tipo.append({"tipo": tipo, "pedido": pedido, "reagendado": reagend,
                         "sem_pedido": sem, "total": total, "taxa_conv": taxa})

    # ── Por vendedor ─────────────────────────────────────────────────────────
    por_vendedor = []
    for nome in sorted(df_vend["nome"].unique()):
        sub = df_vend[df_vend["nome"] == nome]
        pedido  = int(sub.loc[sub["resultado"] == "Pedido",     "qtd"].sum())
        reagend = int(sub.loc[sub["resultado"] == "Reagendado", "qtd"].sum())
        sem     = int(sub.loc[sub["resultado"] == "Sem pedido", "qtd"].sum())
        total   = pedido + reagend + sem
        taxa    = round(pedido / total * 100, 1) if total else 0.0
        ratio   = round(total / pedido, 2) if pedido else 0.0

        tv_sub = df_tv[df_tv["nome"] == nome]
        canal_stats = []
        for canal in ["Ligação", "Positivação", "Visita"]:
            c = tv_sub[tv_sub["tipo"] == canal]
            p = int(c.loc[c["resultado"] == "Pedido", "qtd"].sum())
            t = int(c["qtd"].sum())
            canal_stats.append((canal, round(p / t * 100, 1) if t else 0.0))
        melhor_canal = max(canal_stats, key=lambda x: x[1])[0]

        por_vendedor.append({
            "nome": nome, "pedido": pedido, "reagendado": reagend,
            "sem_pedido": sem, "total": total, "taxa_conv": taxa,
            "ativ_por_pedido": ratio, "melhor_canal": melhor_canal,
        })
    por_vendedor.sort(key=lambda x: -x["taxa_conv"])

    # ── Mensal ────────────────────────────────────────────────────────────────
    meses = sorted(df_mes["mes"].unique())
    mensal = []
    for mes in meses:
        sub = df_mes[df_mes["mes"] == mes]
        p = int(sub.loc[sub["resultado"] == "Pedido",     "qtd"].sum())
        r = int(sub.loc[sub["resultado"] == "Reagendado", "qtd"].sum())
        s = int(sub.loc[sub["resultado"] == "Sem pedido", "qtd"].sum())
        tot = p + r + s
        mensal.append({"mes": mes, "pedido": p, "reagendado": r,
                       "sem_pedido": s, "total": tot,
                       "taxa_conv": round(p / tot * 100, 1) if tot else 0.0})

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_atividades = int(df_tipo["qtd"].sum())
    pedidos_total    = sum(t["pedido"] for t in por_tipo)
    taxa_conv_geral  = round(pedidos_total / total_atividades * 100, 1)
    ativ_por_pedido  = round(total_atividades / pedidos_total, 2)
    melhor_tipo      = max(por_tipo, key=lambda x: x["taxa_conv"])

    D = {
        "kpis": {
            "total_atividades": total_atividades,
            "pedidos_total":    pedidos_total,
            "taxa_conv_geral":  taxa_conv_geral,
            "melhor_canal":     melhor_tipo["tipo"],
            "taxa_melhor_canal": melhor_tipo["taxa_conv"],
            "ativ_por_pedido":  ativ_por_pedido,
        },
        "por_tipo":     por_tipo,
        "por_vendedor": por_vendedor,
        "mensal":       mensal,
    }

    data_json = json.dumps(D, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA__", data_json)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK Gerado: {OUT}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
