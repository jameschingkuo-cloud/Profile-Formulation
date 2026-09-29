"""Build the Profile Formulation UI prototype (published as a claude.ai Artifact, HANDOFF §7.28).

    PKT_DATE=2026-09-28 python ui/build.py     -> out/profile-formulation.html (a snapshot; not live data)

Reads the packets and out/Formulation Master.xlsx (run db/seed_master.py first, or copy the published master there).
"""
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'daily'))
sys.path.insert(0, str(ROOT / 'calc'))
import config  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from db.seed_master import MAP  # noqa: E402

LN = {'SE11': 1, 'SE12': 2, 'SE13': 3, 'SE21': 4, 'SE22': 5, 'SE23': 6, 'SE24': 7, 'SE31': 8, 'SE32': 9, 'SE25': 10,
      'SE42': 12, 'SE43': 13, 'SE61': 16}
DOS = {'SE24': 'WEIGHT', 'SE42': 'WEIGHT', 'SE43': 'WEIGHT', 'SE61': 'WEIGHT'}


def main():
    pk = {}
    for f in sorted(glob.glob(str(config.PACKETS_DIR / 'packet_*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        pk[d['packet_date']] = d
    day = os.environ.get('PKT_DATE') or max(d for d in pk if pk[d]['frm'])
    P = pk[day]
    wb = load_workbook(config.OUTPUT_DIR / 'Formulation Master.xlsx', read_only=True)

    def sheet(n):
        r = list(wb[n].iter_rows(values_only=True))
        return [dict(zip(r[0], x)) for x in r[1:]]

    mats = {m['Material ID']: {'code': m['Material Code'], 'name': m['Name'], 'st': m['IWPFT062 Status'], 'role': m['Role']}
            for m in sheet('Materials')}
    hist = {}
    for d, p in pk.items():
        for pg in p['frm']:
            for g in pg['groups']:
                for o in g['orders']:
                    hist.setdefault(o, []).append([d, pg['line_code'], [f['formula_code'] for f in g['formulas']]])
    lines = []
    for pg in sorted(P['frm'], key=lambda x: LN[x['line_code']]):
        lc = pg['line_code']
        ext = {r['order']: r for e in P['ext'] if e['line'] == lc for r in e['rows']}
        groups = [{'orders': [{'order': o, 'prod': ext.get(o, {}).get('prod_code'), 'colors': ext.get(o, {}).get('colors'),
                               'thk': ext.get(o, {}).get('thk')} for o in g['orders']],
                   'formulas': [{'code': f['formula_code'], 'note': f.get('note', ''),
                                 'feeders': [{'col': c, 'mat': v['material'], 'set': v['set'], 'id': MAP.get(v['material'])}
                                             for c, v in f['feeders'].items() if v['material'] or v['set']]}
                                for f in g['formulas']]}
                  for g in pg['groups']]
        lines.append({'code': lc, 'no': LN[lc], 'dosing': DOS.get(lc, 'AUGER'), 'cols': pg['feeder_columns'],
                      'ac': pg.get('header_note', ''), 'groups': groups, 'notes': pg.get('footnotes', [])})
    stats = json.loads(os.environ.get('UI_STATS', '{"drafted":59,"draft_match":59,"exceptions":16}'))
    stats['orders'] = sum(len(g['orders']) for ln in lines for g in ln['groups'])
    data = {'day': day, 'dates': sorted(pk),
            'scans': {'packet': P['source_scan'], 'frm': P.get('frm_source_scan') or P['source_scan']},
            'lines': lines, 'materials': mats, 'hist': hist, 'stats': stats,
            'issues': [{'sev': i['Severity'], 'line': i['Line'], 'check': i['Check'], 'detail': i['Detail']} for i in sheet('Issues')],
            'master': {'formulas': len(sheet('Formulas')), 'settings': len(sheet('Line Settings')), 'materials': len(mats),
                       'accepted': os.environ.get('UI_ACCEPTED', ''), 'changes': 0},
            'records': json.loads(os.environ.get('UI_RECORDS', '{"frm":1656,"ext":308,"cnv":270}')),
            'open': json.loads((ROOT / 'ui' / 'open_items.json').read_text(encoding='utf-8')),
            'cust': json.loads((ROOT / 'ui' / 'customer_formulas.json').read_text(encoding='utf-8'))}
    t = (ROOT / 'ui' / 'page.template.html').read_text(encoding='utf-8')
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    out = config.OUTPUT_DIR / 'profile-formulation.html'
    out.write_text(t.replace('__DATA__', blob), encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
