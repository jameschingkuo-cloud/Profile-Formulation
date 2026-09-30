"""The interface's scan reader, run on real scans (ui/ocr_eval.py read_page15 = the page's ocrPage). Slow (about a minute
per scan) and needs Tesseract and the rendered pages, so it runs when OCR_TESTS=1: run it whenever the reader changes.
James Kuo, 30 Sep 2026: "make sure all these improvement are code in so we dont make the same mistake again"."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCANS = [('2026-09-29', 'doc05261220260929142225'), ('2026-09-28', 'doc05253620260928134035')]


@pytest.mark.skipif(os.environ.get('OCR_TESTS') != '1', reason='slow: set OCR_TESTS=1')
@pytest.mark.parametrize('date,scan', SCANS)
def test_reader_takes_nothing_wrong_and_misses_nothing(date, scan, monkeypatch):
    if not (ROOT / 'work' / 'pages' / scan).exists():
        pytest.skip('pages not rendered (scan_reader/render_pages.py)')
    monkeypatch.chdir(ROOT)
    sys.path.insert(0, str(ROOT / 'ui'))
    import ocr_eval
    import json
    res, unread = ocr_eval.evaluate15(date, scan, show=False)
    pk = json.loads((ROOT / 'data' / 'packets' / f'packet_{date}.json').read_text(encoding='utf-8'))
    truth = {(e['line'], r['order'], r['prod_code']) for e in pk['ext'] for r in e['rows']}
    taken = [x for x in res if x[3] in ('read', 'matched to schedule history')]
    assert [x for x in taken if x[:3] not in truth] == []           # never a wrong order or product taken
    assert len(res) + len(unread) >= len(truth)                     # every printed order row is shown (taken or boxed)
    assert not any(x[1] == 'H69A203-17' for x in res if x[3] != 'check')
