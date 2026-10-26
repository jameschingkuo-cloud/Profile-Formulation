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


def test_issued_name_follows_the_page_note():
    """RP26717-1 (RPA40WB3051, SE13): Tech grouped it with the sign blanks, "(For sign blank orders only)" FUA152WB4.
    James, 26 Oct 2026: "order RP26717-1 is just standard graphic 40. why is it using sign blank formula?" The order's
    own qualifiers decide: FUA151WB4 whatever group Tech put it in."""
    r = row('RPA40WB3051', 'PPP A R1R1R1', 'RUN WITH NEXT')
    assert assign.wanted('SE13', r, datetime.date(2026, 10, 23))[0] == set()
    sign_group = [{'formula_code': 'FUA152WB4', 'note': '(For sign blank orders only)', 'feeders': {}}]
    assert assign.names_for_issued('SE13', r, datetime.date(2026, 10, 23), sign_group) == {'FUA152WB4': 'FUA151WB4'}
    plain_group = [{'formula_code': 'FUA152WB4', 'note': '', 'feeders': {}}]
    assert assign.names_for_issued('SE13', r, datetime.date(2026, 10, 23), plain_group) == {'FUA152WB4': 'FUA151WB4'}


def test_season_rule():
    assert assign.season(datetime.date(2026, 10, 31)) == 'summer'
    assert assign.season(datetime.date(2026, 11, 1)) == 'winter'
    assert assign.season(datetime.date(2027, 3, 31)) == 'winter'
    assert assign.season(datetime.date(2027, 4, 1)) == 'summer'


def test_james_main_rows_decide():
    issued = {}
    # WB 4 mm graphic: summer and winter Mains (R5)
    p, _ = assign.propose('SE31', row('RPA40WB3051', 'PPP A R1R1R1'), datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FUA151WB4' and (p['settings'] is None or p['settings'][1] == 'calc')   # no page: the calc sheet, if built
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
    # a key with two plain Mains is not decided (KS 6 mm packaging: James to say; KS 3 mm he settled on 26 Oct)
    p, why = assign.propose('SE11', row('RPP60KS100', 'PPP P R1R1R1'), datetime.date(2026, 10, 23), issued)
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


def test_roll_and_ltl_orders():
    """James, 23 Oct 2026, H69A284-3 (RPP40WB890, SE25, R2R2R2 "ROLLS SAME AS ABOVE"): "we don't have roll formulation??"
    A roll order takes his "Main roll" FU0021WB4, with the SE25 settings Tech issued for the rolls on 23 Sep (and the
    run-out row Tech prints with it); an LTL wrap order takes RU0001WB4 "Main, R2 LTL wrap"."""
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        if d['packet_date'] <= '2026-10-07':
            packets[d['packet_date']] = d
    issued = assign.issued_on_line(packets)
    roll = row('RPP40WB890', 'PPP P R2R2R2', 'ROLLS SAME AS ABOVE')
    assert 'roll' in assign.wanted('SE25', roll, datetime.date(2026, 10, 23))[0]
    p, why = assign.propose('SE25', roll, datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'FU0021WB4' and p['settings'] and p['settings'][1] != 'calc', why
    # James, 24 Oct 2026, on H69A284-3: "Roll formula should only have one primary formula. There shouldn't be a
    # secondary formula" - the roll row only, not Tech's run-out row printed with it
    assert [f['formula_code'] for f in p['settings'][2]] == ['FU0021WB4']
    assert 'roll material' in p['settings'][2][0]['note'].lower()
    fm, why = assign.formulation('SE25', roll, datetime.date(2026, 10, 23), issued)
    assert [(m['role'], m['code']) for m in fm['members']] == [('Primary', 'FU0021WB4')], why
    assert [f['formula_code'] for f in fm['members'][0]['rows']] == ['FU0021WB4']
    ltl = row('RPP40WB1186', 'PPP P R2R2R2', '1 Ticket per pallet & move to repacking area.  LTL MATERIAL')
    assert assign.derive('SE25', ltl)[0] == ('RU', '0', 'WB', '4')
    p, why = assign.propose('SE25', ltl, datetime.date(2026, 10, 23), issued)
    assert p['code'] == 'RU0001WB4', why


def test_settings_from_tech_calc_sheet():
    """James, 23 Oct 2026, H68A244-1 (DPP50KS185, SE21): "you sure we don't have this one? This is just black. Double
    check". No FRM page on file carries a KS 5 mm code on SE21, but Tech's SE21 calc sheet has FU0041KS5 (last run May
    2026): the rule names FU0041KS5 and takes those settings, worded as the line's latest page prints each hopper."""
    if not assign.CALC_LIB.exists():
        import pytest
        pytest.skip('Formulation Calc Library not built on this PC')
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        if d['packet_date'] <= '2026-10-07':
            packets[d['packet_date']] = d
    assign.set_pages(packets)
    assign._CALC = None
    p, why = assign.propose('SE21', row('DPP50KS185', 'PPP P R1R1R1', 'Send to Bobst'), datetime.date(2026, 10, 23), assign.issued_on_line(packets))
    assert p['code'] == 'FU0041KS5' and p['settings'] and p['settings'][1] == 'calc'
    feeders = p['settings'][2][0]['feeders']
    assert set(feeders) == {f'Hopper {i}' for i in range(1, 6)}
    assert feeders['Hopper 3']['set'] == '74' and 'Reclaim' in feeders['Hopper 3']['material']
    assert 'calc sheet' in p['how'] and p['settings_src'].startswith("settings from Tech's SE21 calc sheet")


def test_backtest_against_tech_issues():
    """As each morning before Tech issued: for the orders the issue history could not answer, the rule names the
    formulation Tech issued that day in at least 70% of the cases and a different one in at most 24% (23 Sep - 7 Oct:
    ~145 cases; with Tech's 8-23 Oct pages, 26 Oct 2026: 249 cases, 75% / 18%). "Different"
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
    n = sum(tot.values())
    assert n >= 140 and tot['same'] >= 0.70 * n and tot['different'] <= 0.24 * n, dict(tot)


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


def test_rules_first_25_sep(tmp_path):
    """James, 23 Oct 2026: "Moving forward ... we use logic base formulation process. Remove old logic and apply new" and
    "No history process. If logic don't work, ask engineering for help". 25 Sep as that morning, rules first: the two
    new orders get the codes Tech issued (FU0021WB4, FXA020WB4; FXA020WB4 with its settings to be set, as SE31 had never
    run it); an Exception is only an order the rules cannot decide; nothing is printed "as last issued" by itself."""
    out = tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PKT_DATE='2026-09-25',
               RUN_DATE='2026-09-28', HISTORY_BEFORE='2026-09-25')
    r = subprocess.run([sys.executable, str(ROOT / 'daily' / 'resolve.py')], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    from openpyxl import load_workbook
    wb = load_workbook(out / 'FRM Draft 2026-09-25.xlsx', read_only=True)
    rows = list(wb['Draft'].iter_rows(values_only=True))
    h = list(rows[0])
    hows = {}
    for x in rows[1:]:
        d = dict(zip(h, x))
        hows.setdefault(d['Order'], set()).add(str(d['How Resolved']).split(' (')[0])
    assert all(v <= {'By rule', 'Proposed by rule', 'Product to Formula'} for v in hows.values()), hows
    by_rule = {row[1] for row in wb['By Rule'].iter_rows(min_row=2, values_only=True)}
    assert 'H67A120-1' in by_rule
    # FXA020WB4 had never run on SE31 before 25 Sep: the rule names it and prints it, its settings go to the engineer
    to_set = {(s[1], s[3], s[4]) for s in wb['Settings To Set'].iter_rows(min_row=2, values_only=True)}
    assert ('H68A153-1', 'FXA020WB4', 'Primary') in to_set
    for e in wb['Exceptions'].iter_rows(min_row=2, values_only=True):
        assert str(e[8]).startswith('Rules cannot decide: '), e


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
    assert any('PROPOSED BY RULE' in c for c in cells)
    assert 'PROPOSED BY RULE' in doc.sections[0].footer.paragraphs[0].text
    # RP26928-1 shares its cell with RP26311-1, the same formulation (James, 26 Oct 2026: "since these two are the same
    # formula, they should share the same cell"); the rule mark goes under the order
    rp = [row for t in doc.tables for row in t.rows if 'RP26928-1' in row.cells[0].text]
    assert rp and 'RP26311-1' in rp[0].cells[0].text
    for row in rp:                                                    # RP26928-1: FUA060WBA by rule, marked, never silent
        assert any('FUA060WBA' in c.text for c in row.cells) and any('PROPOSED BY RULE' in c.text for c in row.cells)
    # R9: the virgin Secondary prints with the Primary, for production to switch to if reclaim runs out
    assert any('If reclaim runs out' in row.cells[1].text and row.cells[-1].text.startswith('Secondary') for row in rp)


def test_primary_and_secondary_both_shown():
    """R9 (James, 23 Oct 2026): "When a formulation has primary and secondary, it means that both of them will need to be
    displayed, and let the production team will then decide whether we have enough of particular material to run it or
    not". RP26928-1 (RPAA0WB318, SE22, 28 Sep): the FUA060WBA Primary with Tech's two reclaim rows (run first, next) and
    its virgin Secondary, which Tech printed FUA010WBA "in case PP WB Reclaim is run out" - both under James's name."""
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        if d['packet_date'] < '2026-09-28':
            packets[d['packet_date']] = d
    issued = assign.issued_on_line(packets)
    fm, why = assign.formulation('SE22', row('RPAA0WB318', 'PPP A R1R1R1'), datetime.date(2026, 9, 28), issued)
    assert [(m['role'], m['code']) for m in fm['members']] == [('Primary', 'FUA060WBA'), ('Secondary', 'FUA060WBA')], why
    prim, sec = fm['members']
    assert len(prim['rows']) == 2 and all(assign.uses_reclaim(f) for f in prim['rows'])
    assert [f['formula_code'] for f in sec['rows']] == ['FUA010WBA'] and not assign.uses_reclaim(sec['rows'][0])
    assert fm['how'] == "James's Primary FUA060WBA + Secondary FUA060WBA"


def test_void_form_never_reclaim():
    """R10 (James, 23 Oct 2026): "void form should not use any reclaim" - "The reclaim calcium is not stable ... It makes it
    very difficult to control the weight when we're running with reclaim". A VOIDFORM order never gets a Primary or a
    Secondary with reclaim in James's W%, nor a row that feeds reclaim; the old void formulas with reclaim (FU0011WB5
    "secondary Voidform" 35%, Tech's FU0011WB5 / FU0061WBD void groups) are never used."""
    for key in assign.rules()['by_key']:
        for line in ('SE25', 'SE43'):
            for seas in ('summer', 'winter'):
                main, _ = assign.choose(key, {'void'}, seas, line)
                if main:
                    assert not assign.w_reclaim(main), (key, main['code'])
                    sec = assign.secondary_for(main, {'void'}, seas, line)
                    assert sec is None or not assign.w_reclaim(sec), (key, sec['code'])
    main, _ = assign.choose(('FU', '0', 'WB', '5'), {'void'}, 'summer', 'SE25')     # WB 5 mm: FU0051WB5, never FU0011WB5
    assert main['code'] == 'FU0051WB5' and assign.secondary_for(main, {'void'}, 'summer', 'SE25') is None
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        packets[d['packet_date']] = d
    day = datetime.date(2026, 10, 23)
    issued = assign.issued_on_line({d: p for d, p in packets.items() if d < '2026-10-23'})
    void = []
    for pg in packets['2026-10-23']['ext']:
        for r in pg['rows']:
            if 'void' in assign.wanted(pg['line'], r, day)[0]:
                fm, why = assign.formulation(pg['line'], r, day, issued)
                void.append((r['order'], [m['code'] for m in fm['members']]))
                for m in fm['members']:
                    assert not assign.w_reclaim(m['member']), (r['order'], m['code'])
                    assert not any(assign.uses_reclaim(f) for f in m['rows'] or []), (r['order'], m['code'])
    assert dict(void) == {'H6AA197-1': ['FU0022WB3'], 'H68A091-1': ['FU0021WB4'], 'H68A090-1': ['FU0051WB5'],
                          'H64A244-1': ['FU0051WB5'], 'H68A053-1': ['FU0001WBD'], 'H6AA097-1': ['FU0001WBD']}
    # nor from the order's own last issue: a row feeding reclaim is dropped, the settings go to the engineer
    own = ('2026-10-20', 1, [{'formula_code': 'FU0051WB5', 'note': '', 'feeders': {
        'Hopper 1': {'material': 'PP Virgin-silo 4 (6502A)', 'set': '60'}, 'Hopper 3': {'material': 'PP WB Reclaim', 'set': '30'}}}])
    fm, _ = assign.formulation('SE25', row('DPP50WB308', 'PPP P R1R1R1', 'VOIDFORM, PLEASE WATCH WEIGHT'), day, issued, own=own)
    assert [(m['code'], m['rows']) for m in fm['members']] == [('FU0051WB5', None)]


def test_primary_first_even_without_settings():
    """RP26A15-1 (23 Oct, SE21): James's Primary FUA032KS4 has no settings on SE21 yet, its Secondary FUA152KS4 has. The
    Primary still comes first, as one "ENGINEER TO SET" row, then the Secondary, printed for when reclaim runs out."""
    import resolve
    import render_frm
    sec = [{'formula_code': 'FUA152KS4', 'note': '', 'feeders': {'Hopper 1': {'material': 'PP Virgin-silo 3 (F6502A)', 'set': '53'}}}]
    fm = {'how': "James's Primary FUA032KS4 + Secondary FUA152KS4", 'members': [
        {'role': 'Primary', 'code': 'FUA032KS4', 'member': {'code': 'FUA032KS4'}, 'rows': None, 'src': None},
        {'role': 'Secondary', 'code': 'FUA152KS4', 'member': {'code': 'FUA152KS4'}, 'rows': sec, 'src': ('line', '2026-10-07', 12)}]}
    rows, marked, missing = resolve.rule_rows('SE21', 'RP26A15-1', 'RPA40KS744', fm)
    assert [(r[3], r[4], r[14]) for r in rows] == [('FUA032KS4', 'Primary', 1), ('FUA152KS4', 'Secondary', 2)]
    assert rows[0][15].startswith('ENGINEER TO SET') and [m['code'] for m in missing] == ['FUA032KS4'] and marked == '2026-10-07'
    forms = [{'note': rows[0][15], 'feeders': {}}, {'note': rows[1][15], 'feeders': {('', 'Hopper 1'): ('PP Virgin', '53', None)}}]
    assert [render_frm.when_label(forms, i) for i in range(2)] == ['Run first', 'If reclaim runs out']


def test_line_own_recipe_of_a_folded_formulation():
    """James, 24 Oct 2026, on H69A040-1 (CPP40WB320, SE25: FU0031WB4 "ENGINEER TO SET"): "What is the issue with line 10.
    You should have primary formulation for package grade white 4 mm". SE25 runs the packaging grade as FU0021WB4 (36%
    reclaim; James folded it into his Main FU0031WB4, 20%): those issued rows are SE25's own recipe of the Main, the
    Primary, with the run-out row as its Secondary FU0014WB4. An old name's calc-sheet recipe is not taken (SE21's
    FUA021KS5, folded into FUA031KS5, last run Nov 2025)."""
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        packets[d['packet_date']] = d
    day = datetime.date(2026, 10, 23)
    issued = assign.issued_on_line({d: p for d, p in packets.items() if d < '2026-10-23'})
    sched = {r['order']: (pg['line'], r) for pg in packets['2026-10-23']['ext'] for r in pg['rows']}
    fm, why = assign.formulation(*sched['H69A040-1'], day, issued)
    prim, sec = fm['members']
    assert (prim['code'], sec['code']) == ('FU0031WB4', 'FU0014WB4'), why
    assert [f['formula_code'] for f in prim['rows']] == ['FU0021WB4'] and assign.uses_reclaim(prim['rows'][0])
    assert prim['src'][0] == 'line' and prim['src'][1] >= '2026-09-30'      # SE25's latest issue of FU0021WB4
    assert [f['formula_code'] for f in sec['rows']] == ['FU0021WB4'] and not assign.uses_reclaim(sec['rows'][0])
    fm, _ = assign.formulation(*sched['H6AA017-1'], day, issued)
    assert fm['members'][0]['code'] == 'FUA031KS5' and fm['members'][0]['rows'] is None


def test_r4_black():
    """James, 24 Oct 2026, on H6AA173-1 (RPP50KS2219, SE21, PPP P R4R4R4: RU0000KS5 never run there): "remember the auger
    setting is applied universally ... look at other auger setting with similar products such as black productions and
    then put them together. And besides, if it's a R4 black production, it should run about 98% black reclaim and 2% black
    color dye or master batch". Tech's R4 black on SE21 (RU0000KS4, 23-25 Sep): Mix Reclaim on hopper 3 at 99, KS colour
    on hopper 4 at 10. The 5 mm order keeps hopper 3 at 99 and sets hopper 4 for 98/2 (slopes 87.2 and 16.1 g/min per
    unit): 11, marked CALCULATED. The R4 black 4 mm order H6AA173-2 takes Tech's R4 rows, never the packaging recipe
    printed under the old name FU0041KS4 (virgin 32, mix reclaim 70, talc, CaCO3)."""
    if not assign.CALC_LIB.exists():
        import pytest
        pytest.skip('Formulation Calc Library not built on this PC')
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        packets[d['packet_date']] = d
    day = datetime.date(2026, 10, 23)
    before = {d: p for d, p in packets.items() if d < '2026-10-23'}
    issued = assign.issued_on_line(before)
    assign.set_pages(before)
    sched = {r['order']: (pg['line'], r) for pg in packets['2026-10-23']['ext'] for r in pg['rows']}
    fm, why = assign.formulation(*sched['H6AA173-1'], day, issued)
    (x,) = fm['members']
    assert x['code'] == 'RU0000KS5' and x['src'][0] == 'calcd', why
    fed = {c: v['set'] for c, v in x['rows'][0]['feeders'].items() if v.get('set')}
    assert fed == {'Hopper 3': '99', 'Hopper 4': '11'}
    k_r, k_c = x['src'][2]['slopes']
    assert abs(99 * k_r / (99 * k_r + 11 * k_c) - 0.98) < 0.002
    fm, _ = assign.formulation(*sched['H6AA173-2'], day, issued)
    (x,) = fm['members']
    assert x['code'] == 'RU0000KS4' and all(assign.r4_recipe(f) for f in x['rows'])
    assert {c: v['set'] for c, v in x['rows'][0]['feeders'].items() if v.get('set')} == {'Hopper 3': '99', 'Hopper 4': '10'}
    packaging = {'formula_code': 'FU0041KS4', 'note': '', 'feeders': {'Hopper 1': {'material': 'PP Virgin-silo 3 (F6502A)', 'set': '32'},
                 'Hopper 3': {'material': 'PP Mix Reclaim', 'set': '70'}, 'Hopper 4': {'material': 'KS MB-CR401K', 'set': '35'}}}
    assert not assign.r4_recipe(packaging)


def test_u1_natural_10mm_is_fea():
    """James, 26 Oct 2026: "U1 is for FEA". DPPA0NS75 (spec U1U1U1, NS 10 mm) runs FEA001NSA (UV-N26257A 1.4%, anti-static
    1.8%), not FHA001NSA (UV-N26177A 4.8%, anti-static) - both printed FH0001NSA by Tech. FEA001NSA's settings are only
    a recipe with its UV-N26257A: SE21's (Feb 2023); SE22's FH0001NSA recipe is the N26177A one, so on SE22 they are
    still to be set."""
    if not assign.CALC_LIB.exists():
        import pytest
        pytest.skip('Formulation Calc Library not built on this PC')
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        packets[d['packet_date']] = d
    issued = assign.issued_on_line(packets)
    assign.set_pages(packets)
    r = row('DPPA0NS75', 'PPP P U1U1U1', 'Send to Rotary. Mark lead & make sure of pc count.')
    fm, why = assign.formulation('SE22', r, datetime.date(2026, 10, 26), issued)
    assert [(m['code'], m['rows']) for m in fm['members']] == [('FEA001NSA', None)], why
    fm, why = assign.formulation('SE21', r, datetime.date(2026, 10, 26), issued)
    (x,) = fm['members']
    assert x['code'] == 'FEA001NSA' and x['src'][0] == 'calc'
    assert any('N26257A' in v['material'] for v in x['rows'][0]['feeders'].values() if v.get('set'))


def test_ks_3mm_packaging_is_fu0051ks3():
    """James, 26 Oct 2026, on the 2016 FU0032KS3 "Main, Packaging grade" row: "obsolete this one" (assign.LATER_NOTES; his
    23 Oct file stays as received). Black 3 mm packaging (RPP30KS948, R1R1R1) then has one Main, FU0051KS3: SE11 takes its
    issue of 12-13 Oct (H6AA077-11), SE43 keeps its own FU0151KS3; FU0032KS3 Vistech stays a customer Main, never proposed."""
    R = assign.rules()
    plain = {m['code'] for m in R['by_key'][('FU', '0', 'KS', '3')] if not m['quals'] and not m['restricted']}
    assert plain == {'FU0051KS3'}
    assert any(m['code'] == 'FU0032KS3' and m['restricted'] for m in R['mains'])
    if not assign.CALC_LIB.exists():
        import pytest
        pytest.skip('Formulation Calc Library not built on this PC')
    packets = {}
    for pth in config.packet_files():
        d = json.loads(pth.read_text(encoding='utf-8'))
        packets[d['packet_date']] = d
    issued = assign.issued_on_line(packets)
    assign.set_pages(packets)
    r = row('RPP30KS948', 'PPP P R1R1R1', '')
    fm, why = assign.formulation('SE11', r, datetime.date(2026, 10, 26), issued)
    (x,) = fm['members']
    assert x['code'] == 'FU0051KS3' and x['src'][:2] == ('line', '2026-10-13'), why     # Tech ran it on SE11, 12-13 Oct
    fm, why = assign.formulation('SE43', r, datetime.date(2026, 10, 26), issued)
    assert [m['code'] for m in fm['members']] == ['FU0151KS3'], why


def test_draft_vs_tech_23_oct(tmp_path):
    """How close (James Kuo, 26 Oct 2026: "do a comparison see how close are we"): the 23 Oct draft as that morning
    against Tech's 23 Oct pages - 91 of 98 orders the same formulation, 78 also the same settings; Tech's old names
    and spellings (FUA152WB4 / FUA151WB4, 6502A / F6502A, '-' / '–') are not differences (daily/compare_tech.py)."""
    import shutil
    import compare_tech
    calc = config.OUTPUT_DIR / 'Formulation Calc Library.xlsx'
    if calc.exists():
        shutil.copy2(calc, tmp_path / calc.name)
    env = dict(os.environ, PYTHONUTF8='1', PKT_DATE='2026-10-23', HISTORY_BEFORE='2026-10-23', OUTPUT_DIR=str(tmp_path),
               WORK_DIR=str(tmp_path / 'work'))
    r = subprocess.run([sys.executable, str(ROOT / 'daily' / 'resolve.py')], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    P = json.loads((config.PACKETS_DIR / 'packet_2026-10-23.json').read_text(encoding='utf-8'))
    s = compare_tech.summary(compare_tech.compare('2026-10-23', P, tmp_path / 'FRM Draft 2026-10-23.xlsx'))
    assert s['compared'] == 98 and s['formula_same'] >= 88 and s['settings_same'] >= 75 and s['different'] <= 3, s
    assert compare_tech.same_mat('CaCO3 –Heritage HM-10MAX', 'CaCO3 -Heritage HM-10MAX')
    assert compare_tech.same_mat('Q1203K', 'F1203K') and not compare_tech.same_mat('KS MB-CR401K', 'F1203K')
