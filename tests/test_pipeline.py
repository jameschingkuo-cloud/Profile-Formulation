"""Regression tests. Run from the repo root:  python -m pytest -q
They rebuild from the two packets in data/packets and compare with the numbers checked by hand in Cowork (Sep 2026).
Tests that need Tech's calc workbooks skip themselves when CALC_DIR has none."""
import ast, json, os, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'calc'))
import config


def run(script, env_extra, tmp_path):
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(tmp_path / 'out'), **env_extra)
    r = subprocess.run([sys.executable, str(ROOT / script)], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-3000:]
    return r


def dosing_from_source(path):
    """DOSING = {...} read from the file without importing it (daily/load.py needs a packet to import)."""
    for node in ast.parse(Path(path).read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'DOSING' for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f'no DOSING in {path}')


# ---- hardcoded rules --------------------------------------------------------------------------------------------
def test_dosing_tables_agree():
    """James, 26 Sep 2026: lines 7, 12, 13, 16 weigh; the rest are auger lines. The table lives in two files."""
    a = dosing_from_source(ROOT / 'daily' / 'load.py')
    b = dosing_from_source(ROOT / 'calc' / 'auger_rules.py')
    assert a == b
    assert {k for k, v in a.items() if v == 'WEIGHT'} == {'SE24', 'SE42', 'SE43', 'SE61'}
    assert len(a) == 13


def test_scan_reader_rules_block_present():
    s = (ROOT / 'scan_reader' / 'ext_scan_reader.py').read_text(encoding='utf-8')
    assert 'DO NOT REMOVE' in s and 'R1' in s and 'R2' in s


def test_r2_exceptions():
    """James: RD, RM (24 Sep 2026) and OP (28 Sep 2026) are the only letter+letter spec tokens."""
    s = (ROOT / 'scan_reader' / 'ext_scan_reader.py').read_text(encoding='utf-8')
    assert 'SPEC_EXCEPTIONS = ["D", "M", "P"]' in s


def test_rev_index():
    import auger_rules as a
    assert round(a.rev_index(219.1497, '1:14')) == 3068       # virgin PP, 69x69, 1:14
    assert round(a.rev_index(82.3269, '1:36')) == 2964        # 1203K, 69x69, 1:36
    assert a.rev_index(None, '1:36') is None


def test_superseded_copies():
    from common import superseded_copies
    B = [{'line': 'SE25', 'file': 'SE25 Formulation.xls'}, {'line': 'SE25', 'file': 'Copy of SE25 Formulation.xls'},
         {'line': 'SE21', 'file': 'Copy of SE 21 Formulation.xls'},
         {'line': 'SE25', 'file': '3d25b3b2-Copy_of_SE25_Formulation.xls'}]
    assert superseded_copies(B) == {'Copy of SE25 Formulation.xls', '3d25b3b2-Copy_of_SE25_Formulation.xls'}


# ---- daily packet -> checks -------------------------------------------------------------------------------------
# +2 each since 29 Sep 2026: Info notes for the replaced Q1203K and F1102K (checks.REPLACED)
@pytest.mark.parametrize('date,n_issues', [('2026-09-23', 84), ('2026-09-24', 73)])
def test_daily_checks_regression(date, n_issues, tmp_path):
    run('daily/checks.py', {'PKT_DATE': date}, tmp_path)
    issues = json.loads((tmp_path / 'work' / 'issues.json').read_text(encoding='utf-8'))['issues']
    assert len(issues) == n_issues


def test_daily_workbooks_build(tmp_path):
    run('daily/build_xlsx.py', {'PKT_DATE': '2026-09-24', 'RUN_DATE': '2026-09-24'}, tmp_path)
    from openpyxl import load_workbook
    wb = load_workbook(tmp_path / 'out' / 'FRM Formulation Report 2026-09-24.xlsx')
    hdr = [c.value for c in wb['Set Sums'][1]]
    assert hdr[-3:] == ['Dosing', 'Auto = balance (%)', 'Adds to 100?']
    for name in ('EXT Extrusion Schedule', 'CNV Converting Schedule'):
        assert (tmp_path / 'out' / f'{name} 2026-09-24.xlsx').exists()


# ---- calc workbooks (skipped when none are in CALC_DIR) ----------------------------------------------------------
@pytest.mark.skipif(not list(config.CALC_DIR.glob('*Formulation*.xls')), reason='no calc workbooks in CALC_DIR')
def test_calc_parse(tmp_path):
    run('calc/parse_fcal.py', {}, tmp_path)
    assert (tmp_path / 'work' / 'parsed.pkl').exists()


def test_records_append_only(tmp_path):
    """daily/record.py (28 Sep 2026): a date already recorded is skipped if identical, and STOPs if it differs."""
    import shutil
    from openpyxl import load_workbook
    pub, out = tmp_path / 'pub', tmp_path / 'out'
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PUBLISH_DIR=str(pub))
    rec = lambda *d: subprocess.run([sys.executable, str(ROOT / 'daily' / 'record.py'), *d], env=env,
                                    capture_output=True, text=True, cwd=ROOT)
    out.mkdir()
    r = rec('2026-09-23')
    assert r.returncode == 0, r.stdout + r.stderr
    ext = 'Extrusion Production Record.xlsx'
    (pub / 'Extrusion Schedule').mkdir(parents=True)
    shutil.copy(out / ext, pub / 'Extrusion Schedule' / ext)          # as if published
    r = rec('2026-09-23', '2026-09-24')
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'already recorded, identical' in r.stdout and '2026-09-24: 80 rows appended' in r.stdout
    rows = list(load_workbook(out / ext, read_only=True)['Orders by Day'].iter_rows(values_only=True))
    assert len(rows) == 1 + 82 + 80
    wb = load_workbook(pub / 'Extrusion Schedule' / ext)                 # someone edits a past row
    wb['Orders by Day']['F2'] = 1
    wb.save(pub / 'Extrusion Schedule' / ext)
    before = (out / ext).read_bytes()
    r = rec('2026-09-23')
    assert r.returncode == 1 and 'STOP' in r.stdout
    assert (out / ext).read_bytes() == before                           # nothing written


def test_master_change_control(tmp_path):
    """db/preflight.py (28 Sep 2026): an edit to the master without an approved Change Log row stops the run."""
    import shutil
    from openpyxl import load_workbook
    pub, out = tmp_path / 'pub', tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PUBLISH_DIR=str(pub),
               SNAP_DIR=str(tmp_path / 'snap'))
    py = lambda *a: subprocess.run([sys.executable, *a], env=env, capture_output=True, text=True, cwd=ROOT)
    r = py(str(ROOT / 'db' / 'seed_master.py'))
    if r.returncode and 'IWPFT062' in (r.stdout + r.stderr):
        pytest.skip('IWPFT062 not readable (missing, or locked: open in Word or syncing)')
    assert r.returncode == 0, r.stdout + r.stderr
    name = 'Formulation Master.xlsx'
    (pub / 'Formulation Data Base').mkdir(parents=True)
    master = pub / 'Formulation Data Base' / name
    shutil.copy(out / name, master)
    pf = lambda *a: py(str(ROOT / 'db' / 'preflight.py'), *a, name)
    assert pf('check').returncode == 2                          # no accepted version yet
    assert pf('accept', '--baseline').returncode == 0
    assert pf('check').returncode == 0                          # unchanged
    wb = load_workbook(master)                                  # Tech edits a setting, no log
    ws = wb['Line Settings']
    h = [c.value for c in ws[1]]
    ws.cell(2, h.index('Set') + 1).value = '99'
    key = '|'.join(str(ws.cell(2, h.index(k) + 1).value or '') for k in ('Line Code', 'Formula Code', 'Variant', 'Extruder', 'Feeder'))
    wb.save(master)
    r = pf('check')
    assert r.returncode == 1 and 'UNLOGGED' in r.stdout and 'STOP' in r.stdout
    wb = load_workbook(master)                                  # ... then logs it, with an approver
    wb['Change Log'].append([1, datetime_today(), 'Line Settings', key, 'Set', None, '99', 'test', 'Tech', 'Tech'])
    wb.save(master)
    r = pf('check')
    assert r.returncode == 0 and 'approved by Tech' in r.stdout, r.stdout
    assert pf('accept').returncode == 0 and pf('check').returncode == 0


def datetime_today():
    import datetime
    return datetime.date.today()
