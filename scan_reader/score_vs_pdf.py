"""Score a scan reader's output against the system's own PDF of the same report (James Kuo, 1 Oct 2026: "the main goal is
to improve the OCR read and logic check when OCR read failed"). The PDF is exact, so every field is right or wrong.

    python scan_reader/score_vs_pdf.py <reader csv (ext_scan_reader.py read ...)> <BPN9PFR / MMDDYY .PDF> [--show]

Per field: right / wrong / not read. Special instructions are scored two ways: exact (as printed, spacing collapsed) and
letters+digits only. Rows are matched by position on the page (scan page order = report order), so an order number
misread under handwriting still lines up with its truth.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from correct_from_system_pdf import system_rows  # noqa: E402

FIELDS = ['line', 'order', 'prod', 'die', 'thk', 'gsm', 'mat', 'grade', 'spec', 'colors', 'special', 'special (letters+digits)']


def score(csv_path, pdf, show=False):
    info, S = system_rows(Path(pdf))
    truth = list(S.values())                       # report order
    R = list(csv.DictReader(open(csv_path, encoding='utf-8')))
    # align by order where read, else by position
    by_order = {s['order']: s for s in truth}
    used, pairs = set(), []
    for i, r in enumerate(R):
        s = by_order.get(r['order'])
        if s is None and i < len(truth) and truth[i]['order'] not in {x['order'] for x in R}:
            s = truth[i]
        pairs.append((r, s))
    sp = lambda x: ' / '.join(re.sub(r'\s+', ' ', y).strip() for y in (x or '').split(' / ') if y.strip())
    ld = lambda x: re.sub(r'[^A-Z0-9]', '', (x or '').upper())
    c, ex = defaultdict(Counter), defaultdict(list)
    for r, s in pairs:
        if s is None:
            c['order']['wrong'] += 1
            continue
        t = {'line': s['line'], 'order': s['order'], 'prod': s['prod_code'], 'die': s['die'], 'thk': f"{float(s['thk']):.1f}",
             'gsm': str(s['gsm']), 'mat': s['mat'].split()[0], 'grade': s['mat'].split()[1], 'spec': s['mat_spec'], 'colors': s['colour'],
             'special': sp(s['special']), 'special (letters+digits)': ld(s['special'])}
        g = dict(r)
        g['thk'] = f"{float(r['thk']):.1f}" if r.get('thk') else ''
        g['special'] = sp(r.get('special', '').replace(' | ', ' / '))
        g['special (letters+digits)'] = ld(r.get('special'))
        for f in FIELDS:
            a, b = g.get(f, ''), t[f]
            if not a and b:
                c[f]['not read'] += 1; ex[f].append((s['order'], '(blank)', b))
            elif a == b:
                c[f]['right'] += 1
            else:
                c[f]['wrong'] += 1; ex[f].append((s['order'], a, b))
    print(f"{Path(csv_path).name} vs {Path(pdf).name} (run {info['run_date']} {info['run_time']}): {len(R)} rows read, {len(truth)} in the report")
    for f in FIELDS:
        n = sum(c[f].values())
        print(f"  {f:<26} right {c[f]['right']:>3}  wrong {c[f]['wrong']:>3}  not read {c[f]['not read']:>3}   ({100 * c[f]['right'] / n:.0f}%)" if n else f'  {f}: -')
    if show:
        for f in FIELDS:
            for x in ex[f]:
                print('   ', f, '|', x[0], '|', str(x[1])[:100], '||', str(x[2])[:100])
    return c


if __name__ == '__main__':
    score(sys.argv[1], sys.argv[2], '--show' in sys.argv)
