"""The scan reader's logic checks (James Kuo, 1 Oct 2026: "the main goal is to improve the OCR read and logic check when OCR
read failed"). Measured against the system's own PDFs of 23, 24 and 30 Sep 2026: every key field right after the checks.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scan_reader'))
HIST = ROOT / 'work' / 'history' / 'ext_history.csv'
need_hist = pytest.mark.skipif(not HIST.exists(), reason='system schedule history not parsed on this PC (history/prod_instr.py)')


@need_hist
@pytest.mark.parametrize('read,printed', [
    # punctuation from the printed line (a comma and a period look alike on the scan); numbers from the scan
    ('VOIDFORM. PLEASE WATCH WEIGHT (RANGE IS 582 - 600 GSM)', 'VOIDFORM, PLEASE WATCH WEIGHT (RANGE IS 582 - 600 GSM)'),
    ('Send to Bobst. Mark Jead edge & make sure of pc count.', 'Send to Bobst. Mark lead edge & make sure of pc count.'),
    ('RUN WITH RPA40W83051', 'RUN WITH RPA40WB3051'),                  # B read as 8 in a product code
    ('RUN WITH RPA40WB3051 worse', 'RUN WITH RPA40WB3051'),            # marks read after the text
    ('46 PLTS DONE oo EES', '46 PLTS DONE'),
    ('RUN WITH NEXT ee 20 PLTS DONE', 'RUN WITH NEXT 20 PLTS DONE'),
])
def test_instruction_lines_snap_to_printed_text(read, printed):
    import instructions as I
    assert I.snap_line(read)[0] == printed


@need_hist
def test_a_real_wording_difference_is_not_snapped():
    import instructions as I
    k, c = I.key('RUN WIHT RPA40WB3051 16 PLTS DONE'), I.key('RUN WITH RPA40WB3051 16 PLTS DONE')
    assert not I.ocr_explains(k, c)                                    # 'WIHT' is printed so (28-30 Sep): kept as read


@need_hist
def test_cut_row_numbers_are_not_instructions():
    import instructions as I
    assert I.snap_line('31 1/8 50 1/4 30,160')[1].startswith('dropped')


def _rows(**over):
    base = {'scan_page': '1', 'report_page': '1', 'line': 'SE43', 'order': 'H69A038-1', 'prod': 'DPP30WB1020', 'die': 'PA205',
            'thk': '3.0', 'gsm': '631', 'mat': 'PPP', 'grade': 'P', 'spec': 'R1R1R1', 'colors': 'WB WB WB', 'special': '', 'flags': ''}
    base.update(over)
    return base


def test_validate_repairs_from_the_previous_day(monkeypatch):
    import validate_read as V
    yday = [{'line': 'SE43', 'order': 'H69A038-1', 'prod': 'DPP30WB1020', 'die': 'PA205', 'thk': '3.0', 'colors': 'WB WB WB',
             'mat': 'PPP', 'grade': 'P', 'gsm': '631', 'spec': 'R1R1R1', 'special': ''},
            {'line': 'SE12', 'order': 'RP26728-4', 'prod': 'SPA40WB761', 'die': 'PA3B5', 'thk': '4.0', 'colors': 'WB WB WB',
             'mat': 'PPP', 'grade': 'A', 'gsm': '651', 'spec': 'R1R1R1', 'special': ''}]
    monkeypatch.setattr(V, 'schedules', lambda: {'2026-09-29': yday})
    rows = [_rows(order='HR62266-1'),                                       # order under handwriting
            _rows(line='SE12', order='RP26728-4', prod='SPA40WB761', die='PA385', thk='4.0', grade='A'),   # B read as 8
            _rows(scan_page='2', line='SE12', order='', prod='', die='', thk='', gsm='', mat='', grade='', spec='', colors=''),
            _rows(scan_page='2', line='SE12', order='RP26728-4', prod='SPA40WB761', die='PA3B5', thk='4.0', grade='A')]
    out, dropped, gone, prev = V.validate('2026-09-30', rows)
    assert out[0]['order'] == 'H69A038-1' and 'from 2026-09-29' in out[0]['checks']
    assert out[1]['die'] == 'PA3B5'
    assert len(dropped) == 1 and len(out) == 3                              # handwriting read as a row: dropped


def test_validate_never_guesses_between_two_candidates(monkeypatch):
    import validate_read as V
    two = [{'line': 'SE43', 'order': o, 'prod': 'DPP30WB1020', 'die': 'PA205', 'thk': '3.0', 'colors': 'WB WB WB', 'mat': 'PPP',
            'grade': 'P', 'gsm': '631', 'spec': 'R1R1R1', 'special': ''} for o in ('H69A038-1', 'H69A038-2')]
    monkeypatch.setattr(V, 'schedules', lambda: {'2026-09-29': two})
    out, *_ = V.validate('2026-09-30', [_rows(order='HR62266-1')])
    assert out[0]['order'] == 'HR62266-1' and 'check by eye' in out[0]['checks']
