"""Tech's own Word formulation files, read as typed text (James Kuo, 2 Nov 2026: "here are the fomulation left by YC
before he went on vacation" - the Technical Internal library's Daily Formulation\\<MMDDYYYY> folders, synced to this PC).

Each folder holds, per line, the day's page (Lnn-form.doc, "Line N (SExx) Formulations") and the line's running record
(Lnn-form-1.doc / Lnn-form-01.doc(x): every order Tech has issued on the line, one row per formula, oldest first, no
dates; an order's month from its number). Word is blocked from opening them where they are synced, so they are converted
first from a copy (Word, read-only): Lnn-form.conv.docx next to the copies.

    python history/tech_word_frm.py <folder of .conv.docx> <date YYYY-MM-DD> [--packet] [--history]
      --packet   the day's pages into data/packets/packet_<date>.json ('frm', as the daily packet keeps Tech's pages)
      --history  the running records into data/frm_history/tech_word_history.json (one issue month per entry, the daily
                 packet's FRM layout), for the rules' issued settings and the Look up
Nothing is corrected: text as typed, a cell's line breaks joined with a space.
"""
import datetime
import json
import re
import sys
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
from calc.common import split_codes  # noqa: E402
from calc.parse_fcal import order_date  # noqa: E402

LINES = {1: 'SE11', 2: 'SE12', 3: 'SE13', 4: 'SE21', 5: 'SE22', 6: 'SE23', 7: 'SE24', 8: 'SE31', 9: 'SE32', 10: 'SE25',
         11: 'SE41', 12: 'SE42', 13: 'SE43', 14: 'SE44', 15: 'SE51', 16: 'SE61'}      # the files' own titles
FOOTNOTE = re.compile(r'^\s*Note:', re.I)


def cell_text(c):
    # a dash Word could not carry over prints as U+FFFD: Tech's CaCO3 / FOAM dash (the 30 Sep page's "–")
    return re.sub(r'\s+', ' ', c.text.replace('�', '–')).strip()


def rows_of(path):
    """Each table row as its distinct cells (a merged cell once)."""
    d = Document(path)
    out = []
    for t in d.tables:
        for r in t.rows:
            seen, cells = set(), []
            for c in r.cells:
                if id(c._tc) not in seen:
                    seen.add(id(c._tc)); cells.append(cell_text(c))
            out.append(cells)
    notes = [re.sub(r'\s+', ' ', p.text).strip() for p in d.paragraphs if FOOTNOTE.match(p.text)]
    return out, notes


def columns_by_line():
    """The feeder columns of each line as the daily packets name them (latest page on file)."""
    cols = {}
    for p in sorted(config.PACKETS_DIR.glob('packet_*.json')):
        for pg in json.loads(p.read_text(encoding='utf-8'))['frm']:
            cols[pg['line_code']] = pg['feeder_columns']
    return cols


def groups_of(rows, cols):
    """Rows -> [{'orders', 'formulas', 'raw'}]: one Order # cell is one group (merged down its formula rows)."""
    groups, mats, last = [], None, None
    for cells in rows:
        if len(cells) < 4 or not any(cells[1:]):
            continue
        if cells[0].lower().startswith('order') or cells[1].lower().startswith('formula'):
            continue                                    # a header row
        code = cells[1].split(' /')[0].strip()
        if cols and len(cells) - 3 == len(cols):
            # weight-blender lines (SE24, SE31/32, SE42/43, SE61): one column per feeder, a formula on two rows - the
            # materials, then the settings (same Order # and code cells)
            numeric = all(re.fullmatch(r'[\d.]+|Auto', v, re.I) for v in cells[2:-1] if v)
            if mats is None and numeric and groups and last and last[0] == (cells[0], code):
                m = last[1]                             # a second settings row under the same materials (SE43 RP26911-2)
            elif mats is None or mats[0] != (cells[0], code):
                mats = ((cells[0], code), cells)
                continue
            else:
                m, mats = mats[1], None
            last = ((cells[0], code), m)
            f = {'formula_code': code, 'note': m[-1] or cells[-1],
                 'feeders': {cols[i]: {'material': m[2 + i], 'set': cells[2 + i]} for i in range(len(cols))}}
        else:
            n = (len(cells) - 3) // 2
            names = cols if cols and len(cols) == n else [f'#{i}' for i in range(1, n + 1)]
            f = {'formula_code': code, 'note': cells[-1],
                 'feeders': {names[i]: {'material': cells[2 + 2 * i], 'set': cells[3 + 2 * i]} for i in range(n)}}
        # orders one per line in the cell ("H68A053-1 H6AA097-1" once joined): a space before a letter separates them
        orders = split_codes(re.sub(r'\s+(?=[A-Z])', ', ', cells[0]), 'order') or ([cells[0]] if cells[0] else [])
        if groups and (not cells[0] or cells[0] == groups[-1]['raw']):
            groups[-1]['formulas'].append(f)
        else:
            groups.append({'orders': orders, 'formulas': [f], 'raw': cells[0]})
    return groups


def page(no, groups, notes, day, src, cols):
    return {'scan_page': no, 'title': f'Line {no} ({LINES[no]}) Formulations', 'line_no': str(no), 'line_code': LINES[no],
            'date': f'{day.month}/{day.day}/{day:%y}', 'header_note': '', 'feeder_columns': cols,
            'groups': [{'orders': g['orders'], 'formulas': g['formulas']} for g in groups], 'footnotes': notes,
            'footer': 'Tech. Department', 'effective_date': '', 'handwritten': '',
            'unclear': f"From Tech's Word file {src} (typed text, not a scan); the AC header and effective date are not in the file's text."}


def main(folder, date, do_packet, do_history):
    folder, day = Path(folder), datetime.date.fromisoformat(date)
    cols = columns_by_line()
    pages, hist = [], {}
    for no in sorted(LINES):
        cur = folder / f'L{no:02d}-form.conv.docx'
        if cur.exists():
            rows, notes = rows_of(cur)
            c = cols.get(LINES[no], [])
            g = groups_of(rows, c)
            if g and LINES[no] in cols:                 # lines the plant schedules (SE41 / SE44 / SE51 have no page on file)
                pages.append(page(no, g, notes, day, cur.name.replace('.conv.docx', '.doc'), c))
        for name in (f'L{no:02d}-form-01.conv.docx', f'L{no:02d}-form-1.conv.docx'):
            run = folder / name
            if not run.exists():
                continue
            rows, notes = rows_of(run)
            c = cols.get(LINES[no], [])
            last = None
            for k, g in enumerate(groups_of(rows, c)):
                od = next((order_date(o) for o in g['orders'] if order_date(o)), None) or last
                if not od:
                    continue
                last = od
                # an issue month, dated YYYY-MM-00: before that month's daily packets, never the same key as one
                m = f'{od:%Y-%m}-00'
                hp = hist.setdefault(m, {}).setdefault(no, page(no, [], notes, od.replace(day=1),
                                                                   run.name.replace('.conv.docx', '.doc'), c))
                hp['groups'].append({'orders': g['orders'], 'formulas': g['formulas'], 'row': k})
            break
    if do_packet:
        p = config.packet_path(date)
        k = json.loads(p.read_text(encoding='utf-8'))
        if k['frm']:
            raise SystemExit(f'{p.name} already has FRM pages: nothing changed')
        k['frm'] = pages
        k['frm_source_scan'] = f"Tech's Word files, Daily Formulation\\{folder.name.split('raw')[-1] or date} (typed text)"
        p.write_text(json.dumps(k, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(p.name, len(pages), 'pages,', sum(len(x['groups']) for x in pages), 'groups')
    if do_history:
        out = [{'packet_date': m, 'source_scan': f"Tech's Word running records (Daily Formulation, as of {date})",
                'frm_source_scan': f"Tech's Word running records (Daily Formulation, as of {date})",
                'frm': [hist[m][no] for no in sorted(hist[m])], 'ext': [], 'cnv': []} for m in sorted(hist)]
        q = ROOT / 'data' / 'frm_history' / 'tech_word_history.json'
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(json.dumps(out, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
        n = sum(len(pg['groups']) for e in out for pg in e['frm'])
        print(q.name, len(out), 'months', out[0]['packet_date'] if out else '', '-', out[-1]['packet_date'] if out else '', n, 'groups')
    return pages, hist


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], '--packet' in a, '--history' in a)
