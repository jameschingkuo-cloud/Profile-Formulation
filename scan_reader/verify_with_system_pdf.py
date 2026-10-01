"""Every field of a day's scan transcription (data/packets/packet_<date>.json) against the system's own PDF of the same
report (BPN9PFR*.PDF, the text the paper is printed from). James Kuo, 1 Oct 2026: "take a look at yesterday production
schedule PDF file and confirm your scan file is rock solid".

    python scan_reader/verify_with_system_pdf.py <date> <BPN9PFR...PDF>

Prints every order only on one side and every field that differs. The PDF is the authority for printed text; the scan
adds only what is written by hand.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'history'))
import os; os.chdir(ROOT)
import prod_instr as P

DATE, PDF = sys.argv[1], Path(sys.argv[2])
info, rows = P.parse_pdf(PDF)
# each block's cut rows with their sizes, from the same text stream
d = P.pymupdf.open(PDF)
stream = []
for pno in range(d.page_count):
    g = P.grid(d[pno]) if P.upright(d[pno]) else P.grid_any(d[pno])
    hdr = next((k for k, L in enumerate(g) if L.startswith('|___|')), 3)
    stream += [(pno + 1, L) for L in g[hdr + 1:]]
cuts, cur = {}, None
for pno, t in stream:
    m = P.ROW_RX.match(t)
    if m:
        cur = f'{m.group(2)}-{m.group(3)}'
        c = t.split('|')
        cuts[cur] = [(c[7][1:11].strip(), c[7][11:].strip(), c[8].strip())]
        continue
    m = re.match(r'^\|[\s-]*\|\s*([\d /]+?)\s{2,}([\d /]+?)\s*\|\s*([\d,]+)\s*\|', t)
    if m and cur:
        cuts[cur].append((m.group(1).strip(), m.group(2).strip(), m.group(3)))
pk = json.loads(Path(f'data/packets/packet_{DATE}.json').read_text(encoding='utf-8'))
mine = {r['order']: (e, r) for e in pk['ext'] for r in e['rows']}
sysr = {r['order']: r for r in rows}
norm = lambda s: re.sub(r'\s+', ' ', str(s or '').replace(' / ', ' ')).strip()
n = lambda s: str(s).replace(',', '').strip()
diffs, checked = [], 0
print('orders only in the PDF:', sorted(set(sysr) - set(mine)), '| only in the scan:', sorted(set(mine) - set(sysr)))
for o, s in sysr.items():
    if o not in mine:
        continue
    e, r = mine[o]
    ms = r['mat_spec'].split()
    pairs = [('line', e['line'], s['line']), ('report page', str(e['report_page']), str(s['page'])), ('T', r['T'], s['t']),
             ('prod code', r['prod_code'], s['prod_code']), ('die', r['die'], s['die']),
             ('order width', r['order_width'], s['width']), ('order length', r['order_length'], s['length']),
             ('material+grade', ' '.join(ms[:2]), s['mat']), ('spec', ms[2] if len(ms) > 2 else '', s['mat_spec']),
             ('colours', r['colors'], s['colour']), ('thk', n(r['thk']), n(s['thk'])), ('gsm', n(r['gsm']), n(s['gsm'])),
             ('pack', r['pack_code'], s['pack']), ('# plt', n(r['num_plt']), n(s['plts'])), ('pcs/stack', n(r['pcs_per_stack']), n(s['pcs_stack'])),
             ('stk/plt', n(r['stk_per_plt']), n(s['stk_plt'])), ('weight', n(r['weight_lbs']), n(s['weight_lbs'])),
             ('in-str date', r['instr_date'], s['instr_date']), ('web width', r['web_width'], s['web_width']),
             ('cut rows', [(c['width'], c['length'], n(c['total_sheets'])) for c in r['cut_rows']], [(a, b, n(c)) for a, b, c in cuts.get(o, [])]),
             ('special instructions', norm(r['special_instructions']), norm(s['special']))]
    for k, a, b in pairs:
        checked += 1
        if a != b:
            diffs.append((e['line'], o, k, a, b))
print(f"run {info['run_date']} {info['run_time']}, {info['pages']} pages; line totals: {P.footer_check(info, rows) or 'all add up'}")
print(f'{len(sysr)} orders, {checked} fields compared, {len(diffs)} differences')
for x in diffs:
    print('DIFF', x)
