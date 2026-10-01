"""Logic checks on a scan read, for when the OCR read fails (James Kuo, 1 Oct 2026: "the main goal is to improve the OCR
read and logic check when OCR read failed").

    python scan_reader/validate_read.py <date> <reader csv> [out csv]

A field the reader got wrong is caught by what the rest of the row, the page and the previous schedule day say. Each
repair names its reason in 'checks'; nothing is filled from a guess, only from a single consistent candidate:
  1. A row whose order and product both break the code rules, just above a real record, is handwriting over the page
     (24 Sep "-PC405" over RP26410-1): dropped.
  2. An order that breaks the order rule, or was never on any schedule, is taken from the previous schedule day only when
     exactly one order there has the same line, product and die and is not already read today (30 Sep H69A038-1 under
     "-PA205"). If the product is unreadable too, the order between the same two neighbours yesterday is taken.
  3. A product that breaks the code rule is taken from the previous day for a confirmed order on the same line.
  4. Thk, colours, material and grade must agree with the product code (thickness character, colour, family); die must
     be one this line has printed - a B/8 or O/0 slip is repaired to the line's die, else flagged.
  5. Orders on the line the previous day that are not read today are listed (finished, or missed on the page).
  6. In a row the handwriting damaged (order or product repaired), a field that is blank or breaks its rule takes the same
     order's value from the previous day; anywhere, a readable value that differs from the same order yesterday is flagged.
  7. Special instructions: numbers not read ('?') are taken from the same line of the same order the previous day; a line
     printed the previous day but not read today is flagged.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import order_number as ON  # noqa: E402
import product_code as PC  # noqa: E402

HIST = [ROOT / 'work' / 'history' / 'ext_history.csv', ROOT / 'work' / 'history' / 'ext_history_scans.csv']
FAMILY_MAT = {'BBP': 'BBB', 'RBP': 'BBB'}          # board families on SE61 print material BBB; the rest PPP


def schedules():
    """{date: [row dict(line, order, prod, die, thk, colours, mat, grade)]} from the system history and the daily packets."""
    days = defaultdict(list)
    for p in HIST:
        if p.exists():
            for r in csv.DictReader(open(p, encoding='utf-8')):
                m = (r['mat'] or '').split()
                days[r['date']].append({'line': r['line'], 'order': r['order'], 'prod': r['prod_code'], 'die': r['die'], 'thk': r['thk'],
                                        'colors': r['colour'], 'mat': m[0] if m else '', 'grade': m[1] if len(m) > 1 else '',
                                        'gsm': r['gsm'], 'spec': r['mat_spec'], 'special': r['special']})
    for f in sorted((ROOT / 'data' / 'packets').glob('packet_*.json')):
        q = json.loads(f.read_text(encoding='utf-8'))
        d = q['packet_date']
        if d in days:
            continue
        for e in q['ext']:
            for r in e['rows']:
                ms = r['mat_spec'].split()
                days[d].append({'line': e['line'], 'order': r['order'], 'prod': r['prod_code'], 'die': r['die'], 'thk': r['thk'],
                                'colors': r['colors'], 'mat': ms[0] if ms else '', 'grade': ms[1] if len(ms) > 1 else '',
                                'gsm': str(r['gsm']).replace(',', ''), 'spec': ms[2] if len(ms) > 2 else '',
                                'special': r.get('special_instructions') or ''})
    return days


def ok_order(o, on):
    return bool(o) and not ON.problems(o, on)


def ok_prod(p):
    return bool(p) and bool(PC.CODE_RX.match(p)) and not PC.problems(p)


def validate(date, rows):
    import datetime
    on = datetime.date.fromisoformat(date)
    days = schedules()
    prev_day = max((d for d in days if d < date), default=None)
    prev = days.get(prev_day, [])
    known_orders = {r['order'] for d, rs in days.items() if d <= date for r in rs}
    known_prods = {r['prod'] for rs in days.values() for r in rs}
    dies_by_line = defaultdict(set)
    for d, rs in days.items():
        if d <= date:
            for r in rs:
                dies_by_line[r['line']].add(r['die'])
    prev_by_line = defaultdict(list)
    for r in prev:
        prev_by_line[r['line']].append(r)
    out, dropped = [], []
    for i, r in enumerate(rows):
        r = dict(r)
        checks = []
        good_o, good_p = ok_order(r['order'], on), ok_prod(r['prod']) and r['prod'] in known_prods
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        # 1. handwriting read as a row: nothing of a record read (a real record garbled by handwriting over it still reads
        #    its die, spec, thickness ... - 30 Sep H68A020-1 under "-BB510" - and goes to the repairs below instead)
        filled = sum(bool(r.get(k)) for k in ('order', 'prod', 'die', 'thk', 'gsm', 'mat', 'grade', 'spec', 'colors'))
        if not good_o and not ok_prod(r['prod']) and filled <= 2 and nxt and nxt['scan_page'] == r['scan_page'] and ok_prod(nxt['prod']):
            dropped.append((r['scan_page'], r['order'], r['prod'], 'handwriting above the next record read as a row: dropped'))
            continue
        today = {x['order'] for x in rows if ok_order(x['order'], on)}
        cands = [p for p in prev_by_line[r['line']] if p['order'] not in today]
        # 2. order
        if not good_o or r['order'] not in known_orders:
            m = [p for p in cands if p['prod'] == r['prod'] and (p['die'] == r['die'] or not r['die'])] if good_p else []
            if not m and not good_p:                    # product unreadable too: between the same two neighbours
                before = next((x['order'] for x in reversed(out) if x['line'] == r['line']), None)
                after = next((x['order'] for x in rows[i + 1:] if x['line'] == r['line'] and ok_order(x['order'], on)), None)
                lo = [p['order'] for p in prev_by_line[r['line']]]
                if before in lo and after in lo and lo.index(after) - lo.index(before) == 2:
                    m = [prev_by_line[r['line']][lo.index(before) + 1]]
            if len(m) == 1:
                checks.append(f"order '{r['order']}' {'breaks the order rule' if not good_o else 'is on no schedule'}: "
                              f"{m[0]['order']} from {prev_day} (same line{', product' if good_p else ', between the same orders'}"
                              f"{', die' if r['die'] == m[0]['die'] else ''})")
                r['order'] = m[0]['order']
                if not good_p:
                    checks.append(f"product '{r['prod']}' unreadable: {m[0]['prod']} from {prev_day} for {m[0]['order']}")
                    r['prod'] = m[0]['prod']
                    good_p = True
            elif not good_o:
                checks.append(f"order '{r['order']}' breaks the order rule and no single order on {r['line']} on {prev_day} fits: check by eye")
        # 3. product
        if not good_p:
            m = [p for p in prev_by_line[r['line']] if p['order'] == r['order']]
            if len(m) == 1 and ok_order(r['order'], on):
                checks.append(f"product '{r['prod']}' {'breaks the code rule' if not ok_prod(r['prod']) else 'is on no schedule'}: "
                              f"{m[0]['prod']} from {prev_day} for {r['order']}")
                r['prod'] = m[0]['prod']
            elif not ok_prod(r['prod']):
                checks.append(f"product '{r['prod']}' breaks the code rule: check by eye")
        # 4. fields against the product code and the line
        if ok_prod(r['prod']):
            mm = PC.thickness_mm(r['prod'])
            if mm is not None:
                try:
                    t = float(r['thk']) if r['thk'] else None
                except ValueError:
                    t = None
                if t != float(mm):
                    checks.append(f"thk '{r['thk']}' -> {float(mm):.1f} (the product code's thickness)")
                    r['thk'] = f'{float(mm):.1f}'
            col = PC.CODE_RX.match(r['prod']).group(4)
            if r['colors'] and col not in r['colors'].split():
                checks.append(f"colours '{r['colors']}' do not include the product's {col}: check by eye")
            fam = r['prod'][:3]
            grade = 'A' if fam[2] == 'A' else 'P'
            if r.get('grade') and r['grade'] != grade and fam not in ('RBP', 'BBP'):
                checks.append(f"grade '{r['grade']}' vs the product family {fam} ({grade}): check by eye")
        if r['die'] and r['die'] not in dies_by_line[r['line']]:
            look = {'8': 'B', 'B': '8', '0': 'O', 'O': '0', '5': 'S', 'S': '5', '1': 'I', 'I': '1'}
            alts = {r['die'][:k] + look[c] + r['die'][k + 1:] for k, c in enumerate(r['die']) if c in look}
            hit = sorted(alts & dies_by_line[r['line']])
            if len(hit) == 1:
                checks.append(f"die '{r['die']}' -> {hit[0]} (the die this line prints; one look-alike character)")
                r['die'] = hit[0]
            else:
                checks.append(f"die '{r['die']}' not seen on {r['line']} before: check by eye")
        # 6. a row the handwriting damaged (its order or product had to be repaired): a field that is blank or breaks its
        #    rule takes the same order's value from the previous day; a readable value that differs is only flagged
        repaired = any(c.startswith(("order '", "product '")) and 'from ' in c for c in checks)
        y = next((p for p in prev_by_line[r['line']] if p['order'] == r['order']), None)
        if y:
            for f in ('gsm', 'spec', 'die', 'mat', 'grade', 'colors'):
                a, b = (r.get(f) or '').strip(), str(y.get(f) or '').strip()
                if not b or a == b:
                    continue
                bad = not a or (f == 'spec' and not re.fullmatch(r'([A-Z][0-9DM]){3}', a)) or (f == 'gsm' and not a.isdigit())
                if bad or repaired:
                    checks.append(f"{f} '{a}' {'not read' if not a else 'unreliable (handwriting over the row)' if repaired else 'breaks its rule'}: "
                                  f"{b} from {prev_day} for {r['order']}")
                    r[f] = b
                else:
                    checks.append(f"{f} '{a}' differs from {prev_day} ({b}) for the same order: check by eye")
        # 7. special instructions: numbers not read ('?') from the same order's same line the previous day; a line the
        #    previous day had that is not read today is flagged (handwriting may cover it: 30 Sep H63A200-1 "343 PLTS DONE")
        if y and y.get('special') is not None:
            ylines = [re.sub(r'\s+', ' ', x).strip() for x in y['special'].split(' / ') if x.strip()]
            tlines = [x for x in (r.get('special') or '').split(' / ') if x]
            key = lambda x: re.sub(r'[^A-Z]', '', x.upper())
            for k2, t in enumerate(tlines):
                if '?' in t:
                    same = [x for x in ylines if key(x) == key(t)]
                    if len(same) == 1:
                        checks.append(f"instruction '{t}': numbers not read, '{same[0]}' from {prev_day} for {r['order']}")
                        tlines[k2] = same[0]
            missing = [x for x in ylines if key(x) not in {key(t) for t in tlines} and not re.search(r'PLTS? DONE', x, re.I)]
            done_y = [x for x in ylines if re.search(r'PLTS? DONE', x, re.I)]
            if done_y and not any(re.search(r'PLTS? DONE', t, re.I) for t in tlines):
                checks.append(f"'{done_y[0]}' was printed on {prev_day} and is not read today (covered by handwriting? finished?): check by eye")
            trouble = repaired or any('?' in t for t in (r.get('special') or '').split(' / ')) or 'as read' in (r.get('flags') or '')
            for x in (missing if trouble else []):      # instructions change from day to day: only where the read had trouble
                checks.append(f"instruction line '{x}' printed on {prev_day} is not read today: check by eye")
            r['special'] = ' / '.join(tlines)
        r['checks'] = '; '.join(checks)
        out.append(r)
    read = {(r['line'], r['order']) for r in out}
    gone = sorted({(p['line'], p['order']) for p in prev} - read)
    return out, dropped, gone, prev_day


if __name__ == '__main__':
    date, src = sys.argv[1], sys.argv[2]
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    out, dropped, gone, prev_day = validate(date, rows)
    for d in dropped:
        print('DROPPED', d)
    for r in out:
        if r['checks']:
            print(r['scan_page'], r['line'], r['order'], '|', r['checks'])
    print(f'{len(gone)} orders on the schedule on {prev_day} not read today:', ', '.join(f'{l} {o}' for l, o in gone))
    if len(sys.argv) > 3:
        with open(sys.argv[3], 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
