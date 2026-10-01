"""Correct a day's packet from the system's own PDF of the same report (James Kuo, 1 Oct 2026: "correct what you can",
after scan_reader/verify_with_system_pdf.py found special-instruction punctuation, text carried onto the next page and
one order's cut rows read differently from the system).

    python scan_reader/correct_from_system_pdf.py <date> <system pdf> [--dry-run]

The PDF is the text the paper is printed from, so it wins on every printed field: special instructions and cut rows are
taken from it, and so is any other field that differs (each change is listed and noted in the row's 'unclear' field).
Handwriting stays as read from the scan. Then rebuild the day (build_xlsx.py), publish.py --reissue, record.py --reissue.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'history'))
import prod_instr as P  # noqa: E402


def system_rows(pdf):
    """-> {order: row} with 'cuts' = [(width, length, sheets as printed)] for every cut row of the block."""
    info, rows = P.parse_pdf(pdf)
    d = P.pymupdf.open(pdf)
    stream = []
    for pno in range(d.page_count):
        g = P.grid(d[pno]) if P.upright(d[pno]) else P.grid_any(d[pno])
        if not g:
            continue
        hdr = next((k for k, L in enumerate(g) if L.startswith('|___|')), 3)
        stream += [L for L in g[hdr + 1:]]
    cuts, cur = {}, None
    for t in stream:
        m = P.ROW_RX.match(t)
        if m:
            cur = f'{m.group(2)}-{m.group(3)}'
            c = t.split('|')
            cuts[cur] = [(c[7][1:11].strip(), c[7][11:].strip(), c[8].strip())]
            continue
        m = re.match(r'^\|[\s-]*\|\s*([\d /]+?)\s{2,}([\d /]+?)\s*\|\s*([\d,]+)\s*\|', t)
        if m and cur:
            cuts[cur].append((m.group(1).strip(), m.group(2).strip(), m.group(3)))
    out = {}
    for r in rows:
        r['cuts'] = cuts.get(r['order'], [])
        out[(r['line'], r['order'])] = r
    return info, out


def main(argv):
    date, pdf = argv[0], Path(argv[1])
    dry = '--dry-run' in argv
    info, sysr = system_rows(pdf)
    p = ROOT / 'data' / 'packets' / f'packet_{date}.json'
    pk = json.loads(p.read_text(encoding='utf-8'))
    norm = lambda s: re.sub(r'\s+', ' ', str(s or '').replace(' / ', ' ')).strip()
    n = lambda s: str(s).replace(',', '').strip()
    changed = 0
    for e in pk['ext']:
        for r in e['rows']:
            s = sysr.get((e['line'], r['order']))
            if not s:
                print('not in the PDF:', e['line'], r['order'])
                continue
            notes = []
            ms = r['mat_spec'].split()
            simple = [('prod_code', r['prod_code'], s['prod_code']), ('die', r['die'], s['die']), ('order_width', r['order_width'], s['width']),
                      ('order_length', r['order_length'], s['length']), ('colors', r['colors'], s['colour']), ('pack_code', r['pack_code'], s['pack']),
                      ('instr_date', r['instr_date'], s['instr_date']), ('web_width', r['web_width'], s['web_width'])]
            for k, a, b in simple:
                if a != b:
                    notes.append(f'{k} {a!r} -> {b!r}'); r[k] = b
            num_fields = [('thk', s['thk']), ('gsm', s['gsm']), ('num_plt', s['plts']), ('pcs_per_stack', s['pcs_stack']),
                          ('stk_per_plt', s['stk_plt']), ('weight_lbs', s['weight_lbs'])]
            for k, b in num_fields:
                if n(r[k]) != n(b):
                    notes.append(f'{k} {r[k]!r} -> {b!r}')
                    r[k] = f'{b:,}' if isinstance(b, int) and k in ('gsm', 'weight_lbs') else str(b)
            sys_ms = s['mat'] + ' ' + s['mat_spec']
            if ' '.join(ms) != sys_ms:
                notes.append(f'mat_spec {r["mat_spec"]!r} -> {sys_ms!r}'); r['mat_spec'] = sys_ms
            mine_c = [(c['width'], c['length'], n(c['total_sheets'])) for c in r['cut_rows']]
            if mine_c != [(a, b, n(c)) for a, b, c in s['cuts']]:
                notes.append(f'cut rows {len(mine_c)} -> {len(s["cuts"])} (' + '; '.join(f'{a} x {b} = {c}' for a, b, c in s['cuts']) + ')')
                r['cut_rows'] = [{'width': a, 'length': b, 'total_sheets': c} for a, b, c in s['cuts']]
            if norm(r['special_instructions']) != norm(s['special']):
                notes.append(f'special instructions {r["special_instructions"]!r} -> {s["special"]!r}')
                r['special_instructions'] = s['special']
            if r.get('truncated'):                 # the scan missed the page the record runs on to; the PDF has all of it
                r['truncated'] = False
                notes.append('record complete from the PDF (its continuation page is missing from the scan)')
            if notes:
                changed += 1
                note = f'Corrected from the system PDF {pdf.name} (run {info["run_date"]} {info["run_time"]}; James Kuo, 1 Oct 2026): ' + '; '.join(notes)
                r['unclear'] = (r.get('unclear') + ' | ' if r.get('unclear') else '') + note
                print(e['line'], r['order'], '|', '; '.join(notes)[:300])
    pk.setdefault('corrections', []).append({'date': '2026-10-01', 'source': pdf.name, 'run': f'{info["run_date"]} {info["run_time"]}',
                                             'rows_changed': changed, 'by': 'James Kuo: "correct what you can"'})
    print(f'{date}: {changed} rows corrected from {pdf.name}')
    if not dry:
        p.write_text(json.dumps(pk, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1:])
