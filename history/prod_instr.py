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
from datetime import date, datetime
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

FOLDER = Path(r'C:\Users\JamesKuo\Inteplast-WPJK\Profile Process Control - Documents\Technical Engineering Team\Production Instruction')
NAME_RX = re.compile(r'^(\d\d)(\d\d)(\d\d)(?:-(\d))?\.pdf$', re.I)        # MMDDYY[-n].pdf
FIELDS = ['date', 'file', 'run_date', 'run_time', 'page', 'line', 't', 'order', 'order_base', 'suffix', 'prod_code', 'die',
          'width', 'length', 'mat', 'mat_spec', 'colour', 'thk', 'gsm', 'cut_width', 'cut_length', 'total_sheets', 'pack',
          'plts', 'pcs_stack', 'stk_plt', 'weight_lbs', 'instr_date', 'web_width', 'special', 'cut_rows']
ROW_RX = re.compile(r'^\|\s*([A-Z]?)\s*\|\s*([A-Z0-9]{7})\s*-\s*(\d{1,3})\s*\|')
CUT_RX = re.compile(r'^\|[\s-]*\|\s*[\d /]+\|\s*([\d,]+)\s*\|')    # '| ---- | 31 5/8    34 7/8    |  34,675 |'
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


def grid_any(page):
    """The page as its line-printer text from each character's origin and writing direction: for a print laid on its
    side (111723.PDF, 17 Nov 2023, sent through another mail system: characters run up the page, smaller pitch). The
    character pitch and line pitch are measured on the page."""
    chars, runs = [], []
    for b in page.get_text('rawdict')['blocks']:
        for ln in b.get('lines', []):
            dx, dy = ln['dir']
            run = []
            for sp in ln['spans']:
                for c in sp['chars']:
                    ox, oy = c['origin']
                    run.append((ox * dx + oy * dy, -ox * dy + oy * dx, c['c']))
            chars += run
            runs.append(run)
    if not chars:
        return []
    longest = max(runs, key=len)                                 # one character per step, spaces included: exact pitch
    pu = (longest[-1][0] - longest[0][0]) / (len(longest) - 1)
    vs = sorted({round(v, 1) for u, v, c in chars})
    dv = sorted(b - a for a, b in zip(vs, vs[1:]) if b - a > 0.5)
    pv = dv[len(dv) // 4]                                        # the common small step = one line
    u0, v0 = min(u for u, v, c in chars), vs[0]
    rows = {}
    for u, v, ch in chars:
        r, c = round((v - v0) / pv), round((u - u0) / pu)
        line = rows.setdefault(r, {})
        if ch == ' ' or (ch == '_' and line.get(c, ' ') not in (' ', '_')):
            line.setdefault(c, ' ') if ch == ' ' else None
            continue
        line[c] = ch
    out = [''.join(rows[r].get(c, ' ') for c in range(max(rows[r]) + 1)).rstrip() if rows.get(r) else '' for r in range(max(rows) + 1)]
    lead = min((len(l) - len(l.lstrip()) for l in out if l.strip()), default=0)   # the page margin, as in the flat prints
    return [l[lead:] for l in out]


def upright(page):
    """True when the page's text is written left to right (every flat print); False for a print laid on its side."""
    dirs = [tuple(round(x) for x in ln['dir']) for b in page.get_text('dict')['blocks'] for ln in b.get('lines', [])]
    return not dirs or sum(d == (1, 0) for d in dirs) >= len(dirs) / 2


def num(s):
    s = (s or '').replace(',', '').strip()
    try:
        return float(s) if '.' in s else int(s)
    except ValueError:
        return s


def parse_pdf(path):
    """-> (info, rows). info: run date/time, pages, title(s), lines, printed line totals; rows: one dict per order row
    (FIELDS). The pages are read as one stream (their repeated headers left out), so an order block that runs on to the
    next page keeps its further cut rows and instructions (24 Sep 2026 H64A244-1: a cut row and "822 PLTS DONE")."""
    d = pymupdf.open(path)
    info = {'file': path.name, 'pages': d.page_count, 'titles': set(), 'run_date': '', 'run_time': '', 'lines': [], 'rows': 0,
            'odd': [], 'footers': {}}
    stream = []                                          # (page, line code, text) after each page's header
    for pno in range(d.page_count):
        g = grid(d[pno]) if upright(d[pno]) else grid_any(d[pno])
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
        for k, L in enumerate(g):
            m = re.search(r'LINE NO\.\s*(\S+)', L)
            if m:
                tail = ' '.join(g[k:k + 4])
                pcs = re.search(r'([\d,]+)\s*PCs', tail)
                lbs = re.search(r'([\d,]+)\s*LBs', tail)
                info['footers'][m.group(1)] = (int(pcs.group(1).replace(',', '')) if pcs else None,
                                               int(lbs.group(1).replace(',', '')) if lbs else None)
        hdr = next((k for k, L in enumerate(g) if L.startswith('|___|')), 3)     # the column headings' underline
        stream += [(pno + 1, line, L) for L in g[hdr + 1:]]
    rows, i = [], 0
    while i < len(stream):
        pno, line, text = stream[i]
        m = ROW_RX.match(text)
        if not m:
            i += 1
            continue
        cells = text.split('|')
        r = {k: '' for k in FIELDS}
        r.update(file=path.name, run_date=info['run_date'], run_time=info['run_time'], page=pno, line=line,
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
                info['odd'].append(f'p{pno} {r["order"]} spec "{cells[6].strip()}"')
            cd = cells[7]
            r['cut_width'], r['cut_length'] = cd[1:11].strip(), cd[11:].strip()
            r['total_sheets'], r['pack'], r['plts'] = num(cells[8]), cells[9].strip(), num(cells[10])
            ps = cells[11].split()
            r['pcs_stack'] = num(ps[0]) if ps else ''
            r['stk_plt'] = num(ps[1]) if len(ps) > 1 else ''
            r['weight_lbs'], r['instr_date'], r['web_width'] = num(cells[12]), cells[13].strip(), cells[14].strip()
        except IndexError as e:
            info['odd'].append(f'p{pno} {r["order"]}: {e}')
        sp_lines, j = [], i + 1                          # further cut rows and special instructions: to the block's end
        cuts = [r['total_sheets'] if isinstance(r['total_sheets'], int) else 0]
        while j < len(stream) and not stream[j][2].startswith('|___') and not ROW_RX.match(stream[j][2]):
            t = stream[j][2]
            m3 = CUT_RX.match(t)
            if m3:
                cuts.append(int(m3.group(1).replace(',', '')))
                j += 1
                continue
            t = t.strip().strip('|').strip()
            if 'Special_Instructions:' in t:
                sp_lines.append(t.split('Special_Instructions:', 1)[1].strip())
            elif t and not set(t) <= set('-_| ') and not t.startswith('LINE NO'):
                sp_lines.append(t)                       # instruction lines printed without the label count too
                                                         # (8 May 2020 HV4A339-3: "PLSC4W80x80 / Use pallet tickets ...")
            j += 1
        r['special'] = ' / '.join(s for s in sp_lines if s)
        r['cut_rows'] = len(cuts)
        if isinstance(r['total_sheets'], int):
            r['total_sheets'] = sum(cuts)
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


SYSTEM_NAME = re.compile(r'^(BPN9PFR|\d{6,8})', re.I)   # the report's own name, or digits: the only other files opened


def footer_check(info, rows):
    """Each line's rows against the line total the report prints ('LINE NO. SE11 Total: 15,900 PCs 5,724 LBs')."""
    out = []
    for line, (pcs, lbs) in info['footers'].items():
        rs = [r for r in rows if r['line'] == line]
        s_pcs = sum(r['total_sheets'] for r in rs if isinstance(r['total_sheets'], int))
        s_lbs = sum(r['weight_lbs'] for r in rs if isinstance(r['weight_lbs'], int))
        if (pcs is not None and pcs != s_pcs) or (lbs is not None and lbs != s_lbs):
            out.append(f'{line}: rows {s_pcs} PCs {s_lbs} LBs vs printed {pcs} PCs {lbs} LBs')
    return out


def parse_folder(folder=FOLDER, out_dir=None):
    """Every schedule PDF in the folder: MMDDYY[-n].pdf, and the report saved under another name (BPN9PFR$_xxx.PDF,
    0422524.pdf) - its day is its Run Date. Other files (forms, photos, quotes, other reports) are not opened."""
    out_dir = Path(out_dir or config.WORK_DIR / 'history')
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() == '.pdf'
                   and (NAME_RX.match(p.name) or SYSTEM_NAME.match(p.name)))
    infos, n, parsed = [], 0, []
    for p in files:
        try:
            info, rows = parse_pdf(p)
        except Exception as e:                           # a damaged or non-report PDF: listed, never guessed
            infos.append({'file': p.name, 'date': str(file_date(p.name)), 'error': repr(e)})
            continue
        if 'PRODUCTION INSTRUCTION - EXTRUSION' not in info['titles']:
            info.update(date=str(file_date(p.name)), odd='not an extrusion schedule (or no text: image scan)')
            infos.append(info)
            continue
        rd = datetime.strptime(info['run_date'], '%m/%d/%y').date() if info['run_date'] else None
        dte = file_date(p.name)
        if dte is None or (rd and rd != dte):
            info['odd'].append(f'named {p.name}, printed {rd}: dated by its Run Date')
            dte = rd
        info['date'] = str(dte)
        info['footer_check'] = ' ; '.join(footer_check(info, rows))
        for r in rows:
            r['date'] = str(dte)
        parsed.append((dte, info['run_time'], p.name, rows))
        n += len(rows)
        info['odd'] = ' ; '.join(info['odd'][:5])
        info['lines'] = ' '.join(info['lines'])
        info['footers'] = ' '.join(sorted(info['footers']))
        infos.append(info)
    with open(out_dir / 'ext_history.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        for dte, t, name, rows in sorted(parsed, key=lambda x: (x[0], x[1], x[2])):
            w.writerows(rows)
    keys = ['file', 'date', 'run_date', 'run_time', 'pages', 'lines', 'footers', 'rows', 'titles', 'footer_check', 'odd', 'error']
    with open(out_dir / 'files.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(sorted(infos, key=lambda x: (x.get('date') or '', x['file'])))
    return len(files), n, out_dir


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == 'parse':
        print(parse_folder(sys.argv[2] if len(sys.argv) > 2 else FOLDER))
    else:
        print(__doc__)
