"""The order-number rule (order_number.py), read from the system's own schedules 2020-2026 (history/prod_instr.py)."""
import csv
import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import order_number as on  # noqa: E402

SEP29 = date(2026, 9, 29)


def test_format():
    for o in ('H69A039-1', 'H6AA001-1', 'H5CA049-12', 'H4CA049-1', 'SH69A04-1', 'SH3AA03-2', 'RP26821-1', 'RP24C18-4', 'RP20624-1'):
        assert on.problems(o) == [], o
    for o in ('H69B039-1',      # after an H month comes the letter A
              'H6DA001-1',      # month D does not exist
              'H64A039',        # no suffix
              'H69A039-123',    # suffix 1-2 digits
              'HWBA149-1',      # 2021 letter year: not current
              'RP26011-1',      # month 0 does not exist
              'H69A03-1', 'RP2682-1', 'HSA0S-1'):
        assert on.problems(o), o


def test_dates():
    assert on.opened('H69A039-1', SEP29) == (2026, 9) and on.opened('H5CA049-1', SEP29) == (2025, 12)
    assert on.opened('RP24C18-4', SEP29) == (2024, 12) and on.opened('SH3AA03-1', SEP29) == (2023, 10)
    assert on.problems('H6BA001-1', SEP29)            # November 2026 on a September 2026 schedule: a misread (8 vs B)
    assert on.problems('H6AA001-1', date(2026, 10, 1)) == []     # October orders from 1 Oct
    assert on.problems('H4CA049-1', SEP29) == []                 # 21 months: seen
    assert on.problems('H3CA288-1', SEP29)                       # 33 months: an H order never runs that long
    assert on.problems('RP20624-1', date(2026, 9, 9)) == []      # a stock order can (75 months, 9 Sep 2026)


def test_every_system_order_since_aug_2022_keeps_the_rule():
    """The last 2021 letter-year order (HWBA150-1) left the schedule on 27 Jul 2022."""
    hist = config.WORK_DIR / 'history' / 'ext_history.csv'
    if not hist.exists():
        pytest.skip('system history not parsed on this PC (python history/prod_instr.py parse)')
    bad = [(r['date'], r['order'], on.problems(r['order'], date.fromisoformat(r['date'])))
           for r in csv.DictReader(open(hist, encoding='utf-8'))
           if r['date'] >= '2022-08-01' and on.problems(r['order'], date.fromisoformat(r['date']))]
    assert bad == []


def test_packets_keep_the_rule():
    for f in sorted((ROOT / 'data' / 'packets').glob('packet_*.json')):
        pk = json.loads(f.read_text(encoding='utf-8'))
        d = date.fromisoformat(pk['packet_date'])
        bad = [r['order'] for e in pk['ext'] for r in e['rows'] if on.problems(r['order'], d)]
        bad += [r['order'] for c in pk['cnv'] for r in c['rows'] if on.problems(r['order'], d)]
        assert bad == [], (f.name, bad)
