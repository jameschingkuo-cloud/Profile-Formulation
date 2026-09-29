"""The master's Materials follow IWPFT062 (James Kuo, 29 Sep 2026: "doc T062 is correct. Master should match it").

    python db/sync_iwpft062.py            list every difference between IWPFT062 and the master's Materials (exit 1 if any)
    python db/sync_iwpft062.py --apply    make the master match, one Change Log row per change, then:
                                          publish.py, preflight check, preflight accept

Compared for every IWPFT062 row: Material ID (= Material No.), Material Code, Name, Supplier, IWPFT062 Status, and the
further approved sources (IWPFT062 §4) in Approved Substitutes. A row IWPFT062 no longer lists is set to IWPFT062 Status
"Withdrawn" (never deleted). Master-only columns (Role, FRM Text, Other Spellings, Bulk Density, Status) and the
plant-internal INT- / not-listed NL- rows are left alone. IWPFT062 is read only, where it lives.
"""
import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from db import preflight, schema  # noqa: E402
from db.seed_master import IWPFT062, read_iwpft062, role_for  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

NAME = schema.FM
WHO = 'James Kuo'


def expected():
    try:
        rev, iw = read_iwpft062()
    except PermissionError:
        raise SystemExit(f'IWPFT062 is locked (open in Word, or syncing): {IWPFT062.name}. Close it and run again.')
    out = {}
    for mid, m in iw.items():
        out[mid] = {'Material Code': m['code'], 'Name': m['name'], 'Supplier': m['sup'], 'IWPFT062 Status': m['status'],
                    'Approved Substitutes': ' | '.join(m['subs']) or None}
    return rev, out


def diff(ws, exp):
    h = {c.value: i for i, c in enumerate(ws[1], 1)}
    have = {ws.cell(r, h['Material ID']).value: r for r in range(2, ws.max_row + 1) if ws.cell(r, h['Material ID']).value}
    changes = []   # (material id, field, old, new, row or None)
    for mid, fields in exp.items():
        r = have.get(mid)
        if r is None:
            changes.append((mid, '(new row)', None, f"{fields['Material Code']} {fields['Name']} ({fields['Supplier']}, {fields['IWPFT062 Status']})", None))
            continue
        for f, v in fields.items():
            old = ws.cell(r, h[f]).value
            if (old or None) != (v or None):
                changes.append((mid, f, old, v, r))
    for mid, r in have.items():
        if mid in exp or str(mid).startswith(('INT-', 'NL-')):
            continue
        if ws.cell(r, h['IWPFT062 Status']).value != 'Withdrawn':
            changes.append((mid, 'IWPFT062 Status', ws.cell(r, h['IWPFT062 Status']).value, 'Withdrawn', r))
    return h, changes


def main(argv):
    apply = '--apply' in argv
    rev, exp = expected()
    ok, lines, _ = preflight.check(NAME)
    if ok is False:
        print('\n'.join(lines))
        raise SystemExit('STOP: the published master has unaccepted changes; settle those first.')
    src = config.published_path(NAME)
    wb = load_workbook(src)
    h, changes = diff(wb['Materials'], exp)
    print(f'IWPFT062 Rev {rev} vs {NAME} Materials: {len(changes)} difference(s)')
    for mid, f, old, new, _ in changes:
        print(f'  {mid} | {f}: {old!r} -> {new!r}')
    if not changes or not apply:
        raise SystemExit(1 if changes else 0)
    out = config.OUTPUT_DIR / NAME
    shutil.copy(src, out)
    wb = load_workbook(out)
    ws, log = wb['Materials'], wb['Change Log']
    nid = max([r[0] for r in log.iter_rows(min_row=2, values_only=True) if isinstance(r[0], int)] or [0]) + 1
    why = f'Standing rule (James Kuo, 29 Sep 2026): the master matches IWPFT062 (Rev {rev})'
    today = datetime.date.today()
    for mid, f, old, new, r in changes:
        if r is None:
            e = exp[mid]
            row = [None] * len(h)
            for col, v in list(e.items()) + [('Material ID', mid), ('Role', role_for(e['Material Code'], e['Name'])), ('Status', 'Draft')]:
                row[h[col] - 1] = v
            ws.append(row)
        else:
            ws.cell(r, h[f]).value = new
        log.append([nid, today, 'Materials', mid, f, old, new, why, WHO, WHO, f'IWPFT062 Rev {rev}'])
        nid += 1
    wb.save(out)
    print(out, f'- {len(changes)} change(s) logged')


if __name__ == '__main__':
    main(sys.argv[1:])
