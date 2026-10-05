"""One door for a day's schedule, whichever form it comes in (James Kuo, 5 Oct 2026: "make sure you can read PDF word file
as well. I want to be able to feed it in both way (scan and PDf doc) and have it able to process").

    python daily/intake.py <file.pdf> [<file.pdf> ...] [--date YYYY-MM-DD] [--step 1|2]

Each file is recognised by what is in it, not by its name:
  - ext-pdf: the system's extrusion report (text "PP PROFILE PRODUCTION INSTRUCTION - EXTRUSION", BPN9PFR$_*.PDF) -> the
    packet's EXT part from its text (daily/packet_from_pdf.py); the date is its Run Date;
  - cnv-pdf: the converting schedule printed from Excel ("Die Cutting Schedule MM-DD.pdf": text "PRODUCTION INSTRUCTIONS"
    with an Issue Date) -> the packet's converting pages from its text (daily/cnv_from_pdf.py);
  - scan: the copier's scan (pages are pictures, no text; doc<counter><YYYYMMDDhhmmss>.pdf) -> the scan reader: step 1
    daily/stage1_formulation.py (the formulation first), step 2 daily/stage2_records.py (every field, a draft to settle);
    the date from --date, else the scan time in the copier's file name.
Step 1 (default) gives the Word formulation for the floor: the EXT part (PDF) or the step-1 read (scan), then resolve.py,
auger_check.py and render_frm.py. Step 2 adds what the records need: the converting pages of a PDF, or the scan's full read.
A text PDF is never OCR'd, and a scan is never taken as exact: a scan's step 2 is a draft until its notes are settled.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

PY = sys.executable


def kind(pdf):
    """-> (kind, date or '') for one PDF: 'ext-pdf', 'cnv-pdf', 'scan' or 'unknown'."""
    d = pymupdf.open(str(pdf))
    text = ''.join(d[i].get_text() for i in range(min(2, d.page_count)))
    if 'PRODUCTION INSTRUCTION - EXTRUSION' in text:
        m = re.search(r'Run Date:\s*(\d{1,2})/(\d{1,2})/(\d{2})', text)
        return 'ext-pdf', f'20{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}' if m else ''
    if 'PRODUCTION INSTRUCTIONS' in text and 'Issue Date' in text:
        m = re.search(r'Issue Date:\s*(\d{1,2})/(\d{1,2})/(\d{4})', text)
        return 'cnv-pdf', f'{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}' if m else ''
    if len(text.strip()) < 50 and any(d[i].get_images() for i in range(min(2, d.page_count))):
        m = re.search(r'doc\d{6}(\d{4})(\d{2})(\d{2})\d{6}', Path(pdf).name)
        return 'scan', f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else ''
    return 'unknown', ''


def run(args, **env):
    r = subprocess.run([PY] + [str(a) for a in args], env=dict(os.environ, PYTHONUTF8='1', **env), text=True, capture_output=True)
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        raise SystemExit(f'{Path(str(args[0])).name} failed:\n{out}')
    return out


def formulation(date, stage1=False):
    """resolve -> auger check -> Word formulation for a date whose packet (or step-1 read) is in place."""
    env = {'PKT_DATE': date}
    if stage1:
        env['PKT_STAGE1'] = '1'
    for s in ('resolve.py', 'auger_check.py', 'render_frm.py'):
        out = run([ROOT / 'daily' / s], **env)
        print('  ', [l for l in out.splitlines() if l.strip()][-1])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+'); ap.add_argument('--date'); ap.add_argument('--step', type=int, default=1, choices=(1, 2))
    ap.add_argument('--force', action='store_true', help='replace a part of the packet already built from an earlier copy')
    a = ap.parse_args(argv)
    found = [(Path(f), *kind(f)) for f in a.files]
    for f, k, d in found:
        print(f'{f.name}: {k}' + (f', dated {d}' if d else ''))
        if k == 'unknown':
            raise SystemExit(f'{f.name}: neither the extrusion report, the converting schedule nor a scan - not processed')
    dates = {d for f, k, d in found if d}
    date = a.date or (dates.pop() if len(dates) == 1 else None)
    if not date:
        raise SystemExit(f'the files carry different or no dates ({sorted(dates)}): give --date')
    force = ['--force'] if a.force else []
    ext = [f for f, k, d in found if k == 'ext-pdf']
    cnv = [f for f, k, d in found if k == 'cnv-pdf']
    scans = [f for f, k, d in found if k == 'scan']
    if ext and scans:
        print('both the system report and a scan of the extrusion schedule: the report is exact, it is used for EXT')
    if ext:
        print(run([ROOT / 'daily' / 'packet_from_pdf.py', date, '--ext', ext[0]] + force).splitlines()[0])
        if a.step == 1:
            formulation(date)
    elif scans and a.step == 1:
        if config.packet_path(date).exists():
            print(f'{config.packet_path(date).name} is already built: the formulation from it')
            formulation(date)
        else:
            out = run([ROOT / 'daily' / 'stage1_formulation.py', scans[0], '--date', date]).splitlines()
            for l in out:
                if l.startswith(('step 1 done', 'C:', '/')) or 'for an engineer' in l:
                    print('  ', l)
    if a.step == 2:
        if cnv:
            print(run([ROOT / 'daily' / 'packet_from_pdf.py', date, '--cnv', cnv[0]] + force).splitlines()[0])
        if scans and not ext:
            print(run([ROOT / 'daily' / 'stage2_records.py', scans[0], '--date', date]).splitlines()[0])
            print('   the scan read is a draft (work/stage2): settle its notes, then save it to data/packets (CLAUDE.md)')
        elif scans:
            print('   the scan adds only its handwriting and converting pages to the exact report: read those by eye')
    out = config.OUTPUT_DIR / f'FRM Formulation {date}.docx'
    if a.step == 1 and out.exists():
        print(f'Word formulation for the floor: {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
