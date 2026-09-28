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
@pytest.mark.parametrize('date,n_issues', [('2026-09-23', 82), ('2026-09-24', 71)])
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
