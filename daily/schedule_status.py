"""Where a day's schedule run stands, for the scheduled email run (James Kuo, 6 Oct 2026: "check my email everyday for
schedule from JVallejo@wpjk.inteplast.com" ... "Full run, stop on new High" ... "Every 30 min, 11:00-16:00").

    python daily/schedule_status.py [<date>]        (default today)

Looks only at the schedule PDFs in Downloads (BPN9PFR$_*.PDF and "Die Cutting Schedule *.pdf", as the emails name them;
never the copier's doc*.pdf scans or anything else there), at the packet, the Word formulation and the publish manifest.
Prints what was found and one last line "next: <step>":
  wait-ext      the extrusion schedule has not come yet
  step1         build the Word formulation (daily/intake.py <ext pdf>)
  step1-resent  a different extrusion PDF came for a day whose formulation was built: rebuild with --force (records
                not published yet), tell James the floor copy changed
  ask-james     a different extrusion or converting PDF came after the day was published: records stay as issued
  wait-cnv      the formulation is out; the converting schedule has not come yet
  step2         add the converting pages (daily/intake.py <cnv pdf> --step 2), then the Daily run from step 3
  step2-resent  a different converting PDF came before the day was published: replace the pages with --force
  daily-run     the packet is complete; the Daily run from step 3 (manual issues ... publish) is not done
  interface     published; the interface copy (Daily run step 9) is not
  done          nothing left for the day
"""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'daily'))
import config  # noqa: E402
from intake import kind  # noqa: E402

DOWNLOADS = Path.home() / 'Downloads'
NAMES = ('BPN9PFR$_*.PDF', 'BPN9PFR$_*.pdf', 'Die Cutting Schedule *.pdf', 'Die Cutting Schedule *.PDF')


def schedule_pdfs(date, folder=DOWNLOADS, days=4):
    """-> {'ext-pdf': [newest first], 'cnv-pdf': [...]} of the schedule PDFs in the folder dated `date`."""
    since = datetime.datetime.now().timestamp() - days * 86400
    seen, out = set(), {'ext-pdf': [], 'cnv-pdf': []}
    for pat in NAMES:
        for f in folder.glob(pat):
            if f in seen or f.stat().st_mtime < since or 'password' in f.name.lower():
                continue
            seen.add(f)
            try:
                k, d = kind(f)
            except Exception:
                continue
            if d == date and k in out:
                out[k].append(f)
    for k in out:
        out[k].sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return out


def published(date):
    m = json.loads((ROOT / 'data' / 'published_manifest.json').read_text(encoding='utf-8'))
    names = {Path(k).name for k in m}
    return {'workbooks': f'EXT Extrusion Schedule {date}.xlsx' in names and f'CNV Converting Schedule {date}.xlsx' in names,
            'interface': f'Profile Formulation {date}.html' in names}


def status(date):
    pdfs = schedule_pdfs(date)
    pp = config.packet_path(date)
    pk = json.loads(pp.read_text(encoding='utf-8')) if pp.exists() else {}
    word = config.OUTPUT_DIR / f'FRM Formulation {date}.docx'
    pub = published(date)
    ext, cnv = pdfs['ext-pdf'], pdfs['cnv-pdf']
    s = {'date': date, 'ext_pdf': [f.name for f in ext], 'cnv_pdf': [f.name for f in cnv],
         'packet_ext_from': pk.get('source_scan', '') if pk.get('ext') else '',
         'packet_cnv_from': (pk.get('cnv_source') or '(earlier build)') if pk.get('cnv') else '',
         'word': word.exists(), 'published': pub['workbooks'], 'interface_copy': pub['interface']}
    if not ext:
        nxt = 'wait-ext' if not pk.get('ext') else ('wait-cnv' if not pk.get('cnv') else '')
    elif not pk.get('ext') or not word.exists():
        nxt = 'step1'
    elif ext[0].name != s['packet_ext_from']:
        nxt = 'ask-james' if pub['workbooks'] else 'step1-resent'
    else:
        nxt = ''
    if not nxt:
        if not pk.get('cnv'):
            nxt = 'step2' if cnv else 'wait-cnv'
        elif cnv and pk.get('cnv_source') and cnv[0].name != pk['cnv_source']:
            nxt = 'ask-james' if pub['workbooks'] else 'step2-resent'
        elif not pub['workbooks']:
            nxt = 'daily-run'
        elif not pub['interface']:
            nxt = 'interface'
        else:
            nxt = 'done'
    s['next'] = nxt
    return s


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    s = status(d)
    for k, v in s.items():
        if k != 'next':
            print(f'{k}: {v}')
    print(f"next: {s['next']}")
