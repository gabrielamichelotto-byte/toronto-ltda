# -*- coding: utf-8 -*-
import json, re, sqlite3
from collections import Counter

print('=' * 60)
print('AUDITORIA COMPLETA — Toronto LTDA Dashboard')
print('=' * 60)

with open('dashboard.html', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'const D = ({.*?});', html, re.DOTALL)
data = json.loads(m.group(1))
conn = sqlite3.connect('toronto_ltda.db')
erros = []

# 1. Chaves do data dict
esperado = ['kpis','fat_mensal','categorias','regioes','top10','vendedores',
            'funil','inadimplencia','segmentos','ticket_detalhe','inad_detalhe',
            'fat_detalhe','margem_detalhe','cli_detalhe','desc_detalhe',
            'metas_detalhe','abc_detalhe','giro_detalhe','conv_detalhe','estoque_detalhe']
faltando = [k for k in esperado if k not in data]
ok = not faltando
print(f'[1]  Chaves data dict   : {"OK" if ok else "FALTA: "+str(faltando)}')
if not ok: erros.append('chaves')

# 2. KPIs principais
k = data['kpis']
ok = all([k['fat_total']>0, k['media_mensal']>0, k['ticket']>0,
          k['pedidos']>0, k['clientes']>0,
          0<k['inadimplencia']<100, 0<k['margem']<100, 0<=k['desc_medio']<100])
print(f'[2]  KPIs principais    : {"OK" if ok else "ERRO"}')
print(f'     fat={k["fat_total"]:,.0f}  ticket={k["ticket"]:,.0f}  cli={k["clientes"]}  inad={k["inadimplencia"]}%  mg={k["margem"]}%')
if not ok: erros.append('kpis')

# 3. fat_mensal
fm = data['fat_mensal']
ok = (len(fm['labels'])==len(fm['fat'])==len(fm['pedidos'])
      and len(fm['labels'])>=24 and all(v>0 for v in fm['fat']))
print(f'[3]  fat_mensal         : {"OK" if ok else "ERRO"} ({len(fm["labels"])} meses)')
if not ok: erros.append('fat_mensal')

# 4. Categorias / Regiões
ok_c = len(data['categorias']['labels'])==5 and all(v>0 for v in data['categorias']['valores'])
ok_r = len(data['regioes']['labels'])>=3 and all(v>0 for v in data['regioes']['valores'])
print(f'[4]  Categorias         : {"OK" if ok_c else "ERRO"} ({len(data["categorias"]["labels"])} cats)')
print(f'[4]  Regioes            : {"OK" if ok_r else "ERRO"} ({len(data["regioes"]["labels"])} regioes)')
if not ok_c: erros.append('categorias')
if not ok_r: erros.append('regioes')

# 5. ticket_detalhe
td = data['ticket_detalhe']
td_status = set(r['status'] for r in td)
ok = ({'Faturado','Cancelado','Devolvido'} <= td_status
      and all(r['ticket']>0 for r in td if r['status']=='Faturado'))
print(f'[5]  ticket_detalhe     : {"OK" if ok else "ERRO"} (status={td_status})')
if not ok: erros.append('ticket_detalhe')

# 6. inad_detalhe
id2 = data['inad_detalhe']
ok = (len(id2['mensal'])>=24
      and all(0<=r['taxa']<=100 for r in id2['mensal'])
      and len(id2['segmentos'])==6)
print(f'[6]  inad_detalhe       : {"OK" if ok else "ERRO"} ({len(id2["mensal"])} meses, {len(id2["segmentos"])} segs)')
if not ok: erros.append('inad_detalhe')

# 7. fat_detalhe
fd = data['fat_detalhe']
ok = (len(set(r['categoria'] for r in fd['categorias']))==5
      and len(set(r['regiao'] for r in fd['regioes']))>=3
      and all(r['fat']>0 for r in fd['categorias']))
print(f'[7]  fat_detalhe        : {"OK" if ok else "ERRO"}')
if not ok: erros.append('fat_detalhe')

# 8. margem_detalhe
md = data['margem_detalhe']
ok = (len(md['categorias'])==5
      and all(r['margem_pct']>0 for r in md['categorias'])
      and len(md['vendedores'])==8)
print(f'[8]  margem_detalhe     : {"OK" if ok else "ERRO"} ({len(md["categorias"])} cats, {len(md["vendedores"])} vends)')
if not ok: erros.append('margem_detalhe')

# 9. cli_detalhe
cd = data['cli_detalhe']
ok = (len(cd['segmentos'])==6 and len(cd['regioes'])>=3
      and len(cd['ativos_mes'])>=24 and len(cd['top_inativos'])>0
      and all(r['pct_ativo']>=0 for r in cd['segmentos']))
print(f'[9]  cli_detalhe        : {"OK" if ok else "ERRO"} (top_inativos={len(cd["top_inativos"])})')
if not ok: erros.append('cli_detalhe')

# 10. desc_detalhe
dd = data['desc_detalhe']
ok = (len(dd['vendedores'])==8
      and all(r['desc_medio']>=0 for r in dd['vendedores'])
      and len(dd['segmentos'])==6
      and dd['margem_sem_desc']>dd['margem_com_desc'])
print(f'[10] desc_detalhe       : {"OK" if ok else "ERRO"} (mg s/desc={dd["margem_sem_desc"]}% c/desc={dd["margem_com_desc"]}%)')
if not ok: erros.append('desc_detalhe')

# 11. metas_detalhe
mdt = data['metas_detalhe']
anos = set(r['ano'] for r in mdt['anual'])
ok = (len(mdt['mensal_avg'])==8
      and all(r['ating_pct']>0 for r in mdt['mensal_avg'])
      and len(mdt['bimestral'])>=12 and len(anos)>=2)
print(f'[11] metas_detalhe      : {"OK" if ok else "ERRO"} (vends={len(mdt["mensal_avg"])}, bim={len(mdt["bimestral"])}, anos={anos})')
if not ok: erros.append('metas_detalhe')

# 12. abc_detalhe
ab = data['abc_detalhe']
cumuls = [r['cumul_pct'] for r in ab['curva']]
ok = (ab['n_total']>0 and ab['rec_risco']>0 and ab['n_classe_a']>0
      and all(r['classe'] in ['A','B','C'] for r in ab['curva'])
      and all(cumuls[i]<=cumuls[i+1] for i in range(len(cumuls)-1)))
print(f'[12] abc_detalhe        : {"OK" if ok else "ERRO"} (n={ab["n_total"]}, A={ab["n_classe_a"]}, risco=R${ab["rec_risco"]:,.0f})')
if not ok: erros.append('abc_detalhe')

# 13. conv_detalhe
cv = data['conv_detalhe']
total_cv = sum(r['n'] for r in cv['perfil'])
ok = (cv['n_inadimpl']>0 and total_cv==cv['n_inadimpl']
      and len(cv['evolucao'])>=24
      and all(r['taxa_inad']>=0 for r in cv['evolucao']))
print(f'[13] conv_detalhe       : {"OK" if ok else "ERRO"} (inadimpl={cv["n_inadimpl"]}, evo={len(cv["evolucao"])} meses)')
if not ok: erros.append('conv_detalhe')

# 14. giro_detalhe
gd = data['giro_detalhe']
ok = (len(gd['scatter'])>0
      and all(r['recencia_dias']>=0 for r in gd['scatter'])
      and sum(r['n'] for r in gd['hist_rec'])==cv['n_inadimpl'] or True  # hist vs todos clientes
      and gd['med_rec']>=0 and gd['corte_rec']>=0)
n_hist = sum(r['n'] for r in gd['hist_rec'])
n_cli_db = conn.execute("SELECT COUNT(DISTINCT id_cliente) FROM fato_pedidos WHERE status_pedido='Faturado'").fetchone()[0]
ok = (all(r['recencia_dias']>=0 for r in gd['scatter'])
      and n_hist==n_cli_db and gd['corte_rec']>=0)
print(f'[14] giro_detalhe       : {"OK" if ok else "ERRO"} (scatter={len(gd["scatter"])}, hist={n_hist} vs DB={n_cli_db})')
if not ok: erros.append('giro_detalhe')

# 15. estoque_detalhe
ed = data['estoque_detalhe']
ok = (len(ed['produtos'])==120
      and all(p['cobertura_dias']>=0 for p in ed['produtos'])
      and all(p['giro']>=0 for p in ed['produtos'])
      and set(p['status'] for p in ed['produtos']) <= {'Critico','Atencao','Ok','Parado',
                                                        'Crítico','Atenção'})
dist_est = dict(Counter(p['status'] for p in ed['produtos']))
print(f'[15] estoque_detalhe    : {"OK" if ok else "ERRO"} {dist_est}  cob_med={ed["cob_media"]}d  criticos={ed["n_critico"]}')
if not ok: erros.append('estoque_detalhe')

# 16. Consistência cruzada DB × HTML
fat_db   = conn.execute("SELECT ROUND(SUM(valor_liquido),0) FROM fato_pedidos WHERE status_pedido='Faturado'").fetchone()[0]
ok = abs(fat_db - round(data['kpis']['fat_total'],0)) < 1000
print(f'[16] Fat DB×HTML        : {"OK" if ok else "DIVERGENCIA"} (DB={fat_db:,.0f} HTML={data["kpis"]["fat_total"]:,.0f})')
if not ok: erros.append('fat cross')

cli_db = conn.execute("SELECT COUNT(*) FROM dim_clientes WHERE status='Ativo'").fetchone()[0]
ok = cli_db == data['kpis']['clientes']
print(f'[16] Clientes DB×HTML   : {"OK" if ok else "DIVERGENCIA"} (DB={cli_db} HTML={data["kpis"]["clientes"]})')
if not ok: erros.append('clientes cross')

inad_db = conn.execute("SELECT ROUND(100.0*SUM(CASE WHEN status_titulo='Vencido' THEN 1 ELSE 0 END)/COUNT(*),1) FROM fato_financeiro").fetchone()[0]
ok = abs(inad_db - data['kpis']['inadimplencia']) < 0.5
print(f'[16] Inad DB×HTML       : {"OK" if ok else "DIVERGENCIA"} (DB={inad_db}% HTML={data["kpis"]["inadimplencia"]}%)')
if not ok: erros.append('inad cross')

# 17. HTML — IDs críticos
ids_esperados = [
    'kpi-fat','kpi-ticket','kpi-cli','kpi-inad','kpi-margem','kpi-desc',
    'kpi-estoque','kpi-giro','kpi-conv','kpi-abc',
    'modal-margem','modal-fat','modal-inad','modal-ticket','modal-metas',
    'modal-desc','modal-cli','modal-estoque','modal-giro','modal-conv','modal-abc',
    'c1','c2','c3','c4','c5','c6','c7','c8',
    'c-margem','c-fat','c-inad','c-tm','c-metas','c-desc','c-cli',
    'c-est','c-giro','c-conv','c-abc',
]
ids_faltando = [i for i in ids_esperados if f'id="{i}"' not in html]
ok = not ids_faltando
print(f'[17] HTML IDs criticos  : {"OK" if ok else "FALTA: "+str(ids_faltando)}')
if not ok: erros.append('html ids: '+str(ids_faltando))

# 18. Tamanho
size_kb = len(html.encode())//1024
print(f'[18] Tamanho HTML       : {size_kb} KB {"OK" if size_kb<600 else "GRANDE"}')

conn.close()
print()
print('=' * 60)
if erros:
    print(f'ERROS ({len(erros)}): {erros}')
else:
    print('TUDO OK — pronto para publicar')
print('=' * 60)
