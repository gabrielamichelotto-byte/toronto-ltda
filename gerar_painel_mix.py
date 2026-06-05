# -*- coding: utf-8 -*-
"""
gerar_painel_mix.py — Toronto LTDA  (v2 — light theme + sidebar + filtros interativos)
"""
import json, sqlite3
import pandas as pd

DB  = "toronto_ltda.db"
OUT = "painel_mix.html"

MESES_PT = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']

def mes_label(ym):
    y, m = ym.split('-')
    return MESES_PT[int(m)-1] + '/' + y[2:]


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toronto LTDA — Mix de Produtos</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="chartjs.min.js"></script>
<style>
/* ── Reset ───────────────────────────────────────────────── */
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;font-family:'Inter',system-ui,-apple-system,sans-serif;background:#f5f0e8;color:#0f172a}

/* ── App shell ───────────────────────────────────────────── */
.app{display:flex;height:100vh;width:100%;overflow:hidden}

/* ── Sidebar ─────────────────────────────────────────────── */
.sidebar{
  width:210px;flex-shrink:0;background:#fff;
  display:flex;flex-direction:column;overflow-y:auto;
  border-right:1px solid #e8e4dc
}

.sb-logo-top{
  padding:22px 14px 18px;text-align:center;
  border-bottom:1px solid #e8e4dc;flex-shrink:0
}
.sb-logo-big{
  height:96px;width:auto;border-radius:10px;
  background:#f5f0e8;padding:6px 16px;
  display:block;margin:0 auto
}

.sb-sec{
  font-size:.57rem;font-weight:700;letter-spacing:1.6px;color:#a09880;
  padding:14px 14px 5px;text-transform:uppercase;flex-shrink:0
}

.sb-nav{padding:0 8px 6px;flex-shrink:0}
.sb-nav a{
  display:flex;align-items:center;gap:9px;
  padding:8px 10px;font-size:.74rem;color:#64748b;text-decoration:none;
  border-left:3px solid transparent;border-radius:0 6px 6px 0;
  transition:all .15s;margin-bottom:2px
}
.sb-nav a:hover{background:#f5f0e8;color:#0f172a}
.sb-nav a.active{
  background:#ede8df;border-left-color:#8a7560;
  color:#3d2e1e;font-weight:600
}
.sb-nav a .icon{font-size:.85rem;flex-shrink:0}

.sb-filters{padding:0 10px 10px;flex:1}
.flt-grp{margin-bottom:11px}
.flt-label{
  display:block;font-size:.6rem;font-weight:700;letter-spacing:.8px;
  color:#a09880;text-transform:uppercase;margin-bottom:5px
}
.flt-sel{
  width:100%;background:#faf8f5;border:1px solid #ddd8ce;border-radius:7px;
  color:#374151;font-size:.72rem;padding:6px 10px;cursor:pointer;
  outline:none;appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%23a09880'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 9px center;padding-right:26px
}
.flt-sel:focus{border-color:#8a7560;outline:none}

.btn-reset{
  display:block;margin:4px 10px 16px;padding:7px 0;
  background:transparent;border:1px solid #ddd8ce;border-radius:7px;
  color:#a09880;font-size:.68rem;cursor:pointer;width:calc(100% - 20px);
  transition:all .15s;letter-spacing:.3px
}
.btn-reset:hover{background:#f5f0e8;color:#3d2e1e;border-color:#8a7560}

.sb-footer{
  padding:10px 14px;border-top:1px solid #e8e4dc;
  font-size:.58rem;color:#b0a890;flex-shrink:0;line-height:1.6
}

/* ── Main ─────────────────────────────────────────────────── */
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}

.topbar{
  background:#fff;border-bottom:1px solid #e8e4dc;
  padding:8px 22px;display:flex;align-items:center;gap:14px;
  flex-shrink:0;box-shadow:0 1px 4px rgba(0,0,0,.05)
}
.topbar-logo{height:46px;width:auto;border-radius:7px;background:#f5f0e8;padding:3px 8px;flex-shrink:0}
.page-title{
  font-size:.92rem;font-weight:700;color:#0f172a;
  display:flex;align-items:center;gap:8px;flex-shrink:0
}
.page-title-badge{
  background:#f5f0e8;border:1px solid #ddd8ce;
  color:#6b5540;font-size:.62rem;padding:2px 9px;
  border-radius:10px;font-weight:600;letter-spacing:.3px
}
.filter-tags{display:flex;gap:6px;flex-wrap:wrap;flex:1}
.tag{
  background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;
  font-size:.62rem;font-weight:600;padding:3px 8px;border-radius:10px;
  display:flex;align-items:center;gap:4px;white-space:nowrap
}
.tag-x{cursor:pointer;opacity:.6;margin-left:2px;font-size:.65rem}
.tag-x:hover{opacity:1}
.topbar-meta{font-size:.62rem;color:#94a3b8;white-space:nowrap;flex-shrink:0;text-align:right;line-height:1.5}

/* ── Content ──────────────────────────────────────────────── */
.content{flex:1;overflow-y:auto;padding:16px 20px;background:#f5f0e8}

/* ── KPIs ─────────────────────────────────────────────────── */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.kpi{
  background:#fff;border-radius:10px;padding:15px 16px;
  box-shadow:0 1px 3px rgba(0,0,0,.07);
  border-top:3px solid var(--ac,#3b82f6)
}
.kpi-label{font-size:.59rem;color:#64748b;text-transform:uppercase;letter-spacing:1px;font-weight:600}
.kpi-value{font-size:1.35rem;font-weight:700;color:#0f172a;margin:4px 0 2px;line-height:1.2}
.kpi-sub{font-size:.63rem;color:#94a3b8}

/* ── Sections ─────────────────────────────────────────────── */
.section{
  background:#fff;border-radius:10px;padding:16px 18px;
  margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)
}
.section-hd{
  font-size:.63rem;font-weight:700;text-transform:uppercase;
  letter-spacing:1.1px;color:#64748b;margin-bottom:13px;
  display:flex;align-items:center;gap:8px;
  padding-bottom:9px;border-bottom:1px solid #f1f5f9
}
.section-hd::before{
  content:'';display:inline-block;width:3px;height:14px;
  background:#3b82f6;border-radius:2px;flex-shrink:0
}

/* ── Abas principais ──────────────────────────────────────── */
.main-tabs{
  display:flex;gap:0;margin-bottom:16px;
  border-bottom:2px solid #e8e4dc;background:#fff;
  border-radius:10px 10px 0 0;padding:0 6px
}
.main-tab{
  background:transparent;border:none;border-bottom:2px solid transparent;
  padding:12px 20px;font-size:.8rem;font-weight:500;color:#94a3b8;
  cursor:pointer;margin-bottom:-2px;transition:all .15s;font-family:inherit;
  white-space:nowrap
}
.main-tab:hover{color:#374151}
.main-tab.active{color:#2c1e0f;font-weight:700;border-bottom-color:#8a7560}

/* ── Tabs internas (dentro de cada seção) ─────────────────── */
.tabs{display:flex;gap:6px;margin-bottom:13px}
.tab{
  border:1px solid #e2e8f0;background:transparent;color:#64748b;
  padding:4px 13px;border-radius:16px;font-size:.69rem;
  cursor:pointer;transition:all .15s;font-family:inherit
}
.tab.active{background:#2c1e0f;border-color:#2c1e0f;color:#fff;font-weight:600}

/* ── Grid ─────────────────────────────────────────────────── */
.g2{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;align-items:start}
.ch{position:relative}

/* ── Table ─────────────────────────────────────────────────── */
table{width:100%;border-collapse:collapse;font-size:.71rem;margin-top:12px}
th{
  color:#64748b;text-transform:uppercase;letter-spacing:.6px;font-size:.6rem;
  padding:6px 10px;border-bottom:2px solid #f1f5f9;text-align:right;font-weight:600
}
th:first-child{text-align:left}
td{padding:7px 10px;border-bottom:1px solid #f8fafc;text-align:right;color:#374151}
td:first-child{text-align:left;color:#0f172a;font-weight:500}
tr:hover td{background:#f8fafc}
tr:last-child td{border-bottom:none}

/* ── Insight ──────────────────────────────────────────────── */
.insight{
  margin-top:11px;padding:10px 14px;
  background:#f8fafc;border:1px solid #e8edf4;
  border-left:3px solid #3b82f6;border-radius:0 7px 7px 0;
  font-size:.7rem;line-height:1.8;color:#475569
}
.insight strong{color:#0f172a}

/* ── Misc ─────────────────────────────────────────────────── */
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px;vertical-align:middle}
.empty{text-align:center;padding:32px 0;color:#94a3b8;font-size:.8rem}

@media(max-width:960px){
  .sidebar{display:none}
  .kpis{grid-template-columns:1fr 1fr}
  .g2{grid-template-columns:1fr}
}
@media(max-width:520px){.kpis{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="app">

<!-- ── Sidebar ──────────────────────────────────────────────── -->
<aside class="sidebar">
  <div class="sb-logo-top">
    <img src="toronto_logo.png" alt="Toronto LTDA" class="sb-logo-big">
  </div>
  <div class="sb-sec">P&aacute;ginas</div>
  <nav class="sb-nav">
    <a href="painel_mix.html" class="active">
      <span class="icon">&#127863;</span> Mix de Produtos
    </a>
    <a href="painel_funil.html">
      <span class="icon">&#128202;</span> Funil de Vendas
    </a>
    <a href="painel_conversao.html">
      <span class="icon">&#128222;</span> Convers&atilde;o
    </a>
    <a href="painel_cancelamentos.html">
      <span class="icon">&#9888;</span> Cancelamentos
    </a>
  </nav>

  <div class="sb-sec">Filtros</div>
  <div class="sb-filters">
    <div class="flt-grp">
      <label class="flt-label">Ano</label>
      <select class="flt-sel" id="f-ano" onchange="onFilter()">
        <option value="">Todos</option>
      </select>
    </div>
    <div class="flt-grp">
      <label class="flt-label">M&ecirc;s</label>
      <select class="flt-sel" id="f-mes" onchange="onFilter()">
        <option value="">Todos</option>
      </select>
    </div>
    <div class="flt-grp">
      <label class="flt-label">Categoria</label>
      <select class="flt-sel" id="f-cat" onchange="onFilter()">
        <option value="">Todas</option>
      </select>
    </div>
    <div class="flt-grp">
      <label class="flt-label">Pa&iacute;s de Origem</label>
      <select class="flt-sel" id="f-pais" onchange="onFilter()">
        <option value="">Todos</option>
      </select>
    </div>
  </div>
  <button class="btn-reset" onclick="resetFilters()">&#8635;&nbsp; Limpar Filtros</button>

  <div class="sb-footer">
    Dados fict&iacute;cios para portf&oacute;lio<br>
    <span id="sb-dt"></span>
  </div>
</aside>

<!-- ── Main ─────────────────────────────────────────────────── -->
<div class="main">

  <div class="topbar">

    <div class="page-title">
      &#127863; Mix de Produtos
      <span class="page-title-badge">An&aacute;lise de Portf&oacute;lio</span>
    </div>
    <div class="filter-tags" id="filter-tags"></div>
    <div class="topbar-meta" id="topbar-meta"></div>
  </div>

  <div class="content">

    <!-- KPIs -->
    <div class="kpis">
      <div class="kpi" style="--ac:#3b82f6">
        <div class="kpi-label">SKUs no Cat&aacute;logo</div>
        <div class="kpi-value" id="kv-skus">—</div>
        <div class="kpi-sub" id="ks-skus"></div>
      </div>
      <div class="kpi" style="--ac:#c0392b">
        <div class="kpi-label">Categoria L&iacute;der</div>
        <div class="kpi-value" id="kv-cat">—</div>
        <div class="kpi-sub" id="ks-cat"></div>
      </div>
      <div class="kpi" style="--ac:#0ea5e9">
        <div class="kpi-label">Pa&iacute;s L&iacute;der</div>
        <div class="kpi-value" id="kv-pais">—</div>
        <div class="kpi-sub" id="ks-pais"></div>
      </div>
      <div class="kpi" style="--ac:#16a34a">
        <div class="kpi-label">Ticket M&eacute;dio / Item</div>
        <div class="kpi-value" id="kv-ticket">—</div>
        <div class="kpi-sub">valor l&iacute;quido m&eacute;dio por unidade</div>
      </div>
    </div>

    <!-- Abas principais -->
    <div class="main-tabs">
      <button class="main-tab active" data-section="cat">&#127863; Mix por Categoria</button>
      <button class="main-tab" data-section="saz">&#128197; Sazonalidade</button>
      <button class="main-tab" data-section="pais">&#127758; Por Pa&iacute;s de Origem</button>
    </div>

    <!-- Seção 1: Por Categoria -->
    <div class="section" id="sec-cat">
      <div class="section-hd">Mix por Categoria</div>
      <div class="tabs" id="tabs-cat">
        <button class="tab active" data-v="val">Faturamento (R$)</button>
        <button class="tab" data-v="qtd">Volume (un.)</button>
        <button class="tab" data-v="sku">SKUs</button>
      </div>
      <div class="g2">
        <div><div class="ch" style="height:210px"><canvas id="c-cat-bar"></canvas></div></div>
        <div><div class="ch" style="height:210px"><canvas id="c-cat-donut"></canvas></div></div>
      </div>
      <table>
        <thead>
          <tr><th>Categoria</th><th>SKUs</th><th>Volume (un.)</th><th>Faturamento</th><th>% Fat.</th><th>Ticket / Item</th></tr>
        </thead>
        <tbody id="cat-tbody"></tbody>
      </table>
      <div class="insight" id="insight-cat"></div>
    </div>

    <!-- Seção 2: Sazonalidade -->
    <div class="section" id="sec-saz" style="display:none">
      <div class="section-hd">Sazonalidade por Categoria</div>
      <div class="tabs" id="tabs-saz">
        <button class="tab active" data-v="val">Faturamento (R$)</button>
        <button class="tab" data-v="qtd">Volume (un.)</button>
      </div>
      <div class="ch" style="height:230px"><canvas id="c-saz"></canvas></div>
      <div class="insight" id="insight-saz"></div>
    </div>

    <!-- Seção 3: Por País -->
    <div class="section" id="sec-pais" style="display:none">
      <div class="section-hd">Por Pa&iacute;s de Origem</div>
      <div class="tabs" id="tabs-pais">
        <button class="tab active" data-v="val">Faturamento (R$)</button>
        <button class="tab" data-v="qtd">Volume (un.)</button>
      </div>
      <div class="g2">
        <div><div class="ch" style="height:260px"><canvas id="c-pais-bar"></canvas></div></div>
        <div><div class="ch" style="height:260px"><canvas id="c-pais-donut"></canvas></div></div>
      </div>
      <table>
        <thead>
          <tr><th>Pa&iacute;s</th><th>SKUs</th><th>Volume (un.)</th><th>Faturamento</th><th>% Fat.</th><th>Ticket / Item</th></tr>
        </thead>
        <tbody id="pais-tbody"></tbody>
      </table>
      <div class="insight" id="insight-pais"></div>
    </div>

  </div><!-- /content -->
</div><!-- /main -->
</div><!-- /app -->

<script>
const D = __DATA__;

// ── Helpers ───────────────────────────────────────────────────────────────────
function brl(v) {
  if (!v || isNaN(v)) return 'R$ 0';
  if (v >= 1e6) return 'R$ ' + (v / 1e6).toFixed(2).replace('.', ',') + 'M';
  if (v >= 1e3) return 'R$ ' + (v / 1e3).toFixed(0) + 'K';
  return 'R$ ' + v.toLocaleString('pt-BR', {minimumFractionDigits:2,maximumFractionDigits:2});
}
function num(v) { return (v || 0).toLocaleString('pt-BR'); }
function pct(v) { return (v || 0).toFixed(1) + '%'; }

const tipBase = {
  backgroundColor:'#fff', borderColor:'#e2e8f0', borderWidth:1,
  titleColor:'#64748b', bodyColor:'#0f172a', padding:10, boxPadding:4,
  mode:'index', intersect:false
};
const sx = {grid:{color:'#f1f5f9'}, ticks:{color:'#94a3b8', font:{size:11}}};
const sy = {grid:{color:'#f1f5f9'}, ticks:{color:'#94a3b8', font:{size:11}}};

const COR_CAT = {
  'Vinho Tinto':'#dc2626','Rosé':'#db2777',
  'Destilado':'#7c3aed','Espumante':'#ea580c','Vinho Branco':'#ca8a04'
};
const COR_PAIS = [
  '#3b82f6','#10b981','#f59e0b','#8b5cf6','#ef4444',
  '#14b8a6','#f97316','#64748b','#ec4899','#84cc16','#06b6d4'
];

// ── Init ──────────────────────────────────────────────────────────────────────
const now = new Date();
const dtStr = now.toLocaleDateString('pt-BR', {day:'2-digit', month:'short', year:'numeric'});
document.getElementById('sb-dt').textContent = dtStr;
document.getElementById('topbar-meta').innerHTML =
  'Atualizado em ' + dtStr + '<br>Apenas pedidos faturados';

// Populate dropdowns
const dim = D.dim;
dim.anos.forEach(a => addOpt('f-ano', a, a));
dim.meses.forEach(m => addOpt('f-mes', m, dim.mes_labels[m]));
dim.categorias.forEach(c => addOpt('f-cat', c, c));
dim.paises.forEach(p => addOpt('f-pais', p, p));

function addOpt(id, val, label) {
  const o = document.createElement('option');
  o.value = val; o.textContent = label;
  document.getElementById(id).appendChild(o);
}

// ── State ─────────────────────────────────────────────────────────────────────
let state = {ano:'', mes:'', categoria:'', pais:''};
let catMode = 'val', sazMode = 'val', paisMode = 'val';
let activeSection = 'cat';
const charts = {};

function destroyChart(key) {
  if (charts[key]) { charts[key].destroy(); delete charts[key]; }
}

// ── Filtering ─────────────────────────────────────────────────────────────────
function getFiltered() {
  return D.raw.filter(r =>
    (!state.ano       || r.ano       === state.ano)       &&
    (!state.mes       || r.mes       === state.mes)       &&
    (!state.categoria || r.categoria === state.categoria) &&
    (!state.pais      || r.pais      === state.pais)
  );
}

function aggByCat(data) {
  const map = {};
  dim.categorias.forEach(c => { map[c] = {volume:0, faturamento:0}; });
  data.forEach(r => {
    map[r.categoria].volume      += r.volume;
    map[r.categoria].faturamento += r.faturamento;
  });
  return dim.categorias
    .map(c => ({
      categoria:   c,
      skus:        D.skus_cat[c] || 0,
      volume:      map[c].volume,
      faturamento: map[c].faturamento,
      ticket:      map[c].volume ? map[c].faturamento / map[c].volume : 0
    }))
    .filter(c => c.faturamento > 0 || c.volume > 0)
    .sort((a, b) => b.faturamento - a.faturamento);
}

function aggByPais(data) {
  const map = {};
  data.forEach(r => {
    if (!map[r.pais]) map[r.pais] = {volume:0, faturamento:0};
    map[r.pais].volume      += r.volume;
    map[r.pais].faturamento += r.faturamento;
  });
  return Object.entries(map)
    .map(([pais, v]) => ({
      pais,
      skus:        D.skus_pais[pais] || 0,
      volume:      v.volume,
      faturamento: v.faturamento,
      ticket:      v.volume ? v.faturamento / v.volume : 0
    }))
    .sort((a, b) => b.faturamento - a.faturamento);
}

function aggByMes(data) {
  const mesMap = {};
  data.forEach(r => { if (!mesMap[r.mes]) mesMap[r.mes] = r.mes_label; });
  const meses  = Object.keys(mesMap).sort();
  const labels = meses.map(m => mesMap[m]);
  const catSet = [...new Set(data.map(r => r.categoria))];
  const catData = {};
  catSet.forEach(c => { catData[c] = {val: new Array(meses.length).fill(0), qtd: new Array(meses.length).fill(0)}; });
  data.forEach(r => {
    const i = meses.indexOf(r.mes);
    if (i >= 0) { catData[r.categoria].val[i] += r.faturamento; catData[r.categoria].qtd[i] += r.volume; }
  });
  return {meses, labels, catData, catSet};
}

function countSkus() {
  return D.skus_detail.filter(s =>
    (!state.categoria || s.categoria === state.categoria) &&
    (!state.pais      || s.pais      === state.pais)
  ).reduce((sum, s) => sum + s.skus, 0);
}

// ── KPIs ──────────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const totalVol = data.reduce((s, r) => s + r.volume, 0);
  const totalFat = data.reduce((s, r) => s + r.faturamento, 0);
  const cats  = aggByCat(data);
  const paises = aggByPais(data);

  document.getElementById('kv-skus').textContent  = countSkus();
  document.getElementById('ks-skus').textContent  = cats.length + ' categorias · ' + paises.length + ' países';
  document.getElementById('kv-cat').textContent   = cats[0]   ? cats[0].categoria  : '—';
  document.getElementById('ks-cat').textContent   = cats[0]   ? brl(cats[0].faturamento) + ' faturados' : '';
  document.getElementById('kv-pais').textContent  = paises[0] ? paises[0].pais      : '—';
  document.getElementById('ks-pais').textContent  = paises[0] ? brl(paises[0].faturamento) + ' faturados' : '';
  document.getElementById('kv-ticket').textContent = totalVol  ? brl(totalFat / totalVol) : '—';
}

// ── Categoria Charts ──────────────────────────────────────────────────────────
function renderCat(data, mode) {
  const cats  = aggByCat(data);
  const isVal = mode === 'val', isSku = mode === 'sku';
  const vals  = cats.map(c => isSku ? c.skus : isVal ? c.faturamento : c.volume);
  const label = isSku ? 'SKUs' : isVal ? 'Faturamento' : 'Volume (un.)';
  const total = vals.reduce((s, v) => s + v, 0);

  if (!cats.length) {
    ['cat-bar','cat-donut'].forEach(k => destroyChart(k));
    document.getElementById('cat-tbody').innerHTML = '<tr><td colspan="6" class="empty">Nenhum dado para os filtros selecionados</td></tr>';
    document.getElementById('insight-cat').innerHTML = '';
    return;
  }

  destroyChart('cat-bar');
  charts['cat-bar'] = new Chart('c-cat-bar', {
    type: 'bar',
    data: {
      labels: cats.map(c => c.categoria),
      datasets: [{
        label,
        data: vals,
        backgroundColor: cats.map(c => COR_CAT[c.categoria] || '#64748b'),
        borderRadius: 5, borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        tooltip: {...tipBase, callbacks: {label: c => ` ${label}: ${isSku ? c.parsed.x : isVal ? brl(c.parsed.x) : num(c.parsed.x)}`}}
      },
      scales: {
        x: {...sx, ticks: {color:'#94a3b8', callback: v => isVal ? brl(v) : v}},
        y: {...sy, grid: {display: false}}
      }
    }
  });

  destroyChart('cat-donut');
  charts['cat-donut'] = new Chart('c-cat-donut', {
    type: 'doughnut',
    data: {
      labels: cats.map(c => c.categoria),
      datasets: [{
        data: vals,
        backgroundColor: cats.map(c => COR_CAT[c.categoria] || '#64748b'),
        borderWidth: 2, borderColor: '#fff', hoverOffset: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '62%',
      plugins: {
        legend: {position: 'bottom', labels: {color:'#64748b', boxWidth:12, padding:10, font:{size:11}}},
        tooltip: {
          ...tipBase,
          callbacks: {label: c => {
            const p = total ? (c.parsed / total * 100).toFixed(1) : '0.0';
            return ` ${c.label}: ${isSku ? c.parsed : isVal ? brl(c.parsed) : num(c.parsed)} (${p}%)`;
          }}
        }
      }
    }
  });

  const fatTotal = cats.reduce((s, c) => s + c.faturamento, 0);
  document.getElementById('cat-tbody').innerHTML = cats.map(c => {
    const fp = fatTotal ? (c.faturamento / fatTotal * 100).toFixed(1) : '0.0';
    const cor = COR_CAT[c.categoria] || '#64748b';
    return `<tr>
      <td><span class="dot" style="background:${cor}"></span>${c.categoria}</td>
      <td>${c.skus}</td>
      <td>${num(c.volume)}</td>
      <td style="font-weight:600">${brl(c.faturamento)}</td>
      <td>${fp}%</td>
      <td>${brl(c.ticket)}</td>
    </tr>`;
  }).join('');

  const lider   = cats[0];
  const topTick = cats.reduce((a, b) => b.ticket > a.ticket ? b : a, cats[0]);
  document.getElementById('insight-cat').innerHTML =
    `<strong>🏆 Categoria líder:</strong> <strong>${lider.categoria}</strong> — <strong>${brl(lider.faturamento)}</strong>
    (${pct(lider.faturamento / (fatTotal||1) * 100)} do total), ${lider.skus} SKUs, ${num(lider.volume)} unidades.
    &nbsp;·&nbsp;
    <strong>💰 Maior ticket/item:</strong> <strong>${topTick.categoria}</strong> — <strong>${brl(topTick.ticket)}</strong>/un.`;
}

// ── Sazonalidade Chart ────────────────────────────────────────────────────────
function renderSaz(data, mode) {
  const {meses, labels, catData, catSet} = aggByMes(data);
  const isVal = mode === 'val';

  destroyChart('saz');
  if (!meses.length) {
    document.getElementById('insight-saz').innerHTML = '';
    return;
  }

  charts['saz'] = new Chart('c-saz', {
    type: 'bar',
    data: {
      labels,
      datasets: catSet.map(cat => ({
        label: cat,
        data:  isVal ? catData[cat].val : catData[cat].qtd,
        backgroundColor: COR_CAT[cat] || '#64748b',
        stack: 'stack', borderWidth: 0
      }))
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {position:'top', labels:{color:'#64748b', boxWidth:12, padding:12, font:{size:11}}},
        tooltip: {...tipBase, callbacks:{label: c => ` ${c.dataset.label}: ${isVal ? brl(c.parsed.y) : num(c.parsed.y)}`}}
      },
      scales: {
        x: {...sx, stacked:true, ticks:{color:'#94a3b8', maxRotation:45, font:{size:10}}},
        y: {...sy, stacked:true, ticks:{color:'#94a3b8', callback: v => isVal ? brl(v) : v}}
      }
    }
  });

  const totais  = labels.map((_, i) => catSet.reduce((s, c) => s + (isVal ? catData[c].val[i] : catData[c].qtd[i]), 0));
  const maxIdx  = totais.indexOf(Math.max(...totais));
  const minIdx  = totais.indexOf(Math.min(...totais));
  const avg     = totais.reduce((s, v) => s + v, 0) / totais.length;
  document.getElementById('insight-saz').innerHTML =
    `<strong>📅 Pico sazonal:</strong> <strong>${labels[maxIdx]}</strong> — ${isVal ? brl(totais[maxIdx]) : num(totais[maxIdx])},
    <strong>${pct((totais[maxIdx] / avg - 1) * 100)}</strong> acima da média mensal.
    &nbsp;·&nbsp; Menor mês: <strong>${labels[minIdx]}</strong>.
    O portfólio mantém todas as categorias ao longo do ano, com aceleração consistente no segundo semestre.`;
}

// ── País Charts ───────────────────────────────────────────────────────────────
function renderPais(data, mode) {
  const paises = aggByPais(data);
  const isVal  = mode === 'val';
  const vals   = paises.map(p => isVal ? p.faturamento : p.volume);
  const label  = isVal ? 'Faturamento' : 'Volume (un.)';
  const total  = vals.reduce((s, v) => s + v, 0);

  if (!paises.length) {
    ['pais-bar','pais-donut'].forEach(k => destroyChart(k));
    document.getElementById('pais-tbody').innerHTML = '<tr><td colspan="6" class="empty">Nenhum dado para os filtros selecionados</td></tr>';
    document.getElementById('insight-pais').innerHTML = '';
    return;
  }

  destroyChart('pais-bar');
  charts['pais-bar'] = new Chart('c-pais-bar', {
    type: 'bar',
    data: {
      labels: paises.map(p => p.pais),
      datasets: [{
        label,
        data: vals,
        backgroundColor: paises.map((_, i) => COR_PAIS[i % COR_PAIS.length]),
        borderRadius: 5, borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        tooltip: {...tipBase, callbacks:{label: c => ` ${label}: ${isVal ? brl(c.parsed.x) : num(c.parsed.x)}`}}
      },
      scales: {
        x: {...sx, ticks:{color:'#94a3b8', callback: v => isVal ? brl(v) : v}},
        y: {...sy, grid:{display:false}}
      }
    }
  });

  destroyChart('pais-donut');
  charts['pais-donut'] = new Chart('c-pais-donut', {
    type: 'doughnut',
    data: {
      labels: paises.map(p => p.pais),
      datasets: [{
        data: vals,
        backgroundColor: paises.map((_, i) => COR_PAIS[i % COR_PAIS.length]),
        borderWidth: 2, borderColor:'#fff', hoverOffset: 6
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout:'58%',
      plugins: {
        legend: {position:'bottom', labels:{color:'#64748b', boxWidth:10, padding:8, font:{size:10}}},
        tooltip: {
          ...tipBase,
          callbacks:{label: c => {
            const p = total ? (c.parsed / total * 100).toFixed(1) : '0.0';
            return ` ${c.label}: ${isVal ? brl(c.parsed) : num(c.parsed)} (${p}%)`;
          }}
        }
      }
    }
  });

  const fatTotal = paises.reduce((s, p) => s + p.faturamento, 0);
  document.getElementById('pais-tbody').innerHTML = paises.map((p, i) => {
    const fp = fatTotal ? (p.faturamento / fatTotal * 100).toFixed(1) : '0.0';
    return `<tr>
      <td><span class="dot" style="background:${COR_PAIS[i % COR_PAIS.length]}"></span>${p.pais}</td>
      <td>${p.skus}</td>
      <td>${num(p.volume)}</td>
      <td style="font-weight:600">${brl(p.faturamento)}</td>
      <td>${fp}%</td>
      <td>${brl(p.ticket)}</td>
    </tr>`;
  }).join('');

  const lider   = paises[0];
  const top3fat = paises.slice(0, 3).reduce((s, p) => s + p.faturamento, 0);
  const top3nm  = paises.slice(0, 3).map(p => p.pais).join(', ');
  document.getElementById('insight-pais').innerHTML =
    `<strong>🌍 País líder:</strong> <strong>${lider.pais}</strong> — <strong>${brl(lider.faturamento)}</strong>
    (${pct(lider.faturamento / (fatTotal||1) * 100)}), ${lider.skus} SKUs, ticket ${brl(lider.ticket)}/un.
    &nbsp;·&nbsp;
    <strong>Top 3</strong> (${top3nm}): <strong>${pct(top3fat / (fatTotal||1) * 100)}</strong> do faturamento.`;
}

// ── Switch main tab ───────────────────────────────────────────────────────────
function switchTab(sec) {
  activeSection = sec;
  document.querySelectorAll('.main-tab').forEach(b => b.classList.remove('active'));
  document.querySelector(`.main-tab[data-section="${sec}"]`).classList.add('active');
  ['cat','saz','pais'].forEach(s => {
    document.getElementById('sec-' + s).style.display = s === sec ? '' : 'none';
  });
  const data = getFiltered();
  if (sec === 'cat')  renderCat(data, catMode);
  if (sec === 'saz')  renderSaz(data, sazMode);
  if (sec === 'pais') renderPais(data, paisMode);
}

document.querySelectorAll('.main-tab').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.section));
});

// ── Render all ────────────────────────────────────────────────────────────────
function renderAll() {
  const data = getFiltered();
  renderKPIs(data);
  if (activeSection === 'cat')  renderCat(data, catMode);
  if (activeSection === 'saz')  renderSaz(data, sazMode);
  if (activeSection === 'pais') renderPais(data, paisMode);
  updateTags();
}

// ── Filter tags ───────────────────────────────────────────────────────────────
const TAG_LABELS = {ano:'Ano', mes:'Mês', categoria:'Categoria', pais:'País'};
function updateTags() {
  document.getElementById('filter-tags').innerHTML = Object.entries(state)
    .filter(([, v]) => v)
    .map(([k, v]) => {
      const disp = k === 'mes' ? dim.mes_labels[v] || v : v;
      return `<span class="tag">${TAG_LABELS[k]}: <strong>${disp}</strong>
        <span class="tag-x" onclick="clearFilter('${k}')">✕</span></span>`;
    }).join('');
}

function clearFilter(key) {
  state[key] = '';
  const elId = {ano:'f-ano', mes:'f-mes', categoria:'f-cat', pais:'f-pais'}[key];
  document.getElementById(elId).value = '';
  renderAll();
}

// ── Filter interaction ────────────────────────────────────────────────────────
function onFilter() {
  state.ano       = document.getElementById('f-ano').value;
  state.mes       = document.getElementById('f-mes').value;
  state.categoria = document.getElementById('f-cat').value;
  state.pais      = document.getElementById('f-pais').value;

  // Refresh month options for selected year
  const mesEl  = document.getElementById('f-mes');
  const curMes = mesEl.value;
  const avail  = [...new Set(
    D.raw.filter(r => !state.ano || r.ano === state.ano).map(r => r.mes)
  )].sort();
  mesEl.innerHTML = '<option value="">Todos</option>';
  avail.forEach(m => {
    const o = document.createElement('option');
    o.value = m; o.textContent = dim.mes_labels[m] || m;
    if (m === curMes) o.selected = true;
    mesEl.appendChild(o);
  });
  if (!avail.includes(curMes)) state.mes = '';

  renderAll();
}

function resetFilters() {
  state = {ano:'', mes:'', categoria:'', pais:''};
  ['f-ano','f-mes','f-cat','f-pais'].forEach(id => { document.getElementById(id).value = ''; });
  const mesEl = document.getElementById('f-mes');
  mesEl.innerHTML = '<option value="">Todos</option>';
  dim.meses.forEach(m => {
    const o = document.createElement('option');
    o.value = m; o.textContent = dim.mes_labels[m] || m;
    mesEl.appendChild(o);
  });
  renderAll();
}

// ── Tab handlers ──────────────────────────────────────────────────────────────
document.querySelectorAll('#tabs-cat .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-cat .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    catMode = btn.dataset.v;
    renderCat(getFiltered(), catMode);
  });
});
document.querySelectorAll('#tabs-saz .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-saz .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    sazMode = btn.dataset.v;
    renderSaz(getFiltered(), sazMode);
  });
});
document.querySelectorAll('#tabs-pais .tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#tabs-pais .tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    paisMode = btn.dataset.v;
    renderPais(getFiltered(), paisMode);
  });
});

// ── Boot ──────────────────────────────────────────────────────────────────────
renderAll();
</script>
</body>
</html>"""


def main():
    conn = sqlite3.connect(DB)

    df = pd.read_sql("""
        SELECT
            substr(p.data_pedido, 1, 4) AS ano,
            substr(p.data_pedido, 1, 7) AS mes,
            pr.categoria,
            pr.pais_origem AS pais,
            SUM(p.quantidade)           AS volume,
            ROUND(SUM(p.valor_liquido), 2) AS faturamento
        FROM fato_pedidos p
        JOIN dim_produtos pr ON p.id_produto = pr.id_produto
        WHERE p.status_pedido = 'Faturado'
        GROUP BY ano, mes, pr.categoria, pr.pais_origem
        ORDER BY mes, categoria, pais
    """, conn)

    df_skus_d = pd.read_sql("""
        SELECT categoria, pais_origem AS pais, COUNT(DISTINCT id_produto) AS skus
        FROM dim_produtos GROUP BY categoria, pais_origem
    """, conn)
    df_skus_c = pd.read_sql("""
        SELECT categoria, COUNT(DISTINCT id_produto) AS skus
        FROM dim_produtos GROUP BY categoria
    """, conn)
    df_skus_p = pd.read_sql("""
        SELECT pais_origem AS pais, COUNT(DISTINCT id_produto) AS skus
        FROM dim_produtos GROUP BY pais_origem
    """, conn)
    conn.close()

    # Ordered dimensions (by total faturamento)
    cats_ord  = (df.groupby("categoria")["faturamento"].sum()
                   .sort_values(ascending=False).index.tolist())
    paises_ord = (df.groupby("pais")["faturamento"].sum()
                    .sort_values(ascending=False).index.tolist())
    anos   = sorted(df["ano"].unique().tolist())
    meses  = sorted(df["mes"].unique().tolist())

    raw = [
        {
            "ano":         row["ano"],
            "mes":         row["mes"],
            "mes_label":   mes_label(row["mes"]),
            "categoria":   row["categoria"],
            "pais":        row["pais"],
            "volume":      int(row["volume"]),
            "faturamento": round(float(row["faturamento"]), 2),
        }
        for _, row in df.iterrows()
    ]

    DATA = {
        "raw": raw,
        "dim": {
            "anos":       anos,
            "meses":      meses,
            "mes_labels": {m: mes_label(m) for m in meses},
            "categorias": cats_ord,
            "paises":     paises_ord,
        },
        "skus_cat":    {r["categoria"]: int(r["skus"]) for _, r in df_skus_c.iterrows()},
        "skus_pais":   {r["pais"]:      int(r["skus"]) for _, r in df_skus_p.iterrows()},
        "skus_detail": [
            {"categoria": r["categoria"], "pais": r["pais"], "skus": int(r["skus"])}
            for _, r in df_skus_d.iterrows()
        ],
    }

    data_json = json.dumps(DATA, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA__", data_json)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK Gerado: {OUT}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
