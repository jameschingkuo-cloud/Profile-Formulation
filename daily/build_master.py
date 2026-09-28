"""Product Master (material master). Product Code is the key. Each run merges one day's packet into the prior master
(PRIOR_MASTER env). Usage: PKT_DATE=YYYY-MM-DD [PRIOR_MASTER=<Product Master.xlsx>] [CALC_JSON=work/calc_products.json] [RUN_DATE=YYYY-MM-DD] python daily/build_master.py"""
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1])); import config  # repo root config
import re, json
from collections import defaultdict, OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment
from load import *

PACKET = '2026-09-23'
F = 'Arial'
HDR = PatternFill('solid', fgColor='1F3864'); HFONT = Font(name=F, bold=True, color='FFFFFF', size=10)
GRP = {'id': '1F3864', 'code': '2F5597', 'ext': '375623', 'frm': '7F6000', 'cnv': '843C0C', 'hist': '595959', 'ctl': '7030A0'}
BODY = Font(name=F, size=10); CONF = PatternFill('solid', fgColor='FCE4D6'); INPUT = PatternFill('solid', fgColor='FFF2CC')

frm_by_order = defaultdict(list)
for f in frm_rows:
    for o in f['orders']:
        frm_by_order[o].append(f)

def thk_from_code(pc):
    a, b = pc[3], pc[4]
    if a.isdigit(): return float(a + '.' + b)
    return 10.0 + ord(a) - ord('A')

TYPE = {'D': 'D (die-cut route: Baysek/Bobst) - inferred', 'S': 'S (slit/sheeted: Slitter/Guillotine) - inferred',
        'R': 'R (stock sheet / reclaim-spec) - inferred', 'C': 'C (converted/printed: Rotary/Folder gluer) - inferred'}

def weight_target(note):
    m = re.search(r'Target wt is\s*(\d*\.\d+)\.?\s*Acceptable range is\s*(\d*\.\d+)\s*-\s*(\d*\.\d+)', note or '')
    return (float(m.group(1)), float(m.group(2)), float(m.group(3))) if m else (None, None, None)

def mark(note):
    m = re.search(r'(Mark[^.]*?#)', note or '')
    return m.group(1) if m else ''

# ------------------------------------------------------------------ collect every appearance
P = OrderedDict()
def prod(pc):
    return P.setdefault(pc, defaultdict(list))
hist = []   # order history rows
for r in ext_rows:
    d = prod(r['prod_code'])
    mat, grade, spec = (r['mat_spec'].split() + ['', '', ''])[:3]
    for k, v in [('mat', mat), ('grade', grade), ('spec', spec), ('colors', r['colors']), ('thk', float(r['thk'])), ('gsm', num(r['gsm'])),
                 ('width', r['order_width']), ('length', r['order_length']),
                 ('cut', ' / '.join(sorted({c['width'] + ' x ' + c['length'] for c in r['cut_rows']}))), ('ups', len(r['cut_rows'])),
                 ('web', r['web_width']), ('pack_ext', r['pack_code']), ('pcs_stack', num(r['pcs_per_stack'])), ('stk_plt', num(r['stk_per_plt']))]:
        d[k].append((v, r['order']))
    m = re.search(r'RANGE(?:\s+IS|\s+WEIGHT)?\s*(\d[\d,]{2,5})\s*-\s*(\d[\d,]{2,5})', r['special_instructions'].replace(',', ''), re.I)
    if m and 'GSM' in r['special_instructions'].upper() or (m and 'VOIDFORM' in r['special_instructions'].upper()):
        d['gsm_range'].append((f"{m.group(1)}-{m.group(2)}", r['order']))
    tags = [t for t in ['VOIDFORM', 'CORN BOX', 'COOL SEAL', 'ULTRA SMOOTH', 'GENESIS', 'Bradford', 'Rolls', 'SIGN BLANK'] if t.upper() in r['special_instructions'].upper()]
    for t in tags: d['tags'].append((t, r['order']))
    dest = re.search(r'(?:SEND|Send) to ([A-Za-z]+)', r['special_instructions'])
    if dest: d['send_to'].append((dest.group(1).upper().rstrip('.'), r['order']))
    d['line'].append((r['line'], r['order']))
    d['die_line'].append((f"{r['line']}: {r['die']}", r['order']))
    for f in frm_by_order.get(r['order'], []):
        role = 'Primary' if f['row_in_group'] == 1 else f"Alt {f['row_in_group']-1}"
        d['formula_by_line'].append((f"{r['line']}: {f['formula_code']} ({role})", r['order']))   # (7-sheet design, unused)
    hist.append([PACKET, r['order'], r['prod_code'], 'EXT', r['line'], r['die'], ', '.join(f"{f['formula_code']}" for f in frm_by_order.get(r['order'], [])),
                 sum(num(c['total_sheets']) or 0 for c in r['cut_rows']), num(r['weight_lbs']), r['special_instructions'][:200], f"scan p{r['scan_page']}"])
for c in cnv_rows:
    d = prod(c['product_code'])
    wt, lo, hi = weight_target(c['row_notes'])
    for k, v in [('cnv_line', c['cnv_line']), ('cnv_die', c['die_no']), ('cnv_die_desc', c['die_description']), ('semi_size', c['semi_size']),
                 ('semi_pcplt', num(c['semi_pc_plt'])), ('cnv_color', c['color']), ('apl', c['apl']), ('mm', c['mm']), ('flute', c['flute']),
                 ('plate', c['plate_status']), ('ink', c['ink_color']), ('pack_cnv', c['pack_code']), ('pc_plt', num(c['pc_per_plt']))]:
        if v not in (None, ''): d[k].append((v, c['order'])); d['_cl_' + k].append((c['cnv_line'], v))
    if wt: d['wt'].append((f"{wt:.4f} ({lo:.4f}-{hi:.4f})", c['order'])); d['_cl_wt'].append((c['cnv_line'], f"{wt:.4f} ({lo:.4f}-{hi:.4f})"))
    mk = mark(c['row_notes'])
    if mk: d['mark'].append((mk, c['order']))
    hist.append([PACKET, c['order'], c['product_code'], 'CNV', c['cnv_line'], c['die_no'], '', num(c['total_sheets']), None,
                 (c['extrusion_status'] + ' | ' + (c['row_notes'] or ''))[:200], f"scan p{c['scan_page']}"])

def _n(v):
    return int(v) if isinstance(v, float) and v.is_integer() and v > 50 else v

def vals(d, k):
    out = []
    for v, o in d.get(k, []):
        v = _n(v)
        if v not in out: out.append(v)
    return out

def one(d, k):
    v = vals(d, k)
    if not v: return None, False
    if len(v) == 1: return v[0], False
    return ' | '.join(str(x) for x in v), True

# ------------------------------------------------------------------ master rows (simple: one row per product, no history, no line)
import datetime
import os
PKT_DATE = datetime.date.fromisoformat(os.environ.get('PKT_DATE', '2026-09-23'))       # date of the packet in PKT_OUT
LAST_UPDATE = datetime.date.fromisoformat(os.environ.get('RUN_DATE', str(PKT_DATE)))     # date written into Last Updated for rows this run changes
CALC_JSON = os.environ.get('CALC_JSON')   # per-product summary of Tech's formulation calc workbooks (export_calc_products.py), optional
MASTER = config.OUTPUT_DIR / 'Product Master.xlsx'
# existing master to merge into: PRIOR_MASTER, else the published one (PUBLISH_DIR/Product Master/; None = build fresh)
_pub = config.published_path('Product Master.xlsx')
PRIOR = os.environ.get('PRIOR_MASTER') or (str(_pub) if _pub and _pub.exists() else None)
if PRIOR and os.path.exists(PRIOR): config.record_read(PRIOR, 'prior Product Master')
cols = [  # (header, group, key, width)
 ('Product Code', 'id', None, 14),
 ('Material', 'ext', 'mat', 9), ('Grade', 'ext', 'grade', 7), ('End Use', 'ext', 'end_use', 11), ('Spec', 'ext', 'spec', 7), ('Colours (3 layers)', 'ext', 'colors', 12),
 ('Thk (mm)', 'ext', 'thk', 8), ('GSM', 'ext', 'gsm', 8), ('GSM Range (VOIDFORM)', 'ext', 'gsm_range', 12),
 ('Width (in)', 'ext', 'width', 9), ('Length (in)', 'ext', 'length', 9), ('Cut Size (in)', 'ext', 'cut', 22),
 ('EXT Pack Code', 'ext', 'pack_ext', 9), ('PCs/Stack', 'ext', 'pcs_stack', 9), ('Stk/Plt', 'ext', 'stk_plt', 7), ('Handling Tags', 'ext', 'tags', 16),
 ('CNV Die #', 'cnv', 'cnv_die', 9), ('CNV Die Description', 'cnv', 'cnv_die_desc', 26), ('Semi Size (in)', 'cnv', 'semi_size', 20),
 ('Semi pc/plt', 'cnv', 'semi_pcplt', 8), ('CNV Colour', 'cnv', 'cnv_color', 8), ('Apl.', 'cnv', 'apl', 5), ('MM', 'cnv', 'mm', 5),
 ('Flute', 'cnv', 'flute', 5), ('Plate', 'cnv', 'plate', 10), ('Ink', 'cnv', 'ink', 16), ('CNV Pack Code', 'cnv', 'pack_cnv', 9),
 ('Pc/Plt (finished)', 'cnv', 'pc_plt', 9), ('Piece Wt Target', 'cnv', 'wt_t', 9), ('Piece Wt Min', 'cnv', 'wt_lo', 9), ('Piece Wt Max', 'cnv', 'wt_hi', 9),
 ('Marking', 'cnv', 'mark', 22),
 ('Formula Code(s)', 'frm', 'formula', 22), ('Formula Last Run', 'frm', 'formula_last', 11),
 ('Source', 'ctl', 'source', 16), ('Check', 'ctl', None, 36), ('Status', 'ctl', None, 11), ('Last Updated', 'ctl', None, 12)]

# piece weight as three numeric columns
for c in cnv_rows:
    wt, lo, hi = weight_target(c['row_notes'])
    if wt:
        d = P[c['product_code']]
        d['wt_t'].append((wt, c['order'])); d['wt_lo'].append((lo, c['order'])); d['wt_hi'].append((hi, c['order']))

for r in ext_rows:                                   # packet: formula from the same day's FRM (primary row), source
    d = P[r['prod_code']]
    d['source'].append(('Packet', r['order']))
    for f in frm_by_order.get(r['order'], []):
        if f['row_in_group'] == 1:
            d['formula'].append((f['formula_code'], r['order'])); d['formula_last'].append((PKT_DATE, r['order']))
for c in cnv_rows:
    P[c['product_code']]['source'].append(('Packet', c['order']))
CALC = json.load(open(CALC_JSON, encoding='utf-8')) if CALC_JSON else {}
MULTI_OK = {'tags', 'formula', 'source'}   # lists, not conflicts
QUIET = {'formula', 'formula_last', 'source', 'end_use'}   # filling these is not worth a Check note
def nk(v):                                 # comparison key: 3 == 3.0 == '3.0'; text trimmed
    try: return f"{float(str(v).replace(',', '')):g}"
    except ValueError: return str(v).strip()

# ---- prior master: values per product per key (cells may hold "A | B")
old, old_meta = {}, {}
if PRIOR and os.path.exists(PRIOR):
    from openpyxl import load_workbook
    pw = load_workbook(PRIOR)['Product Master']
    ph = [c.value for c in pw[1]]
    for row in pw.iter_rows(min_row=2, values_only=True):
        if not row[0]: continue
        rec = {}
        for h, g, k, w in cols[1:-3]:
            v = row[ph.index(h)] if h in ph else None
            if v is None or v == '': rec[k] = []
            elif isinstance(v, str): rec[k] = [x.strip() for x in v.split(', ' if k in MULTI_OK else ' | ') if x.strip()]
            else: rec[k] = [v.date() if isinstance(v, datetime.datetime) else v]
        old[row[0]] = rec
        lu = row[ph.index('Last Updated')]
        old_meta[row[0]] = {'status': row[ph.index('Status')] or 'Draft', 'last': lu.date() if hasattr(lu, 'date') else lu,
                            'check': str(row[ph.index('Check')] or '') if 'Check' in ph else ''}

def fnum_(v):
    return f"{v:g}" if isinstance(v, float) else str(v)
def asdate(v):
    if isinstance(v, datetime.datetime): return v.date()
    if isinstance(v, datetime.date): return v
    try: return datetime.date.fromisoformat(str(v)[:10])
    except ValueError: return None
rows, nchk, n_new, n_changed, n_calc_new = [], 0, 0, 0, 0
for pc in sorted(set(P) | set(old) | set(CALC)):
    d = P.get(pc, {})
    o = old.get(pc)
    code_ok = bool(re.fullmatch(r'[A-Z]{3}([0-9]{2}|[A-Z]0)[A-Z]{2}\d{1,5}', pc))
    chk, changed, quiet = [], [], False
    M = {}                                          # merged values per key
    for h, g, k, w in cols[1:-3]:
        new_v = vals(d, k) if d else []
        prev = (o or {}).get(k, [])
        merged = list(prev)
        for v in new_v:
            if nk(v) not in {nk(x) for x in merged}:
                merged.append(v)
                if prev and k not in QUIET: changed.append(f"{h} new {v}")
                elif k in QUIET and k != 'formula_last': quiet = True     # formula_last: compared as max date below
        if o is not None and not prev and new_v and k not in QUIET: changed.append(f"{h} added")
        M[k] = merged
    if o is not None and not o.get('source'):          # masters built before the Source column came only from packets
        M['source'] = ['Packet'] + [x for x in M.get('source', []) if x != 'Packet']
    # ---- Tech's formulation calc workbooks: fill what is empty, note what disagrees
    if not CALC and pc in old_meta:   # no calc data this run: keep the calc notes the prior master had (28 Sep 2026)
        chk += [x for x in old_meta[pc]['check'].split('; ') if x.startswith('calc ')]
    C = CALC.get(pc)
    if C:
        def fill(k, v, label, conflict=True):
            global quiet
            if v in (None, '', []): return
            if not M.get(k):
                M[k] = [v]; return 'filled'
            if conflict and nk(v) not in {nk(x) for x in M[k]}:
                chk.append(f"calc {label} {fnum_(v)}")
        r1 = fill('thk', C['thk'], 'Thk'); r2 = fill('gsm', C['gsm'], 'GSM')
        cut = f"{C['width']} x {C['length']}" if C.get('width') else None
        r3 = fill('cut', cut, 'size', conflict=False); r4 = fill('end_use', C['end_use'], 'end use')
        codes = [c for c in C['formula'] if nk(c) not in {nk(x) for x in M.get('formula', [])}]
        if codes: M['formula'] = codes + M.get('formula', [])
        if 'Formulation calc' not in M.get('source', []): M['source'] = M.get('source', []) + ['Formulation calc']
        if any(x == 'filled' for x in (r1, r2, r3, r4)) or codes: quiet = True
        if C['formula_last']: M['formula_last'] = M.get('formula_last', []) + [C['formula_last']]
    fls = [asdate(x) for x in M.get('formula_last', []) if asdate(x)]
    M['formula_last'] = [max(fls)] if fls else []
    if o is not None and asdate((o.get('formula_last') or [None])[0]) != (M['formula_last'] or [None])[0]: quiet = True
    row = [pc]
    for h, g, k, w in cols[1:-3]:
        merged = M.get(k) or []
        if not merged: row.append(None); continue
        if len(merged) == 1: row.append(merged[0]); continue
        row.append(', '.join(str(x) for x in merged) if k in MULTI_OK else ' | '.join(str(x) for x in merged))
        if k not in MULTI_OK: chk.append(f"{h}: {' | '.join(str(x) for x in merged)}")
    mv = lambda k: M.get(k) or []
    def fl(v):
        try: return float(str(v).replace(',', ''))
        except ValueError: return None
    if code_ok and mv('thk') and fl(mv('thk')[0]) is not None and abs(thk_from_code(pc) - fl(mv('thk')[0])) > 0.01:
        chk.append(f"code thk {thk_from_code(pc):g} vs Thk {fl(mv('thk')[0]):g}")
    if code_ok and mv('colors') and pc[5:7] not in str(mv('colors')[0]).split():
        chk.append(f"code colour {pc[5:7]} vs {mv('colors')[0]}")
    if code_ok and mv('grade') and ((pc[2] == 'A') != (mv('grade')[0] == 'A')) and pc[1:3] != 'BP':
        chk.append(f"code {pc[1:3]} vs grade {mv('grade')[0]}")
    if mv('width') and mv('semi_size'):
        ow, ol = frac(str(mv('width')[0])), frac(str(mv('length')[0]))
        for sz in mv('semi_size'):
            sw, sl = size_pair(sz)
            if sw and ow and {round(sw, 3), round(sl, 3)} != {round(ow, 3), round(ol, 3)}:
                chk.append(f"semi size {sz} vs EXT {mv('width')[0]} x {mv('length')[0]}")
    if mv('semi_pcplt') and mv('pcs_stack'):
        ep = fl(mv('pcs_stack')[0]) * (fl((mv('stk_plt') or [1])[0]) or 1)
        if any(fl(x) != ep for x in mv('semi_pcplt')):
            chk.append(f"semi pc/plt {[_n(fl(x)) for x in mv('semi_pcplt')]} vs EXT {ep:.0f}")
    if not code_ok: chk.append('code does not fit 3 letters + thickness + colour + digits')
    if changed: chk.append(f"{LAST_UPDATE}: " + ', '.join(changed))
    nchk += bool(chk)
    if o is None:
        status, last = 'Draft', LAST_UPDATE; n_new += 1
        if pc not in P: n_calc_new += 1
    else:
        status, last = old_meta[pc]['status'], old_meta[pc]['last']
        if changed or quiet:
            last = LAST_UPDATE; n_changed += 1
            if changed and status == 'Verified': status = 'Needs Review'
    row += ['; '.join(dict.fromkeys(chk)) or None, status, last]
    rows.append(row)

# ------------------------------------------------------------------ workbook
wb = Workbook()
ws = wb.active; ws.title = 'Product Master'
ws.append([c[0] for c in cols])
for r in rows: ws.append(r)
n = len(rows)
ci = {h: j for j, (h, g, k, w) in enumerate(cols, 1)}
for j, (h, g, k, w) in enumerate(cols, 1):
    c = ws.cell(1, j); c.font = HFONT; c.fill = PatternFill('solid', fgColor=GRP[g]); c.alignment = Alignment(wrap_text=True, vertical='center')
    ws.column_dimensions[get_column_letter(j)].width = w
ws.row_dimensions[1].height = 42
WRAP = {ci['Cut Size (in)'], ci['Semi Size (in)'], ci['Check'], ci['CNV Die Description'], ci['Formula Code(s)']}
for i in range(2, n + 2):
    for j in range(1, len(cols) + 1):
        cell = ws.cell(i, j); cell.font = BODY; cell.alignment = Alignment(vertical='top', wrap_text=j in WRAP)
    ws.cell(i, 1).font = Font(name=F, size=10, bold=True)
    ws.cell(i, ci['Last Updated']).number_format = 'yyyy-mm-dd'; ws.cell(i, ci['Formula Last Run']).number_format = 'yyyy-mm-dd'
    for h in ('Piece Wt Target', 'Piece Wt Min', 'Piece Wt Max'):
        if isinstance(ws.cell(i, ci[h]).value, float): ws.cell(i, ci[h]).number_format = '0.0000'
    for h in ('PCs/Stack', 'Semi pc/plt', 'Pc/Plt (finished)'):
        if isinstance(ws.cell(i, ci[h]).value, (int, float)): ws.cell(i, ci[h]).number_format = '#,##0'
    if ws.cell(i, ci['Check']).value: ws.cell(i, ci['Check']).fill = CONF
    ws.cell(i, ci['Status']).fill = INPUT
ws.freeze_panes = 'B2'
t = Table(displayName='ProductMaster', ref=f"A1:{get_column_letter(len(cols))}{n+1}")
t.tableStyleInfo = TableStyleInfo(name='TableStyleLight1', showRowStripes=True); ws.add_table(t)
dv = DataValidation(type='list', formula1='"Draft,Verified,Needs Review,Obsolete"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"{get_column_letter(ci['Status'])}2:{get_column_letter(ci['Status'])}{n+1}")
ws.cell(1, 1).comment = Comment('Product Code = material master number (James Kuo, 24 Sep 2026). One row per code - never duplicate.', 'Claude')
ws.cell(1, ci['Last Updated']).comment = Comment('Date of the source (daily packet, or Tech formulation calc workbooks) that last added or changed a value on this row.', 'Claude')
ws.cell(1, ci['Formula Code(s)']).comment = Comment('Formula codes this product ran with: the daily FRM page (primary formula) and Tech formulation calc workbooks (codes used within a year of the latest run), most recent first. Line-by-line recipes are in Formulation Master.xlsx (approved) and Formulation Calc Library.xlsx (Tech's calcs).', 'Claude')
ws.cell(1, ci['Formula Last Run']).comment = Comment('Latest run date of this product in the formulation calc workbooks (Prod. Period, else estimated from the order number) or the daily packet.', 'Claude')

# summary counts under Read Me (formulas)
rm = wb.create_sheet('Read Me', 0)
L = get_column_letter
lines = ['Product Master - material master list for Profile Plant sheet products',
         '',
         'Key: Product Code = material master number. One row per code; the code is always column A.',
         'Green headers = extrusion data (Extrusion Production Schedule). Brown headers = converting data (Converting Production Schedule). Olive headers = formulation (daily FRM page and Tech\'s SExx Formulation.xls calc workbooks).',
         'Source says where a row came from: Packet (daily extrusion/converting schedules) and/or Formulation calc. Products found only in the calc workbooks carry the basic data the calc holds: Thk, GSM, cut size and end use (taken only from calc blocks that name that product alone), and formula codes. Where the calc disagrees with the packet on Thk or GSM, Check says "calc ...".',
         'No order history and no line assignments are kept here - only the product\'s own attributes.',
         'Blank = the packet did not show that value for this product. Values read from scans; Status stays "Draft" until Tech verifies the row.',
         'If one product showed different values on different orders, the cell lists them (A | B) and the Check column says so (orange). Check also flags code vs data mismatches.',
         'Last Updated = date of the packet that last added or changed a value on the row. Each daily packet is merged in: a new product is added as Draft; a new value for an existing product is added beside the old one (A | B), the Check column names it with the date, and Last Updated changes. A Verified row that changes goes back to Needs Review. Nothing is deleted when a product is not on a packet.',
         '',
         'Summary']
for i, l in enumerate(lines, 1):
    rm.cell(i, 1, l).font = Font(name=F, size=12 if i == 1 else 10, bold=i in (1, len(lines))); rm.cell(i, 1).alignment = Alignment(wrap_text=True)
PM = "'Product Master'"
summ = [('Products', f"=COUNTA({PM}!A2:A{n+1})"),
        ('With extrusion data', f"=COUNTA({PM}!{L(ci['Material'])}2:{L(ci['Material'])}{n+1})"),
        ('With converting data', f"=SUMPRODUCT(--((({PM}!{L(ci['CNV Die #'])}2:{L(ci['CNV Die #'])}{n+1}<>\"\")+({PM}!{L(ci['Semi Size (in)'])}2:{L(ci['Semi Size (in)'])}{n+1}<>\"\"))>0))"),
        ('With formulation data', f"=COUNTA({PM}!{L(ci['Formula Code(s)'])}2:{L(ci['Formula Code(s)'])}{n+1})"),
        ('From daily packets', f"=COUNTIF({PM}!{L(ci['Source'])}2:{L(ci['Source'])}{n+1},\"*Packet*\")"),
        ('From formulation calcs only', f"=COUNTIF({PM}!{L(ci['Source'])}2:{L(ci['Source'])}{n+1},\"Formulation calc\")"),
        ('Rows with a Check', f"=COUNTA({PM}!{L(ci['Check'])}2:{L(ci['Check'])}{n+1})"),
        ('Verified', f"=COUNTIF({PM}!{L(ci['Status'])}2:{L(ci['Status'])}{n+1},\"Verified\")"),
        ('Latest update', f"=MAX({PM}!{L(ci['Last Updated'])}2:{L(ci['Last Updated'])}{n+1})")]
for k, (a, f) in enumerate(summ, len(lines) + 1):
    rm.cell(k, 1, a).font = BODY; c = rm.cell(k, 2, f); c.font = BODY
    c.number_format = 'yyyy-mm-dd' if a == 'Latest update' else '#,##0'
rm.column_dimensions['A'].width = 120; rm.column_dimensions['B'].width = 14
wb.active = 1
wb.save(MASTER)
print(n, 'products;', n_new, 'new (', n_calc_new, 'from calc only);', n_changed, 'changed;', nchk, 'rows with a check')
