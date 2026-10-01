"""Step 2 of a day's scan: everything else, for the database - the Production Records (James Kuo, 1 Oct 2026: "do read all.
But make it two step. Get the fomulation to production team first. then read the rest for the data base update
(Production Record)").

    python daily/stage2_records.py <scan.pdf> [--date YYYY-MM-DD] [--workers N]
    python daily/stage2_records.py --compare YYYY-MM-DD      # the step-2 read against a transcribed packet

Every EXT record is read in full: the key fields as in step 1 (with each record's special instructions), and every other
column by its printed column (scan_reader/ext_fields.py: order and cut sizes, total sheets, pack code, pallets, pieces,
weight, in-str date, web width, further cut rows, the line totals). Then the logic checks:
  - the key-field checks (scan_reader/validate_read.py) and each record's own arithmetic (ext_fields.check_record);
  - the same order on the previous transcribed day: sizes, pack, pieces/stack, stacks/pallet, in-str date and web width
    do not change for an order (99.3 - 100% next day, Apr 2020 - Sep 2026). A value that breaks its printed form takes
    the previous day's, with the reason; a readable value that differs is flagged. Quantities (cut rows, pallets,
    weight) change only with the order: a changed block is accepted only when its own arithmetic holds;
  - each line's total sheets and weight against the line total the report prints.
The result is a packet draft, work/stage2/packet_<date>.json ("stage": 2) with every flag in the record's 'unclear'.
Each flag is settled by looking at the page (CLAUDE.md, Daily run step 2) before the packet goes to data/packets and the
records (daily/record.py). Converting pages are not read here yet.
"""
import argparse
import datetime
import json
import os
import sys
import time
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scan_reader'))
import config  # noqa: E402

STAGE2_DIR = config.WORK_DIR / 'stage2'
KEEP = ('order_width', 'order_length', 'pack_code', 'pcs_per_stack', 'stk_per_plt', 'instr_date', 'web_width')
QTY = ('cut_rows', 'num_plt', 'weight_lbs')


def previous(date):
    """(previous transcribed day, {(line, order): packet row})."""
    ps = sorted(p for p in config.PACKETS_DIR.glob('packet_*.json') if p.stem.split('_', 1)[1] < date)
    if not ps:
        return None, {}
    pk = json.loads(ps[-1].read_text(encoding='utf-8'))
    return pk['packet_date'], {(pg['line'], r['order']): r for pg in pk['ext'] for r in pg['rows']}


def redated(old, new, date):
    """True when an in-str date that had passed by the schedule date was moved to a later one (30 Sep 2026: five orders
    re-dated from 21 - 29 Sep)."""
    def as_date(s):
        try:
            d = datetime.datetime.strptime(f'{s}-{date[:4]}', '%d-%b-%Y').date()
        except ValueError:
            return None
        day = datetime.date.fromisoformat(date)
        return d.replace(year=d.year - 1) if (d - day).days > 200 else d.replace(year=d.year + 1) if (day - d).days > 200 else d
    a, b = as_date(old), as_date(new)
    return bool(a and b and a <= datetime.date.fromisoformat(date) and b > a)


def with_previous(f, gsm, p, pday, date):
    """The previous day's same order -> notes; f is repaired in place where the read breaks its form."""
    import ext_fields as F
    notes = []
    probs = '; '.join(F.check_record(f, gsm))
    for k in KEEP:
        if str(f.get(k, '')) == str(p.get(k, '')):
            continue
        if k == 'instr_date' and redated(p.get(k, ''), f.get(k, ''), date):
            notes.append(f"in-str date {p.get(k)} had passed: now {f.get(k)}")
            continue
        if f"{k} '" in probs or (k == 'instr_date' and 'in-str date' in probs) or (k == 'pack_code' and 'pack code' in probs):
            notes.append(f"{k} read '{f.get(k, '')}' (not a printed form): '{p.get(k, '')}' from {pday}")
            f[k] = p.get(k, '')
        else:
            notes.append(f"CHECK {k} '{f.get(k, '')}' differs from {pday} '{p.get(k, '')}'")
    qa = (f['cut_rows'], f['num_plt'], f['weight_lbs'])
    qb = (p.get('cut_rows') or [], p.get('num_plt', ''), p.get('weight_lbs', ''))
    if json.dumps(qa) != json.dumps(qb):
        if F.check_record(f, gsm):
            g = dict(f, cut_rows=qb[0], num_plt=qb[1], weight_lbs=qb[2])
            if not F.check_record(g, gsm):
                notes.append(f"cut rows / pallets / weight read do not add up; {pday}'s do: taken from {pday} - "
                             f"read {qa[0]} {qa[1]} {qa[2]}")
                f.update(cut_rows=qb[0], num_plt=qb[1], weight_lbs=qb[2])
        else:
            notes.append(f'quantities changed since {pday} (they add up): {qb[1]} -> {qa[1]} pallets, {qb[2]} -> {qa[2]} lb')
    return notes


def footer(dec, info):
    """A page's line total (PCs, LBs) read by column, or None."""
    import ext_fields as F
    cells = info.get('footer_cells')
    if not cells:
        return None
    by = {c[0]: c for cs in cells.values() for c in cs}
    pcs = F.read_number(dec, by, F.NUM_END['total'])[0]
    lbs = F.read_number(dec, by, F.NUM_END['weight'])[0]
    return F.number(pcs), F.number(lbs)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('scan', nargs='?'); ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--workers', type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    ap.add_argument('--compare', metavar='DATE')
    ap.add_argument('--fields-bank', help='another glyph bank for the other columns (testing on a day the bank has not seen)')
    a = ap.parse_args(argv)
    if a.compare:
        return compare(a.compare)
    if not a.scan:
        ap.error('the scan PDF is needed')
    import ext_scan_reader as R
    import ext_fields as F
    import validate_read as V
    t0 = time.time()
    config.record_read(a.scan, 'daily schedule scan (step 2: records)')
    key_bank = R.Bank.load(str(ROOT / 'scan_reader' / 'glyph_bank.npz'))
    fields_bank = F.load_bank(a.fields_bank)
    infos = R.read_pages(a.scan, instructions_crop=True, workers=a.workers, fields=True)
    rows = R.read_scan(a.scan, key_bank, fields_bank=fields_bank, infos=infos)
    t_read = time.time() - t0
    out, dropped, gone, prev_day = V.validate(a.date, rows)
    pday, prev = previous(a.date)
    dec = R.Decoder(fields_bank)
    totals = {}
    for i, info in enumerate(infos, 1):
        ft = footer(dec, info)
        if ft:
            totals[i] = ft
    pages, by_line = OrderedDict(), defaultdict(list)
    n_flag = 0
    for r in out:
        f = r.get('fields')
        notes = [x for x in (r.get('checks'), r.get('flags')) if x]
        notes += r.get('field_flags') or []
        if f is None:
            p = prev.get((r['line'], r['order']))
            f = {k: (p or {}).get(k, '') for k in ('T', 'order_width', 'order_length', 'pack_code', 'num_plt', 'pcs_per_stack',
                                                    'stk_per_plt', 'weight_lbs', 'instr_date', 'web_width')}
            f['cut_rows'] = [dict(c) for c in (p or {}).get('cut_rows') or []]
            notes.append("CHECK the record line's other columns could not be read (handwriting?): "
                         + (f"the same order's on {pday} filled in" if p else 'left blank'))
        else:
            notes += F.check_record(f, r['gsm'])
            p = prev.get((r['line'], r['order']))
            if p:
                notes += with_previous(f, r['gsm'], p, pday, a.date)
        by_line[r['line']].append(f)
        unclear = '; '.join(notes)
        n_flag += bool(unclear)
        pg = pages.setdefault((int(r['scan_page']), r['line']), {
            'scan_page': int(r['scan_page']), 'report_page': str(r['report_page'] or ''), 'line': r['line'],
            'run_date': infos[int(r['scan_page']) - 1].get('run_date', ''), 'run_time': infos[int(r['scan_page']) - 1].get('run_time', ''),
            'carryover_top': '', 'rows': [], 'line_total_pcs': '', 'line_total_lbs': '', 'final_total': '',
            'page_notes': 'step 2: read from the scan'})
        pg['rows'].append({'T': f['T'], 'order': r['order'], 'prod_code': r['prod'], 'die': r['die'],
                           'order_width': f['order_width'], 'order_length': f['order_length'],
                           'mat_spec': ' '.join(x for x in (r['mat'], r['grade'], r['spec']) if x), 'colors': r['colors'],
                           'thk': r['thk'], 'gsm': f"{int(r['gsm']):,}" if str(r['gsm'] or '').isdigit() else r['gsm'],
                           'cut_rows': f['cut_rows'], 'pack_code': f['pack_code'], 'num_plt': f['num_plt'],
                           'pcs_per_stack': f['pcs_per_stack'], 'stk_per_plt': f['stk_per_plt'], 'weight_lbs': f['weight_lbs'],
                           'instr_date': f['instr_date'], 'web_width': f['web_width'],
                           'special_instructions': r.get('special', ''), 'handwritten': '', 'unclear': unclear})
    # line totals: on the line's last page
    line_notes = []
    for (sp, line), pg in pages.items():
        if sp in totals and pg is [p for (s, l), p in pages.items() if l == line][-1]:
            pcs, lbs = totals[sp]
            pg['line_total_pcs'], pg['line_total_lbs'] = (f'{pcs:,}' if pcs else ''), (f'{lbs:,}' if lbs else '')
            fs = by_line[line]
            s_pcs = sum(F.number(c['total_sheets']) or 0 for f in fs for c in f['cut_rows'])
            s_lbs = sum(F.number(f['weight_lbs']) or 0 for f in fs)
            ok = (s_pcs == pcs, s_lbs == lbs)
            line_notes.append(f"{line}: total sheets {s_pcs:,} vs printed {pcs or '?'} {'OK' if ok[0] else 'CHECK'}; "
                              f"weight {s_lbs:,} vs printed {lbs or '?'} {'OK' if ok[1] else 'CHECK'}")
            if not all(ok):
                pg['page_notes'] += f'; CHECK line total: read rows add up to {s_pcs:,} PCs / {s_lbs:,} LBs, printed {pcs} / {lbs}'
    pk = {'packet_date': a.date, 'source_scan': Path(a.scan).name, 'stage': 2, 'ext': list(pages.values()), 'cnv': [], 'frm': [],
          'frm_source_scan': '', 'stage2': {'read_seconds': round(t_read), 'rows': len(out), 'rows_flagged': n_flag,
                                            'previous_day': pday, 'line_totals': line_notes,
                                            'dropped': [list(x) for x in dropped],
                                            'not_read_today': [f'{l} {o}' for l, o in gone]}}
    STAGE2_DIR.mkdir(parents=True, exist_ok=True)
    dest = STAGE2_DIR / f'packet_{a.date}.json'
    dest.write_text(json.dumps(pk, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'step 2 read in {t_read:.0f} s: {len(out)} records, {n_flag} with a note to settle; previous day {pday}; packet {dest}')
    for x in line_notes:
        print('  ', x)
    return 0


def compare(date):
    """The step-2 packet against the transcribed packet of the same day, field by field."""
    import ext_fields as F
    s2p, full = STAGE2_DIR / f'packet_{date}.json', config.packet_path(date)
    a, b = json.loads(s2p.read_text(encoding='utf-8')), json.loads(full.read_text(encoding='utf-8'))
    rows = lambda pk: {(pg['line'], r['order']): r for pg in pk['ext'] for r in pg['rows']}
    ra, rb = rows(a), rows(b)
    from collections import Counter
    c, diff = Counter(), []
    keys = ('T', 'prod_code', 'die', 'order_width', 'order_length', 'mat_spec', 'colors', 'thk', 'gsm', 'cut_rows', 'pack_code',
            'num_plt', 'pcs_per_stack', 'stk_per_plt', 'weight_lbs', 'instr_date', 'web_width', 'special_instructions')
    norm = lambda k, v: (json.dumps([{x: str(y) for x, y in d.items()} for d in v], sort_keys=True) if k == 'cut_rows'
                         else ' '.join(str(v).split()) if k == 'special_instructions'      # spacing is not read
                         else f'{float(v):.1f}' if k == 'thk' and str(v).replace('.', '').isdigit() else str(v).strip())
    for key, t in rb.items():
        r = ra.get(key)
        if r is None:
            diff.append((key, 'missing in step 2', '', ''))
            continue
        for k in keys:
            ok = norm(k, r.get(k, '')) == norm(k, t.get(k, ''))
            c[(k, ok)] += 1
            if not ok:
                diff.append((key, k, r.get(k, ''), t.get(k, ''), 'flagged' if r.get('unclear') else 'NOT FLAGGED'))
    print(f'step 2 vs transcribed {date}: {len(ra)} / {len(rb)} records')
    for k in keys:
        n = c[(k, True)] + c[(k, False)]
        print(f'  {k:<22} {c[(k, True)]}/{n}')
    for d in diff:
        print('   ', d[0], '|', *[str(x)[:120] for x in d[1:]])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
