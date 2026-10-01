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


def test_bank_prime_gives_exactly_the_same_distances():
    import numpy as np
    import ext_scan_reader as R
    rng = np.random.default_rng(1)
    X = rng.normal(size=(500, 40)).astype(np.float32)
    B = R.Bank(X, rng.choice(list('ABC0123'), 500)).fit()
    F = [X[i] + rng.normal(0, s, 40).astype(np.float32) for i, s in zip(rng.integers(0, 500, 50), rng.uniform(0, .5, 50))]
    F.append(X[3].copy())                                                   # a bank glyph itself: distance 0
    ref = []
    for f in F:                                                             # the original per-label loop
        d = np.linalg.norm(B.A - f, axis=1)
        ref.append({lab: float(d[B.labels == lab].min()) for lab in np.unique(B.labels)})
    assert [B.dists(f) for f in F] == ref
    B.cache = {}
    B.prime(F)
    assert [B.cache[f.tobytes()] for f in F] == ref


def test_a_step1_packet_is_read_only_by_the_formulation_scripts(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT))
    import config
    full, s1 = tmp_path / 'packets', tmp_path / 'stage1'
    full.mkdir(); s1.mkdir()
    (full / 'packet_2026-09-29.json').write_text('{}'); (s1 / 'packet_2026-09-30.json').write_text('{}')
    monkeypatch.setattr(config, 'PACKETS_DIR', full); monkeypatch.setattr(config, 'STAGE1_DIR', s1)
    monkeypatch.setenv('PKT_DATE', '2026-09-30'); monkeypatch.delenv('PKT_STAGE1', raising=False)
    assert [p.name for p in config.packet_files()] == ['packet_2026-09-29.json']
    monkeypatch.setenv('PKT_STAGE1', '1')
    assert config.packet_files()[-1] == s1 / 'packet_2026-09-30.json'
    (full / 'packet_2026-09-30.json').write_text('{}')                     # step 2 done: the full packet wins
    assert all(p.parent == full for p in config.packet_files())


def test_validate_never_guesses_between_two_candidates(monkeypatch):
    import validate_read as V
    two = [{'line': 'SE43', 'order': o, 'prod': 'DPP30WB1020', 'die': 'PA205', 'thk': '3.0', 'colors': 'WB WB WB', 'mat': 'PPP',
            'grade': 'P', 'gsm': '631', 'spec': 'R1R1R1', 'special': ''} for o in ('H69A038-1', 'H69A038-2')]
    monkeypatch.setattr(V, 'schedules', lambda: {'2026-09-29': two})
    out, *_ = V.validate('2026-09-30', [_rows(order='HR62266-1')])
    assert out[0]['order'] == 'HR62266-1' and 'check by eye' in out[0]['checks']


def _fields(**over):
    f = {'T': 'Y', 'order_width': '31 5/8', 'order_length': '34 1/4', 'pack_code': '30X42', 'num_plt': '190',
         'cut_rows': [{'width': '31 5/8', 'length': '34 7/8', 'total_sheets': '34,675'}] * 2, 'pcs_per_stack': '365',
         'stk_per_plt': '1', 'weight_lbs': '67,270', 'instr_date': '16-Oct', 'web_width': '63 1/4'}      # 30 Sep H69A039-1
    f.update(over)
    return f


def test_step2_record_checks():
    import ext_fields as F
    assert F.check_record(_fields(), '631') == []
    assert F.check_record(_fields(weight_lbs='61,270'), '631')                # weight vs size x GSM x sheets
    assert F.check_record(_fields(num_plt='19'), '631')                       # pallets x pieces x stacks vs sheets
    assert F.check_record(_fields(num_plt='191'), '631') == []                # the report rounds pallets by up to one
    assert F.check_record(_fields(order_width='31 4/8'), '631')               # not a printed fraction
    assert F.check_record(_fields(web_width='64 1/4'), '631')                 # web = whole cut widths
    assert F.check_record(_fields(pack_code='30442'), '631')                  # X read as 4
    big = _fields(cut_rows=[{'width': '31 1/8', 'length': '51 1/4', 'total_sheets': '184,867'}] * 3, num_plt='999', web_width='93 3/8',
                  pcs_per_stack='295')
    assert F.check_record(big, None) == []                                    # 999 = the most the report prints
    assert F.check_record(dict(big, pcs_per_stack='9295'), None)              # a stroke read as a digit (30 Sep H68A091-1)


def test_step2_cut_rows_and_dates():
    import ext_fields as F
    a, b = {'width': '31 1/8', 'length': '51 1/4', 'total_sheets': '184,867'}, {'width': '31 1/8', 'length': '51 1/8', 'total_sheets': '184,867'}
    rows = [dict(a), dict(b), dict(a)]
    assert 'taken from them' in F.agree_cut_rows(rows)[0] and rows[1] == a   # one row against two that agree
    rows = [dict(a), dict(b)]
    assert 'check' in F.agree_cut_rows(rows)[0] and rows[1] == b             # one against one: never chosen
    assert [F.snap_instr(t) for t in ('20-0ct', 'St0ck', '19-Mar', '19 Mar', 'garbage')] == ['20-Oct', 'Stock', '19-Mar', '19-Mar', '']
