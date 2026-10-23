"""Rule-based formula assignment (daily/assign.py; James Kuo's rules of 23 Oct 2026, docs/FORMULA_ASSIGNMENT_RULES.md)."""
import datetime
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'daily'))
sys.path.insert(0, str(ROOT))

import assign  # noqa: E402
import config  # noqa: E402


def row(prod, mat_spec='PPP P R1R1R1', si=''):
    return {'prod_code': prod, 'mat_spec': mat_spec, 'special_instructions': si}


def test_fixed_parts_of_the_code():
    # R1: a colour other than KS / WB is graphic grade; KS / WB take the schedule's grade
    assert assign.derive('SE21', row('RPA40GS109', 'PPP A R1R1R1'))[0] == ('FU', 'A', 'GS', '4')
    assert assign.derive('SE21', row('DPP40EA12', 'PPP P R1R1R1'))[0] == ('FU', 'A', 'EA', '4')
    assert assign.derive('SE21', row('DPP40KS303', 'PPP P R1R1R1'))[0] == ('FU', '0', 'KS', '4')
    assert assign.derive('SE21', row('RPA40KS744', 'PPP A R1R1R1'))[0] == ('FU', 'A', 'KS', '4')
    # the special grades are graphic whatever the schedule grade; the bubble line is packaging whatever the colour
    assert assign.derive('SE11', row('RPP30WB1049', 'PPP P F4F4F4'))[0] == ('FR', 'A', 'WB', '3')
    assert assign.derive('SE31', row('SPA40WB767', 'PPP A OPOPOP'))[0] == ('FX', 'A', 'WB', '4')
    assert assign.derive('SE61', row('RBP33EB40', 'BBB P R6R6R6'))[0] == ('BF', '0', 'EB', '3')
    # R3: the Spec decides the prefix; R4R4R4 is reclaim
    assert assign.derive('SE21', row('RPP40KS1372', 'PPP P R4R4R4'))[0] == ('RU', '0', 'KS', '4')
    # thickness: 6.3 mm runs a ..6 code; 10 mm is A, 13 mm is D
    assert assign.derive('SE21', row('RPP63KS1'))[0][3] == '6'
    assert assign.derive('SE22', row('DPPA0WB268'))[0][3] == 'A'
    assert assign.derive('SE32', row('RPPD0WB165'))[0][3] == 'D'
    # not decided: a code that breaks the product rule, a spec without a rule
    assert assign.derive('SE21', row('RPAQWRAN72'))[0] is None
    assert assign.derive('SE21', row('RPP40WB1', 'PPP P Z9Z9Z9'))[0] is None


def test_print_james_names_not_old_codes():
    """James, 23 Oct 2026: "Don't use old formula code in the print out"."""
    assert assign.current_name('FU0014BA4') == 'FUA014BA4'          # renamed
    assert assign.current_name('FH0012WB4') == 'FHA012WB4'          # renamed (old UV letter)
    assert assign.current_name('RO000WB4') == 'RU0000WB4'
    assert assign.current_name('FUA152WB4') == 'FUA152WB4'          # still a current name (winter / sign blank): unchanged
    assert assign.current_name('FU0021WB4') == 'FU0021WB4'          # a Main under its own name
    assert assign.current_name('FH0001NSA') == 'FH0001NSA'          # points to two Mains: left for James


def test_season_rule():
    assert assign.season(datetime.date(2026, 10, 31)) == 'summer'
    assert assign.season(datetime.date(2026, 11, 1)) == 'winter'
    assert assign.season(datetime.date(2027, 3, 31)) == 'winter'
    assert assign.season(datetime.date(2027, 4, 1)) == 'summer'


def test_james_main_rows_decide():
    issued = {}
    # WB 4 mm graphic: summer and winter Mains (R5)
    p, _ = assign.propose('SE31', row('RPA40WB3051', 'PPP A R1R1R1'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FUA151WB4' and p['settings'] is None
    p, _ = assign.propose('SE31', row('RPA40WB3051', 'PPP A R1R1R1'), datetime.date(2026, 11, 2), issued)
    assert p['code'] == 'FUA152WB4'
    # VOIDFORM picks the VOIDFORM Main; SE43's own Main outranks the general one there
    p, _ = assign.propose('SE25', row('DPP40WB1673', 'PPP P R1R1R1', 'VOIDFORM, PLEASE WATCH WEIGHT'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FU0021WB4'
    p, _ = assign.propose('SE43', row('DPP40WB1673', 'PPP P R1R1R1', 'VOIDFORM'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FU0151WB4'
    # R7: an SPA product or an order sent to the slitter takes the sign-blank Main; a colour with no sign-blank Main
    # takes its plain Main (SPA40WM8 -> FUA151WM4, as Tech prints)
    p, _ = assign.propose('SE13', row('SPA40WB958', 'PPP A R1R1R1'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FUA152WB4'
    p, _ = assign.propose('SE13', row('RPA40WB3502', 'PPP A R1R1R1', 'SEND TO SLITTER. MARK EDGE'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FUA152WB4'
    p, _ = assign.propose('SE31', row('SPA40WM8', 'PPP A R1R1R1', 'SEND TO SLITTER'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FUA151WM4'
    # a key with two plain Mains is not decided (KS 3 mm packaging: James to say)
    p, why = assign.propose('SE11', row('RPP30KS948', 'PPP P R1R1R1'), datetime.date(2026, 10, 23), issued)
    assert p is None and why.startswith('several Mains')
    # a customer-specific Main is never proposed by rule
    assert all(not m['restricted'] or m['code'] not in ('FU0001BLA',) for m in assign.rules()['mains'] if m['code'] == 'FU0001BLA' and not m['restricted'])


def test_settings_come_from_the_line_and_the_bubble_line_falls_back():
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        if d['packet_date'] <= '2026-10-07':
            packets[d['packet_date']] = d
    issued = assign.issued_on_line(packets)
    # James's Main FUA151WB4 (summer) was printed FUA152WB4 on SE31: the settings come under that name
    p, _ = assign.propose('SE31', row('RPA40WB3051', 'PPP A R1R1R1'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FUA151WB4' and p['printed_as'] == 'FUA152WB4' and p['settings'][0] == '2026-10-07'
    # SE61: no W% row for BF0000EB3, but Tech issued it on the line -> taken from the line
    p, _ = assign.propose('SE61', row('RBP33EB40', 'BBB P R6R6R6', 'Bradford'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'BF0000EB3' and p['how'].startswith('code already issued on SE61')


def test_backtest_against_tech_issues():
    """As each morning before Tech issued: for the orders the issue history could not answer, the rule names the
    formulation Tech issued that day in at least 95 of the ~145 cases, and a different one in at most 35. "Different"
    includes Tech printing a code James replaced by another composition (his cleanup of 23 Oct: FU0041WB4 -> FU0031WB4,
    FU0011WB5 -> FU0051WB5 ...): the rule follows James's Main there, by design."""
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        packets[d['packet_date']] = d
    tot = Counter()
    for day in sorted(d for d in packets if packets[d]['frm']):
        before = {d: p for d, p in packets.items() if d < day}
        issued = assign.issued_on_line(before)
        seen = {(pg['line_code'], o) for d in before for pg in before[d]['frm'] for g in pg['groups'] for o in g['orders']}
        tech = {(pg['line_code'], o): [f['formula_code'] for f in g['formulas']] for pg in packets[day]['frm'] for g in pg['groups'] for o in g['orders']}
        for pg in packets[day]['ext']:
            for r in pg['rows']:
                k = (pg['line'], r['order'])
                if k in seen or k not in tech:
                    continue
                p, _ = assign.propose(pg['line'], r, datetime.date.fromisoformat(day), issued)
                if p is None:
                    tot['none'] += 1
                    continue
                names = (p['main']['printed'] if p['main'] else set()) | {p['code']}
                tot['same' if any(c in names for c in tech[k]) else 'different'] += 1
    assert tot['same'] >= 95 and tot['different'] <= 35, dict(tot)


def test_draft_prints_james_names(tmp_path):
    """29 Sep, every order as last issued: the codes print under James's names (FU0001RF6 -> FUA001RF6; FUA152WB4 on an
    auger line in September -> FUA151WB4, his summer name), the settings untouched; the printed name stays in Source."""
    out = tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PKT_DATE='2026-09-29')
    r = subprocess.run([sys.executable, str(ROOT / 'daily' / 'resolve.py')], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    from openpyxl import load_workbook
    rows = list(load_workbook(out / 'FRM Draft 2026-09-29.xlsx', read_only=True)['Draft'].iter_rows(values_only=True))
    h = list(rows[0])
    got = {}
    for x in rows[1:]:
        d = dict(zip(h, x))
        got.setdefault(d['Order'], set()).add((d['Formula Code'], 'printed as' in str(d['Source'])))
    assert got['H67A164-2'] == {('FUA001RF6', True)}
    assert got['RP26604-1'] == {('FUA152WB4', False)}        # an SPA sign blank (R7): FUA152WB4 is its Main, no rename
    assert got['H67A164-1'] == {('FU0070KS6', False)}


def test_word_marks_rule_rows(tmp_path):
    out = tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PKT_DATE='2026-09-28', HISTORY_BEFORE='2026-09-28')
    for script in ('resolve.py', 'render_frm.py'):
        r = subprocess.run([sys.executable, str(ROOT / 'daily' / script)], env=env, capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0, r.stdout + r.stderr
    from docx import Document
    doc = Document(out / 'FRM Formulation 2026-09-28.docx')
    cells = [c.text for t in doc.tables for row in t.rows for c in row.cells]
    assert any(c.startswith('PROPOSED BY RULE') for c in cells)
    assert 'PROPOSED BY RULE' in doc.sections[0].footer.paragraphs[0].text
    for row in (row for t in doc.tables for row in t.rows):           # RP26928-1: FUA060WBA by rule, marked, never silent
        if row.cells[0].text.startswith('RP26928-1'):
            assert any('FUA060WBA' in c.text for c in row.cells) and any('PROPOSED BY RULE' in c.text for c in row.cells)
