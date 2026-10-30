"""The help loop, Claude's side (James Kuo, 30 Oct 2026: "yes build it"; the QC Master's design, its handoff 5.2).

The interface page sends the rows its scan reader could not settle to the artifact's database:
    scans/<scanId>              schedule date, file, rows, boxed, help ('asked' / 'answered'), outcomes
    scans/<scanId>/help/<row>   line, page, order / prod as read, raw, why, hint, img (JPEG data URL), then
                                answer {order, prod, notOrder, note, by, at} (Claude) and confirmed {.., outcome} (person)
Claude fetches them with the ArtifactData tool, `out_dir` = work/help/db (the pictures stay out of the conversation), then:

    python ui/help_rows.py show work/help/db      every open row: what the readers saw, the picture saved as a .jpg to Read
    python ui/help_rows.py log --scan S --row R --order O --prod P --outcome right|miss|WRONG-ACCEPTED --why "..."

Read each picture by eye (the original scan in Downloads too, when James sent it), answer with ArtifactData `update` on
scans/<scanId>/help/<row> {answer: {...}} pinned to its version, set scans/<scanId> help: 'answered', and log the case.
WRONG-ACCEPTED (the page took a reading that was wrong) must never happen; a repeated cause is the next reader fix
(ui/ocr_eval.py first, parity 0, the scan becomes a test in tests/test_scan_reader_page.py).
"""
import argparse
import base64
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'work' / 'help' / 'reader_cases.jsonl'


def show(db_dir):
    scans = Path(db_dir) / 'scans'
    n = 0
    for head in sorted(scans.glob('*.json')):
        s = json.loads(head.read_text(encoding='utf-8'))
        body = s.get('data', s)
        rows = sorted((scans / head.stem / 'help').glob('*.json'))
        if not rows:
            continue
        print(f"== {head.stem}: schedule {body.get('date')} · {body.get('source')} · {body.get('rows')} rows, "
              f"{body.get('boxed')} boxed · help {body.get('help')} · outcomes {body.get('outcomes', {})}")
        for f in rows:
            r = json.loads(f.read_text(encoding='utf-8'))
            d = r.get('data', r)
            img = d.get('img') or ''
            pic = ''
            if img.startswith('data:image/'):
                pic = f.with_suffix('.jpg')
                pic.write_bytes(base64.b64decode(img.split(',', 1)[1]))
            state = ('confirmed ' + d['confirmed'].get('outcome', '')) if d.get('confirmed') else (
                'answered' if d.get('answer') else 'OPEN')
            n += state == 'OPEN'
            print(f"  {f.stem} [{state}] {d.get('line')} p{d.get('page')} {d.get('kind')}: {d.get('order')} · {d.get('prod')}"
                  f" | read as {d.get('raw')!r} | {d.get('why')}" + (f" | closest on file {d.get('hint')}" if d.get('hint') else '')
                  + (f" | answer {d['answer']}" if d.get('answer') else '') + (f"\n      picture {pic}" if pic else ''))
    print(f'{n} open row(s)')


def log(a):
    CASES.parent.mkdir(parents=True, exist_ok=True)
    rec = {'at': datetime.datetime.now().isoformat(timespec='seconds'), 'scan': a.scan, 'row': a.row, 'order': a.order,
           'prod': a.prod, 'outcome': a.outcome, 'why': a.why}
    with CASES.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print('logged', rec)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('show'); s.add_argument('db_dir')
    g = sub.add_parser('log')
    for k in ('scan', 'row', 'order', 'prod', 'why'):
        g.add_argument('--' + k, default='')
    g.add_argument('--outcome', required=True, choices=['right', 'miss', 'WRONG-ACCEPTED'])
    a = ap.parse_args()
    show(a.db_dir) if a.cmd == 'show' else log(a)
    sys.exit(0)
