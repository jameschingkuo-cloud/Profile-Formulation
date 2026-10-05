"""The converting schedule from its PDF ("Die Cutting Schedule MM-DD.pdf", printed from Excel; 2 Oct 2026) -> the packet's
'cnv' pages, in the same form as a transcription of the paper (daily/packet_from_pdf.py --cnv).

The PDF carries its text, so nothing is OCR'd. Each page's columns are the table's own vertical lines, named by the header
cells above them (Order # ... Req. Date; the slitter page adds 'Extrusio Start' -> semi_start). On a record line every
character goes to the column its centre falls in, so a cell whose text runs on into the next cell reads as the paper shows
it (H68A127-1: Semi-Size text running into Color) and is noted. The other lines of the table, as the transcriptions record
them (30 Sep 2026 packet):
  - 'N DONE' -> done_note of the record it sits under;
  - text inside one cell under a record (die description '(Rev 8.5")', '900041004. ARD') -> that field, joined ' / ';
  - text across the columns: directly under a record -> its row_notes 'Lines directly below: "..."'; '**For next ...' and
    'BOARD USE FROM OTHER ORDER ...' directly above a record -> its row_notes 'Line directly above: "..."'; a line of
    '***' instructions, one printed outside the table ('For Corn Boxes below: ...'), or one apart from any record (an
    empty row between) -> a banner note on the page.
"""
import re
import sys
from pathlib import Path

import pymupdf

FIELD = {'Order #': 'order', 'Product Code': 'product_code', 'Extrusion Status': 'extrusion_status', 'Semi pc/plt': 'semi_pc_plt',
         'Extrusio Start': 'semi_start', 'Semi-Size': 'semi_size', 'Color': 'color', 'Apl.': 'apl', 'MM': 'mm', 'Flute': 'flute',
         'Die #': 'die_no', 'Die Description': 'die_description', 'Die Status': 'die_status', 'Plate Status': 'plate_status',
         'Ink Color': 'ink_color', 'Total Sheets': 'total_sheets', 'Pack Code': 'pack_code', '# of Plts.': 'num_plts',
         'Pc. / Plt.': 'pc_per_plt', 'Req. Date': 'req_date'}
HEAD_RX = [(r'Order', 'order'), (r'Product', 'product_code'), (r'pc/plt', 'semi_pc_plt'), (r'Start', 'semi_start'),
           (r'Extrusion|Status', None), (r'Semi-Size', 'semi_size'), (r'^Color', 'color'), (r'Apl', 'apl'), (r'^MM', 'mm'),
           (r'Flute', 'flute'), (r'Die #', 'die_no'), (r'Description', 'die_description'), (r'Plate', 'plate_status'),
           (r'Ink', 'ink_color'), (r'Total', 'total_sheets'), (r'Pack', 'pack_code'), (r'Plts', 'num_plts'), (r'Pc\.', 'pc_per_plt'),
           (r'Req', 'req_date')]
CONTINUED = {'die_description', 'ink_color', 'plate_status'}  # cells whose text goes on to a second line (' / ')


def field(head):
    """A header cell -> packet field. Header text can run into the next cell ('Semi E pc/plt' + 'xtrusio Start' on the
    slitter page), so the words are matched, not the whole cell."""
    if head in FIELD:
        return FIELD[head]
    if re.search(r'Extrusion\s*Status', head):
        return 'extrusion_status'
    if re.search(r'Die\s*Status', head):
        return 'die_status'
    return next((f for rx, f in HEAD_RX if f and re.search(rx, head)), None)


ROW_KEYS = ['order', 'product_code', 'extrusion_status', 'semi_pc_plt', 'semi_size', 'color', 'apl', 'mm', 'flute', 'die_no',
            'die_description', 'die_status', 'plate_status', 'ink_color', 'total_sheets', 'pack_code', 'num_plts', 'pc_per_plt',
            'req_date', 'done_note', 'row_notes', 'handwritten', 'unclear']
ORDER = re.compile(r'^[A-Z0-9]{7}-\d{1,3}$')
DONE = re.compile(r'^\d[\d,]*\s+(TOTAL\s+)?DONE\b', re.I)        # '24 DONE', '6 DONE PRINTING', '490 TOTAL DONE'
ABOVE = re.compile(r'^(\*\*(?!\*)|BOARD USE)', re.I)        # notes printed directly above the record they are for
GAP = 18                                                     # points between two text lines with no empty row between


def grid(page):
    """(column x lines, vertical segments [(x, y0, y1)]) drawn on the page."""
    segs = []
    for dr in page.get_drawings():
        for it in dr['items']:
            if it[0] == 'l' and abs(it[1].x - it[2].x) < 0.5 and abs(it[1].y - it[2].y) > 5:
                segs.append((it[1].x, min(it[1].y, it[2].y), max(it[1].y, it[2].y)))
            elif it[0] == 're' and it[1].width < 1.5 and it[1].height > 5:
                segs.append((it[1].x0, it[1].y0, it[1].y1))
    xs = []
    for x in sorted(s[0] for s in segs):
        if not xs or x - xs[-1] > 2:
            xs.append(x)
    return xs, segs


def text_lines(page):
    """Visual lines of cell texts: [(y, [(x0, x1, text)])], top to bottom. Each text is one text-drawing operation of the
    PDF - one Excel cell - read whole, also where the paper cuts it off at the cell's edge (H68A127-1's Color 'WB GT WB'
    shows as 'B GT V'; H68A170-2's Semi-Size '51 4/16 X 73 12/16' as '... 12/1')."""
    ops = []
    for t in page.get_texttrace():
        txt = ''.join(chr(c[0]) for c in t['chars'] if c[0] > 0)
        if txt.strip():
            x0, y0, x1, y1 = t['bbox']
            ops.append(((y0 + y1) / 2, x0, x1, re.sub(r'\s+', ' ', txt).strip()))
    ops.sort()
    lines = []
    for yc, x0, x1, txt in ops:
        if lines and abs(lines[-1][0] - yc) < 2.5:
            lines[-1][1].append((x0, x1, txt))
        else:
            lines.append([yc, [(x0, x1, txt)]])
    return [(y, sorted(cs)) for y, cs in lines]


def join(cs):
    return re.sub(r'\s+', ' ', ' '.join(c[2] for c in sorted(cs))).strip()


def segments(cs, xs):
    """A line's cell texts, neighbours closer than a space merged -> [(text, columns it covers)]."""
    groups = []
    for c in cs:
        if groups and c[0] - groups[-1][-1][1] < 4.5:
            groups[-1].append(c)
        else:
            groups.append([c])
    out = []
    for g in groups:
        x0, x1 = min(c[0] for c in g), max(c[1] for c in g)
        out.append((join(g), [i for i, (a, b) in enumerate(zip(xs, xs[1:])) if x0 < b - 0.5 and x1 > a + 0.5]))
    return out


def record_cells(cs, xs, cols):
    """A record line's cells: each text goes to the column its middle falls in."""
    cells, wide = {}, []
    for c in cs:
        mid = (c[0] + c[1]) / 2
        i = 0 if mid < xs[0] else len(xs) - 2 if mid >= xs[-1] else next(k for k in range(len(xs) - 1) if xs[k] <= mid < xs[k + 1])
        if cols[i]:
            cells.setdefault(cols[i], []).append(c)
            if c[0] < xs[i] - 1 or c[1] > xs[i + 1] + 1:
                wide.append(cols[i])
    return {k: join(v) for k, v in cells.items() if join(v)}, wide


def add_note(r, kind, text):
    r.setdefault('_notes', {}).setdefault(kind, []).append(text)


def cnv_pages(pdf):
    pdf = Path(pdf)
    d = pymupdf.open(str(pdf))
    pages, carry = [], None                              # carry: (line code, last record) of the page before
    for pno, page in enumerate(d, 1):
        xs, segs = grid(page)
        lines = text_lines(page)
        hdr_i = next(i for i, (y, cs) in enumerate(lines) if join(cs).startswith('Order #'))
        hy = lines[hdr_i][0]
        head = [' '.join(t for t in (join(c for c in cs if a < (c[0] + c[1]) / 2 < b) for y, cs in lines[hdr_i:hdr_i + 2]) if t)
                for a, b in zip(xs, xs[1:])]
        cols = [field(h) for h in head]
        if 'order' not in cols:
            raise SystemExit(f'{pdf.name} page {pno}: no Order # column ({head})')
        top_lines = [join(cs) for y, cs in lines[:hdr_i]]
        top = ' '.join(top_lines)
        title = next((join(c for c in cs if c[0] < 640) for y, cs in lines[:hdr_i] if 'PRODUCTION INSTRUCTION' in join(cs)), '')
        m = re.search(r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})', top)
        issue = m.group(1) if m else ''
        m = re.search(r'Page:\s*(\d+)\s*of\s*(\d+)', top)
        page_of = f'{m.group(1)} of {m.group(2)}' if m else ''
        lno = next((cs for y, cs in lines[:hdr_i] if join(cs).startswith('LINE NO')), None)
        line_no = line_code = ''
        if lno:
            line_no = re.sub(r'^LINE NO:\s*', '', join(c for c in lno if c[0] < 600))
            line_code = join(c for c in lno if c[0] >= 600) or line_no.split()[0]
        pg = {'scan_page': pno, 'title': title, 'line_no': line_no, 'line_code': line_code, 'issue_date': issue, 'page_of': page_of,
              'banner_notes': [], 'page_notes': f'From the PDF {pdf.name} (text, no OCR).', 'rows': []}
        # items: ('rec', y, row) or ('txt', y, segments)
        items = []
        for y, cs in lines[hdr_i + 2:]:
            if not join(cs):
                continue
            first = join(c for c in cs if (c[0] + c[1]) / 2 < xs[1])
            if ORDER.match(first):
                cells, wide = record_cells(cs, xs, cols)
                keys = ROW_KEYS[:4] + (['semi_start'] if 'semi_start' in cols else []) + ROW_KEYS[4:]   # the slitter page
                r = {k: '' for k in keys}
                r.update({k: v for k, v in cells.items() if k in r})
                if wide:
                    r['unclear'] = (f"{', '.join(wide)}: the text is wider than its cell and cut off on the paper; copied in full "
                                    f"from the PDF")
                pg['rows'].append(r)
                items.append(('rec', y, r))
            else:
                items.append(('txt', y, segments(cs, xs)))
        recs = [i for i, it in enumerate(items) if it[0] == 'rec']
        outside = lambda y: not any(y0 - 1 <= y <= y1 + 1 for x, y0, y1 in segs)   # no table line beside it
        banners = []
        for i, (kind, y, segs_) in enumerate(items):
            if kind == 'rec':
                continue
            a = max((k for k in recs if k < i), default=None)
            b = min((k for k in recs if k > i), default=None)
            chain_prev = a is not None and all(items[k + 1][1] - items[k][1] < GAP for k in range(a, i))
            chain_next = b is not None and all(items[k + 1][1] - items[k][1] < GAP for k in range(i, b))
            A = items[a][2] if a is not None else (carry[1] if carry and carry[0] == line_code and i == 0 else None)
            B = items[b][2] if b is not None else None
            if a is None and A is not None:
                chain_prev = items[0][1] - hy < 40           # the first lines of the page, carried on from the page before
            for k in range(len(segs_) - 1, 0, -1):          # '490' + 'TOTAL DONE' in two cells is one note
                if re.match(r'^(TOTAL\s+)?DONE\b', segs_[k][0], re.I) and re.fullmatch(r'\d[\d,]*', segs_[k - 1][0]):
                    segs_[k - 1:k + 1] = [(segs_[k - 1][0] + ' ' + segs_[k][0], segs_[k - 1][1] + segs_[k][1])]
            owned = A is not None and chain_prev            # the line sits under a record, no empty row between
            done = [t for t, c in segs_ if DONE.match(t)] if owned else []
            cell = [(t, c) for t, c in segs_ if owned and t not in done and len(c) == 1 and cols[c[0]] in CONTINUED]
            free = [t for t, c in segs_ if t not in done and (t, c) not in cell]
            if done:                                         # '256 DONE / 234 DONE IN COOLSEAL / 490 TOTAL DONE'
                A['done_note'] = ' / '.join(x for x in [A['done_note']] + [re.sub(r'\s+', ' ', t) for t in done] if x)
            for t, c in cell:                                # a cell's second line: 'HMC WATSONTOWN / BRICK 1/2 SURROUND'
                f = cols[c[0]]
                A[f] = f'{A[f]} / {t}' if A[f] else t
            if not free:
                continue
            text = ' '.join(free)
            if text.startswith('***') or outside(y):
                banners.append((i, a, b, text))
            elif ABOVE.match(text) and chain_next:
                add_note(B, 'above', text)
            elif owned:
                add_note(A, 'below', text)
            elif chain_next:
                add_note(B, 'above', text)
            else:
                banners.append((i, a, b, text))
        merged = []
        for i, a, b, text in banners:                    # a banner printed over two lines is one note
            if merged and merged[-1][0] == i - 1 and not text.startswith('*') and items[i][1] - items[i - 1][1] < GAP:
                merged[-1] = (i, merged[-1][1], merged[-1][2], merged[-1][3] + ' ' + text)
            else:
                merged.append((i, a, b, text))
        for i, a, b, text in merged:
            where = [f"after order {items[a][2]['order']}" if a is not None else 'top of the table, below the header',
                     f"before order {items[b][2]['order']}" if b is not None else 'end of the page']
            pg['banner_notes'].append({'position': ', '.join(where), 'text': text})
        for r in pg['rows']:
            n = r.pop('_notes', {})
            parts = []
            if n.get('above'):
                parts.append('Line directly above: ' + ' | '.join(f'"{t}"' for t in n['above']))
            if n.get('below'):
                parts.append('Lines directly below: ' + ' | '.join(f'"{t}"' for t in n['below']))
            r['row_notes'] = ' '.join(parts)
        if carry and carry[1].get('_notes'):            # notes added to the previous page's last record
            n = carry[1].pop('_notes')
            if n.get('below'):
                carry[1]['row_notes'] = (carry[1]['row_notes'] + ' ' if carry[1]['row_notes'] else '') + \
                    'Lines directly below (top of the next page): ' + ' | '.join(f'"{t}"' for t in n['below'])
        if pg['rows']:
            carry = (line_code, pg['rows'][-1])
        pages.append(pg)
    return pages


if __name__ == '__main__':
    import json
    for pg in cnv_pages(sys.argv[1]):
        print(json.dumps({k: v for k, v in pg.items() if k != 'rows'}, ensure_ascii=False))
        for r in pg['rows']:
            print('   ', json.dumps({k: v for k, v in r.items() if v}, ensure_ascii=False))
