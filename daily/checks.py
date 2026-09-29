from load import *
import csv, re, os, datetime
PKT=datetime.date.fromisoformat(os.environ.get('PKT_DATE','2026-09-23'))
PKT_US=f'{PKT.month}/{PKT.day}/{PKT:%y}'
from collections import defaultdict, Counter
# normalize SE24 feeder names
for r in frm_rows:
    r['feeders']={k.replace('Extruder ',''):v for k,v in r['feeders'].items()}
    r['columns']=[c.replace('Extruder ','') for c in r['columns']]
issues=[]   # (severity, document, line, order, check, detail, source)
def add(sev,doc,line,order,check,detail,src=''):
    issues.append({'Severity':sev,'Document':doc,'Line':line,'Order':order,'Check':check,'Detail':detail,'Source':src})

# 0. EXT vs verified truth
T={t['order']:t for t in csv.DictReader(open(config.TRUTH_CSV,encoding='utf-8',newline=''))}
for r in ext_rows:
    t=T.get(r['order']); mat,grade,spec=(r['mat_spec'].split()+['','',''])[:3]
    if not t: print('not in truth',r['order']); continue
    for k,v in [('prod',r['prod_code']),('die',r['die']),('mat',mat),('grade',grade),('spec',spec),('colors',r['colors']),('thk',r['thk']),('gsm',r['gsm'].replace(',',''))]:
        if v!=t[k]: print('TRUTH MISMATCH',r['order'],k,v,t[k])

# 1. EXT internal
bytline=defaultdict(list)
for r in ext_rows: bytline[r['line']].append(r)
line_totals={}
for p in EXT:
    if p.get('line_total_pcs'): line_totals[p['line']]=(num(p['line_total_pcs']),num(p['line_total_lbs']),p['scan_page'])
for ln,rows in bytline.items():
    pcs=sum(num(c['total_sheets']) or 0 for r in rows for c in r['cut_rows']); lbs=sum(num(r['weight_lbs']) or 0 for r in rows)
    if ln in line_totals:
        tp,tl,sp=line_totals[ln]
        ok=(pcs==tp and lbs==tl)
        if not ok: add('High','EXT',ln,'','R9 line-total checksum',f'read {pcs:,.0f} PCs / {lbs:,.0f} LBs vs printed {tp:,.0f} / {tl:,.0f}',f'scan p{sp}')
    else:
        # no printed total for this line (its last report page is missing from the scan): use the Final Total
        ft=next((p['final_total'] for p in EXT if p.get('final_total')),'')
        m=re.search(r'([\d,]+)\s*PCs\s*/\s*([\d,]+)\s*LBs',ft)
        if m:
            fp,fl=num(m.group(1)),num(m.group(2))
            op=sum(v[0] for k,v in line_totals.items()); ol=sum(v[1] for k,v in line_totals.items())
            ep,el=fp-op,fl-ol
            if pcs==ep and lbs==el:
                add('Info','EXT',ln,'','R9 line-total checksum',f'No {ln} line total in the scan (a report page is missing). Rows read: {pcs:,.0f} PCs / {lbs:,.0f} LBs, exactly what the printed Final Total leaves for {ln}, so nothing is missing.','scan p16')
            else:
                add('High' if lbs!=el else 'Medium','EXT',ln,'','R9 line-total checksum (via Final Total)',f'No {ln} line total in the scan (a report page is missing). The Final Total leaves {ep:,.0f} PCs / {el:,.0f} LBs for {ln}; rows read give {pcs:,.0f} / {lbs:,.0f} (gap {ep-pcs:,.0f} PCs / {el-lbs:,.0f} LBs). '+('LBs match, so no order is missing: the gap is cut rows printed on the missing page.' if lbs==el else 'An order may be missing.'),'scan p13, p16')
        else:
            add('Medium','EXT',ln,'','R9 line-total checksum',f'No {ln} line total and no Final Total to check against. Rows read: {pcs:,.0f} PCs / {lbs:,.0f} LBs.','')
for r in ext_rows:
    if r.get('truncated'):
        add('Medium','EXT',r['line'],r['order'],'Record cut off by missing page',f"Only {len(r['cut_rows'])} cut row(s) printed on scan p{r['scan_page']}; the rest of the record (more cut rows, special instructions) is on a report page missing from the scan. Pallet and weight checks skipped for this order.",f"scan p{r['scan_page']}")
        if r['handwritten']: add('Info','EXT',r['line'],r['order'],'Handwriting on printout',r['handwritten'],f"scan p{r['scan_page']}")
        continue
    sheets=sum(num(c['total_sheets']) or 0 for c in r['cut_rows'])
    plt,pcs,stk=num(r['num_plt']),num(r['pcs_per_stack']),num(r['stk_per_plt'])
    src=f"scan p{r['scan_page']}"
    if plt and pcs and stk:
        need=sheets/(pcs*stk)
        if plt==999 and need>999.5:
            add('High','EXT',r['line'],r['order'],'# Plt field capped at 999',f'Printed 999 pallets but {sheets:,.0f} sheets / ({pcs:.0f}x{stk:.0f}) = {need:,.1f} pallets. '+(f"Handwritten correction: {r['handwritten']}" if r['handwritten'] else 'No hand correction.'),src)
        elif abs(plt*pcs*stk-sheets)>0 and plt!=999 and abs(need-plt)>=0.01:
            add('Low','EXT',r['line'],r['order'],'Pallets x pcs/stack x stacks vs sheets',f'{plt:.0f} x {pcs:.0f} x {stk:.0f} = {plt*pcs*stk:,.0f} vs {sheets:,.0f} sheets (diff {sheets-plt*pcs*stk:+,.0f})',src)
    # GSM vs instruction range
    m=re.search(r'RANGE(?:\s+IS|\s+WEIGHT)?\s*(\d{3,4})\s*-\s*(\d{3,4})',r['special_instructions'].replace(',',''),re.I)
    g=num(r['gsm'])
    if m and g and not (int(m.group(1))<=g<=int(m.group(2))):
        mid=(int(m.group(1))+int(m.group(2)))/2
        add('Medium','EXT',r['line'],r['order'],'GSM vs special-instruction weight range',f'Printed GSM {g:.0f} but instruction says range {m.group(1)}-{m.group(2)} GSM (printed GSM is {g/mid-1:+.1%} vs the middle of the range; every VOIDFORM order with a range shows the same ~7% gap, so it looks systematic - which target does the floor run to?)',src)
    # weight plausibility: order size x sheets x gsm
    ow,ol=frac(r['order_width']),frac(r['order_length'])
    if ow and ol and g and num(r['weight_lbs']):
        est=sheets*ow*ol*0.00064516*g/453.592
        ratio=num(r['weight_lbs'])/est
        if abs(ratio-1)>0.03: add('Medium','EXT',r['line'],r['order'],'Weight vs sheets x order size x GSM',f'printed {num(r["weight_lbs"]):,.0f} lb vs calculated {est:,.0f} lb (ratio {ratio:.3f})',src)
    if r['handwritten']: add('Info','EXT',r['line'],r['order'],'Handwriting on printout',r['handwritten'],src)
# dates in the past
MON={m:i for i,m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)}
def past(d):
    m=re.fullmatch(r'(\d{1,2})-([A-Za-z]{3})',d.strip()) if d else None
    if not m: return None
    return (MON[m.group(2).title()],int(m.group(1)))<(PKT.month,PKT.day)
for r in ext_rows:
    if past(r['instr_date']): add('Low','EXT',r['line'],r['order'],'In-str date before run date',f"In-str {r['instr_date']} (run {PKT_US})",f"scan p{r['scan_page']}")
# duplicate identical big stock orders
for p in EXT:
    if p.get('page_notes'): pass

# 2. EXT vs FRM
frm_orders=defaultdict(set)
for f in frm_rows:
    for o in f['orders']: frm_orders[f['line']].add(o)
ext_by_order={r['order']:r for r in ext_rows}
for ln,rows in bytline.items():
    eo={r['order'] for r in rows}; fo=frm_orders.get(ln,set())
    for o in sorted(eo-fo): add('High','EXT vs FRM',ln,o,'Order has no formulation',f'{o} is on the extrusion schedule for {ln} but not on the {ln} formulation page','')
    for o in sorted(fo-eo): add('Medium','EXT vs FRM',ln,o,'Formulation for an order not scheduled',f'{o} is on the {ln} formulation page but not on the {ln} extrusion schedule','')
# formula code vs order attributes
def thkchar(t):
    v=float(t); return str(int(v)) if v<10 else chr(ord('A')+int(v)-10)
for f in frm_rows:
    code=f['formula_code']
    for o in f['orders']:
        r=ext_by_order.get(o)
        if not r: continue
        mat,grade,spec=(r['mat_spec'].split()+['','',''])[:3]
        exp_thk=thkchar(r['thk'])
        if code[-1]!=exp_thk:
            add('High','EXT vs FRM',f['line'],o,'Formula thickness vs order thickness',f'{code} ends in "{code[-1]}" but order Thk is {r["thk"]} (expects "{exp_thk}")',f"FRM p{f['scan_page']}")
        col=r['colors'].split()[0]
        if col not in code[6:]:
            add('Info','EXT vs FRM',f['line'],o,'Formula colour vs order colour',f'{code} vs order colours {r["colors"]}',f"FRM p{f['scan_page']}")
        is_A = len(code)>2 and code[2]=='A'
        if (grade=='A')!=is_A and f['row_in_group']==1:
            ri='RUN WITH' in r['special_instructions'].upper()
            add('Info' if ri else 'Medium','EXT vs FRM',f['line'],o,'Formula grade vs order grade',f'Order grade {grade} ({r["mat_spec"]}) but primary formula {code}'+(' — order is RUN WITH another order, so it takes that formula' if ri else ''),f"FRM p{f['scan_page']}")
        if spec.startswith('R4') and not code.startswith('RU') and f['row_in_group']==1:
            add('Medium','EXT vs FRM',f['line'],o,'R4 spec vs formula family',f'Order spec {spec} but primary formula {code} (R4 orders elsewhere get RU…)',f"FRM p{f['scan_page']}")
# 3. FRM internal -- the check depends on the line's dosing type (load.DOSING, James 26 Sep 2026)
def ext_of(line,k):
    return k.split()[0] if line in ('SE24','SE31','SE32','SE61') else 'all'
for f in frm_rows:
    dose=DOSING.get(f['line'])
    if dose is None: add('Medium','FRM',f['line'],', '.join(f['orders']),'Line with no dosing type','Not in load.DOSING (new line?). Ask James whether it is weight or auger dosed',f"FRM p{f['scan_page']}")
    sets=defaultdict(float); autos=defaultdict(int)
    for k,v in f['feeders'].items():
        s=num(v['set']); ex=ext_of(f['line'],k)
        if s is not None: sets[ex]+=s
        elif str(v['set']).strip().lower()=='auto': autos[ex]+=1; sets[ex]+=0
        elif v['set']: add('Medium','FRM',f['line'],', '.join(f['orders']),'Setting is not a number',f"{f['formula_code']} {k}: {v['set']!r}",f"FRM p{f['scan_page']}")
        if v['material'] and not v['set']: add('Medium','FRM',f['line'],', '.join(f['orders']),'Material with no setting',f"{f['formula_code']} {k}: {v['material']}",f"FRM p{f['scan_page']}")
        if dose=='AUGER' and s is not None and not (0<s<=100):
            add('High','FRM',f['line'],', '.join(f['orders']),'Auger setting outside 0-100',f"{f['formula_code']} {k}: {v['set']} (auger speed dial is 0-100)",f"FRM p{f['scan_page']}")
        if dose=='AUGER' and str(v['set']).strip().lower()=='auto':
            add('High','FRM',f['line'],', '.join(f['orders']),'"Auto" on an auger line',f"{f['formula_code']} {k}: Auto only exists on weight blenders",f"FRM p{f['scan_page']}")
    if dose=='WEIGHT':
        for ex,s in sets.items():
            if autos[ex]==0 and abs(s-100)>0.05:
                add('Medium','FRM',f['line'],', '.join(f['orders']),'Weight line does not add to 100',f"{f['formula_code']} extruder {ex}: {s:g}",f"FRM p{f['scan_page']}")
            elif autos[ex]==1 and not (0<=100-s<=100):
                add('High','FRM',f['line'],', '.join(f['orders']),'Weight line: Auto balance impossible',f"{f['formula_code']} extruder {ex}: fixed settings add to {s:g}, so Auto would be {100-s:g}",f"FRM p{f['scan_page']}")
            elif autos[ex]>1:
                add('Medium','FRM',f['line'],', '.join(f['orders']),'Weight line: more than one Auto',f"{f['formula_code']} extruder {ex}: {autos[ex]} feeders on Auto",f"FRM p{f['scan_page']}")
# same formula code different recipes within a line
seen=defaultdict(list)
for f in frm_rows:
    rec=tuple(sorted((k,v['material'],v['set']) for k,v in f['feeders'].items() if v['material'] or v['set']))
    seen[(f['line'],f['formula_code'])].append((rec,f))
for (ln,code),lst in seen.items():
    recs={x[0] for x in lst}
    if len(recs)>1:
        add('Medium','FRM',ln,'; '.join(', '.join(x[1]['orders']) for x in lst),'Same formula code, different recipes on one line',f'{code} appears {len(lst)} times with {len(recs)} different settings/materials',f"FRM p{lst[0][1]['scan_page']}")
codes_lines=defaultdict(set)
for f in frm_rows: codes_lines[f['formula_code']].add(f['line'])
# material spellings
mats=Counter()
for f in frm_rows:
    for v in f['feeders'].values():
        if v['material']: mats[v['material']]+=1
# known substitutions: the page still prints a material the master has replaced (James decides; master Change Log)
REPLACED={  # printed text -> (what it is now, decision)
    'Q1203K':('F1203K (PH1203, 50-3963-019)','James Kuo, 29 Sep 2026: Q1203K withdrawn at IWPFT062 Rev 16.0, replaced by F1203K; master Changes 8-12'),
}
for f in frm_rows:
    for k,v in f['feeders'].items():
        if v['material'] in REPLACED:
            now,why=REPLACED[v['material']]
            add('Info','FRM',f['line'],', '.join(f['orders']),'Page prints a replaced material',f"{f['formula_code']} {k} prints \"{v['material']}\"; read as {now}. {why}. Tech to correct the page",f"FRM p{f['scan_page']}")
# 4. EXT vs CNV
cnv_by_order=defaultdict(list)
for c in cnv_rows: cnv_by_order[c['order']].append(c)
for o,cs in cnv_by_order.items():
    if len(cs)>1 and len({c['cnv_line'] for c in cs})==1:
        add('Medium','CNV',cs[0]['cnv_line'],o,'Order listed twice on one converting sheet',' | '.join(f"status {c['extrusion_status']}, total {c['total_sheets']}" for c in cs),f"scan p{cs[0]['scan_page']}")
for c in cnv_rows:
    src=f"scan p{c['scan_page']}"
    m=re.fullmatch(r'\s*(\d+)\s+(?:OF|of)\s+(\d+)\s*',c['extrusion_status'] or '')
    if m and int(m.group(1))>int(m.group(2)):
        add('Medium','CNV',c['cnv_line'],c['order'],'Extrusion status: done > ordered',f"{c['extrusion_status']}",src)
    ts,pl,pp=num(c['total_sheets']),num(c['num_plts']),num(c['pc_per_plt'])
    if c['total_sheets'] and '#' in c['total_sheets']:
        add('Medium','CNV',c['cnv_line'],c['order'],'Excel overflow in Total Sheets',f"cell prints {c['total_sheets']}; # of Plts x Pc/Plt = {pl*pp:,.0f}" if pl and pp else c['total_sheets'],src)
    elif ts is not None and pl and pp and abs(ts-pl*pp)>0.5:
        add('High' if abs(ts-pl*pp)/(pl*pp)>0.01 else 'Low','CNV',c['cnv_line'],c['order'],'Total Sheets vs # of Plts x Pc/Plt',f"printed {c['total_sheets']} vs {pl:.0f} x {pp:.0f} = {pl*pp:,.0f}",src)
    if past(c['req_date']): add('Info','CNV',c['cnv_line'],c['order'],'Req. date before issue date',f"Req {c['req_date']} (issued {PKT.month}/{PKT.day}/{PKT.year})",src)
    e=ext_by_order.get(c['order'])
    if e:
        if e['prod_code']!=c['product_code']:
            add('High','EXT vs CNV',e['line']+' / '+c['cnv_line'],c['order'],'Product code differs',f"EXT {e['prod_code']} vs CNV {c['product_code']}",src)
        # CNV semi size is the extruded sheet = EXT actual order size
        sw,sl=size_pair(c['semi_size'])
        ow,ol=frac(e['order_width']),frac(e['order_length'])
        if sw and ow and not ({round(sw,3),round(sl,3)}=={round(ow,3),round(ol,3)}):
            add('High','EXT vs CNV',e['line']+' / '+c['cnv_line'],c['order'],'CNV semi size vs EXT order size',f"CNV semi {c['semi_size']} vs EXT order size {e['order_width']} x {e['order_length']}",src)
        # semi pc/plt vs pcs/stack*stk
        sp=num(c['semi_pc_plt']); ep=(num(e['pcs_per_stack']) or 0)*(num(e['stk_per_plt']) or 0)
        if sp and ep and sp!=ep:
            add('Low','EXT vs CNV',e['line']+' / '+c['cnv_line'],c['order'],'CNV semi pc/plt vs EXT pcs per pallet',f"CNV {c['semi_pc_plt']} vs EXT {e['pcs_per_stack']} x {e['stk_per_plt']} = {ep:.0f}",src)
        # extrusion status vs EXT plts
        m=re.fullmatch(r'\s*(\d+)\s+(?:OF|of)\s+(\d+)\s*',c['extrusion_status'] or '')
        dm=re.search(r'(\d+)\s*PLTS? DONE',e['special_instructions'].upper())
        eplt=num(e['num_plt'])
        if m:
            x,y=int(m.group(1)),int(m.group(2))
            real_plt=eplt
            hw=[int(x) for x in re.findall(r"'(\d{3,4})'",e['handwritten'] or '') if int(x)>999]
            if eplt==999 and hw: real_plt=hw[0]
            if real_plt and y!=real_plt and (y-x)!=real_plt:
                add('Medium','EXT vs CNV',e['line']+' / '+c['cnv_line'],c['order'],'Pallets: CNV status vs EXT # Plt',f"CNV {c['extrusion_status']} (remaining {y-x}) vs EXT # Plt {e['num_plt']}"+(f" (hand-corrected {real_plt})" if real_plt!=eplt else '')+" - matches neither the full order nor the remainder",src)
            if dm and int(dm.group(1))!=x:
                add('Low','EXT vs CNV',e['line']+' / '+c['cnv_line'],c['order'],'Pallets done: CNV vs EXT note',f"CNV {x} done vs EXT note '{dm.group(0)}'",src)
import json
json.dump({'issues':issues,'mats':mats.most_common(),'codes_lines':{k:sorted(v) for k,v in codes_lines.items()}},open(config.WORK_DIR/'issues.json','w',encoding='utf-8'),indent=1)
if __name__=='__main__':
    c=Counter((i['Severity'],i['Check']) for i in issues)
    for k,v in sorted(c.items()): print(v,k)
    print(len(issues))
    ov=[o for o in cnv_by_order if o in ext_by_order]; print('orders on both EXT and CNV:',len(ov),'of CNV',len(cnv_by_order))
