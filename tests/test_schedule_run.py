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


def test_gate_dates_and_skips(tmp_path, monkeypatch):
    import datetime
    import json
    import schedule_gate as g
    assert g.dates(datetime.date(2026, 10, 6)) == ['2026-10-05', '2026-10-06']
    assert g.dates(datetime.date(2026, 10, 5)) == ['2026-10-02', '2026-10-05']      # Monday -> Friday
    monkeypatch.setattr(g, 'LOCK', tmp_path / 'schedule_run.lock')
    monkeypatch.setattr(g, 'LEDGER', tmp_path / 'handled.json')
    row = ('already', r'C:\x\Die Cutting Schedule 10-06.pdf', 'DIE CUT SCHEDULE ', '2026-10-06 13:24')
    monkeypatch.setattr(g, 'fetch', lambda ds, wait=30: [row])
    noon = datetime.datetime(2026, 10, 6, 12, 0)
    assert g.check(now=datetime.datetime(2026, 10, 6, 16, 35)).startswith('gate: skip (after 16:20')
    assert g.check(now=noon) == 'gate: run'                                          # not handled yet
    assert g.check(now=noon).startswith('gate: skip (a run is working')
    g.done()
    assert not g.LOCK.exists() and list(json.loads(g.LEDGER.read_text())) == [g.key(row)]
    assert g.check(now=noon).startswith('gate: skip (no new schedule email')
