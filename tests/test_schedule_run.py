"""The scheduled email run's helpers: which Downloads files it looks at, and what it does next."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'daily'))

import schedule_status  # noqa: E402


def test_only_schedule_pdfs_are_looked_at(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(schedule_status, 'kind', lambda f: seen.append(f.name) or ('ext-pdf', '2026-10-06'))
    for n in ('BPN9PFR$_Z7Y53NYt.PDF', 'Die Cutting Schedule 10-06.pdf', 'doc05302620261006093602.pdf',
              'AS400_Order_Inquiry_Sample.xlsx', 'BPN9PFR Password list.pdf'):
        (tmp_path / n).write_bytes(b'%PDF-1.4')
    found = schedule_status.schedule_pdfs('2026-10-06', folder=tmp_path)
    assert sorted(seen) == ['BPN9PFR$_Z7Y53NYt.PDF', 'Die Cutting Schedule 10-06.pdf']
    assert len(found['ext-pdf']) == 2


def test_nothing_received_waits(monkeypatch):
    monkeypatch.setattr(schedule_status, 'schedule_pdfs', lambda d: {'ext-pdf': [], 'cnv-pdf': []})
    assert schedule_status.status('2099-01-05')['next'] == 'wait-ext'


def test_gate_window(tmp_path, monkeypatch):
    import datetime
    import json
    import schedule_gate as g
    for name in ('LOCK', 'LEDGER', 'LAST'):
        monkeypatch.setattr(g, name, tmp_path / name)
    row = ('already', r'C:\x\Die Cutting Schedule 10-06.pdf', 'DIE CUT SCHEDULE ', '2026-10-06 13:24:10')
    asked = []

    def fetch(since, until, wait=30):
        asked.append((since, until))
        return [row] if since <= datetime.datetime(2026, 10, 6, 13, 24, 10) < until else []
    monkeypatch.setattr(g, 'fetch', fetch)
    at = lambda h, m: datetime.datetime(2026, 10, 6, h, m)  # noqa: E731
    assert g.check(now=at(16, 43)) == 'gate: skip (after 16:20)'
    assert g.check(now=at(13, 13)).startswith('gate: skip (No new email in system')    # 12:43-13:13: none
    assert asked[-1] == (at(12, 43), at(13, 13)) and g.LAST.read_text() == '2026-10-06 13:13:00'
    assert g.check(now=at(13, 43)) == 'gate: run'                                      # 13:13-13:43 has it
    assert g.check(now=at(14, 13)).startswith('gate: skip (a run is working')            # window stays put
    g.done()
    assert not g.LOCK.exists() and list(json.loads(g.LEDGER.read_text())) == [g.key(row)]
    assert g.check(now=at(14, 13)).startswith('gate: skip (No new email in system')
    assert asked[-1] == (at(13, 43), at(14, 13))
    assert g.check(now=at(13, 43), since=at(13, 13), test=True).startswith('gate: skip (No new email in system: the email')
    assert g.window_dates(datetime.datetime(2026, 10, 2, 16, 13), at(11, 13)) == \
        ['2026-10-02', '2026-10-03', '2026-10-04', '2026-10-05', '2026-10-06']
