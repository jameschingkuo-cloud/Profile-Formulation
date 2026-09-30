# Reference and evaluation harness for the in-page scan reader (ui/page.template.html, ocrPage). read_page15 / evaluate15 is
# the version the page mirrors (30 Sep 2026); earlier versions are the record of what was tried. Run from the repo root.
"""Parser for Tesseract text of the EXT page's left strip (to be mirrored in the interface page's JavaScript).
Tested against transcribed packets. Rule: a value is taken only when it is certain (exact, or exactly one Product
Master code among the look-alike variants); anything else is returned flagged, never guessed."""
import itertools, json, re, sys
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


def fix_order(base, suf):
    if base[0] == 'H':                   # H69A039: H + 2 digits + letter + 3 digits
        b = 'H' + d(base[1:3]) + base[3] + d(base[4:7])
    else:                                # RP26811 / RP24C18 / RP25A08: RP + 2 digits + (digit|A-C) + 2 digits
        c4 = base[4] if base[4] in 'ABC' else d(base[4])
        b = 'RP' + d(base[2:4]) + c4 + d(base[5:7])
    s = d(suf)
    ok = bool(re.fullmatch(r'H\d\d[A-Z]\d{3}|RP\d\d[0-9A-C]\d\d', b)) and s.isdigit()
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


ORD_CELL = re.compile(r'^[^A-Z0-9]*(H[0-9A-Z]{6}|RP[0-9A-Z]{5})-*([0-9ITLJZSOD]{1,2})[^A-Z0-9]*$')


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
