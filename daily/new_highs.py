"""High issues on a day's workbooks that the previous day did not have: the scheduled email run stops before publishing
when there is one (James Kuo, 6 Oct 2026: "Full run, stop on new High").

    python daily/new_highs.py <date>      exit 1 when there is a new High, else 0

Reads the Issues sheets of out/EXT Extrusion Schedule, CNV Converting Schedule and FRM * workbooks of the date and of
the previous packet date. A High is the same as yesterday's when its document, line, order and check match (the detail
may change, e.g. a count). "No formula to propose" (a new order without an issued formula) is not counted: it is the
Word formulation's ENGINEER TO COMPLETE row, reported with step 1 every day.
"""
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

EXPECTED = {'No formula to propose'}


def highs(date):
    out = {}
    for pat in (f'EXT Extrusion Schedule {date}.xlsx', f'CNV Converting Schedule {date}.xlsx', f'FRM * {date}.xlsx'):
        for f in sorted(config.OUTPUT_DIR.glob(pat)):
            wb = openpyxl.load_workbook(f, read_only=True)
            for ws in wb:
                if ws.title != 'Issues':
                    continue
                rows = list(ws.iter_rows(values_only=True))
                h = [str(c or '') for c in rows[0]]
                for r in rows[1:]:
                    d = dict(zip(h, (str(c or '') for c in r)))
                    if d.get('Severity') == 'High' and d.get('Check') not in EXPECTED:
                        key = (d.get('Document'), d.get('Line'), d.get('Order'), d.get('Check'))
                        out.setdefault(key, (f.name, d.get('Detail', '')))
            wb.close()
    return out


def previous_date(date):
    days = sorted(p.stem.replace('packet_', '') for p in config.PACKETS_DIR.glob('packet_*.json'))
    days = [d for d in days if d < date]
    return days[-1] if days else None


def main(argv):
    date = argv[0]
    prev = previous_date(date)
    today, before = highs(date), (highs(prev) if prev else {})
    new = {k: v for k, v in today.items() if k not in before}
    print(f'{date}: {len(today)} High (not counting "No formula to propose"); {len(today) - len(new)} also on {prev}; {len(new)} new')
    for (doc, line, order, check), (f, detail) in new.items():
        print(f'  NEW High | {doc} | {line} | {order} | {check} | {detail} ({f})')
    return 1 if new else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
