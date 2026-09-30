"""W% Master Formulation (DRAFT for James, 30 Sep 2026): every unique formulation as pure weight % - no line, no auger
data (James Kuo, 30 Sep 2026: "Lets start with W% master formulation. Pull up all unique formulation (including the
specific one like void form)" / "This has no auger data or line data. Just pure fomulation").

A formulation = formula code + application (Standard, VOIDFORM, Sign blank, Corn box, Roll, Reclaim run-out, or the calc
sheet's own note), with its weight % by material. Evidence, newest first:
  - Tech's calc workbooks (Formulation Calc Library, 'Current' version of each code on each line): Formulation % as calculated
    (co-extrusion: the calc's whole-sheet 'Total' rows);
  - Tech's issued FRM pages (daily packets and the older scans): weight-blender lines give weight % directly ('Auto' = the
    balance); auger lines give % = slope x setting / total, with the calc's current slope for that hopper and material
    (the slope unit cancels out, so the rate question does not affect %). A formula whose slope is not known is listed, not
    guessed.
Compositions of one code + application that agree within TOL points on every material group are one formulation; the
newest is shown and the spread is reported. F1102K / Q1203K count as F1203K (James, 30 Sep 2026).
Writes out/W% Master Formulation (draft).xlsx. Read only: no master is changed.
"""
import datetime
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'daily')); sys.path.insert(0, str(ROOT / 'calc'))
import config  # noqa: E402
from common import mat_key  # noqa: E402
from openpyxl import Workbook, load_workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

TOL = 1.5
BLENDER = {'SE24', 'SE42', 'SE43', 'SE61'}
GROUPS = ['Virgin PP', 'Homo PP (F1203K)', 'Reclaim', 'Talc', 'CaCO3', 'Colour MB', 'Vistamaxx', 'Additive', 'Foam', 'HDPE', 'Skin', 'Other']


def material(text):
    """-> (group, name) for a material as written on a calc sheet or an FRM page."""
    k = mat_key(text)
    u = str(text or '').upper()
    if not u.strip():
        return None, None
    if k == 'VIRGIN PP' or 'YUNGSOX' in u:
        return 'Virgin PP', 'Virgin PP' + (' (Yungsox 5050S)' if 'YUNGSOX' in u else '')
    if k in ('1203K', '1102K') or re.search(r'Q1203K', u):
        return 'Homo PP (F1203K)', 'F1203K'
    if k in ('MIX RECLAIM', 'WB RECLAIM', 'RECLAIM') or 'RECLAIM' in u:
        return 'Reclaim', {'MIX RECLAIM': 'PP Mix Reclaim', 'WB RECLAIM': 'PP WB Reclaim'}.get(k, 'PP WB Reclaim' if 'WHITE' in u else 'Reclaim')
    if k == 'TALC':
        return 'Talc', 'Talc'
    if k == 'CACO3':
        return 'CaCO3', 'CaCO3'
    if k == 'VISTAMAXX':
        return 'Vistamaxx', 'Vistamaxx 6102FL'
    if re.search(r'ADSYL|ADYSEL', u):
        return 'Skin', 'Adsyl 5C30F'
    if re.search(r'FOAM|BERGEN|X[O0]-256|^FA-', u):
        return 'Foam', 'Foam Bergen XO-256'
    if re.search(r'HDPE|HF3728|HB5[25]02|HD ?520|F3728', u):
        return 'HDPE', re.sub(r'\s+', ' ', str(text).strip())
    if re.search(r'^\s*(UV|AS|FR)[- ]|ANTI.?STAT|CEE00250|GPP300', u):
        return 'Additive', re.sub(r'\s+', ' ', str(text).strip())
    if k in ('WB COLOR', 'KS COLOR') or re.search(r'PRE-?MIX|NPC|BLACK|MB-CR|^\s*[A-Z]{2}[- ]|B2600|B6038|D2600|D2000|R2600|R3487|G26|G5028|W4002|W2632|W2215|Z2600|E2600|41941', u):
        c = {'WB COLOR': 'WB-W26038A', 'KS COLOR': 'KS masterbatch'}.get(k)
        if not c:
            for rx, nm in [(r'B26003|B60387', 'BL-B26003A'), (r'B26004', 'BD-B26004A'), (r'R34874', 'OF-PP-R34874'), (r'R26006', 'RF-R26006A'),
                           (r'D26074', 'OG-D26074A'), (r'W40020', 'WB-W40020M'), (r'W26329', 'WM-W26329M'), (r'W22151', 'WB-NPC PE-W22151'),
                           (r'D2600?2M|D20002M', 'EA-D26002M'), (r'G50289', 'GS-NPC G50289'), (r'41941', 'YF-NPC PP-41941')]:
                if re.search(rx, u):
                    c = nm; break
        return 'Colour MB', c or re.sub(r'\s+', ' ', str(text).strip())
    return 'Other', re.sub(r'\s+', ' ', str(text).strip())


APPS = [  # note on the FRM page or calc sheet -> application (the note itself is kept in 'Notes as printed')
    (r'run\s*out', 'Reclaim run-out'), (r'void\s*form|^\s*VF\b|\bVF\b', 'VOIDFORM'), (r'sign\s*blank', 'Sign blank'),
    (r'corn\s*box', 'Corn box'), (r'\broll\b|cable wrap', 'Roll'),
    (r'orbis|frito', 'Customer: Orbis'), (r'carter', 'Customer: Carter'), (r'vistech|cadil+ac|trunk', 'Customer: Vistech'),
    (r'tzu.?chi', 'Customer: Tzu-Chi'), (r'nissan', 'Customer: Nissan'), (r'floor cover', 'Floor cover'), (r'roof batten', 'Roof battens'),
    (r'ltl wrap', 'LTL wrap'), (r'PE Part', 'PE part 17356'),
    (r'flame|\bFR\b', 'Flame retardant'), (r'anti.?static|^\s*AS\s*$', 'Anti-static'), (r'extra uv', 'Extra UV'),
    (r'extra opaque|opaque trial', 'Extra opaque'), (r'ultra smooth', 'Ultra smooth'), (r'treated', 'Treated'), (r'utility grade', 'Utility grade'),
    (r'^\s*R4\s*$', 'Spec R4'),
    (r'sample|trial|make up|screw & barrel', 'Trial / sample'),
]
PLAIN = r'gsm|match colou?r|new formula|W26038A/D2|WB\s*:\s*EA'   # sheet notes that do not make a different formulation


def application(note):
    n = re.sub(r'match colou?r and opacity with QC sample', '', note or '', flags=re.I).strip()   # a standard instruction, not a trial
    for rx, name in APPS:
        if re.search(rx, n, re.I):
            return name
    if not n or re.search(PLAIN, n, re.I):
        return 'Standard'
    return f'Other: {n}'


def num(s):
    try:
        return float(str(s).replace(',', ''))
    except (TypeError, ValueError):
        return None


def compose(parts):
    """parts: [(material text, pct)] -> ({group: pct}, {group: {name: pct}}, total)"""
    g, names = defaultdict(float), defaultdict(lambda: defaultdict(float))
    for m, p in parts:
        if p is None or p <= 0:
            continue
        grp, nm = material(m)
        if not grp:
            continue
        g[grp] += p; names[grp][nm] += p
    return dict(g), {k: dict(v) for k, v in names.items()}, sum(g.values())


def norm100(g, names):
    t = sum(g.values())
    if not t:
        return g, names
    return ({k: v * 100 / t for k, v in g.items()}, {k: {n: v * 100 / t for n, v in d.items()} for k, d in names.items()})


# ---- 1. Tech's calc workbooks
calc = load_workbook(config.OUTPUT_DIR / 'Formulation Calc Library.xlsx', read_only=True, data_only=True)
def sheet(ws):
    it = calc[ws].iter_rows(values_only=True); h = next(it)
    return [dict(zip(h, r)) for r in it if any(r)]
lib = {(r['Line'], r['Formula Code']): r for r in sheet('Formula Library') if r['Status'] == 'Current'}
rec = defaultdict(list)
for r in sheet('Current Recipes'):
    rec[(r['Line'], r['Formula Code'])].append(r)
cal = defaultdict(list)                            # (line, feeder) -> [(setup, material key, slope, last used, blocks)]
for r in sheet('Auger Calibration'):
    cal[(r['Line'], r['Feeder'])].append(((r['Gear Ratio'], r['Screw']), mat_key(r['Material (as written)']), r['Current Slope (g/min per unit)'],
                                         r['Last Used'] or datetime.datetime.min, r['Calc Blocks'] or 0))
recipe_slope = defaultdict(dict)                   # (line, code) -> {feeder: (material key, slope)}  Tech's own recipe
for (ln, cd), rs in rec.items():
    for r in rs:
        if r['Feeder'] and r['Calibration Slope (g/min per unit)'] and not r['Extruder']:
            recipe_slope[(ln, cd)][r['Feeder']] = (mat_key(r['Material (as written)']), r['Calibration Slope (g/min per unit)'])


def keys(k):
    return {k, '1203K', '1102K'} if k in ('1203K', '1102K') else {k}


def slope_for(line, code, feeder, k):
    """The slope of the hopper as it is set up now. One hopper name has had several gear/screw setups over the years
    (SE31 H1: 1:14 69x69 slope 219 and 1:24 49x49 slope 39.9), so: Tech's recipe for this code on this line first, then the
    hopper's current setup (the setup used most recently), then the most recent slope for this material on any setup."""
    r = recipe_slope.get((line, code), {}).get(feeder)
    if r and r[0] in keys(k) and r[1]:
        return r[1], ''
    rows = cal.get((line, feeder), [])
    if not rows:
        return None, ''
    setup = max(rows, key=lambda x: (x[3], x[4]))[0]
    cur = [x for x in rows if x[0] == setup and x[1] in keys(k)]
    if cur:
        return max(cur, key=lambda x: (x[3], x[4]))[2], ''
    anyx = [x for x in rows if x[1] in keys(k)]
    if anyx:
        x = max(anyx, key=lambda x: (x[3], x[4]))
        return x[2], f'{feeder} {k}: slope from an older setup {x[0]}'
    return None, ''
ORDER_RX = re.compile(r'^S?[A-Z]{1,2}[0-9A-Z]{2,5}-\d{1,2}$')


def orders_in(text):
    return {t for t in re.split(r'[,;\s]+', str(text or '').upper()) if ORDER_RX.match(t)}


calc_orders = defaultdict(set)                     # (line, code) -> {(line, order)} from the calc's Product to Formula sheet
for r in sheet('Product to Formula'):
    calc_orders[(r['Line'], r['Formula Code'])] |= {(r['Line'], o) for o in orders_in(r['Last Orders'])}
layer_share = {}                                   # code -> {extruder: share}
evidence = []                                      # dicts
for (line, code), rows in rec.items():
    L = lib.get((line, code), {})
    tot = [r for r in rows if str(r['Extruder'] or '').startswith('Total')]
    use = tot if tot else [r for r in rows if not r['Extruder'] or len({x['Extruder'] for x in rows}) == 1]
    if not tot and len({r['Extruder'] for r in rows if r['Extruder']}) > 1:
        use = []                                   # co-ex without a whole-sheet total: per layer only
    for r in rows:
        if r['Extruder'] and r['Extruder Share'] and not str(r['Extruder']).startswith('Total'):
            layer_share.setdefault(code, {})[r['Extruder']] = r['Extruder Share']
    g, names, t = compose([(r['Material (as written)'], r['Formulation %']) for r in use])
    last = L.get('Last Run') or max((r['Last Run'] for r in rows if r['Last Run']), default=None)
    evidence.append({'code': code, 'app': application(L.get('Application / Note')), 'source': 'Calc workbook', 'line': line,
                     'date': last.date() if isinstance(last, datetime.datetime) else last, 'g': g, 'names': names, 'total': t,
                     'where': L.get('Source (last block)') or '', 'products': L.get('Products') or '', 'note': L.get('Application / Note') or '',
                     'layers': '' if use else 'co-extrusion: no whole-sheet total in the calc',
                     'orders': {(line, o) for o in orders_in(L.get('Last Orders'))} | calc_orders.get((line, code), set()),
                     'prods': {(line, p) for p in re.split(r'[,\s]+', str(L.get('Products') or '')) if p}})

# ---- 2. Tech's issued FRM pages
packets = []
for f in sorted((ROOT / 'data' / 'packets').glob('packet_*.json')):
    q = json.loads(f.read_text(encoding='utf-8'))
    if q.get('frm'):
        packets.append((q['packet_date'], q.get('frm_source_scan') or q.get('source_scan'), q['frm']))
old = ROOT / 'work' / 'history' / 'frm_scans.json'
if old.exists():
    for q in json.loads(old.read_text(encoding='utf-8')):
        packets.append((q['packet_date'], q.get('frm_source_scan'), q['frm']))
not_computed = []
seen = {}
for day, scan, pages in sorted(packets, key=lambda x: x[0], reverse=True):
    for pg in pages:
        line = pg['line_code']
        for gr in pg['groups']:
            for f in gr['formulas']:
                if f.get('superseded_on_page'):
                    continue
                code, app = f['formula_code'], application(f.get('note'))
                cells = [(c, v.get('material'), v.get('set')) for c, v in f['feeders'].items() if v.get('material') or v.get('set')]
                sig = (line, code, app, tuple(sorted((c, m, str(s)) for c, m, s in cells)))
                if sig in seen:                    # the same formula again (another group, an older issue): keep its orders too
                    if seen[sig] is not None:
                        seen[sig]['orders'] |= {(line, o) for o in gr['orders']}
                    continue
                seen[sig] = None
                parts, why, layers = [], '', ''
                if line in BLENDER:
                    byx = defaultdict(list)
                    for c, m, s in cells:
                        x = (re.match(r'(?:Extruder )?([A-D]) ', c) or [None, ''])[1]
                        byx[x].append((m, s))
                    lay = {}
                    for x, cs in byx.items():
                        fixed = sum(num(s) or 0 for m, s in cs if num(s) is not None)
                        lay[x] = [(m, num(s) if num(s) is not None else max(0.0, 100 - fixed)) for m, s in cs]   # 'Auto' = balance
                    if len(lay) == 1:
                        parts = next(iter(lay.values()))
                    else:
                        share = layer_share.get(code)
                        layers = '; '.join(f"{x}: " + ', '.join(f'{material(m)[1]} {p:g}' for m, p in cs) for x, cs in sorted(lay.items()))
                        if share and set(share) >= set(lay):
                            parts = [(m, p * share[x]) for x, cs in lay.items() for m, p in cs]
                        else:
                            why = 'co-extrusion: layer shares not known'
                else:
                    notes = []
                    for c, m, s in cells:
                        feeder = 'H' + re.sub(r'\D', '', c.split()[-1]) if re.search(r'(Hopper|V)\s*\d', c) else c
                        sv, nt = slope_for(line, code, feeder, mat_key(m))
                        if sv is None or num(s) is None:
                            why = f'no calc slope for {m} on {line} {feeder}'; break
                        if nt: notes.append(nt)
                        parts.append((m, sv * num(s)))
                    layers = '; '.join(notes)
                if why and not parts:
                    not_computed.append({'code': code, 'app': app, 'line': line, 'date': day, 'why': why, 'layers': layers,
                                         'settings': '; '.join(f'{c} {m} {s}' for c, m, s in cells)})
                    continue
                g, names, t = compose(parts)
                g, names = norm100(g, names)
                evidence.append({'code': code, 'app': app, 'source': 'Tech FRM page', 'line': line, 'date': datetime.date.fromisoformat(day),
                                 'g': g, 'names': names, 'total': 100.0, 'where': f'FRM {day} ({scan}) {line}',
                                 'products': '', 'note': f.get('note') or '', 'layers': layers,
                                 'orders': {(line, o) for o in gr['orders']}, 'prods': set()})
                seen[sig] = evidence[-1]

# ---- 3. one formulation per code + application + composition (within TOL)
for e in evidence:
    e['code'] = e['code'] or '(no code on the calc sheet)'
def close(a, b):
    return all(abs(a.get(k, 0) - b.get(k, 0)) <= TOL for k in set(a) | set(b))
by = defaultdict(list)
for e in evidence:
    by[(e['code'], e['app'])].append(e)
forms = []
for (code, app), es in by.items():
    es.sort(key=lambda e: (e['date'] or datetime.date.min, e['source'] == 'Tech FRM page'), reverse=True)
    clusters = []
    for e in es:
        for c in clusters:
            if close(c[0]['g'], e['g']):
                c.append(e); break
        else:
            clusters.append([e])
    for i, c in enumerate(clusters):
        rep = c[0]
        spread = max((max(x['g'].get(k, 0) for x in c) - min(x['g'].get(k, 0) for x in c)) for k in GROUPS) if len(c) > 1 else 0
        names = defaultdict(float)
        for grp in ('Reclaim', 'Colour MB', 'Additive', 'Foam', 'HDPE', 'Skin', 'Other', 'Virgin PP'):
            for nm, p in rep['names'].get(grp, {}).items():
                if grp == 'Virgin PP' and nm == 'Virgin PP':
                    continue
                names[nm] += p
        forms.append({'code': code, 'app': app, 'version': f'{i + 1} of {len(clusters)}' if len(clusters) > 1 else '',
                      'g': rep['g'], 'total': rep['total'], 'materials': ', '.join(f'{n} {p:.1f}' for n, p in names.items()),
                      'n': len(c), 'calc': sum(x['source'] == 'Calc workbook' for x in c), 'frm': sum(x['source'] == 'Tech FRM page' for x in c),
                      'spread': spread, 'last': rep['date'], 'basis': rep['where'], 'layers': rep['layers'],
                      'note': '; '.join(sorted({x['note'] for x in c if x['note']})),
                      'orders': set().union(*(x['orders'] for x in c)), 'prods': set().union(*(x['prods'] for x in c))})
ORDER = ['Standard', 'VOIDFORM', 'Sign blank', 'Corn box', 'Roll', 'Reclaim run-out']
forms.sort(key=lambda f: (str(f['code']), ORDER.index(f['app']) if f['app'] in ORDER else 9, f['app'], f['version'].zfill(8)))

# ---- 4. the latest run of each formulation: every field of the production schedule (James Kuo, 30 Sep 2026: "On the right
# side after formulation, put together the latest run data. I need every field from production schedule sheet to be on it.
# This way we can create a pattern and match them")
SCHED = ['Run Date', 'Line', 'T', 'Order', 'Prod Code', 'Die', 'Order Width', 'Order Length', 'Material', 'Grade', 'Spec', 'Colors',
         'Thk (mm)', 'GSM', 'Cut Width', 'Cut Length', 'Cut Rows', 'Total Sheets', 'Pack Code', '# Plt', 'PCs/Stack', 'Stk/Plt',
         'Weight (LBs)', 'In-str Date', 'Web Width', 'Special Instructions']
import csv  # noqa: E402
sched = defaultdict(list)                          # (line, order) -> [row dict]
sched_prod = defaultdict(list)                     # (line, product) -> [row dict]
def add_row(d):
    sched[(d['Line'], d['Order'])].append(d); sched_prod[(d['Line'], d['Prod Code'])].append(d)
for name in ('ext_history.csv', 'ext_history_scans.csv'):
    p = ROOT / 'work' / 'history' / name
    if not p.exists():
        continue
    for r in csv.DictReader(open(p, encoding='utf-8')):
        mat = (r['mat'] or '').split()
        add_row({'Run Date': datetime.date.fromisoformat(r['date']), 'Line': r['line'], 'T': r['t'], 'Order': r['order'], 'Prod Code': r['prod_code'],
                 'Die': r['die'], 'Order Width': r['width'], 'Order Length': r['length'], 'Material': mat[0] if mat else '',
                 'Grade': mat[1] if len(mat) > 1 else '', 'Spec': r['mat_spec'], 'Colors': r['colour'], 'Thk (mm)': num(r['thk']),
                 'GSM': num(r['gsm']), 'Cut Width': r['cut_width'], 'Cut Length': r['cut_length'], 'Cut Rows': num(r['cut_rows']),
                 'Total Sheets': num(r['total_sheets']), 'Pack Code': r['pack'], '# Plt': num(r['plts']), 'PCs/Stack': num(r['pcs_stack']),
                 'Stk/Plt': num(r['stk_plt']), 'Weight (LBs)': num(r['weight_lbs']), 'In-str Date': r['instr_date'], 'Web Width': r['web_width'],
                 'Special Instructions': r['special'], 'from': 'System schedule ' + r['file']})
for f in sorted((ROOT / 'data' / 'packets').glob('packet_*.json')):
    q = json.loads(f.read_text(encoding='utf-8'))
    for e in q['ext']:
        for r in e['rows']:
            ms = (r.get('mat_spec') or '').split()
            cuts = r.get('cut_rows') or []
            add_row({'Run Date': datetime.date.fromisoformat(q['packet_date']), 'Line': e['line'], 'T': r.get('T'), 'Order': r['order'],
                     'Prod Code': r['prod_code'], 'Die': r.get('die'), 'Order Width': r.get('order_width'), 'Order Length': r.get('order_length'),
                     'Material': ms[0] if ms else '', 'Grade': ms[1] if len(ms) > 1 else '', 'Spec': ms[2] if len(ms) > 2 else '',
                     'Colors': r.get('colors'), 'Thk (mm)': num(r.get('thk')), 'GSM': num(r.get('gsm')),
                     'Cut Width': cuts[0]['width'] if cuts else '', 'Cut Length': cuts[0]['length'] if cuts else '', 'Cut Rows': len(cuts),
                     'Total Sheets': sum(num(c['total_sheets']) or 0 for c in cuts), 'Pack Code': r.get('pack_code'), '# Plt': num(r.get('num_plt')),
                     'PCs/Stack': num(r.get('pcs_per_stack')), 'Stk/Plt': num(r.get('stk_per_plt')), 'Weight (LBs)': num(r.get('weight_lbs')),
                     'In-str Date': r.get('instr_date'), 'Web Width': r.get('web_width'), 'Special Instructions': r.get('special_instructions'),
                     'from': 'Daily scan ' + (q.get('source_scan') or '')})
for fm in forms:
    runs = [d for k in fm['orders'] for d in sched.get(k, [])]
    fm['orders_found'] = len({(d['Line'], d['Order']) for d in runs})
    if runs:
        fm['run'] = max(runs, key=lambda d: d['Run Date'])
        fm['run_how'] = 'Order named on Tech\'s page / calc sheet for this formulation'
        continue
    cap = (fm['last'] or datetime.date.min) + datetime.timedelta(days=60) if fm['last'] else None
    pr = [d for k in fm['prods'] for d in sched_prod.get(k, []) if cap and d['Run Date'] <= cap]
    if pr:
        fm['run'] = max(pr, key=lambda d: d['Run Date'])
        fm['run_how'] = 'Product named on the calc sheet (the order is not; formula for that run not confirmed)'
    else:
        fm['run'] = None
        fm['run_how'] = 'No run on the schedules on file (Apr 2020 - Sep 2026)' if fm['orders'] or fm['prods'] else 'No order or product named'

# ---- 5. workbook
wb = Workbook()
HEAD = PatternFill('solid', fgColor='1F3864'); HF = Font(color='FFFFFF', bold=True); WRAP = Alignment(wrap_text=True, vertical='top')
def table(ws, header, rows, widths):
    ws.append(header)
    for c in ws[1]:
        c.fill = HEAD; c.font = HF; c.alignment = Alignment(wrap_text=True, vertical='center')
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'C2'; ws.auto_filter.ref = ws.dimensions
rd = wb.active; rd.title = 'Read Me'
n_codes = len({f['code'] for f in forms})
apps = defaultdict(int)
for f in forms:
    apps['Customer-specific' if f['app'].startswith('Customer') else 'Other note' if f['app'].startswith('Other') else f['app']] += 1
for line in [
    'W% Master Formulation - DRAFT for James Kuo (30 Sep 2026)',
    '',
    'James Kuo, 30 Sep 2026: "Lets start with W% master formulation. Pull up all unique formulation (including the specific one like void form)" '
    '/ "This has no auger data or line data. Just pure fomulation".',
    '',
    f'{len(forms)} formulations: {n_codes} formula codes, split by application ('
    + ', '.join(f'{k} {v}' for k, v in sorted(apps.items(), key=lambda kv: -kv[1])) + ') and, where one code has clearly different compositions, by version.',
    'Each row is weight % by material group (adds to 100). "Materials" names the reclaim, colour and additive in it.',
    'Evidence: Tech\'s calc workbooks (current version of each code) and every formulation on Tech\'s FRM pages (23-30 Sep 2026, and the older scans). '
    'Weight-blender pages give % directly; auger pages give % = calibration slope x setting / total (the slope unit cancels out).',
    f'Compositions of one code + application within {TOL} points on every group count as one formulation (the newest is shown; "Spread" = the largest '
    'difference between them). Versions "1 of 2" etc. are the same code + application with different compositions: James to say which is right.',
    'F1102K and Q1203K are counted as F1203K (James, 30 Sep 2026). Nothing here is approved; no master was changed.',
    f'Not computed ({len(not_computed)}): formulas on Tech\'s pages whose calibration slope or layer share is not in the calc workbooks (sheet "Not computed").',
]:
    rd.append([line])
rd.column_dimensions['A'].width = 160
for c in rd['A']:
    c.alignment = Alignment(wrap_text=True, vertical='top')
rd['A1'].font = Font(bold=True, size=13)
for line in ['',
             'Sheet "Formulation + Latest Run": the formulation on the left (weight %), then the latest time it ran on the right, with every field '
             'of the production schedule for that run (James Kuo, 30 Sep 2026: "I need every field from production schedule sheet to be on it. This way '
             'we can create a pattern and match them"). The run is the latest schedule day of an order that Tech\'s page or calc sheet names for this '
             'formulation; where only the product is named, the product\'s latest run on that line within 60 days of the formulation\'s last use '
             '(marked in "Run found by"). Schedules on file: the system schedules Apr 2020 - Sep 2026, five scanned days, and the daily scans.']:
    rd.append([line]); rd.cell(rd.max_row, 1).alignment = Alignment(wrap_text=True, vertical='top')

RUNHEAD = PatternFill('solid', fgColor='375623')
lr = wb.create_sheet('Formulation + Latest Run')
fcols = ['Formula Code', 'Application', 'Version'] + [f'{g} %' for g in GROUPS] + ['Total', 'Materials', 'Evidence (calc / FRM)', 'Spread (points)', 'Last used']
rcols = [f'Run: {c}' for c in SCHED] + ['Run found by', 'Orders on file with this formulation', 'Run row from']
lr.append(fcols + [''] + rcols)
for fm in forms:
    r = fm['run'] or {}
    lr.append([fm['code'], fm['app'], fm['version']] + [round(fm['g'][g], 1) if fm['g'].get(g) else None for g in GROUPS]
              + [round(fm['total'], 1) if fm['g'] else None, fm['materials'], f"{fm['calc']} / {fm['frm']}",
                 round(fm['spread'], 1) if fm['n'] > 1 else None, fm['last'], '']
              + [r.get(c) for c in SCHED] + [fm['run_how'], fm['orders_found'] or None, r.get('from')])
nf = len(fcols)
for i, c in enumerate(lr[1], 1):
    c.font = HF; c.alignment = Alignment(wrap_text=True, vertical='center')
    c.fill = HEAD if i <= nf else (PatternFill('solid', fgColor='FFFFFF') if i == nf + 1 else RUNHEAD)
widths = [13, 16, 8] + [7] * len(GROUPS) + [7, 34, 10, 8, 11, 2] + [11, 7, 4, 12, 13, 8, 9, 9, 8, 6, 12, 14, 6, 7, 9, 10, 6, 10, 9, 6, 9, 7, 10, 10, 9, 60] + [34, 10, 40]
for i, w in enumerate(widths, 1):
    lr.column_dimensions[get_column_letter(i)].width = w
lr.freeze_panes = 'C2'; lr.auto_filter.ref = lr.dimensions
for row in lr.iter_rows(min_row=2):
    row[nf - 1].number_format = 'yyyy-mm-dd'; row[nf + 1].number_format = 'yyyy-mm-dd'
    row[nf].fill = PatternFill('solid', fgColor='D9D9D9')
    if row[2].value:
        for c in row[:3]:
            c.fill = PatternFill('solid', fgColor='FFF2CC')
lr.row_dimensions[1].height = 45
wb.move_sheet(lr, offset=-(len(wb.sheetnames) - 2))

ws = wb.create_sheet('W% Master')
table(ws, ['Formula Code', 'Application', 'Version'] + [f'{g} %' for g in GROUPS] + ['Total', 'Materials', 'Evidence (calc / FRM)', 'Spread (points)',
                                                                                     'Last used', 'Layers (co-extrusion)', 'Notes as printed', 'Newest evidence'],
      [[f['code'], f['app'], f['version']] + [round(f['g'][g], 1) if f['g'].get(g) else None for g in GROUPS]
       + [round(f['total'], 1) if f['g'] else None, f['materials'], f"{f['calc']} / {f['frm']}", round(f['spread'], 1) if f['n'] > 1 else None,
          f['last'], f['layers'], f['note'], f['basis']] for f in forms],
      [13, 16, 8] + [8] * len(GROUPS) + [7, 40, 11, 9, 11, 50, 40, 60])
for row in ws.iter_rows(min_row=2):
    row[len(GROUPS) + 7].number_format = 'yyyy-mm-dd'
    if row[2].value:
        for c in row[:3]:
            c.fill = PatternFill('solid', fgColor='FFF2CC')

ev = wb.create_sheet('Evidence')
table(ev, ['Formula Code', 'Application', 'Source', 'Line (evidence only)', 'Date'] + [f'{g} %' for g in GROUPS] + ['Total', 'Where', 'Products', 'Note'],
      [[e['code'], e['app'], e['source'], e['line'], e['date']] + [round(e['g'][g], 1) if e['g'].get(g) else None for g in GROUPS]
       + [round(e['total'], 1), e['where'], e['products'], e['note']] for e in sorted(evidence, key=lambda e: (str(e['code']), e['app'], str(e['date'])))],
      [13, 16, 14, 10, 11] + [8] * len(GROUPS) + [7, 50, 40, 30])
nc = wb.create_sheet('Not computed')
table(nc, ['Formula Code', 'Application', 'Line', 'Date', 'Why', 'Layers', 'Settings as printed'],
      [[x['code'], x['app'], x['line'], x['date'], x['why'], x['layers'], x['settings']] for x in not_computed],
      [13, 16, 8, 11, 45, 70, 100])
out = config.OUTPUT_DIR / 'W% Master Formulation (draft).xlsx'
wb.save(out)
print(out)
print(f'{len(forms)} formulations, {n_codes} codes; evidence {len(evidence)} ({sum(e["source"] == "Calc workbook" for e in evidence)} calc, '
      f'{sum(e["source"] == "Tech FRM page" for e in evidence)} FRM); not computed {len(not_computed)}')
print('applications:', dict(apps))
print('codes with >1 version:', sorted({f['code'] + ' ' + f['app'] for f in forms if f['version']})[:40], len({(f['code'], f['app']) for f in forms if f['version']}))
