"""Add what one day's issued FRM (Tech's pages, in the packet) has that the Formulation Master does not, as Draft rows,
every row logged in the Change Log (James Kuo, 29 Sep 2026, on Tech's 29 Sep FRM: "update your data base with it").

    python db/import_frm.py --date 2026-09-29 --by "James Kuo" --why "..."   [--dry-run]

Adds, never changes:
  - Formulas            (code, variant) not in the master
  - Line Settings       (line, code, variant, extruder, feeder) not in the master
  - Product to Formula  (product, line, code, variant) not in the master (first formula of an order = Primary)
A printed material is mapped through the master's Materials (FRM Text / Other Spellings); a replaced material
(checks.REPLACED, e.g. F1102K -> F1203K) is recorded as its replacement. A material with no mapping is NOT written:
its setting is listed for James (add the spelling in Materials first, then run again). A setting that differs from the
master's is listed, not applied (settings change only on Tech's / James's say-so, via db/edit_master.py).
Works on a copy of the published master in out/; then publish.py, preflight check, preflight accept.
"""
import argparse
import ast
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'daily'))
import config  # noqa: E402
from db import preflight, schema  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from resolve import split_feeder, variant  # noqa: E402

NAME = schema.FM


def replaced():
    """checks.REPLACED without running checks.py: printed text -> Material ID of what it is now."""
    tree = ast.parse((ROOT / 'daily' / 'checks.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'REPLACED' for t in node.targets):
            return {k: re.search(r'\d{2}-\d{4}-\d{3}', v[0]).group(0) for k, v in ast.literal_eval(node.value).items()}
    return {}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True); ap.add_argument('--by', required=True); ap.add_argument('--why', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    pkp = config.PACKETS_DIR / f'packet_{a.date}.json'
    config.record_read(pkp, 'daily packet (FRM as issued)')
    pk = json.loads(pkp.read_text(encoding='utf-8'))
    if not pk.get('frm'):
        raise SystemExit(f'No FRM pages in the {a.date} packet: nothing to import.')
    ok, lines, (cur, _) = preflight.check(NAME)
    if not ok:
        print('\n'.join(lines))
        raise SystemExit('STOP: the published master has unaccepted changes (or no accepted version); settle that first.')

    spell = {}
    for mid, m in sorted(cur['Materials'].items(), key=lambda kv: kv[1].get('Status') != 'Retired'):   # active rows win
        for t in [m.get('FRM Text')] + str(m.get('Other Spellings') or '').split(' | '):
            if t and t.strip():
                spell[t.strip()] = mid
    spell.update(replaced())
    # XO-256 is a misprint of X0-256 (James Kuo, 29 Sep 2026: "Unless you have mroe XO then change them to X0")
    spell = {**{k.replace('X0-256', 'XO-256'): v for k, v in spell.items() if 'X0-256' in k}, **spell}
    prod = {r['order']: r['prod_code'] for pg in pk['ext'] for r in pg['rows']}
    have_f = {(f['Formula Code'], f['Variant']) for f in cur['Formulas'].values()}
    have_s = {(s['Line Code'], s['Formula Code'], s['Variant'], s['Extruder'] or '', s['Feeder']): s for s in cur['Line Settings'].values()}
    have_p = {(p['Product Code'], p['Line Code'], p['Formula Code'], p['Variant']) for p in cur['Product to Formula'].values()}
    day = datetime.date.fromisoformat(a.date)
    src = f"FRM {a.date} ({pk.get('frm_source_scan') or pk.get('source_scan')})"

    add = {'Formulas': [], 'Line Settings': [], 'Product to Formula': []}
    unmapped, differs = [], []
    for pg in pk['frm']:
        line = pg['line_code']
        for g in pg['groups']:
            for i, f in enumerate(g['formulas']):
                code, var = f['formula_code'], variant(f.get('note', ''), i == 0)
                if (code, var) not in have_f:
                    have_f.add((code, var))
                    add['Formulas'].append({'Formula Code': code, 'Variant': var, 'Family': code[:2], 'When to Use': f.get('note') or None,
                                            'Status': 'Draft', 'Seeded From': f'{src} p{pg["scan_page"]} ({line})'})
                for c, v in f['feeders'].items():
                    if not (v.get('material') or v.get('set')):
                        continue
                    ext, feeder = split_feeder(c)
                    k = (line, code, var, ext, feeder)
                    mid = spell.get((v.get('material') or '').strip())
                    if k in have_s:
                        s = have_s[k]
                        if (s['Material ID'], str(s['Set'])) != (mid, str(v.get('set'))):
                            differs.append(f"{line} {code} {var} {ext} {feeder}: master {s['Material ID']} {s['Set']} vs FRM {v.get('material')} {v.get('set')}")
                        continue
                    if not mid:
                        unmapped.append(f"{line} {code} {var} {ext} {feeder}: \"{v.get('material')}\" {v.get('set')} (orders {', '.join(g['orders'])})")
                        continue
                    have_s[k] = {'Material ID': mid, 'Set': v.get('set')}
                    add['Line Settings'].append({'Line Code': line, 'Formula Code': code, 'Variant': var, 'Extruder': ext or None,
                                                 'Feeder': feeder, 'Material ID': mid, 'Set': v.get('set'), 'Source': 'FRM', 'Status': 'Draft'})
                for o in g['orders']:
                    p = prod.get(o)
                    if p and (p, line, code, var) not in have_p:
                        have_p.add((p, line, code, var))
                        add['Product to Formula'].append({'Product Code': p, 'Line Code': line, 'Formula Code': code, 'Variant': var,
                                                          'Priority': 'Primary' if i == 0 else 'Alternate', 'Last Run': day, 'Status': 'Draft'})

    for sheet, rows in add.items():
        for r in rows:
            print(f'ADD {sheet}: ' + ' | '.join(f'{k}={v}' for k, v in r.items() if v not in (None, '')))
    for u in unmapped:
        print('NOT WRITTEN (material not mapped): ' + u)
    for d in differs:
        print('DIFFERS (not applied): ' + d)
    if a.dry_run or not any(add.values()):
        print('dry run - nothing written' if a.dry_run else 'nothing to add')
        return add, unmapped, differs

    out = config.OUTPUT_DIR / NAME
    shutil.copy(config.published_path(NAME), out)
    wb = load_workbook(out)
    log = wb['Change Log']
    nid = max([r[0] for r in log.iter_rows(min_row=2, values_only=True) if isinstance(r[0], int)] or [0]) + 1
    first = nid
    keys = {s.name: [c.name for c in s.cols if getattr(c, 'key', False)] for s in schema.BY_NAME[NAME].sheets}
    for sheet, rows in add.items():
        ws = wb[sheet]
        h = {c.value: j for j, c in enumerate(ws[1], 1)}
        kc = keys.get(sheet) or {'Formulas': ['Formula Code', 'Variant'],
                                 'Line Settings': ['Line Code', 'Formula Code', 'Variant', 'Extruder', 'Feeder'],
                                 'Product to Formula': ['Product Code', 'Line Code', 'Formula Code', 'Variant']}[sheet]
        for r in rows:
            vals = [None] * len(h)
            for k, v in r.items():
                vals[h[k] - 1] = v
            ws.append(vals)
            log.append([nid, day, sheet, '|'.join(str(r.get(k) or '') for k in kc), '(new row)', None,
                        ', '.join(f'{k} {r[k]}' for k in ('Material ID', 'Set', 'Priority') if r.get(k)) or r.get('Status'),
                        a.why, a.by, a.by, src])
            nid += 1
    wb.save(out)
    print(out, f'- Changes {first}-{nid - 1} logged')
    return add, unmapped, differs


if __name__ == '__main__':
    main(sys.argv[1:])
