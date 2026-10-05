"""A day's packet from the system's own PDFs instead of a scan (2 Oct 2026: James sent the extrusion schedule as the AIX
report itself, BPN9PFR$_*.PDF, and the converting schedule as "Die Cutting Schedule MM-DD.pdf" printed from Excel).
Both PDFs carry their text, so nothing is OCR'd and every value is copied exactly as printed.

    python daily/packet_from_pdf.py <date> --ext <BPN9PFR pdf> [--cnv <Die Cutting Schedule pdf>] [--force]

Two steps (James Kuo, 1 Oct 2026: "Get the fomulation to production team first. then read the rest for the data base
update (Production Record)"): --ext alone writes the packet's EXT part, enough for resolve / auger_check / render_frm;
--cnv adds the converting pages later (the packet's EXT part is kept). The EXT report must add up to the line totals it
prints (history/prod_instr.footer_check), or nothing is written. A PDF carries no handwriting: 'handwritten' stays empty.
"""
import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'history'))
import config  # noqa: E402
import prod_instr as P  # noqa: E402

CUT_LINE = re.compile(r'^\|[\s-]*\|\s*([\d /]+?)\s{2,}([\d /]+?)\s*\|\s*([\d,]+)\s*\|')


def ext_pages(pdf):
    """The EXT report -> (packet 'ext' pages, info). Each record with its cut rows and special instructions as printed."""
    pdf = Path(pdf)
    info, parsed = P.parse_pdf(pdf)
    if P.footer_check(info, parsed):
        raise SystemExit(f'{pdf.name}: the records do not add up to the printed line totals: {P.footer_check(info, parsed)}')
    special = {(r['line'], r['order']): r['special'] for r in parsed}
    d = P.pymupdf.open(str(pdf))
    stream, report_page, final = [], {}, ''
    for pno in range(d.page_count):
        g = P.grid(d[pno]) if P.upright(d[pno]) else P.grid_any(d[pno])
        if not g:
            continue
        line = next((m.group(1) for L in g[1:4] for m in [re.search(r'LINE NO:\s*(\S+)', L)] if m), '')
        m = re.search(r'PAGE\s*:\s*(\d+)', g[0])
        report_page[pno + 1] = m.group(1) if m else ''
        for L in g:
            m = re.search(r'Final Total:\s*([\d,]+)\s*PCs\s*([\d,]+)\s*LBs', L)
            if m:
                final = f'{m.group(1)} PCs / {m.group(2)} LBs'
        hdr = next((k for k, L in enumerate(g) if L.startswith('|___|')), 3)
        stream += [(pno + 1, line, L) for L in g[hdr + 1:]]
    pages, last_page = OrderedDict(), {}
    cur = None
    for pno, line, t in stream:
        m = P.ROW_RX.match(t)
        if m:
            c = t.split('|')
            sp = P.SPEC_RX.match(c[6].strip())
            mat, grade, spec, colours, thk, gsm = sp.groups() if sp else ('', '', '', '', '', '')
            ps = c[11].split()
            cur = {'T': c[1].strip(), 'order': f'{m.group(2)}-{m.group(3)}', 'prod_code': c[3].strip(), 'die': c[4].strip(),
                   'order_width': c[5][1:11].strip(), 'order_length': c[5][11:].strip(),
                   'mat_spec': ' '.join(x for x in (mat, grade, spec) if x), 'colors': colours, 'thk': thk, 'gsm': gsm,
                   'cut_rows': [{'width': c[7][1:11].strip(), 'length': c[7][11:].strip(), 'total_sheets': c[8].strip()}],
                   'pack_code': c[9].strip(), 'num_plt': c[10].strip(), 'pcs_per_stack': ps[0] if ps else '',
                   'stk_per_plt': ps[1] if len(ps) > 1 else '', 'weight_lbs': c[12].strip(), 'instr_date': c[13].strip(),
                   'web_width': c[14].strip(), 'special_instructions': special.get((line, f'{m.group(2)}-{m.group(3)}'), ''),
                   'handwritten': '', 'unclear': ''}
            pg = pages.setdefault((pno, line), {'scan_page': pno, 'report_page': report_page.get(pno, ''), 'line': line,
                                                'run_date': info['run_date'], 'run_time': info['run_time'], 'carryover_top': '',
                                                'rows': [], 'line_total_pcs': '', 'line_total_lbs': '', 'final_total': '',
                                                'page_notes': f'From the system PDF {pdf.name} (text, no OCR).'})
            pg['rows'].append(cur)
            last_page[line] = pg
            continue
        m = CUT_LINE.match(t)
        if m and cur:
            cur['cut_rows'].append({'width': m.group(1).strip(), 'length': m.group(2).strip(), 'total_sheets': m.group(3)})
        elif t.startswith('|___'):
            cur = None
    for line, (pcs, lbs) in info['footers'].items():
        if line in last_page:
            last_page[line]['line_total_pcs'] = f'{pcs:,}' if pcs is not None else ''
            last_page[line]['line_total_lbs'] = f'{lbs:,}' if lbs is not None else ''
    if pages and final:
        list(pages.values())[-1]['final_total'] = final
    for pg in pages.values():                          # the packet's sheet count is the sum of the cut rows
        for r in pg['rows']:
            p = next(x for x in parsed if x['order'] == r['order'] and x['line'] == pg['line'])
            got = sum(int(c['total_sheets'].replace(',', '')) for c in r['cut_rows'])
            if isinstance(p['total_sheets'], int) and got != p['total_sheets']:
                raise SystemExit(f"{r['order']}: cut rows add up to {got:,}, the report's block to {p['total_sheets']:,}")
    return list(pages.values()), info


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('date'); ap.add_argument('--ext'); ap.add_argument('--cnv'); ap.add_argument('--force', action='store_true')
    a = ap.parse_args(argv)
    dest = config.packet_path(a.date)
    pk = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {
        'packet_date': a.date, 'source_scan': '', 'ext': [], 'cnv': [], 'frm': [], 'frm_source_scan': ''}
    if a.ext:
        if pk['ext'] and not a.force:
            raise SystemExit(f'{dest.name} already has its EXT part (--force to replace it before it is recorded)')
        config.record_read(a.ext, 'EXT schedule (system PDF)')
        pk['ext'], info = ext_pages(a.ext)
        pk['source_scan'] = Path(a.ext).name
        n = sum(len(p['rows']) for p in pk['ext'])
        print(f"EXT: {n} records, {len(info['lines'])} lines, run {info['run_date']} {info['run_time']}; every line adds up to its printed total")
    if a.cnv:
        import cnv_from_pdf
        if pk['cnv'] and not a.force:
            raise SystemExit(f'{dest.name} already has its CNV part (--force to replace it before it is recorded)')
        config.record_read(a.cnv, 'CNV schedule (PDF)')
        pk['cnv'] = cnv_from_pdf.cnv_pages(a.cnv)
        pk['cnv_source'] = Path(a.cnv).name
        print(f"CNV: {sum(len(p['rows']) for p in pk['cnv'])} rows on {len(pk['cnv'])} pages")
    dest.write_text(json.dumps(pk, ensure_ascii=False, indent=1), encoding='utf-8')
    print(dest)


if __name__ == '__main__':
    main(sys.argv[1:])
