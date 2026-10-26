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

VARIANT_RULES = [  # note text on the FRM row -> variant (db/schema.py VARIANTS)
    (re.compile(r"run\s*out", re.I), "Reclaim run-out"),
    (re.compile(r"void\s*form", re.I), "VOIDFORM"),
    (re.compile(r"sign\s*blank", re.I), "Sign blank"),
    (re.compile(r"corn\s*box", re.I), "Corn box"),
    (re.compile(r"roll", re.I), "Roll"),
]
RUN_WITH = re.compile(r"RUN\s+WI(?:TH|HT)\s+([A-Z]{3}[0-9A-Z]{2}[A-Z]{2}\d+)", re.I)   # "RUN WIHT" printed 28 Sep


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


def issued_history(packets, before=None):
    """(line, order) -> (issue date, scan page, [formula dicts]); product -> same, keyed (line, product).
    Every issued FRM on file, whatever the schedule's date (James Kuo, 30 Sep 2026: "Always provide up to date
    formulation. even if someone give you an past schedule"); `before` only for callers that need an earlier view."""
    by_order, by_product = {}, {}
    for date in sorted(d for d in packets if before is None or d < before):
        pk = packets[date]
        prod_of = {r["order"]: r["prod_code"] for pg in pk["ext"] for r in pg["rows"]}
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
        src = (f"Tech's calc sheet, last run {date}" if page == 'calc' else f"FRM {date} scan p{page}") + (f" (printed as {printed})" if shown != printed else "")
        for col, v in f["feeders"].items():
            if not (v.get("material") or v.get("set")):
                continue
            ext, feeder = split_feeder(col)
            rows.append([line, order, product, shown, var, ext, feeder, None, v.get("material", ""),
                         v.get("set", ""), None, "Last issued (same order, same line)",
                         datetime.date.fromisoformat(date), src, i + 1, f.get("note", "")])
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
    by_order, by_product = issued_history(packets, cut)                  # latest issue on file, any date
    history_dates = sorted(d for d in packets if packets[d]["frm"] and (cut is None or d < cut))
    approved, _ = approved_master()
    seen_pk = {d: p for d, p in packets.items() if cut is None or d < cut}     # backtests: only what was issued by then
    issued = assign.issued_on_line(seen_pk) if RULES else {}
    if RULES:
        assign.set_pages(seen_pk)            # the lines' feeder columns and wording, for settings taken from the calc sheets

    draft, exceptions, by_rule, to_set = [], [], [], []
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
            fm, why = assign.formulation(line, r, datetime.date.fromisoformat(PKT), issued, own=rec) if RULES else (None, 'rules off')
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
    entries, missing = [], []
    for x in fm['members']:
        if x['rows']:
            entries += run_order([dict(f, _x=x) for f in x['rows']])
        else:
            missing.append(x)
            entries.append(dict(formula_code=x['code'], feeders={}, note='', _x=x))
    rows, marked = [], None
    for i, f in enumerate(entries):
        x = f['_x']
        kind, date, page = x['src'] or (None, None, None)
        printed = f['formula_code']
        shown = x['code'] if x['member'] else assign.current_name(printed)
        if not f['feeders']:                 # a member without settings on this line
            rows.append([line, order, product, shown, x['role'], None, None, None, None, None, None,
                         f"Proposed by rule ({fm['how']}); no settings for {shown} on {line}: engineer to set", None,
                         f"no settings for {shown} on {line} (no FRM page on file, no calc sheet)", i + 1,
                         f"ENGINEER TO SET: settings for {shown} on {line} · {x['role']}"])
            continue
        src = (f"Tech's {line} calc sheet, last run {date}" if kind == 'calc' else f"FRM {date} scan p{page}") + \
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
        elif kind == 'own':
            how = f"By rule ({fm['how']}); settings as last issued for this order"
            note = x['role']
        else:
            how = f"Proposed by rule ({fm['how']}); " + (f"settings from Tech's {line} calc sheet" if kind == 'calc' else f"settings as issued on {line} {date}")
            # no "PROPOSED BY RULE" on the row: every formulation is by rule (James, 26 Oct 2026: "no need to say that.
            # everything is now rule base remember?"); where the settings came from stays in How Resolved / Source
            note = x['role'] + (" · settings from the calc sheet" if kind == 'calc' else "")
            marked = marked or date
        note += f" · {f.get('note')}" if f.get('note') else ""
        for col, v in f["feeders"].items():
            if not (v.get("material") or v.get("set")):
                continue
            ext, feeder = split_feeder(col)
            last = datetime.date.fromisoformat(date) if kind != 'calc' and date else None
            rows.append([line, order, product, shown, x['role'], ext, feeder, None, v.get("material", ""), v.get("set", ""),
                         None, how, last, src, i + 1, note])
    return rows, marked, missing


def write(today, draft, exceptions, dropped, last, history_dates, by_rule=(), to_set=()):
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
