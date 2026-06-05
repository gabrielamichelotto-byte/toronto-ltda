# -*- coding: utf-8 -*-
"""
gerar_painel_cancelamentos.py — Toronto LTDA (v2 — light theme + sidebar + abas)
"""
import json, sqlite3
import pandas as pd

DB  = "toronto_ltda.db"
OUT = "painel_cancelamentos.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toronto LTDA — Cancelamentos &amp; Devoluções</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="chartjs.min.js"></script>
<style>
:root{--accent:#f59e0b}
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
.chip{display:inline-block;font-size:.62rem;padding:1px 8px;border-radius:10px;font-weight:600}

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
    <a href="painel_conversao.html">&#128222; Convers&atilde;o</a>
    <a href="painel_cancelamentos.html" class="active">&#9888; Cancelamentos</a>
    <a href="painel_mix.html">&#127863; Mix de Produtos</a>
  </nav>
  <div class="sb-footer">Toronto LTDA &mdash; Dados fict&iacute;cios<br>Portf&oacute;lio de An&aacute;lise de Dados</div>
</aside>

<div class="main">
  <div class="topbar">
    <div class="page-title">&#9888; Cancelamentos &amp; Devolu&ccedil;&otilde;es <span class="page-title-badge">Controle de Perdas</span></div>
  </div>
  <div class="content">

    <div class="kpis">
      <div class="kpi" style="--ac:var(--accent)">
        <div class="kpi-icon">&#10060;</div>
        <div class="kpi-label">Cancelamentos</div>
        <div class="kpi-value" id="kv-canc"></div>
        <div class="kpi-sub" id="ks-canc"></div>
      </div>
      <div class="kpi" style="--ac:#f0853a">
        <div class="kpi-icon">&#8617;</div>
        <div class="kpi-label">Devolu&ccedil;&otilde;es</div>
        <div class="kpi-value" id="kv-dev"></div>
        <div class="kpi-sub" id="ks-dev"></div>
      </div>
      <div class="kpi" style="--ac:#dc2626">
        <div class="kpi-icon">&#128184;</div>
        <div class="kpi-label">Valor em Risco</div>
        <div class="kpi-value" id="kv-risco"></div>
        <div class="kpi-sub">cancelamentos + devolu&ccedil;&otilde;es</div>
      </div>
      <div class="kpi" style="--ac:#9b7fe8">
        <div class="kpi-icon">&#128202;</div>
        <div class="kpi-label">Taxa de Perda</div>
        <div class="kpi-value" id="kv-taxa"></div>
        <div class="kpi-sub">itens perdidos / total de itens</div>
        <span class="kpi-badge" id="kb-taxa"></span>
      </div>
    </div>

    <div class="main-tabs">
      <button class="main-tab active" data-section="mes">&#128197; Evolu&ccedil;&atilde;o Mensal</button>
      <button class="main-tab" data-section="vend">&#128100; Por Vendedor</button>
      <button class="main-tab" data-section="cat">&#127991; Por Categoria</button>
      <button class="main-tab" data-section="seg">&#127970; Por Segmento</button>
    </div>

    <!-- Seção 1: Evolução Mensal -->
    <div class="section" id="sec-mes">
      <div class="section-hd"><em>&#9679;</em> Evolu&ccedil;&atilde;o Mensal</div>
      <div class="tabs" id="tabs-mes">
        <button class="tab active" data-v="qtd">Volume (itens)</button>
        <button class="tab" data-v="val">Valor (R$)</button>
      </div>
      <div class="ch" style="height:240px"><canvas id="c-mes"></canvas></div>
      <div class="insight" id="insight-mes"></div>
    </div>

    <!-- Seção 2: Por Vendedor -->
    <div class="section" id="sec-vend">
      <div class="section-hd"><em>&#9679;</em> Por Vendedor</div>
      <div class="tabs" id="tabs-vend">
        <button class="tab active" data-v="qtd">Volume (itens)</button>
        <button class="tab" data-v="val">Valor (R$)</button>
        <button class="tab" data-v="taxa">Taxa de Perda (%)</button>
      </div>
      <div class="ch" style="height:260px"><canvas id="c-vend"></canvas></div>
      <table>
        <thead>
          <tr><th>Vendedor</th><th>Cancelamentos</th><th>Devolu&ccedil;&otilde;es</th><th>Total Perdido</th><th>Valor Perdido</th><th>Taxa Perda</th></tr>
        </thead>
        <tbody id="vend-tbody"></tbody>
      </table>
      <div class="insight" id="insight-vend"></div>
    </div>

    <!-- Seção 3: Por Categoria -->
    <div class="section" id="sec-cat">
      <div class="section-hd"><em>&#9679;</em> Por Categoria de Produto</div>
      <div class="tabs" id="tabs-cat">
        <button class="tab active" data-v="qtd">Volume (itens)</button>
        <button class="tab" data-v="val">Valor (R$)</button>
      </div>
      <div class="g2">
        <div><div class="ch" style="height:220px"><canvas id="c-cat"></canvas></div></div>
        <div><div class="ch" style="height:220px"><canvas id="c-cat-donut"></canvas></div></div>
      </div>
      <table>
        <thead>
          <tr><th>Categoria</th><th>Cancelamentos</th><th>Devolu&ccedil;&otilde;es</th><th>Total</th><th>Valor Perdido</th><th>% do Total</th></tr>
        </thead>
        <tbody id="cat-tbody"></tbody>
      </table>
      <div class="insight" id="insight-cat"></div>
    </div>

    <!-- Seção 4: Por Segmento -->
    <div class="section" id="sec-seg">
      <div class="section-hd"><em>&#9679;</em> Por Segmento de Cliente</div>
      <div class="tabs" id="tabs-seg">
        <button class="tab active" data-v="qtd">Volume (itens)</button>
        <button class="tab" data-v="val">Valor (R$)</button>
        <button class="tab" data-v="taxa">Taxa de Perda (%)</button>
      </div>
      <div class="ch" style="height:240px"><canvas id="c-seg"></canvas></div>
      <table>
        <thead>
          <tr><th>Segmento</th><th>Cancelamentos</th><th>Devolu&ccedil;&otilde;es</th><th>Total</th><th>Valor Perdido</th><th>Taxa Perda</th></tr>
        </thead>
        <tbody id="seg-tbody"></tbody>
      </table>
      <div class="insight" id="insight-seg"></div>
    </div>

  </div>
</div>
</div>

<script>
const D = __DATA__;

// ── Helpers ────────────────────────────────────────────────────────────────────
function brl(v) {
  if (v >= 1e6) return 'R$ ' + (v / 1e6).toFixed(2).replace('.', ',') + 'M';
  if (v >= 1e3) return 'R$ ' + (v / 1e3).toFixed(0) + 'K';
  return 'R$ ' + v.toLocaleString('pt-BR');
}
function pct(v)  { return v.toFixed(1) + '%'; }
function num(v)  { return v.toLocaleString('pt-BR'); }

const tip = {mode:'index',intersect:false,backgroundColor:'#fff',borderColor:'#e8e4dc',borderWidth:1,titleColor:'#8a7560',bodyColor:'#0f172a',padding:10};
const sx  = {grid:{color:'#f0ebe0'},ticks:{color:'#64748b',font:{size:10}}};
const sy  = {grid:{color:'#f0ebe0'},ticks:{color:'#64748b'}};
const LEG = {color:'#374151',boxWidth:12,padding:12};
const COR_CANC = '#f59e0b';
const COR_DEV  = '#f0853a';

// ── KPIs ───────────────────────────────────────────────────────────────────────
const K = D.kpis;
document.getElementById('kv-canc').textContent  = num(K.canc_itens);
document.getElementById('ks-canc').textContent  = brl(K.canc_valor) + ' perdidos';
document.getElementById('kv-dev').textContent   = num(K.dev_itens);
document.getElementById('ks-dev').textContent   = brl(K.dev_valor) + ' revertidos';
document.getElementById('kv-risco').textContent = brl(K.total_valor);
document.getElementById('kv-taxa').textContent  = pct(K.taxa_perda);

const badge = document.getElementById('kb-taxa');
badge.textContent      = K.taxa_perda < 8 ? '▼ Controlado' : K.taxa_perda < 12 ? '◆ Atenção' : '▲ Crítico';
badge.style.background = K.taxa_perda < 8 ? '#dcfce7' : K.taxa_perda < 12 ? '#fef9c3' : '#fee2e2';
badge.style.color      = K.taxa_perda < 8 ? '#16a34a'  : K.taxa_perda < 12 ? '#d97706' : '#dc2626';

// ── Main-tabs ──────────────────────────────────────────────────────────────────
let activeSection = 'mes';
function switchTab(sec) {
  document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
  document.getElementById('sec-' + sec).style.display = 'block';
  document.querySelectorAll('.main-tab').forEach(t => t.classList.toggle('active', t.dataset.section === sec));
  activeSection = sec;
}
document.querySelectorAll('.main-tab').forEach(btn =>
  btn.addEventListener('click', () => switchTab(btn.dataset.section))
);

// ── Evolução Mensal ────────────────────────────────────────────────────────────
let mesChart = null;

function buildMes(mode) {
  if (mesChart) { mesChart.destroy(); mesChart = null; }
  const meses = D.mensal.map(m => m.mes);
  const cancD = D.mensal.map(m => mode === 'qtd' ? m.canc_qtd : m.canc_val);
  const devD  = D.mensal.map(m => mode === 'qtd' ? m.dev_qtd  : m.dev_val);
  const yFmt  = mode === 'qtd' ? v => v : v => brl(v);

  mesChart = new Chart('c-mes', {
    type: 'line',
    data: {
      labels: meses,
      datasets: [
        { label: 'Cancelamentos', data: cancD, borderColor: COR_CANC, backgroundColor: COR_CANC + '22', borderWidth: 2.5, pointRadius: 3, fill: true, tension: .35 },
        { label: 'Devoluções',    data: devD,  borderColor: COR_DEV,  backgroundColor: COR_DEV  + '22', borderWidth: 2.5, pointRadius: 3, fill: true, tension: .35 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: LEG },
        tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${mode === 'qtd' ? c.parsed.y : brl(c.parsed.y)}` } }
      },
      scales: { x: { ...sx, ticks: { ...sx.ticks, maxRotation: 45 } }, y: { ...sy, ticks: { ...sy.ticks, callback: yFmt } } }
    }
  });

  const totalMes = D.mensal.map(m => mode === 'qtd' ? m.canc_qtd + m.dev_qtd : m.canc_val + m.dev_val);
  const maxIdx = totalMes.indexOf(Math.max(...totalMes));
  const minIdx = totalMes.indexOf(Math.min(...totalMes));
  const avg    = totalMes.reduce((s, v) => s + v, 0) / totalMes.length;
  document.getElementById('insight-mes').innerHTML =
    `<strong>&#128337; Sazonalidade das perdas</strong><br>
    Média mensal: <strong>${mode === 'qtd' ? Math.round(avg) + ' itens' : brl(avg)}</strong>.
    Pico em <strong>${meses[maxIdx]}</strong> &mdash; maior concentração de ${mode === 'qtd' ? 'cancelamentos e devoluções' : 'valor perdido'}.
    Melhor mês: <strong>${meses[minIdx]}</strong>.`;
}
buildMes('qtd');

document.querySelectorAll('#tabs-mes .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-mes .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); buildMes(btn.dataset.v);
  });
});

// ── Por Vendedor ───────────────────────────────────────────────────────────────
const vends = D.por_vendedor;
let vendChart = null;

function buildVend(mode) {
  if (vendChart) { vendChart.destroy(); vendChart = null; }
  const labels = vends.map(v => v.nome);

  if (mode === 'taxa') {
    vendChart = new Chart('c-vend', {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Taxa de Perda (%)', data: vends.map(v => v.taxa_perda),
        backgroundColor: vends.map(v => v.taxa_perda < 8 ? '#16a34a' : v.taxa_perda < 12 ? '#f59e0b' : '#dc2626'), borderRadius: 6 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { ...tip, callbacks: { label: c => ` Taxa: ${c.parsed.y.toFixed(1)}%` } } },
        scales: { x: { ...sx }, y: { ...sy, ticks: { ...sy.ticks, callback: v => v + '%' } } }
      }
    });
  } else {
    const isVal = mode === 'val';
    vendChart = new Chart('c-vend', {
      type: 'bar',
      data: { labels, datasets: [
        { label: 'Cancelamentos', data: vends.map(v => isVal ? v.canc_val : v.canc_qtd), backgroundColor: COR_CANC, borderRadius: 4 },
        { label: 'Devoluções',    data: vends.map(v => isVal ? v.dev_val  : v.dev_qtd),  backgroundColor: COR_DEV,  borderRadius: 4 }
      ]},
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: LEG }, tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${isVal ? brl(c.parsed.y) : c.parsed.y}` } } },
        scales: { x: { ...sx }, y: { ...sy, ticks: { ...sy.ticks, callback: v => isVal ? brl(v) : v } } }
      }
    });
  }
}
buildVend('qtd');

document.querySelectorAll('#tabs-vend .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-vend .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); buildVend(btn.dataset.v);
  });
});

document.getElementById('vend-tbody').innerHTML = vends.map(v => {
  const cor = v.taxa_perda < 8 ? '#16a34a' : v.taxa_perda < 12 ? '#f59e0b' : '#dc2626';
  return `<tr>
    <td class="td-name">${v.nome}</td>
    <td style="color:${COR_CANC}">${v.canc_qtd}</td>
    <td style="color:${COR_DEV}">${v.dev_qtd}</td>
    <td>${v.total_qtd}</td>
    <td style="color:#dc2626;font-weight:600">${brl(v.total_val)}</td>
    <td style="color:${cor};font-weight:700">${pct(v.taxa_perda)}</td>
  </tr>`;
}).join('');

const piorVend   = vends.reduce((a, b) => b.taxa_perda > a.taxa_perda ? b : a, vends[0]);
const melhorVend = vends.reduce((a, b) => b.taxa_perda < a.taxa_perda ? b : a, vends[0]);
document.getElementById('insight-vend').innerHTML =
  `<strong>&#9888; Maior taxa de perda:</strong> <strong>${piorVend.nome}</strong> &mdash; <strong>${pct(piorVend.taxa_perda)}</strong>
  dos itens (${piorVend.total_qtd} ocorrências, ${brl(piorVend.total_val)} em risco).
  &nbsp;&#183;&nbsp;
  <strong>&#9989; Menor taxa:</strong> <strong>${melhorVend.nome}</strong> com <strong>${pct(melhorVend.taxa_perda)}</strong> &mdash; carteira mais estável.`;

// ── Por Categoria ──────────────────────────────────────────────────────────────
const cats = D.por_categoria;
let catChart = null;

function buildCat(mode) {
  if (catChart) { catChart.destroy(); catChart = null; }
  const isVal = mode === 'val';
  catChart = new Chart('c-cat', {
    type: 'bar',
    data: { labels: cats.map(c => c.categoria), datasets: [
      { label: 'Cancelamentos', data: cats.map(c => isVal ? c.canc_val : c.canc_qtd), backgroundColor: COR_CANC, borderRadius: 4 },
      { label: 'Devoluções',    data: cats.map(c => isVal ? c.dev_val  : c.dev_qtd),  backgroundColor: COR_DEV,  borderRadius: 4 }
    ]},
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top', labels: LEG }, tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${isVal ? brl(c.parsed.y) : c.parsed.y}` } } },
      scales: { x: { ...sx, ticks: { ...sx.ticks, maxRotation: 45 } }, y: { ...sy, ticks: { ...sy.ticks, callback: v => isVal ? brl(v) : v } } }
    }
  });
}
buildCat('qtd');

document.querySelectorAll('#tabs-cat .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-cat .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); buildCat(btn.dataset.v);
  });
});

const totalCanc = cats.reduce((s, c) => s + c.canc_qtd, 0);
const totalDev  = cats.reduce((s, c) => s + c.dev_qtd,  0);
new Chart('c-cat-donut', {
  type: 'doughnut',
  data: {
    labels: ['Cancelamentos', 'Devoluções'],
    datasets: [{ data: [totalCanc, totalDev], backgroundColor: [COR_CANC, COR_DEV], borderWidth: 0, hoverOffset: 6 }]
  },
  options: {
    responsive: true, maintainAspectRatio: false, cutout: '64%',
    plugins: {
      legend: { position: 'bottom', labels: { ...LEG, padding: 14 } },
      tooltip: { ...tip, callbacks: { label: c => ` ${c.label}: ${c.parsed} itens (${pct(c.parsed / (totalCanc + totalDev) * 100)})` } }
    }
  }
});

const totalCatAll = cats.reduce((s, c) => s + c.total_qtd, 0);
document.getElementById('cat-tbody').innerHTML = cats.map(c => {
  return `<tr>
    <td class="td-name">${c.categoria}</td>
    <td style="color:${COR_CANC}">${c.canc_qtd}</td>
    <td style="color:${COR_DEV}">${c.dev_qtd}</td>
    <td>${c.total_qtd}</td>
    <td style="color:#dc2626;font-weight:600">${brl(c.total_val)}</td>
    <td>${(c.total_qtd / totalCatAll * 100).toFixed(1)}%</td>
  </tr>`;
}).join('');

const piorCat  = cats.reduce((a, b) => b.total_qtd > a.total_qtd ? b : a, cats[0]);
const piorCatV = cats.reduce((a, b) => b.total_val > a.total_val ? b : a, cats[0]);
document.getElementById('insight-cat').innerHTML =
  `<strong>&#128269; Mais ocorrências:</strong> <strong>${piorCat.categoria}</strong> &mdash;
  ${piorCat.total_qtd} itens (${pct(piorCat.total_qtd / totalCatAll * 100)} do total de perdas).
  &nbsp;&#183;&nbsp;
  <strong>&#128184; Maior impacto financeiro:</strong> <strong>${piorCatV.categoria}</strong> com <strong>${brl(piorCatV.total_val)}</strong>.`;

// ── Por Segmento ───────────────────────────────────────────────────────────────
const segs = D.por_segmento;
let segChart = null;

function buildSeg(mode) {
  if (segChart) { segChart.destroy(); segChart = null; }
  const labels = segs.map(s => s.segmento);

  if (mode === 'taxa') {
    segChart = new Chart('c-seg', {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Taxa de Perda (%)', data: segs.map(s => s.taxa_perda),
        backgroundColor: segs.map(s => s.taxa_perda < 8 ? '#16a34a' : s.taxa_perda < 12 ? '#f59e0b' : '#dc2626'), borderRadius: 6 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { ...tip, callbacks: { label: c => ` Taxa: ${c.parsed.y.toFixed(1)}%` } } },
        scales: { x: { ...sx }, y: { ...sy, ticks: { ...sy.ticks, callback: v => v + '%' } } }
      }
    });
  } else {
    const isVal = mode === 'val';
    segChart = new Chart('c-seg', {
      type: 'bar',
      data: { labels, datasets: [
        { label: 'Cancelamentos', data: segs.map(s => isVal ? s.canc_val : s.canc_qtd), backgroundColor: COR_CANC, borderRadius: 4 },
        { label: 'Devoluções',    data: segs.map(s => isVal ? s.dev_val  : s.dev_qtd),  backgroundColor: COR_DEV,  borderRadius: 4 }
      ]},
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: LEG }, tooltip: { ...tip, callbacks: { label: c => ` ${c.dataset.label}: ${isVal ? brl(c.parsed.y) : c.parsed.y}` } } },
        scales: { x: { ...sx }, y: { ...sy, ticks: { ...sy.ticks, callback: v => isVal ? brl(v) : v } } }
      }
    });
  }
}
buildSeg('qtd');

document.querySelectorAll('#tabs-seg .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-seg .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); buildSeg(btn.dataset.v);
  });
});

document.getElementById('seg-tbody').innerHTML = segs.map(s => {
  const cor = s.taxa_perda < 8 ? '#16a34a' : s.taxa_perda < 12 ? '#f59e0b' : '#dc2626';
  return `<tr>
    <td class="td-name">${s.segmento}</td>
    <td style="color:${COR_CANC}">${s.canc_qtd}</td>
    <td style="color:${COR_DEV}">${s.dev_qtd}</td>
    <td>${s.total_qtd}</td>
    <td style="color:#dc2626;font-weight:600">${brl(s.total_val)}</td>
    <td style="color:${cor};font-weight:700">${pct(s.taxa_perda)}</td>
  </tr>`;
}).join('');

const piorSeg   = segs.reduce((a, b) => b.taxa_perda > a.taxa_perda ? b : a, segs[0]);
const melhorSeg = segs.reduce((a, b) => b.taxa_perda < a.taxa_perda ? b : a, segs[0]);
document.getElementById('insight-seg').innerHTML =
  `<strong>&#9888; Segmento mais crítico:</strong> <strong>${piorSeg.segmento}</strong> &mdash;
  taxa de perda de <strong>${pct(piorSeg.taxa_perda)}</strong> (${piorSeg.total_qtd} itens, ${brl(piorSeg.total_val)}).
  Avaliar política de retorno e qualificação de pedidos neste segmento.
  &nbsp;&#183;&nbsp;
  <strong>&#9989; Mais confiável:</strong> <strong>${melhorSeg.segmento}</strong> com <strong>${pct(melhorSeg.taxa_perda)}</strong>.`;

// Ocultar seções não-ativas (após todos os charts renderizados)
document.getElementById('sec-vend').style.display = 'none';
document.getElementById('sec-cat').style.display  = 'none';
document.getElementById('sec-seg').style.display  = 'none';
</script>
</body>
</html>"""


# ── Queries e processamento ───────────────────────────────────────────────────
def main():
    conn = sqlite3.connect(DB)

    df = pd.read_sql("""
        SELECT
            p.status_pedido,
            substr(p.data_pedido, 1, 7) AS mes,
            p.valor_liquido,
            p.quantidade,
            v.nome AS vendedor,
            pr.categoria,
            cl.segmento
        FROM fato_pedidos p
        JOIN dim_vendedores v  ON p.id_vendedor = v.id_vendedor
        JOIN dim_produtos   pr ON p.id_produto  = pr.id_produto
        JOIN dim_clientes   cl ON p.id_cliente  = cl.id_cliente
    """, conn)
    conn.close()

    df_total = df.copy()
    df_cd    = df[df["status_pedido"].isin(["Cancelado", "Devolvido"])].copy()
    df_canc  = df_cd[df_cd["status_pedido"] == "Cancelado"]
    df_dev   = df_cd[df_cd["status_pedido"] == "Devolvido"]

    # ── KPIs ─────────────────────────────────────────────────────────────────
    canc_itens  = int(df_canc["quantidade"].sum())
    dev_itens   = int(df_dev["quantidade"].sum())
    canc_valor  = round(float(df_canc["valor_liquido"].sum()), 2)
    dev_valor   = round(float(df_dev["valor_liquido"].sum()), 2)
    total_valor = round(canc_valor + dev_valor, 2)
    total_itens_geral = int(df_total["quantidade"].sum())
    taxa_perda  = round((canc_itens + dev_itens) / total_itens_geral * 100, 1)

    # ── Por mês ───────────────────────────────────────────────────────────────
    meses = sorted(df_total["mes"].unique())
    mensal = []
    for mes in meses:
        c = df_canc[df_canc["mes"] == mes]
        d = df_dev[df_dev["mes"] == mes]
        mensal.append({
            "mes":      mes,
            "canc_qtd": int(c["quantidade"].sum()),
            "dev_qtd":  int(d["quantidade"].sum()),
            "canc_val": round(float(c["valor_liquido"].sum()), 0),
            "dev_val":  round(float(d["valor_liquido"].sum()), 0),
        })

    # ── Por vendedor ──────────────────────────────────────────────────────────
    por_vendedor = []
    for nome in sorted(df_total["vendedor"].unique()):
        total_v = df_total[df_total["vendedor"] == nome]
        canc_v  = df_canc[df_canc["vendedor"] == nome]
        dev_v   = df_dev[df_dev["vendedor"] == nome]
        total_q = int(total_v["quantidade"].sum())
        canc_q  = int(canc_v["quantidade"].sum())
        dev_q   = int(dev_v["quantidade"].sum())
        lost_q  = canc_q + dev_q
        canc_vv = round(float(canc_v["valor_liquido"].sum()), 0)
        dev_vv  = round(float(dev_v["valor_liquido"].sum()), 0)
        taxa    = round(lost_q / total_q * 100, 1) if total_q else 0.0
        por_vendedor.append({
            "nome":      nome,
            "canc_qtd":  canc_q,
            "dev_qtd":   dev_q,
            "total_qtd": lost_q,
            "canc_val":  canc_vv,
            "dev_val":   dev_vv,
            "total_val": canc_vv + dev_vv,
            "taxa_perda": taxa,
        })
    por_vendedor.sort(key=lambda x: -x["taxa_perda"])

    # ── Por categoria ─────────────────────────────────────────────────────────
    por_categoria = []
    for cat in sorted(df_total["categoria"].unique()):
        canc_c = df_canc[df_canc["categoria"] == cat]
        dev_c  = df_dev[df_dev["categoria"] == cat]
        canc_q = int(canc_c["quantidade"].sum())
        dev_q  = int(dev_c["quantidade"].sum())
        canc_v = round(float(canc_c["valor_liquido"].sum()), 0)
        dev_v  = round(float(dev_c["valor_liquido"].sum()), 0)
        por_categoria.append({
            "categoria": cat,
            "canc_qtd":  canc_q,
            "dev_qtd":   dev_q,
            "total_qtd": canc_q + dev_q,
            "canc_val":  canc_v,
            "dev_val":   dev_v,
            "total_val": canc_v + dev_v,
        })
    por_categoria.sort(key=lambda x: -x["total_qtd"])

    # ── Por segmento ──────────────────────────────────────────────────────────
    por_segmento = []
    for seg in sorted(df_total["segmento"].unique()):
        total_s = df_total[df_total["segmento"] == seg]
        canc_s  = df_canc[df_canc["segmento"] == seg]
        dev_s   = df_dev[df_dev["segmento"] == seg]
        total_q = int(total_s["quantidade"].sum())
        canc_q  = int(canc_s["quantidade"].sum())
        dev_q   = int(dev_s["quantidade"].sum())
        lost_q  = canc_q + dev_q
        canc_sv = round(float(canc_s["valor_liquido"].sum()), 0)
        dev_sv  = round(float(dev_s["valor_liquido"].sum()), 0)
        taxa    = round(lost_q / total_q * 100, 1) if total_q else 0.0
        por_segmento.append({
            "segmento":   seg,
            "canc_qtd":   canc_q,
            "dev_qtd":    dev_q,
            "total_qtd":  lost_q,
            "canc_val":   canc_sv,
            "dev_val":    dev_sv,
            "total_val":  canc_sv + dev_sv,
            "taxa_perda": taxa,
        })
    por_segmento.sort(key=lambda x: -x["taxa_perda"])

    DATA = {
        "kpis": {
            "canc_itens":  canc_itens,
            "canc_valor":  canc_valor,
            "dev_itens":   dev_itens,
            "dev_valor":   dev_valor,
            "total_valor": total_valor,
            "taxa_perda":  taxa_perda,
        },
        "mensal":        mensal,
        "por_vendedor":  por_vendedor,
        "por_categoria": por_categoria,
        "por_segmento":  por_segmento,
    }

    data_json = json.dumps(DATA, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA__", data_json)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK Gerado: {OUT}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
