"""Parse the per-line 'SExx Formulation.xls' calculation workbooks into a long table.
One block = one order's formulation calc (Order # ... Formulation (%)). One output row per block x feeder."""
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1])); import config  # repo root config
import xlrd, glob, re, json, datetime, os, sys
ORDER_LABELS = {'order #', 'order number', 'orcer #', 'porder #'}
GROUP_LABELS = {'hopper': None, 'extruder (a)': 'A', 'extruder a': 'A', 'extruder (b)': 'B', 'extruder b': 'B', 'extruder c': 'C',
                'extruder (c)': 'C', 'extruder (d)': 'D', 'extruder d': 'D', 'main hopper (a)': 'A', 'co-ex b hopper': 'B', 'co-ex c hopper': 'C'}
ROWKEYS = {'material': 'material', 'calibration slope': 'slope', 'formula setting': 'setting', 'amount (g/min.)': 'amount',
           'formulation (%)': 'pct', 'lb./hr.': 'lbhr'}
MON = '123456789ABC'
def order_date(o):
    """Estimated production month from the order number (inferred pattern, not confirmed):
    RP<YY><M><DD>  e.g. RP26811 = 2026-08-11 ; H<digit year 202x><M>A..  e.g. H69A = 2026-09 ;
    H<letter year><M>A.. with K=2009 ... W=2021 e.g. HS2A = 2017-02."""
    o = (o or '').strip().upper()
    m = re.match(r'S?RP(\d\d)([1-9ABC])(\d\d)', o)
    if m:
        try: return datetime.date(2000 + int(m.group(1)), MON.index(m.group(2)) + 1, int(m.group(3)))
        except ValueError: return None
    m = re.match(r'S?H(\d)([1-9ABC])[A-Z]', o)
    if m: return datetime.date(2020 + int(m.group(1)), MON.index(m.group(2)) + 1, 1)
    m = re.match(r'S?H([K-W])([1-9ABC])[A-Z]', o)
    if m: return datetime.date(2009 + ord(m.group(1)) - ord('K'), MON.index(m.group(2)) + 1, 1)
    return None
def period_dates(p, wb):
    """'102522-' / '010623-022123' / '2016-12-20' / excel date -> (start, end)"""
    if isinstance(p, tuple):                            # (value, ctype)
        v, ct = p
        if ct == 3:                                     # a real Excel date
            d = xlrd.xldate_as_datetime(v, wb.datemode).date(); return d, d
        p = str(int(v)).zfill(6) if isinstance(v, float) else v   # a number typed as MMDDYY (e.g. 22326 = 02/23/26)
    s = str(p or '').strip()
    ds = []
    for m in re.finditer(r'(\d{4})-(\d\d)-(\d\d)|(\d\d)(\d\d)(\d\d)(?!\d)', s):
        try:
            if m.group(1): ds.append(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            else: ds.append(datetime.date(2000 + int(m.group(6)), int(m.group(4)), int(m.group(5))))
        except ValueError: pass
    if not ds: return None, None
    return ds[0], (ds[1] if len(ds) > 1 else None)
def num(v):
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(',', '').strip())
    except ValueError: return None
def feeder_meta(h):
    m = re.match(r'\s*([A-Z]{0,2}\s*\d+)\s*\((1:\d+)\s*,\s*([\dx]+)\)', str(h))
    if m: return m.group(1).replace(' ', ''), m.group(2), m.group(3)
    return str(h).strip().replace(' ', ''), '', ''

def parse(path, line_hint=None):
    wb = xlrd.open_workbook(path)
    out, blocks = [], []
    for si, s in enumerate(wb.sheets()):
        line = None
        if s.nrows:
            m = re.search(r'\((SE\s?\d\d)\)', str(s.cell_value(0, 0)))
            line = m.group(1).replace(' ', '') if m else line_hint
        r = 0
        while r < s.nrows:
            a = str(s.cell_value(r, 0)).strip().lower()
            if a not in ORDER_LABELS: r += 1; continue
            # block runs until next order label
            r2 = r + 1
            while r2 < s.nrows and str(s.cell_value(r2, 0)).strip().lower() not in ORDER_LABELS: r2 += 1
            blk = {'file': os.path.basename(path), 'line': line or line_hint, 'sheet': s.name.strip(), 'sheet_index': si, 'row': r + 1,
                   'orders': str(s.cell_value(r, 1)).strip(), 'extra': []}
            groups, cur, pending_name = [], None, None
            for rr in range(r + 1, r2):
                row = s.row_values(rr)
                lab = str(row[0]).strip()
                ll = lab.lower()
                if ll == 'product code':
                    blk['product'] = str(row[1]).strip(); blk['formula_code'] = str(row[5]).strip() if len(row) > 5 else ''
                    blk['period_raw'] = row[7] if len(row) > 7 else ''
                    blk['_period_cell'] = (s.cell_value(rr, 7), s.cell_type(rr, 7)) if s.ncols > 7 else ''
                elif ll == 'thickness (mm)':
                    blk['thk'] = row[1]; blk['gsm'] = num(row[3]); blk['lsp'] = num(row[5]); blk['output_lbhr'] = num(row[7])
                elif ll == 'grade':
                    blk['grade'] = str(row[1]).strip(); blk['size'] = str(row[3]).strip(); blk['application'] = str(row[5]).strip() if len(row) > 5 else ''
                elif ll in ('b', 'c', 'd') and not any(str(x).strip() for x in row[1:]):
                    pending_name = lab.upper()
                elif ll in GROUP_LABELS or ll == 'total':
                    name = 'Total' if ll == 'total' else (GROUP_LABELS[ll] or pending_name or '')
                    pending_name = None
                    hdr = row[1:7] if ll != 'total' else [f'#{i}' for i in range(1, 7)]
                    cur = {'group': name, 'label': lab, 'feeders': [str(h).strip() for h in hdr], 'vals': {}, 'share': None, 'comment': ''}
                    groups.append(cur)
                elif ll in ROWKEYS and cur is None:          # hopper header row missing: feeders by position
                    cur = {'group': '', 'label': '(no header)', 'feeders': [f'H {i}' for i in range(1, 7)], 'vals': {}, 'share': None, 'comment': ''}
                    groups.append(cur)
                    cur['vals'][ROWKEYS[ll]] = row[1:7]
                    if ROWKEYS[ll] == 'material' and len(row) > 7 and str(row[7]).strip(): cur['comment'] = str(row[7]).strip()
                elif ll in ROWKEYS and cur is not None:
                    key = ROWKEYS[ll]
                    if key == 'material' and cur['vals'].get('material'):   # a second Material row without header (e.g. 'Total' blocks)
                        cur = {'group': cur['group'] + '+', 'label': 'cont', 'feeders': cur['feeders'], 'vals': {}, 'share': None, 'comment': ''}
                        groups.append(cur)
                    cur['vals'][key] = row[1:7]
                    if key == 'material' and len(row) > 7 and str(row[7]).strip(): cur['comment'] = str(row[7]).strip()
                elif isinstance(row[0], float) and cur is not None and cur['share'] is None:
                    cur['share'] = row[0]
                elif lab and ll not in ('prod. period',):
                    blk['extra'].append(lab)
            blk['groups'] = groups
            ps, pe = period_dates(blk.get('_period_cell', ''), wb)
            blk.pop('_period_cell', None)
            blk['period_start'], blk['period_end'] = ps, pe
            first_order = re.split(r'[&,/ ]+', blk['orders'])[0] if blk['orders'] else ''
            blk['order_date'] = order_date(first_order)
            blocks.append(blk)
            for g in groups:
                mats = g['vals'].get('material', [''] * 6)
                for i in range(6):
                    mat = str(mats[i]).strip() if i < len(mats) else ''
                    vals = {k: (g['vals'][k][i] if k in g['vals'] and i < len(g['vals'][k]) else '') for k in ('slope', 'setting', 'amount', 'pct', 'lbhr')}
                    hdr_txt = str(g['feeders'][i]).strip().lower() if i < len(g['feeders']) else ''
                    if hdr_txt in ('total', 'comments'):
                        if hdr_txt == 'total' and num(vals['amount']) is not None: g['total_gmin'] = num(vals['amount'])
                        continue
                    if not mat and all(v in ('', None) for v in vals.values()): continue
                    feeder, ratio, screw = feeder_meta(g['feeders'][i]) if i < len(g['feeders']) else ('', '', '')
                    bad_hdr = ''
                    if not re.fullmatch(r'(H|V)\d|[A-D]\d|#\d', feeder or ''):       # header cell overwritten (e.g. '6502A') or blank
                        bad_hdr = g['feeders'][i] if i < len(g['feeders']) else ''
                        feeder = ('H' if g['group'] in ('', ) else (g['group'][:1] or 'H')) + str(i + 1) if g['group'] != 'Total' else f'#{i + 1}'
                    out.append({**{k: blk.get(k) for k in ('file', 'line', 'sheet', 'sheet_index', 'row', 'orders', 'product', 'formula_code', 'period_raw',
                                                           'period_start', 'period_end', 'order_date', 'thk', 'gsm', 'lsp', 'output_lbhr', 'grade', 'size', 'application')},
                                'group': g['group'], 'feeder': feeder, 'gear_ratio': ratio, 'screw': screw, 'feeder_header': g['feeders'][i] if i < len(g['feeders']) else '',
                                'material': mat, 'slope': num(vals['slope']), 'setting': num(vals['setting']), 'setting_raw': vals['setting'],
                                'amount_gmin': num(vals['amount']), 'pct': num(vals['pct']), 'lbhr': num(vals['lbhr']),
                                'extruder_share': g['share'], 'comment': g['comment'], 'pos': i + 1, 'bad_header': bad_hdr})
            r = r2
    return blocks, out

if __name__ == '__main__':
    import pickle
    allb, allr = [], []
    files = sorted(p for p in config.CALC_DIR.glob('*Formulation*.xls') if not p.name.startswith('~$'))
    if not files: raise SystemExit(f'No *Formulation*.xls in {config.CALC_DIR} (set CALC_DIR in local_settings.json)')
    for f in files:
        config.record_read(f, 'calc workbook')
        b, o = parse(str(f))
        allb += b; allr += o
        print(f, len(b), 'blocks', len(o), 'feeder rows')
    pickle.dump((allb, allr), open(config.WORK_DIR / 'parsed.pkl', 'wb'))
