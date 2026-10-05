"""A day sent as the system's own PDFs (2 Oct 2026: BPN9PFR$_Z7Ubmp3i.PDF and "Die Cutting Schedule 10-02.pdf"):
daily/packet_from_pdf.py and daily/cnv_from_pdf.py build the packet from the PDFs' text."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'daily'))
PK = ROOT / 'data' / 'packets' / 'packet_2026-10-02.json'
EXT_PDF = Path(r'C:/Users/JamesKuo/Downloads/BPN9PFR$_Z7Ubmp3i.PDF')
CNV_PDF = Path(r'C:/Users/JamesKuo/Downloads/Die Cutting Schedule 10-02.pdf')
num = lambda s: int(str(s).replace(',', ''))


def test_ext_from_the_pdf_adds_up():
    pk = json.loads(PK.read_text(encoding='utf-8'))
    rows = [(pg['line'], r) for pg in pk['ext'] for r in pg['rows']]
    assert len(rows) == 88
    for pg in pk['ext']:
        if pg['line_total_pcs']:
            mine = [r for line, r in rows if line == pg['line']]
            assert sum(num(c['total_sheets']) for r in mine for c in r['cut_rows']) == num(pg['line_total_pcs'])
            assert sum(num(r['weight_lbs']) for r in mine) == num(pg['line_total_lbs'])
    assert pk['ext'][-1]['final_total'] == '6,325,199 PCs / 21,541,117 LBs'


def test_cnv_from_the_pdf():
    pk = json.loads(PK.read_text(encoding='utf-8'))
    rows = {r['order']: r for pg in pk['cnv'] for r in pg['rows']}
    assert sum(len(pg['rows']) for pg in pk['cnv']) == 64 and len(pk['cnv']) == 11
    assert all(re.fullmatch(r'[A-Z0-9]{7}-\d{1,3}', o) for o in rows)
    assert rows['H68A127-1']['color'] == 'WB GT WB'                      # cut off on the paper ('B GT V'), whole in the PDF
    assert rows['H68A170-2']['semi_size'] == '51 4/16 X 73 12/16'
    assert rows['H68A091-1']['done_note'] == '256 DONE / 234 DONE IN COOLSEAL / 490 TOTAL DONE'
    assert 'Target wt is 0.3619' in rows['H68A091-1']['row_notes']        # build_master.weight_target reads it here
    assert rows['H68A252-1']['ink_color'] == 'Black / 187 RED'            # a cell's second line
    assert rows['RP26525-3']['semi_start'] == '####'                      # the slitter page's extra column


@pytest.mark.skipif(not (EXT_PDF.exists() and CNV_PDF.exists()), reason='the 2 Oct PDFs are not on this PC')
def test_the_packet_is_what_the_pdfs_give():
    import packet_from_pdf as E
    import cnv_from_pdf as C
    pk = json.loads(PK.read_text(encoding='utf-8'))
    assert E.ext_pages(EXT_PDF)[0] == pk['ext']
    assert C.cnv_pages(CNV_PDF) == pk['cnv']


INTAKE = [(Path(r'C:/Users/JamesKuo/Downloads/BPN9PFR$_Z7XTIDbA.PDF'), ('ext-pdf', '2026-10-05')), (EXT_PDF, ('ext-pdf', '2026-10-02')),
          (CNV_PDF, ('cnv-pdf', '2026-10-02')), (Path(r'C:/Users/JamesKuo/Downloads/doc05268320260930114819.pdf'), ('scan', '2026-09-30'))]


@pytest.mark.parametrize('pdf,expected', INTAKE)
def test_intake_tells_a_scan_from_a_system_pdf(pdf, expected):
    """James Kuo, 5 Oct 2026: "I want to be able to feed it in both way (scan and PDf doc) and have it able to process"."""
    if not pdf.exists():
        pytest.skip(f'{pdf.name} is not on this PC')
    import intake
    assert intake.kind(pdf) == expected
