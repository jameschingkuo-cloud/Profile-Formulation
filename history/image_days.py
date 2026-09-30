"""Schedule days kept only as image scans in the Production Instruction folder (050820, 111323, 111423; James Kuo,
30 Sep 2026: "if its scan, OCR them", "if it needs to be rotated, rotate them"). Read with the checks the system text
allows, never guessed:

  1. each page is turned upright (work/history/scans/<name>.pdf, turned by reading the title) and rendered at 300 dpi;
  2. order + product: the two-reader rule of ui/ocr_eval.py (Tesseract + glyph bank), history = the orders on the
     system's own schedules on the days either side;
  3. the row's figures (total sheets per cut, weight, pallets, pcs/stack): the same order on the neighbouring day's
     system text gives them; they are taken only when every one of them is found in this day's OCR of the row;
  4. "NNN PLTS DONE": read by OCR, taken only when it lies between the neighbouring days' counts;
  5. everything else is listed for a person (work/history/image_days_check.csv) and not recorded until checked.

    python history/image_days.py      -> work/history/ext_history_scans.csv (+ image_days_check.csv)
"""
import csv
import datetime
import re
import sys
from pathlib import Path

import numpy as np
import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'ui'))
sys.path.insert(0, str(ROOT / 'history'))
import config  # noqa: E402
import ocr_eval as P  # noqa: E402
import prod_instr as H  # noqa: E402

DAYS = {'050820': '2020-05-08', '111323': '2023-11-13', '111423': '2023-11-14'}
HIST = config.WORK_DIR / 'history' / 'ext_history.csv'
PLTS_DONE = re.compile(r'(\d[\d,]*)\s*PLTS?\s+DONE', re.I)


def neighbours(rows, day, n=2):
    days = sorted({r['date'] for r in rows})
    before = [d for d in days if d < day][-n:]
    after = [d for d in days if d > day][:n]
    return before, after


def fmt(v):
    return f'{int(v):,}' if str(v).isdigit() else str(v)


def main():
    hist = list(csv.DictReader(open(HIST, encoding='utf-8')))
    codes_by_len = {}
    for c in P.PRODS:
        codes_by_len.setdefault(len(c), []).append(c)
    out, check = [], []
    for name, day in DAYS.items():
        before, after = neighbours(hist, day)
        near = [r for r in hist if r['date'] in before + after]
        pairs = {(r['order'], r['prod_code']) for r in near}
        by_order = {}
        for r in sorted(near, key=lambda r: r['date']):
            by_order.setdefault(r['order'], []).append(r)
        pdir = config.WORK_DIR / 'pages' / f'scan_{name}'
        if not pdir.exists():
            import subprocess
            subprocess.run([sys.executable, str(ROOT / 'scan_reader' / 'render_pages.py'),
                            str(config.WORK_DIR / 'history' / 'scans' / f'{name}.pdf'), str(pdir)], check=True)
        for png in sorted(pdir.glob('p[0-9][0-9].png')):
            im = Image.open(png).convert('L')
            a = np.asarray(im)
            h, w = a.shape
            line, lreads = P.read_line_code2(im)
            rows = []
            for (y0, y1) in [b for b in P.row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
                bars = P.row_bars(a, y0, y1, w)
                if bars:
                    rows.append((y0, y1, bars))
            if not rows:
                continue
            pitch = P.XR.estimate_pitch([a[max(0, y0 - 6):y1 + 6, b[0] + 4:b[2] - 4] for y0, y1, b in rows])
            for k, (y0, y1, bars) in enumerate(rows):
                to, tp, go, gp, raws = P.read_row_both(im, a, pitch, y0, y1, bars, codes_by_len, w)
                if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)):
                    continue
                o, p_, st = P.decide(to, tp, go, gp, pairs, datetime.date.fromisoformat(day))
                y_next = rows[k + 1][0] - 12 if k + 1 < len(rows) else min(h, y1 + 700)
                block = pytesseract.image_to_string(im.crop((0, max(0, y0 - 10), w, y_next)), config='--psm 6')
                flat = re.sub(r'\s+', ' ', block)
                if st == 'check' or not o or not p_:
                    # the neighbouring days' rows (same line when known) with the product either reader read; the order
                    # is taken when exactly one of them fits, and its order number is found in this row's text by
                    # look-alikes (2020 orders have a year letter: HV4A408, which the current order rule refuses)
                    txt = re.sub(r'[^A-Z0-9-]', '', flat.upper())
                    cands = {(r['order'], r['prod_code']) for r in near
                             if r['prod_code'] in {tp, gp} and (not line or r['line'] == line)}
                    fits = [(oo, pp) for oo, pp in cands
                            if min((P.strict_dist(oo.split('-')[0], txt[i:i + 7]) for i in range(max(1, len(txt) - 6))), default=99) <= 1.0]
                    if len(fits) == 1:
                        o, p_, st = fits[0][0], fits[0][1], 'matched to the days either side'
                ref = by_order.get(o, [])
                ref = [r for r in ref if r['prod_code'] == p_]
                rec = {k2: '' for k2 in H.FIELDS}
                rec.update(date=day, file=f'{name}.pdf', run_date='', run_time='', page=int(png.stem[1:]), line=line or '',
                           order=o or '', order_base=(o or '-').split('-')[0], suffix=(o or '-').split('-')[-1], prod_code=p_ or '')
                why = []
                if st == 'check' or not o or not p_:
                    why.append(f'order/product not confirmed ({to}|{tp} text, {go}|{gp} glyphs)')
                if not line:
                    why.append(f'line code not certain {lreads}')
                if ref:
                    r0 = ref[-1] if [r for r in ref if r['date'] < day] == [] else [r for r in ref if r['date'] < day][-1]
                    per_cut = int(r0['total_sheets']) // max(1, int(r0['cut_rows'] or 1)) if str(r0['total_sheets']).isdigit() else None
                    need = [fmt(r0['weight_lbs']), fmt(r0['plts']), fmt(r0['pcs_stack'])] + ([fmt(per_cut)] if per_cut else [])
                    missing = [v for v in need if v and v not in flat]
                    if missing:
                        why.append(f'figures not all found in the OCR ({missing} from {r0["date"]})')
                    for f in ('die', 'width', 'length', 'mat', 'mat_spec', 'colour', 'thk', 'gsm', 'cut_width', 'cut_length',
                              'total_sheets', 'pack', 'plts', 'pcs_stack', 'stk_plt', 'weight_lbs', 'instr_date', 'web_width', 'cut_rows'):
                        rec[f] = r0[f]
                else:
                    why.append('order not on the neighbouring days: figures need reading by eye')
                m = PLTS_DONE.search(flat)
                done = int(m.group(1).replace(',', '')) if m else None
                prev = [int(PLTS_DONE.search(r['special']).group(1).replace(',', '')) for r in ref
                        if r['date'] < day and PLTS_DONE.search(r['special'] or '')]
                nxt = [int(PLTS_DONE.search(r['special']).group(1).replace(',', '')) for r in ref
                       if r['date'] > day and PLTS_DONE.search(r['special'] or '')]
                if done is not None and not ((not prev or prev[-1] <= done) and (not nxt or done <= nxt[0])):
                    why.append(f'PLTS DONE read {done}, neighbours {prev[-1:]} / {nxt[:1]}')
                sp = flat.split('Special', 1)[1] if 'Special' in flat else ''
                sp = re.sub(r'^[_\s]*Instructions?[:;]?\s*', '', sp).strip(' |_')
                rec['special'] = sp
                rec['source'] = 'image scan, read by the scan reader and checked against the system schedules either side'
                if why:
                    check.append({'day': day, 'page': png.name, 'y0': y0, 'y1': y_next, 'order': o, 'prod': p_,
                                  'why': ' ; '.join(why), 'ocr': flat[:300]})
                    rec['source'] += ' - CHECKED BY EYE'
                out.append((rec, bool(why)))
    ok = [r for r, bad in out if not bad]
    with open(config.WORK_DIR / 'history' / 'image_days_rows.csv', 'w', newline='', encoding='utf-8') as fh:
        wtr = csv.DictWriter(fh, H.FIELDS + ['source', 'needs_eye'])
        wtr.writeheader()
        for r, bad in out:
            wtr.writerow({**r, 'needs_eye': 'yes' if bad else ''})
    with open(config.WORK_DIR / 'history' / 'image_days_check.csv', 'w', newline='', encoding='utf-8') as fh:
        wtr = csv.DictWriter(fh, ['day', 'page', 'y0', 'y1', 'order', 'prod', 'why', 'ocr'])
        wtr.writeheader()
        wtr.writerows(check)
    return len(out), len(ok), len(check)


if __name__ == '__main__':
    print(main())
