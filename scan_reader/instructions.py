"""Special instructions: snap OCR text to the lines the system really prints (James Kuo, 1 Oct 2026: "the main goal is to
improve the OCR read and logic check when OCR read failed").

The system's own schedules (history/prod_instr.py -> work/history/ext_history.csv, Apr 2020 - Sep 2026) hold the exact
text of every special-instruction line ever printed. Instructions repeat ("Send to Guillotine. Mark lead edge & make sure
of pc count." ...), so an OCR line is matched to the printed line it is closest to, with its numbers as placeholders:
the printed wording, spacing-free punctuation (a comma vs a period cannot be told apart on the scan) and spelling come
from the library, and the numbers ("123 PLTS DONE", "RANGE IS 582 - 600 GSM") come from the OCR. A line that matches
nothing closely enough is kept as read and flagged. Logic checks on the result:
  - a line that is only numbers and fractions is a cut row that leaked into the text: dropped;
  - a standard line that always sits between two lines that were read (e.g. "Sheets must be flat. ..." after "Send to
    Guillotine. ...") but was not read: flagged as missed (never filled in silently).
"""
import csv
import difflib
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
import product_code as PC  # noqa: E402
HIST = [ROOT / 'work' / 'history' / 'ext_history.csv', ROOT / 'work' / 'history' / 'ext_history_scans.csv']
MIN_RATIO = 0.86
_LIB = None
import os  # noqa: E402
EXCLUDE = set(filter(None, os.environ.get('INSTR_EXCLUDE_DATES', '').split(',')))   # leave-one-day-out scoring


def key(s):
    """Comparison key: letters kept, every digit run one '#', everything else dropped."""
    return re.sub(r'[^A-Z#]', '', re.sub(r'\d+', '#', (s or '').upper()))


def library():
    """-> (templates: {key: (printed line, count)}, follows: {line key: Counter(next line key)}). The printed form of a
    line is its most recent one: the wording and punctuation can change over the years ('Hold' / 'hold')."""
    global _LIB
    if _LIB is None:
        latest, count, follows = {}, Counter(), defaultdict(Counter)
        for p in HIST:
            if not p.exists():
                continue
            for r in csv.DictReader(open(p, encoding='utf-8')):
                if r['date'] in EXCLUDE:          # scoring a day: its own text is left out of the library
                    continue
                parts = [re.sub(r'\s+', ' ', x).strip() for x in (r['special'] or '').split(' / ')]
                parts = [x for x in parts if x]
                for i, x in enumerate(parts):
                    k = key(x)
                    if len(k) >= 4:
                        count[k] += 1
                        f = re.sub(r'\d+', '#', x)
                        FORMS[k][f] = max(FORMS[k].get(f, ''), r['date'])
                        if k not in latest or r['date'] >= latest[k][0]:
                            latest[k] = (r['date'], f)
                    if i + 1 < len(parts):
                        follows[k][key(parts[i + 1])] += 1
        tmpl = {k: (latest[k][1], count[k]) for k in latest}
        _LIB = (tmpl, follows)
    return _LIB


FORMS = defaultdict(dict)        # key -> {printed form: latest date}: one line can be typed with different spacing


def best_form(k, ocr):
    """Of the printed forms of one line, the one whose spacing matches the scan (spacing is read reliably); punctuation is
    not compared (a comma and a period look alike on the scan), so ties go to the most recent form."""
    sp = lambda s: re.sub(r'[.,]', '', re.sub(r'\d+', '#', s))          # case is read reliably: compared too
    o = sp(ocr)
    return min(FORMS[k], key=lambda f: (difflib.SequenceMatcher(None, sp(f), o).ratio() * -1, -int(FORMS[k][f].replace('-', ''))))


# letters a scan of this printer font confuses (glyph bank and Tesseract misreads seen on the daily scans)
CONFUSE = {frozenset(p) for p in ['EF', 'JL', 'IL', 'IT', 'OD', 'OQ', 'CG', 'MN', 'HN', 'UV', 'BE', 'BR', 'PR', 'SB', 'ZS', 'KR']}


def ocr_explains(k, c):
    """True when the read key k differs from the printed key c only in ways a scan explains: confusable letters, a few
    noise characters read after (or before) the text, and at most one other single-character slip on a long line. A real
    wording difference ('RUN WIHT' vs 'RUN WITH': letters swapped) is not explained, so the line is kept as read."""
    other = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, k, c, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        if op == 'replace' and i2 - i1 == j2 - j1 and all(frozenset((a, b)) in CONFUSE for a, b in zip(k[i1:i2], c[j1:j2])):
            continue
        if op in ('replace', 'insert') and set(c[j1:j2]) == {'#'} and i2 - i1 <= 4:
            continue                              # a number not read (handwriting over it, smudge): it stays '?' below
        if op == 'insert' and i1 == 0 and j1 == 0 and j2 - j1 <= 1:
            continue
        if op == 'delete' and (i2 == len(k) and i2 - i1 <= 4 or i1 == 0 and i2 - i1 <= 2):   # noise read after / before
            continue
        other += max(i2 - i1, j2 - j1)
    return other == 0 or (other == 1 and len(c) >= 30)


def _fill(template, ocr):
    """Put the OCR's digit runs into the template's '#' slots, in order. None if the counts differ."""
    nums = re.findall(r'\d+', ocr)
    slots = template.count('#')
    if slots != len(nums):
        return None
    it = iter(nums)
    return re.sub(r'#', lambda m: next(it), template)


NUMERIC_LINE = re.compile(r'^[\d\s/.,:;|~-]+$')


NOISE_LETTERS = set('EOCNRSAW')
_VOCAB, _PRODS = set(), set()


def _vocab():
    """Words the system prints in instructions, and product codes it has printed (for 'RUN WITH RPA40WB3051')."""
    if not _VOCAB:
        tmpl, _ = library()
        for f in tmpl.values():
            _VOCAB.update(w for w in re.findall(r'[A-Z]+', f[0].upper()))
        for p in HIST:
            if p.exists():
                _PRODS.update(r['prod_code'] for r in csv.DictReader(open(p, encoding='utf-8')) if r['prod_code'])
    return _VOCAB, _PRODS


def preclean(t):
    """Before matching: a product code in the text repaired by the code rules when the repair is a product the system has
    printed (RPA4OWB3051 -> RPA40WB3051, RPA40W83051 -> RPA40WB3051); short marks made only of letters a dotted line reads
    as ('ee', 'oo', 'EES', 'worse') dropped unless they are words the instructions use."""
    vocab, prods = _vocab()
    out = []
    for tok in t.split():
        core = re.sub(r'[^A-Za-z0-9]', '', tok)
        u = core.upper()
        if len(u) >= 8 and re.match(r'^[A-Z]{3}', u) and u not in prods:
            fixed, _ = PC.repair(u)                                 # the code rule: letters / digits by position
            colour8 = u[:5] + u[5:7].replace('8', 'B') + u[7:]      # B read as 8 in the colour
            for cand in (fixed, colour8, PC.repair(colour8)[0]):
                if cand and cand in prods:
                    tok = tok.replace(core, cand)
                    break
        letters = re.sub(r'[^A-Za-z]', '', tok)
        if letters and len(letters) <= 5 and not re.search(r'\d', tok) and set(letters.upper()) <= NOISE_LETTERS \
                and letters.upper() not in vocab:
            continue
        out.append(tok)
    return ' '.join(out)


def snap_line(text):
    """-> (printed text, how): how = 'library' | 'library (numbers kept as read)' | 'as read' | 'dropped: cut row'."""
    t = re.sub(r'\s+', ' ', text or '').strip(' :;~|')
    t = preclean(t)
    if not t:
        return '', 'empty'
    if NUMERIC_LINE.match(t):
        return '', 'dropped: cut row numbers'
    tmpl, _ = library()
    k = key(t)
    if k in tmpl:
        best = k
    else:
        cands = difflib.get_close_matches(k, tmpl.keys(), n=8, cutoff=MIN_RATIO - 0.1)
        ok = [c for c in cands if ocr_explains(k, c)]
        best = max(ok, key=lambda c: (difflib.SequenceMatcher(None, k, c).ratio(), tmpl[c][1])) if ok else None
    if best is None:
        return t, 'as read (no printed line explains it)'
    template = best_form(best, t)
    filled = _fill(template, t)
    if filled is None:                    # a lone digit read from a mark after the text ('... RPA40WB3051 0 EEE')
        t2 = re.sub(r'(\s+\d)+\s*$', '', t)
        filled = _fill(template, t2) if t2 != t else None
    if filled is not None:
        return filled, 'library'
    return template.replace('#', '?'), 'library (numbers not read: ? marks them)'


def snap(special, sep=' | '):
    """A whole instruction block as read (lines joined by sep) -> (printed text joined by ' / ', flags)."""
    raw = [x for x in (special or '').split(sep)]
    out, flags = [], []
    for x in raw:
        s, how = snap_line(x)
        if how.startswith('dropped'):
            flags.append(f'"{x.strip()}" {how}')
            continue
        if s:
            out.append(s)
            if how.startswith('as read') or '?' in how:
                flags.append(f'"{s}" {how}')
    # a standard line that always comes between two lines that were read, but was not read
    _, follows = library()
    keys = [key(x) for x in out]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if follows[a] and b not in follows[a]:
            mid = follows[a].most_common(1)[0][0]
            if b in follows.get(mid, {}):
                tmpl, _ = library()
                flags.append(f'a line seems missed after "{out[i]}": usually "{tmpl[mid][0]}"')
    return ' / '.join(out), flags
