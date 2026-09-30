"""The system's own past schedules (history/): every line of every day adds up to the total the report prints, the
rotated print and the misnamed files are read, and the days kept only as scans add up to their printed totals."""
import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'history'))
import config  # noqa: E402
import prod_instr as H  # noqa: E402


def need_folder():
    if not H.FOLDER.exists():
        pytest.skip('Production Instruction folder not synced on this PC')


def test_one_day_adds_up_and_keeps_continued_blocks():
    need_folder()
    info, rows = H.parse_pdf(H.FOLDER / '092426.PDF')
    assert len(rows) == 80 and H.footer_check(info, rows) == []
    r = [x for x in rows if x['order'] == 'H64A244-1'][0]             # block runs on to the next page
    assert r['total_sheets'] == 240120 and '822 PLTS DONE' in r['special']


def test_rotated_print_and_misnamed_files():
    need_folder()
    info, rows = H.parse_pdf(H.FOLDER / '111723.PDF')                 # printed on its side by another mail system
    assert info['run_date'] == '11/17/23' and len(rows) == 53 and H.footer_check(info, rows) == []
    for f, rd in (('0422524.pdf', '4/25/24'), ('BPN9PFR$_Xs7tuhwc.PDF', '10/14/24'), ('BPN9PFR$_YQuWBVBj.PDF', '6/12/25')):
        info, rows = H.parse_pdf(H.FOLDER / f)
        assert info['run_date'] == rd and rows and H.footer_check(info, rows) == []


def test_unlabelled_instructions_are_kept():
    need_folder()
    info, rows = H.parse_pdf(H.FOLDER / '050720.pdf')
    assert [r['special'] for r in rows if r['order'] == 'HV4A339-3'] == ['PLSC4W80x80 / Use pallet tickets without Inteplast logo']


def test_every_parsed_day_adds_up():
    files = config.WORK_DIR / 'history' / 'files.csv'
    if not files.exists():
        pytest.skip('history not parsed on this PC (python history/prod_instr.py parse)')
    rows = list(csv.DictReader(open(files, encoding='utf-8')))
    ext = [f for f in rows if 'EXTRUSION' in (f.get('titles') or '')]
    assert len(ext) >= 1166 and [f['file'] for f in ext if f.get('footer_check')] == []


def test_scanned_days_add_up_to_their_printed_totals(tmp_path):
    if not (config.WORK_DIR / 'history' / 'ext_history.csv').exists():
        pytest.skip('history not parsed on this PC')
    import image_days_manual as M
    n, notes, _ = M.build(out_csv=tmp_path / 'scans.csv')          # raises if a line or a day's total is off
    assert n == 224
    import cnv_scans
    assert cnv_scans.main()[1] == 28
