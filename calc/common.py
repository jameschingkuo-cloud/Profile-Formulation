import re, datetime
def split_codes(s, kind='product'):
    """'RPA40WB3410 & 3051, SPA40WB755' -> ['RPA40WB3410','RPA40WB3051','SPA40WB755'];
       orders: 'H62A094-2 & 1, RP24C18-1' -> ['H62A094-2','H62A094-1','RP24C18-1'];  'HQ3A274-2,3 &4' -> -2,-3,-4"""
    s = str(s or '').upper().replace(' AND ', ' & ')
    toks = [t.strip() for t in re.split(r'[&,/;+]|\s{2,}|\s(?=[A-Z]{2,}\d)', s) if t.strip()]
    out, last = [], None
    for t in toks:
        t = t.replace(' ', '')
        if kind == 'order':
            m = re.fullmatch(r'(S?[A-Z]{1,2}[0-9A-Z]{4,6})-?(\d{1,2})', t)
            if m: last = m.group(1); out.append(f'{last}-{m.group(2)}'); continue
            if re.fullmatch(r'-?\d{1,2}', t) and last: out.append(f'{last}-{t.lstrip("-")}'); continue
        else:
            m = re.fullmatch(r'([A-Z]{3}[0-9A-Z]{2}[A-Z]{2})(\d{1,5})', t)
            if m: last = m.group(1); out.append(t); continue
            if re.fullmatch(r'\d{1,5}', t) and last: out.append(last + t); continue
    return list(dict.fromkeys(out))
FORMULA_RE = re.compile(r'^([A-Z]{2}[A-Z0-9]\d{3}[A-Z]{2}[0-9A-Z]|[A-Z]{2}[A-Z0-9]\d{2}[A-Z]{3}[0-9A-Z]|SUA\d{4}[A-Z]{2}\d)$')  # std 9-char, premix 3-letter colour, PS line
def mat_key(m):
    """Broad material class used only to compare FRM text with calc text (proposed, not a master name)."""
    u = str(m or '').upper()
    if not u.strip(): return ''
    if 'TALC' in u or 'N40109' in u or 'N40108' in u or 'TL460' in u: return 'TALC'
    if 'CACO3' in u or 'CA410' in u or 'HM-10' in u: return 'CACO3'
    if '6102' in u or 'VISTA' in u: return 'VISTAMAXX'
    if 'MIX' in u and 'REC' in u: return 'MIX RECLAIM'
    if 'WB' in u and 'REC' in u: return 'WB RECLAIM'
    if 'REC' in u: return 'RECLAIM'
    if '1203' in u: return '1203K'
    if '1102' in u: return '1102K'
    if 'W26038' in u: return 'WB COLOR'
    if re.search(r'\bKS\b|KS-|KS MB|PE-500|90000F|B60009|D250|LD.?250|CR40[01]K', u): return 'KS COLOR'
    if re.search(r'6502|6520|PC ?416|PC ?716|PC ?530|PC ?5050|PC ?357|BRASKEM|TOTAL ?4252|VIRGIN|DOW-C104|C104', u): return 'VIRGIN PP'
    return str(m).strip()

def display_name(fname):
    """Workbook name without the 8-hex upload prefix a chat upload adds ('3d25b3b2-SE25_Formulation.xls' -> 'SE25_Formulation.xls')."""
    return re.sub(r'^[0-9a-f]{8}-', '', str(fname))

def superseded_copies(blocks):
    """Files to leave out: when a line has more than one calc workbook, the ones named 'Copy of ...' are older copies
    (checked 25 Sep 2026: every block in 'Copy of SE25 Formulation.xls' is also in 'SE25 Formulation.xls').
    A line whose only workbook is a copy (SE21: 'Copy of SE 21 Formulation.xls') keeps it."""
    by_line = {}
    for b in blocks:
        by_line.setdefault(b.get('line'), set()).add(b['file'])
    drop = set()
    for line, files in by_line.items():
        if len(files) > 1:
            copies = {f for f in files if 'copy' in display_name(f).lower().replace('_', ' ')}
            if copies and copies != files: drop |= copies
    return drop
