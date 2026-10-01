"""Step 2 of a day's scan: every other field of each EXT record, for the Production Records (James Kuo, 1 Oct 2026: "do
read all. But make it two step. Get the fomulation to production team first. then read the rest for the data base update
(Production Record)").

The report is line-printer text: each field sits at a fixed character column between '|' bars (history/prod_instr.py
reads the same columns from the system's PDFs). On the scan, the bars of a record line give the column of every glyph
(the bars found are fitted to the bars' printed columns: on 30 Sep every glyph fell within 0.25 of a column), so the
line is rebuilt as its printed text and cut into fields by column, exactly as the system PDF is parsed:

    T | Mfg# - Ord# | Prod Code | Die | Width Length | Mat .. GSM | Cut Width Length | Total Sheets | pack | # Plt |
    PCs/Stack Stk/Plt | Weight | In-str Date | Web Width

Further cut rows are the lines under the record line with nothing printed left of the cut columns (their bars are
often too faint to find: they take the record line's columns); cut rows at the top of a page belong to the last record
of the page before. Each field is read in its printed form: numbers right-aligned with the commas by their place, sizes
as whole inches and a printed fraction, the pack code NNXNN, the in-str date 'DD-Mon' or 'Stock' (also read by Tesseract,
for months the glyph bank has not seen yet). Glyphs are classified with their own bank (glyph_bank_fields.npz: the glyphs
of these columns labelled from the system PDFs, added to the key-field bank), so the key-field reader and the page
reader are not changed. The logic checks on a record (check_record, agree_cut_rows):
  - every number in its printed form (1,234; 31 5/8 with a real fraction; 30X42; 16-Oct or Stock);
  - # plt x pcs/stack x stk/plt = total sheets within a pallet and a half; 999 pallets (the most the report prints) only
    when the sheets fill at least that many;
  - weight = order width x length x GSM x total sheets x 1.4187e-6 lb (within 3%; 98% of rows within 0.6%);
  - web width = a whole number of cut widths;
  - a record's cut rows are printed alike: one read differently from two or more that agree takes theirs.
The line totals and the previous day's same order are checked in daily/stage2_records.py.
"""
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ext_scan_reader as R  # noqa: E402

BAR_COLS = (0, 4, 20, 34, 42, 64, 100, 122, 132, 142, 148, 163, 175, 184, 196)   # a record line's '|' columns
CUT_BARS = (0, 100, 122, 132, 142, 148, 163, 175, 184, 196)                      # a further cut row
SPANS = {'t': (0, 4), 'actual': (42, 64), 'cut': (100, 122), 'total': (122, 132), 'pack': (132, 142),
         'plts': (142, 148), 'pcs_stk': (148, 163), 'weight': (163, 175), 'instr': (175, 184), 'web': (184, 196)}
CUT_SPANS = ('cut', 'total')
FOOT_SPANS = {'foot_pcs': (110, 132), 'foot_lbs': (150, 175)}    # the line total: 1,094,216 PCs starts in column 122
DIG = R.DIGITS
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
INSTR_OPTIONS = ['Stock'] + [f'{d:02d}-{m}' for m in MONTHS for d in range(1, 32)]
FIELDS_BANK = Path(__file__).resolve().parent / 'glyph_bank_fields.npz'     # only the glyphs these columns add
KEY_BANK = Path(__file__).resolve().parent / 'glyph_bank.npz'
WEIGHT_K, WEIGHT_TOL = 1.4187e-6, 0.03          # 98% of rows within 0.6%; small orders up to 2% (30 Sep H69A206-1)
FRACTION = re.compile(r'^(\d+)(?: (\d+)/(\d+))?$')
NUMBER = re.compile(r'^\d{1,3}(?:,\d{3})*$')


# ------------------------------------------------------------------------------------ columns from the bars
def bar_xs(bw, y0, y1):
    """x of every vertical bar crossing the text band y0..y1 (a '|' printed on that line)."""
    band = bw[max(0, y0 - 4):y1 + 5] > 0
    xs = np.flatnonzero(band.sum(0) >= 0.8 * band.shape[0])
    groups = []
    for x in xs:
        if groups and x - groups[-1][-1] <= 2:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [float(np.mean(g)) for g in groups if len(g) <= 6]


def _fit(xs, cols, a, b, tol):
    """Bars matched to a + b * column, then a and b refitted on them (twice) -> (a, b, matched)."""
    m = []
    for _ in range(3):
        m = match_bars(xs, cols, a, b, tol)
        if len(m) < 3 or max(c for c, _ in m) - min(c for c, _ in m) < 40:
            break
        C, V = np.array([c for c, _ in m], float), np.array([v for _, v in m])
        b, a = (float(v) for v in np.polyfit(C, V, 1))
    return a, b, m


def col_map(xs, cols, b=None, tol=4.0):
    """Fit x = a + b * column to the bars found -> (a, b, bars matched) or None (fewer than 3 bars fit). The pitch b is
    voted for by every pair of bars found and every gap between printed bars (stray strokes then cannot pull it: on the
    SE61 page of 30 Sep the reader's glyph pitch was 15.27, the bars' 15.00); with b given, only the offset is searched."""
    if len(xs) < 2:
        return None
    X, C = np.asarray(xs, float), np.asarray(cols, float)
    if b is None:
        if len(xs) < 3:
            return None
        dx = (X[None, :] - X[:, None])[np.triu_indices(len(X), 1)]
        dc = np.unique((C[None, :] - C[:, None])[np.triu_indices(len(C), 1)])
        cand = (dx[:, None] / dc[None, :]).ravel()
        cand = np.round(cand[(cand > 12) & (cand < 18)] / 0.02).astype(int)
        if not len(cand):
            return None
        v, n = np.unique(cand, return_counts=True)
        bs = [k * 0.02 for k in v[np.argsort(-n)[:10]]]
    else:
        bs = [b]
    best = None
    Xs = np.sort(X)
    for b0 in bs:
        A = (X[:, None] - b0 * C[None, :]).ravel()          # every bar at every printed bar column: count what fits
        E = A[:, None] + b0 * C[None, :]
        i = np.clip(np.searchsorted(Xs, E), 1, len(Xs) - 1)
        hits = (np.minimum(abs(E - Xs[i - 1]), abs(E - Xs[i])) < tol).sum(1)
        for a0 in A[hits == hits.max()][:3]:
            a, b1, m = _fit(xs, cols, float(a0), b0, tol) if b is None else (float(a0), b0, match_bars(xs, cols, a0, b0, tol))
            if len(m) < (3 if b is None else 2):
                continue
            if b is not None:
                a = float(np.median([x - b0 * c for c, x in m]))
            res = max(abs(a + b1 * c - x) for c, x in m)
            key = (len(m), -res)
            if best is None or key > best[0]:
                best = (key, a, b1, m)
    return None if best is None else best[1:]


def match_bars(xs, cols, a, b, tol=5.0):
    """(column, x) of each bar found within tol pixels of a + b * column."""
    out = []
    for c in cols:
        e = a + b * c
        near = [v for v in xs if abs(v - e) < tol]
        if near:
            out.append((c, min(near, key=lambda v: abs(v - e))))
    return out


def text_marks(bw, y0, y1, x0, x1):
    """Text-height marks in a band (an instruction line has many; a cut row has none left of its columns)."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(bw[y0:y1 + 1, max(0, x0):x1], 8)
    return sum(1 for i in range(1, n) if st[i][3] >= 12)


def instr_text(im, y0, y1, a, b):
    """The In-str Date column read by Tesseract as well: a second reading for the months the glyph bank has few or no
    samples of (the three days it was trained on hold Sep, Oct, Nov and Stock; one Aug, one Mar)."""
    import pytesseract
    crop = im[max(0, y0 - 10):y1 + 10, int(a + b * 176.4):int(a + b * 183.6)]
    if not crop.size:
        return ''
    crop = cv2.copyMakeBorder(cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), 20, 20, 20, 20,
                              cv2.BORDER_CONSTANT, value=255)
    return pytesseract.image_to_string(crop, config='--psm 7').strip()


def line_cells(im, y0, y1, a, b, spans):
    """Glyph cells of the named spans of one printed line: {span: [(column, feature, box)]}."""
    out = {}
    for name in spans:
        c1, c2 = SPANS.get(name) or FOOT_SPANS[name]
        x0, x1 = int(round(a + b * (c1 + 0.6))), int(round(a + b * (c2 - 0.6)))
        crop = im[max(0, y0 - 10):y1 + 10, max(0, x0):x1]
        cells = []
        if crop.size:
            for c in R.segment(crop, b):
                k, g, (cx, cy, cw, ch) = c
                col = int(round((max(0, x0) + cx + cw / 2 - a) / b))
                if c1 < col < c2:
                    cells.append((col, R.feature(c), c[2]))
        out[name] = cells
    return out


def page_lines(im, bw, runs, end, pitch=None):
    """Each record of a page (runs: its record lines) -> [{kind, y0, y1, a, b, bars, cells}] for the record line and the
    cut rows under it, or None when its bars cannot be placed (that record is then read by eye). One pitch for the page
    (the median of the lines with most bars found: a line with few bars can fit a pitch 0.4% off, a column at the right
    end, 30 Sep H64A289-1); each line's own offset from its bars. A cut row's bars are often too faint to find: it takes the
    record line's columns. The cut rows end at the first line with text left of the cut columns."""
    bars = [bar_xs(bw, r0, r1) for r0, r1 in runs]
    fits = [col_map(xs, BAR_COLS) for xs in bars]
    span = lambda f: f[2][-1][0] - f[2][0][0]
    good = [f[1] for f in fits if f and len(f[2]) >= 8] or [f[1] for f in fits if f and len(f[2]) >= 5 and span(f) >= 60]
    bp = float(np.median(good)) if good else None
    maps = []
    for xs, f in zip(bars, fits):
        if f and len(f[2]) >= 6 and span(f) >= 120 and (bp is None or abs(f[1] / bp - 1) < 0.01):
            maps.append(f)                             # enough bars across the line: its own pitch
        elif bp is not None and col_map(xs, BAR_COLS, b=bp):
            maps.append(col_map(xs, BAR_COLS, b=bp))   # else the page's pitch, the line's own offset
        elif f and len(f[2]) >= 4 and span(f) >= 40:
            maps.append(f)                             # a page with no line of many bars: the line's own fit
        else:
            maps.append(None)
    # the offset drifts smoothly down a page (what deskew leaves): a line placed by few bars that is off the drift of the
    # well-placed lines by more than a third of a column takes the drift's offset
    sure = [(r[0], mp[0]) for r, mp in zip(runs, maps) if mp and len(mp[2]) >= 5]
    if len(sure) >= 3:
        k1, k0 = np.polyfit([y for y, _ in sure], [a for _, a in sure], 1)
        for i, (r, mp) in enumerate(zip(runs, maps)):
            if mp and len(mp[2]) < 5 and abs(mp[0] - (k0 + k1 * r[0])) > mp[1] / 3:
                maps[i] = (float(k0 + k1 * r[0]), mp[1], mp[2])
    out = []
    for k, ((r0, r1), mp) in enumerate(zip(runs, maps)):
        if mp is None:
            out.append(None)
            continue
        a, b, m = mp
        lines = [{'kind': 'record', 'y0': r0, 'y1': r1, 'a': a, 'b': b, 'bars': len(m), 'cells': line_cells(im, r0, r1, a, b, SPANS),
                  'instr_text': instr_text(im, r0, r1, a, b)}]
        limit = runs[k + 1][0] - 6 if k + 1 < len(runs) else end
        lines += cut_lines(im, bw, r1 + 8, limit, a, b)
        out.append(lines)
    return out


def cut_lines(im, bw, y_from, y_to, a, b):
    """The cut rows between y_from and y_to (under a record line, or at the top of a page where a record's block carries
    on from the page before: 24 Sep 2026 H64A244-1). They end at the first line with text left of the cut columns."""
    out = []
    for y0, y1 in R.ink_runs(bw, int(a + b * 101), int(a + b * 131), y_from, y_to, min_ink=8, min_h=12):
        if text_marks(bw, y0, y1, int(a + b * 20), int(a + b * 98)) >= 3:
            break                                      # an instruction line: the cut rows have ended
        m2 = match_bars(bar_xs(bw, y0, y1), CUT_BARS, a, b)
        a2 = float(np.median([x - b * c for c, x in m2])) if m2 else a
        out.append({'kind': 'cut', 'y0': y0, 'y1': y1, 'a': a2, 'b': b, 'bars': len(m2),
                    'cells': line_cells(im, y0, y1, a2, b, CUT_SPANS)})
    return out


def read_cut(dec, ln):
    by = {c[0]: c for cs in ln['cells'].values() for c in cs}
    return {'width': read_size(dec, by, SIZE_AT['cut_width'])[0], 'length': read_size(dec, by, SIZE_AT['cut_length'])[0],
            'total_sheets': read_number(dec, by, NUM_END['total'])[0]}


def carry_cuts(bank, rec, lines, page):
    """Cut rows at the top of a page belong to the last record of the page before."""
    dec = R.Decoder(bank)
    rec['fields']['cut_rows'] += [read_cut(dec, ln) for ln in lines]
    rec['field_flags'] = (rec.get('field_flags') or []) + [f'{len(lines)} cut row(s) continue at the top of scan page {page}']
    rec['field_flags'] += agree_cut_rows(rec['fields']['cut_rows'])


# ------------------------------------------------------------------------------------ text, field by field
FRACS = sorted({f'{n}/{d}' for d in (2, 4, 8, 16, 32) for n in range(1, d, 2)})
NUM_END = {'total': 130, 'weight': 173, 'plts': 146, 'pcs': 154, 'stk': 161}      # right-aligned: last column
NUM_MAX = {'total': 9, 'weight': 9, 'plts': 3, 'pcs': 4, 'stk': 1}               # widest printed (history 2020-2026)
SIZE_AT = {'order_width': 44, 'order_length': 54, 'cut_width': 102, 'cut_length': 112, 'web_width': 186}
PACK_AT, INSTR_AT = 134, 177
MISSING = 1.5                                         # cost of a printed character with no glyph read in its column


def read_number(dec, by, end, commas=True, width=9):
    """A right-aligned number whose last digit is in column `end`: digits by glyph, the commas by their place (every
    fourth column from the right, only between digits: a comma is small and often read as a digit or not at all).
    -> (text, margin, columns used)."""
    s, m, col = '', 1.0, end
    while len(s) < width:
        if commas and (end - col) % 4 == 3:
            if col - 1 in by:
                s, col = ',' + s, col - 1
                continue
            break
        if col not in by:
            break
        ch, mg = dec.char(by[col], DIG)
        s, m, col = ch + s, min(m, mg), col - 1
    return s, (m if s else 0.0), set(range(col + 1, end + 1))


def read_size(dec, by, start):
    """'W' or 'W N/D' printed from column `start`: whole inches, a space, a fraction (one of the printed forms 1/2 ..
    31/32: a slash is read as 1 or 7 on its own, never inside a fraction). -> (text, margin, columns used)."""
    col, w, m = start, '', 1.0
    while col in by:
        ch, mg = dec.char(by[col], DIG)
        w, m, col = w + ch, min(m, mg), col + 1
    if not w:
        return '', 0.0, set()
    run, c = [], col + 1
    while c in by:
        run.append(by[c])
        c += 1
    if not run:
        return w, m, set(range(start, col))
    fx, mg = dec.word(run, [f for f in FRACS if len(f) == len(run)])
    if fx is None:
        return f'{w} ?', 0.0, set(range(start, c))
    return f'{w} {fx}', min(m, mg), set(range(start, c))


def read_pack(dec, by):
    """Pack code NNXNN from column 134: digits by glyph, the X's place chosen by the glyphs."""
    run, c = [], PACK_AT
    while c in by:
        run.append(by[c])
        c += 1
    sc = []
    for p in range(1, len(run) - 1):
        s, cost = '', 0.0
        for i, cell in enumerate(run):
            ch = 'X' if i == p else dec.char(cell, DIG)[0]
            s += ch
            cost += dec.bank.dists(cell[1]).get(ch, 9.0)
        sc.append((cost, s))
    sc.sort()
    if not sc:
        return '', 0.0, set()
    return sc[0][1], (sc[1][0] - sc[0][0]) if len(sc) > 1 else 1.0, set(range(PACK_AT, c))


def read_instr(dec, by):
    """In-str date from column 177: 'DD-Mon' or 'Stock', the option whose characters the glyphs in their columns fit best."""
    cols = [c for c in by if 176 <= c <= 183]
    if not cols:
        return '', 0.0, set()
    sc = []
    for o in INSTR_OPTIONS:
        cost = sum(dec.bank.dists(by[INSTR_AT + i][1]).get(ch, 9.0) if INSTR_AT + i in by else MISSING for i, ch in enumerate(o))
        cost += MISSING * sum(1 for c in cols if not INSTR_AT <= c < INSTR_AT + len(o))
        sc.append((cost, o))
    sc.sort()
    return sc[0][1], sc[1][0] - sc[0][0], set(range(176, 184))


def decode(dec, lines):
    """page_lines() output for one record -> (the packet fields {'T', 'order_width', ...}, reading flags)."""
    by = {c[0]: c for cs in lines[0]['cells'].values() for c in cs}
    out, margin, used = {}, {}, {2}
    t = by.get(2)
    out['T'], margin['T'] = dec.char(t, ['Y', 'N']) if t else ('', 1.0)
    for k in ('order_width', 'order_length', 'web_width'):
        out[k], margin[k], u = read_size(dec, by, SIZE_AT[k])
        used |= u
    cw, mw, u1 = read_size(dec, by, SIZE_AT['cut_width'])
    cl, ml, u2 = read_size(dec, by, SIZE_AT['cut_length'])
    ts, mt, u3 = read_number(dec, by, NUM_END['total'])
    used |= u1 | u2 | u3
    out['cut_rows'] = [{'width': cw, 'length': cl, 'total_sheets': ts}]
    margin['cut_rows'] = min(mw, ml, mt)
    out['pack_code'], margin['pack_code'], u = read_pack(dec, by)
    used |= u
    for k, n, commas in (('num_plt', 'plts', False), ('pcs_per_stack', 'pcs', False), ('stk_per_plt', 'stk', False),
                         ('weight_lbs', 'weight', True)):
        out[k], margin[k], u = read_number(dec, by, NUM_END[n], commas, NUM_MAX[n])
        used |= u
    out['instr_date'], margin['instr_date'], u = read_instr(dec, by)
    used |= u
    flags = []
    t = snap_instr(lines[0].get('instr_text', ''))
    if t and t != out['instr_date']:
        few = [ch for ch in t if counts(dec.bank).get(ch, 0) < 5]
        if few:                                    # letters the glyph bank has (almost) never seen: Tesseract's reading
            flags.append(f"in-str date '{t}' read by Tesseract (glyphs: '{out['instr_date']}'; the glyph bank has few "
                         f"samples of {''.join(sorted(set(few)))})")
            out['instr_date'], margin['instr_date'] = t, 1.0
        else:
            flags.append(f"in-str date: glyphs read '{out['instr_date']}', Tesseract '{t}' - check")
    flags += [f'{k}: low confidence' for k, m in margin.items() if out.get(k) and m < R.MARGIN]
    extra = sorted(c for c in by if c not in used)
    if extra:
        flags.append(f'marks read in columns {extra} outside the printed fields (handwriting?)')
    out['cut_rows'] += [read_cut(dec, ln) for ln in lines[1:]]
    flags += agree_cut_rows(out['cut_rows'])
    return out, flags


def counts(bank):
    if not hasattr(bank, '_counts'):
        from collections import Counter
        bank._counts = Counter(str(x) for x in bank.labels)
    return bank._counts


def snap_instr(text):
    """Tesseract's in-str date -> the printed option it reads as ('0' and 'O' look alike in this font), or ''."""
    t = re.sub(r'[^0-9A-Za-z-]', '', text or '')
    m = re.fullmatch(r'([0-9OoDQ]{2})-?([0-9A-Za-z]{3})', t)
    if t.lower().replace('0', 'o') == 'stock':
        return 'Stock'
    if not m:
        return ''
    day = m.group(1).translate(str.maketrans('OoDQ', '0000'))
    mon = m.group(2).replace('0', 'O')
    mon = next((x for x in MONTHS if x.lower() == mon.lower()), None)
    return f'{day}-{mon}' if mon and f'{day}-{mon}' in INSTR_OPTIONS else ''


def agree_cut_rows(rows):
    """A record's cut rows are printed alike (240 of 240 records with more than one, 23 - 30 Sep 2026). One row read
    differently from all the others (at least two that agree) was misread: it takes theirs, with the reason. Two rows
    that differ: flagged, never chosen between."""
    if len(rows) < 2:
        return []
    key = lambda r: (r['width'], r['length'], r['total_sheets'])
    from collections import Counter
    c = Counter(key(r) for r in rows)
    (best, n), = c.most_common(1)
    if n == len(rows):
        return []
    if n >= 2 and n == len(rows) - 1:
        i = next(i for i, r in enumerate(rows) if key(r) != best)
        was = ' '.join(key(rows[i]))
        rows[i] = dict(zip(('width', 'length', 'total_sheets'), best))
        return [f"cut row {i + 1} read '{was}', the other {n} rows '{' '.join(best)}': taken from them"]
    return [f'cut rows read differently: {[" ".join(key(r)) for r in rows]} - check']


# ------------------------------------------------------------------------------------ logic checks
def fraction(s):
    """'31 5/8' -> 31.625; None unless whole inches and, if any, a reduced fraction of 2, 4, 8, 16 or 32."""
    m = FRACTION.match(s.strip())
    if not m:
        return None
    w, n, d = m.groups()
    if n is None:
        return float(w)
    n, d = int(n), int(d)
    if d not in (2, 4, 8, 16, 32) or not 0 < n < d or n % 2 == 0:
        return None
    return int(w) + n / d


def number(s):
    s = s.strip()
    return int(s.replace(',', '')) if NUMBER.match(s) else None


def check_record(f, gsm):
    """The printed forms and the arithmetic between one record's fields -> list of problems ('' = none)."""
    bad = []
    for k in ('order_width', 'order_length', 'web_width'):
        if fraction(f[k]) is None:
            bad.append(f"{k} '{f[k]}' is not a size")
    for i, c in enumerate(f['cut_rows']):
        for k in ('width', 'length'):
            if fraction(c[k]) is None:
                bad.append(f"cut row {i + 1} {k} '{c[k]}' is not a size")
        if number(c['total_sheets']) is None:
            bad.append(f"cut row {i + 1} sheets '{c['total_sheets']}' is not a number")
    for k in ('num_plt', 'pcs_per_stack', 'stk_per_plt'):
        if not f[k].isdigit():
            bad.append(f"{k} '{f[k]}' is not a number")
    if number(f['weight_lbs']) is None:
        bad.append(f"weight '{f['weight_lbs']}' is not a number")
    if not re.fullmatch(r'\d+X\d+', f['pack_code']):
        bad.append(f"pack code '{f['pack_code']}' is not NNXNN")
    if f['instr_date'] not in INSTR_OPTIONS:
        bad.append(f"in-str date '{f['instr_date']}' not read")
    if bad:
        return bad
    sheets = sum(number(c['total_sheets']) for c in f['cut_rows'])
    pl, ps, sp = int(f['num_plt']), int(f['pcs_per_stack']), int(f['stk_per_plt'])
    if pl == 999 and sheets <= 998 * ps * sp:        # 999 = the most the report prints: at least that many pallets
        bad.append(f'# plt printed 999 but total sheets {sheets:,} fill {sheets / (ps * sp):,.0f} pallets of {ps} x {sp}')
    if pl != 999 and abs(pl - sheets / (ps * sp)) > 1.5:   # the report rounds pallets either way by up to one (2024-26)
        bad.append(f'# plt {pl} x pcs/stack {ps} x stk/plt {sp} = {pl * ps * sp:,}, total sheets {sheets:,}')
    w, l = fraction(f['order_width']), fraction(f['order_length'])
    if gsm:
        est = w * l * int(str(gsm).replace(',', '')) * sheets * WEIGHT_K
        if est and abs(number(f['weight_lbs']) / est - 1) > WEIGHT_TOL:
            bad.append(f"weight {f['weight_lbs']} lb, size x GSM x sheets gives {est:,.0f}")
    cw = fraction(f['cut_rows'][0]['width'])
    web = fraction(f['web_width'])
    if cw and web and abs(web / cw - round(web / cw)) > 0.02:
        bad.append(f"web width {f['web_width']} is not a whole number of cut widths {f['cut_rows'][0]['width']}")
    return bad


def read_row(bank, row):
    """One record of page_rows(fields=True) -> (packet fields or None, flags)."""
    lines = row.get('fields_lines')
    if not lines:
        return None, ["the record line's bars were not found: its other columns are read by eye"]
    return decode(R.Decoder(bank), lines)


# ------------------------------------------------------------------------------------ truth from the system PDF
def _history():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'history'))
    import prod_instr as H
    return H


def pdf_blocks(pdf):
    """{order: [record line text, further cut row texts ...]} from the system's own PDF of the report."""
    import pymupdf
    H = _history()
    d = pymupdf.open(str(pdf))
    stream = []
    for pno in range(d.page_count):
        g = H.grid(d[pno]) if H.upright(d[pno]) else H.grid_any(d[pno])
        hdr = next((k for k, L in enumerate(g) if L.startswith('|___|')), 3)
        stream += g[hdr + 1:]
    out, cur = {}, None
    for L in stream:
        m = H.ROW_RX.match(L)
        if m:
            cur = out.setdefault(f'{m.group(2)}-{m.group(3)}', [L])
        elif cur is not None and H.CUT_RX.match(L):
            cur.append(L)
        elif L.startswith('|___'):
            cur = None
    return out


def pdf_fields(lines):
    """The packet fields of one record from its system-PDF lines (cut as prod_instr.parse_pdf cuts them)."""
    cells = lines[0].split('|')
    ao, cd = cells[5], cells[7]
    ps = cells[11].split()
    f = {'T': cells[1].strip(), 'order_width': ao[1:11].strip(), 'order_length': ao[11:].strip(),
         'cut_rows': [{'width': cd[1:11].strip(), 'length': cd[11:].strip(), 'total_sheets': cells[8].strip()}],
         'pack_code': cells[9].strip(), 'num_plt': cells[10].strip(), 'pcs_per_stack': ps[0] if ps else '',
         'stk_per_plt': ps[1] if len(ps) > 1 else '', 'weight_lbs': cells[12].strip(), 'instr_date': cells[13].strip(),
         'web_width': cells[14].strip(), 'gsm': cells[6].split()[-1]}
    for L in lines[1:]:
        c = L.split('|')
        f['cut_rows'].append({'width': c[2][1:11].strip(), 'length': c[2][11:].strip(), 'total_sheets': c[3].strip()})
    return f


def labelled(row, truth):
    """(feature, label) for each glyph of a record and its cut rows whose column holds a printed character in the truth
    lines; and the count of glyphs on a column the truth leaves blank (handwriting, marks: not labelled)."""
    pairs, blank = [], 0
    for ln, text in zip(row.get('fields_lines') or [], truth):
        for span, cs in ln['cells'].items():
            for col, f, box in cs:
                ch = text[col] if col < len(text) else ' '
                if ch in ' |':
                    blank += 1
                else:
                    pairs.append((f, ch))
    return pairs, blank


def _infos(scan, cache_dir, workers):
    import pickle
    p = Path(cache_dir) / (Path(scan).stem + '.fields.pkl')
    if p.exists():
        return pickle.load(open(p, 'rb'))
    infos = R.read_pages(scan, instructions_crop=False, workers=workers, fields=True)
    pickle.dump(infos, open(p, 'wb'))
    return infos


def _orders(infos, key_bank):
    dec = R.Decoder(key_bank)
    return [[R.decode_row(dec, row)[0].get('order') for row in info['rows']] for info in infos]


def load_bank(path=None):
    """The bank for these columns: the key-field bank plus the glyphs labelled from these columns (stored on their own)."""
    key, z = R.Bank.load(str(KEY_BANK)), np.load(str(path or FIELDS_BANK))
    return R.Bank(list(key.A) + list(z['X']), list(key.labels) + list(z['y'])).fit()


def build_bank(pair_lists, key_bank):
    b = R.Bank(list(key_bank.A), list(key_bank.labels))
    for pairs in pair_lists:
        for f, ch in pairs:
            b.add(f, ch)
    return b.fit()


def score(infos, orders, blocks, bank):
    """Per field: right / wrong against the system PDF, and what the logic checks say about each record."""
    from collections import Counter
    c, wrong = Counter(), []
    bank.prime([x[1] for info in infos for row in info["rows"] for ln in (row.get("fields_lines") or [])
                for cs in ln["cells"].values() for x in cs])
    for info, ords in zip(infos, orders):
        for row, o in zip(info['rows'], ords):
            if o not in blocks:
                continue
            f, flags = read_row(bank, row)
            if f is None:
                c['no bars'] += 1
                continue
            t = pdf_fields(blocks[o])
            probs = check_record(f, t['gsm'])
            for k in t:
                if k != 'gsm':
                    ok = f.get(k) == t[k]
                    c[(k, ok)] += 1
                    if not ok:
                        wrong.append((o, k, f.get(k), t[k], '; '.join(probs) or 'CHECKS PASS'))
            c['checks flagged' if probs else 'checks pass'] += 1
    return c, wrong


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='train / score the step-2 field reader on scans with their system PDFs')
    ap.add_argument('cmd', choices=['train', 'loo'])
    ap.add_argument('pairs', nargs='+', help='scan.pdf system.pdf [scan.pdf system.pdf ...]')
    ap.add_argument('--cache', default=str(Path(__file__).resolve().parents[1] / 'work' / 'fields_cache'))
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--out', default=str(FIELDS_BANK), help='train: the bank to write')
    a = ap.parse_args()
    Path(a.cache).mkdir(parents=True, exist_ok=True)
    key_bank = R.Bank.load(str(Path(__file__).resolve().parent / 'glyph_bank.npz'))
    data = []
    for scan, pdf in zip(a.pairs[::2], a.pairs[1::2]):
        infos = _infos(scan, a.cache, a.workers)
        orders = _orders(infos, key_bank)
        blocks = pdf_blocks(pdf)
        pairs, blank, n = [], 0, 0
        for info, ords in zip(infos, orders):
            for row, o in zip(info['rows'], ords):
                if o in blocks:
                    p, bl = labelled(row, blocks[o]); pairs += p; blank += bl; n += 1
        print(f'{Path(scan).name}: {n} records matched to the PDF, {len(pairs)} glyphs labelled, {blank} on blank columns')
        data.append((scan, infos, orders, blocks, pairs))
    if a.cmd == 'train':
        pairs = [x for d in data for x in d[4]]
        np.savez_compressed(a.out, X=np.array([f for f, _ in pairs], np.float32), y=np.array([ch for _, ch in pairs]))
        print(f'{a.out}: {len(pairs)} glyphs added to the key-field bank, labels {"".join(sorted({ch for _, ch in pairs}))}')
    else:                                                  # leave one day out: train on the others, score the one left
        for i, (scan, infos, orders, blocks, pairs) in enumerate(data):
            bank = build_bank([d[4] for j, d in enumerate(data) if j != i], key_bank)
            c, wrong = score(infos, orders, blocks, bank)
            ks = [k for k in ('T', 'order_width', 'order_length', 'cut_rows', 'pack_code', 'num_plt', 'pcs_per_stack',
                              'stk_per_plt', 'weight_lbs', 'instr_date', 'web_width')]
            print(f'== {Path(scan).name} (bank without it): ' + ', '.join(f'{k} {c[(k, True)]}/{c[(k, True)] + c[(k, False)]}' for k in ks))
            print(f"   checks pass {c['checks pass']}, flagged {c['checks flagged']}; bars not found {c['no bars']}")
            for w in wrong:
                print('   ', w[0], w[1], '| read', w[2], '| printed', w[3], '| checks:', w[4][:160])
