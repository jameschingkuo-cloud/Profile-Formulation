"""Build the Profile Formulation UI prototype (published as a claude.ai Artifact, HANDOFF §7.28).

    PKT_DATE=2026-09-29 python ui/build.py  -> out/Profile Formulation <date>.html (+ out/profile-formulation.html)
    python publish.py "Profile Formulation <date>.html"  -> Daily Formulation Report/Interface Copy/

A copy, refreshed after each daily run, not live data (James Kuo, 29 Sep 2026: "lets keep a copy create a separate
folder in the fomulation record for now to hold these file. No Tech sign off require"). Reads the packets, the
PUBLISHED Formulation Master (pre-flighted) and records, and out/FRM Draft <date>.xlsx for the draft-vs-Tech figures.
"""
import datetime
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'daily'))
sys.path.insert(0, str(ROOT / 'calc'))
import config  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from db.seed_master import MAP  # noqa: E402

LN = {'SE11': 1, 'SE12': 2, 'SE13': 3, 'SE21': 4, 'SE22': 5, 'SE23': 6, 'SE24': 7, 'SE31': 8, 'SE32': 9, 'SE25': 10,
      'SE42': 12, 'SE43': 13, 'SE61': 16}
DOS = {'SE24': 'WEIGHT', 'SE42': 'WEIGHT', 'SE43': 'WEIGHT', 'SE61': 'WEIGHT'}


def real_pallets(r):
    """AS400 caps # Plt at 999 (James Kuo, 29 Sep 2026): above that, sheets / (pcs per stack x stacks per pallet)."""
    def n(s):
        try:
            return float(str(s).replace(',', ''))
        except (TypeError, ValueError):
            return None
    plt, pcs, stk = n(r.get('num_plt')), n(r.get('pcs_per_stack')), n(r.get('stk_per_plt'))
    sheets = sum(n(c.get('total_sheets')) or 0 for c in r.get('cut_rows', []))
    if plt == 999 and pcs and stk and sheets / (pcs * stk) > 999.5:
        return round(sheets / (pcs * stk))
    return None


def replaced():
    """checks.REPLACED (printed text -> what to load, and why), read from the source without running the checks."""
    import ast
    tree = ast.parse((ROOT / 'daily' / 'checks.py').read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'REPLACED' for t in node.targets):
            return {k: {'now': v[0], 'why': v[1]} for k, v in ast.literal_eval(node.value).items()}
    return {}


def draft_vs_tech(day, P):
    """Orders the FRM Draft proposed, how many equal Tech's issue field for field, and the Exceptions."""
    from resolve import split_feeder
    src = config.OUTPUT_DIR / f'FRM Draft {day}.xlsx'
    if not src.exists():
        return {'drafted': 0, 'draft_match': 0, 'exceptions': 0}
    config.record_read(src, 'FRM Draft (interface copy)')
    wb = load_workbook(src, read_only=True)
    rows = list(wb['Draft'].iter_rows(values_only=True)); h = {k: i for i, k in enumerate(rows[0])}
    draft = {}
    for r in rows[1:]:
        k = (r[h['Line Code']], r[h['Order']])
        draft.setdefault(k, {}).setdefault((r[h['Formula Row']], r[h['Formula Code']]), set()).add(
            (r[h['Extruder']] or '', r[h['Feeder']], r[h['Material (as issued)']] or '', r[h['Set']] or ''))
    draft = {k: [(c, v) for (_, c), v in sorted(d.items())] for k, d in draft.items()}
    tech = {}
    for pg in P['frm']:
        for g in pg['groups']:
            for f in g['formulas']:
                s = {split_feeder(c) + (v['material'], v['set']) for c, v in f['feeders'].items() if v['material'] or v['set']}
                for o in g['orders']:
                    tech.setdefault((pg['line_code'], o), []).append((f['formula_code'], s))
    exc = len(list(wb['Exceptions'].iter_rows(values_only=True))) - 1
    return {'drafted': len(draft), 'draft_match': sum(1 for k, v in draft.items() if tech.get(k) == v), 'exceptions': exc}


def record_rows():
    """Rows in the three published records (read where they live)."""
    out = {}
    for key, (name, sheet) in {'frm': ('Formulation Report Record.xlsx', 'Issued'), 'ext': ('Extrusion Production Record.xlsx', 'Orders by Day'),
                               'cnv': ('Converting Production Record.xlsx', 'Orders by Day')}.items():
        p = config.published_path(name)
        if p and p.exists():
            config.record_read(p, 'record (interface copy)')
            out[key] = load_workbook(p, read_only=True)[sheet].max_row - 1
        else:
            out[key] = 0
    return out


ENG_URL = 'https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata'


def eng_data():
    """out/eng-data.js: Tesseract's English 'fast' LSTM model (tesseract-ocr/tessdata_fast, Apache-2.0; the same file the
    Tesseract 5.4 install on James's PC uses), gzipped and base64'd as a script published next to the page (Artifact
    `files`). The page cannot download it itself: an artifact page may load scripts from the CDN but not fetch data
    (tested 29 Sep 2026). 'fast' reads these schedules better than 'best_int' (61 vs 49 of 76 orders on 29 Sep)."""
    import base64
    import gzip
    import urllib.request
    out = config.OUTPUT_DIR / 'eng-data.js'
    tag = '/* tessdata_fast eng */'
    if out.exists() and out.read_text(encoding='ascii', errors='ignore')[:len(tag)] == tag:
        return out
    raw = config.WORK_DIR / 'eng_fast.traineddata'
    if not raw.exists():
        urllib.request.urlretrieve(ENG_URL, raw)
    gz = gzip.compress(raw.read_bytes(), 9)
    out.write_text(tag + 'window.ENG_TRAINEDDATA_GZ_B64="' + base64.b64encode(gz).decode() + '";', encoding='ascii')
    return out


def line_layout(pk):
    """Per line: number, dosing, and the layout of Tech's latest issued page (feeder columns, AC, footnotes, effective
    date), for the Word formulation the page generates (same layout as daily/render_frm.py)."""
    out = {c: {'no': n, 'dosing': DOS.get(c, 'AUGER'), 'cols': [], 'ac': '', 'notes': [], 'effective': ''} for c, n in LN.items()}
    for d in sorted(pk):
        for pg in pk[d]['frm']:
            if pg['line_code'] in out:
                out[pg['line_code']].update(cols=pg['feeder_columns'], ac=pg.get('header_note', ''), notes=pg.get('footnotes', []),
                                            effective=pg.get('effective_date', ''))
    return out


def product_codes():
    """Product codes in the published Product Master (to flag a code the page read that the plant does not know)."""
    p = config.published_path('Product Master.xlsx')
    if not (p and p.exists()):
        return []
    config.record_read(p, 'Product Master (interface copy)')
    ws = load_workbook(p, read_only=True)['Product Master']
    return sorted({r[0] for r in ws.iter_rows(min_row=2, max_col=1, values_only=True) if r[0]})


def approved_decisions(sheet):
    """Engineer decisions (APPROVED Product to Formula rows with that line's settings), as daily/resolve.py uses them:
    {'LINE|PRODUCT': [formula, ...]} in run order (Primary first)."""
    text = {m['Material ID']: (m.get('FRM Text') or m.get('Name') or m['Material ID']) for m in sheet('Materials')}
    sets = {}
    for s in sheet('Line Settings'):
        sets.setdefault((s['Line Code'], s['Formula Code'], s['Variant']), []).append(s)
    out = {}
    for p in sheet('Product to Formula'):
        k = (p['Line Code'], p['Formula Code'], p['Variant'])
        if p['Status'] != 'Approved' or k not in sets:
            continue
        out.setdefault(f"{p['Line Code']}|{p['Product Code']}", []).append((p['Priority'] != 'Primary', {
            'code': p['Formula Code'], 'note': p['Variant'] if p['Variant'] != 'Primary' else '',
            'feeders': [{'col': (s['Extruder'] + ' ' + s['Feeder']).strip() if s['Extruder'] else s['Feeder'],
                         'mat': text.get(s['Material ID'], s['Material ID']), 'set': s['Set'], 'id': s['Material ID']} for s in sets[k]]}))
    return {k: [f for _, f in sorted(v, key=lambda x: x[0])] for k, v in out.items()}


def main():
    pk = {}
    for f in sorted(glob.glob(str(config.PACKETS_DIR / 'packet_*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        pk[d['packet_date']] = d
    day = os.environ.get('PKT_DATE') or max(d for d in pk if pk[d]['frm'])
    P = pk[day]
    from db import preflight, schema
    ok, pf_lines, _ = preflight.check(schema.FM)          # hard rule: the master is read where it lives, pre-flighted
    if not ok:
        print(chr(10).join(pf_lines)); raise SystemExit('STOP: the Formulation Master has unaccepted changes; interface not built.')
    accepted = re.search(r'accepted version \(([^)]+)\)', pf_lines[0])
    fm = config.published_path(schema.FM)
    config.record_read(fm, 'master (interface copy)')
    wb = load_workbook(fm, read_only=True)

    def sheet(n):
        r = list(wb[n].iter_rows(values_only=True))
        return [dict(zip(r[0], x)) for x in r[1:]]

    mats = {m['Material ID']: {'code': m['Material Code'], 'name': m['Name'], 'st': m['IWPFT062 Status'], 'role': m['Role']}
            for m in sheet('Materials')}
    hist = {}
    for d, p in pk.items():
        for pg in p['frm']:
            for g in pg['groups']:
                for o in g['orders']:
                    hist.setdefault(o, []).append([d, pg['line_code'], [f['formula_code'] for f in g['formulas']]])
    lines = []
    for pg in sorted(P['frm'], key=lambda x: LN[x['line_code']]):
        lc = pg['line_code']
        ext = {r['order']: r for e in P['ext'] if e['line'] == lc for r in e['rows']}
        groups = [{'orders': [{'order': o, 'prod': ext.get(o, {}).get('prod_code'), 'colors': ext.get(o, {}).get('colors'),
                               'thk': ext.get(o, {}).get('thk')} for o in g['orders']],
                   'formulas': [{'code': f['formula_code'], 'note': f.get('note', ''),
                                 'feeders': [{'col': c, 'mat': v['material'], 'set': v['set'], 'id': MAP.get(v['material'])}
                                             for c, v in f['feeders'].items() if v['material'] or v['set']]}
                                for f in g['formulas']]}
                  for g in pg['groups']]
        grp_of = {o: gi for gi, g in enumerate(pg['groups']) for o in g['orders']}
        sched = [{'order': r['order'], 'prod': r['prod_code'], 'colors': r.get('colors'), 'thk': r.get('thk'), 'gsm': r.get('gsm'),
                  'size': f"{r.get('order_width', '')} × {r.get('order_length', '')}", 'die': r.get('die'),
                  'plt': r.get('num_plt'), 'lbs': r.get('weight_lbs'), 'si': r.get('special_instructions') or '',
                  'hw': r.get('handwritten') or '', 'g': grp_of.get(r['order']), 'plt_real': real_pallets(r)}
                 for e in sorted(P['ext'], key=lambda e: e['scan_page']) if e['line'] == lc for r in e['rows']]
        lines.append({'code': lc, 'no': LN[lc], 'dosing': DOS.get(lc, 'AUGER'), 'cols': pg['feeder_columns'],
                      'ac': pg.get('header_note', ''), 'groups': groups, 'notes': pg.get('footnotes', []), 'sched': sched})
    stats = draft_vs_tech(day, P)
    stats['orders'] = sum(len(g['orders']) for ln in lines for g in ln['groups'])
    data = {'day': day, 'dates': sorted(pk),
            'scans': {'packet': P['source_scan'], 'frm': P.get('frm_source_scan') or P['source_scan']},
            'lines': lines, 'materials': mats, 'hist': hist, 'stats': stats,
            'issues': [{'sev': i['Severity'], 'line': i['Line'], 'check': i['Check'], 'detail': i['Detail']} for i in sheet('Issues')],
            'master': {'formulas': len(sheet('Formulas')), 'settings': len(sheet('Line Settings')), 'materials': len(mats),
                       'accepted': accepted.group(1)[:16].replace('T', ' ') if accepted else '', 'changes': 0},
            'records': record_rows(), 'built': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'open': json.loads((ROOT / 'ui' / 'open_items.json').read_text(encoding='utf-8')),
            'cust': json.loads((ROOT / 'ui' / 'customer_formulas.json').read_text(encoding='utf-8')),
            'replaced': replaced(),
            # for "generate from a scan" on the Daily run tab (James Kuo, 29 Sep 2026: "let me put the same production
            # file in the artifact. see if it generate the right formulation"): every issued FRM by date, the
            # transcribed schedule by date (to check the page's reading), known product codes, approved decisions
            'issued': {d: {pg['line_code']: [{'orders': g['orders'],
                                              'formulas': [{'code': f['formula_code'], 'note': f.get('note', ''),
                                                            'feeders': [{'col': c, 'mat': v['material'], 'set': v['set'], 'id': MAP.get(v['material'])}
                                                                        for c, v in f['feeders'].items() if v['material'] or v['set']]}
                                                           for f in g['formulas']]} for g in pg['groups']]
                           for pg in p['frm']} for d, p in pk.items() if p['frm']},
            'sched_by_date': {d: [[e['line'], r['order'], r['prod_code']] for e in p['ext'] for r in e['rows']] for d, p in pk.items()},
            'products': product_codes(),
            'approved': approved_decisions(sheet),
            'linemeta': line_layout(pk)}
    t = (ROOT / 'ui' / 'page.template.html').read_text(encoding='utf-8')
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    page = t.replace('__DATA__', blob)
    eng_data()
    # the artifact source is the page fragment (the Artifact tool adds the document skeleton); the dated copy kept in
    # SharePoint is opened as a file, so it carries its own skeleton and charset
    full = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '</head><body>' + page + '</body></html>')
    for out, text in ((config.OUTPUT_DIR / f'Profile Formulation {day}.html', full), (config.OUTPUT_DIR / 'profile-formulation.html', page)):
        out.write_text(text, encoding='utf-8')
        print(out)


if __name__ == '__main__':
    main()
