"""FRM Draft <date>: propose the day's formulation from what was last issued, for Tech to check and sign.

    PKT_DATE=2026-09-28 python daily/resolve.py

For every order on the day's EXT schedule (data/packets/packet_<PKT_DATE>.json) it looks for the formulation
last ISSUED for that same order on that same line, in the FRM pages of earlier packets (data/packets/*.json).

  * Found  -> Draft rows (every formula of that order: primary and alternates, as last issued), marked with the
              date they were issued.
  * Not found -> Exceptions, for an engineer. When the same product (or the RUN WITH partner product) had a
              formula on that line, it is shown there as a suggestion only; it never goes into the Draft, because
              the formula can depend on the order (VOIDFORM, sign blank, corn box, rolls) (HANDOFF §6.3, §7.4).

Nothing is guessed and nothing is issued: the workbook is a draft until Tech signs it (HANDOFF standing
instructions). This is the first cut of the resolve step (docs/DATABASE.md §3 step 6); once the Formulation
Master holds approved Product to Formula rows it becomes the primary source and this history lookup the check.
"""
import datetime
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

PKT = os.environ.get("PKT_DATE")   # checked in main(), so daily/record.py can import variant() and split_feeder()
RUN_DATE = os.environ.get("RUN_DATE") or datetime.date.today().isoformat()
RULES = os.environ.get("ASSIGN_RULES", "1") != "0"   # ASSIGN_RULES=0: history only (backtests of the pre-rule behaviour)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import assign  # noqa: E402

RECLAIM_OUT = re.compile(r'reclaim\b[^()]*?\brun\s*out', re.I)     # Tech's "(Use this formula in case PP WB Reclaim is run out)"

VARIANT_RULES = [  # note text on the FRM row -> variant (db/schema.py VARIANTS)
    (re.compile(r"run\s*out", re.I), "Reclaim run-out"),
    (re.compile(r"void\s*form", re.I), "VOIDFORM"),
    (re.compile(r"sign\s*blank", re.I), "Sign blank"),
    (re.compile(r"corn\s*box", re.I), "Corn box"),
    (re.compile(r"roll", re.I), "Roll"),
]
RUN_WITH = re.compile(r"RUN\s+WI(?:TH|HT)\s+([A-Z]{3}[0-9A-Z]{2}[A-Z]{2}\d+)", re.I)   # "RUN WIHT" printed 28 Sep
RUN_WITH_NEXT = re.compile(r"RUN\s+WI(?:TH|HT)\s+NEXT", re.I)


def run_with(today, pre):
    """RUN WITH: orders that run side by side on one sheet (cut to size after) take one formulation, and sign blank
    supersedes the regular white formula (James Kuo, 27 Oct 2026: "If it says run with next. put them the same formula and
    sign blank superseed regular white formula"; asked about RUN WITH <product>: "pair them the same way"). RUN WITH NEXT
    links an order to the next one on the line; RUN WITH <product> to that product's orders on the line. Linked orders form
    one group (SE24 RP26803-2 runs with two orders), and the strictest formulation wins: the one whose order has every
    qualifier the others have. No single strictest: each keeps its own and the note says to check. Changes
    pre[(line, order)] = (fm, why) in place."""
    by_line = {}
    for pg in today["ext"]:
        by_line.setdefault(pg["line"], []).extend(pg["rows"])
    for line, rows in by_line.items():
        group = {r["order"]: {r["order"]} for r in rows}
        def link(a, b):
            g = group[a] | group[b]
            for o in g:
                group[o] = g
        for i, r in enumerate(rows):
            si = r.get("special_instructions") or ""
            if RUN_WITH_NEXT.search(si):
                partners = rows[i + 1:i + 2]
            elif RUN_WITH.search(si):
                prod = RUN_WITH.search(si).group(1).upper()
                partners = [x for x in rows if x.get("prod_code") == prod and x is not r]
            else:
                continue
            for p in partners:
                link(r["order"], p["order"])
        done = set()
        for o, g in group.items():
            if len(g) < 2 or o in done:
                continue
            done |= g
            fms = {x: (pre.get((line, x)) or (None, ""))[0] for x in g}
            fms = {x: f for x, f in fms.items() if f}
            codes = {x: [m["code"] for m in f["members"]] for x, f in fms.items()}
            if len({tuple(c) for c in codes.values()}) < 2:
                continue
            q = {x: set(f["want"]) & set(assign.QMARK) for x, f in fms.items()}
            top = [x for x in fms if all(q[y] <= q[x] for y in fms)]
            if not top or len({tuple(codes[x]) for x in top}) > 1:
                for x, f in fms.items():
                    others = ", ".join(sorted(g - {x}))
                    pre[(line, x)] = (dict(f, run_with=f"RUN WITH {others}: different formulation, engineer to check"), "")
                continue
            so = sorted(top)[0]
            strong = fms[so]
            for x, f in fms.items():
                if codes[x] != codes[so]:
                    pre[(line, x)] = (dict(strong, want=f["want"], how=f"{strong['how']}; RUN WITH {so}: the stricter formulation of the group",
                                           run_with=f"RUN WITH {so}: same sheet, same formulation"), "")


def variant(note, first):
    for rx, name in VARIANT_RULES:
        if rx.search(note or ""):
            return name
    return "Primary" if first else "Other"


def split_feeder(col):
    col = col.replace("Extruder ", "").strip()
    m = re.fullmatch(r"([A-D]) (.+)", col)
    return (m.group(1), m.group(2)) if m else ("", col)


def load_packets():
    out = {}
    for p in config.packet_files():
        config.record_read(p, "daily packet")
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d.get("packet_date") or p.stem.split("_", 1)[1]] = d
    return out


def _rp26b03_2(line, order, product):
    """James Kuo, 4 Nov 2026, SE23 RP26B03-2 (RPP40WB1625 floor cover, normally RU0000WB4 100% reclaim): "put this
    formulation on today only ... PP, talc, wb reclaim, WB, caco3 as 53,7,32,3,5" - "we are running low on reclaim". The
    W% on SE23's hopper calibration (slopes 219.1 / 148.7 / 87.2 / 17.5 / 30.7 g/min per unit), the highest at 90."""
    why = ("James Kuo, 4 Nov 2026: reclaim running low, today only - W% PP 53 / talc 7 / WB reclaim 32 / WB 3 / CaCO3 5, "
           "settings from SE23's calibration (highest 90)")
    src = "James Kuo, 4 Nov 2026 (W% given in chat; SE23 calibration slopes)"
    note = "For 11/4 only (reclaim running low), in place of RU0000WB4 · W% PP 53 / talc 7 / WB reclaim 32 / WB 3 / CaCO3 5"
    feed = [('Hopper 1', 'PP Virgin-silo 4 (6502A)', '59'), ('Hopper 2', 'HiTalc ZS (or N40109A)', '12'),
            ('Hopper 3', 'PP WB Reclaim', '90'), ('Hopper 4', 'WB-W26038A', '42'), ('Hopper 5', 'CaCO3 -Heritage HM-10MAX', '40')]
    return [[line, order, product, 'SPECIAL', 'Main', '', f, None, m, st, None, why, None, src, 1, note] for f, m, st in feed]


# formulations James sets for one day only: (packet date, line, order) -> rows
DAY_ONLY = {('2026-11-04', 'SE23', 'RP26B03-2'): _rp26b03_2}

PRODUCT_ISSUE = {}      # (line, product) -> Tech's last issue for it (issued_history), set in main
# (line, the rules' Main) -> the code Tech runs for that job on the line, where the Main has no settings there and the
# product was never issued on the line (2 Nov 2026, from Tech's Word running records: SE43 has no reclaim feeder)
LINE_STANDIN = {('SE43', 'FU0031WB4'): 'FU0151WB4', ('SE43', 'FU0032WB3'): 'FU0151WB3', ('SE43', 'FUA152WB4'): 'FUA151WB4'}


def issue_day(date):
    """An issue date; a Word-record month (YYYY-MM-00) as its first day."""
    return datetime.date.fromisoformat(str(date)[:8] + '01' if str(date).endswith('-00') else str(date))


def frm_src(date, page):
    """Where an issued formulation comes from: a day's FRM page, or a month of Tech's Word running record (date YYYY-MM-00)."""
    if str(date).endswith('-00'):
        return f"Tech's Word record {date[:7]}" + (f" (L{int(page):02d})" if isinstance(page, (int, str)) and str(page).isdigit() else '')
    return f"FRM {date} scan p{page}"


def history_packets(before=None):
    """Tech's issues kept outside the daily packets (data/frm_history: the Word running records of every line, 2009 on,
    one entry per issue month, and older days' FRM pages read from scans), in the packet layout, keyed by date. James
    Kuo, 2 Nov 2026: "update what you can, if anything missing, you can assign formulation"."""
    out = {}
    if os.environ.get('FRM_HISTORY') == '0':          # tests pinned to the packets alone
        return out
    for p in sorted((config.ROOT / 'data' / 'frm_history').glob('*.json')):
        config.record_read(p, "Tech's issued formulations kept outside the daily packets")
        for pk in json.loads(p.read_text(encoding='utf-8')):
            # a month of the Word records holds that whole month's issues: a backtest ("as that morning") takes only
            # months before its own
            if before is None or pk['packet_date'] < str(before)[:8] + '00':
                out.setdefault(pk['packet_date'], pk)
    return out


_ORDER_PRODUCT = {}


def order_products():
    """order -> product from the Extrusion Production Record (every schedule since 2020): the product of an order in
    Tech's Word running records, which print none."""
    if not _ORDER_PRODUCT:
        from openpyxl import load_workbook
        p = config.published_path('Extrusion Production Record.xlsx')
        if p and p.exists():
            config.record_read(p, 'Extrusion Production Record (order -> product)')
            ws = load_workbook(p, read_only=True)['Orders by Day']
            it = ws.iter_rows(values_only=True); h = {k: i for i, k in enumerate(next(it))}
            for r in it:
                if r[h['Order']] and r[h['Product Code']]:
                    _ORDER_PRODUCT[r[h['Order']]] = r[h['Product Code']]
        _ORDER_PRODUCT.setdefault('', '')
    return _ORDER_PRODUCT


def issued_history(packets, before=None):
    """(line, order) -> (issue date, scan page, [formula dicts]); product -> same, keyed (line, product).
    Every issued FRM on file, whatever the schedule's date (James Kuo, 30 Sep 2026: "Always provide up to date
    formulation. even if someone give you an past schedule"); `before` only for callers that need an earlier view."""
    by_order, by_product = {}, {}
    for date in sorted(d for d in packets if before is None or d < before):
        pk = packets[date]
        prod_of = {r["order"]: r["prod_code"] for pg in pk["ext"] for r in pg["rows"]} or order_products()
        for pg in pk["frm"]:
            for g in pg["groups"]:
                for o in g["orders"]:
                    rec = (date, pg["scan_page"], g["formulas"])
                    by_order[(pg["line_code"], o)] = rec          # later dates overwrite: the latest issue wins
                    if o in prod_of:
                        by_product[(pg["line_code"], prod_of[o])] = rec + (o,)
    return by_order, by_product


def uses_reclaim(f):
    return any("reclaim" in (v.get("material") or "").lower() and _num(v.get("set")) > 0 for v in f["feeders"].values())


def _num(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def run_order(formulas):
    """Reclaim formulas first, then the ones without reclaim, a note saying 'run out' last; page order otherwise (James Kuo, 30 Sep 2026: 'the one with reclaim first. we always want to use up our scrap first before using Virgin PP')."""
    return sorted(formulas, key=lambda f: (bool(re.search(r"run\s*out", f.get("note") or "", re.I)), not uses_reclaim(f)))


def draft_rows(line, order, product, rec, names=None):
    """names: printed code -> the code to show (James, 23 Oct 2026: "Don't use old formula code in the print out"). With
    the rules on, an old name James renamed shows as his name; the name Tech printed stays in Source."""
    date, page, formulas = rec
    formulas = run_order(formulas)
    rows = []
    for i, f in enumerate(formulas):
        var = variant(f.get("note", ""), i == 0)
        printed = f["formula_code"]
        shown = (names or {}).get(printed) or (assign.current_name(printed) if RULES else printed)
        src = (f"Tech's calc sheet, last run {date}" if page == 'calc' else frm_src(date, page)) + (f" (printed as {printed})" if shown != printed else "")
        for col, v in f["feeders"].items():
            if not (v.get("material") or v.get("set")):
                continue
            ext, feeder = split_feeder(col)
            rows.append([line, order, product, shown, var, ext, feeder, None, v.get("material", ""),
                         v.get("set", ""), None, "Last issued (same order, same line)",
                         issue_day(date), src, i + 1, f.get("note", "")])
    return rows


def approved_master():
    """Engineer decisions from the Formulation Master (James Kuo, 29 Sep 2026: an Exception is completed by an engineer
    in the database, then the run is repeated). Only APPROVED Product to Formula rows are used, with that line's
    settings; the master is pre-flighted first (hard rule). Returns {(line, product): [formula dicts in run order]}."""
    from db import preflight, schema
    pub = config.published_path(schema.FM)
    if not (pub and pub.exists()):
        return {}, None
    ok, lines, (cur, _log) = preflight.check(schema.FM)
    if ok is None:            # no accepted version yet: cannot vouch for it, so do not use it
        print("Formulation Master has no accepted version (db/preflight.py accept --baseline); not used for this draft.")
        return {}, None
    if ok is False:
        print("\n".join(lines))
        raise SystemExit("STOP: the Formulation Master has changes without an approved Change Log row. Nothing built.")
    mats = cur["Materials"]
    text = {k: (m.get("FRM Text") or m.get("Name") or k) for k, m in mats.items()}
    notes = {(f["Formula Code"], f["Variant"]): f.get("When to Use") or "" for f in cur["Formulas"].values()}
    settings = {}
    for s in cur["Line Settings"].values():
        settings.setdefault((s["Line Code"], s["Formula Code"], s["Variant"]), []).append(s)
    out = {}
    for p in cur["Product to Formula"].values():
        if p["Status"] != "Approved":
            continue
        key = (p["Line Code"], p["Formula Code"], p["Variant"])
        if key not in settings:
            continue          # approved, but no settings on this line: stays an Exception (reason says so)
        rows = settings[key]
        reclaim = sum(float(s["Set"]) for s in rows if "RCL" in (s["Material ID"] or "") and s["Set"].replace(".", "", 1).isdigit())
        out.setdefault((p["Line Code"], p["Product Code"]), []).append({
            "formula_code": p["Formula Code"], "variant": p["Variant"], "note": notes.get((p["Formula Code"], p["Variant"]), ""),
            "approved_by": p.get("Approved By") or "", "rank": (p["Priority"] != "Primary", p["Variant"] == "Reclaim run-out", -reclaim),
            "feeders": {(s["Extruder"] + " " + s["Feeder"]).strip(): {"material": text.get(s["Material ID"], s["Material ID"]), "set": s["Set"]}
                        for s in rows}})
    for k in out:
        out[k].sort(key=lambda f: f["rank"])
    return out, pub


def master_rows(line, order, product, formulas):
    rows = []
    for i, f in enumerate(formulas):
        for col, v in f["feeders"].items():
            ext, feeder = split_feeder(col)
            rows.append([line, order, product, f["formula_code"], f["variant"], ext, feeder, None, v["material"], v["set"], None,
                         "Product to Formula", None, f"Formulation Master, approved by {f['approved_by']}", i + 1, f["note"]])
    return rows


def main():
    if not PKT:
        raise SystemExit("Set PKT_DATE=YYYY-MM-DD")
    packets = load_packets()
    if PKT not in packets:
        raise SystemExit(f"No packet for {PKT} in {config.PACKETS_DIR}")
    today = packets[PKT]
    # HISTORY_BEFORE is for backtests only ("as that morning, before Tech issued"); normal runs use every issue on file
    cut = os.environ.get("HISTORY_BEFORE") or None
    hist = history_packets(cut)                                          # Tech's Word records and older scanned days
    by_order, by_product = issued_history({**hist, **packets}, cut)      # latest issue on file, any date
    PRODUCT_ISSUE.clear(); PRODUCT_ISSUE.update(by_product)
    history_dates = sorted(d for d in packets if packets[d]["frm"] and (cut is None or d < cut))
    approved, _ = approved_master()
    seen_pk = {d: p for d, p in packets.items() if cut is None or d < cut}     # backtests: only what was issued by then
    issued = assign.issued_on_line({**hist, **seen_pk}) if RULES else {}
    if RULES:
        assign.set_pages(seen_pk)            # the lines' feeder columns and wording, for settings taken from the calc sheets

    draft, exceptions, by_rule, to_set = [], [], [], []
    pre = {}                                     # (line, order) -> the rules' (formulation, why), before RUN WITH pairs
    if RULES:
        for pg in today["ext"]:
            for r in pg["rows"]:
                if not r.get("read_check") and (pg["line"], r["prod_code"]) not in approved:
                    pre[(pg["line"], r["order"])] = assign.formulation(pg["line"], r, datetime.date.fromisoformat(PKT), issued,
                                                                       own=by_order.get((pg["line"], r["order"])))
        run_with(today, pre)
    for pg in today["ext"]:
        for r in pg["rows"]:
            line, order, product = pg["line"], r["order"], r["prod_code"]
            if r.get("read_check"):              # step 1 from the scan: the order or product could not be confirmed
                exceptions.append([line, order, product, r.get("mat_spec", ""), r.get("colors", ""), r.get("thk", ""),
                                   r.get("gsm", ""), (r.get("special_instructions") or "")[:160],
                                   f"Scan read not certain - check the order and product on the paper: {r['read_check']}", "", None, None])
                continue
            rec = by_order.get((line, order))
            if rec and not RULES:                # ASSIGN_RULES=0: the pre-23-Oct draft, each order as last issued
                draft += draft_rows(line, order, product, rec)
                continue
            if (line, product) in approved:      # an engineer decided it in the master: outranks the rules
                draft += master_rows(line, order, product, approved[(line, product)])
                continue
            # The rules (James Kuo, 23 Oct 2026: "Moving forward, including today we use logic base formulation process.
            # Remove old logic and apply new"; "No history process. If logic don't work, ask engineering for help"):
            # daily/assign.py formulation() - James's Primary and its Secondary, both printed ("let the production team
            # ... decide whether we have enough of particular material"), each with its rows from this order's own last
            # issue, else the line's, else Tech's calc sheet; a member without settings on the line prints "ENGINEER TO
            # SET" under its code (every member, when none has settings here yet). VOIDFORM: never reclaim.
            fm, why = pre[(line, order)] if RULES else (None, 'rules off')
            if fm:
                rows_, marked, missing = rule_rows(line, order, product, fm)
                draft += rows_
                if marked:
                    by_rule.append([line, order, product, ' + '.join(x['code'] for x in fm['members']), fm['how'], marked])
                for x in missing:
                    w = ", ".join(f"{k.split(' ')[0]} {v:g}" for k, v in ((x['member'] or {}).get('w') or {}).items() if v)
                    to_set.append([line, order, product, x['code'], x['role'], fm['how'], w,
                                   f"{', '.join(f['formula_code'] for f in rec[2])} on {rec[0]}" if rec else ""])
                continue
            src_rec = (rec[:3] + (order,)) if rec else by_product.get((line, product))
            if RULES and src_rec:
                # the rules cannot decide (no Main for the key, several Mains, a spec with no rule): the formulation Tech
                # last issued for this order, else for this product, on this line (James Kuo, 2 Nov 2026: "update what you
                # can, if anything missing, you can assign formulation")
                rr = draft_rows(line, order, product, src_rec[:3])
                for x in rr:
                    x[11] = (f"Assigned: rules cannot decide ({why}); as Tech last issued for "
                             + ("this order" if rec else f"{product} on {line} (order {src_rec[3]})") + " (James Kuo, 2 Nov 2026)")
                    x[15] = ((x[15] + ' · ') if x[15] else '') + ("as Tech last issued for this order" if rec else
                                                                  f"as Tech last issued for this product on {line}")
                draft += rr
                by_rule.append([line, order, product, ' + '.join(dict.fromkeys(f['formula_code'] for f in src_rec[2])),
                                f"assigned from Tech's last issue ({why})", issue_day(src_rec[0])])
                continue
            hint = why if why else ""
            if rec:
                hint = f"Rules cannot decide ({why}); last issued for this order as {', '.join(f['formula_code'] for f in rec[2])} on {rec[0]} - ask engineering"
            hint0 = hint
            hint = ""
            prod_rec = by_product.get((line, product))
            m = RUN_WITH.search(r.get("special_instructions", ""))
            partner = by_product.get((line, m.group(1).upper())) if m else None
            if partner:
                codes = ", ".join(f["formula_code"] for f in partner[2])
                hint = f"RUN WITH {m.group(1).upper()}: that product last ran here as {partner[3]} ({partner[0]}) with {codes}"
            elif prod_rec:
                codes = ", ".join(f["formula_code"] for f in prod_rec[2])
                hint = f"Same product last ran here as {prod_rec[3]} ({prod_rec[0]}) with {codes}"
            hint = " | ".join(h for h in (hint0, hint) if h)
            other = sorted({ln for (ln, o) in by_order if o == order and ln != line})
            reason = "New order on this line: no formula issued for it before"
            if other:
                reason = f"Order was issued on another line before ({', '.join(other)}), not on {line}"
            if RULES and why and not why.startswith("rules off"):       # the rules' reason first, the history only as context
                reason = f"Rules cannot decide: {why}; " + ("issued for this order on this line before (see the suggestion)" if rec
                                                             else reason[0].lower() + reason[1:])
            exceptions.append([line, order, product, r.get("mat_spec", ""), r.get("colors", ""), r.get("thk", ""),
                               r.get("gsm", ""), (r.get("special_instructions") or "")[:160], reason, hint, None, None])

    today_orders = {(pg["line"], r["order"]) for pg in today["ext"] for r in pg["rows"]}
    last = max((d for d in history_dates if d < PKT), default=None)     # "dropped since" = vs the previous issue
    dropped = sorted({(pg["line_code"], o) for pg in packets[last]["frm"] for g in pg["groups"] for o in g["orders"]}
                     - today_orders) if last else []

    write(today, draft, exceptions, dropped, last, history_dates, by_rule, to_set)


def rule_rows(line, order, product, fm):
    """Draft rows for a formulation decided by the rules (assign.formulation): the Primary, then its Secondary (R9), each
    member's formula rows in run order (reclaim first, a run-out note last: James Kuo, 30 Sep 2026), under James's name
    with its role and where its settings came from; a member without settings on the line gets one row "ENGINEER TO SET"
    in its place. -> (rows, settings date of the rows proposed from the line or None, members without settings)."""
    entries, missing, took = [], [], None
    rec = PRODUCT_ISSUE.get((line, product))
    for x in fm['members']:
        if x['rows']:
            entries += run_order([dict(f, _x=x) for f in x['rows']])
        elif rec and took is None and x['role'] == 'Primary':
            # the rules' Main has no settings on this line: the formulation Tech last issued for this product on this
            # line, under its current name (James Kuo, 2 Nov 2026: "if anything missing, you can assign formulation") -
            # e.g. SE43 makes packaging white 4 mm as FU0151WB4 (no reclaim feeder), not the reclaim Main FU0031WB4
            took = dict(x, src=('product', rec[0], rec[1]), member=None, shown=None, rules_code=x['code'], from_order=rec[3])
            entries += run_order([dict(f, _x=took) for f in rec[2]])
        elif took is not None:
            continue                          # Tech's issue carries its own run-out row
        elif x['role'] == 'Primary' and (line, x['code']) in LINE_STANDIN and took is None:
            # never issued for this product on this line: the code Tech runs for that job on the line, its newest group
            # (with the order's qualifier note first) - SE43 cannot feed reclaim, so its packaging white is FU0151WB4
            code = LINE_STANDIN[(line, x['code'])]
            gs = sorted(assign._ISSUED_GROUPS.get((line, code), []), key=lambda g: (any(q in (fm.get('want') or ()) for f in g[2]
                        for q in assign.quals(f.get('note', ''))), g[0]), reverse=True)
            if gs:
                took = dict(x, src=('standin', gs[0][0], gs[0][1]), member=None, shown=None, rules_code=x['code'], from_order=code)
                entries += run_order([dict(f, _x=took) for f in gs[0][2] if f['formula_code'] == code] or [dict(gs[0][2][0], _x=took)])
            else:
                missing.append(x)
                entries.append(dict(formula_code=x['code'], feeders={}, note='', _x=x))
        else:
            missing.append(x)
            entries.append(dict(formula_code=x['code'], feeders={}, note='', _x=x))
    rows, marked = [], None
    for i, f in enumerate(entries):
        x = f['_x']
        kind, date, page = x['src'] or (None, None, None)
        printed = f['formula_code']
        shown = x.get('shown') or (x['code'] if x['member'] else assign.current_name(printed))
        if not f['feeders']:                 # a member without settings on this line
            rows.append([line, order, product, shown, x['role'], None, None, None, None, None, None,
                         f"Proposed by rule ({fm['how']}); no settings for {shown} on {line}: engineer to set", None,
                         f"no settings for {shown} on {line} (no FRM page on file, no calc sheet)", i + 1,
                         f"ENGINEER TO SET: settings for {shown} on {line} · {x['role']}"])
            continue
        src = (f"Tech's {line} calc sheet, last run {date}" if kind == 'calc' else frm_src(date, page)) + \
              (f" (printed as {printed})" if shown != printed else "")
        if kind == 'calcd':                  # worked out from the line's augers (assign.r4_black_settings), never issued
            d = page
            src = f"CALCULATED from {d['template']}; slopes {d['slopes'][0]:g} / {d['slopes'][1]:g} g/min per unit"
            how = (f"Proposed by rule ({fm['how']}); settings CALCULATED for R4 black: {d['share'][0]:g}% black reclaim + "
                   f"{d['share'][1]:g}% black colour (James Kuo, 24 Oct 2026), {d['basis']}, {d['T']:,.0f} g/min")
            note = (f"{x['role']} · CALCULATED SETTINGS, check before running · "
                    f"R4 black {d['share'][0]:g}% reclaim / {d['share'][1]:g}% colour")
            marked = marked or 'calculated'
            date = None
        elif kind == 'calcw':                # the W% on the line's auger calibration (assign.calc_auger_settings), never issued
            d = page
            src = f"CALCULATED from the W% of {shown} on {line}'s auger calibration; throughput of {d['template']}, {d['T']:,.0f} g/min"
            how = f"Proposed by rule ({fm['how']}); settings CALCULATED: W% x {d['T']:,.0f} g/min / each hopper's slope"
            note = f"{x['role']} · CALCULATED SETTINGS, check before running"
            marked = marked or 'calculated'
            date = None
        elif kind == 'w':                    # weight-by-weight line: the W% on James's feeder layout (assign.w_settings)
            src = f"W% Master {shown}: {line} weight by weight, {', '.join(c for c, _, _ in assign.W_LAYOUT[line])} (James Kuo, 26 Oct 2026)"
            how = f"Proposed by rule ({fm['how']}); settings = the W% on {line} (weight by weight)"
            note = x['role'] + " · settings from the W%" + \
                (f" · no CaCO3 on {line} (virgin PP takes its share)" if (page or {}).get('no_caco3') else "")
            date = None
        elif kind == 'confirmed':            # calculated once, then checked by James (assign.CONFIRMED_SETTINGS)
            src = f"Settings for {shown} on {line} confirmed by {page}"
            how = f"Proposed by rule ({fm['how']}); settings confirmed by {page}"
            note = x['role']
            date = None
        elif kind == 'own':
            how = f"By rule ({fm['how']}); settings as last issued for this order"
            note = x['role']
        elif kind == 'standin':
            src = f"{frm_src(date, page)}: Tech's {x['from_order']} on {line}" + (f" (printed as {printed})" if shown != printed else "")
            how = (f"Assigned: {x['rules_code']} (the rules' Main, {fm['how']}) has no settings on {line} and {product} has no "
                   f"issue there; the formulation Tech runs for it on {line}, {x['from_order']} (James Kuo, 2 Nov 2026)")
            note = ('Primary' if i == 0 else 'Secondary') + f" · as Tech runs it on {line}"
            marked = marked or date
        elif kind == 'product':
            src = f"as Tech last issued for {product} on {line}: {frm_src(date, page)}, order {x['from_order']}" +                   (f" (printed as {printed})" if shown != printed else "")
            how = (f"Assigned: {x['rules_code']} (the rules' Main, {fm['how']}) has no settings on {line}; the formulation Tech "
                   f"last issued for {product} on {line} (James Kuo, 2 Nov 2026)")
            note = ('Primary' if i == 0 else 'Secondary') + f" · as Tech last issued for this product on {line}"
            marked = marked or date
        else:
            how = f"Proposed by rule ({fm['how']}); " + (f"settings from Tech's {line} calc sheet" if kind == 'calc' else f"settings as issued on {line} {date}")
            # no "PROPOSED BY RULE" on the row: every formulation is by rule (James, 26 Oct 2026: "no need to say that.
            # everything is now rule base remember?"); where the settings came from stays in How Resolved / Source
            note = x['role'] + (" · settings from the calc sheet" if kind == 'calc' else "")
            marked = marked or date
        # the virgin Secondary standing in as a VOIDFORM order's only formula (assign.choose, R10): Tech's "in case ... run
        # out" note does not apply to it, and it is the VOIDFORM formula (James Kuo, 29 Oct 2026, SE22 H6AA171-1)
        void_sec = 'void' in fm.get('want', ()) and (x['member'] or {}).get('level') == 'secondary' and x['role'] == 'Primary'
        tech_note = f.get('note') or ''
        if not tech_note and x['code'][:2] == 'FR':
            tech_note = assign.line_note(line, 'FR')     # Tech's FR processing note (die temps, keep the FR bag sealed)
        if void_sec and RECLAIM_OUT.search(tech_note):
            tech_note = ''
        note += f" · {tech_note}" if tech_note else ""
        note += f" · {fm['run_with']}" if fm.get('run_with') else ""
        if void_sec and 'void' not in assign.quals(note):
            note += f" · {assign.QUAL_NOTE['void']}"
        for q in sorted(set(fm.get('want', ())) & set((x['member'] or {}).get('quals', ()))):   # the Main is for it
            if q in assign.QUAL_NOTE and q not in assign.quals(note):
                note += f" · {assign.QUAL_NOTE[q]}"
        if f.get('season'):                  # R5: F1203K halved / doubled for the season, PP Virgin fills (assign.season_settings)
            how += f"; {f['season']}"
        feeders, was = assign.raise_to_top(line, f["feeders"])
        if was:
            how += (f"; speeds raised so the highest is {assign.AUGER_TOP} (was {was:g}), the others in proportion, weight "
                    f"ratio kept (James Kuo, 28 Oct 2026)")
        for col, v in feeders.items():
            if not (v.get("material") or v.get("set")):
                continue
            ext, feeder = split_feeder(col)
            last = issue_day(date) if kind != 'calc' and date else None
            rows.append([line, order, product, shown, x['role'], ext, feeder, None, v.get("material", ""), v.get("set", ""),
                         None, how, last, src, i + 1, note])
    return rows, marked, missing


def add_day_only(draft):
    """James's formulation for one day replaces the order's own formulation for that day (James Kuo, 4 Nov 2026: "When
    special formation are requested, it temprary replace whatever we have. So no need to do the run first etc."); the
    order goes back to its own formulation the next day."""
    for (day, line, order), fn in DAY_ONLY.items():
        if day != PKT:
            continue
        own = [i for i, r in enumerate(draft) if r[0] == line and r[1] == order]
        if not own:
            continue
        rows = fn(line, order, draft[own[0]][2])
        draft[own[0]:own[-1] + 1] = rows
    return draft


def write(today, draft, exceptions, dropped, last, history_dates, by_rule=(), to_set=()):
    draft = add_day_only(draft)
    F = "Arial"
    hfont, hfill, body = Font(name=F, bold=True, color="FFFFFF", size=10), PatternFill("solid", fgColor="1F3864"), Font(name=F, size=10)
    wb = Workbook()

    def sheet(name, header, rows, widths=None, first=False):
        ws = wb.active if first else wb.create_sheet(name)
        ws.title = name
        ws.append(header)
        for c in ws[1]:
            c.font, c.fill = hfont, hfill
        for row in rows:
            ws.append(row)
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.font = body
                if isinstance(c.value, datetime.date):
                    c.number_format = "yyyy-mm-dd"
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, h in enumerate(header, 1):
            ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, max(10, min(30, len(h) + 3)))
        return ws

    sheet("Draft", ["Line Code", "Order", "Product Code", "Formula Code", "Variant", "Extruder", "Feeder", "Material ID",
                    "Material (as issued)", "Set", "Weight %", "How Resolved", "Last Issued", "Source", "Formula Row", "Note"],
          draft, {"Material (as issued)": 40, "How Resolved": 32, "Note": 50}, first=True)
    sheet("Exceptions", ["Line Code", "Order", "Product Code", "Mat / Grade / Spec", "Colours", "Thk", "GSM",
                         "Special Instructions (start)", "Reason", "Suggestion (not used)", "Engineer Decision", "Decided By"],
          exceptions, {"Reason": 50, "Suggestion (not used)": 60, "Special Instructions (start)": 50, "Engineer Decision": 30})
    n_orders = len({(r[0], r[1]) for r in draft})
    issues = [["High", "FRM Draft", e[0], e[1], "No formula to propose", e[8], "EXT", None] for e in exceptions]
    issues += [["Medium", "FRM Draft", b[0], b[1], "Proposed by rule, not issued for this order before",
                f"{b[3]}: {b[4]}; " + ("settings CALCULATED from the line's augers, check before running" if b[5] == 'calculated'
                                       else f"settings as issued on {b[0]} {b[5]}") + " (docs/FORMULA_ASSIGNMENT_RULES.md)", "rules", None]
               for b in by_rule]
    issues += [["High", "FRM Draft", s[0], s[1], f"{s[4]} has no settings on the line",
                f"{s[3]} ({s[4]} of {s[5]}): no FRM page on file and no calc sheet for it on {s[0]} - engineer to set", "rules", None]
               for s in to_set]
    sheet("By Rule", ["Line Code", "Order", "Product Code", "Formula Code", "How", "Settings issued"], list(by_rule), {"How": 60})
    sheet("Settings To Set", ["Line Code", "Order", "Product Code", "Formula Code", "Role", "Formulation", "James's W%", "Last issued for this order"],
          list(to_set), {"Formulation": 50, "James's W%": 50, "Last issued for this order": 28})
    issues += [["Info", "FRM Draft", ln, o, f"On the {last} FRM, not on today's schedule", "Dropped since the last issued FRM", f"FRM {last}", None]
               for ln, o in dropped]
    sheet("Issues", ["Severity", "Document", "Line", "Order", "Check", "Detail", "Source", "James / Tech response"], issues,
          {"Detail": 60, "Check": 36, "James / Tech response": 30})
    reads = config.reads()
    ws = sheet("Read Me", ["Item", "Value"], [
        ["Workbook", f"FRM Draft {PKT}: proposed formulation for the {PKT} schedule. DRAFT until Tech signs it; nothing here is issued."],
        ["How", "Each scheduled order gets the formulation last issued for that same order on that same line (primary and alternates). "
                "Anything without such a match is on Exceptions for an engineer; suggestions there are never used automatically."],
        ["Schedule", f"{today.get('source_scan', '')} (EXT, packet {PKT})"],
        ["Issued FRMs searched", ", ".join(history_dates) or "none"],
        ["Orders proposed", f"{n_orders} of {n_orders + len(exceptions)}"],
        ["Proposed by rule", f"{len(by_rule)} (sheet By Rule; James Kuo's rules of 23 Oct 2026, docs/FORMULA_ASSIGNMENT_RULES.md: "
                             "the Main he marked in the W% Master for the product's colour, thickness, grade and spec, with the settings "
                             "Tech last issued for that formulation on the line; How Resolved says where each row's settings came from)"],
        ["Exceptions", len(exceptions)],
        ["Settings", "As last issued. Auger lines: Set is motor speed 0-100 (not %). Weight lines (SE24, SE42, SE43, SE61): Set is weight %, Auto = balance."],
        ["Run", RUN_DATE],
    ] + [[f"Source read: {Path(k).name}", f"{v['modified']} · sha256 {v['sha256'][:16]}"] for k, v in reads.items()
         if "packet_" in k], {"Item": 28, "Value": 110})
    out = config.OUTPUT_DIR / f"FRM Draft {PKT}.xlsx"
    wb.save(out)
    print(out, f"- {n_orders} orders proposed, {len(exceptions)} exceptions, {len(dropped)} dropped since {last}")
    for e in exceptions:
        print("  EXCEPTION", e[0], e[1], e[2], "|", e[8], "|", e[9])


if __name__ == "__main__":
    main()
