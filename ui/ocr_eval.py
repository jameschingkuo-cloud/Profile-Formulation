# Reference and evaluation harness for the in-page scan reader (ui/page.template.html, ocrPage). read_page15 / evaluate15 is
# the version the page mirrors (30 Sep 2026); earlier versions are the record of what was tried. Run from the repo root.
"""Parser for Tesseract text of the EXT page's left strip (to be mirrored in the interface page's JavaScript).
Tested against transcribed packets. Rule: a value is taken only when it is certain (exact, or exactly one Product
Master code among the look-alike variants); anything else is returned flagged, never guessed."""
import datetime, itertools, json, os, re, sys
from pathlib import Path
import pytesseract
from PIL import Image
from openpyxl import load_workbook
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
WL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-:/.'
PRODS = {r[0] for r in load_workbook(config.published_path('Product Master.xlsx'), read_only=True)['Product Master'].iter_rows(min_row=2, max_col=1, values_only=True) if r[0]}
TO_D = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'T': '1', 'J': '1', 'Z': '2', 'S': '5', 'G': '6', 'E': '6', 'B': '8', 'A': '4', '/': '7'}
TO_L = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '6': 'G', '8': 'B', '4': 'A'}
LOOK = {'0': 'OD', 'O': '0D', 'D': '0O', '1': 'IT', 'I': '1T', 'T': '1I', '5': 'S', 'S': '5', '8': 'B', 'B': '8', '4': 'AG', 'A': '4', '2': 'Z', 'Z': '2', '6': 'G', 'G': '64', 'M': 'N', 'N': 'M', '/': '71', '7': '/'}
d = lambda s: ''.join(TO_D.get(c, c) for c in s)


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import order_number as ONUM                   # the order-number rule (order_number.py, from the system's own schedules)
mon = lambda c: c if c in ONUM.MONTHS else TO_D.get(c, c)          # month: 1-9, A, B, C (a B stays a B: November)


def fix_order(base, suf):
    """Positional repair of an order cell's reading (order_number.py): digits where digits belong, the month as read
    when it is a month, the letter A after an H/SH month."""
    if base[:2] == 'SH':                 # SH69A04: SH + year digit + month + A + 2 digits
        b = 'SH' + d(base[2]) + mon(base[3]) + ('A' if base[4] in 'A4' else base[4]) + d(base[5:7])
    elif base[0] == 'H':                 # H69A039: H + year digit + month + A + 3 digits
        b = 'H' + d(base[1]) + mon(base[2]) + ('A' if base[3] in 'A4' else base[3]) + d(base[4:7])
    else:                                # RP26811 / RP24C18 / RP25A08: RP + 2-digit year + month + 2 digits
        b = 'RP' + d(base[2:4]) + mon(base[4]) + d(base[5:7])
    s = d(suf)
    ok = bool(ONUM.BASE_RX.match(b)) and s.isdigit()
    return f'{b}-{s}', ok


def fix_prod(t):
    if t in PRODS: return t, 'exact'
    opts = [[c] + list(LOOK.get(c, '')) for c in t]
    if len(t) > 12: return t, 'unknown'
    hits = {''.join(p) for p in itertools.product(*opts) if ''.join(p) in PRODS}
    if len(hits) == 1: return hits.pop(), 'corrected'
    return t, ('ambiguous: ' + ', '.join(sorted(hits))) if hits else 'unknown'


ROW = re.compile(r'(H[0-9OISBZDQEGLT]{2}[A-Z][0-9OISBZDQTLJEG]{3}|RP[0-9OISBZDQEG]{2}[0-9A-Z][0-9OISBZDQTLJEG]{2})[-.]+([0-9ITLJ]{1,2})[-./:]*([A-Z0-9/]{6,12}?)[:.-]*(?=P[ABC]|B[AB][0-9SI]|$)')


def near(a, b):
    """a and b differ only by look-alike characters (same length), or by the order suffix."""
    if len(a) == len(b):
        return all(x == y or y in LOOK.get(x, '') or x in LOOK.get(y, '') for x, y in zip(a, b))
    return a.split('-')[0] == b.split('-')[0]


def snap(line, order, prod, known):
    """known: {(order, prod)} from every schedule / FRM on file. Exact -> 'known'. One near match with the same
    product -> that order ('snapped'). Else a new order (checked by the engineer anyway)."""
    if (order, prod) in known: return order, 'known'
    c = [o for o, p in known if p == prod and near(order, o)]
    if len(c) == 1: return c[0], 'snapped'
    return order, 'new'


def parse(txt):
    m = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', txt)
    if not m: return None, []
    line = 'SE' + d(m.group(1))
    rows = []
    for l in txt.splitlines():
        s = re.sub(r'\s+', '', l.upper())
        mm = ROW.search(s)
        if not mm: continue
        o, ook = fix_order(mm.group(1), mm.group(2))
        p, how = fix_prod(mm.group(3))
        rows.append({'order': o, 'prod': p, 'order_ok': ook, 'prod_how': how, 'raw': l.strip()})
    return line, rows


def ocr_page(png):
    im = Image.open(png)
    if im.height > im.width: im = im.rotate(-90, expand=True)
    w, h = im.size
    return pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), h)), config=f'--psm 6 -c tessedit_char_whitelist={WL}')


if __name__ == '__main__':
    for scan, date in [('doc05261220260929142225', '2026-09-29'), ('doc05253620260928134035', '2026-09-28')]:
        pdir = Path('work/pages') / scan
        if not pdir.exists(): print('no pages for', scan); continue
        pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
        truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
        got, flagged = set(), []
        for png in sorted(pdir.glob('p[0-9][0-9].png')):
            line, rows = parse(ocr_page(png))
            if not line: continue
            for r in rows:
                if r['order_ok'] and r['prod_how'] in ('exact', 'corrected'): got.add((line, r['order'], r['prod']))
                else: flagged.append((png.name, line, r))
        print(f'== {date}: truth {len(truth)}, taken {len(got)}, correct {len(got & truth)}, WRONG {len(got - truth)}, flagged {len(flagged)}, missing {len(truth - got)}')
        for x in sorted(got - truth): print('  WRONG', x)
        for f in flagged: print('  FLAG', f[0], f[1], f[2]['order'], f[2]['prod'], f[2]['prod_how'], '|', f[2]['raw'])
        miss = sorted(truth - got - {(f[1], f[2]['order'], f[2]['prod']) for f in flagged})
        for x in miss: print('  MISS', x)


def evaluate(date, scan, crop=(0.0, 0.30), scale=1.0):
    from PIL import Image
    known = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        dd = f.stem.split('_')[1]
        if dd >= date: continue
        q = json.load(open(f, encoding='utf-8'))
        known |= {(r['order'], r['prod_code']) for e in q['ext'] for r in e['rows']}
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        w, h = im.size
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        b = im.crop((int(w * crop[0]), 0, int(w * crop[1]), h))
        if scale != 1: b = b.resize((int(b.width * scale), int(b.height * scale)), Image.LANCZOS)
        line, rows = parse(top + '\n' + pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}'))
        if not line: continue
        for r in rows:
            if not (r['order_ok'] and r['prod_how'] in ('exact', 'corrected')):
                res.append((line, r['order'], r['prod'], 'FLAG ' + r['prod_how'], r['raw'])); continue
            o, how = snap(line, r['order'], r['prod'], known)
            res.append((line, o, r['prod'], how, r['raw']))
    taken = {(a, b, c) for a, b, c, h, _ in res if not h.startswith('FLAG')}
    wrong = [(a, b, c, h, raw) for a, b, c, h, raw in res if not h.startswith('FLAG') and (a, b, c) not in truth]
    flags = [x for x in res if x[3].startswith('FLAG')]
    print(f'{date} crop={crop} scale={scale}: truth {len(truth)} | right {len(taken & truth)} | WRONG {len(wrong)} | flagged {len(flags)} | missing {len(truth - taken) - len(flags)}')
    return wrong, flags, truth - taken


# ---- v2: weighted OCR distance, history first, looser row finder --------------------------------------------------
PAIRS = {frozenset(p) for p in ['0O', '0D', 'OD', '0Q', '1I', '1T', '1L', 'IT', 'IL', '1J', '5S', '8B', '4A', '4G', '6G', '6E', '2Z', '3S', '8S', 'BE', 'MN', '7/', '71', '3B', '8E']}
SOFT = set('OSIZTE/:.-')          # characters OCR inserts or drops


def ocr_dist(a, b):
    """Edit distance where look-alike swaps cost 0.3 and a stray look-alike character 0.5."""
    n, m = len(a), len(b)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): D[i][0] = D[i - 1][0] + (0.5 if a[i - 1] in SOFT else 1)
    for j in range(1, m + 1): D[0][j] = D[0][j - 1] + (0.5 if b[j - 1] in SOFT else 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            x, y = a[i - 1], b[j - 1]
            sub = 0 if x == y else (0.3 if frozenset((x, y)) in PAIRS else 1)
            D[i][j] = min(D[i - 1][j - 1] + sub, D[i - 1][j] + (0.5 if x in SOFT else 1), D[i][j - 1] + (0.5 if y in SOFT else 1))
    return D[n][m]


def best(tok, pool, limit):
    sc = sorted((ocr_dist(tok, c), c) for c in pool if abs(len(c) - len(tok)) <= 2)
    if sc and sc[0][0] <= limit and (len(sc) == 1 or sc[1][0] - sc[0][0] >= 0.5): return sc[0][1], sc[0][0]
    return None, sc[:2]


ORD = re.compile(r'(H[0-9A-Z/]{6}|RP[0-9A-Z/]{5})[-.:]+([0-9ITLJ/]{1,2})')


def read_row(s, known_by_order, orders_pool):
    """s: one OCR line without spaces. Returns (order, prod, status) or None."""
    m = ORD.search(s)
    if not m: return None
    raw_o = m.group(1) + '-' + m.group(2)
    rest = re.sub(r'^[-./:]+', '', s[m.end():])
    rest = re.split(r'(?=P[ABC][0-9A-Z]{2,3}|B[AB][0-9SI]{3})', rest)[0][:13]
    o, dist = best(raw_o, orders_pool, 1.0)
    if o:                                              # an order on file: its product must be close to what was read
        kp = known_by_order[o]
        if ocr_dist(rest, kp) <= 1.6: return o, kp, 'known' if dist == 0 and rest == kp else 'matched history'
        return o, rest, 'check product'
    fo, ok = fix_order(m.group(1), m.group(2))
    p, pd = best(rest, PRODS, 1.0)
    if p and ok: return fo, p, 'new order'
    return fo, (p or rest), 'check'


def evaluate2(date, scan, crop=(0.05, 0.25), scale=2.0, show=True):
    from PIL import Image
    known_by_order = {}
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            for r in e['rows']: known_by_order[r['order']] = r['prod_code']
    pool = list(known_by_order)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        w, h = im.size
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        b = im.crop((int(w * crop[0]), 0, int(w * crop[1]), h)).resize((int(w * (crop[1] - crop[0]) * scale), int(h * scale)), Image.LANCZOS)
        for l in pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines():
            r = read_row(re.sub(r'\s+', '', l.upper()), known_by_order, pool)
            if r: res.append((line,) + r + (l.strip(),))
    ok_status = ('known', 'matched history', 'new order')
    taken = {(a, b, c) for a, b, c, st, _ in res if st in ok_status}
    wrong = [x for x in res if x[3] in ok_status and x[:3] not in truth]
    flags = [x for x in res if x[3] not in ok_status]
    seen = {x[:3] for x in res}
    print(f'{date}: truth {len(truth)} | right {len(taken & truth)} | WRONG {len(wrong)} | flagged {len(flags)} | not found {len(truth - seen - {f[:3] for f in flags})}'
          f" | new-order rows {sum(1 for x in res if x[3] == 'new order')}")
    if show:
        for x in wrong: print('   WRONG', x)
        for x in flags: print('   FLAG ', x)
        for x in sorted(truth - taken - {f[:3] for f in flags}): print('   NOTFOUND', x)
    return res


# ---- v3: product token not cut inside itself; order + product matched together against the pairs on file ----------
def read_row3(s, pairs):
    m = ORD.search(s)
    if not m: return None
    raw_o = m.group(1) + '-' + m.group(2)
    tail = re.sub(r'^[-./:]+', '', s[m.end():])
    raw_p = (tail[:6] + re.split(r'(?=P[ABC][0-9A-Z]{2}|B[AB][0-9SI]{2})', tail[6:])[0])[:13].strip('-./:')
    sc = sorted((ocr_dist(raw_o, o) + ocr_dist(raw_p, p), o, p) for o, p in pairs)
    if sc and sc[0][0] <= 2.0 and (len(sc) == 1 or sc[1][0] - sc[0][0] >= 1.0):
        return sc[0][1], sc[0][2], 'known' if sc[0][0] == 0 else 'matched history', raw_o + ' ' + raw_p
    fo, ok = fix_order(m.group(1), m.group(2))
    p, _ = best(raw_p, PRODS, 1.0)
    return fo, (p or raw_p), ('new order' if (p and ok) else 'check'), raw_o + ' ' + raw_p


def evaluate3(date, scan, crop=(0.05, 0.25), scale=2.0, show=True):
    from PIL import Image
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        w, h = im.size
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        b = im.crop((int(w * crop[0]), 0, int(w * crop[1]), h)).resize((int(w * (crop[1] - crop[0]) * scale), int(h * scale)), Image.LANCZOS)
        for l in pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines():
            r = read_row3(re.sub(r'\s+', '', l.upper()), pairs)
            if r: res.append((line,) + r)
    taken = [x for x in res if x[3] in ('known', 'matched history')]
    new = [x for x in res if x[3] == 'new order']
    flags = [x for x in res if x[3] == 'check']
    wrong = [x for x in taken if x[:3] not in truth]
    seen = {x[:3] for x in res}
    print(f'{date}: truth {len(truth)} | matched {len(taken)} (wrong {len(wrong)}) | new-order rows {len(new)} (right {sum(1 for x in new if x[:3] in truth)}) | check {len(flags)} | not found {len(truth - seen)}')
    if show:
        for x in wrong: print('   WRONG', x)
        for x in new: print('   NEW  ', x, 'OK' if x[:3] in truth else 'WRONG')
        for x in flags: print('   CHECK', x)
        for x in sorted(truth - seen): print('   NOTFOUND', x)
    return res


# ---- v4: find each order row in the image (ink in the Mfg#/Ord# column), read it as one line ------------------------
def row_bands(im, x0=0.08, x1=0.13, y0=0.07, thr=140, min_ink=5, min_h=12, gap=4):
    import numpy as np
    a = np.asarray(im)
    w = a.shape[1]; h = a.shape[0]
    col = (a[int(h * y0):, int(w * x0):int(w * x1)] < thr).sum(axis=1)
    bands, start, last = [], None, None
    for i, v in enumerate(col > min_ink):
        if v:
            start = i if start is None else start; last = i
        elif start is not None and i - last > gap:
            if last - start >= min_h: bands.append((int(h * y0) + start, int(h * y0) + last))
            start = None
    if start is not None and last - start >= min_h: bands.append((int(h * y0) + start, int(h * y0) + last))
    return bands


def evaluate4(date, scan, show=True, scale=2.0):
    from PIL import Image
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        w, h = im.size
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        for (a, b) in row_bands(im):
            crop = im.crop((int(w * 0.05), max(0, a - 6), int(w * 0.25), min(h, b + 6)))
            crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
            t = pytesseract.image_to_string(crop, config=f'--psm 7 -c tessedit_char_whitelist={WL}')
            r = read_row3(re.sub(r'\s+', '', t.upper()), pairs)
            if r: res.append((line,) + r)
    taken = [x for x in res if x[3] in ('known', 'matched history')]
    new = [x for x in res if x[3] == 'new order']
    flags = [x for x in res if x[3] == 'check']
    seen = {x[:3] for x in res}
    print(f'{date}: truth {len(truth)} | matched {len(taken)} (wrong {sum(1 for x in taken if x[:3] not in truth)}) | new {len(new)} (right {sum(1 for x in new if x[:3] in truth)}) | check {len(flags)} | not found {len(truth - seen)}')
    if show:
        for x in taken + new:
            if x[:3] not in truth: print('   WRONG', x)
        for x in flags: print('   CHECK', x)
        for x in sorted(truth - seen): print('   NOTFOUND', x)
    return res


# ---- v5: trimmed product token; row-by-row reading merged with whole-strip reading ------------------------------
def prod_token(tail):
    t = re.sub(r'^[-./:|17IT]*(?=[A-Z]{3})', '', tail)                    # separator read as 1/7/I before the code
    m = re.search(r'[-.:|]|[1I7T]?(?:P[ABCR]|B[AB])', t[7:])              # die (or its separator) after the code
    return (t[:7 + m.start()] if m else t)[:12].strip('-./:')


def read_row5(s, pairs):
    m = ORD.search(s)
    if not m: return None
    raw_o = m.group(1) + '-' + m.group(2)
    raw_p = prod_token(s[m.end():])
    sc = sorted((ocr_dist(raw_o, o) + ocr_dist(raw_p, p), o, p) for o, p in pairs)
    if sc and sc[0][0] <= 2.0 and (len(sc) == 1 or sc[1][0] - sc[0][0] >= 1.0):
        return sc[0][1], sc[0][2], 'known' if sc[0][0] == 0 else 'matched history', raw_o + ' ' + raw_p
    fo, ok = fix_order(m.group(1), m.group(2))
    p, _ = best(raw_p, PRODS, 1.0)
    return fo, (p or raw_p), ('new order' if (p and ok) else 'check'), raw_o + ' ' + raw_p


RANK = {'known': 0, 'matched history': 1, 'new order': 2, 'check': 3}


def read_page(im, pairs, scale=2.0):
    w, h = im.size
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, []
    line = 'SE' + d(mm.group(1))
    reads = []
    b = im.crop((int(w * 0.05), 0, int(w * 0.25), h)).resize((int(w * 0.20 * scale), int(h * scale)), Image.LANCZOS)
    for l in pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines():
        r = read_row5(re.sub(r'\s+', '', l.upper()), pairs)
        if r: reads.append(r)
    for (a, c) in row_bands(im):
        crop = im.crop((int(w * 0.05), max(0, a - 6), int(w * 0.25), min(h, c + 6)))
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
        r = read_row5(re.sub(r'\s+', '', pytesseract.image_to_string(crop, config=f'--psm 7 -c tessedit_char_whitelist={WL}').upper()), pairs)
        if r: reads.append(r)
    # one entry per order: the best-settled reading wins; a 'check' is dropped if the same order was settled
    by = {}
    for r in reads:
        k = r[0]
        if k not in by or RANK[r[2]] < RANK[by[k][2]]: by[k] = r
    settled = {r[0].split('-')[0] for r in by.values() if r[2] != 'check'}
    return line, [r for r in by.values() if r[2] != 'check' or r[0].split('-')[0] not in settled]


from PIL import Image


def evaluate5(date, scan, show=True):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows = read_page(im, pairs)
        res += [(line,) + r for r in rows] if line else []
    ok = [x for x in res if x[3] != 'check']
    print(f'{date}: truth {len(truth)} | settled {len(ok)}: right {sum(1 for x in ok if x[:3] in truth)}, WRONG {sum(1 for x in ok if x[:3] not in truth)} '
          f"(new-order rows {sum(1 for x in ok if x[3] == 'new order')}) | check {len(res) - len(ok)} | not found {len(truth - {x[:3] for x in res})}")
    if show:
        for x in ok:
            if x[:3] not in truth: print('   WRONG', x)
        for x in res:
            if x[3] == 'check': print('   CHECK', x)
        for x in sorted(truth - {x[:3] for x in res}): print('   NOTFOUND', x)
    return res


# ---- v6: semi-global alignment of each row's text against every (order, product) on file --------------------------
INS_SOFT = set('OSIZTE/:.-17J|')     # extra characters OCR adds (separators, specks)


def align(pat, txt):
    """Cost of finding pat inside txt (free leading / trailing text). Look-alike swap 0.3, other swap 5,
    extra text char 0.5 (separator-like) or 1.0, missing pattern char 1.5 ('-' 0.3)."""
    n, m = len(pat), len(txt)
    prev = [0.0] * (m + 1)
    for i in range(1, n + 1):
        cur = [prev[0] + (0.3 if pat[i - 1] == '-' else 1.5)] + [0.0] * m
        for j in range(1, m + 1):
            x, y = pat[i - 1], txt[j - 1]
            sub = 0 if x == y else (0.3 if frozenset((x, y)) in PAIRS else 5)
            cur[j] = min(prev[j - 1] + sub,
                         prev[j] + (0.3 if x == '-' else 1.5),
                         cur[j - 1] + (0.5 if y in INS_SOFT else 1.0))
        prev = cur
    return min(prev)


ORD6 = re.compile(r'(H[0-9A-Z/]{5,6}|RP[0-9A-Z/]{4,5})[-.:]+([0-9ITLJ/]{1,2})')


def read_row6(s, pairs):
    s = s.strip()
    if len(s) < 12: return None
    sc = sorted((align(o + p, s.replace('-', '')), o, p) for o, p in pairs)
    if sc and sc[0][0] <= 2.0 and (len(sc) == 1 or sc[1][0] - sc[0][0] >= 1.0):
        return sc[0][1], sc[0][2], 'known' if sc[0][0] == 0 else 'matched history', s
    m = ORD.search(s)
    if not m: return None
    fo, ok = fix_order(m.group(1), m.group(2))
    p, _ = best(prod_token(s[m.end():]), PRODS, 1.0)
    return fo, (p or prod_token(s[m.end():])), ('new order' if (p and ok) else 'check'), s


def read_page6(im, pairs, scale=2.0):
    w, h = im.size
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, []
    line = 'SE' + d(mm.group(1))
    texts = []
    b = im.crop((int(w * 0.05), 0, int(w * 0.25), h)).resize((int(w * 0.20 * scale), int(h * scale)), Image.LANCZOS)
    texts += pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines()
    for (a, c) in row_bands(im):
        crop = im.crop((int(w * 0.05), max(0, a - 6), int(w * 0.25), min(h, c + 6)))
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
        texts.append(pytesseract.image_to_string(crop, config=f'--psm 7 -c tessedit_char_whitelist={WL}'))
    by = {}
    for t in texts:
        s = re.sub(r'\s+', '', t.upper())
        if not re.search(r'H\w{4}|RP\w{4}', s): continue
        r = read_row6(s, pairs)
        if r and (r[0] not in by or RANK[r[2]] < RANK[by[r[0]][2]]): by[r[0]] = r
    settled = {r[0].split('-')[0] for r in by.values() if r[2] != 'check'}
    return line, [r for r in by.values() if r[2] != 'check' or r[0].split('-')[0] not in settled]


def evaluate6(date, scan, show=True):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows = read_page6(im, pairs)
        res += [(line,) + r for r in rows] if line else []
    hist = [x for x in res if x[3] in ('known', 'matched history')]
    new = [x for x in res if x[3] == 'new order']
    print(f'{date}: truth {len(truth)} | from history {len(hist)} (WRONG {sum(1 for x in hist if x[:3] not in truth)}) | new orders {len(new)} (right {sum(1 for x in new if x[:3] in truth)}) '
          f"| check {sum(1 for x in res if x[3] == 'check')} | not found {len(truth - {x[:3] for x in res})}")
    if show:
        for x in hist + new:
            if x[:3] not in truth: print('   WRONG', x)
        for x in res:
            if x[3] == 'check': print('   CHECK', x)
        for x in sorted(truth - {x[:3] for x in res}): print('   NOTFOUND', x)
    return res


def collapse(rows):
    """rows: (order, prod, status, raw). Keep the best-settled reading of each physical row: drop a reading whose product
    matches a kept one and whose order differs only by OCR noise."""
    kept = []
    for r in sorted(rows, key=lambda r: RANK.get(r[2], 9) if r[2] in RANK else {'known': 0, 'matched history': 1, 'new order': 2}.get(r[2], 3)):
        if r[2] not in ('known', 'matched history') and any((r[1] == k[1] or ocr_dist(r[1], k[1]) <= 1.5) and ocr_dist(r[0], k[0]) <= 2.5 for k in kept):
            continue
        kept.append(r)
    return kept


def evaluate7(date, scan, tessdir=None):
    import pytesseract as pt
    orig = pt.image_to_string
    if tessdir:
        pt.image_to_string = lambda img, config='': orig(img, config=config + f' --tessdata-dir {tessdir}')
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows = read_page6(im, pairs)
        if line: res += [(line,) + r for r in collapse(rows)]
    pt.image_to_string = orig
    settled = [x for x in res if x[3] in ('known', 'matched history')]
    print(f'{date}: truth {len(truth)} | rows shown {len(res)} | settled {len(settled)} (WRONG {sum(1 for x in settled if x[:3] not in truth)}) '
          f'| exactly right overall {len({x[:3] for x in res} & truth)} | shown but not in truth {sum(1 for x in res if x[:3] not in truth)}')
    return res


# ---- v8: every order row in the image is accounted for -----------------------------------------------------------
def read_page8(im, pairs, scale=2.0):
    w, h = im.size
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, [], []
    line = 'SE' + d(mm.group(1))
    texts = []
    b = im.crop((int(w * 0.05), 0, int(w * 0.25), h)).resize((int(w * 0.20 * scale), int(h * scale)), Image.LANCZOS)
    texts += [(None, t) for t in pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines()]
    bands = row_bands(im)
    for bb in bands:
        a, c = bb
        crop = im.crop((int(w * 0.05), max(0, a - 6), int(w * 0.25), min(h, c + 6)))
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
        texts.append((bb, pytesseract.image_to_string(crop, config=f'--psm 7 -c tessedit_char_whitelist={WL}')))
    reads = []
    for bb, t in texts:
        s = re.sub(r'\s+', '', t.upper())
        if not re.search(r'H\w{4}|RP\w{4}', s): continue
        r = read_row6(s, pairs)
        if r: reads.append(r)
    kept = []
    for r in sorted(reads, key=lambda r: RANK[r[2]]):
        matched = r[2] in ('known', 'matched history')
        if any(k[0] == r[0] for k in kept): continue
        if not matched and any(align(k[0] + k[1], r[3].replace('-', '')) <= 3.0 for k in kept if k[2] in ('known', 'matched history')): continue
        if not matched and any((r[1] == k[1] or ocr_dist(r[1], k[1]) <= 1.5) and ocr_dist(r[0], k[0]) <= 2.5 for k in kept): continue
        kept.append(r)
    unexplained = []
    for bb, t in texts:
        if bb is None: continue
        s = re.sub(r'\s+', '', t.upper()).replace('-', '')
        if len(s) < 8 or re.search(r'LINE|TOTAL|MFG|ORD|SPECIAL|INSTR', s): continue
        if not any(align(k[0].replace('-', '') + k[1], s) <= 4.0 for k in kept):
            unexplained.append((bb, t.strip()))
    return line, kept, unexplained


def evaluate8(date, scan):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res, unex = [], []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows, un = read_page8(im, pairs)
        if not line: continue
        res += [(line,) + r for r in rows]
        unex += [(png.name, line, u) for u in un]
    got = {x[:3] for x in res}
    print(f'{date}: truth {len(truth)} | shown {len(res)} | right {len(got & truth)} | shown-not-right {len(res) - len(got & truth)} | truth not shown {len(truth - got)} | unexplained rows {len(unex)}')
    for x in sorted(truth - got): print('   NOT SHOWN', x)
    for x in res:
        if x[:3] not in truth: print('   SHOWN WRONG', x[:4])
    for u in unex: print('   UNEXPLAINED', u)
    return res, unex


# ---- v9: each row band read with fallbacks until it matches; empty bands count as unread --------------------------
BAND_TRIES = [(2, 7, 14), (2, 13, 6), (3, 7, 10), (2, 6, 6)]


def read_page9(im, pairs):
    w, h = im.size
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, [], []
    line = 'SE' + d(mm.group(1))
    reads, band_txt = [], []
    b = im.crop((int(w * 0.05), 0, int(w * 0.25), h)).resize((int(w * 0.20 * 2), int(h * 2)), Image.LANCZOS)
    for t in pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines():
        s = re.sub(r'\s+', '', t.upper())
        if re.search(r'H\w{4}|RP\w{4}', s):
            r = read_row6(s, pairs)
            if r: reads.append(r)
    for (a, c) in row_bands(im):
        texts = []
        for scale, psm, pad in BAND_TRIES:
            crop = im.crop((int(w * 0.05), max(0, a - pad), int(w * 0.25), min(h, c + pad)))
            crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
            s = re.sub(r'\s+', '', pytesseract.image_to_string(crop, config=f'--psm {psm} -c tessedit_char_whitelist={WL}').upper())
            texts.append(s)
            r = read_row6(s, pairs) if re.search(r'H\w{4}|RP\w{4}', s) else None
            if r: reads.append(r)
            if r and r[2] in ('known', 'matched history'): break
        band_txt.append(((a, c), texts))
    kept = []
    for r in sorted(reads, key=lambda r: RANK[r[2]]):
        matched = r[2] in ('known', 'matched history')
        if any(k[0] == r[0] for k in kept): continue
        if not matched and any(align(k[0] + k[1], r[3].replace('-', '')) <= 3.0 for k in kept if k[2] in ('known', 'matched history')): continue
        if not matched and any((r[1] == k[1] or ocr_dist(r[1], k[1]) <= 1.5) and ocr_dist(r[0], k[0]) <= 2.5 for k in kept): continue
        kept.append(r)
    unexplained = []
    for (a, c), texts in band_txt:
        joined = ' '.join(texts)
        if a < h * 0.10 or re.search(r'LINE|TOTAL|ENDOF|REPORT', joined): continue       # column header, line total, end
        if not any(any(align(k[0].replace('-', '') + k[1], t.replace('-', '')) <= 4.0 for t in texts if t) for k in kept):
            unexplained.append(((a, c), next((t for t in texts if t), '')))
    return line, kept, unexplained


def evaluate9(date, scan, show=True):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    res, unex = [], []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows, un = read_page9(im, pairs)
        if not line: continue
        res += [(line,) + r for r in rows]
        unex += [(png.name, line, u) for u in un]
    got = {x[:3] for x in res}
    matched = [x for x in res if x[3] in ('known', 'matched history')]
    print(f'{date}: truth {len(truth)} | shown {len(res)} | right {len(got & truth)} | matched {len(matched)} (WRONG {sum(1 for x in matched if x[:3] not in truth)}) '
          f'| boxed {len(res) - len(matched)} | truth not shown {len(truth - got)} | unread rows flagged {len(unex)}')
    if show:
        for x in sorted(truth - got): print('   NOT SHOWN', x)
        for u in unex: print('   UNREAD ROW', u)
    return res, unex


# ---- v10: one reading per printed row; the strip pass only contributes matched readings ------------------------------
MATCHED = ('known', 'matched history')


def read_page10(im, pairs):
    w, h = im.size
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, [], []
    line = 'SE' + d(mm.group(1))
    kept = []
    def add(r):
        if r and not any(k[0] == r[0] for k in kept): kept.append(r)
    b = im.crop((int(w * 0.05), 0, int(w * 0.25), h)).resize((int(w * 0.20 * 2), int(h * 2)), Image.LANCZOS)
    for t in pytesseract.image_to_string(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}').splitlines():
        s = re.sub(r'\s+', '', t.upper())
        if re.search(r'H\w{4}|RP\w{4}', s):
            r = read_row6(s, pairs)
            if r and r[2] in MATCHED: add(r)
    bands = []
    for (a, c) in row_bands(im):
        texts, best_r = [], None
        for scale, psm, pad in BAND_TRIES:
            crop = im.crop((int(w * 0.05), max(0, a - pad), int(w * 0.25), min(h, c + pad)))
            crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
            s = re.sub(r'\s+', '', pytesseract.image_to_string(crop, config=f'--psm {psm} -c tessedit_char_whitelist={WL}').upper())
            texts.append(s)
            r = read_row6(s, pairs) if re.search(r'H\w{4}|RP\w{4}', s) else None
            if r and (best_r is None or RANK[r[2]] < RANK[best_r[2]]): best_r = r
            if r and r[2] in MATCHED: break
        if best_r and best_r[2] in MATCHED: add(best_r)
        bands.append(((a, c), texts, best_r))
    unexplained = []
    for (a, c), texts, best_r in bands:
        if a < h * 0.10 or re.search(r'LINE|TOTAL|ENDOF|REPORT', ' '.join(texts)): continue
        if any(any(t and align(k[0].replace('-', '') + k[1], t.replace('-', '')) <= 4.0 for t in texts) for k in kept): continue
        if best_r: add(best_r)
        else: unexplained.append(((a, c), next((t for t in texts if t), '')))
    return line, kept, unexplained


def evaluate10(date, scan):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    res, unex = [], []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows, un = read_page10(im, pairs)
        if not line: continue
        res += [(line,) + r for r in rows]
        unex += [(png.name, line, u) for u in un]
    shown = {x[:3] for x in res}
    matched = [x for x in res if x[3] in MATCHED]
    boxed = [x for x in res if x[3] not in MATCHED]
    ul = {}
    for _, l, _u in unex: ul[l] = ul.get(l, 0) + 1
    silent = []
    for t in truth:
        if t in shown: continue
        if any(x[0] == t[0] and (ocr_dist(x[1], t[1]) <= 3 or ocr_dist(x[2], t[2]) <= 3) for x in boxed): continue
        if ul.get(t[0]): ul[t[0]] -= 1; continue
        silent.append(t)
    print(f'{date}: truth {len(truth)} | right {len(shown & set(truth))} | matched {len(matched)} (WRONG {sum(1 for x in matched if x[:3] not in set(truth))}) '
          f'| boxed {len(boxed)} (of which right {sum(1 for x in boxed if x[:3] in set(truth))}) | unread rows {len(unex)} | SILENT MISSES {silent}')
    return res, unex


# ---- v11: strip readings carry their height on the page; a printed row explained by one is not read again -------------
def strip_lines(im, scale=2.0):
    w, h = im.size
    b = im.crop((int(w * 0.05), 0, int(w * 0.25), h)).resize((int(w * 0.20 * scale), int(h * scale)), Image.LANCZOS)
    dd = pytesseract.image_to_data(b, config=f'--psm 6 -c tessedit_char_whitelist={WL}', output_type=pytesseract.Output.DICT)
    lines = {}
    for i, t in enumerate(dd['text']):
        if not t.strip(): continue
        k = (dd['block_num'][i], dd['par_num'][i], dd['line_num'][i])
        L = lines.setdefault(k, {'t': [], 'y0': 10 ** 9, 'y1': 0})
        L['t'].append(t); L['y0'] = min(L['y0'], dd['top'][i] / scale); L['y1'] = max(L['y1'], (dd['top'][i] + dd['height'][i]) / scale)
    return [(''.join(L['t']).upper(), L['y0'], L['y1']) for L in lines.values()]


def read_page11(im, pairs):
    w, h = im.size
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, [], []
    line = 'SE' + d(mm.group(1))
    kept, strip_y = [], []
    def add(r):
        if r and not any(k[0] == r[0] for k in kept): kept.append(r); return True
        return False
    for s, y0, y1 in strip_lines(im):
        s = re.sub(r'\s+', '', s)
        if re.search(r'H\w{4}|RP\w{4}', s):
            r = read_row6(s, pairs)
            if r and r[2] in MATCHED:
                add(r); strip_y.append(((y0 + y1) / 2, r[0]))
    unexplained = []
    for (a, c) in row_bands(im):
        if any(a - 15 <= y <= c + 15 for y, _ in strip_y): continue          # this printed row was read in the strip pass
        texts, best_r = [], None
        for scale, psm, pad in BAND_TRIES:
            crop = im.crop((int(w * 0.05), max(0, a - pad), int(w * 0.25), min(h, c + pad)))
            crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
            s = re.sub(r'\s+', '', pytesseract.image_to_string(crop, config=f'--psm {psm} -c tessedit_char_whitelist={WL}').upper())
            texts.append(s)
            r = read_row6(s, pairs) if re.search(r'H\w{4}|RP\w{4}', s) else None
            if r and (best_r is None or RANK[r[2]] < RANK[best_r[2]]): best_r = r
            if r and r[2] in MATCHED: break
        if a < h * 0.10 or re.search(r'LINE|TOTAL|ENDOF|REPORT', ' '.join(texts)): continue
        if best_r and best_r[2] in MATCHED: add(best_r); continue
        if any(any(t and align(k[0].replace('-', '') + k[1], t.replace('-', '')) <= 4.0 for t in texts) for k in kept): continue
        if best_r: add(best_r)
        else: unexplained.append(((a, c), next((t for t in texts if t), '')))
    return line, kept, unexplained


def evaluate11(date, scan):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        for e in json.load(open(f, encoding='utf-8'))['ext']:
            pairs |= {(r['order'], r['prod_code']) for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    res, unex = [], []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows, un = read_page11(im, pairs)
        if not line: continue
        res += [(line,) + r for r in rows]
        unex += [(png.name, line, u) for u in un]
    shown = {x[:3] for x in res}
    matched = [x for x in res if x[3] in MATCHED]
    boxed = [x for x in res if x[3] not in MATCHED]
    ul = {}
    for _, l, _u in unex: ul[l] = ul.get(l, 0) + 1
    silent = []
    for t in truth:
        if t in shown: continue
        if any(x[0] == t[0] and (ocr_dist(x[1], t[1]) <= 3 or ocr_dist(x[2], t[2]) <= 3) for x in boxed): continue
        if ul.get(t[0]): ul[t[0]] -= 1; continue
        silent.append(t)
    print(f'{date}: truth {len(truth)} | right {len(shown & set(truth))} | matched {len(matched)} (WRONG {sum(1 for x in matched if x[:3] not in set(truth))}) '
          f'| boxed {len(boxed)} (right {sum(1 for x in boxed if x[:3] in set(truth))}) | unread rows {len(unex)} | SILENT MISSES {silent}')
    for x in boxed: print('   BOXED', x[:4])
    return res, unex


# ---- v12: cells between the printed bars -------------------------------------------------------------------------
import numpy as np
BAR_NEAR = {'y': 0.081, 'suf': 0.1545, 'die': 0.2185}


def find_bars(a, bands, w):
    """x of the bar after 'Y', after the order suffix, and before the die, from ink just below each row's text
    (bars run below the baseline, letters and digits do not). One x per page (monospace print)."""
    out = {}
    for k, fx in BAR_NEAR.items():
        x0, x1 = int(w * (fx - 0.012)), int(w * (fx + 0.012))
        score = np.zeros(x1 - x0)
        for (y0, y1) in bands:
            win = a[y1 + 1:y1 + 7, x0:x1] < 140
            if win.size: score += win.mean(axis=0)
        out[k] = x0 + int(np.argmax(score)) if score.max() > 0 else int(w * fx)
    return out


ORDER_WL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
CELL_TRIES = [(3, 7), (2, 7), (3, 13), (4, 8)]


def ocr_cell(im, x0, x1, y0, y1, scale, psm, wl=ORDER_WL, pad=8):
    c = im.crop((x0, max(0, y0 - pad), x1, y1 + pad))
    c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
    return re.sub(r'\s+', '', pytesseract.image_to_string(c, config=f'--psm {psm} -c tessedit_char_whitelist={wl}').upper())


ORD_CELL = re.compile(r'^[^A-Z0-9]*(H[0-9A-Z]{6}|SH[0-9A-Z]{5}|RP[0-9A-Z]{5})-*([0-9ITLJZSOD]{1,2})[^A-Z0-9]*$')


def parse_order_cell(t):
    m = ORD_CELL.match(t)
    if not m: return None
    o, ok = fix_order(m.group(1), m.group(2))
    return o if ok else None


PROD_CELL = re.compile(r'^[^A-Z0-9]*([A-Z0-9]{6,12})[^A-Z0-9]*$')


def parse_prod_cell(t):
    m = PROD_CELL.match(t)
    if not m: return None, 'unread'
    tok = m.group(1)
    if tok in PRODS: return tok, 'exact'
    p, _ = best(tok, PRODS, 1.0)
    return (p, 'corrected') if p else (tok, 'unknown')


def read_rows_cells(im):
    """[(order or None, prod or None, prod_how, raw)] per printed order row, from the cells alone (no history)."""
    a = np.asarray(im); h, w = a.shape
    bands = [b for b in row_bands(im) if b[0] > h * 0.10]
    bars = find_bars(a, bands, w)
    out = []
    for (y0, y1) in bands:
        o = p = None; how = 'unread'; raws = []
        for scale, psm in CELL_TRIES:
            if o is None:
                t = ocr_cell(im, bars['y'] + 4, bars['suf'] - 3, y0, y1, scale, psm); raws.append(t)
                o = parse_order_cell(t)
            if p is None or how == 'unknown':
                t2 = ocr_cell(im, bars['suf'] + 4, bars['die'] - 3, y0, y1, scale, psm); raws.append(t2)
                pp, hh = parse_prod_cell(t2)
                if hh in ('exact', 'corrected') or p is None: p, how = pp, hh
            if o and how in ('exact', 'corrected'): break
        out.append((o, p, how, raws))
    return out


def evaluate12(date, scan):
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    got = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        w, h = im.size
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        for o, p, how, raws in read_rows_cells(im):
            got.append((line, o, p, how, png.name, raws))
    rows = [(l, o, p) for l, o, p, how, *_ in got if o and p]
    ords = {(l, o) for l, o, p, *_ in got if o}
    print(f'{date}: truth {len(truth)} | printed rows found {len(got)} | order right {len(ords & {(l, o) for l, o, _ in truth})} '
          f'| order+product right {len(set(rows) & tset)} | wrong (taken but not in truth) {sum(1 for r in rows if r not in tset)} '
          f'| order unread {sum(1 for g in got if not g[1])}')
    for g in got:
        if (g[0], g[1], g[2]) not in tset: print('   ', g[0], g[1], g[2], g[3], g[4], g[5][:4])
    return got


def row_bars(a, y0, y1, w):
    """Per row: x of the bar after 'Y', after the suffix, before the die (strokes that run below the text)."""
    below = (a[y1 + 2:y1 + 8, :] < 140).mean(axis=0)
    xs = [x for x in range(int(w * 0.06), int(w * 0.24)) if below[x] >= 0.8]
    suf = next((x for x in xs if w * 0.145 <= x <= w * 0.162), None)
    if suf is None: return None
    die = min((x for x in xs if abs(x - (suf + w * 0.064)) <= w * 0.006), key=lambda x: abs(x - (suf + w * 0.064)), default=int(suf + w * 0.064))
    ybar = min((x for x in xs if abs(x - (suf - w * 0.073)) <= w * 0.006), key=lambda x: abs(x - (suf - w * 0.073)), default=int(suf - w * 0.073))
    return ybar, suf, die


def read_rows_cells2(im):
    a = np.asarray(im); h, w = a.shape
    out = []
    for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
        bars = row_bars(a, y0, y1, w)
        if not bars: continue                                   # not an order row (no bar after the suffix)
        yb, sb, db = bars
        o = p = None; how = 'unread'; raws = []
        for scale, psm in CELL_TRIES:
            if o is None:
                t = ocr_cell(im, yb + 5, sb - 3, y0, y1, scale, psm); raws.append(t)
                o = parse_order_cell(t)
            if p is None or how == 'unknown':
                t2 = ocr_cell(im, sb + 5, db - 3, y0, y1, scale, psm); raws.append(t2)
                pp, hh = parse_prod_cell(t2)
                if hh in ('exact', 'corrected') or p is None: p, how = pp, hh
            if o and how in ('exact', 'corrected'): break
        out.append((o, p, how, raws))
    return out


def evaluate13(date, scan, show=True):
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    got = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        w, h = im.size
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        for o, p, how, raws in read_rows_cells2(im):
            got.append((line, o, p, how, png.name, raws))
    ords = [(l, o) for l, o, *_ in got if o]
    tords = {(l, o) for l, o, _ in truth}
    both = [(l, o, p) for l, o, p, how, *_ in got if o and how in ('exact', 'corrected')]
    print(f'{date}: truth {len(truth)} | order rows found {len(got)} | order right {sum(1 for x in ords if x in tords)} WRONG {sum(1 for x in ords if x not in tords)} unread {sum(1 for g in got if not g[1])} '
          f'| order+product taken {len(both)} right {sum(1 for x in both if x in tset)}')
    if show:
        for g in got:
            if (g[0], g[1], g[2]) not in tset: print('   ', g[0], g[1], g[2], g[3], g[4], g[5][:4])
    return got


# ---- v14 (final): cells between the bars + match to orders on file; nothing unconfirmed is taken ----------------------
PAIRS |= {frozenset(p) for p in ['4Z', '2Z', '6G', '3S', '0Q', 'MN', 'WN', '8R', 'BR', 'EF']}


def match_pair(o_raw, p_raw, pairs):
    """Best (order, product) on file for what the cells read; accepted only when clearly closest."""
    sc = sorted((ocr_dist(o_raw, o) + ocr_dist(p_raw, p), o, p) for o, p in pairs)
    if sc and sc[0][0] <= 2.5 and (len(sc) == 1 or sc[1][0] - sc[0][0] >= 1.0):
        return sc[0][1], sc[0][2], sc[0][0]
    return None


def read_page14(im, pairs):
    a = np.asarray(im); h, w = a.shape
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, []
    line = 'SE' + d(mm.group(1))
    rows = []
    for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
        bars = row_bars(a, y0, y1, w)
        if not bars: continue
        yb, sb, db = bars
        best_r = None
        for scale, psm in CELL_TRIES:
            t = ocr_cell(im, yb + 5, sb - 3, y0, y1, scale, psm)
            t2 = ocr_cell(im, sb + 5, db - 3, y0, y1, scale, psm)
            if re.search(r'LINE|TOTAL|REPORT', t + t2): best_r = ('skip',); break
            o_raw = re.sub(r'[^A-Z0-9-]', '', t).strip('-'); p_raw = re.sub(r'[^A-Z0-9]', '', t2)
            m = match_pair(o_raw, p_raw, pairs) if o_raw and p_raw else None
            if m:
                best_r = (m[0], m[1], 'read' if m[2] == 0 else 'matched to schedule history', f'{t} | {t2}'); break
            o = parse_order_cell(t); p, how = parse_prod_cell(t2)
            if o and how in ('exact', 'corrected'):
                if not best_r or best_r[2] == 'check': best_r = (o, p, 'new order', f'{t} | {t2}')
            elif not best_r:
                best_r = (o or o_raw, p or p_raw, 'check', f'{t} | {t2}')
        if best_r and best_r[0] != 'skip': rows.append(best_r)
    return line, rows


def evaluate14(date, scan, use_history=True, show=True):
    pairs = set()
    if use_history:
        for f in sorted(Path('data/packets').glob('packet_*.json')):
            if f.stem.split('_')[1] >= date: continue
            q = json.load(open(f, encoding='utf-8'))
            pairs |= {(r['order'], r['prod_code']) for e in q['ext'] for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows = read_page14(im, pairs)
        if line: res += [(line,) + r + (png.name,) for r in rows]
    taken = [x for x in res if x[3] in ('read', 'matched to schedule history')]
    new = [x for x in res if x[3] == 'new order']
    chk = [x for x in res if x[3] == 'check']
    print(f'{date} history={use_history}: truth {len(truth)} | rows {len(res)} | taken {len(taken)} WRONG {sum(1 for x in taken if x[:3] not in tset)} '
          f'| new-order boxed {len(new)} (right {sum(1 for x in new if x[:3] in tset)}) | check boxed {len(chk)} | truth rows not found {len(tset - {x[:3] for x in res}) - len(chk) - sum(1 for x in new if x[:3] not in tset)}')
    if show:
        for x in taken:
            if x[:3] not in tset: print('   TAKEN WRONG', x)
        for x in new + chk: print('   BOXED', x[:4], x[4][:50])
    return res


def row_bars(a, y0, y1, w):
    """Per row: bars that run below the text. The suffix bar and the die bar are 0.064 of the page width apart and the
    'Y' bar 0.073 before the suffix bar; found by that spacing, so a page shifted on the copier glass still works."""
    below = (a[y1 + 2:y1 + 8, :] < 140).mean(axis=0)
    xs = [x for x in range(int(w * 0.03), int(w * 0.26)) if below[x] >= 0.8]
    near = lambda t, tol: min((x for x in xs if abs(x - t) <= tol), key=lambda x: abs(x - t), default=None)
    for suf in xs:
        if not (w * 0.11 <= suf <= w * 0.19): continue
        die = near(suf + w * 0.064, w * 0.005)
        if die is None: continue
        yb = near(suf - w * 0.073, w * 0.006)
        return (yb if yb is not None else int(suf - w * 0.073)), suf, die
    return None


def strict_dist(a, b):
    """As ocr_dist, but a substitution that is not a look-alike costs 10: history may only differ by OCR look-alikes."""
    n, m = len(a), len(b)
    D = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): D[i][0] = D[i - 1][0] + (0.5 if a[i - 1] in SOFT else 1.5)
    for j in range(1, m + 1): D[0][j] = D[0][j - 1] + (0.5 if b[j - 1] in SOFT else 1.5)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            x, y = a[i - 1], b[j - 1]
            sub = 0 if x == y else (0.3 if frozenset((x, y)) in PAIRS else 10)
            D[i][j] = min(D[i - 1][j - 1] + sub, D[i - 1][j] + (0.5 if x in SOFT else 1.5), D[i][j - 1] + (0.5 if y in SOFT else 1.5))
    return D[n][m]


def match_pair(o_raw, p_raw, pairs):
    sc = sorted((strict_dist(o_raw, o) + strict_dist(p_raw, p), o, p) for o, p in pairs)
    if sc and sc[0][0] <= 2.5 and (len(sc) == 1 or sc[1][0] - sc[0][0] >= 1.0):
        return sc[0][1], sc[0][2], sc[0][0]
    return None


# ---- v15: product code hard rule in the reader ---------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import product_code as PCODE


def take_prod(t2):
    """Product from a cell: exact in the Product Master, or its rule-based repair in the Product Master. Else None."""
    tok = re.sub(r'[^A-Z0-9/]', '', t2)
    for cand in [tok, tok[1:], tok[:-1], tok[1:-1]]:
        if cand in PRODS: return cand
        fixed, _ = PCODE.repair(cand)
        if fixed and fixed in PRODS: return fixed
    return None


def read_page15(im, pairs):
    a = np.asarray(im); h, w = a.shape
    top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
    mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
    if not mm: return None, [], []
    line = 'SE' + d(mm.group(1))
    rows, unread = [], []
    for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
        bars = row_bars(a, y0, y1, w)
        if not bars:
            t = ocr_cell(im, int(w * 0.06), int(w * 0.24), y0, y1, 2, 7, WL)
            if re.search(r'LINE|TOTAL|REPORT|SI:|SPECIAL', t) or not re.search(r'\d{3}', t): continue
            unread.append(((y0, y1), t)); continue
        yb, sb, db = bars
        best_r = None
        for scale, psm in CELL_TRIES:
            t = ocr_cell(im, yb + 5, sb - 3, y0, y1, scale, psm)
            t2 = ocr_cell(im, sb + 5, db - 3, y0, y1, scale, psm)
            if re.search(r'LINE|TOTAL|REPORT', t + t2): best_r = ('skip',); break
            o_raw = re.sub(r'[^A-Z0-9-]', '', t).strip('-'); p_raw = re.sub(r'[^A-Z0-9]', '', t2)
            m = match_pair(o_raw, p_raw, pairs) if o_raw and p_raw else None
            if m: best_r = (m[0], m[1], 'read' if m[2] == 0 else 'matched to schedule history', f'{t} | {t2}'); break
            o = parse_order_cell(t); p = take_prod(t2)
            if o and p:                                   # keeps the rules but is not on file: read on, it may still match
                if not best_r or best_r[2] == 'check': best_r = (o, p, 'new order', f'{t} | {t2}')
            elif not best_r: best_r = (o or o_raw, p or p_raw, 'check', f'{t} | {t2}')   # odd: read again with the next setting
        if best_r and best_r[0] != 'skip': rows.append(best_r)
    return line, rows, unread


def evaluate15(date, scan, show=True):
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        if f.stem.split('_')[1] >= date: continue
        q = json.load(open(f, encoding='utf-8'))
        pairs |= {(r['order'], r['prod_code']) for e in q['ext'] for r in e['rows']}
    pairs = sorted(pairs)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    res, un = [], []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        line, rows, unread = read_page15(im, pairs)
        if line:
            res += [(line,) + r + (png.name,) for r in rows]; un += [(png.name, line, u) for u in unread]
    taken = [x for x in res if x[3] in ('read', 'matched to schedule history')]
    new = [x for x in res if x[3] == 'new order']; chk = [x for x in res if x[3] == 'check']
    silent = tset - {x[:3] for x in res}
    silent = {t for t in silent if not any(c[0] == t[0] for c in chk) or True}
    print(f'{date}: truth {len(truth)} | taken {len(taken)} WRONG {sum(1 for x in taken if x[:3] not in tset)} | new-order boxed {len(new)} '
          f'(right {sum(1 for x in new if x[:3] in tset)}) | check boxed {len(chk)} | unread pictures {len(un)} | truth not in any row {len(tset - {x[:3] for x in res})}')
    if show:
        for x in new + chk: print('   BOXED', x[:4], x[4][:50])
        for u in un: print('   UNREAD', u)
    return res, un


# ---- v16: clean cells (ruled lines erased, trimmed to the text, white margin, black and white) ------------------------
def clean_cell(im, x0, x1, y0, y1, scale, pad=10, thr=150, margin=12):
    """Crop, erase ruled lines (a row of the crop more than half dark), trim to the text rows, binarize, enlarge, border."""
    a = np.asarray(im.crop((int(x0), max(0, int(y0) - pad), int(x1), int(y1) + pad))).copy()
    dark = a < thr
    rows = dark.mean(axis=1)
    a[rows > 0.5, :] = 255                                   # horizontal ruled lines
    dark = a < thr
    cols = dark.mean(axis=0)
    a[:, cols > 0.85] = 255                                   # a bar caught at the edge
    dark = a < thr
    ink_rows = np.where(dark.sum(axis=1) > 1)[0]
    if len(ink_rows):
        a = a[max(0, ink_rows[0] - 2):ink_rows[-1] + 3, :]
    ink_cols = np.where((a < thr).sum(axis=0) > 0)[0]
    if len(ink_cols):
        a = a[:, max(0, ink_cols[0] - 2):ink_cols[-1] + 3]
    c = Image.fromarray(a)
    if scale != 1:
        c = c.resize((max(1, int(c.width * scale)), max(1, int(c.height * scale))), Image.LANCZOS)
    c = c.point(lambda v: 0 if v < 160 else 255)
    out = Image.new('L', (c.width + 2 * margin, c.height + 2 * margin), 255)
    out.paste(c, (margin, margin))
    return out


def ocr_clean(im, x0, x1, y0, y1, scale, psm, wl=ORDER_WL):
    c = clean_cell(im, x0, x1, y0, y1, scale)
    return re.sub(r'\s+', '', pytesseract.image_to_string(c, config=f'--psm {psm} -c tessedit_char_whitelist={wl}').upper())


def evaluate_raw(date, scan, reader='clean', tries=None, show=False):
    """Raw reading, no history: for each printed order row, does some try give the exact order and product?"""
    tries = tries or CELL_TRIES
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    tord = {(l, o) for l, o, _ in truth}
    n = ok_o = ok_p = ok_both = wrong_o = wrong_p = 0
    misses = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if not bars: continue
            yb, sb, db = bars
            o = p = None; raws = []
            for scale, psm in tries:
                f = ocr_clean if reader == 'clean' else ocr_cell
                t = f(im, yb + 5, sb - 3, y0, y1, scale, psm) if o is None else ''
                t2 = f(im, sb + 5, db - 3, y0, y1, scale, psm) if p is None else ''
                raws.append((t, t2))
                if o is None: o = parse_order_cell(t)
                if p is None: p = take_prod(t2)
                if o and p: break
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            n += 1
            ok_o += (line, o) in tord; ok_p += any(pp == p for _, _, pp in truth if _ == line) if p else 0
            ok_both += (line, o, p) in truth
            wrong_o += bool(o) and (line, o) not in tord
            if (line, o, p) not in truth: misses.append((png.name, line, o, p, raws[:2]))
    print(f'{date} [{reader}]: rows {n} / truth {len(truth)} | order right {ok_o} (wrong {wrong_o}) | product right {ok_p} | both right {ok_both}')
    if show:
        for m in misses: print('   ', m)
    return misses


def cells_x(yb, sb, db, w):
    """Cell edges well clear of the bars (they lean with the page skew): order cell, product cell."""
    g = int(w * 0.003)                                        # about 10 px at 300 dpi
    return (yb + g, sb - g), (sb + g, db - g)


def evaluate_raw2(date, scan, show=False, tries=None):
    tries = tries or CELL_TRIES
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    tord = {(l, o) for l, o, _ in truth}
    n = ok_o = ok_both = wrong_o = 0; misses = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if not bars: continue
            (ox0, ox1), (px0, px1) = cells_x(*bars, w)
            o = p = None; raws = []
            for scale, psm in tries:
                t = ocr_clean(im, ox0, ox1, y0, y1, scale, psm) if o is None else ''
                t2 = ocr_clean(im, px0, px1, y0, y1, scale, psm) if p is None else ''
                raws.append((t, t2))
                if o is None: o = parse_order_cell(t)
                if p is None: p = take_prod(t2)
                if o and p: break
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            n += 1; ok_o += (line, o) in tord; ok_both += (line, o, p) in truth; wrong_o += bool(o) and (line, o) not in tord
            if (line, o, p) not in truth: misses.append((png.name, line, o, p, raws[:2]))
    print(f'{date}: rows {n} / truth {len(truth)} | order right {ok_o} (wrong {wrong_o}) | both right {ok_both}')
    if show:
        for m in misses: print('   ', m)
    return misses


# ---- v17: glyph reading of each cell (the plant's own glyph bank, scan_reader/glyph_bank.npz), position rules --------
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scan_reader'))
import ext_scan_reader as XR
_BANK = None
def bank():
    global _BANK
    if _BANK is None:
        _BANK = XR.Bank.load(str(Path(__file__).resolve().parents[1] / 'scan_reader' / 'glyph_bank.npz'))
        if os.environ.get('GLYPH_Q'):                       # the page's copy of the bank (quantized as ui/build.py ships it)
            sys.path.insert(0, str(Path(__file__).resolve().parent)); import build as _B
            _BANK = XR.Bank(_B.dequantize_bank(_B.quantize_bank(_BANK.A)), _BANK.labels).fit()
    return _BANK

DIG = '0123456789'; LET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def glyph_cells(a, x0, x1, y0, y1, pitch, pad=6):
    crop = a[max(0, y0 - pad):y1 + pad, int(x0):int(x1)]
    cells = XR.segment(crop, pitch)
    return [(k, XR.feature(c), box) for (k, g, box), c in zip(cells, cells)]


def decode_order(cells):
    """cells: [(slot, feature, box)]. Base of 7 characters, a dash, 1-2 suffix digits (right of the dash)."""
    B = bank()
    if len(cells) < 9: return None, 0.0, 'too few characters'
    hs = [c[2][3] for c in cells]; hmax = max(hs)
    dash = [i for i, c in enumerate(cells) if c[2][3] < 0.45 * hmax]      # the dash is a short mark
    if len(dash) != 1: return None, 0.0, f'{len(dash)} dash(es)'
    i = dash[0]
    base, suf = cells[:i], cells[i + 1:]
    if len(base) != 7 or not (1 <= len(suf) <= 2): return None, 0.0, f'{len(base)} + {len(suf)} characters'
    best = None
    for pat in (['H', DIG, ONUM.MONTHS, 'A', DIG, DIG, DIG], ['S', 'H', DIG, ONUM.MONTHS, 'A', DIG, DIG],
                ['R', 'P', DIG, DIG, ONUM.MONTHS, DIG, DIG]):             # order_number.py
        s, tot, mg = '', 0.0, 9.0
        for c, allowed in zip(base, pat):
            d = B.dists(c[1]); r = sorted((d.get(ch, 9.0), ch) for ch in allowed)
            s += r[0][1]; tot += r[0][0]; mg = min(mg, (r[1][0] - r[0][0]) if len(r) > 1 else 1.0)
        if best is None or tot < best[1]: best = (s, tot, mg)
    sfx, mg2 = '', 9.0
    for c in suf:
        d = B.dists(c[1]); r = sorted((d.get(ch, 9.0), ch) for ch in DIG)
        sfx += r[0][1]; mg2 = min(mg2, r[1][0] - r[0][0])
    return f'{best[0]}-{sfx}', min(best[2], mg2), ''


def decode_product(cells, codes_by_len):
    """Nearest Product Master code with the same number of characters (the code rule is built into the list)."""
    B = bank()
    n = len(cells)
    opts = codes_by_len.get(n, [])
    if not opts: return None, 0.0, f'{n} characters'
    ds = [B.dists(c[1]) for c in cells]
    sc = sorted((sum(d.get(ch, 9.0) for d, ch in zip(ds, o)), o) for o in opts)
    return sc[0][1], (sc[1][0] - sc[0][0]) if len(sc) > 1 else 1.0, ''


def evaluate_glyph(date, scan, show=False):
    codes_by_len = {}
    for c in PRODS: codes_by_len.setdefault(len(c), []).append(c)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    tord = {(l, o) for l, o, _ in truth}; tprod = {(l, p) for l, _, p in truth}
    n = ok_o = ok_p = ok_both = wrong_o = wrong_p = 0; misses = []; margins = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        rows = []
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if bars: rows.append((y0, y1) + bars)
        crops = [a[max(0, y0 - 6):y1 + 6, yb + 4:db - 4] for (y0, y1, yb, sb, db) in rows]
        pitch = XR.estimate_pitch(crops) if crops else 15.0
        for (y0, y1, yb, sb, db) in rows:
            (ox0, ox1), (px0, px1) = cells_x(yb, sb, db, w)
            oc = glyph_cells(a, ox0, ox1, y0, y1, pitch); pcl = glyph_cells(a, px0, px1, y0, y1, pitch)
            o, om, oe = decode_order(oc); p, pm, pe = decode_product(pcl, codes_by_len)
            n += 1; ok_o += (line, o) in tord; ok_p += (line, p) in tprod; ok_both += (line, o, p) in truth
            wrong_o += bool(o) and (line, o) not in tord; wrong_p += bool(p) and (line, p) not in tprod
            margins.append((om, (line, o) in tord, pm, (line, p) in tprod))
            if (line, o, p) not in truth: misses.append((png.name, line, o, round(om, 2), oe, p, round(pm, 2), pe))
    print(f'{date} [glyph]: rows {n} / truth {len(truth)} | order right {ok_o} wrong {wrong_o} | product right {ok_p} wrong {wrong_p} | both right {ok_both}')
    if show:
        for m in misses: print('   ', m)
    return margins


def clean_cell(im, x0, x1, y0, y1, scale, pad=10, thr=150, margin=12):
    """Crop; split at the sheet's ruled lines and keep the part holding the printed text (the lowest part with ink: the
    band ends at the printed text, handwriting sits above the ruled line); erase ruled lines and edge bars; trim; binarize;
    enlarge; white border."""
    a = np.asarray(im.crop((int(x0), max(0, int(y0) - pad), int(x1), int(y1) + pad))).copy()
    dark = a < thr
    ruled = np.where(dark.mean(axis=1) > 0.5)[0]
    a[ruled, :] = 255
    if len(ruled):                                            # parts between ruled lines: keep the lowest one with ink
        cuts = [0] + [int(r) for r in ruled] + [a.shape[0]]
        parts = [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] > 4]
        def ink_h(s, e):
            r = np.where((a[s:e] < thr).sum(axis=1) > 1)[0]
            return (r[-1] - r[0] + 1) if len(r) else 0
        texty = [(s, e) for s, e in parts if 16 <= ink_h(s, e) <= 34]      # printed characters are ~22-30 px tall
        if len(texty) >= 1 and len(parts) > 1 and len([1 for s, e in parts if ink_h(s, e) > 6]) > 1:
            s, e = texty[-1]; a = a[s:e]
    cols = (a < thr).mean(axis=0)
    a[:, cols > 0.85] = 255
    ink_rows = np.where((a < thr).sum(axis=1) > 1)[0]
    if len(ink_rows): a = a[max(0, ink_rows[0] - 2):ink_rows[-1] + 3, :]
    ink_cols = np.where((a < thr).sum(axis=0) > 0)[0]
    if len(ink_cols): a = a[:, max(0, ink_cols[0] - 2):ink_cols[-1] + 3]
    c = Image.fromarray(a)
    if scale != 1: c = c.resize((max(1, int(c.width * scale)), max(1, int(c.height * scale))), Image.LANCZOS)
    c = c.point(lambda v: 0 if v < 160 else 255)
    out = Image.new('L', (c.width + 2 * margin, c.height + 2 * margin), 255); out.paste(c, (margin, margin))
    return out


import cv2
def suffix_marks(im, x0, x1, y0, y1):
    """Number of printed characters after the dash in an order cell (marks grouped by horizontal overlap)."""
    c = np.asarray(clean_cell(im, x0, x1, y0, y1, 1, margin=4))
    bw = (c < 128).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(bw, 8)
    comps = [st[i] for i in range(1, n) if st[i][4] >= 8]
    if not comps: return None
    hmax = max(s[3] for s in comps)
    dashes = [s for s in comps if s[3] < 0.45 * hmax and s[2] >= s[3]]
    if not dashes: return None
    dx = max(s[0] + s[2] for s in dashes)                  # right end of the (last) dash
    right = sorted([s for s in comps if s[0] > dx and s[3] >= 0.45 * hmax], key=lambda s: s[0])
    groups = []
    for s in right:
        if groups and s[0] <= groups[-1][1] + 1: groups[-1][1] = max(groups[-1][1], s[0] + s[2])
        else: groups.append([s[0], s[0] + s[2]])
    return len(groups)


def parse_order_cell2(t, marks):
    m = ORD_CELL.match(t)
    if not m: return None
    suf = m.group(2)
    if marks and len(suf) > marks: suf = suf[:marks]           # a bar or a split '1' read as an extra character
    if marks and len(suf) < marks: return None
    o, ok = fix_order(m.group(1), suf)
    return o if ok else None


def evaluate_raw3(date, scan, show=False, tries=None):
    tries = tries or CELL_TRIES
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    tord = {(l, o) for l, o, _ in truth}
    n = ok_o = ok_both = wrong_o = 0; misses = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if not bars: continue
            (ox0, ox1), (px0, px1) = cells_x(*bars, w)
            marks = suffix_marks(im, ox0, ox1, y0, y1)
            o = p = None; raws = []
            for scale, psm in tries:
                t = ocr_clean(im, ox0, ox1, y0, y1, scale, psm) if o is None else ''
                t2 = ocr_clean(im, px0, px1, y0, y1, scale, psm) if p is None else ''
                raws.append((t, t2))
                if o is None: o = parse_order_cell2(t, marks)
                if p is None: p = take_prod(t2)
                if o and p: break
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            n += 1; ok_o += (line, o) in tord; ok_both += (line, o, p) in truth; wrong_o += bool(o) and (line, o) not in tord
            if (line, o, p) not in truth: misses.append((png.name, line, o, p, marks, raws[:2]))
    print(f'{date}: rows {n} / truth {len(truth)} | order right {ok_o} (wrong {wrong_o}) | both right {ok_both}')
    if show:
        for m_ in misses: print('   ', m_)
    return misses


# ---- v19: two independent readers (Tesseract on clean cells + the plant glyph bank); a value is taken when they agree --
def read_row_both(im, a, line_pitch, y0, y1, bars, codes_by_len, w):
    (ox0, ox1), (px0, px1) = cells_x(*bars, w)
    marks = suffix_marks(im, ox0, ox1, y0, y1)
    to = tp = None; raws = []
    for scale, psm in CELL_TRIES:
        t = ocr_clean(im, ox0, ox1, y0, y1, scale, psm) if to is None else ''
        t2 = ocr_clean(im, px0, px1, y0, y1, scale, psm) if tp is None else ''
        raws.append((t, t2))
        if to is None: to = parse_order_cell2(t, marks)
        if tp is None: tp = take_prod(t2)
        if to and tp: break
    go, _, _ = decode_order(glyph_cells(a, ox0, ox1, y0, y1, line_pitch))
    gp, _, _ = decode_product(glyph_cells(a, px0, px1, y0, y1, line_pitch), codes_by_len)
    return to, tp, go, gp, raws


def evaluate_both(date, scan, show=False):
    codes_by_len = {}
    for c in PRODS: codes_by_len.setdefault(len(c), []).append(c)
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    tord = {(l, o) for l, o, _ in truth}; tprod = {(l, p) for l, _, p in truth}
    stats = dict(rows=0, o_agree=0, o_agree_wrong=0, p_agree=0, p_agree_wrong=0, both_agree=0, both_agree_wrong=0)
    out = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        rows = []
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if bars: rows.append((y0, y1, bars))
        pitch = XR.estimate_pitch([a[max(0, y0 - 6):y1 + 6, b[0] + 4:b[2] - 4] for y0, y1, b in rows]) if rows else 15.0
        for y0, y1, bars in rows:
            to, tp, go, gp, raws = read_row_both(im, a, pitch, y0, y1, bars, codes_by_len, w)
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            stats['rows'] += 1
            if to and to == go:
                stats['o_agree'] += 1; stats['o_agree_wrong'] += (line, to) not in tord
            if tp and tp == gp:
                stats['p_agree'] += 1; stats['p_agree_wrong'] += (line, tp) not in tprod
            if to and to == go and tp and tp == gp:
                stats['both_agree'] += 1; stats['both_agree_wrong'] += (line, to, tp) not in truth
            out.append((png.name, line, to, go, tp, gp))
    print(date, stats)
    if show:
        for r in out:
            if not (r[2] and r[2] == r[3] and r[4] and r[4] == r[5]): print('   ', r)
    return out


# ---- v20: the decision the page makes, and an audit of every scan on file -------------------------------------------
LOOK_MONTH = {'B': '8', '8': 'B', 'A': '4', '4': 'A'}


def month_fix(o, on):
    """An order reading that the schedule date rules out (order_number.py) is no reading - unless its month is a
    look-alike (B/8, A/4) and the look-alike is possible: then that is the reading (28 Sep p14: 'H6BA020-1', November
    on a September schedule, printed H68A020-1). It is still taken only on file or when the other reader agrees."""
    if not o or not ONUM.problems(o, on):
        return o
    base, suf = o.split('-')
    k = 4 if base.startswith('RP') else 3 if base.startswith('SH') else 2
    alt = base[:k] + LOOK_MONTH.get(base[k], base[k]) + base[k + 1:] + '-' + suf
    return alt if alt != o and not ONUM.problems(alt, on) else None


def decide(to, tp, go, gp, pairs, on=None):
    """-> (order, product, status). Taken: matches an order + product on file, or both readers agree (0 wrong on 28/29 Sep
    in 227 agreements). Otherwise boxed with the best reading. `on` = the schedule date: an order reading dated after it
    (or an H/SH order two years or more before it) is no reading at all (order_number.py)."""
    if on:
        t2, g2 = month_fix(to, on), month_fix(go, on)
        both_fixed = bool(to and go and t2 != to and g2 != go)   # two look-alike fixes agreeing is no agreement
        to, go = t2, g2
    else:
        both_fixed = False
    for o, p in [(to, tp), (go, gp), (to, gp), (go, tp)]:
        if o and p and (o, p) in pairs: return o, p, 'read'
    m = match_pair(to or '', tp or '', pairs) if to and tp else None
    if m and m[0] in (to, go) and m[1] in (tp, gp): return m[0], m[1], 'matched to schedule history'
    if to and to == go and tp and tp == gp and not both_fixed: return to, tp, 'read by both readers'
    o = to if to == go else (to or go); p = tp if tp == gp else (tp or gp)
    return o, p, 'check'


def audit(date, scan, history='before'):
    codes_by_len = {}
    for c in PRODS: codes_by_len.setdefault(len(c), []).append(c)
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        dd = f.stem.split('_')[1]
        if history == 'before' and dd >= date: continue
        q = json.load(open(f, encoding='utf-8'))
        pairs |= {(r['order'], r['prod_code']) for e in q['ext'] for r in e['rows']}
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.30), int(h * 0.08))), config=f'--psm 6 -c tessedit_char_whitelist={WL}')
        mm = re.search(r'LINE\s*N[O0]\s*[:.]?\s*S[EF]([0-9OISBZ]{2})', top)
        if not mm: continue
        line = 'SE' + d(mm.group(1))
        rows = []
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if bars: rows.append((y0, y1, bars))
        pitch = XR.estimate_pitch([a[max(0, y0 - 6):y1 + 6, b[0] + 4:b[2] - 4] for y0, y1, b in rows]) if rows else 15.0
        for y0, y1, bars in rows:
            to, tp, go, gp, raws = read_row_both(im, a, pitch, y0, y1, bars, codes_by_len, w)
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            o, p, st = decide(to, tp, go, gp, pairs)
            res.append((png.name, line, o, p, st, to, tp, go, gp))
    taken = [r for r in res if r[4] != 'check']
    got = {(r[1], r[2], r[3]) for r in res}
    wrong = [r for r in taken if (r[1], r[2], r[3]) not in tset]
    print(f'{date} (history {history}): truth {len(truth)} | rows {len(res)} | taken {len(taken)} WRONG {len(wrong)} | boxed {len(res) - len(taken)} | truth rows with no row {len(tset - got) - sum(1 for r in res if r[4] == "check" and (r[1], r[2], r[3]) not in tset)}')
    for r in wrong: print('   TAKEN BUT DIFFERENT FROM MY TRANSCRIPTION', r)
    return res, truth


# ---- line code: a known line, read two ways, underline erased ---------------------------------------------------------
LINES = ['SE11', 'SE12', 'SE13', 'SE21', 'SE22', 'SE23', 'SE24', 'SE25', 'SE31', 'SE32', 'SE42', 'SE43', 'SE61']


def line_code_box(im):
    """Box of the line-code word ('SE22') next to 'LINE NO' in the title strip, or None (not an EXT page)."""
    w, h = im.size
    strip = im.crop((0, 0, int(w * 0.40), int(h * 0.12)))
    dd = pytesseract.image_to_data(strip, config='--psm 6', output_type=pytesseract.Output.DICT)
    words = [(dd['text'][i].upper(), dd['left'][i], dd['top'][i], dd['width'][i], dd['height'][i], dd['line_num'][i], dd['block_num'][i])
             for i in range(len(dd['text'])) if dd['text'][i].strip()]
    for k, (t, x, y, ww, hh, ln, bl) in enumerate(words):
        if t.startswith('LINE'):
            after = [u for u in words[k + 1:k + 4] if u[5] == ln and u[6] == bl]
            for u in after:
                m = re.search(r'S[EF5][\w]{2}', u[0].replace(':', '').replace('.', ''))
                if m and not u[0].startswith('NO'):
                    return (u[1], u[2], u[1] + u[3], u[2] + u[4])
            if len(after) >= 2:                                  # 'NO:' then the code
                u = after[1] if after[0][0].startswith('NO') else after[0]
                return (u[1], u[2], u[1] + u[3], u[2] + u[4])
    return None


def read_line_code(im):
    """-> (line or None, readings). Underline erased; Tesseract (2 scales, SE + digits) and the glyph bank must agree on a
    known line."""
    box = line_code_box(im)
    if not box: return None, ['no LINE NO label']
    x0, y0, x1, y1 = box
    a = np.asarray(im)
    reads = []
    for scale in (3, 4):
        c = clean_cell(im, x0 - 4, x1 + 6, y0, y1, scale, pad=6)
        t = re.sub(r'\s+', '', pytesseract.image_to_string(c, config='--psm 7 -c tessedit_char_whitelist=SEF0123456789').upper())
        t = 'SE' + t[2:] if len(t) >= 4 else t
        reads.append(t[:4])
    crop = a[max(0, y0 - 6):y1 + 6, max(0, x0 - 4):x1 + 6]
    cells = XR.segment(crop, 15.0)
    g = None
    if len(cells) == 4:
        B = bank(); s = ''
        for c, allowed in zip(cells, ['S', 'E', DIG, DIG]):
            dd_ = B.dists(XR.feature(c)); s += min(allowed, key=lambda ch: dd_.get(ch, 9.0))
        g = s
    reads.append(g)
    vals = [r for r in reads if r in LINES]
    if g in LINES and vals.count(g) >= 2: return g, reads
    if len(vals) >= 2 and len(set(vals)) == 1 and g is None: return vals[0], reads
    return None, reads


def audit_lines():
    for date, scan in [('2026-09-25', 'doc05252320260928124922'), ('2026-09-28', 'doc05253620260928134035'), ('2026-09-29', 'doc05261220260929142225')]:
        pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
        want = {e['scan_page']: e['line'] for e in pk['ext']}
        ok = bad = none = 0
        for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
            im = Image.open(png).convert('L')
            if im.height > im.width: im = im.rotate(-90, expand=True)
            sp = int(png.stem[1:])
            line, reads = read_line_code(im)
            exp = want.get(sp)
            if exp is None and line is None: continue
            if line == exp: ok += 1
            elif line is None: none += 1; print('  ', date, png.name, 'expected', exp, 'NOT READ', reads)
            else: bad += 1; print('  ', date, png.name, 'expected', exp, 'READ', line, reads)
        print(date, 'line codes right', ok, 'wrong', bad, 'not read (page boxed)', none)


def fit_line(t):
    """A Tesseract word -> the known line it can only be (look-alikes only), else None."""
    t = re.sub(r'[^A-Z0-9]', '', (t or '').upper())
    m = re.search(r'S[EF5][0-9A-Z]{2}$', t) or re.search(r'S[EF5][0-9A-Z]{2}', t)    # S, E, two characters: nothing guessed
    if not m: return None
    w = 'SE' + m.group(0)[-2:]
    sc = sorted((strict_dist(w, L), L) for L in LINES)
    return sc[0][1] if sc[0][0] <= 0.6 and (len(sc) < 2 or sc[1][0] - sc[0][0] >= 0.3) else None


def read_line_code2(im):
    """Known line only; the header word (Tesseract), the 'LINE NO. SExx Total' footer (Tesseract, when on the page) and the
    glyph bank on the header (the whole word compared with the 13 lines) - two must agree, else the page is boxed."""
    w, h = im.size
    lines = XR.ocr_lines(np.asarray(im))
    reads, glyph = [], None
    for ln in lines:
        U = ' '.join(t[4] for t in ln).upper()
        if re.search(r'LINE\s*N[O0]', U):
            no = [j for j, t in enumerate(ln) if re.match(r'N[O0]', t[4].upper())]
            if not no or no[0] + 1 >= len(ln): continue
            word = ln[no[0] + 1][4]
            reads.append(('footer' if 'TOTAL' in U else 'header', fit_line(word), word))
            if 'TOTAL' not in U and glyph is None:
                x = ln[no[0]]
                a = np.asarray(im)
                crop = a[max(0, x[1] - 12):x[1] + x[3] + 12, x[0] + x[2] + 5:x[0] + x[2] + 150]
                cells = XR.segment(crop, 15.0)
                if len(cells) >= 4:
                    ds = [bank().dists(XR.feature(c)) for c in cells[:4]]
                    sc = sorted((sum(d.get(ch, 9.0) for d, ch in zip(ds, L)), L) for L in LINES)
                    glyph = sc[0][1] if sc[1][0] - sc[0][0] >= 0.15 else None
                    reads.append(('glyph', glyph, f'{sc[0][1]} {sc[1][0] - sc[0][0]:.2f}'))
    vals = [r[1] for r in reads if r[1]]
    best = max(set(vals), key=vals.count) if vals else None
    if best and vals.count(best) >= 2 and all(v == best for v in vals): return best, reads
    return None, reads


def audit_lines2():
    for date, scan in [('2026-09-25', 'doc05252320260928124922'), ('2026-09-28', 'doc05253620260928134035'), ('2026-09-29', 'doc05261220260929142225')]:
        pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
        want = {e['scan_page']: e['line'] for e in pk['ext']}
        ok = bad = none = 0
        for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
            sp = int(png.stem[1:])
            if sp not in want and sp > max(want): continue
            im = Image.open(png).convert('L')
            if im.height > im.width: im = im.rotate(-90, expand=True)
            line, reads = read_line_code2(im)
            exp = want.get(sp)
            if line == exp: ok += 1
            elif line is None: none += 1; print('  ', date, png.name, 'expected', exp, 'BOXED', reads)
            else: bad += 1; print('  ', date, png.name, 'expected', exp, 'WRONG', line, reads)
        print(date, 'line codes right', ok, 'WRONG', bad, 'boxed', none)


def audit2(date, scan, history='before', show=True):
    codes_by_len = {}
    for c in PRODS: codes_by_len.setdefault(len(c), []).append(c)
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        dd = f.stem.split('_')[1]
        if history == 'before' and dd >= date: continue
        q = json.load(open(f, encoding='utf-8'))
        pairs |= {(r['order'], r['prod_code']) for e in q['ext'] for r in e['rows']}
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    res = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.75), int(h * 0.10))), config='--psm 6').upper()
        if not re.search(r'LINE\s*N[O0]', top) or not re.search(r'EXTRUS|WPPPOPRC|PRODUCTION\s*INSTRUCTION\s*-\s*EXT', top) or re.search(r'LINE\s*N[O0]\W*S[DC]\d', top): continue      # not an extrusion page (CNV: SD.., SC..)
        line, lreads = read_line_code2(im)
        rows = []
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if bars: rows.append((y0, y1, bars))
        pitch = XR.estimate_pitch([a[max(0, y0 - 6):y1 + 6, b[0] + 4:b[2] - 4] for y0, y1, b in rows]) if rows else 15.0
        for y0, y1, bars in rows:
            to, tp, go, gp, raws = read_row_both(im, a, pitch, y0, y1, bars, codes_by_len, w)
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            o, p, st = decide(to, tp, go, gp, pairs)
            if line is None: st = 'check'                                     # line code not certain: the page is boxed
            res.append((png.name, line, o, p, st))
    taken = [r for r in res if r[4] != 'check']
    got = {(r[1], r[2], r[3]) for r in res}
    wrong = [r for r in taken if (r[1], r[2], r[3]) not in tset]
    per_page = {}
    for e in pk['ext']: per_page[e['scan_page']] = len(e['rows'])
    found = {}
    for r in res: found[int(r[0][1:3])] = found.get(int(r[0][1:3]), 0) + 1
    missing_pages = {p: (n, found.get(p, 0)) for p, n in per_page.items() if found.get(p, 0) < n}
    print(f'{date} (history {history}): truth {len(truth)} | rows {len(res)} | taken {len(taken)} WRONG {len(wrong)} | boxed {len(res) - len(taken)} | pages short of rows {missing_pages}')
    if show:
        for r in wrong: print('   TAKEN BUT DIFFERENT FROM MY TRANSCRIPTION', r)
    return res


# ---- v21: the sheet's solid border lines isolate the printed row (handwriting sits between blocks); ruling scraps -------
def line_groups(st, n, W):
    """The sheet's solid lines in a row band, from the pieces of long horizontal runs: a line broken where notes cross
    it (28 Sep p14 under '-BB510': two pieces 15 px apart, one step lower across the tilt) is joined again. Pieces
    (under 18 px high, at least 40 px long) that follow on (gap under 60 px, centres within 8 px) form one line; a line
    spans more than 0.6 of the row. -> [[label, ...], ...] top to bottom."""
    fr = sorted((i for i in range(1, n) if st[i][3] < 18 and st[i][2] >= 40), key=lambda i: st[i][0])
    grp = {i: [i] for i in fr}
    for a_ in fr:
        for b_ in fr:
            if a_ >= b_ or grp[a_] is grp[b_]:
                continue
            gap = max(st[b_][0] - (st[a_][0] + st[a_][2]), st[a_][0] - (st[b_][0] + st[b_][2]))
            ca, cb = st[a_][1] + st[a_][3] / 2, st[b_][1] + st[b_][3] / 2
            if gap < 60 and abs(ca - cb) <= 8:
                g = grp[a_] + grp[b_]
                for k in g:
                    grp[k] = g
    out = []
    for g in {id(g): g for g in grp.values()}.values():
        x0 = min(st[i][0] for i in g); x1 = max(st[i][0] + st[i][2] for i in g)
        top = min(st[i][1] for i in g); bot = max(st[i][1] + st[i][3] for i in g)
        if x1 - x0 > 0.6 * W and bot - top < 24:
            out.append(sorted(g))
    return sorted(out, key=lambda g: min(st[i][1] for i in g))


def isolate_row(a, bars, y0, y1, pad=10, thr=150):
    """-> (page array, y0, y1). A row band holding a solid ruled line with ink on both sides (production notes written above
    a block's top border, James Kuo 30 Sep: "ignore hand writing") is cut along the line - column by column, so a page
    tilted on the glass still cuts cleanly - and only the side holding the printed '|' bars is kept; the rest (and the line)
    is whited out in a copy of the page. Unchanged when there is nothing to cut."""
    h, w = a.shape
    xa, xb = max(0, int(bars[0]) - 6), min(w, int(bars[2]) + 6)
    ya, yb = max(0, int(y0) - pad), min(h, int(y1) + pad)
    reg = (a[ya:yb, xa:xb] < thr).astype(np.uint8)
    W = reg.shape[1]
    op = cv2.morphologyEx(reg, cv2.MORPH_OPEN, np.ones((1, 60), np.uint8))
    cl = cv2.morphologyEx(op, cv2.MORPH_CLOSE, np.ones((5, 25), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cl, 8)
    lines = line_groups(st, n, W)
    if not lines: return a, y0, y1
    H = reg.shape[0]
    yy = np.arange(H)[:, None]
    edges = []                                                   # per line: top and bottom row per column
    for grp in lines:
        m = np.isin(lab, grp) & (op > 0)
        cols = np.where(m.any(axis=0))[0]
        top = np.full(W, np.nan); bot = np.full(W, np.nan)
        for x in cols:
            r = np.where(m[:, x])[0]; top[x], bot[x] = r[0], r[-1]
        xs = np.arange(W); ok = ~np.isnan(top)
        top = np.interp(xs, xs[ok], top[ok]); bot = np.interp(xs, xs[ok], bot[ok])
        edges.append((top, bot))
    line_px = np.zeros_like(reg, bool)
    for top, bot in edges: line_px |= (yy >= top[None, :] - 1) & (yy <= bot[None, :] + 1)
    ink = reg.astype(bool) & ~line_px
    segs = []                                                    # regions between consecutive lines
    bounds = [(None, None)] + edges + [(None, None)]
    for k in range(len(bounds) - 1):
        lo = bounds[k][1]; hi = bounds[k + 1][0]
        m = np.ones_like(reg, bool)
        if lo is not None: m &= yy > lo[None, :] + 1
        if hi is not None: m &= yy < hi[None, :] - 1
        segs.append(m)
    bx = [int(b) - xa for b in bars]
    def score(m):
        e = ink & m
        rows = np.where(e.sum(axis=1) > 2)[0]
        if not len(rows): return None
        nb = 0
        for x in bx:                                             # the printed '|' bars: a tall stroke at the bar column
            c = e[:, max(0, x - 4):x + 5].any(axis=1)
            run = best = 0
            for v in c:
                run = run + 1 if v else 0; best = max(best, run)
            nb += best >= 12
        return nb, rows[0], rows[-1] + 1
    sc = [(score(m), m) for m in segs]
    inked = [(s_, m) for s_, m in sc if s_ and s_[2] - s_[1] > 6]
    if len(inked) < 2: return a, y0, y1
    (nb, r0, r1), keep = max(inked, key=lambda t: (t[0][0], -abs((t[0][2] - t[0][1]) - 24)))
    if nb == 0: return a, y0, y1
    out = a.copy()
    sub = out[ya:yb, xa:xb]
    sub[~keep | line_px] = 255
    return out, ya + int(r0), ya + int(r1)


def glyph_cells(a, x0, x1, y0, y1, pitch, pad=6):
    """Glyph cells of a printed cell; a 1-px ruling scrap is not a character, nor is a short mark at either end (the dash
    is always inside an order number)."""
    crop = a[max(0, y0 - pad):y1 + pad, int(x0):int(x1)]
    cells = [c for c in XR.segment(crop, pitch) if c[2][3] > 1]
    if cells:
        hmax = max(c[2][3] for c in cells)
        while cells and cells[0][2][3] < 0.45 * hmax: cells = cells[1:]
        while cells and cells[-1][2][3] < 0.45 * hmax: cells = cells[:-1]
    return [(c[0], XR.feature(c), c[2]) for c in cells]


def read_row_both(im, a, line_pitch, y0, y1, bars, codes_by_len, w):
    (ox0, ox1), (px0, px1) = cells_x(*bars, w)
    a2, y0, y1 = isolate_row(a, bars, y0, y1)
    if a2 is not a: a, im = a2, Image.fromarray(a2)
    marks = suffix_marks(im, ox0, ox1, y0, y1)
    to = tp = None; raws = []
    for scale, psm in CELL_TRIES:
        t = ocr_clean(im, ox0, ox1, y0, y1, scale, psm) if to is None else ''
        t2 = ocr_clean(im, px0, px1, y0, y1, scale, psm) if tp is None else ''
        raws.append((t, t2))
        if to is None: to = parse_order_cell2(t, marks)
        if tp is None: tp = take_prod(t2)
        if to and tp: break
    go, _, _ = decode_order(glyph_cells(a, ox0, ox1, y0, y1, line_pitch))
    gp, _, _ = decode_product(glyph_cells(a, px0, px1, y0, y1, line_pitch), codes_by_len)
    return to, tp, go, gp, raws


# ---- v22: a line's pages run on until its 'LINE NO. SExx Total' footer, so a page without a footer continues on the next --
def settle_lines(pages):
    """pages: [{'line': certain line or None, 'reads': [(kind, value, raw)]}] in scan order (extrusion pages only).
    A page whose line was not certain takes the line of the next page when it has no footer (the line continues) and its
    own header or glyph reading says the same; or of the previous page when that one had no footer. Two independent
    agreements, as for any other line code; otherwise the page stays boxed."""
    for i, p in enumerate(pages):
        if p['line']: continue
        own = {r[1] for r in p['reads'] if r[1] and r[0] in ('header', 'glyph')}
        has_footer = any(r[0] == 'footer' for r in p['reads'])
        nxt = pages[i + 1] if i + 1 < len(pages) else None
        prv = pages[i - 1] if i else None
        if nxt and not has_footer and nxt['line'] and nxt['line'] in own and len(own) == 1:
            p['line'] = nxt['line']; p['how'] = 'continues on the next page'
        elif prv and prv['line'] and not any(r[0] == 'footer' for r in prv['reads']) and prv['line'] in own and len(own) == 1:
            p['line'] = prv['line']; p['how'] = 'continued from the previous page'
    return pages


def audit3(date, scan, history='before', show=True):
    codes_by_len = {}
    for c in PRODS: codes_by_len.setdefault(len(c), []).append(c)
    pairs = set()
    for f in sorted(Path('data/packets').glob('packet_*.json')):
        dd = f.stem.split('_')[1]
        if history == 'before' and dd >= date: continue
        q = json.load(open(f, encoding='utf-8'))
        pairs |= {(r['order'], r['prod_code']) for e in q['ext'] for r in e['rows']}
    pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
    truth = [(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']]
    tset = set(truth)
    pages = []
    for png in sorted((Path('work/pages') / scan).glob('p[0-9][0-9].png')):
        im = Image.open(png).convert('L')
        if im.height > im.width: im = im.rotate(-90, expand=True)
        a = np.asarray(im); h, w = a.shape
        top = pytesseract.image_to_string(im.crop((0, 0, int(w * 0.75), int(h * 0.10))), config='--psm 6').upper()
        if not re.search(r'LINE\s*N[O0]', top) or not re.search(r'EXTRUS|WPPPOPRC|PRODUCTION\s*INSTRUCTION\s*-\s*EXT', top) or re.search(r'LINE\s*N[O0]\W*S[DC]\d', top): continue
        line, lreads = read_line_code2(im)
        rows = []
        for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
            bars = row_bars(a, y0, y1, w)
            if bars: rows.append((y0, y1, bars))
        pitch = XR.estimate_pitch([a[max(0, y0 - 6):y1 + 6, b[0] + 4:b[2] - 4] for y0, y1, b in rows]) if rows else 15.0
        got = []
        for y0, y1, bars in rows:
            to, tp, go, gp, raws = read_row_both(im, a, pitch, y0, y1, bars, codes_by_len, w)
            if re.search(r'LINE|TOTAL|REPORT', ''.join(x + y for x, y in raws)): continue
            got.append(decide(to, tp, go, gp, pairs, datetime.date.fromisoformat(date)))
        pages.append({'png': png.name, 'line': line, 'reads': lreads, 'rows': got})
    settle_lines(pages)
    res = [(p['png'], p['line'], o, pr, st if p['line'] else 'check') for p in pages for o, pr, st in p['rows']]
    taken = [r for r in res if r[4] != 'check']
    wrong = [r for r in taken if (r[1], r[2], r[3]) not in tset]
    per_page = {e['scan_page']: len(e['rows']) for e in pk['ext']}
    found = {}
    for r in res: found[int(r[0][1:3])] = found.get(int(r[0][1:3]), 0) + 1
    missing_pages = {p: (n, found.get(p, 0)) for p, n in per_page.items() if found.get(p, 0) < n}
    print(f'{date} (history {history}): truth {len(truth)} | rows {len(res)} | taken {len(taken)} WRONG {len(wrong)} | boxed {len(res) - len(taken)} | pages short of rows {missing_pages}')
    for p in pages:
        if p.get('how'): print('   line', p['png'], p['line'], p['how'])
    if show:
        for r in wrong: print('   TAKEN BUT DIFFERENT FROM MY TRANSCRIPTION', r)
        for r in res:
            if r[4] == 'check': print('   boxed', r)
    return res


SCANS = [('2026-09-25', 'doc05252320260928124922'), ('2026-09-28', 'doc05253620260928134035'), ('2026-09-29', 'doc05261220260929142225')]


def dump_parity(out_dir, scans=SCANS):
    """For tests/js/reader_parity.js: each extrusion page as raw grey bytes plus this reader's results per row (bands,
    bars, glyph pitch, row isolation, suffix marks, glyph readings, cleaned-cell size). Run with GLYPH_Q=1 (the page's
    copy of the glyph bank)."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    codes_by_len = {}
    for c in PRODS: codes_by_len.setdefault(len(c), []).append(c)
    n = 0
    for date, scan in scans:
        pk = json.load(open(f'data/packets/packet_{date}.json', encoding='utf-8'))
        for sp in sorted({e['scan_page'] for e in pk['ext']}):
            pg = f'p{sp:02d}'
            im = Image.open(Path('work/pages') / scan / f'{pg}.png').convert('L')
            if im.height > im.width: im = im.rotate(-90, expand=True)
            a = np.asarray(im); h, w = a.shape
            rows = []
            for (y0, y1) in [b for b in row_bands(im, x0=0.086, x1=0.13) if b[0] > h * 0.10]:
                bars = row_bars(a, y0, y1, w)
                rows.append([int(y0), int(y1), [int(v) for v in bars] if bars else None])
            br = [(y0, y1, b) for y0, y1, b in rows if b]
            pitch = XR.estimate_pitch([a[max(0, y0 - 6):y1 + 6, b[0] + 4:b[2] - 4] for y0, y1, b in br]) if br else 15.0
            res = []
            for y0, y1, b in br:
                (ox0, ox1), (px0, px1) = cells_x(*b, w)
                a2, ny0, ny1 = isolate_row(a, b, y0, y1)
                im2 = Image.fromarray(a2) if a2 is not a else im
                go, _, _ = decode_order(glyph_cells(a2, ox0, ox1, ny0, ny1, pitch))
                gp, _, _ = decode_product(glyph_cells(a2, px0, px1, ny0, ny1, pitch), codes_by_len)
                cc = np.asarray(clean_cell(im2, ox0, ox1, ny0, ny1, 3))
                res.append({'y0': y0, 'y1': y1, 'bars': b, 'iso': [int(ny0), int(ny1)], 'marks': suffix_marks(im2, ox0, ox1, ny0, ny1),
                            'go': go, 'gp': gp, 'clean_shape': list(cc.shape), 'clean_dark': int((cc < 128).sum())})
                n += 1
            a.tofile(out_dir / f'{scan}_{pg}.bin')
            json.dump({'W': w, 'H': h, 'bands': rows, 'pitch': pitch, 'rows': res}, open(out_dir / f'{scan}_{pg}.json', 'w'))
    return n
