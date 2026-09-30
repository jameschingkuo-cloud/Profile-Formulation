"""The interface's scan reader, run on every scan on file (25, 28 and 29 Sep). Slow (several minutes) and needs Tesseract,
node and the rendered pages, so it runs when OCR_TESTS=1: run it whenever the reader changes.
- ui/ocr_eval.py audit3 is the reference reader: every printed order row of every scan must be taken with the right line,
  order and product (history from schedules before the scan's day only), none wrong, none boxed, none missed.
- tests/js/reader_parity.js runs the page's own reader (ui/reader.js) on the same page images: bands, bars, glyph pitch,
  row isolation, suffix marks, glyph readings and cleaned cells must equal the reference on every row.
James Kuo, 30 Sep 2026: "make sure all these improvement are code in so we dont make the same mistake again", "use this
opportunity to check every scan file you currently have", "ignore hand writing"."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SLOW = pytest.mark.skipif(os.environ.get('OCR_TESTS') != '1', reason='slow: set OCR_TESTS=1')


def _reader(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv('GLYPH_Q', '1')                      # the page's copy of the glyph bank
    sys.path.insert(0, str(ROOT / 'ui'))
    import ocr_eval
    ocr_eval._BANK = None
    return ocr_eval


@SLOW
@pytest.mark.parametrize('date,scan', [('2026-09-25', 'doc05252320260928124922'), ('2026-09-28', 'doc05253620260928134035'),
                                       ('2026-09-29', 'doc05261220260929142225')])
def test_reference_reader_reads_every_row_right(date, scan, monkeypatch):
    if not (ROOT / 'work' / 'pages' / scan).exists():
        pytest.skip('pages not rendered (scan_reader/render_pages.py)')
    P = _reader(monkeypatch)
    import json
    pk = json.loads((ROOT / 'data' / 'packets' / f'packet_{date}.json').read_text(encoding='utf-8'))
    truth = sorted(((e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']), key=str)
    res = P.audit3(date, scan, 'before', show=False)
    taken = [r for r in res if r[4] != 'check']
    assert [r for r in taken if (r[1], r[2], r[3]) not in set(truth)] == []      # never a wrong line, order or product
    assert sorted(((r[1], r[2], r[3]) for r in res), key=str) == truth           # every printed row, nothing extra
    assert len(taken) == len(truth)                                                # and nothing left for a person
    assert not any(r[2] == 'H69A203-17' for r in res)


@SLOW
def test_page_reader_equals_reference(monkeypatch, tmp_path):
    node = shutil.which('node')
    if not node or not (ROOT / 'out' / 'glyph-bank.js').exists() or not (ROOT / 'work' / 'pages').exists():
        pytest.skip('node, the built page (ui/build.py) or the rendered pages are missing')
    P = _reader(monkeypatch)
    n = P.dump_parity(tmp_path)
    r = subprocess.run([node, str(ROOT / 'tests' / 'js' / 'reader_parity.js'), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    last = r.stdout.strip().splitlines()[-1]
    assert re.fullmatch(rf'{n} rows, 0 differences', last), '\n'.join(l for l in r.stdout.splitlines() if l.startswith('DIFF'))[:3000]
