"""Edit cells in the Formulation Master, every edit logged in its Change Log (DATABASE.md §7).

    python db/edit_master.py --by "James Kuo" --why "..." \\
        --set "Materials" "50-7002-430" "FRM Text" "FOAM – Bergen X0-256" [--set ...] \\
        [--issue "text in the Issues detail" --issue-sev Info --issue-check "..." --issue-detail "..."]

Row keys are the sheet's key columns joined by '|' (as in the Change Log). Key columns cannot be edited here
(that is a row removal + addition: see db/replace_material.py). Works on a copy of the published master in out/; then
publish.py, preflight check, preflight accept. Only on James's or Tech's instruction.
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
    ap.add_argument('--by', required=True); ap.add_argument('--why', required=True); ap.add_argument('--source', default='')
    ap.add_argument('--set', nargs=4, action='append', required=True, metavar=('SHEET', 'ROWKEY', 'FIELD', 'VALUE'))
    ap.add_argument('--issue'); ap.add_argument('--issue-sev'); ap.add_argument('--issue-check'); ap.add_argument('--issue-detail')
    a = ap.parse_args(argv)
    ok, lines, _ = preflight.check(NAME)
    if not ok:
        print('\n'.join(lines))
        raise SystemExit('STOP: the published master has unaccepted changes; settle those first.')
    book = schema.BY_NAME[NAME]
    out = config.OUTPUT_DIR / NAME
    shutil.copy(config.published_path(NAME), out)
    wb = load_workbook(out)
    log = wb['Change Log']
    nid = max([r[0] for r in log.iter_rows(min_row=2, values_only=True) if isinstance(r[0], int)] or [0]) + 1
    first, today = nid, datetime.date.today()
    for sheet, rk, field, value in a.set:
        s = next((x for x in book.sheets if x.name == sheet), None)
        if not s:
            raise SystemExit(f'No sheet {sheet!r}')
        keys = [c.name for c in s.cols if c.key] or [s.cols[0].name]
        if field in keys:
            raise SystemExit(f'{field!r} is a key column of {sheet}: use a row removal + addition')
        ws = wb[sheet]
        h = {c.value: i for i, c in enumerate(ws[1], 1)}
        if field not in h:
            raise SystemExit(f'No column {field!r} in {sheet}')
        rows = [r for r in range(2, ws.max_row + 1)
                if '|'.join('' if ws.cell(r, h[k]).value is None else str(ws.cell(r, h[k]).value) for k in keys) == rk]
        if len(rows) != 1:
            raise SystemExit(f'{sheet} row {rk!r}: found {len(rows)} rows, expected 1. Nothing written.')
        old = ws.cell(rows[0], h[field]).value
        if str(old or '') == value:
            print(f'  unchanged {sheet} | {rk} | {field}')
            continue
        ws.cell(rows[0], h[field]).value = value
        log.append([nid, today, sheet, rk, field, old, value, a.why, a.by, a.by, a.source or None])
        nid += 1
    if a.issue:
        ws = wb['Issues']
        h = {c.value: i for i, c in enumerate(ws[1], 1)}
        for r in range(2, ws.max_row + 1):
            if a.issue in str(ws.cell(r, h['Detail']).value or ''):
                for col, v in (('Severity', a.issue_sev), ('Check', a.issue_check), ('Detail', a.issue_detail)):
                    if v:
                        ws.cell(r, h[col]).value = v
                ws.cell(r, h['James / Tech response']).value = f'{a.why} ({a.by})'
    wb.save(out)
    print(out, f'- Changes {first}-{nid - 1} logged' if nid > first else '- nothing changed')


if __name__ == '__main__':
    main(sys.argv[1:])
