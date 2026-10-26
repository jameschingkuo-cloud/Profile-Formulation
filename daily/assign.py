"""Rule-based formula assignment (James Kuo, 23 Oct 2026: "There are too many new product code which make the one to one
match not very useful. To make it work, we need to build logic system so that you assign formulation to product base on
logic"). The rules, quoted from James and tested, are in docs/FORMULA_ASSIGNMENT_RULES.md:

  R1  colour other than KS (black) / WB (white) -> graphic grade, third character 'A'; KS / WB take the schedule's grade
      (A -> 'A', P -> '0'); the special grades (UV, flame retardant, anti-static, opaque, smooth) are always 'A';
      the bubble line (SE61, BF codes) is always '0' ("its BF0 even when its EB").
  R2  reclaim only in KS / WB formulations (a consequence of R1; not used to choose, only to check).
  R3  the schedule's Spec column decides the first two letters (R1R1R1 -> FU, R4R4R4 -> RU, OPOPOP -> FX, S1S1S1 -> FS,
      R2R2R2 -> FU as Tech issues it (RU0001WB4 'LTL wrap' is a customer-specific Main),
      A1A1A1 -> FA, U1U1U1 -> FE ("Extra UV is FE"; FH on older pages), F?F?F? -> FR, the bubble line's R6/RD/RM -> BF).
  R4  the three middle digits are a version number: which version is current is what James marked Main in the W% Master.
  R5  summer formulation 1 Apr - 31 Oct, winter 1 Nov - 31 Mar, where a key has a "Summer" and a "Winter" Main.

The authority for "which code is Main" is James's annotated W% Master (data/w_master/...xlsx, Notes column). A proposal
names the Main code (James's final name after his renames) and, when Tech has issued that formulation on the line
before under any of its old printed names, those settings as last printed. A Main without settings on the line is not a
formulation yet (the auger calculation from the W% is the next step): it stays an Exception that names the code.

    python daily/assign.py                      -> the rule table and a self-test on the exceptions of recent drafts
"""
import datetime
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import product_code as pc  # noqa: E402

W_MASTER = config.ROOT / 'data' / 'w_master' / 'W Master Formulation draft (version 1) - James notes 2026-10-23.xlsx'
# James's notes given after that file (it stays as received): (code, its note in the file, the note now). Applied on read
# by rules() and calc/revise_w_master.py, so the daily run and the W% v2 revision agree.
LATER_NOTES = [
    ('FU0032KS3', 'Main, Packaging grade',
     'obsolete (James, 26 Oct 2026: "obsolete this one"; 23 Oct note: Main, Packaging grade)'),
]

# codes Tech issues that have no W% Master row, renamed by James after 23 Oct (printed under the new name; the W% Master
# gets the row at the clean-up)
LATER_RENAMES = {
    'FR0021FW4': ('FRA021FW4', 'James, 26 Oct 2026, on RP26826-6 (SE21 FW 4 mm flame retardant): "ok we need to change '
                               'it to FRA as well. make a notes, we will clean up after"'),
}


def apply_later_notes(R):
    """Rewrite the Notes of the W% Master rows James re-noted after 23 Oct (LATER_NOTES)."""
    for r in R:
        for code, old, new in LATER_NOTES:
            if r['Formula Code'] == code and (r['Notes'] or '').strip() == old:
                r['Notes'] = new
    return R

PREFIX = {'R1R1R1': 'FU', 'R3R3R3': 'FU', 'R2R2R2': 'FU', 'R4R4R4': 'RU', 'OPOPOP': 'FX', 'S1S1S1': 'FS',
          'A1A1A1': 'FA', 'U1U1U1': 'FE', 'F1F1F1': 'FR', 'F4F4F4': 'FR', 'R6R6R6': 'BF', 'RDRDRD': 'BF', 'RMR6R6': 'BF'}
OLD_PREFIX = {'FE': ('FH',)}            # James, 23 Oct 2026: "Extra UV is FE"; Tech's older pages print FH for it
SPECIAL = {'OPOPOP', 'S1S1S1', 'A1A1A1', 'U1U1U1', 'F1F1F1', 'F4F4F4'}      # always graphic grade 'A'
BLACK_WHITE = {'KS', 'WB'}
ALWAYS_A = {PREFIX[s] for s in SPECIAL}                 # FX FS FA FE FR: R1, always graphic grade 'A'
CODE_RX = re.compile(r'\b([A-Z]{2}[A-Z0-9]{3,5}[A-Z]{2,3}[0-9A-Z])\b')
RENAME_RX = re.compile(r'(?:change (?:name )?to|replace name with|change)\s+([A-Z]{2}[A-Z0-9]{3,5}[A-Z]{2,3}[0-9A-Z])', re.I)
W_COLS = ['Virgin PP %', 'Homo PP (F1203K) %', 'Reclaim %', 'Talc %', 'CaCO3 %', 'Colour MB %', 'Vistamaxx %',
          'Additive %', 'Foam %', 'HDPE %', 'Skin %', 'Other %']
# words in James's notes that make a Main apply to some orders only (the schedule or the line says which)
QUALIFIERS = {'void': ('void',), 'corn': ('corn',), 'sign': ('sign blank', 'spa'), 'summer': ('summer',),
              'winter': ('winter',), 'se43': ('se43',), '6.3': ('6.3',), '4.6': ('4.6',), 'roll': ('roll',), 'ltl': ('ltl',)}
# words that mark a Main for a customer or a product kind the schedule does not name: never proposed by rule
RESTRICTED = ('orbis', 'carter', 'tzu', 'vistech', 'nissan', 'batten', 'cabbage', 'hdpe', 'pe f', 'pe part',
              'bb line', 'customer', 'triple wall')


def level(note):
    n = (note or '').strip().lower()
    if n.startswith(('main', 'customer')):
        return 'main'
    if n.startswith('secondary'):
        return 'secondary'
    if n.startswith(('replace', 'replay', 'relace', 'replacey')):
        return 'replace'
    if n.startswith(('remove', 'delete', 'obsolete')):
        return 'remove'
    if 'archive' in n or n.startswith(('sample', 'basel')):
        return 'archive'
    return 'other'


def final_code(row):
    m = RENAME_RX.search(row['Notes'] or '')
    return m.group(1) if m else row['Formula Code']


def quals(note):
    n = (note or '').lower()
    return frozenset(q for q, words in QUALIFIERS.items() if any(w in n for w in words))


def restricted(note):
    n = (note or '').lower()
    return any(w in n for w in RESTRICTED)


def canon_prefix(pre):
    """'FH' -> 'FE' (the old letter for extra UV); anything else as it is."""
    return next((k for k, olds in OLD_PREFIX.items() if pre in olds), pre)


def thk_char(mm):
    """4.0 -> '4'; 6.3 -> '6' (a 6.3 mm order runs a ..6 code); 10 -> 'A'; 13 -> 'D'; 25 -> 'P'."""
    n = int(mm + 1e-9)
    return str(n) if n < 10 else chr(ord('A') + n - 10)


def season(day):
    """R5: 'summer' from 1 Apr to 31 Oct, 'winter' from 1 Nov to 31 Mar."""
    return 'summer' if 4 <= day.month <= 10 else 'winter'


_RULES = None


def rules():
    """James's W% Master, read once: Main / Secondary rows with their key, qualifiers, composition and the printed
    names Tech used for them (the row's own code and every row James says to replace by it)."""
    global _RULES
    if _RULES is not None:
        return _RULES
    from openpyxl import load_workbook
    config.record_read(W_MASTER, "W% Master with James's notes (formula assignment)")
    ws = load_workbook(W_MASTER, read_only=True, data_only=True)['Formulation + Latest Run']
    rows = list(ws.iter_rows(values_only=True))
    R = apply_later_notes([dict(zip(rows[0], r)) for r in rows[1:] if r[0]])
    mains, by_key = [], defaultdict(list)
    for r in R:
        lv = level(r['Notes'])
        if lv not in ('main', 'secondary') or not r['Colour'] or r['Thk (mm)'] is None:
            continue
        code = final_code(r)
        if len(code) != 9:
            continue                     # premix colours / odd lengths: James to spell them (rules doc R1)
        m = {'code': code, 'printed': {r['Formula Code'], code}, 'level': lv, 'quals': quals(r['Notes']),
             'restricted': restricted(r['Notes']), 'application': r['Application'], 'note': r['Notes'],
             'key': (canon_prefix(code[:2]), code[2], r['Colour'][:2], thk_char(float(r['Thk (mm)']))),
             'w': {c: r.get(c) for c in W_COLS}, 'materials': r.get('Materials')}
        mains.append(m); by_key[m['key']].append(m)
    # "replace by/with ..." rows fold into their Main. An old name of the same formulation (its composition within SAME_TOL
    # of the Main's: James consolidating names, e.g. FUA152WB4 on the auger lines -> his FUA151WB4 "Summer") goes in
    # 'printed': it prints as the Main (R6) and its settings anywhere are the Main's. One with another composition (SE25's
    # FU0021WB4 at 36% reclaim -> FU0031WB4 at 20%) goes in 'replaces' only: its issued rows on a line are that line's own
    # recipe of the Main, used after the Main's own names (member_settings; James, 24 Oct 2026).
    for r in R:
        if level(r['Notes']) != 'replace':
            continue
        target = replace_target(r, mains)
        if target is None:
            continue
        if same_composition(r, target['w']):
            target['printed'].add(r['Formula Code'])
        target.setdefault('replaces', set()).add(r['Formula Code'])
    _RULES = {'mains': mains, 'by_key': by_key}
    return _RULES


def current_name(code):
    """James's name for a code (James, 23 Oct 2026: "Don't use old formula code in the print out"). An old name that is
    not a current Main / Secondary name anywhere (FU0014BA4 -> FUA014BA4, FH0012WB4 -> FHA012WB4, RO000WB4 -> RU0000WB4)
    becomes the name he gave it; a name still current (FUA152WB4 is his winter name and the sign-blank Main) or one that
    points to several Mains stays as printed."""
    if code in LATER_RENAMES:
        return LATER_RENAMES[code][0]
    R = rules()
    if 'rename' not in R:
        current = {m['code'] for m in R['mains']}
        to = defaultdict(set)
        for m in R['mains']:
            for p in m['printed']:
                if p not in current:
                    to[p].add(m['code'])
        R['rename'] = {p: next(iter(c)) for p, c in to.items() if len(c) == 1}
    return R['rename'].get(code, code)


SAME_TOL = 2.5      # points of weight %, every material group


def same_composition(row, w):
    """True when the row's W% is within SAME_TOL of the Main's on every group (James's rounded values)."""
    return all(abs((row.get(c) or 0) - (w.get(c) or 0)) <= SAME_TOL for c in W_COLS)


def replace_target(r, mains):
    """The Main (or Secondary) a "replace by/with ..." row folds into: the code named in the note; the row's own code
    (another version of it marked Main); else, by description, the one of the same colour, thickness, prefix and grade
    with the same words. None when none or several fit."""
    note = r['Notes'] or ''
    lv = 'secondary' if 'secondary' in note.lower() else 'main'
    codes = CODE_RX.findall(note)
    named = [c for c in codes if c != r['Formula Code']]
    if named:
        t = [m for m in mains if m['code'] == named[0] or named[0] in m['printed']]
        return t[0] if len(t) == 1 else (next((m for m in t if m['level'] == lv), None) if t else None)
    if codes:                                  # its own code: the version of it James marked Main / Secondary
        t = [m for m in mains if r['Formula Code'] in m['printed'] and m['level'] == lv]
        t = t or [m for m in mains if r['Formula Code'] in m['printed']]
        for narrow in (lambda m: quals(note) == m['quals'],          # "replace by Main SPA FUA152WB4": the sign-blank Main
                       lambda m: m['code'] == r['Formula Code'],      # the version still under this name, not one that absorbed it
                       lambda m: not m['restricted']):                # the plain Main, not a customer's
            if len(t) > 1:
                t = [m for m in t if narrow(m)] or t
        return t[0] if len(t) == 1 else None
    own = final_code(r)
    gch = 'A' if 'graphic' in note.lower() else ('0' if 'pack' in note.lower() else (own[2] if len(own) == 9 else None))
    cands = [m for m in mains if m['level'] == lv and not m['restricted'] and m['key'][2] == (r['Colour'] or '')[:2]
             and r['Thk (mm)'] is not None and m['key'][3] == thk_char(float(r['Thk (mm)'])) and m['quals'] == quals(note)
             and m['key'][0] == canon_prefix(own[:2]) and (gch is None or m['key'][1] == gch)]
    return cands[0] if len(cands) == 1 else None


def derive(line, row):
    """The code's fixed parts for a schedule row: (prefix, grade char, colour, thickness char) or (None, why)."""
    prod = row.get('prod_code') or ''
    m = pc.CODE_RX.match(prod)
    mm = pc.thickness_mm(prod)
    if not m or mm is None:
        return None, f'product code {prod!r} does not keep the code rule'
    colour = m.group(4)
    parts = (row.get('mat_spec') or '').split()
    grade, spec = (parts[1] if len(parts) > 2 else ''), (parts[-1] if parts else '')
    prefix = PREFIX.get(spec)
    if not prefix:
        return None, f'no rule for spec {spec!r} yet'
    si = (row.get('special_instructions') or '').upper()
    if spec == 'R2R2R2' and ('LTL' in si or 'WRAP' in si):
        prefix = 'RU'                                      # LTL wrap: James's Main is RU0001WB4 "Main, R2 LTL wrap"
    if prefix == 'BF':
        gchar = '0'                                        # bubble line: packaging grade only (James, 23 Oct)
    elif colour not in BLACK_WHITE or spec in SPECIAL:
        gchar = 'A'                                        # R1
    elif grade in ('A', 'P'):
        gchar = 'A' if grade == 'A' else '0'
    else:
        return None, f'grade {grade!r} on a {colour} order: cannot tell graphic from packaging'
    return (prefix, gchar, colour, thk_char(mm)), ''


def wanted(line, row, day):
    """The qualifiers an order asks for, from its special instructions and line."""
    si = (row.get('special_instructions') or '').upper()
    prod = row.get('prod_code') or ''
    q = set()
    if 'VOIDFORM' in si or 'VOID FORM' in si:
        q.add('void')
    if 'CORN' in si:
        q.add('corn')
    # R7 (James, 23 Oct 2026): "The slitter should use the same formula like SPA signs blank". A sign blank is an SPA
    # (or SPP) product, or any order sent to the slitter; Tech prints these under "(For sign blank orders only)".
    if 'SIGN BLANK' in si or 'SIGNBLANK' in si or 'SLIT' in si or prod[:3] in ('SPA', 'SPP'):
        q.add('sign')
    # R8 (James, 23 Oct 2026, H69A284-3: "we don't have roll formulation??"): a roll order says ROLLS / ROLLED MATERIAL;
    # Tech prints "(For roll material only)"; James's Main is FU0021WB4 "Main roll". LTL wrap likewise ("LTL MATERIAL").
    if 'ROLL' in si:
        q.add('roll')
    if 'LTL' in si or 'WRAP' in si:
        q.add('ltl')
    mm = pc.thickness_mm(row.get('prod_code') or '')
    if mm is not None and abs(mm - 6.3) < 1e-6:
        q.add('6.3')
    if mm is not None and abs(mm - 4.6) < 1e-6:
        q.add('4.6')
    return q, season(day)


RECLAIM_MIN = 1.0      # W% points: from this much up a formulation counts as one with reclaim


def w_reclaim(m):
    """James's W% for the formulation carries reclaim."""
    return (m['w'].get('Reclaim %') or 0) >= RECLAIM_MIN


def uses_reclaim(f):
    """A formula row (issued page or calc sheet) feeds reclaim: a reclaim material with a setting above 0."""
    for v in f['feeders'].values():
        mat, s = (v.get('material') or '').lower(), str(v.get('set') or '')
        try:
            n = float(s.replace(',', ''))
        except ValueError:
            n = 0
        if 'reclaim' in mat and n > 0:
            return True
    return False


BASE_RESIN = ('virgin', 'silo', '6502', 'sv258', 'basell', 'braskem', '1203k', '1102k', 'talc')


def r4_recipe(f):
    """An R4 row: reclaim and none of the virgin base (virgin PP, homopolymer, talc) - colour masterbatch and CaCO3 at most
    beside it. James, 24 Oct 2026: "if it's a R4 black production, it should run about 98% black reclaim and 2% black
    color dye or master batch". Keeps a packaging recipe printed under an old name folded into an R4 Main (SE21's FU0041KS4
    page: virgin 32, mix reclaim 70, talc, CaCO3) from being printed as the R4 one."""
    if not uses_reclaim(f):
        return False
    for v in f['feeders'].values():
        mat, s = (v.get('material') or '').lower(), str(v.get('set') or '').strip().lower()
        try:
            fed = s == 'auto' or float(s.replace(',', '')) > 0
        except ValueError:
            fed = False
        if fed and 'reclaim' not in mat and any(k in mat for k in BASE_RESIN):
            return False
    return True


ADDITIVE_RX = re.compile(r'\b(?:UV|AS|FR)[- ]?N?(\d{5})', re.I)


def feeds_additives(f, m):
    """A row carries every additive (UV, anti-static, flame retardant) the member's W% lists, by its number: FEA001NSA
    (UV-N26257A) and FHA001NSA (UV-N26177A) were both printed FH0001NSA, so SE22's FH0001NSA recipe (N26177A) is
    FHA001NSA's, not FEA001NSA's (James, 26 Oct 2026: "U1 is for FEA")."""
    need = set(ADDITIVE_RX.findall(m.get('materials') or ''))
    if not need:
        return True
    fed = set()
    for v in f['feeders'].values():
        s = str(v.get('set') or '').strip().lower()
        try:
            on = s == 'auto' or float(s.replace(',', '')) > 0
        except ValueError:
            on = False
        if on:
            fed |= set(re.findall(r'(\d{5})', v.get('material') or ''))
    return need <= fed


R4_BLACK = (98.0, 2.0)     # % black reclaim, % black colour MB (James, 24 Oct 2026)
_SLOPES = None


def slope(line, column, reclaim):
    """The current calibration slope (g/min per setting unit) of a line's hopper ('Hopper 3') for reclaim or for a colour
    masterbatch, from Tech's calc library (sheet "Auger Calibration"); None if not there."""
    global _SLOPES
    if _SLOPES is None:
        _SLOPES = defaultdict(list)
        if CALC_LIB.exists():
            from openpyxl import load_workbook
            ws = load_workbook(CALC_LIB, read_only=True, data_only=True)['Auger Calibration']
            rows = list(ws.iter_rows(values_only=True))
            for r in rows[1:]:
                d = dict(zip(rows[0], r))
                if d['Current Slope (g/min per unit)']:
                    _SLOPES[(d['Line'], d['Feeder'])].append(d)
    m = re.fullmatch(r'Hopper (\d)', column)
    if not m:
        return None
    rs = [d for d in _SLOPES.get((line, 'H' + m.group(1)), [])
          if ('RECLAIM' in str(d['Material Class']).upper()) == reclaim and (reclaim or 'COLOR' in str(d['Material Class']).upper())]
    rs.sort(key=lambda d: str(d['Last Used'] or ''), reverse=True)
    return float(rs[0]['Current Slope (g/min per unit)']) if rs else None


def r4_black_settings(line, m):
    """Calculated settings for an R4 black Main with no R4 recipe on the line. James, 24 Oct 2026, on H6AA173-1 (RU0000KS5,
    SE21): "remember the [auger] setting is applied universally ... look at other [auger] setting with similar products
    such as black productions and then put them together. And besides, if it's a R4 black production, it should run about
    98% black reclaim and 2% black color dye or master batch". Auger lines only.
    1. Tech's latest issued R4 black recipe on the line (any thickness; SE21: RU0000KS4, Mix Reclaim on hopper 3 at 99,
       KS colour on hopper 4 at 10): the reclaim hopper as Tech runs it, the colour hopper set for 98/2 with the line's
       calibration slopes.
    2. Else the line's R4 black recipe in Tech's calc sheet for the hoppers and slopes, and the line's black recipes of the
       same thickness for the throughput (median g/min, the last three years of the sheet); setting = share x g/min / slope.
    -> (rows, ('calcd', template date, detail)) or (None, None)."""
    if line in ('SE24', 'SE42', 'SE43', 'SE61'):
        return None, None
    best = None
    for (ln, _), gs in _ISSUED_GROUPS.items():
        if ln != line:
            continue
        for date, page, fs in gs:
            for f in fs:
                if f['formula_code'][-3:-1] == 'KS' and r4_recipe(f) and (best is None or date > best[0]):
                    best = (date, page, f)
    if best:
        date, page, f = best
        fed = {c: v for c, v in f['feeders'].items() if v.get('material') and str(v.get('set') or '').strip() not in ('', '0')}
        rec = [c for c, v in fed.items() if 'reclaim' in v['material'].lower()]
        col = [c for c, v in fed.items() if 'reclaim' not in v['material'].lower() and 'caco3' not in v['material'].lower()]
        if len(rec) == 1 and len(col) == 1 and len(fed) == 2:
            s_r, k_r, k_c = float(fed[rec[0]]['set']), slope(line, rec[0], True), slope(line, col[0], False)
            if k_r and k_c:
                s_c = round(R4_BLACK[1] / R4_BLACK[0] * s_r * k_r / k_c)
                feeders = {c: dict(v) for c, v in f['feeders'].items()}
                feeders[col[0]]['set'] = str(s_c)
                return ([{'formula_code': m['code'], 'feeders': feeders, 'note': ''}],
                        ('calcd', date, {'template': f"{f['formula_code']} as issued on {line} {date} (scan p{page})",
                                         'T': s_r * k_r + s_c * k_c, 'basis': f"{rec[0]} reclaim kept at Tech's {s_r:g}",
                                         'share': R4_BLACK, 'slopes': (k_r, k_c)}))
    calc_recipes()
    on_line = {code: rs for (ln, code), rs in _CALC_RAW.items() if ln == line and code}
    if not on_line:
        return None, None
    last = {code: max(str(d['Last Run'] or '')[:10] for d in rs) for code, rs in on_line.items()}
    tmpl = None
    for code, rs in on_line.items():
        if str(code)[:2] != 'RU' or str(code)[-3:-1] != 'KS' or (line, code) not in _CALC:
            continue
        fed = [d for d in rs if not d['Extruder'] and float(d['g/min'] or 0) > 0]
        rec = [d for d in fed if 'RECLAIM' in str(d['Material Class']).upper()]
        col = [d for d in fed if str(d['Material Class']).upper() == 'KS COLOR']
        if len(fed) == 2 and len(rec) == 1 and len(col) == 1 and (tmpl is None or last[code] > tmpl[0]):
            tmpl = (last[code], code, rec[0], col[0])
    if tmpl is None:
        return None, None
    cut = f'{int(max(last.values())[:4]) - 3}{max(last.values())[4:]}'
    thk = m['key'][3]

    def total(rs):
        return sum(float(d['g/min'] or 0) for d in rs if not d['Extruder'])
    same = [total(rs) for code, rs in on_line.items() if str(code)[:2] in ('FU', 'RU') and str(code)[-1] == thk
            and last[code] >= cut and total(rs) > 0]
    black = [total(rs) for code, rs in on_line.items() if str(code)[:2] in ('FU', 'RU') and str(code)[-1] == thk
             and str(code)[-3:-1] == 'KS' and last[code] >= cut and total(rs) > 0]
    pool, basis = (black, f'{line} black {thk} recipes') if black else ((same, f'{line} {thk} recipes') if same else
                                                                        ([total(on_line[tmpl[1]])], f'{tmpl[1]} on {line}'))
    T = statistics.median(pool)
    _, code, rec, col = tmpl
    s_rec = round(R4_BLACK[0] / 100 * T / float(rec['Calibration Slope (g/min per unit)']))
    s_col = round(R4_BLACK[1] / 100 * T / float(col['Calibration Slope (g/min per unit)']))
    shaped = _CALC[(line, code)][1][0]
    feeders = {c: dict(v) for c, v in shaped['feeders'].items()}
    for c, v in feeders.items():
        if v.get('material'):
            v['set'] = str(s_rec if 'reclaim' in v['material'].lower() else s_col)
    return ([{'formula_code': m['code'], 'feeders': feeders, 'note': ''}],
            ('calcd', last[code], {'template': code, 'T': T, 'basis': f'{basis}, {len(pool)} recipe(s)', 'share': R4_BLACK,
                                   'slopes': (float(rec['Calibration Slope (g/min per unit)']), float(col['Calibration Slope (g/min per unit)']))}))


def choose(key, want, seas, line):
    """The Main for a key and what the order asks for. -> (main, why) with main None when none or several fit."""
    cands = [m for m in rules()['by_key'].get(key, []) if m['level'] == 'main' and not m['restricted']]
    if 'void' in want:
        # R10 (James, 23 Oct 2026): "void form should not use any reclaim" - "The reclaim calcium is not stable ... It
        # makes it very difficult to control the weight when we're running with reclaim". Never a reclaim formulation.
        cands = [m for m in cands if not w_reclaim(m)]
    if not cands:
        return None, 'no Main in the W% Master for ' + '/'.join(key) + (' without reclaim (VOIDFORM)' if 'void' in want else '')
    def fits(m):
        q = set(m['quals'])
        if 'se43' in q:
            if line != 'SE43':
                return False
            q.discard('se43')
        if ('summer' in q or 'winter' in q):
            if seas not in q:
                return False
            q -= {'summer', 'winter'}
        return q == want
    fit = [m for m in cands if fits(m)]
    if line == 'SE43' and any('se43' in m['quals'] for m in fit):
        fit = [m for m in fit if 'se43' in m['quals']]           # James: "Main SE43" / "Main SE43 only" outranks the general Main there
    if not fit and want:                                   # e.g. VOIDFORM with no VOIDFORM Main: the plain Main
        fit = [m for m in cands if fits_plain(m, seas, line)]
    if len({m['code'] for m in fit}) > 1 and key[0] == 'FE':
        # James, 26 Oct 2026, on NS 10 mm FEA001NSA / FHA001NSA: "U1 is for FEA" - his FE name outranks one kept under
        # the old letter FH (FHA001NSA is the anti-static formula)
        fit = [m for m in fit if m['code'][:2] == 'FE'] or fit
    codes = {m['code'] for m in fit}
    if len(codes) == 1:
        return fit[0], ''
    if not codes:
        return None, 'no Main fits (' + ', '.join(sorted({m['code'] + (' ' + '+'.join(sorted(m['quals'])) if m['quals'] else '') for m in cands})) + ')'
    return None, 'several Mains: ' + ', '.join(sorted(codes))


def fits_plain(m, seas, line):
    q = set(m['quals']) - {'summer', 'winter', 'se43'}
    if 'se43' in m['quals'] and line != 'SE43':
        return False
    if ('summer' in m['quals'] or 'winter' in m['quals']) and seas not in m['quals']:
        return False
    return not q


def names_for_issued(line, row, day, formulas):
    """printed code -> James's name for an order's issued formulas (R6). The order's own qualifiers decide, not the
    note of the group Tech put it in: James, 26 Oct 2026, on RP26717-1 (RPA40WB3051, which Tech grouped with the sign
    blanks): "order RP26717-1 is just standard graphic 40. why is it using sign blank formula?" A page note counts only
    when the order asks for it too."""
    key, why = derive(line, row)
    if key is None:
        return {}
    want, seas = wanted(line, row, day)
    main, _ = choose(key, want, seas, line)
    if main is None:
        return {}
    return {f['formula_code']: main['code'] for f in formulas if f['formula_code'] in main['printed']}


CALC_LIB = config.OUTPUT_DIR / 'Formulation Calc Library.xlsx'      # calc/parse_fcal.py from Tech's SExx Formulation.xls
_CALC = None
_CALC_RAW = {}         # (line, code) -> the calc sheet's rows as written (feeder, material class, slope, setting, g/min)
_PAGES = {}


def set_pages(packets):
    """The latest Tech FRM page per line (feeder columns and the wording printed on each hopper), for calc recipes."""
    global _PAGES
    _PAGES = {}
    for d in sorted(packets):
        for pg in packets[d]['frm']:
            _PAGES[pg['line_code']] = pg


def calc_feeder(line, ext, feeder, columns):
    """A calc-sheet feeder ('H1'; ('A','V1'); ('B','H1') on SE31; 'V1'; ('A','A1')) -> the line's FRM column name."""
    f = str(feeder or '').strip().upper()
    ext = (str(ext or '').strip().upper() or None)
    if f.startswith('#') or ext == 'TOTAL':
        return None
    cands = []
    if f.startswith('H') and f[1:].isdigit():
        cands = [f'Hopper {f[1:]}', f'{ext or "A"} V{f[1:]}', f'Extruder {ext or "A"} V{f[1:]}', f'{ext or "A"} {f[1:]}']
    elif f.startswith('V') and f[1:].isdigit():
        cands = [f, f'{ext or "A"} {f}', f'Extruder {ext or "A"} {f}']
    elif len(f) >= 2 and f[0] in 'ABCD' and f[1:].isdigit():
        cands = [f'{f[0]} {f[1:]}']
    return next((c for c in cands if c in columns), None)


def calc_recipes():
    """Tech's current calc recipes: (line, code) -> (last run, [formula dict]) in the shape of an issued FRM group.
    Settings as Tech wrote them (auger lines: the setting; weight lines: the %); materials re-worded as the line's
    latest FRM page prints the same role on that hopper, else as written in the calc sheet."""
    global _CALC
    if _CALC is not None:
        return _CALC
    _CALC = {}
    if not CALC_LIB.exists():
        return _CALC
    from openpyxl import load_workbook
    sys.path.insert(0, str(config.ROOT / 'calc'))
    from common import mat_key  # noqa: E402
    config.record_read(CALC_LIB, "Tech's calc recipes (formula assignment settings)")
    ws = load_workbook(CALC_LIB, read_only=True, data_only=True)['Current Recipes']
    rows = list(ws.iter_rows(values_only=True))
    H = rows[0]
    groups = defaultdict(list)
    for r in rows[1:]:
        d = dict(zip(H, r))
        groups[(d['Line'], d['Formula Code'])].append(d)
    _CALC_RAW.clear()
    _CALC_RAW.update(groups)
    for (line, code), rs in groups.items():
        pg = _PAGES.get(line)
        columns = pg['feeder_columns'] if pg else []
        # the page's wording for the SAME material (by material key) on that hopper - never another material of the
        # same role: a black order's "KS MB-CR401K" must not come out as the page's "WB-W26038A"
        wording = {}
        if pg:
            for g in pg['groups']:
                for f in g['formulas']:
                    for col, v in f['feeders'].items():
                        if v.get('material'):
                            wording[(col, mat_key(v['material']))] = v['material']
        feeders = {c: {'material': '', 'set': ''} for c in columns}
        for d in rs:
            col = calc_feeder(line, d['Extruder'], d['Feeder'], columns) if columns else (f"Hopper {str(d['Feeder'])[1:]}" if str(d['Feeder']).startswith('H') else None)
            if not col or not d['Material (as written)']:
                continue
            weight = line in ('SE24', 'SE42', 'SE43', 'SE61')
            val = d['Formulation %'] if weight else d['Setting']
            if val is None or (isinstance(val, (int, float)) and float(val) == 0):
                continue                                   # a hopper Tech does not feed is left empty, as on the page
            mat = d['Material (as written)']
            mat = wording.get((col, mat_key(mat)), mat)
            s = f'{float(val):g}' if isinstance(val, (int, float)) else str(val)
            feeders[col] = {'material': mat, 'set': s}
        if any(v['material'] for v in feeders.values()):
            last = max(str(d['Last Run'] or '')[:10] for d in rs)
            _CALC[(line, code)] = (last, [{'formula_code': code, 'feeders': feeders, 'note': ''}])
    return _CALC


_ISSUED_GROUPS = defaultdict(list)     # (line, printed code) -> every issued group with it, newest first


def issued_on_line(packets):
    """(line, printed code) -> (date, scan page, [formula dicts of the group]) from every Tech issue on file, latest wins.
    Every group is kept too (_ISSUED_GROUPS), so an order with a qualifier can take the group Tech noted for it: the
    roll group "(For roll material only)" of FU0021WB4 on SE25, not the plain packaging group under the same code."""
    out = {}
    _ISSUED_GROUPS.clear()
    for date in sorted(packets):
        for pg in packets[date]['frm']:
            for g in pg['groups']:
                for f in g['formulas']:
                    out[(pg['line_code'], f['formula_code'])] = (date, pg['scan_page'], g['formulas'])
                    _ISSUED_GROUPS[(pg['line_code'], f['formula_code'])].insert(0, (date, pg['scan_page'], g['formulas']))
    return out


def group_for(line, printed, want, issued):
    """The issued group to take the settings from: the newest whose notes carry the order's qualifier (roll, VOIDFORM,
    corn box, sign blank), else the newest with no such note, else the newest."""
    groups = _ISSUED_GROUPS.get((line, printed)) or ([issued[(line, printed)]] if (line, printed) in issued else [])
    if not groups:
        return None
    def notes_q(fs):
        q = set()
        for f in fs:
            q |= {x for x in quals(f.get('note', '')) if x in ('roll', 'void', 'corn', 'sign', 'ltl')}
        return q
    marked = {q for q in want if q in ('roll', 'void', 'corn', 'sign', 'ltl')}
    for g in groups:
        if marked and notes_q(g[2]) & marked:
            return g
    for g in groups:
        if not marked and not notes_q(g[2]):
            return g
    return groups[0]


def issued_for_key(line, key, issued):
    """Codes Tech has issued on the line whose fixed parts (R1, R3, colour, thickness) are the key: the W% Master has
    no row for some of them (the bubble line's BF0000EB3 / EB5 are co-extrusion, 'Not computed'). Latest issue first.
    Where R1 makes the order graphic 'A' whatever its grade (a colour, or a special spec), Tech's older '0' name counts
    too: James renames those 0 -> A (FR0021FW3 -> FRA021FW3, FR0021WB4 -> FRA021WB4). James, 26 Oct 2026, on RP26826-6
    (RPP40FW2, F4F4F4, SE21): "you should have Flame retardent formulation for this. look at FR0021FW4"."""
    grades = {key[1]} | ({'0'} if key[1] == 'A' and (key[2] not in BLACK_WHITE or key[0] in ALWAYS_A) else set())
    hits = [(rec, code) for (ln, code), rec in issued.items()
            if ln == line and len(code) == 9 and code[2] in grades
            and (canon_prefix(code[:2]), code[6:8], code[8]) == (key[0], key[2], key[3])]
    return sorted(hits, key=lambda x: x[0][0], reverse=True)


def propose(line, row, day, issued):
    """-> (proposal, why). proposal = dict(code, main, settings=(date, page, formulas) or None, printed_as, season,
    how) or None. 'how' says what decided it: James's Main (with the settings Tech last printed for it on the line), or a
    code already issued on the line for these fixed parts when the W% Master has no Main for them."""
    key, why = derive(line, row)
    if key is None:
        return None, why
    want, seas = wanted(line, row, day)
    main, why = choose(key, want, seas, line)
    if main is None:
        if why.startswith('no Main') and not want:
            prior = issued_for_key(line, key, issued)
            if prior:
                rec, code = prior[0]
                return {'code': current_name(code), 'main': None, 'settings': rec, 'printed_as': code, 'season': seas,
                        'how': f'code already issued on {line} for {"/".join(key)} (no W% Master row)',
                        'settings_src': f'settings as issued on {line} {rec[0]} (FRM scan p{rec[1]})'}, ''
        return None, why
    for printed in sorted(main['printed'], key=lambda c: c != main['code']):   # James's name first, then old names
        rec = group_for(line, printed, want, issued)
        if rec:
            # only this formulation's rows of the issued group (a group can hold another order's primary, e.g. the
            # VOIDFORM run-out FU0022WB3 printed under a FU0042WB3 order); its own run-out partner comes with it, except
            # on a roll or VOIDFORM order: one Main only (James, 24 Oct 2026: "Roll formula should only have one primary formula")
            formulas = [f for f in rec[2] if f['formula_code'] in main['printed']]
            if not formulas:
                continue
            if not want & SPECIAL_ONLY:
                formulas += [f for f in rec[2] if f not in formulas and re.search(r'run\s*out', f.get('note') or '', re.I)]
            return {'code': main['code'], 'main': main, 'settings': (rec[0], rec[1], formulas), 'printed_as': printed, 'season': seas,
                    'how': f"James's Main {main['code']}" + (f' (Tech printed it as {printed})' if printed != main['code'] else ''),
                    'settings_src': f'settings as issued on {line} {rec[0]} (FRM scan p{rec[1]})'}, ''
    # not on a page on file: Tech's own calc sheet for the line (James, 23 Oct 2026, H68A244-1 DPP50KS185: "you sure we
    # don't have this one? This is just black. Double check" - FU0041KS5 had been on SE21's calc sheet since May 2026)
    for printed in sorted(main['printed'], key=lambda c: c != main['code']):
        rec = calc_recipes().get((line, printed))
        if rec:
            last, formulas = rec
            return {'code': main['code'], 'main': main, 'settings': (last, 'calc', formulas), 'printed_as': printed, 'season': seas,
                    'how': f"James's Main {main['code']}" + (f' (calc sheet has it as {printed})' if printed != main['code'] else '') + f"; settings from Tech's {line} calc sheet, last run {last}",
                    'settings_src': f"settings from Tech's {line} calc sheet (last run {last}" + (f', as {printed}' if printed != main['code'] else '') + ')'}, ''
    return {'code': main['code'], 'main': main, 'settings': None, 'printed_as': None, 'season': seas, 'how': "James's Main"}, \
        f'{main["code"]} by rule, never run on {line}: no settings on this line (no page, no calc sheet)'


QMARK = ('roll', 'void', 'corn', 'sign', 'ltl')     # qualifiers Tech writes on a page row ("(For roll material only)")
SPECIAL_ONLY = {'roll', 'void'}                       # special products: their special formula, one Main, no Secondary


def secondary_for(main, want, seas, line):
    """R9 (James, 23 Oct 2026): "When a formulation has primary and secondary, it means that both of them will need to be
    displayed, and let the production team ... decide whether we have enough of particular material to run it ... if we
    [are] running out of reclaim, then the reclaim primary will be removed and replaced with virgin resin secondary".
    The Secondary James marked for the same colour, thickness, prefix, grade and qualifiers; a qualified order with no
    Secondary of its own whose Primary runs reclaim takes the plain one (LTL wrap RU0001WB4 -> RU0022WB4). R10: never one
    with reclaim on a VOIDFORM order. A roll or VOIDFORM order has none: its special formula only (James, 24 Oct 2026, on
    H69A284-3: "This order is a roll order, so it should use a roll formula. Roll formula should only have one primary
    formula. There shouldn't be a secondary formula. It should just be one main formula." - "Roll like void form ...
    They're all order that have a special formula ... because of their unique physical properties"). None if none, or
    if several different codes would fit."""
    if want & SPECIAL_ONLY:
        return None

    def fits(m, quals):
        q = set(m['quals'])
        if 'se43' in q:
            if line != 'SE43':
                return False
            q.discard('se43')
        if 'summer' in q or 'winter' in q:
            if seas not in q:
                return False
            q -= {'summer', 'winter'}
        return q == quals
    base = set(main['quals']) - {'se43', 'summer', 'winter'}
    cands = [m for m in rules()['by_key'].get(main['key'], []) if m['level'] == 'secondary' and not m['restricted']]
    if 'void' in want:
        cands = [m for m in cands if not w_reclaim(m)]
    fit = [m for m in cands if fits(m, base)]
    if not fit and base and w_reclaim(main):
        fit = [m for m in cands if fits(m, set())]
    if len({m['code'] for m in fit}) > 1:                      # prefer the virgin run-out to a reclaim Primary
        fit = [m for m in fit if w_reclaim(m) != w_reclaim(main)] or fit
    return fit[0] if len({m['code'] for m in fit}) == 1 else None


def member_settings(line, m, want, issued, own=None):
    """The rows of one member (Primary or Secondary) on the line: from the order's own last issue, else the line's issued
    groups (the one Tech noted for the order's qualifier first), else Tech's calc sheet. A row belongs to the member when
    its code is one of the member's printed names and it feeds reclaim exactly when the member's W% has reclaim (so the
    Primary and Secondary of one code, FU0011WB5 52% and 0%, each get their own row).
    Then the old names James folded into the member with another composition ('replaces'): the line's own recipe of that
    formulation. James, 24 Oct 2026, on FU0031WB4 "ENGINEER TO SET" on SE25: "What is the issue with line 10. You should
    have primary formulation for package grade white 4 mm" - SE25 runs it as FU0021WB4 (his "replace by Main, packaging
    grade"). Only from Tech's issued pages (an old name's calc-sheet recipe can be years old), and only from a group noted
    for the order's own qualifier or a plain one. -> (rows, (kind, date, page)) or (None, None)."""
    want_r = w_reclaim(m)
    r4 = m['key'][0] == 'RU' and want_r          # an R4 Primary takes R4 rows only (r4_recipe)
    marked = {q for q in want if q in QMARK}

    def notes_q(fs):
        q = set()
        for f in fs:
            q |= {x for x in quals(f.get('note', '')) if x in QMARK}
        return q
    for names, own_recipe in ((m['printed'], False), (m.get('replaces', set()) - m['printed'], True)):
        if not names:
            continue

        def pick(fs):
            return [f for f in fs if f['formula_code'] in names and uses_reclaim(f) == want_r and (not r4 or r4_recipe(f))
                    and feeds_additives(f, m)]

        # the order's own last issue only when its notes ask for no qualifier the order lacks (James, 26 Oct 2026, on
        # RP26717-1: "order RP26717-1 is just standard graphic 40. why is it using sign blank formula?" - Tech had
        # grouped it with the sign blanks on 23 Oct; a plain order takes a plain group's settings)
        if own and notes_q(own[2]) <= marked:
            rows = pick(own[2])
            if rows:
                return rows, ('own', own[0], own[1])
        groups = sorted({id(g): g for p in names for g in _ISSUED_GROUPS.get((line, p), [])}.values(),
                        key=lambda g: g[0], reverse=True)
        if not groups:
            groups = [issued[(line, p)] for p in names if (line, p) in issued]
        # never a group noted for a qualifier the order lacks (a plain SE32 order took FU0001WBD from Tech's "(For
        # VOIDFORM order only)" group; James, 26 Oct 2026, on RP26717-1 in a sign-blank group: "why is it using sign
        # blank formula?") - then the calc sheet, else the engineer sets it
        ordered = ([g for g in groups if marked and notes_q(g[2]) & marked] + [g for g in groups if not notes_q(g[2])]
                   + ([] if own_recipe else [g for g in groups if notes_q(g[2]) <= marked]))
        for g in ordered:
            rows = pick(g[2])
            if rows:
                return rows, ('line', g[0], g[1])
        if own_recipe:
            continue
        for printed in sorted(names, key=lambda c: c != m['code']):
            rec = calc_recipes().get((line, printed))
            if rec:
                rows = pick(rec[1])
                if rows:
                    return rows, ('calc', rec[0], 'calc')
    return None, None


def formulation(line, row, day, issued, own=None):
    """R9: an order's whole formulation - James's Primary (his Main) and, where he has one, its Secondary - each with its
    rows on the line (member_settings). own: the order's own last issue on this line (date, page, formulas), if any.
    R10: on a VOIDFORM order no row that feeds reclaim is ever kept. -> (dict(members, key, how), why) or (None, why);
    members: [dict(role, code, member, rows or None, src)] Primary first."""
    key, why = derive(line, row)
    if key is None:
        return None, why
    want, seas = wanted(line, row, day)
    main, why = choose(key, want, seas, line)
    if main is None:
        if why.startswith('no Main') and not want:     # the bubble line's BF codes: a code already issued on the line
            prior = issued_for_key(line, key, issued)
            if prior:
                rec, code = prior[0]
                rows = one_row([f for f in rec[2] if f['formula_code'] == code], code)
                return {'members': [{'role': 'Primary', 'code': current_name(code), 'member': None, 'rows': rows, 'src': ('line', rec[0], rec[1])}],
                        'key': key, 'how': f'code already issued on {line} for {"/".join(key)} (no W% Master row)'}, ''
        return None, why
    pair = [('Primary', main)]
    sec = secondary_for(main, want, seas, line)
    if sec is not None:
        pair.append(('Secondary', sec))
    members = []
    for role_, m in pair:
        rows, src = member_settings(line, m, want, issued, own)
        if rows is None and m['key'][0] == 'RU' and m['key'][2] == 'KS' and w_reclaim(m):
            rows, src = r4_black_settings(line, m)          # James, 24 Oct 2026: R4 black, 98% reclaim + 2% colour
        if rows and 'void' in want:
            rows = [f for f in rows if not uses_reclaim(f)] or None
        rows = one_row(rows, m['code'])
        members.append({'role': role_, 'code': m['code'], 'member': m, 'rows': rows, 'src': src})
    how = f"James's Primary {main['code']}" + (f" + Secondary {sec['code']}" if sec else '')
    return {'members': members, 'key': key, 'how': how}, ''


def one_row(rows, code):
    """One formula row per member: the Primary once and the Secondary once (James, 26 Oct 2026, on RP26512-1, where
    Tech's SE21 page printed the same formulation twice, as FU0041WB4 and FU0031WB4: "i dont think we go with triple
    formulation now, just one primary and one secondary"). The row printed under James's own name first, else the
    first in Tech's order."""
    if not rows:
        return rows
    return [next((f for f in rows if f['formula_code'] == code), rows[0])]


if __name__ == '__main__':
    R = rules()
    print(f"{len(R['mains'])} Main/Secondary rows, {len(R['by_key'])} keys; "
          f"{sum(1 for v in R['by_key'].values() if len({m['code'] for m in v if m['level']=='main' and not m['restricted'] and not m['quals']}) > 1)} keys with several plain Mains")
    for k, v in sorted(R['by_key'].items()):
        plain = {m['code'] for m in v if m['level'] == 'main' and not m['restricted'] and not m['quals']}
        if len(plain) > 1:
            print('   ', '/'.join(k), sorted(plain))
