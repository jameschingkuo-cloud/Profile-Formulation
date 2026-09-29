"""Replace one material with another in the Formulation Master, every edit logged in its Change Log (DATABASE.md §7).

    python db/replace_material.py OLD_ID NEW_ID --by "James Kuo" --why "..." [--spelling "FRM text"] [--source "..."]
                                  [--issue "text in the Issues detail" --issue-sev Medium --issue-detail "..."]

Works on a copy of the published master in out/: Line Settings (Material ID), Recipe (Material ID is part of the key,
so the row is logged as removed and added back), the old material is set Retired with a note (never deleted);
--spelling adds an FRM spelling to the new material's Other Spellings. Then:
    python publish.py "Formulation Master.xlsx"
    python db/preflight.py check  "Formulation Master.xlsx"     every change must match an approved log row
    python db/preflight.py accept "Formulation Master.xlsx"
Only on James's or Tech's instruction; the person goes in Requested By and Approved By.
"""
import argparse
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from db import preflight, schema  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

NAME = schema.FM


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('old'); ap.add_argument('new')
    ap.add_argument('--by', required=True); ap.add_argument('--why', required=True)
    ap.add_argument('--spelling'); ap.add_argument('--source', default='')
    ap.add_argument('--issue'); ap.add_argument('--issue-sev'); ap.add_argument('--issue-detail'); ap.add_argument('--issue-check')
    a = ap.parse_args(argv)

    ok, lines, _ = preflight.check(NAME)
    if not ok:
        print('\n'.join(lines))
        raise SystemExit('STOP: the published master has unaccepted changes; settle those first.')
    pub = config.published_path(NAME)
    out = config.OUTPUT_DIR / NAME
    shutil.copy(pub, out)
    wb = load_workbook(out)
    log = wb['Change Log']
    ids = [r[0] for r in log.iter_rows(min_row=2, values_only=True) if isinstance(r[0], int)]
    state = {'next': max(ids or [0]) + 1, 'first': None}
    today = datetime.date.today()

    def cols(ws):
        return {c.value: i for i, c in enumerate(ws[1], 1)}

    def key(ws, row, names):
        h = cols(ws)
        return '|'.join('' if ws.cell(row, h[n]).value is None else str(ws.cell(row, h[n]).value) for n in names)

    def logrow(sheet, rk, field, old, new):
        log.append([state['next'], today, sheet, rk, field, old, new, a.why, a.by, a.by, a.source or None])
        state['first'] = state['first'] or state['next']
        state['next'] += 1

    mats = {r[0] for r in wb['Materials'].iter_rows(min_row=2, values_only=True)}
    if a.old not in mats or a.new not in mats:
        raise SystemExit(f'Both materials must be in Materials: {a.old} {"ok" if a.old in mats else "MISSING"}, '
                         f'{a.new} {"ok" if a.new in mats else "MISSING"}')

    ws = wb['Line Settings']; h = cols(ws)
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, h['Material ID']).value == a.old:
            rk = key(ws, r, ['Line Code', 'Formula Code', 'Variant', 'Extruder', 'Feeder'])
            ws.cell(r, h['Material ID']).value = a.new
            logrow('Line Settings', rk, 'Material ID', a.old, a.new)

    ws = wb['Recipe']; h = cols(ws)
    k = ['Formula Code', 'Variant', 'Extruder', 'Material ID']
    existing = {key(ws, r, k) for r in range(2, ws.max_row + 1)}
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, h['Material ID']).value == a.old:
            old_rk = key(ws, r, k)
            new_rk = old_rk.rsplit('|', 1)[0] + '|' + a.new
            if new_rk in existing:
                raise SystemExit(f'STOP: Recipe already has {new_rk}; merging two rows needs an engineer. Nothing written.')
            ws.cell(r, h['Material ID']).value = a.new
            logrow('Recipe', old_rk, '(row removed)', a.old, None)
            logrow('Recipe', new_rk, '(new row)', None, a.new)

    ws = wb['Materials']; h = cols(ws)
    for r in range(2, ws.max_row + 1):
        mid = ws.cell(r, h['Material ID']).value
        if mid == a.new and a.spelling:
            old = ws.cell(r, h['Other Spellings']).value
            if a.spelling not in (old or '').split(' | ') and a.spelling != ws.cell(r, h['FRM Text']).value:
                new = ' | '.join(x for x in [old, a.spelling] if x)
                ws.cell(r, h['Other Spellings']).value = new
                logrow('Materials', a.new, 'Other Spellings', old, new)
        if mid == a.old:
            for field, new in (('Status', 'Retired'),
                               ('Approved Substitutes', f'Replaced by {a.new} ({a.by}, {today:%d %b %Y})')):
                old = ws.cell(r, h[field]).value
                if old != new:
                    ws.cell(r, h[field]).value = new
                    logrow('Materials', a.old, field, old, new)

    if a.issue:
        ws = wb['Issues']; h = cols(ws)
        for r in range(2, ws.max_row + 1):
            if a.issue in str(ws.cell(r, h['Detail']).value or ''):
                if a.issue_sev: ws.cell(r, h['Severity']).value = a.issue_sev
                if a.issue_check: ws.cell(r, h['Check']).value = a.issue_check
                if a.issue_detail: ws.cell(r, h['Detail']).value = a.issue_detail
                ws.cell(r, h['James / Tech response']).value = f'{a.why} ({a.by})'
    wb.save(out)
    print(out, f"- Changes {state['first']}-{state['next'] - 1} logged" if state['first'] else '- nothing to change')


if __name__ == '__main__':
    main(sys.argv[1:])
