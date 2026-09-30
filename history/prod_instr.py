"""Past extrusion schedules from the AIX system's own PDFs ("PP PROFILE PRODUCTION INSTRUCTION - EXTRUSION", report
WPPPOPRC, printed by afp2pdf in Courier), in Technical Engineering Team/Production Instruction (James Kuo, 30 Sep 2026:
"i got the past production schedule and put it into this folder. Go through and refine your data base").

The PDFs hold the exact text of the report that is printed and scanned each day, so no OCR is needed: each page is
rebuilt as its line-printer text (Courier, 4.8 pt per character, 12 pt per line) and parsed by its '|' columns.

    python history/prod_instr.py parse [folder]     -> work/history/ext_history.csv (+ files.csv: one row per PDF)
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

FOLDER = Path(r'C:\Users\JamesKuo\Inteplast-WPJK\Profile Process Control - Documents\Technical Engineering Team\Production Instruction')
NAME_RX = re.compile(r'^(\d\d)(\d\d)(\d\d)(?:-(\d))?\.pdf$', re.I)        # MMDDYY[-n].pdf
FIELDS = ['date', 'file', 'run_date', 'run_time', 'page', 'line', 't', 'order', 'order_base', 'suffix', 'prod_code', 'die',
          'width', 'length', 'mat', 'mat_spec', 'colour', 'thk', 'gsm', 'cut_width', 'cut_length', 'total_sheets', 'pack',
          'plts', 'pcs_stack', 'stk_plt', 'weight_lbs', 'instr_date', 'web_width', 'special']
ROW_RX = re.compile(r'^\|\s*([A-Z]?)\s*\|\s*([A-Z0-9]{7})\s*-\s*(\d{1,3})\s*\|')
SPEC_RX = re.compile(r'^(\S+)\s+(\S+)\s+(\S+)\s+(.*?)\s+(\d+(?:\.\d+)?)\s+(\d[\d,]*)$')


def grid(page):
    """The page as its line-printer text (overstruck underlines dropped where a character is printed)."""
    rows = {}
    for x0, y0, x1, y1, w, *_ in page.get_text('words'):
        r = round((y0 - 4.5) / 12)
        c = round((x0 - 4.8) / 4.8)
        line = rows.setdefault(r, {})
        for k, ch in enumerate(w):
            if ch == '_' and line.get(c + k, ' ') not in (' ', '_'):
                continue
            line[c + k] = ch
    if not rows:
        return []
    return [''.join(rows[r].get(c, ' ') for c in range(max(rows[r]) + 1)) if rows.get(r) else '' for r in range(max(rows) + 1)]


def num(s):
    s = (s or '').replace(',', '').strip()
    try:
        return float(s) if '.' in s else int(s)
    except ValueError:
        return s


def parse_pdf(path):
    """-> (info, rows). info: run date/time, pages, title(s), lines; rows: one dict per order row (FIELDS)."""
    d = pymupdf.open(path)
    info = {'file': path.name, 'pages': d.page_count, 'titles': set(), 'run_date': '', 'run_time': '', 'lines': [], 'rows': 0,
            'odd': [], 'footers': {}}
    rows = []
    for pno in range(d.page_count):
        g = grid(d[pno])
        if not g:
            continue
        head = g[0]
        m = re.search(r'(PP PROFILE PRODUCTION INSTRUCTION - \w+)', head)
        info['titles'].add(m.group(1) if m else head[:90].strip())
        m = re.search(r'Run Date:\s*(\d{1,2}/\d\d/\d\d)\s+(\d\d:\d\d:\d\d)', head)
        if m:
            info['run_date'], info['run_time'] = m.group(1), m.group(2)
        line = ''
        for L in g[1:4]:
            m = re.search(r'LINE NO:\s*(\S+)', L)
            if m:
                line = m.group(1)
        if line and line not in info['lines']:
            info['lines'].append(line)
        for L in g:
            m = re.search(r'LINE NO\.\s*(\S+)', L)
            if m:
                info['footers'][m.group(1)] = pno + 1
        i = 0
        while i < len(g):
            m = ROW_RX.match(g[i])
            if not m:
                i += 1
                continue
            cells = g[i].split('|')
            r = {k: '' for k in FIELDS}
            r.update(file=path.name, run_date=info['run_date'], run_time=info['run_time'], page=pno + 1, line=line,
                     t=m.group(1), order_base=m.group(2), suffix=m.group(3), order=f'{m.group(2)}-{m.group(3)}')
            try:
                r['prod_code'], r['die'] = cells[3].strip(), cells[4].strip()
                ao = cells[5]
                r['width'], r['length'] = ao[1:11].strip(), ao[11:].strip()
                sp = SPEC_RX.match(cells[6].strip())
                if sp:
                    r['mat'], r['mat_spec'], r['colour'] = sp.group(1) + ' ' + sp.group(2), sp.group(3), sp.group(4)
                    r['thk'], r['gsm'] = num(sp.group(5)), num(sp.group(6))
                else:
                    info['odd'].append(f'p{pno + 1} {r["order"]} spec "{cells[6].strip()}"')
                cd = cells[7]
                r['cut_width'], r['cut_length'] = cd[1:11].strip(), cd[11:].strip()
                r['total_sheets'], r['pack'], r['plts'] = num(cells[8]), cells[9].strip(), num(cells[10])
                ps = cells[11].split()
                r['pcs_stack'] = num(ps[0]) if ps else ''
                r['stk_plt'] = num(ps[1]) if len(ps) > 1 else ''
                r['weight_lbs'], r['instr_date'], r['web_width'] = num(cells[12]), cells[13].strip(), cells[14].strip()
            except IndexError as e:
                info['odd'].append(f'p{pno + 1} {r["order"]}: {e}')
            sp_lines, j = [], i + 1                      # special instructions: until the block's closing line
            while j < len(g) and not g[j].startswith('|___') and not ROW_RX.match(g[j]):
                t = g[j].strip().strip('|').strip()
                if 'Special_Instructions:' in t:
                    t = t.split('Special_Instructions:', 1)[1].strip()
                    sp_lines.append(t)
                elif sp_lines and t and not set(t) <= set('-_ '):
                    sp_lines.append(t)
                j += 1
            r['special'] = ' / '.join(s for s in sp_lines if s)
            rows.append(r)
            i = j
    info['rows'] = len(rows)
    info['titles'] = ' ; '.join(sorted(info['titles']))
    return info, rows


def file_date(name):
    m = NAME_RX.match(name)
    if not m:
        return None
    try:
        return date(2000 + int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None


def parse_folder(folder=FOLDER, out_dir=None):
    out_dir = Path(out_dir or config.WORK_DIR / 'history')
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted((p for p in Path(folder).iterdir() if p.is_file() and NAME_RX.match(p.name)),
                   key=lambda p: (file_date(p.name) or date.min, p.name))
    infos, n = [], 0
    with open(out_dir / 'ext_history.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for p in files:
            dte = file_date(p.name)
            try:
                info, rows = parse_pdf(p)
            except Exception as e:                       # a damaged or non-report PDF: listed, never guessed
                infos.append({'file': p.name, 'date': str(dte), 'error': repr(e)})
                continue
            info['date'] = str(dte)
            for r in rows:
                r['date'] = str(dte)
                w.writerow(r)
            n += len(rows)
            info['odd'] = ' ; '.join(info['odd'][:5])
            info['lines'] = ' '.join(info['lines'])
            info['footers'] = ' '.join(sorted(info['footers']))
            infos.append(info)
    keys = ['file', 'date', 'run_date', 'run_time', 'pages', 'lines', 'footers', 'rows', 'titles', 'odd', 'error']
    with open(out_dir / 'files.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(infos)
    return len(files), n, out_dir


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'parse':
        print(parse_folder(sys.argv[2] if len(sys.argv) > 2 else FOLDER))
    else:
        print(__doc__)
