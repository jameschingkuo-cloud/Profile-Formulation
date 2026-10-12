"""Tech's FRM pages read by eye into text: the converter keeps every value as written and refuses what is not a page."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'daily'))
import frm_from_text as f  # noqa: E402

TEXT = """# comment
## 4 | SE21 | 4 | 10/6/26 |  | H5 | 5/30/00
foot: Note: CaCO3 means calcium carbonate.
> RP26916-2
FUA021WB6 ; PP Virgin-silo 3 (F6502A) @ 50 ; HiTalc ZS (or N40109A) @ 5 ; PP WB Reclaim @ 35 ; WB-W26038A @ 12 ; CaCO3 -Heritage HM-10MAX @ 15
FUA021WB6 ; PP Virgin-silo 3 (6502A) @ 63 ; HiTalc ZS (or N40109A) @ 5 ; - ; WB-W26038A @ 18 ; CaCO3 -Heritage HM-10MAX @ 25 ; # (Use this formula in case PP WB Reclaim is run out)
## 34 | SE31 | 8 | 10/5/26 |  | ABC13 | 6/15/00
> H69A031-3
FUA01WM6! ; A V1=PP Virgin-silo 4 (F6502A) @ 69 ; A V3=HiTalc ZS (or N40109A) @ 6
"""


def test_parse_keeps_values_and_flags_odd_codes():
    f.ODD.clear()
    pages = f.parse(TEXT)
    se21, se31 = pages
    assert se21['feeder_columns'][0] == 'Hopper 1' and se21['footnotes'] == ['Note: CaCO3 means calcium carbonate.']
    a, b = se21['groups'][0]['formulas']
    assert a['feeders']['Hopper 3'] == {'material': 'PP WB Reclaim', 'set': '35'}
    assert b['feeders']['Hopper 3'] == {'material': '', 'set': ''} and b['note'].startswith('(Use this formula')
    assert se31['groups'][0]['formulas'][0]['formula_code'] == 'FUA01WM6'          # as printed, not corrected
    assert se31['groups'][0]['formulas'][0]['feeders']['A V2'] == {'material': '', 'set': ''}
    assert f.ODD == [(34, 'SE31', 'FUA01WM6')]


def test_parse_refuses_bad_lines():
    with pytest.raises(SystemExit):
        f.parse('## 1 | SE11 | 1 | 10/6/26 | AC = 1 | H5 | 06/06/00\n> H69A039-1\nFU0022WB ; WB @ 50\n')   # code too short, no "!"
    with pytest.raises(SystemExit):
        f.parse('## 1 | SE11 | 1 | 10/6/26 | AC = 1 | H5 | 06/06/00\n> H69A03-1\n')                     # not an order number
