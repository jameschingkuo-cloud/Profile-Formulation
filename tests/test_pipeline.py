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


def test_draft_keeps_every_formulation(tmp_path):
    """James, 29 Sep 2026: reclaim first, then virgin -- when a formulation is given, give all of them, in run order. James,
    30 Sep 2026: "the one with reclaim first. we always want to use up our scrap first before using Virgin PP" -- a formula
    with reclaim runs before one without, whatever order the page lists them (H68A053-1: FU0061WBD before FU0001WBD)."""
    from openpyxl import load_workbook
    out = tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PKT_DATE='2026-09-28', HISTORY_BEFORE='2026-09-28')
    r = subprocess.run([sys.executable, str(ROOT / 'daily' / 'resolve.py')], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = list(load_workbook(out / 'FRM Draft 2026-09-28.xlsx', read_only=True)['Draft'].iter_rows(values_only=True))
    h = list(rows[0])
    got = {}
    for x in rows[1:]:
        d = dict(zip(h, x))
        got.setdefault((d['Line Code'], d['Order']), {})[d['Formula Row']] = d['Formula Code']
    issued = {}                                    # latest issue before 28 Sep wins, as in resolve.issued_history
    for d in ('2026-09-23', '2026-09-24', '2026-09-25'):
        pk = json.loads((ROOT / 'data' / 'packets' / f'packet_{d}.json').read_text(encoding='utf-8'))
        issued.update({(pg['line_code'], o): [f['formula_code'] for f in run_order(g['formulas'])]
                       for pg in pk['frm'] for g in pg['groups'] for o in g['orders']})
    multi = 0
    for k, rowmap in got.items():
        want = issued[k]
        assert [rowmap[i] for i in sorted(rowmap)] == want, (k, rowmap, want)
        multi += len(want) > 1
    assert multi >= 5          # RP26311-1 (3 formulas), RP26512-1 (3), RP26731-2, RP26902-1, H68A111-4/-5, H69A097-1 ...
    assert [got[('SE22', 'H68A053-1')][i] for i in sorted(got[('SE22', 'H68A053-1')])] == ['FU0061WBD', 'FU0001WBD']   # reclaim 99 first


def run_order(formulas):
    """Independent of daily/resolve.py: reclaim (set > 0) first, a 'run out' note last, page order otherwise."""
    rec = lambda f: any('reclaim' in (v.get('material') or '').lower() and float(str(v.get('set') or 0).replace(',', '') or 0) > 0
                        for v in f['feeders'].values())
    out = lambda f: 'run out' in (f.get('note') or '').lower()
    return sorted(formulas, key=lambda f: (out(f), not rec(f)))


def test_print_formulation_docx(tmp_path):
    """daily/render_frm.py (29 Sep 2026): the Word formulation for the floor. One page per line, every formulation,
    exceptions blank for an engineer (never a suggestion), replaced materials printed as what to load."""
    from docx import Document
    out = tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PKT_DATE='2026-09-28', HISTORY_BEFORE='2026-09-28')
    for script in ('resolve.py', 'render_frm.py'):
        r = subprocess.run([sys.executable, str(ROOT / 'daily' / script)], env=env, capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0, r.stdout + r.stderr
    doc = Document(out / 'FRM Formulation 2026-09-28.docx')
    text = '\n'.join(p.text for p in doc.paragraphs)
    cells = [c.text for t in doc.tables for row in t.rows for c in row.cells]
    assert sum(1 for p in doc.paragraphs if p.text.startswith('Line ') and p.text.endswith('Formulations')) == 13
    assert 'DRAFT' in ' '.join(cells) and 'DRAFT' in doc.sections[0].header.paragraphs[0].text
    rows = [row for t in doc.tables for row in t.rows]
    assert sum(any('ENGINEER TO COMPLETE' in c.text for c in row.cells) for row in rows) == 16   # the 16 Exceptions
    assert any('F1203K' in c and 'replaces Q1203K' in c for c in cells)           # SE42 V3
    assert not any('XO-256' in c for c in cells) and any('X0-256' in c for c in cells)
    assert any('If reclaim runs out' in c for c in cells) and any('Run first' in c for c in cells)
    for row in rows:                                                          # an exception is never filled from a suggestion
        if row.cells[0].text.startswith('RP26928-1'):
            assert any('ENGINEER TO COMPLETE' in c.text for c in row.cells) and not any('FUA060WBA' in c.text for c in row.cells)


def test_engineer_decision_fills_the_rerun(tmp_path):
    """James, 29 Sep 2026: an Exception is completed by an engineer in the database, then the run is repeated.
    db/assign_formula.py approves Product to Formula rows (logged); resolve.py then fills the order, every formulation."""
    import shutil
    from openpyxl import load_workbook
    pub, out = tmp_path / 'pub', tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PUBLISH_DIR=str(pub),
               SNAP_DIR=str(tmp_path / 'snap'), PKT_DATE='2026-09-28', HISTORY_BEFORE='2026-09-28')
    py = lambda *a: subprocess.run([sys.executable, *a], env=env, capture_output=True, text=True, cwd=ROOT)
    name = 'Formulation Master.xlsx'
    live = config.published_path(name)                       # a copy of the published master (read only)
    if not (live and live.exists()):
        pytest.skip('Formulation Master not published on this PC')
    (pub / 'Formulation Data Base').mkdir(parents=True)
    shutil.copy(live, pub / 'Formulation Data Base' / name)
    assert py(str(ROOT / 'db' / 'preflight.py'), 'accept', name, '--baseline').returncode == 0

    def exceptions():
        assert py(str(ROOT / 'daily' / 'resolve.py')).returncode == 0
        wb = load_workbook(out / 'FRM Draft 2026-09-28.xlsx', read_only=True)
        exc = [x[1] for x in list(wb['Exceptions'].iter_rows(values_only=True))[1:]]
        draft = [x for x in list(wb['Draft'].iter_rows(values_only=True))[1:] if x[1] == 'RP26928-1']
        return exc, draft
    exc, draft = exceptions()
    assert 'RP26928-1' in exc and not draft                     # Draft rows in the master are not used
    r = py(str(ROOT / 'db' / 'assign_formula.py'), '--line', 'SE22', '--product', 'RPAA0WB318', '--by', 'Test', '--why', 'test',
           '--formula', 'FUA060WBA', 'Primary', '--formula', 'FUA060WBA', 'Other', '--formula', 'FUA010WBA', 'Reclaim run-out')
    assert r.returncode == 0, r.stdout + r.stderr
    shutil.copy(out / name, pub / 'Formulation Data Base' / name)   # as publish.py would
    assert py(str(ROOT / 'db' / 'preflight.py'), 'accept', name).returncode == 0
    exc, draft = exceptions()
    assert 'RP26928-1' not in exc
    assert [c for c in dict.fromkeys((x[14], x[3], x[4]) for x in draft)] == \
        [(1, 'FUA060WBA', 'Primary'), (2, 'FUA060WBA', 'Other'), (3, 'FUA010WBA', 'Reclaim run-out')]
    assert all(x[11] == 'Product to Formula' for x in draft)


def test_reader_header_anchor_survives_rod():
    """Tesseract 5.4 (29 Sep 2026) reads the 'Prod' header as 'ROD' on some pages; the columns must still be found,
    at the same x as when 'Prod' and 'Weight' are both read."""
    sys.path.insert(0, str(ROOT / 'scan_reader'))
    pytest.importorskip('cv2'); pytest.importorskip('pytesseract')
    import ext_scan_reader as e
    words = [('Mfg#', 274), ('Prod', 500), ('Die', 725), ('Thk', 1517), ('GSM', 1607), ('Total', 2040), ('Weight', 2688)]
    line = lambda ws: [[(x, 300, 40, 20, w) for w, x in ws]]
    good, _ = e.anchors(line(words))
    rod, _ = e.anchors(line([('ROD' if w == 'Prod' else w, x) for w, x in words]))
    no_weight, _ = e.anchors(line([(w, x) for w, x in words if w not in ('Prod', 'Weight')]))
    assert good and rod and no_weight is None
    assert all(abs(good(k) - rod(k)) <= 1 for k in e.REF)


def test_import_frm_adds_only_what_is_missing(tmp_path):
    """James, 29 Sep 2026 (Tech's FRM): "update your data base with it". db/import_frm.py adds the day's new formulas as
    logged Draft rows; a second run adds nothing; a material with no mapping (DOW-C104) is never written."""
    import shutil
    pub, out = tmp_path / 'pub', tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PUBLISH_DIR=str(pub),
               SNAP_DIR=str(tmp_path / 'snap'))
    py = lambda *a: subprocess.run([sys.executable, *a], env=env, capture_output=True, text=True, cwd=ROOT)
    name = 'Formulation Master.xlsx'
    live = config.published_path(name)
    if not (live and live.exists()):
        pytest.skip('Formulation Master not published on this PC')
    (pub / 'Formulation Data Base').mkdir(parents=True)
    shutil.copy(live, pub / 'Formulation Data Base' / name)
    assert py(str(ROOT / 'db' / 'preflight.py'), 'accept', name, '--baseline').returncode == 0
    r = py(str(ROOT / 'db' / 'import_frm.py'), '--date', '2026-09-29', '--by', 'test', '--why', 'test', '--dry-run')
    assert r.returncode == 0, r.stderr
    assert 'DIFFERS' not in r.stdout                                   # retired spellings do not shadow active ones
    # "PP Virgin-silo 3 (DOW-C104)" is F6502A (James Kuo, 30 Sep 2026: "thats F6502A. just old formulation where we used to use
    # Dow plastic"; master Change 264), so every material on Tech's 29 Sep pages is mapped and FU0012BL5 is complete (Change 265)
    assert [l for l in r.stdout.splitlines() if l.startswith('NOT WRITTEN')] == []


def test_past_schedule_gets_the_latest_formulation(tmp_path):
    """James, 30 Sep 2026: "Always provide up to date formulation. even if someone give you an past schedule." The 29 Sep
    schedule, run again after Tech's 29 Sep FRM is on file, gets that formulation for the four new orders."""
    from openpyxl import load_workbook
    out = tmp_path / 'out'
    out.mkdir()
    env = dict(os.environ, PYTHONUTF8='1', WORK_DIR=str(tmp_path / 'work'), OUTPUT_DIR=str(out), PKT_DATE='2026-09-29')
    env.pop('HISTORY_BEFORE', None)
    r = subprocess.run([sys.executable, str(ROOT / 'daily' / 'resolve.py')], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    wb = load_workbook(out / 'FRM Draft 2026-09-29.xlsx', read_only=True)
    exc = [x[1] for x in list(wb['Exceptions'].iter_rows(values_only=True))[1:]]
    got = {x[1]: x[3] for x in list(wb['Draft'].iter_rows(values_only=True))[1:]}
    assert exc == []
    assert got['H69A203-1'] == 'FU0012BL5' and got['H67A164-2'] == 'FU0001RF6' and got['H67A164-1'] == 'FU0070KS6'
    assert got['RP26604-1'] == 'FUA152WB4'
