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
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import product_code as pc  # noqa: E402

W_MASTER = config.ROOT / 'data' / 'w_master' / 'W Master Formulation draft (version 1) - James notes 2026-10-23.xlsx'

PREFIX = {'R1R1R1': 'FU', 'R3R3R3': 'FU', 'R2R2R2': 'FU', 'R4R4R4': 'RU', 'OPOPOP': 'FX', 'S1S1S1': 'FS',
          'A1A1A1': 'FA', 'U1U1U1': 'FE', 'F1F1F1': 'FR', 'F4F4F4': 'FR', 'R6R6R6': 'BF', 'RDRDRD': 'BF', 'RMR6R6': 'BF'}
OLD_PREFIX = {'FE': ('FH',)}            # James, 23 Oct 2026: "Extra UV is FE"; Tech's older pages print FH for it
SPECIAL = {'OPOPOP', 'S1S1S1', 'A1A1A1', 'U1U1U1', 'F1F1F1', 'F4F4F4'}      # always graphic grade 'A'
BLACK_WHITE = {'KS', 'WB'}
CODE_RX = re.compile(r'\b([A-Z]{2}[A-Z0-9]{3,5}[A-Z]{2,3}[0-9A-Z])\b')
RENAME_RX = re.compile(r'(?:change (?:name )?to|replace name with|change)\s+([A-Z]{2}[A-Z0-9]{3,5}[A-Z]{2,3}[0-9A-Z])', re.I)
W_COLS = ['Virgin PP %', 'Homo PP (F1203K) %', 'Reclaim %', 'Talc %', 'CaCO3 %', 'Colour MB %', 'Vistamaxx %',
          'Additive %', 'Foam %', 'HDPE %', 'Skin %', 'Other %']
# words in James's notes that make a Main apply to some orders only (the schedule or the line says which)
QUALIFIERS = {'void': ('void',), 'corn': ('corn',), 'sign': ('sign blank', 'spa'), 'summer': ('summer',),
              'winter': ('winter',), 'se43': ('se43',), '6.3': ('6.3',), '4.6': ('4.6',)}
# words that mark a Main for a customer or a product kind the schedule does not name: never proposed by rule
RESTRICTED = ('orbis', 'carter', 'tzu', 'vistech', 'nissan', 'roll', 'ltl', 'batten', 'cabbage', 'hdpe', 'pe f', 'pe part',
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
    R = [dict(zip(rows[0], r)) for r in rows[1:] if r[0]]
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
    # printed names: a row "replace by/with X" (or by description) carries the settings of its Main under the old name
    for r in R:
        if level(r['Notes']) != 'replace':
            continue
        note = r['Notes'] or ''
        named = [c for c in CODE_RX.findall(note) if c != r['Formula Code']]
        want = quals(note)
        target = None
        if named:
            target = next((m for m in mains if m['code'] == named[0] or named[0] in m['printed']), None)
        if target is None:                     # by description, or its own code: the Main of the same colour/thk with the same words
            lv = 'secondary' if 'secondary' in note.lower() else 'main'
            own = final_code(r)
            gch = 'A' if 'graphic' in note.lower() else ('0' if 'pack' in note.lower() else (own[2] if len(own) == 9 else None))
            cands = [m for m in mains if m['level'] == lv and m['key'][2] == (r['Colour'] or '')[:2]
                     and r['Thk (mm)'] is not None and m['key'][3] == thk_char(float(r['Thk (mm)'])) and m['quals'] == want
                     and m['key'][0] == canon_prefix(own[:2]) and (gch is None or m['key'][1] == gch)]
            if len(cands) == 1:
                target = cands[0]
        if target is not None:
            target['printed'].add(r['Formula Code'])
    _RULES = {'mains': mains, 'by_key': by_key}
    return _RULES


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
    q = set()
    if 'VOIDFORM' in si or 'VOID FORM' in si:
        q.add('void')
    if 'CORN' in si:
        q.add('corn')
    if 'SIGN BLANK' in si or 'SIGNBLANK' in si:
        q.add('sign')
    mm = pc.thickness_mm(row.get('prod_code') or '')
    if mm is not None and abs(mm - 6.3) < 1e-6:
        q.add('6.3')
    if mm is not None and abs(mm - 4.6) < 1e-6:
        q.add('4.6')
    return q, season(day)


def choose(key, want, seas, line):
    """The Main for a key and what the order asks for. -> (main, why) with main None when none or several fit."""
    cands = [m for m in rules()['by_key'].get(key, []) if m['level'] == 'main' and not m['restricted']]
    if not cands:
        return None, 'no Main in the W% Master for ' + '/'.join(key)
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


def issued_on_line(packets):
    """(line, printed code) -> (date, scan page, [formula dicts of the group]) from every Tech issue on file, latest wins."""
    out = {}
    for date in sorted(packets):
        for pg in packets[date]['frm']:
            for g in pg['groups']:
                for f in g['formulas']:
                    out[(pg['line_code'], f['formula_code'])] = (date, pg['scan_page'], g['formulas'])
    return out


def issued_for_key(line, key, issued):
    """Codes Tech has issued on the line whose fixed parts (R1, R3, colour, thickness) are the key: the W% Master has
    no row for some of them (the bubble line's BF0000EB3 / EB5 are co-extrusion, 'Not computed'). Latest issue first."""
    hits = [(rec, code) for (ln, code), rec in issued.items()
            if ln == line and len(code) == 9 and (canon_prefix(code[:2]) + code[2], code[6:8], code[8]) == (key[0] + key[1], key[2], key[3])]
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
                return {'code': code, 'main': None, 'settings': rec, 'printed_as': code, 'season': seas,
                        'how': f'code already issued on {line} for {"/".join(key)} (no W% Master row)'}, ''
        return None, why
    for printed in sorted(main['printed'], key=lambda c: c != main['code']):   # James's name first, then old names
        rec = issued.get((line, printed))
        if rec:
            # only this formulation's rows of the issued group (a group can hold another order's primary, e.g. the
            # VOIDFORM run-out FU0022WB3 printed under a FU0042WB3 order); its own run-out partner comes with it
            formulas = [f for f in rec[2] if f['formula_code'] in main['printed']]
            if not formulas:
                continue
            return {'code': main['code'], 'main': main, 'settings': (rec[0], rec[1], formulas), 'printed_as': printed, 'season': seas,
                    'how': f"James's Main {main['code']}" + (f' (Tech printed it as {printed})' if printed != main['code'] else '')}, ''
    return {'code': main['code'], 'main': main, 'settings': None, 'printed_as': None, 'season': seas, 'how': "James's Main"}, \
        f'{main["code"]} by rule, never run on {line}: no settings on this line yet'


if __name__ == '__main__':
    R = rules()
    print(f"{len(R['mains'])} Main/Secondary rows, {len(R['by_key'])} keys; "
          f"{sum(1 for v in R['by_key'].values() if len({m['code'] for m in v if m['level']=='main' and not m['restricted'] and not m['quals']}) > 1)} keys with several plain Mains")
    for k, v in sorted(R['by_key'].items()):
        plain = {m['code'] for m in v if m['level'] == 'main' and not m['restricted'] and not m['quals']}
        if len(plain) > 1:
            print('   ', '/'.join(k), sorted(plain))
