"""Per-product summary from the formulation calc workbooks (parsed.pkl) for the Product Master.
Latest calc block per product gives Thk, GSM, size and end use; formula codes = codes used within 365 days of the
product's latest calc run (most recent first)."""
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1])); import config  # repo root config
import pickle, json, re, datetime, collections
from common import split_codes, superseded_copies
B, R = pickle.load(open(config.WORK_DIR / 'parsed.pkl', 'rb'))
_drop = superseded_copies(B)
B = [b for b in B if b['file'] not in _drop]
def copy_no(sheet):
    m = re.search(r'\((\d+)\)\s*$', sheet); return int(m.group(1)) if m else 0
END = {'packaging': 'Packaging', 'packing': 'Packaging', 'graphic arts': 'Graphic Arts', 'graphic': 'Graphic Arts', 'garphic arts': 'Graphic Arts',
       'graphics': 'Graphic Arts', 'a/p': 'A/P', 'p/a': 'A/P', 'a & p': 'A/P', 'industrial': 'Industrial'}
per = collections.defaultdict(list)
for b in B:
    b['date'] = b['period_start'] or b['order_date']
    b['sortkey'] = (b['date'] or datetime.date(1900, 1, 1), copy_no(b['sheet']), b['row'])
    for p in split_codes(b.get('product')):
        per[p].append(b)
out = {}
for p, bl in per.items():
    bl.sort(key=lambda b: b['sortkey'])
    last = bl[-1]
    singles = [b for b in bl if len(split_codes(b.get('product'))) == 1]     # GSM / size / end use only from blocks naming this product alone
    one = singles[-1] if singles else None
    size = str((one or {}).get('size') or '').strip()
    m = re.fullmatch(r'(\d+(?:\s+\d+/\d+)?)\s*[xX]\s*(\d+(?:\s+\d+/\d+)?)', size)
    thk = last.get('thk')
    try: thk = float(thk)
    except (TypeError, ValueError): thk = None
    ld = last['date']
    recent = [b for b in reversed(bl) if not ld or not b['date'] or (ld - b['date']).days <= 365]
    codes = list(dict.fromkeys(b['formula_code'].strip() for b in recent if (b.get('formula_code') or '').strip()))
    eu = str((one or {}).get('grade') or '').strip()
    out[p] = {'thk': thk, 'gsm': (one or {}).get('gsm'), 'width': m.group(1) if m else None, 'length': m.group(2) if m else None,
              'end_use': END.get(eu.lower(), eu or None),
              'formula': codes, 'formula_last': ld.isoformat() if ld else None, 'blocks': len(bl)}
json.dump(out, open(config.WORK_DIR / 'calc_products.json', 'w', encoding='utf-8'), indent=0)
print(len(out), 'products;', sum(1 for v in out.values() if v['formula']), 'with formula codes')
