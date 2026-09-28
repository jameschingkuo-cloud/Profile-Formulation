import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1])); import config  # repo root config
import json, glob, re, os
from fractions import Fraction
# The day's packet: data/packets/packet_<PKT_DATE>.json (one file: {'ext': [...], 'cnv': [...], 'frm': [...]}),
# or PKT_JSON=<file>, or the older split page files in PKT_OUT=<dir>/ (ext_p01_04.json ...).
PKT_DATE_STR=os.environ.get('PKT_DATE')
PKT_JSON=os.environ.get('PKT_JSON') or (str(config.packet_path(PKT_DATE_STR)) if PKT_DATE_STR and config.packet_path(PKT_DATE_STR).exists() else None)
OUT=os.environ.get('PKT_OUT')
if not PKT_JSON and not OUT:
    raise SystemExit(f'No packet: set PKT_DATE=YYYY-MM-DD (file data/packets/packet_<date>.json), PKT_JSON=<file> or PKT_OUT=<dir>/. Got PKT_DATE={PKT_DATE_STR!r}')
_PK=json.load(open(PKT_JSON,encoding='utf-8')) if PKT_JSON else None
if PKT_JSON: config.record_read(PKT_JSON,'daily packet')
# ---- DOSING TYPE PER LINE (James Kuo, 26 Sep 2026) -- DO NOT CHANGE WITHOUT JAMES'S SAY-SO ----
# "line 7, 12, 13, and 16 use more modern weight based dosing. The rest of the lines use old Auger dosing.
#  ... the motor rotation speed is no RPM or some measurement. It is simply speed setting 0 to 100."
# WEIGHT : Set = weight %; each extruder adds to 100; one feeder may be "Auto" (= the balance to 100).
# AUGER  : Set = auger motor speed 0-100 (no RPM feedback); weight % only via calibration slope x setting;
#          settings are not expected to add to 100.  Same table as auger_rules.DOSING: change both together.
DOSING={'SE24':'WEIGHT','SE42':'WEIGHT','SE43':'WEIGHT','SE61':'WEIGHT',
        'SE11':'AUGER','SE12':'AUGER','SE13':'AUGER','SE21':'AUGER','SE22':'AUGER','SE23':'AUGER',
        'SE25':'AUGER','SE31':'AUGER','SE32':'AUGER'}
DOSING_LABEL={'WEIGHT':'Weight blender (Set = %)','AUGER':'Auger speed 0-100 (Set is not %)'}
def pages(prefix):
    if _PK is not None: return sorted(_PK[prefix],key=lambda p:p['scan_page'])
    P=[]
    for f in sorted(glob.glob(OUT+prefix+'_p*.json')):
        P+=json.load(open(f,encoding='utf-8'))['pages']
    return sorted(P,key=lambda p:p['scan_page'])
def num(s):
    if s is None: return None
    s=str(s).replace(',','').strip()
    try: return float(s)
    except: return None
def frac(s):
    """'31 5/8' -> 31.625 ; '17 9/16' ; '96' ; returns None if unparsable"""
    if s is None: return None
    s=str(s).strip()
    m=re.fullmatch(r'(\d+)(?:\s+(\d+)/(\d+))?',s)
    if m:
        v=Fraction(int(m.group(1)))
        if m.group(2): v+=Fraction(int(m.group(2)),int(m.group(3)))
        return float(v)
    m=re.fullmatch(r'(\d+)/(\d+)',s)
    if m: return int(m.group(1))/int(m.group(2))
    return None
def size_pair(s):
    """'49 12/16 X 44 12/16' or '31 10/16X42 4/16' or '29x44 3/8' -> (w,l)"""
    if not s: return (None,None)
    parts=re.split(r'\s*[xX]\s*',str(s).strip())
    if len(parts)!=2: return (None,None)
    return frac(parts[0]),frac(parts[1])
EXT=pages('ext'); CNV=pages('cnv'); FRM=pages('frm')
# a sheet scanned twice (same line, same page-of, identical rows) is kept once
DUP_PAGES=[]
_seen={}
for p in CNV:
    k=(p['line_code'],p.get('page_of'),json.dumps([{kk:vv for kk,vv in r.items() if kk not in ('unclear',)} for r in p['rows']],sort_keys=True))
    if k in _seen: DUP_PAGES.append((p['scan_page'],_seen[k]))
    else: _seen[k]=p['scan_page']
CNV=[p for p in CNV if p['scan_page'] not in {d for d,_ in DUP_PAGES}]
ext_rows=[]
for p in EXT:
    for r in p['rows']:
        r=dict(r); r['scan_page']=p['scan_page']; r['report_page']=p['report_page']; r['line']=p['line']; ext_rows.append(r)
cnv_rows=[]
for p in CNV:
    for r in p['rows']:
        r=dict(r); r['scan_page']=p['scan_page']; r['cnv_line']=p['line_code']; r['cnv_line_no']=p['line_no']; cnv_rows.append(r)
frm_rows=[]
for p in FRM:
    for gi,g in enumerate(p['groups']):
        for fi,f in enumerate(g['formulas']):
            frm_rows.append({'scan_page':p['scan_page'],'line_no':p['line_no'],'line':p['line_code'],'group':gi+1,
                             'orders':g['orders'],'formula_code':f['formula_code'],'feeders':f['feeders'],'note':f.get('note',''),
                             'row_in_group':fi+1,'columns':p['feeder_columns']})
