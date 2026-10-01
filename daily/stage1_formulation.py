"""Step 1 of a day's scan: the formulation to the production team first (James Kuo, 1 Oct 2026: "do read all. But make it
two step. Get the fomulation to production team first. then read the rest for the data base update (Production Record)"
- "this will reduce the wait time").

    python daily/stage1_formulation.py <scan.pdf> [--date YYYY-MM-DD] [--workers N]
    python daily/stage1_formulation.py --compare YYYY-MM-DD      # after step 2: did step 1 send the right orders?

Reads only what the formulation needs - each extrusion record's line, order, product (and die, thickness, GSM, spec,
colours for the checks) - with the pages read in parallel and without the slower per-record instruction read; runs the
logic checks (scan_reader/validate_read.py); writes a step-1 packet to STAGE1_DIR (work/stage1/packet_<date>.json,
"stage": 1) and runs resolve.py, auger_check.py and render_frm.py (PKT_STAGE1=1) -> out/FRM Formulation <date>.docx for the
production team. A row whose order or product the checks cannot confirm is an Exception ("check the order and product on
the paper"), never a formula from a guess. The step-1 packet stays out of data/packets: the Production Records, the masters
and the reader's evaluation never take a machine read as a transcription. Step 2 (the full read, data/packets) follows;
--compare then lists every key field where step 1 differed, so a wrong formulation sent in step 1 is caught and re-issued.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scan_reader'))
import config  # noqa: E402

CERTAIN_FAIL = ('breaks the order rule and no single order', "breaks the code rule: check by eye")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('scan', nargs='?'); ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--workers', type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    ap.add_argument('--compare', metavar='DATE')
    a = ap.parse_args(argv)
    if a.compare:
        return compare(a.compare)
    if not a.scan:
        ap.error('the scan PDF is needed')
    if config.packet_path(a.date).exists():
        raise SystemExit(f'{config.packet_path(a.date).name} is already transcribed (step 2 done): run resolve.py / '
                         f'render_frm.py on it (PKT_DATE={a.date}), not step 1.')
    import ext_scan_reader as R
    import validate_read as V
    t0 = time.time()
    config.record_read(a.scan, 'daily schedule scan (step 1: formulation)')
    rows = R.read_scan(a.scan, R.Bank.load(str(ROOT / 'scan_reader' / 'glyph_bank.npz')), instructions_crop=False, workers=a.workers)
    t_read = time.time() - t0
    out, dropped, gone, prev_day = V.validate(a.date, rows)
    pages = OrderedDict()
    n_check = 0
    for r in out:
        sure_o, sure_p = V.ok_order(r['order'], datetime.date.fromisoformat(a.date)), V.ok_prod(r['prod'])
        unresolved = [c for c in (r.get('checks') or '').split('; ') if any(k in c for k in CERTAIN_FAIL)]
        read_check = '; '.join(unresolved) or ('' if sure_o and sure_p else f"read '{r['order']}' / '{r['prod']}'")
        n_check += bool(read_check)
        pg = pages.setdefault((int(r['scan_page']), r['line']), {'scan_page': int(r['scan_page']), 'report_page': r['report_page'],
                                                                 'line': r['line'], 'rows': [], 'page_notes': 'step 1: read from the scan'})
        pg['rows'].append({'T': '', 'order': r['order'], 'prod_code': r['prod'], 'die': r['die'], 'thk': r['thk'], 'gsm': f"{int(r['gsm']):,}" if str(r['gsm'] or '').isdigit() else r['gsm'],
                           'mat_spec': ' '.join(x for x in (r['mat'], r['grade'], r['spec']) if x), 'colors': r['colors'],
                           'special_instructions': r.get('special', ''), 'cut_rows': [], 'handwritten': '',
                           'unclear': '; '.join(x for x in (r.get('checks'), r.get('flags')) if x), 'read_check': read_check})
    pk = {'packet_date': a.date, 'source_scan': Path(a.scan).name, 'stage': 1, 'ext': list(pages.values()), 'cnv': [], 'frm': [],
          'frm_source_scan': '',
          'stage1': {'read_seconds': round(t_read), 'workers': a.workers, 'rows': len(out), 'rows_to_check': n_check,
                     'dropped': [list(x) for x in dropped], 'previous_day': prev_day,
                     'not_read_today': [f'{l} {o}' for l, o in gone]}}
    config.STAGE1_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.STAGE1_DIR / f'packet_{a.date}.json'
    dest.write_text(json.dumps(pk, ensure_ascii=False, indent=1), encoding='utf-8')
    env = dict(os.environ, PKT_DATE=a.date, PKT_STAGE1='1', PYTHONUTF8='1')
    for script in ('resolve.py', 'auger_check.py', 'render_frm.py'):
        r = subprocess.run([sys.executable, str(ROOT / 'daily' / script)], env=env, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f'{script} failed:\n{r.stdout}\n{r.stderr}')
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else script)
    print(f'step 1 done in {time.time() - t0:.0f} s (read {t_read:.0f} s, {a.workers} workers): {len(out)} orders, '
          f'{n_check} to check on paper, {len(dropped)} handwriting rows dropped; packet {dest}')
    for r in out:
        if r.get('checks'):
            print('  ', r['line'], r['order'], '|', r['checks'][:200])


KEYS = ('order', 'prod_code', 'die', 'thk', 'gsm', 'mat_spec', 'colors')


def compare(date):
    """Step 1 against the full packet of the same day (step 2): the orders and products the step-1 formulation was built
    from. A difference in line, order or product means the step-1 Word file must be re-issued from the full packet."""
    s1p, full = config.STAGE1_DIR / f'packet_{date}.json', config.packet_path(date)
    if not s1p.exists() or not full.exists():
        raise SystemExit(f'need both {s1p} and {full}')
    rows = lambda pk: [(pg['line'], r) for pg in pk['ext'] for r in pg['rows']]
    a, b = rows(json.loads(s1p.read_text(encoding='utf-8'))), rows(json.loads(full.read_text(encoding='utf-8')))
    fb = {(l, r['order']): r for l, r in b}
    bad, other = [], []
    for l, r in a:
        t = fb.pop((l, r['order']), None)
        if t is None:
            bad.append(f"{l} {r['order']} {r['prod_code']}: step 1 read this order; the full read has no such order on {l}")
            continue
        for k in KEYS[1:]:
            x, y = str(r.get(k, '')).replace(',', ''), str(t.get(k, '')).replace(',', '')
            if k == 'thk' and x and y:
                x, y = f'{float(x):.1f}', f'{float(y):.1f}'
            if x != y:
                (bad if k == 'prod_code' else other).append(f"{l} {r['order']}: {k} step 1 '{r.get(k, '')}', full read '{t.get(k, '')}'")
    bad += [f"{l} {o}: in the full read, not read in step 1" for (l, o) in fb]
    print(f'step 1 vs full packet {date}: {len(a)} / {len(b)} orders')
    print(f'  re-issue the formulation: {len(bad)}' if bad else '  line, order and product all match: the step-1 formulation stands')
    for x in bad:
        print('   ', x)
    if other:
        print(f'  other key fields that differ ({len(other)}; the formulation does not use them):')
        for x in other:
            print('   ', x)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
