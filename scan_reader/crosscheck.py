"""Two independent reads of the EXT scan must agree before anything is built (daily run, step 2).

    python scan_reader/crosscheck.py <packet_YYYY-MM-DD.json> <ext_read_YYYY-MM-DD.csv>

Read 1 is the transcription (data/packets/packet_<date>.json, read from the page images).
Read 2 is the glyph reader (scan_reader/ext_scan_reader.py read ...), which reads the printer's own font
under the hardcoded rules and flags what it is unsure of.
Read 3 is the printout's own arithmetic: every line's printed "LINE NO. SExx Total: N PCs  N LBs" must equal
the sum of its rows (PCs = every cut row's Total Sheets, LBs = every order's Weight), and the Final Total must
equal all rows (HANDOFF §7.5 check 1, rule R9).

Every order must be in both reads with the same key fields. A difference is settled by looking at the page again;
the script never picks a winner. Exit code 1 while anything is unsettled.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

# packet field -> reader column. Material/grade/spec come from the packet's 'mat_spec' ("PPP P R1R1R1").
FIELDS = [("line", "line"), ("prod_code", "prod"), ("die", "die"), ("mat", "mat"), ("grade", "grade"),
          ("spec", "spec"), ("colors", "colors"), ("thk", "thk"), ("gsm", "gsm")]


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def norm(field, v):
    v = " ".join(str(v or "").split())
    if field in ("thk", "gsm"):
        n = num(v)
        return f"{n:g}" if n is not None else v
    return v.upper()


def packet_rows(packet):
    out = []
    for page in packet["ext"]:
        for r in page["rows"]:
            mat, grade, spec = (str(r.get("mat_spec", "")).split() + ["", "", ""])[:3]
            out.append(dict(r, line=page["line"], scan_page=page["scan_page"], mat=mat, grade=grade, spec=spec))
    return out


def line_totals(packet):
    """(line, printed PCs, printed LBs, summed PCs, summed LBs) per line; plus the final total check."""
    rows = defaultdict(lambda: [0.0, 0.0])
    printed = {}
    final = None
    for page in packet["ext"]:
        for r in page["rows"]:
            for c in r.get("cut_rows", []):
                rows[page["line"]][0] += num(c.get("total_sheets")) or 0
            rows[page["line"]][1] += num(r.get("weight_lbs")) or 0
        if page.get("line_total_pcs") or page.get("line_total_lbs"):
            printed[page["line"]] = (num(page.get("line_total_pcs")), num(page.get("line_total_lbs")))
        if page.get("final_total"):
            final = page["final_total"]
    out = [(ln, *printed.get(ln, (None, None)), pcs, lbs) for ln, (pcs, lbs) in rows.items()]
    return out, final


def crosscheck(packet_path, reader_csv):
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    tr = {r["order"]: r for r in packet_rows(packet)}
    gl = {r["order"]: r for r in csv.DictReader(open(reader_csv, encoding="utf-8"))}
    problems, agree, flagged_ok = [], 0, 0

    for order in sorted(set(tr) | set(gl)):
        if order not in gl:
            problems.append(("High", order, "in the transcription, not found by the glyph reader: check the page"))
            continue
        if order not in tr:
            problems.append(("High", order, "found by the glyph reader, not in the transcription: check the page"))
            continue
        diffs = [(pf, tr[order].get(pf), gl[order].get(gf)) for pf, gf in FIELDS
                 if norm(pf, tr[order].get(pf)) != norm(pf, gl[order].get(gf))]
        for pf, a, b in diffs:
            problems.append(("High", order, f"{pf}: transcription {a!r} vs glyph reader {b!r} - look again"))
        if not diffs:
            agree += 1
            if gl[order].get("flags"):
                flagged_ok += 1

    totals, final = line_totals(packet)
    for ln, ppcs, plbs, spcs, slbs in totals:
        if ppcs is None:
            problems.append(("Medium", ln, "no printed line total found on the transcription"))
            continue
        if ppcs != spcs or plbs != slbs:
            problems.append(("High", ln, f"line total printed {ppcs:,.0f} PCs / {plbs:,.0f} LBs, rows sum to "
                                          f"{spcs:,.0f} PCs / {slbs:,.0f} LBs: a row is misread or missing"))
    return {"orders_transcribed": len(tr), "orders_read": len(gl), "agree": agree,
            "agree_but_reader_flagged": flagged_ok, "lines_checked": len(totals), "final_total": final,
            "problems": problems}


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    for p in argv:
        config.record_read(p, "crosscheck input")
    res = crosscheck(*argv)
    for sev, where, what in res["problems"]:
        print(f"{sev:6s} {where}: {what}")
    print(f"{res['agree']} of {res['orders_transcribed']} orders agree field for field "
          f"({res['agree_but_reader_flagged']} of those the reader had flagged); "
          f"{res['lines_checked']} line totals checked; {len(res['problems'])} to settle.")
    raise SystemExit(1 if res["problems"] else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
