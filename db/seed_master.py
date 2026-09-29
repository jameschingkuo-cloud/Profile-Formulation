"""Seed Formulation Master.xlsx as DRAFT from what exists now (James Kuo, 28 Sep 2026: "lets build it this way").

    python db/seed_master.py            -> out/Formulation Master.xlsx

Sources (each read and recorded, per the hard rule):
  - IWPFT062 Qualified Suppliers and Materials List (controlled document; read only) -> Materials
  - data/packets/*.json, Tech's issued FRM pages                                      -> Formulas, Line Settings,
                                                                                         Product to Formula, Recipe
                                                                                         (weight lines), Standing Notes
Tech's calc workbooks are not on this PC yet: auger-line recipes (weight %) and the Auger Calibration master wait for
them. Every seeded row is Draft. After this first publish the master is maintained in Excel by Tech/James, every change
logged in its Change Log sheet, and db/preflight.py stops any run that finds a change without a logged approval.
"""
import datetime
import html
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'daily'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'calc'))
import config  # noqa: E402
from db import schema  # noqa: E402
from resolve import split_feeder, variant  # noqa: E402

IWPFT062 = Path(r'C:/Users/JamesKuo/Inteplast-WPJK/Profile Process Control - Documents/ISO SOP, WT and Training Guide/'
                r'Departments/Technical/Controlled Documents/IWPFT062 - Qualified Suppliers and Materials List.docx')
WEIGHT_LINES = {'SE24', 'SE42', 'SE43', 'SE61'}   # load.DOSING / auger_rules.DOSING

# ---- materials the qualified list does not carry ------------------------------------------------------------
# (Material ID, code, name, supplier, IWPFT062 status, role, note)
EXTRA_MATERIALS = [
    ('50-3963-301', 'Q1203K', 'Q1203K', 'Formosa', 'Withdrawn', 'HOMO',
     'Withdrawn from IWPFT062 at Rev 16.0 (Kevin Sung, 9.9.2026; "IWPFT062 Rev 16 - vendor list revision.md")'),
    # NL-HM-10HP was seeded on 28 Sep and retired on 29 Sep (same material as CA410; master Changes 6-7)
    # NL-YUNGSOX-5050S was seeded on 28 Sep and retired on 29 Sep: IWPFT062 Rev 18.0 lists it as 50-1560-163 (Changes 24-44)
    ('INT-RCL-PP-MIX', '', 'PP Mix Reclaim', 'Plant', 'Not listed', 'RECLAIM', 'Plant reclaim (boxes / silo 8)'),
    ('INT-RCL-PP-WB', '', 'PP WB Reclaim', 'Plant', 'Not listed', 'RECLAIM', 'Plant reclaim, WB colour'),
    ('INT-RCL-WHITE', '', 'White Reclaim', 'Plant', 'Not listed', 'RECLAIM', 'Plant reclaim; same as PP WB Reclaim?'),
    ('INT-PREMIX-WB-EA', '', 'WB : EA premix 9 : 1', 'Plant', 'Not listed', 'COLOUR',
     'WB W26038A (CR411WB) + EA/GT D26002M (CR400EA), 9 : 1 (FRM note on H68A127-1)'),
]

# ---- FRM spelling -> Material ID, and what to tell James/Tech about it ----------------------------------------
V = '50-1560-050'   # PC416 Formosa F6502A, the virgin resin in silos 3 and 4
KS = '50-7002-324'  # CR400K black masterbatch
MAP = {
    'PP Virgin-silo 3 (6502A)': V, 'PP Virgin-silo 3 (F6502A)': V, 'PP Virgin-silo 3 (F-6502A)': V,
    'PP Virgin-silo 4 (6502A)': V, 'PP Virgin-silo 4 (F6502A)': V, 'PP Virgin (F6502A)': V, 'F6502A': V,
    'F1203K': '50-3963-019', 'F1102K': '50-3963-002', 'Q1203K': '50-3963-301',
    'HiTalc ZS (or N40109A)': '50-7002-433',
    'CaCO3 -Heritage HM-10MAX': '50-7002-034', 'CaCO3 –Heritage HM-10MAX': '50-7002-034',
    'CaCO3 -Heritage HM-10HP': '50-7002-034',   # same CaCO3 as CA410 (James Kuo, 29 Sep 2026; master Changes 1-7)
    'WB-W26038A': '50-7002-248', 'WB-W40020M': '50-7002-095', 'NPC NPC PE-W22151': '50-7002-393',
    'WM-W26329M': '50-7015-557', 'BD-B26004A': '50-7002-356', 'OF-PP-R34874 (New NPC orange color)': '50-7002-602',
    'OG-D26074A': '50-7002-372', 'BL-B26003A (OR NPC-B60387)': '50-7002-281', 'UV-N26177A': '50-7002-249',
    'Exxon - Vistamaxx 6102FL': '50-7100-610', 'Exxon – Vistamaxx 6102FL': '50-7100-610',
    'Adsyl 5C30F': '50-8510-004', 'FOAM – Bergen X0-256': '50-7002-430',
    'FOAM – Bergen XO-256': '50-7002-430',   # misprint of X0-256 (James Kuo, 29 Sep 2026; master Changes 13-14)
    'KS- NPC PE90000F (or Spartech B60009 or MDI PE-500)': KS, 'KS-MDI PE-500 (or PolyOne LD-250 or NPC PE90000F': KS,
    'KS-MDI PE-500 (or Spartech B60009 or NPC PE90000F)': KS, 'KS-MDI PE-500 (or Spartech B60009)': KS,
    'PP Yungsox 5050S': '50-1560-163',   # PC5050, added to IWPFT062 at Rev 18.0 (James Kuo, 29 Sep 2026)
    'PP Mix Reclaim': 'INT-RCL-PP-MIX', 'PP WB Reclaim': 'INT-RCL-PP-WB',
    'White Reclaim': 'INT-RCL-PP-WB',   # same as PP WB Reclaim (James Kuo, 29 Sep 2026); INT-RCL-WHITE retired
    'WB EA Premix': 'INT-PREMIX-WB-EA', 'WB GT Premix': 'INT-PREMIX-WB-EA',
    'PP Virgin': V,   # James Kuo, 29 Sep 2026: PP Virgin is F6502A (master Changes 21-23)
}
MAP_ISSUES = [  # (severity, FRM text(s), check, detail)
    ('Medium', ['Q1203K'], 'FRM page still prints a withdrawn material',
     'SE42 FU0021WB4 V3 prints Q1203K (withdrawn at IWPFT062 Rev 16.0). James Kuo, 29 Sep 2026: replaced by F1203K (50-3963-019); master Changes 8-12. Tech to correct the SE42 page'),
    ('High', ['F1102K'], 'In-active material in a current formula',
     'F1102K (PH401, 50-3963-002) is In-active on IWPFT062 Rev 16.0, yet FUA151WB3 (SE43, RP26911-2, 28 Sep) and SE42 (25 Sep) use it'),
    ('Info', ['PP Yungsox 5050S'], 'Added to IWPFT062 at Rev 18.0',
     'PP Yungsox 5050S (SE61 extruders B and D): IWPFT062 Rev 18.0 (James Kuo, 29 Sep 2026) lists it as 50-1560-163, PC5050, Formosa, Active'),
    ('Info', ['CaCO3 -Heritage HM-10HP'], 'Grade name differs from IWPFT062',
     'FRM prints "Heritage HM-10HP" (SE24, FU0011WB5 on SE25); IWPFT062 CA410 reads "HM10 MAX". James Kuo, 29 Sep 2026: same CaCO3 -> 50-7002-034'),
    ('Info', ['PP Virgin'], 'Resin named by James',
     'SE23 corn box formulas print just "PP Virgin". James Kuo, 29 Sep 2026: PP Virgin is F6502A (50-1560-050)'),
    ('Medium', ['KS- NPC PE90000F (or Spartech B60009 or MDI PE-500)', 'KS-MDI PE-500 (or PolyOne LD-250 or NPC PE90000F',
                'KS-MDI PE-500 (or Spartech B60009 or NPC PE90000F)', 'KS-MDI PE-500 (or Spartech B60009)'],
     'Alternate sources not on IWPFT062',
     'Mapped to CR400K black (NPC PE-B9000F; MDI Black PE-500 is an approved second source). Spartech B60009 and PolyOne LD-250 are not on the list; the FRM writes the NPC grade "PE90000F", the list "PE-B9000F"'),
    ('Low', ['BL-B26003A (OR NPC-B60387)'], 'Primary name not on IWPFT062',
     'Mapped to CR410BL (NPC PE-B60387). "BL-B26003A" is not on the list'),
    ('Info', ['HiTalc ZS (or N40109A)'], 'Trade name recorded in the master',
     'TL460 (Amtopp N40109A). James Kuo, 29 Sep 2026: HiTalc ZS is its accepted trade name (Change 45); IWPFT062 unchanged'),
    ('Low', ['FOAM – Bergen XO-256'], 'FRM page misprint',
     'SE24 FSA200WB4 prints Bergen XO-256 (letter O). James Kuo, 29 Sep 2026: it is X0-256 (digit zero), IWPFT062 CF400; master FRM Text corrected. Tech to correct the SE24 page'),
    ('Info', ['WB EA Premix', 'WB GT Premix'], 'One premix, two names',
     'SE25 (25 Sep) "WB GT Premix", SE23 (28 Sep) "WB EA Premix"; the note gives WB W26038A + GT D26002M = CR400EA "Sp. gray". Mapped to one internal material'),
    ('Info', ['PP Mix Reclaim', 'PP WB Reclaim', 'White Reclaim'], 'Plant materials have no IWPFT062 number',
     'Given internal IDs INT-RCL-*. SE42 "White Reclaim" = PP WB Reclaim (James Kuo, 29 Sep 2026; master Changes 15-20)'),
]


def role_for(code, name):
    n = name.upper()
    if 'VISTAMAXX' in n: return 'MODIFIER'
    if code.startswith('PH'): return 'HOMO'
    if code == 'PC530': return 'SKIN'
    if code.startswith('PC') and code not in ('PC625',): return 'VIRGIN'
    if code.startswith('HD'): return 'HDPE'
    if code.startswith('CA'): return 'CACO3'
    if code.startswith('TL'): return 'TALC'
    if code.startswith('CF'): return 'FOAM'
    if code.startswith('CR'): return 'COLOUR'
    if re.match(r'(UV|AS|FR|CD|CEE|NA|NU|VCI)', code): return 'ADDITIVE'
    return 'OTHER'


def read_iwpft062():
    config.record_read(IWPFT062, 'IWPFT062 (controlled document, read only)')
    x = zipfile.ZipFile(IWPFT062).read('word/document.xml').decode('utf-8')
    txt = lambda s: html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'</w:p>', ' ', s))).strip()  # noqa: E731
    rev = None
    rows = []
    for t in re.findall(r'<w:tbl>.*?</w:tbl>', x, re.S):
        trs = [[txt(c) for c in re.findall(r'<w:tc>.*?</w:tc>', r, re.S)] for r in re.findall(r'<w:tr[ >].*?</w:tr>', t, re.S)]
        if trs and trs[0][:2] == ['Revision', 'Date']:
            rev = trs[-1][0]
        if trs and trs[0][:3] == ['Material No.', 'Technical Code', 'Material Name']:
            rows += trs[1:]
    mats, last = {}, None
    for no, code, name, sup, status in (r[:5] for r in rows):
        if not no and not code and last:          # a further approved source for the row above (IWPFT062 §4)
            mats[last]['subs'].append(f'{name} ({sup})')
            continue
        key = no if no not in mats else f'{no} {code}'   # 50-7555-010 appears twice (TPP40, PP/PC625): flagged
        mats[key] = {'code': code, 'name': name, 'sup': sup, 'status': status, 'subs': []}
        last = key
    return rev, mats


def load_packets():
    out = {}
    for p in sorted(config.PACKETS_DIR.glob('packet_*.json')):
        config.record_read(p, 'daily packet (FRM as issued)')
        d = json.loads(p.read_text(encoding='utf-8'))
        out[d['packet_date']] = d
    return out


def num(s):
    try:
        return float(str(s).replace(',', ''))
    except ValueError:
        return None


def build():
    rev, iw = read_iwpft062()
    packets = load_packets()
    dates = sorted(packets)
    issues = []

    # Materials
    spell = defaultdict(list)
    for t, mid in MAP.items():
        if mid:
            spell[mid].append(t)
    materials = []
    for mid, m in iw.items():
        s = spell.get(mid, [])
        materials.append({'Material ID': mid, 'Material Code': m['code'], 'Name': m['name'], 'Supplier': m['sup'],
                          'IWPFT062 Status': m['status'], 'Role': role_for(m['code'], m['name']),
                          'FRM Text': s[0] if s else None, 'Other Spellings': ' | '.join(s[1:]) or None,
                          'Approved Substitutes': ' | '.join(m['subs']) or None, 'Bulk Density (g/cm3)': None,
                          'Status': 'Draft'})
    for mid, code, name, sup, st, role, note in EXTRA_MATERIALS:
        s = spell.get(mid, [])
        materials.append({'Material ID': mid, 'Material Code': code or None, 'Name': name, 'Supplier': sup,
                          'IWPFT062 Status': st, 'Role': role, 'FRM Text': s[0] if s else None,
                          'Other Spellings': ' | '.join(s[1:]) or None, 'Approved Substitutes': note, 'Status': 'Draft'})
    if any(' ' in k for k in iw):
        issues.append(('Medium', 'Materials', '', '', 'Duplicate material number on IWPFT062',
                       '50-7555-010 is listed twice (TPP40 In-active, PP/PC625 Active); keyed "50-7555-010 PP/PC625" here', 'IWPFT062'))

    # Issued formulas from the packets, latest issue wins; history kept for conflicts
    seen = defaultdict(dict)         # (line, code, variant, ext, feeder) -> {date: (material, set, page)}
    formulas = {}                    # (code, variant) -> {'note', 'dates', 'lines'}
    p2f = {}                         # (product, line, code, variant) -> {'priority', 'last'}
    notes = {}                       # line -> (date, footnotes, header_note, effective)
    unmapped = defaultdict(set)
    for d in dates:
        pk = packets[d]
        prod = {r['order']: r['prod_code'] for pg in pk['ext'] for r in pg['rows']}
        for pg in pk['frm']:
            line = pg['line_code']
            notes[line] = (d, pg.get('footnotes') or [], pg.get('header_note') or '', pg.get('effective_date') or '')
            for g in pg['groups']:
                for i, f in enumerate(g['formulas']):
                    var = variant(f.get('note', ''), i == 0)
                    fk = (f['formula_code'], var)
                    rec = formulas.setdefault(fk, {'note': '', 'dates': set(), 'lines': set()})
                    rec['dates'].add(d); rec['lines'].add(line)
                    if f.get('note'): rec['note'] = f['note']
                    for c, v in f['feeders'].items():
                        if not (v.get('material') or v.get('set')):
                            continue
                        ext, feeder = split_feeder(c)
                        k = (line, f['formula_code'], var, ext, feeder)
                        val = (v.get('material', ''), v.get('set', ''), pg['scan_page'])
                        prev = seen[k].get(d)
                        if prev and prev[:2] != val[:2]:
                            issues.append(('High', 'Line Settings', line, ', '.join(g['orders']), 'Same formula, two settings on one day',
                                           f"{f['formula_code']} {var} {ext} {feeder}: {prev[0]} {prev[1]} vs {val[0]} {val[1]} ({d})", f'FRM {d}'))
                        seen[k][d] = val
                        if v.get('material') and v['material'] not in MAP:
                            unmapped[v['material']].add(line)
                    for o in g['orders']:
                        if o in prod:
                            pk2 = (prod[o], line, f['formula_code'], var)
                            e = p2f.setdefault(pk2, {'priority': 'Primary' if i == 0 else 'Alternate', 'last': d})
                            e['last'] = max(e['last'], d)
    for t, lines in unmapped.items():
        issues.append(('High', 'Materials', ', '.join(sorted(lines)), '', 'FRM material not mapped', f'"{t}" has no Material ID mapping', 'FRM'))

    line_settings, recipe = [], []
    for (line, code, var, ext, feeder), hist in sorted(seen.items()):
        last = max(hist)
        mat, st, page = hist[last]
        changed = sorted({(h[0], h[1]) for h in hist.values()})
        if len(changed) > 1:
            issues.append(('Medium', 'Line Settings', line, '', 'Setting changed between packets',
                           f"{code} {var} {ext} {feeder}: " + '; '.join(f"{dd} {h[0]} {h[1]}" for dd, h in sorted(hist.items())) +
                           f' - latest ({last}) seeded', 'FRM'))
        line_settings.append({'Line Code': line, 'Formula Code': code, 'Variant': var, 'Extruder': ext or None,
                              'Feeder': feeder, 'Material ID': MAP.get(mat), 'Set': st,
                              'Slope Used': None, 'Weight % (from Set)': None, 'Recipe Weight %': None, 'Deviation (pts)': None,
                              'Source': 'FRM', 'Status': 'Draft', '_mat': mat, '_from': f'FRM {last} p{page}'})
    # Recipe: weight lines only (Set = weight %, Auto = balance per extruder)
    by_formula = defaultdict(list)
    for r in line_settings:
        if r['Line Code'] in WEIGHT_LINES:
            by_formula[(r['Formula Code'], r['Variant'], r['Line Code'])].append(r)
    rec_by_key = {}
    for (code, var, line), rows in sorted(by_formula.items()):
        ext_rows = defaultdict(list)
        for r in rows:
            ext_rows[r['Extruder'] or ''].append(r)
        for ext, rs in ext_rows.items():
            autos = [r for r in rs if str(r['Set']).strip().lower() == 'auto']
            fixed = [(r, num(r['Set'])) for r in rs if r not in autos]
            for r, pct in fixed + [(a, round(100 - sum(p for _, p in fixed if p is not None), 4)) for a in autos[:1]]:
                key = (code, var, ext, r['Material ID'] or r['_mat'])
                out = {'Formula Code': code, 'Variant': var, 'Extruder': ext or None, 'Material ID': r['Material ID'],
                       'Weight %': None if r in autos else pct, 'Balance': 'Yes' if r in autos else 'No',
                       'Note': f"from {line} {r['_from']}" + (f' (Auto = {pct:g})' if r in autos else '')}
                if key in rec_by_key and (rec_by_key[key]['Weight %'], rec_by_key[key]['Balance']) != (out['Weight %'], out['Balance']):
                    issues.append(('Medium', 'Recipe', line, '', 'One formula, different weight % on two weight lines',
                                   f"{code} {var} {ext} {r['_mat']}: {rec_by_key[key]['Note']} vs {out['Note']}; first kept", 'FRM'))
                    continue
                rec_by_key[key] = out
    recipe = list(rec_by_key.values())
    if recipe and any(r['Material ID'] is None for r in recipe):
        pass  # 'PP Virgin' only on SE23 (auger): no weight-line recipe row lacks an ID today

    form_rows = [{'Formula Code': c, 'Variant': v, 'Family': c[:2], 'Description': None,
                  'When to Use': rec['note'] or None, 'Status': 'Draft', 'Approved By': None, 'Approved Date': None,
                  'Seeded From': f"FRM {', '.join(sorted(rec['dates']))} ({', '.join(sorted(rec['lines']))})"}
                 for (c, v), rec in sorted(formulas.items())]
    p2f_rows = [{'Product Code': p, 'Line Code': ln, 'Formula Code': c, 'Variant': v, 'Priority': e['priority'],
                 'Last Run': datetime.date.fromisoformat(e['last']), 'Status': 'Draft', 'Approved By': None, 'Approved Date': None}
                for (p, ln, c, v), e in sorted(p2f.items())]
    lines_rows = []
    import auger_rules
    for code, no, layout, ext, acv in schema.LINES:
        n = notes.get(code)
        lines_rows.append({'Line Code': code, 'Line No': no, 'Dosing': auger_rules.DOSING[code], 'Feeder Layout': layout,
                           'Extruders': ext, 'AC': (n[2].replace('AC = ', '') if n and n[2] else acv) or None,
                           'Form Effective Date': n[3] if n else None, 'Active': 'Yes'})
    std = [{'Line Code': ln, 'No': i, 'Note': t} for ln, (d, fn, *_) in sorted(notes.items()) for i, t in enumerate(fn, 1)]
    for sev, texts, check, detail in MAP_ISSUES:
        lines = sorted({r['Line Code'] for r in line_settings if r['_mat'] in texts})
        if lines:
            issues.append((sev, 'Materials', ', '.join(lines), '', check, detail, 'IWPFT062 vs FRM'))
    return {'rev': rev, 'dates': dates, 'Lines': lines_rows, 'Materials': materials, 'Formulas': form_rows,
            'Recipe': recipe, 'Line Settings': line_settings, 'Product to Formula': p2f_rows, 'Standing Notes': std,
            'issues': issues}


def write(data, out):
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    book = schema.BY_NAME[schema.FM]
    hfont, hfill, body = Font(name='Arial', size=10, bold=True, color='FFFFFF'), PatternFill('solid', fgColor='1F3864'), Font(name='Arial', size=10)
    wb = Workbook()
    wb.remove(wb.active)
    MAXR = 5000
    refcol = {}   # 'Sheet/Column' -> 'Sheet!$A$2:$A$5000'
    for s in book.sheets:
        for i, c in enumerate(s.cols, 1):
            refcol[f'{s.name}/{c.name}'] = f"'{s.name}'!${get_column_letter(i)}$2:${get_column_letter(i)}${MAXR}"
    rows_for = dict(data)
    rows_for['Issues'] = [dict(zip(['Severity', 'Document', 'Line', 'Order', 'Check', 'Detail', 'Source'], x)) for x in
                          sorted(data['issues'], key=lambda x: ['High', 'Medium', 'Low', 'Info'].index(x[0]))]
    rows_for['Change Log'] = []
    rows_for['Read Me'] = [{'Item': a, 'Value': b} for a, b in readme(data)]
    for s in book.sheets:
        ws = wb.create_sheet(s.name)
        header = [c.name for c in s.cols]
        ws.append(header)
        for c in ws[1]:
            c.font, c.fill = hfont, hfill
        for r in rows_for.get(s.name, []):
            ws.append([r.get(h) for h in header])
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.font = body
                if isinstance(cell.value, (datetime.date, datetime.datetime)):
                    cell.number_format = 'yyyy-mm-dd'
        for i, c in enumerate(s.cols, 1):
            L = get_column_letter(i)
            ws.column_dimensions[L].width = {'Note': 50, 'Detail': 90, 'Why': 40, 'When to Use': 45, 'Name': 30,
                                             'FRM Text': 40, 'Other Spellings': 50, 'Approved Substitutes': 45,
                                             'Seeded From': 40, 'Value': 110, 'Item': 30, 'Check': 36}.get(c.name, max(11, min(24, len(c.name) + 3)))
            if c.note:
                ws.cell(1, i).comment = Comment(c.note, 'schema')
            dv = None
            if c.values:
                dv = DataValidation(type='list', formula1='"' + ','.join(c.values) + '"', allow_blank=not c.required)
            elif c.ref and c.ref.startswith(schema.FM + '/'):
                _, rs, rc = c.ref.split('/')
                dv = DataValidation(type='list', formula1='=' + refcol[f'{rs}/{rc}'], allow_blank=True)
            if dv:
                dv.error, dv.errorTitle = f'Choose a value from the list ({c.name}).', 'Not on the list'
                dv.showErrorMessage = True
                ws.add_data_validation(dv)
                dv.add(f'{L}2:{L}{MAXR}')
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = f'A1:{get_column_letter(len(header))}{max(2, ws.max_row)}'
    wb.security.lockStructure = True   # sheets cannot be added, deleted or renamed; cells stay editable (no password)
    wb.save(out)


def readme(data):
    n = {k: len(data[k]) for k in ('Lines', 'Materials', 'Formulas', 'Recipe', 'Line Settings', 'Product to Formula', 'Standing Notes')}
    yield 'Workbook', 'Formulation Master.xlsx: the approved formulations. DRAFT: seeded 28 Sep 2026; nothing here is approved until Tech approves it.'
    yield 'How to change it', ('Edit the cell in Excel, then add a row to Change Log: Change ID (next number), Date, Sheet, Row Key (the key '
                              'columns joined by "|", e.g. SE24|FUA152WB4|Primary|A|V1), Field (column name, or "(new row)" / "(row removed)"), '
                              'Old Value, New Value, Why, Requested By, Approved By. The next pipeline run compares the master with the last '
                              'version it accepted; any changed cell without a matching approved Change Log row STOPS the run and is listed.')
    yield 'Who approves', 'Formulas and slopes: Tech. Rules (dosing, R1/R2, hopper roles): James Kuo. (James, 28 Sep 2026)'
    yield 'Drop-down lists', 'Coded columns (Line, Material ID, Formula Code, Variant, Status ...) only accept values from their lists. Sheets cannot be added, renamed or deleted (Review > Protect Workbook, no password).'
    yield 'Material ID', f'IWPFT062 Material No. (James, 28 Sep 2026), from IWPFT062 Rev {data["rev"]}. INT- = plant material (reclaim, premix); NL- = used on the FRM but not on IWPFT062.'
    yield 'Seeded from', f"Tech's issued FRM pages, packets {', '.join(data['dates'])}: latest issue wins; changes between packets are on Issues."
    yield 'Recipe', 'Weight lines only (SE24, SE42, SE43, SE61: Set = weight %, Auto = balance). Auger-line recipes need the calibration slopes from Tech\'s calc workbooks (not on this PC yet).'
    yield 'Line Settings', 'Set as printed on the FRM. Auger lines: motor speed 0-100, not %.'
    yield 'Variants', 'Primary, Reclaim run-out, VOIDFORM, Sign blank, Corn box, Roll, Other (James, 28 Sep 2026). From the FRM row note; a second formula with no note = Other.'
    yield 'Rows', ', '.join(f'{k} {v}' for k, v in n.items())
    for k, v in config.reads().items():
        if 'packet_' in k or 'IWPFT062' in k:
            yield f'Source read: {Path(k).name}', f"{v['modified']} · sha256 {v['sha256'][:16]}"


def main():
    data = build()
    out = config.OUTPUT_DIR / schema.FM
    write(data, out)
    from collections import Counter
    print(out, '-', ', '.join(f'{k} {len(data[k])}' for k in ('Materials', 'Formulas', 'Recipe', 'Line Settings', 'Product to Formula')),
          '| issues', dict(Counter(i[0] for i in data['issues'])))


if __name__ == '__main__':
    main()
