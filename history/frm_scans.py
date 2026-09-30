"""Tech's formulation pages kept in older copier scans, 2021 on, read by eye (Claude, 30 Sep 2026; James Kuo: "go ahead and
add everything after 2020", "if the fomulation is obsolete one (replaced by something newer) put it in the log instead").
Written in the daily packet's FRM layout, one packet per issue date, so db/import_frm.py (--history) and daily/record.py
(--history-frm) handle them as they handle a day's FRM. Handwriting is kept in 'handwritten', never as data. Each order's
product comes from the extrusion schedule history (the nearest schedule on or after the issue, else before).

    python history/frm_scans.py        -> work/history/frm_scans.json
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

HOP = ['Hopper 1', 'Hopper 2', 'Hopper 3', 'Hopper 4', 'Hopper 5']
VCOL = ['A V1', 'A V2', 'A V3', 'A V4', 'A V5', 'B V1', 'B V2', 'B V3', 'B V4', 'C V1', 'C V2', 'C V3', 'C V4']
V9 = [f'V{i}' for i in range(1, 10)]
S61 = ['A 1', 'A 2', 'A 3', 'A 4', 'A 5', 'A 6', 'B 1', 'C 1', 'C 2', 'C 3', 'C 4', 'C 5', 'C 6', 'D 1']
RUNOUT = 'Use this formula in case PP WB Reclaim is run out'
V3 = 'PP Virgin-silo 3 (6502A)'
V3F = 'PP Virgin-silo 3 (F6502A)'
V4 = 'PP Virgin-silo 4 (6502A)'
V4F = 'PP Virgin-silo 4 (F6502A)'
TALC = 'HiTalc ZS (or N40109A)'
WB = 'WB-W26038A'
CACO3 = 'CaCO3 -Heritage HM-10MAX'
REC = 'PP WB Reclaim'
KS_MDI = 'KS-MDI PE-500 (or Spartech B60009 or NPC PE90000F)'
KS_NPC = 'KS- NPC PE90000F (or Spartech B60009 or MDI PE-500)'
VMX = 'Vistamaxx 3588FL Pre-mix'
YUNG = 'PP Yungsox 5050S'


def f(code, cols, feeds, note='', **extra):
    fe = {c: {'material': '', 'set': ''} for c in cols}
    for c, (m, s) in feeds.items():
        fe[c] = {'material': m, 'set': s}
    return {'formula_code': code, 'feeders': fe, 'note': note, **extra}


def page(line, no, cols, groups, scan_page, date, ac='', footnotes=(), effective='', handwritten=''):
    return {'scan_page': scan_page, 'title': f'Line {no} ({line}) Formulations', 'line_no': str(no), 'line_code': line,
            'date': date, 'header_note': ac, 'feeder_columns': cols, 'footnotes': list(footnotes), 'footer': 'Tech. Department',
            'effective_date': effective, 'handwritten': handwritten, 'unclear': '',
            'groups': [{'orders': o, 'formulas': fs} for o, fs in groups]}


def se61_a(a1, a2, a3m, a3, a4, b1m, c2, c3, c4, c6m=None, c6=None, a5=None, c1=None):
    d = {'A 1': ('PP Mix Reclaim', a1), 'A 2': (a2, 'Auto'), 'A 3': (a3m, a3), 'A 4': (TALC, a4), 'B 1': (b1m, '100'),
         'C 2': ('F6502A', 'Auto'), 'C 4': (TALC, c4), 'D 1': (b1m, '100')}
    if c3:
        d['C 3'] = ('OG-D26074A', c3)
    if c6m:
        d['C 6'] = (c6m, c6)
    if a5:
        d['A 5'] = ('FR-GPP30003 MP', a5)
    if c1:
        d['C 1'] = ('FR-GPP30003 MP', c1)
    return d


PK = 'Downloads/doc05067520260827113931.pdf'
D22 = '10/28/22'
ISSUES = [
    {'packet_date': '2022-10-28', 'frm_source_scan': PK + ' (2 Nov 2022 packet, sheets 111-116: two pages a sheet)', 'frm': [
        page('SE11', 1, HOP, [(['H2AA266-1', 'H2AA257-1'], [
            f('FU0042WB3', HOP, {'Hopper 1': (WB, '41'), 'Hopper 2': (TALC, '15'), 'Hopper 3': (REC, '31'), 'Hopper 4': (V3, '30'), 'Hopper 5': (CACO3, '23')}),
            f('FU0022WB3', HOP, {'Hopper 1': (WB, '50'), 'Hopper 2': (TALC, '15'), 'Hopper 3': ('F1203K', '16'), 'Hopper 4': (V3, '45'), 'Hopper 5': (CACO3, '18')}, RUNOUT)])],
            '116b', D22, 'AC = 1', ['Note: CaCO3 means calcium carbonate.'], '06/06/00'),
        page('SE12', 2, HOP, [
            (['H2AA029-1', 'H2AA028-1', 'H2AA305-1'], [
                f('FU0041WB4', HOP, {'Hopper 1': (WB, '33'), 'Hopper 2': (TALC, '17'), 'Hopper 3': (REC, '41'), 'Hopper 4': (V3, '44')}),
                f('FU0151WB4', HOP, {'Hopper 1': (WB, '50'), 'Hopper 2': (TALC, '17'), 'Hopper 3': ('F1203K', '7'), 'Hopper 4': (V3, '74'), 'Hopper 5': (CACO3, '13')}, RUNOUT)]),
            (['RP22421-4'], [f('FUA152WB4', HOP, {'Hopper 1': (WB, '50'), 'Hopper 2': (TALC, '27'), 'Hopper 3': ('F1203K', '14'), 'Hopper 4': (V3, '71')})])],
            '116a', D22, 'AC = 90', ['Note: CaCO3 means calcium carbonate.'], '06/06/00',
            'Running conditions written by hand 10/31-11/4/22 (LSP, Ext, MT, MP, T.R., CT); never read as data'),
        page('SE13', 3, HOP, [
            (['RP22701-5'], [f('FUA151BL4', HOP, {'Hopper 2': (TALC, '42'), 'Hopper 3': ('F1203K', '22'), 'Hopper 4': (V3F, '42'), 'Hopper 5': ('BL-B26003A (OR NPC-B60387)', '18')}, 'Match color and opacity with QC sample')]),
            (['H2AA326-1', 'H2AA326-2'], [f('FUA001WB6', HOP, {'Hopper 2': (TALC, '46'), 'Hopper 4': (V3, '55'), 'Hopper 5': (WB, '15')})]),
            (['RP22421-4'], [f('FUA152WB4', HOP, {'Hopper 2': (TALC, '50'), 'Hopper 3': ('F1203K', '13'), 'Hopper 4': (V3F, '48'), 'Hopper 5': (WB, '15')})])],
            '115b', D22, 'AC = 90', ['Note: CaCO3 means calcium carbonate.'], '06/06/00',
            'Running conditions written by hand 10/31-11/4/22; never read as data'),
        page('SE21', 4, HOP, [
            (['RP22907-2', 'RP22A25-2', 'RP22928-1'], [f('FUA152WB4', HOP, {'Hopper 1': (V3F, '51'), 'Hopper 2': (TALC, '8'), 'Hopper 3': ('F1203K', '13'), 'Hopper 4': (WB, '21')})]),
            (['RP22A12-1'], [
                f('FUA021WB6', HOP, {'Hopper 1': (V3F, '50'), 'Hopper 2': (TALC, '5'), 'Hopper 3': (REC, '35'), 'Hopper 4': (WB, '12'), 'Hopper 5': (CACO3, '15')}),
                f('FUA001WB6', HOP, {'Hopper 1': (V3F, '63'), 'Hopper 2': (TALC, '5'), 'Hopper 4': (WB, '18'), 'Hopper 5': (CACO3, '25')}, RUNOUT)])],
            '115a', D22, '', ['Note: CaCO3 means calcium carbonate.'], '5/30/00',
            'Running conditions written by hand 10/31-11/4/22; never read as data'),
        page('SE22', 5, HOP, [
            (['H2AA227-1'], [
                f('FU0041WBA', HOP, {'Hopper 1': (V3, '40'), 'Hopper 2': (TALC, '5'), 'Hopper 3': (REC, '60'), 'Hopper 4': (WB, '7'), 'Hopper 5': (CACO3, '4')}),
                f('FU0001WBA', HOP, {'Hopper 1': (V3, '56'), 'Hopper 2': (TALC, '4'), 'Hopper 4': (WB, '15'), 'Hopper 5': (CACO3, '4')}, RUNOUT)]),
            (['H2AA006-1', 'H2AA169-1', 'H2AA283-1'], [
                f('FU0061WBD', HOP, {'Hopper 1': (V4, '22'), 'Hopper 2': (TALC, '4'), 'Hopper 3': (REC, '99'), 'Hopper 4': (WB, '6'), 'Hopper 5': (CACO3, '4')}),
                f('FU0001WBD', HOP, {'Hopper 1': (V4, '64'), 'Hopper 2': (TALC, '4'), 'Hopper 4': (WB, '13'), 'Hopper 5': (CACO3, '4')}, RUNOUT)])],
            '111b', D22, '', ['Note: CaCO3 means calcium carbonate.'], '5/30/00',
            'Running conditions written by hand 10/31-11/4/22; never read as data'),
        page('SE23', 6, HOP, [(['RP22630-1'], [f('FUA152WB4', HOP, {'Hopper 1': (V4F, '99'), 'Hopper 2': (TALC, '16'), 'Hopper 3': ('F1203K', '27'), 'Hopper 4': (WB, '40')})])],
             '111a', D22, 'AC = 1', ['Note: CaCO3 means calcium carbonate.'], '5/30/00',
             'Running conditions written by hand 10/31-11/4/22; never read as data'),
        page('SE24', 7, VCOL, [(['H2AA206-1', 'RP22630-1', 'RP22912-2'], [f('FUA152WB4', VCOL, {'A V1': (WB, '2.7'), 'A V3': (TALC, '9'), 'A V4': (V4, '80.3'), 'A V5': ('F1203K', '8')})])],
             '112b', D22, '', [], '6/15/00', 'Running conditions written by hand 10/31-11/4/22; never read as data'),
        page('SE25', 10, HOP, [
            (['H2AA122-1', 'H2AA291-1', 'H2AA291-2'], [
                f('FU0021WB4', HOP, {'Hopper 1': (V4F, '40'), 'Hopper 2': (REC, '72'), 'Hopper 4': (WB, '13'), 'Hopper 5': (TALC, '16')}),
                f('FU0021WB4', HOP, {'Hopper 1': (V4F, '45'), 'Hopper 2': ('F1203K', '16'), 'Hopper 4': (WB, '16'), 'Hopper 5': (TALC, '16')}, RUNOUT)]),
            (['H2AA291-3'], [f('FU0110WB7', HOP, {'Hopper 1': (V4F, '64'), 'Hopper 2': ('F1203K', '21'), 'Hopper 4': (WB, '13'), 'Hopper 5': (TALC, '54')})]),
            (['RP22201-1'], [
                f('RU0001WB4', HOP, {'Hopper 1': (REC, '99')}),
                f('FU0021WB4', HOP, {'Hopper 1': (V4F, '40'), 'Hopper 2': (REC, '50'), 'Hopper 3': (CACO3, '5'), 'Hopper 4': (WB, '13'), 'Hopper 5': (TALC, '8')}, RUNOUT)])],
            '113a', D22, 'AC = 1',
            ['Note: For KS, increase Hopper 4 setting if the board looks too gray, because the PP Mix from the boxes/silo 8 might be too much WB (or others) colored.',
             'Note: CaCO3 means calcium carbonate.'], '5/30/00', 'Running conditions written by hand 11/2-11/4/22; never read as data'),
        page('SE31', 8, VCOL, [
            (['RP22A20-2', 'H2AA313-1', 'H2AA298-1', 'RP22A20-4'], [f('FUA152WB4', VCOL, {'A V1': (V4, '48'), 'A V2': ('F1203K', '12'), 'A V3': (TALC, '8'), 'A V4': (WB, '19')})]),
            (['H2AA249-3', 'RP22A14-2', 'RP22602-5'], [f('FXA020WB4', VCOL, {
                'A V1': (V4, '17'), 'A V2': ('F1203K', '34'), 'A V3': (TALC, '7'), 'A V4': ('WB-W40020M', '44'),
                'B V1': (V4, '59'), 'B V3': (TALC, '60'), 'B V4': ('WB-NPC PE-W22151', '57'),
                'C V1': (V4, '59'), 'C V3': (TALC, '60'), 'C V4': ('WB-NPC PE-W22151', '57')}, '(Please use W26038A if NPC PE-W22151 is run out)')]),
            (['H2AA315-1'], [f('FUA152WB4', VCOL, {'A V1': (V4, '48'), 'A V2': ('F1203K', '12'), 'A V3': (TALC, '8'), 'A V4': (WB, '19')})])],
            '112a', D22, '', [], '6/15/00', 'Running conditions written by hand 10/31-11/4/22; never read as data'),
        page('SE32', 9, VCOL, [(['RP22630-1'], [
            f('FUA152WB4', VCOL, {'A V1': (V4, '51'), 'A V2': ('F1203K', '25'), 'A V3': (TALC, '9'), 'A V4': (WB, '20')}, '', superseded_on_page=True),
            f('FUA152WB4', VCOL, {'A V1': (V4, '48'), 'A V2': ('F1203K', '29'), 'A V3': (TALC, '10'), 'A V4': (WB, '19')}, '(New Formula)', replaces_row=1)])],
            '113b', D22, '', ['Note: CaCO3 means calcium carbonate.'], '6/15/00'),
        page('SE43', 13, V9, [(['RP22630-1'], [f('FUA151WB4', V9, {'V1': (TALC, '9'), 'V5': ('PP Virgin (F6502A)', '80.3'), 'V7': ('F1203K', '8'), 'V8': (WB, '2.7')})])],
             '114b', D22, '', [], '6/15/00', "'WP20238' written at the top; running conditions written by hand 10/31-11/4/22; never read as data"),
        page('SE61', 16, S61, [
            (['H2AA186-1', 'H2AA180-1', 'RP22518-1'], [f('BF0000KSA', S61, se61_a('40', 'F1102K', KS_MDI, '1.0', '10', VMX, 'Auto', None, '5', KS_MDI, '2.0'))]),
            (['H29A351-1', 'H2AA296-1'], [f('BF0000EBA', S61, se61_a('25', 'F1203K', KS_MDI, '2.0', '5', VMX, 'Auto', '3.0', '5'))]),
            (['H2AA031-1'], [f('BF0000EB3', S61, se61_a('25', 'F1203K', KS_NPC, '2.0', '10', VMX, 'Auto', '3.0', '5'))])],
            '114a', D22, '', [], '6/15/00', "'KS-357' circled and running conditions written by hand 10/31 and 11/2/22; never read as data"),
    ]},
    {'packet_date': '2025-09-03', 'frm_source_scan': 'Downloads/doc05052220260825135824.pdf', 'frm': [
        page('SE43', 13, V9, [(['RP25730-1', 'RP24A30-1'], [f('FUA151WB4', V9, {'V1': (TALC, '8'), 'V5': ('PP Virgin (F6502A)', '74'), 'V7': ('F1203K', '15'), 'V8': (WB, '3')})])],
             18, '9/3/25', '', [], '6/15/00'),
        page('SE61', 16, S61, [
            (['H58A120-1', 'H58A195-2', 'H58A120-2', 'H58A195-1'], [f('BF0000EB3', S61, se61_a('50', 'F6502A', KS_NPC, '2.0', '10', YUNG, 'Auto', '3.0', '5'))]),
            (['H57A107-2'], [f('BFR000EB3', S61, se61_a('50', 'F1203K', KS_NPC, '2.0', '10', YUNG, 'Auto', '3.0', '5', a5='15', c1='15'))]),
            (['RP25630-1'], [f('BF0000EB3', S61, se61_a('50', 'F6502A', KS_NPC, '2.0', '10', YUNG, 'Auto', '3.0', '5'))]),
            (['RP25818-1'], [f('BF0000EB5', S61, se61_a('50', 'F6502A', KS_MDI, '2.0', '10', YUNG, 'Auto', '3.0', '5'))])],
            18, '9/3/25', '', [], '6/15/00', 'A hand-drawn arrow at H57A107-2'),
    ]},
    {'packet_date': '2021-09-15', 'frm_source_scan': 'Downloads/doc05075620260828083812.pdf', 'frm': [
        page('SE23', 6, HOP, [(['HW5A227-1', 'HW9A128-1', 'RP21714-6'], [f('FUA152WB4', HOP, {'Hopper 1': (V3F, '99'), 'Hopper 2': (TALC, '20'), 'Hopper 3': ('F1203K', '55'), 'Hopper 4': (WB, '44')})])],
             11, '9/15/21', 'AC = 1', [], '5/30/00',
             "'AT 9:00AM' written in the note; a second copy (scan page 25) has '(F6502A)' struck out with 'EXXON' and '9:30am' written - never read as data"),
    ]},
    {'packet_date': '2021-08-05', 'frm_source_scan': 'Downloads/doc05120620260903124629.pdf', 'frm': [
        page('SE31', 8, VCOL, [
            (['HW7A195-1', 'RP21729-1', 'HW7A188-1'], [f('FUA152WB4', VCOL, {'A V1': (V3F, '48'), 'A V2': ('F1203K', '12'), 'A V3': (TALC, '8'), 'A V4': (WB, '19')})]),
            (['RP21413-2', 'HW3A156-1', 'HW3A157-1', 'HW3A158-1', 'HW4A186-1'], [f('FXA020WB4', VCOL, {
                'A V1': (V3F, '17'), 'A V2': ('F1203K', '34'), 'A V3': (TALC, '7'), 'A V4': ('WB-W40020M', '44'),
                'B V1': (V3F, '59'), 'B V3': (TALC, '60'), 'B V4': ('WB-NPC PE-W22151', '57'),
                'C V1': (V3F, '59'), 'C V3': (TALC, '60'), 'C V4': ('WB-NPC PE-W22151', '57')})])],
            39, '8/5/21', '', [], ''),
    ]},
]


def products():
    """order -> [(date, product)] from the extrusion schedule history (text PDFs and scanned days)."""
    out = {}
    for fn in ('ext_history.csv', 'ext_history_scans.csv'):
        p = config.WORK_DIR / 'history' / fn
        for r in csv.DictReader(open(p, encoding='utf-8')):
            out.setdefault(r['order'], []).append((r['date'], r['prod_code']))
    return out


def main():
    prods = products()
    out, missing = [], []
    for pk in ISSUES:
        d = pk['packet_date']
        rows = []
        for pg in pk['frm']:
            for g in pg['groups']:
                for o in g['orders']:
                    seen = sorted(prods.get(o, []))
                    after = [x for x in seen if x[0] >= d]
                    pick = (after[0] if after else seen[-1]) if seen else None
                    if pick:
                        rows.append({'order': o, 'prod_code': pick[1], 'from': pick[0]})
                    else:
                        missing.append((d, pg['line_code'], o))
        out.append({**pk, 'source_scan': pk['frm_source_scan'], 'ext': [{'line': '', 'scan_page': 0, 'rows': rows}], 'cnv': []})
    p = config.WORK_DIR / 'history' / 'frm_scans.json'
    p.write_text(json.dumps(out, indent=1), encoding='utf-8')
    return p, sum(len(g['formulas']) for pk in ISSUES for pg in pk['frm'] for g in pg['groups']), missing


if __name__ == '__main__':
    print(main())
