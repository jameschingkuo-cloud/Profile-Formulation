"""
ext_scan_reader.py — read the scanned AS400 report "PP PROFILE PRODUCTION INSTRUCTION - EXTRUSION"
(program BPN9PFR, report WPPPOPRC) into structured order rows for the formulation pipeline.

Production Formulation Automation, Inteplast Group Profile Plant (WPJK).  Owner: James Kuo.
Documented in HANDOFF - Production Formulation Automation.md, §7.6 (rules) and §7.7 (method, test results).

Why not plain OCR: the AS400 cannot export this report as text (it is tied to the printer, James,
23 Sep 2026), and Tesseract misreads its printer font (1->I, 5/8->578, R1->RI, dropped fields).
This reader instead:
  1. deskews the scan and finds the column header,
  2. cuts each record line into fixed-pitch character cells (the report is monospace, and every
     field sits at a fixed character column),
  3. classifies each cell against a bank of labelled glyphs from real scans (nearest neighbour),
  4. decodes each field under the HARDCODED RULES below, which restrict every character position to
     letters or digits and snap codes to known values,
  5. flags anything uncertain for a person — nothing guessed goes out.

Usage
  python3 ext_scan_reader.py train  <scan.pdf> <truth.csv> <bank.npz>   # build/extend the glyph bank
  python3 ext_scan_reader.py read   <scan.pdf> <bank.npz> [out.csv]      # read a new day's scan
"""
import csv, json, re, string, subprocess, sys, tempfile, os
import cv2, numpy as np, pytesseract
# Windows: point pytesseract at tesseract.exe (TESSERACT_CMD in the environment or in local_settings.json)
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import config as _cfg
    _tc = os.environ.get("TESSERACT_CMD") or _cfg._S.get("TESSERACT_CMD")
except Exception:
    _tc = os.environ.get("TESSERACT_CMD")
if _tc:
    pytesseract.pytesseract.tesseract_cmd = _tc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import instructions  # noqa: E402  special instructions snapped to the printed lines (1 Oct 2026)

# =====================================================================================================
#  HARDCODED FIELD RULES — DO NOT REMOVE OR LOOSEN WITHOUT JAMES KUO'S SAY-SO.
#  James, 23 Sep 2026: "make sure these are hardcode so we never forget these instruction".
#  Every rule is also listed in HANDOFF §7.6.  Change both together and log it in the revision history.
#  Position classes: L = letter A-Z, D = digit 0-9.
# =====================================================================================================
LETTERS = list(string.ascii_uppercase)
DIGITS = list(string.digits)

# R1 (James): the extrusion line is ALWAYS two letters followed by two digits.   SE11, SE24, SE61
LINE_CODE_TEMPLATE = "LLDD"
LINE_CODE_RE = re.compile(r"^[A-Z]{2}\d{2}$")

# R1b: the extrusion lines on the Formulation Report (23 Sep 2026).  A code that fits R1 but is not
#   in this list is flagged as a possible new line, never silently accepted.
KNOWN_LINES = ["SE11", "SE12", "SE13", "SE21", "SE22", "SE23", "SE24", "SE25", "SE31", "SE32",
               "SE42", "SE43", "SE61"]

# R2 (James): the material spec is a letter followed by a number, one token per layer, 3 layers.
#   R1R1R1, R4R4R4, R2R2R2, S1S1S1.
#   Exceptions seen only on SE61 (23 Sep 2026): RD and RM (letter + letter), e.g. RDRDRD, RMR6R6.
#   They are accepted only from this list and are always flagged for a person to confirm.
#   CONFIRMED by James Kuo, 24 Sep 2026 (rule and exception handling, as written above).
#   OP added by James Kuo, 28 Sep 2026: H68A153-1 (SE31, 25 Sep) prints OPOPOP, "WHITE OPAQUE".
#   Same handling as RD/RM: accepted from this list, always flagged.
SPEC_SECOND_CHAR = DIGITS
SPEC_EXCEPTIONS = ["D", "M", "P"]

# R3: Mfg# (order) is 7 characters in one of these shapes; Ord# after the hyphen is digits.
#   H68A007 (LDDLDDD), RP26811 (LLDDDDD), RP24C18 (LLDDLDD)
ORDER_TEMPLATES = ["LDDLDDD", "LLDDDDD", "LLDDLDD"]

# R4: Product code = type letter + 2 letters + thickness (2 digits, or letter+0 for >= 10 mm)
#   + 2-letter colour + digits.   DPP30WB1066, RPA20WB28, RPAA0WB318, RPPD0WB176, RBP50EB52
PROD_RE = re.compile(r"^[A-Z]{3}([0-9]{2}|[A-Z]0)[A-Z]{2}\d{1,5}$")

# R5: Die = letter, letter, digit, letter-or-digit, digit.   PB204, PA3B5, PC607, BB510
DIE_CLASSES = [LETTERS, LETTERS, DIGITS, LETTERS + DIGITS, DIGITS]

# R6: material family and grade.
MATERIALS = ["PPP", "BBB"]
GRADES = ["P", "A"]

# R7: colour codes.  A colour is decoded as a whole two-letter word from this list, never letter by
#   letter.  A colour that doesn't look like any of these gets flagged: each colour is also read letter by
#   letter and any difference is flagged (colour_word; added 28 Sep 2026 after BD was read as BL unflagged).
COLORS = ["WB", "KS", "BL", "WM", "GT", "EB", "NS", "OF", "BD"]   # OF = fade-resistant orange, BD = dark blue (James Kuo, 28 Sep 2026)
COLORS += [c for c in ("RF", "EA", "YF", "GS", "JG", "OG", "SS", "NC", "PK", "TS", "LY") if c not in COLORS]   # in use in the Product Master (30 Sep 2026)

# R8: thickness in the product code must equal the Thk column.  "30" = 3.0 mm, "A0" = 10 mm,
#   "D0" = 13 mm (letter = 10 + n; same rule as the Void Form pipeline).
def thk_code(thk):
    v = float(thk)
    return f"{int(v)}{int(round(v * 10)) % 10}" if v < 10 else f"{chr(ord('A') + int(v) - 10)}0"

# R9: each line's printed total is the checksum.  PCs = sum of every Total Sheets value (every cut
#   row); LBs = sum of Weight (LBs).  A line that doesn't add up is re-read, never passed on.

# R10 (observed layout, 23 Sep 2026): WPPPOPRC prints every field at a fixed character column.
#   span A (from Mfg#):     Mfg# 0-6 | '-' 8 | Ord# right-aligned ending 12 | Prod code from 16 | Die 30-34
#   span B (from material): material 0-2 | grade 4 | spec 6-11 | colours 13-14, 16-17, 19-20
#                           | Thk right-aligned ending 26 | GSM right-aligned ending 32
A_MAND = list(range(0, 7)) + list(range(30, 35)); A_BLANK = [7, 13, 14, 15, 28, 29]
B_MAND = [0, 1, 2, 4, 6, 7, 8, 9, 10, 11, 13, 14, 16, 17, 19, 20]; B_BLANK = [3, 5, 12, 15, 18, 21, 22]

# Confidence gates (calibrated on the 23 Sep 2026 scan, leave-one-page-out):
UNFAMILIAR = 0.65   # glyph distance to nearest trained glyph; 99% of correct glyphs < 0.65,
                    # every misread or never-seen glyph > 0.66
MARGIN = 0.04       # best vs second-best candidate; closer than this = low confidence
# =====================================================================================================


# ------------------------------------------------------------------------------------ image prep
def render_pdf(pdf, dpi=300):
    """Pages as 300-dpi PNGs. Uses poppler's pdftoppm when it is on PATH (how the glyph bank was built), otherwise
    PyMuPDF (pip install pymupdf) - no separate install on Windows. Set EXT_RENDERER=pymupdf|pdftoppm to force one."""
    import shutil
    d = tempfile.mkdtemp()
    how = os.environ.get("EXT_RENDERER") or ("pdftoppm" if shutil.which("pdftoppm") else "pymupdf")
    if how == "pdftoppm":
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", pdf, os.path.join(d, "p")], check=True)
    else:
        import pymupdf
        doc = pymupdf.open(pdf)
        for i, page in enumerate(doc, 1):
            page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY).save(os.path.join(d, f"p-{i:03d}.png"))
    return [os.path.join(d, f) for f in sorted(os.listdir(d))]


def upright(path):
    im = cv2.imread(path, 0)
    if im.shape[0] > im.shape[1]:                      # landscape report scanned as portrait
        im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    return im


def deskew(im):
    bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    lines = cv2.HoughLinesP(bw, 1, np.pi / 1800, threshold=300, minLineLength=800, maxLineGap=20)
    angs = [np.degrees(np.arctan2(y2 - y1, x2 - x1)) for x1, y1, x2, y2 in (lines[:, 0] if lines is not None else [])]
    angs = [a for a in angs if abs(a) < 3]
    a = float(np.median(angs)) if angs else 0.0
    h, w = im.shape
    return cv2.warpAffine(im, cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0), (w, h),
                          flags=cv2.INTER_CUBIC, borderValue=255)


def clean(im):
    bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, lab, st, _ = cv2.connectedComponentsWithStats(bw, 8)
    out = im.copy()
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if (h <= 6 and w >= 10) or (w <= 7 and h >= 38) or (w >= 150 and h <= 12):
            out[lab == i] = 255
    return out


def ocr_lines(im):
    d = pytesseract.image_to_data(im, config="--psm 6", output_type=pytesseract.Output.DICT)
    lines = {}
    for i, w in enumerate(d["text"]):
        if w.strip():
            k = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            lines.setdefault(k, []).append((d["left"][i], d["top"][i], d["width"][i], d["height"][i], w))
    return sorted(lines.values(), key=lambda v: min(t[1] for t in v))


# Column anchors (x at 300 dpi, deskewed) measured on page 1; scaled per page from 'Prod' and 'Weight'.
REF = {"Mfg": 274, "Prod": 500, "Die": 725, "Actual": 830, "Mat": 1161, "Thk": 1517, "GSM": 1607,
       "Cut": 1696, "Total": 2040, "pack": 2178, "Weight": 2688, "Instr": 2827}


# Header words that fix a column (lower-case, OCR variants). Tesseract 5.4 (installed 29 Sep 2026) reads 'Prod'
# as 'ROD' on some pages, so any two of these on the header line will do, not just Prod and Weight.
HDR_WORDS = {"prod": "Prod", "rod": "Prod", "die": "Die", "actual": "Actual", "thk": "Thk", "gsm": "GSM",
             "total": "Total", "pack": "pack", "in-str": "Instr", "instr": "Instr"}


def anchors(lines):
    for ln in lines:
        found = {}
        for x, y, _, _, w in ln:
            k = w.lower().strip(".:|")
            key = "Weight" if k.startswith("weigh") else HDR_WORDS.get(k)
            if key and key not in found:
                found[key] = x
        if len(found) >= 3 and ("Prod" in found or "Weight" in found):
            a, b = min(found, key=lambda k: REF[k]), max(found, key=lambda k: REF[k])
            s = (found[b] - found[a]) / (REF[b] - REF[a])
            x0, r0 = found[a], REF[a]
            return (lambda k: int(x0 + (REF[k] - r0) * s)), min(t[1] for t in ln)
    return None, None


def ink_runs(bw, x0, x1, y0, y1, min_ink=40, min_h=14, gap=6):
    prof = bw[y0:y1, x0:x1].sum(axis=1) / 255
    runs, start, last = [], None, None
    for i, v in enumerate(prof > min_ink):
        if v:
            start = i if start is None else start; last = i
        elif start is not None and i - last > gap:
            if last - start >= min_h: runs.append((y0 + start, y0 + last))
            start = None
    if start is not None and last - start >= min_h:
        runs.append((y0 + start, y0 + last))
    return runs


# ------------------------------------------------------------------------------------ glyphs
GW, GH = 20, 28


def _binarize(crop):
    bw = (crop < 140).astype(np.uint8)
    h, w = bw.shape
    for x in np.where(bw.sum(axis=0) >= 0.75 * h)[0]:
        bw[:, max(0, x - 2):x + 3] = 0
    for y in np.where(bw.sum(axis=1) >= 0.5 * w)[0]:
        bw[max(0, y - 1):y + 2, :] = 0
    # underlines (the report underlines the line code): any horizontal run longer than 2.5 characters
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (38, 1)))
    if horiz.any():
        bw[cv2.dilate(horiz, np.ones((3, 1), np.uint8)) > 0] = 0
    return bw


def estimate_pitch(crops):
    diffs = []
    for c in crops:
        n, lab, st, cen = cv2.connectedComponentsWithStats(_binarize(c), 8)
        xs = sorted(cen[i][0] for i in range(1, n) if 9 <= st[i][2] <= 16 and st[i][3] >= 14)
        diffs += [d for d in np.diff(xs) if 10 < d < 24]
    return float(np.median(diffs)) if len(diffs) > 10 else 15.0


def segment(crop, pitch):
    """Fixed-pitch character cells; components go to the cell holding their centre."""
    bw = _binarize(crop)
    h, w = bw.shape
    col = bw.sum(axis=0).astype(float)
    ink = np.where(col > 0)[0]
    if len(ink) == 0:
        return []
    x_first, x_last = ink[0], ink[-1]
    n, lab, st, cen = cv2.connectedComponentsWithStats(bw, 8)
    # grid phase from the centres of single, normal-width characters (circular mean mod pitch)
    cs = [cen[i][0] for i in range(1, n) if 8 <= st[i][2] <= 16 and st[i][3] >= 14]
    if cs:
        ang = np.array(cs) / pitch * 2 * np.pi
        phase = (np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2 * np.pi) * pitch) % pitch
    else:
        phase = (x_first + pitch / 2) % pitch
    start = phase - pitch / 2
    start -= pitch * np.ceil((start - (x_first - pitch)) / pitch)       # first cell left of the ink
    pieces = {}
    for i in range(1, n):
        x, y, cw, ch, area = st[i]
        if area < 6:
            continue
        m = (lab == i)
        if cw <= 1.3 * pitch:
            pieces.setdefault(int((cen[i][0] - start) // pitch), []).append(m)
        else:
            for k in range(int((x - start) // pitch), int((x + cw - 1 - start) // pitch) + 1):
                a, b = int(round(start + k * pitch)), int(round(start + (k + 1) * pitch))
                sub = np.zeros_like(m); sub[:, max(0, a):max(0, b)] = m[:, max(0, a):max(0, b)]
                if sub.sum() >= 8:
                    pieces.setdefault(k, []).append(sub)
    cells = []
    for k in sorted(pieces):
        m = np.any(pieces[k], axis=0)
        ys, xs = np.where(m)
        if len(ys) < 8:
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        if (x1 - x0 + 1) <= 3 and (y1 - y0 + 1) < 18:
            continue                                            # sliver of a neighbour
        if (x1 - x0 + 1) <= 4 and (y1 - y0 + 1) >= 18:
            continue                                            # remains of a '|' bar
        cells.append((k, m[y0:y1 + 1, x0:x1 + 1].astype(np.uint8), (x0, y0, x1 - x0 + 1, y1 - y0 + 1)))
    return cells


def feature(cell, line_h=22.0):
    k, g, (x, y, w, h) = cell
    img = (g * 255).astype(np.uint8)
    s = max(h / GH, w / GW, 1e-6)
    nh, nw = max(1, int(round(h / s))), max(1, int(round(w / s)))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    canvas = np.zeros((GH, GW), np.float32)
    canvas[(GH - nh) // 2:(GH - nh) // 2 + nh, (GW - nw) // 2:(GW - nw) // 2 + nw] = r
    v = canvas.ravel(); v = v - v.mean(); v = v / (np.linalg.norm(v) or 1)
    return np.concatenate([v, np.array([h / line_h, w / line_h, (y + h / 2) / line_h]) * 1.5]).astype(np.float32)


class Bank:
    """Nearest-neighbour glyph classifier."""
    def __init__(self, X=None, y=None):
        self.X = list(X) if X is not None else []
        self.y = list(y) if y is not None else []

    def add(self, f, label):
        self.X.append(f); self.y.append(label)

    def fit(self):
        self.A = np.array(self.X, np.float32); self.labels = np.array(self.y)
        order = np.argsort(self.labels, kind="stable")            # the bank grouped by label: one min per group
        self.As, ls = self.A[order], self.labels[order]
        self.starts = np.r_[0, np.flatnonzero(ls[1:] != ls[:-1]) + 1] if len(ls) else np.zeros(0, int)
        self.ulabels = ls[self.starts]
        self.cache = {}
        return self

    def dists(self, f):
        key = f.tobytes()
        if key not in self.cache:
            d = np.linalg.norm(self.As - f, axis=1)
            self.cache[key] = {lab: float(m) for lab, m in zip(self.ulabels, np.minimum.reduceat(d, self.starts))}
        return self.cache[key]

    def prime(self, feats, tol=1e-4, batch=256):
        """Fill the cache for many glyphs at once (step 1 speed: James Kuo, 1 Oct 2026, "this will reduce the wait time").
        The values are exactly the ones dists() gives: a float64 matrix product finds, per label, the few bank glyphs
        that can be the nearest (within tol, far above the float32 rounding of a distance), and only those distances are
        then computed the way dists() computes them."""
        new = {}
        for f in feats:
            k = f.tobytes()
            if k not in self.cache:
                new.setdefault(k, f)
        if not new or not len(self.As):
            return
        if not hasattr(self, "A64"):
            self.A64 = self.As.astype(np.float64); self.n64 = (self.A64 ** 2).sum(1)
            self.counts = np.diff(np.r_[self.starts, len(self.As)])
        keys, F = list(new), np.array(list(new.values()), np.float32)
        for i0 in range(0, len(F), batch):
            Fb = F[i0:i0 + batch].astype(np.float64)
            d = np.sqrt(np.maximum(self.n64[None, :] - 2 * Fb @ self.A64.T + (Fb ** 2).sum(1)[:, None], 0))
            lim = np.repeat(np.minimum.reduceat(d, self.starts, axis=1), self.counts, axis=1) + tol
            for j in range(len(Fb)):
                f = F[i0 + j]
                cand = np.flatnonzero(d[j] <= lim[j])
                exact = np.linalg.norm(self.As[cand] - f, axis=1)
                best = np.full(len(self.starts), np.inf, np.float32)
                np.minimum.at(best, np.searchsorted(self.starts, cand, "right") - 1, exact)
                self.cache[keys[i0 + j]] = {lab: float(m) for lab, m in zip(self.ulabels, best)}

    def save(self, path):
        np.savez_compressed(path, X=np.array(self.X, np.float32), y=np.array(self.y))

    @classmethod
    def load(cls, path):
        z = np.load(path)
        return cls(z["X"], z["y"]).fit()


# ------------------------------------------------------------------------------------ page -> cells
def is_ext_page(im):
    """Cheap check on the title strip: only 'PRODUCTION INSTRUCTION - EXTRUSION' pages are read."""
    top = im[: im.shape[0] // 9, :]
    txt = pytesseract.image_to_string(cv2.resize(top, None, fx=0.5, fy=0.5), config="--psm 6").upper()
    return "EXTRUSION" in txt or "WPPPOPRC" in txt


def page_rows(path, instructions_crop=True):
    """Find record lines on one EXT page; return line code, page no., per-row cells, totals cells."""
    raw = upright(path)
    if not is_ext_page(raw):
        return {"path": path, "rows": [], "line_cells": None, "page": None, "flags": [], "skipped": True}
    im = clean(deskew(raw))
    bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    lines = ocr_lines(im)
    X, hy = anchors(lines)
    info = {"path": path, "rows": [], "line_cells": None, "page": None, "flags": []}
    if X is None:
        info["flags"].append("column header not found - is this an EXT page?")
        return info
    for ln in lines:
        U = " ".join(w for *_, w in ln).upper()
        m = re.search(r"PAGE\s*:?\s*(\d+)", U)
        if m and info["page"] is None:
            info["page"] = int(m.group(1))
        if re.search(r"LINE\s*NO", U):
            no = [j for j, t in enumerate(ln) if t[4].upper().startswith("NO")]
            if no and no[0] + 1 < len(ln):
                info.setdefault("line_words", []).append(ln[no[0] + 1][4])
            if no and "TOTAL" not in U and "line_crop" not in info:
                x = ln[no[0]]
                info["line_crop"] = im[x[1] - 12:x[1] + x[3] + 12, x[0] + x[2] + 5:x[0] + x[2] + 150]
    total = next((ln for ln in lines if min(t[1] for t in ln) > hy
                  and re.search(r"LINE.*TOTAL", " ".join(w for *_, w in ln).upper())), None)
    end = min(t[1] for t in total) - 10 if total else im.shape[0] - 50
    runs = ink_runs(bw, X("Mfg") - 18, X("Prod") - 18, hy + 70, end)
    A = (X("Mfg") - 18, X("Actual") - 12)
    B = (X("Mat") - 8, X("Cut") - 20)
    crops = [(im[r0 - 10:r1 + 10, A[0]:A[1]], im[r0 - 10:r1 + 10, B[0]:B[1]], r0) for r0, r1 in runs]
    pitch = estimate_pitch([c[0] for c in crops] + [c[1] for c in crops]) if crops else 15.0
    info["pitch"] = pitch
    for ca, cb, y in crops:
        info["rows"].append({"y": y,
                             "A": [(c[0], feature(c), c[2]) for c in segment(ca, pitch)],
                             "B": [(c[0], feature(c), c[2]) for c in segment(cb, pitch)]})
    if info.get("line_crop") is not None and info["line_crop"].size:
        info["line_cells"] = [(c[0], feature(c), c[2]) for c in segment(info["line_crop"], pitch)]
    # special instructions: full-page text of the lines under each record
    for ln in lines:
        top = min(t[1] for t in ln)
        if top < hy + 70 or top > end or any(abs(top - r["y"]) < 25 for r in info["rows"]):
            continue
        txt = " ".join(w for *_, w in ln if w not in "|[]")
        owner = [r for r in info["rows"] if r["y"] < top]
        xs = min(t[0] for t in ln)
        if owner and ("SPECIAL" in txt.upper() or X("Actual") - 40 < xs < X("Cut")):
            owner[-1].setdefault("special", []).append(re.sub(r"^.*Instructions:\s*", "", txt))
    # special instructions, read per record (1 Oct 2026, measured against the system PDF): the record's own area below its
    # first line, from the product column to just before Total Sheets, read on its own. The full-page read above merges
    # these lines with the cut rows beside them and drops lines near a record line ("Sheets must be flat ...", "23 PLTS DONE").
    for k, (r0, r1) in enumerate(runs if instructions_crop else []):   # step 1 (formulation) skips this: speed
        y0, y1 = r1 + 4, (runs[k + 1][0] - 4 if k + 1 < len(runs) else end)
        crop = im[y0:y1, max(0, X("Prod") - 60):X("Total") - 15]
        if crop.size and y1 - y0 > 12:
            info["rows"][k]["special_crop"] = special_from_crop(crop)
    # the top of the page, above its first record: instructions carried on from the last record of the page before
    # (30 Sep RP26717-1: "RUN WITH NEXT 78 PLTS DONE" at the top of report page 4)
    if instructions_crop and runs and runs[0][0] - (hy + 60) > 20:
        top = im[hy + 60:runs[0][0] - 6, max(0, X("Prod") - 60):X("Total") - 15]
        info["carry_special"] = special_from_crop(top, need_label=False)
    return info


LABEL = re.compile(r"^.*?(?:Spec\w*\s+)?Ins\w*\s*:\s*|^.*?Special\s+\S+\s*", re.I)
DASHES = re.compile(r"^[\W_eEcCoOnNrRsStTwWaAiIu]{0,3}$")


TRAIL_NOISE = re.compile(r"(\s+(oe|ee|eo|ae|os|[‘’'\"_~—-]+))+\s*$")


def special_from_crop(crop, need_label=True):
    """The instruction lines of one record, read on their own. Every instruction block starts with the printed label
    'Special Instructions:', so without the label there are none (dashed lines then only read as noise); reading starts at
    the label, which keeps the cut rows printed above it out. Dashed separator lines (read as 'eee ee re ...'), lines that are
    only cut-row numbers and noise marks after the text are dropped. Erasing the dashes as pixels damaged the letters
    touching them (tried 1 Oct). need_label=False: the top of a page, where a record's text carries on from the page before."""
    txt = pytesseract.image_to_string(crop, config="--psm 6").splitlines()
    lab = next((i for i, s in enumerate(txt) if re.search(r"sp\w*al\s+\S*n|instruc|inst\w*ions", s, re.I)), None)
    if lab is None and need_label:
        return []
    if lab is not None:
        txt = txt[lab:]
        txt[0] = LABEL.sub("", txt[0], count=1)
    out = []
    for s in txt:
        s = TRAIL_NOISE.sub("", s.strip(" |_~:;'\"‘’")).strip(" |_~:;'\"‘’")
        if not s:
            continue
        words = re.findall(r"[A-Za-z]+", s)
        if words and len(words) >= 3 and sum(len(w) for w in words) / len(words) <= 3.2 and \
                sum(c in "eEcCoOnNrRsStTwWaA" for w in words for c in w) >= 0.85 * sum(len(w) for w in words):
            continue                                       # a dashed separator line read as letters
        if instructions.NUMERIC_LINE.match(s) or re.fullmatch(r"\W*\w{0,3}\W*\d+(\s+\d+/\d+)?\W*", s):
            continue                                       # cut-row numbers ("96 3/4", "S963 4")
        if sum(ch.isalnum() for ch in s) < 3 or not re.search(r"[A-Za-z0-9]{2}", s):
            continue                                       # specks ("a", "- ; a")
        if not need_label and not instructions.snap_line(s)[1].startswith('library'):
            continue                                       # page top: only lines the system really prints (header noise)
        out.append(s)
    return out


# ------------------------------------------------------------------------------------ decoding
def _origin(cells, mand, blank):
    occ = {c[0] for c in cells}
    return max(range(0, 5), key=lambda o: sum((o + i) in occ for i in mand) - 2 * sum((o + i) in occ for i in blank))


class Decoder:
    def __init__(self, bank):
        self.bank = bank

    def char(self, cell, allowed):
        d = self.bank.dists(cell[1])
        r = sorted(((a, d.get(a, 9.0)) for a in allowed), key=lambda t: t[1])
        return r[0][0], (r[1][1] - r[0][1]) if len(r) > 1 else 1.0

    def classes(self, cells, cls):
        s, m = "", 1.0
        for c, a in zip(cells, cls):
            ch, mg = self.char(c, a); s += ch; m = min(m, mg)
        return s, m

    def word(self, cells, options):
        ds = [self.bank.dists(c[1]) for c in cells]
        sc = sorted(((o, sum(d.get(ch, 9.0) for d, ch in zip(ds, o))) for o in options if len(o) == len(cells)),
                    key=lambda t: t[1])
        if not sc:
            return None, 0.0
        return sc[0][0], (sc[1][1] - sc[0][1]) if len(sc) > 1 else 1.0


def colour_word(dec, cells, flags, where):
    """R7: read a colour as a whole word from COLORS, and also letter by letter. A colour outside the list
    (BD, OF on 28 Sep 2026) otherwise snaps silently to its nearest listed word (BD -> BL): when the two
    readings differ, flag it, never pass the list word on silently."""
    col, m = dec.word(cells, COLORS)
    free, _ = dec.classes(cells, [LETTERS, LETTERS])
    if free != col:
        flags.append(f"R7: {where} colour reads {free} letter by letter but {col} from the colour list - check (new colour?)")
    return col, m


def _fit(s, tpl):
    """Coerce OCR text to an L/D template using the usual confusions; None if impossible."""
    TO_D = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "T": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "A": "4"}
    TO_L = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G", "4": "A"}
    s = re.sub(r"[^A-Z0-9]", "", s.upper())
    if len(s) < len(tpl):
        return None
    out = ""
    for c, t in zip(s, tpl):
        if t == "L": out += c if c.isalpha() else TO_L.get(c, "?")
        else: out += c if c.isdigit() else TO_D.get(c, "?")
    return None if "?" in out else out


def decode_line_code(dec, info):
    """R1 + R1b.  Three independent readings must agree: the header word, the 'LINE NO. xxxx Total'
    word (both by Tesseract, coerced to LLDD) and the glyph classifier on the header."""
    reads = [_fit(w, LINE_CODE_TEMPLATE) for w in info.get("line_words", [])]
    cells = info.get("line_cells")
    if cells and len(cells) >= 4:
        reads.append(dec.classes(cells[:4], [LETTERS, LETTERS, DIGITS, DIGITS])[0])
    reads = [r for r in reads if r and LINE_CODE_RE.match(r)]
    if not reads:
        return None, ["R1: line code unreadable"]
    best = max(set(reads), key=reads.count)
    fl = []
    if reads.count(best) < len(reads):
        fl.append(f"line code readings disagree {reads} - took {best}, check")
    if best not in KNOWN_LINES:
        fl.append(f"line code {best} is not a known line (R1b) - new line?")
    return best, fl


def decode_row(dec, row):
    out, flags = {}, []
    for span in ("A", "B"):
        for c in row[span]:
            if min(dec.bank.dists(c[1]).values()) > UNFAMILIAR:
                flags.append(f"unfamiliar glyph (span {span}, col {c[0]}) - check by eye")
    A = {c[0]: c for c in row["A"]}; B = {c[0]: c for c in row["B"]}
    oa, ob = _origin(row["A"], A_MAND, A_BLANK), _origin(row["B"], B_MAND, B_BLANK)
    get = lambda S, o, rng: [S[o + i] for i in rng if (o + i) in S]
    low = lambda name, m: flags.append(f"{name}: low confidence") if m < MARGIN else None

    tk = get(B, ob, range(21, 27))                                             # Thk
    if len(tk) >= 3:
        out["thk"], m = dec.classes(tk, [DIGITS] * (len(tk) - 2) + [["."], DIGITS]); low("thk", m)
    else:
        out["thk"] = None; flags.append("thk unreadable")
    g = get(B, ob, range(27, 34))                                              # GSM
    if len(g) == 5:
        out["gsm"], m = dec.classes(g, [DIGITS, [","], DIGITS, DIGITS, DIGITS])
    elif len(g) in (2, 3, 4):
        out["gsm"], m = dec.classes(g, [DIGITS] * len(g))
    else:
        out["gsm"], m = None, 0
    low("gsm", m)
    if out["gsm"]:
        out["gsm"] = out["gsm"].replace(",", "")

    mf = get(A, oa, range(0, 7))                                               # R3 order
    mfg = None
    if len(mf) == 7:
        best = None
        for t in ORDER_TEMPLATES:
            cls = [LETTERS if c == "L" else DIGITS for c in t]
            s, m = dec.classes(mf, cls)
            cost = sum(dec.bank.dists(c[1]).get(ch, 9) for c, ch in zip(mf, s))
            if best is None or cost < best[0]:
                best = (cost, s, m)
        mfg = best[1]; low("order", best[2])
    else:
        flags.append("order: Mfg# is not 7 characters")
    od = get(A, oa, range(9, 14))
    ordn, m = dec.classes(od, [DIGITS] * len(od)) if od else (None, 0); low("ord#", m)
    out["order"] = f"{mfg}-{int(ordn)}" if mfg and ordn else None

    pc = []                                                                    # R4 product code
    for i in range(16, 28):
        if (oa + i) in A: pc.append(A[oa + i])
        elif pc: break
    if len(pc) >= 8:
        t3, m1 = dec.classes(pc[:3], [LETTERS] * 3)
        free = [a + b for a in DIGITS for b in DIGITS] + [a + "0" for a in LETTERS]
        read_thk, _ = dec.word(pc[3:5], free)
        if out["thk"]:
            tk2 = thk_code(out["thk"])                                         # R8
            if read_thk != tk2:
                flags.append(f"R8: product thickness read {read_thk}, Thk column says {tk2} - check")
        else:
            tk2 = read_thk
        col, m3 = colour_word(dec, pc[5:7], flags, "product-code")             # R7
        tail, m4 = dec.classes(pc[7:], [DIGITS] * len(pc[7:]))
        out["prod"] = t3 + tk2 + col + tail; low("prod", min(m1, m3, m4))
        if not PROD_RE.match(out["prod"]):
            flags.append(f"R4: {out['prod']} does not fit the product-code pattern")
    else:
        out["prod"] = None; flags.append("prod unreadable")

    dc = get(A, oa, range(30, 35))                                             # R5 die
    if len(dc) == 5:
        out["die"], m = dec.classes(dc, DIE_CLASSES); low("die", m)
    else:
        out["die"] = None; flags.append("die unreadable")

    mc = get(B, ob, range(0, 3))                                               # R6
    out["mat"], m = dec.word(mc, MATERIALS) if len(mc) == 3 else (None, 0); low("mat", m)
    gc = get(B, ob, [4])
    out["grade"], m = dec.word(gc, GRADES) if gc else (None, 0); low("grade", m)
    spec = ""
    for i in (6, 8, 10):                                                       # R2
        pair = get(B, ob, [i, i + 1])
        if len(pair) != 2:
            spec = None; flags.append("spec unreadable"); break
        a, m1 = dec.char(pair[0], LETTERS)
        b, m2 = dec.char(pair[1], SPEC_SECOND_CHAR + SPEC_EXCEPTIONS)
        if b in SPEC_EXCEPTIONS:
            flags.append(f"R2 exception: spec token {a}{b} is letter+letter - confirm")
        spec += a + b; low("spec", min(m1, m2))
    out["spec"] = spec
    cols = []
    for i in (13, 16, 19):                                                     # R7
        pair = get(B, ob, [i, i + 1])
        if len(pair) != 2:
            cols = None; flags.append("colour unreadable"); break
        c, m = colour_word(dec, pair, flags, f"layer {len(cols) + 1}"); cols.append(c); low("colour", m)
    out["colors"] = " ".join(cols) if cols else None
    return out, flags


# ------------------------------------------------------------------------------------ truth labels
def truth_labels(t):
    """Char-column -> label maps for spans A and B from one verified truth row."""
    mfg, ordn = t["order"].split("-")
    a = {i: ch for i, ch in enumerate(mfg)}
    a[8] = "-"
    for i, ch in enumerate(reversed(ordn)): a[12 - i] = ch
    for i, ch in enumerate(t["prod"]): a[16 + i] = ch
    for i, ch in enumerate(t["die"]): a[30 + i] = ch
    s = f"{t['mat']} {t['grade']} {t['spec']} {t['colors']}"
    b = {i: ch for i, ch in enumerate(s) if ch != " "}
    for i, ch in enumerate(reversed(t["thk"])): b[26 - i] = ch
    for i, ch in enumerate(reversed(f"{int(t['gsm']):,}")): b[32 - i] = ch
    return a, b


def add_to_bank(bank, page_info, truth_rows):
    for t, row in zip(truth_rows, page_info["rows"]):
        la, lb = truth_labels(t)
        for span, lab, mand, blank in (("A", la, A_MAND, A_BLANK), ("B", lb, B_MAND, B_BLANK)):
            o = _origin(row[span], mand, blank)
            for c in row[span]:
                if c[0] - o in lab:
                    bank.add(c[1], lab[c[0] - o])
    if page_info.get("line_cells") and truth_rows:
        for c, ch in zip(page_info["line_cells"], truth_rows[0]["line"]):
            bank.add(c[1], ch)


def load_truth(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------------------------ main
def read_scan(pdf, bank, instructions_crop=True, workers=1):
    """workers > 1: the pages are read in parallel processes (the page reads are independent; step 1 uses this so the
    formulation reaches the production team sooner - James Kuo, 1 Oct 2026: "this will reduce the wait time")."""
    dec = Decoder(bank)
    out = []
    paths = render_pdf(pdf)
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        from functools import partial
        with ProcessPoolExecutor(workers) as ex:
            infos = list(ex.map(partial(page_rows, instructions_crop=instructions_crop), paths))
    else:
        infos = [page_rows(p, instructions_crop) for p in paths]
    bank.prime([c[1] for info in infos for row in info["rows"] for s in ("A", "B") for c in row[s]]
               + [c[1] for info in infos for c in (info.get("line_cells") or [])])     # all glyphs at once: same values
    for i, info in enumerate(infos, 1):
        line, lf = decode_line_code(dec, info)
        if info.get("carry_special") and out:              # carried on from the previous page's last record
            prev = out[-1]
            raw = " | ".join(x for x in [prev["special_raw"]] + info["carry_special"] if x)
            prev["special"], sflags = instructions.snap(raw)
            prev["special_raw"] = raw
            prev["flags"] = "; ".join(x for x in [prev["flags"], f"instructions continue at the top of scan page {i}"] + sflags if x)
        for row in info["rows"]:
            vals, flags = decode_row(dec, row)
            raw = " | ".join(row.get("special_crop", row.get("special", [])))
            text, sflags = instructions.snap(raw)      # the printed wording, from the system's own past schedules
            out.append({"scan_page": i, "report_page": info["page"], "line": line, **vals,
                        "special": text, "special_raw": raw, "flags": "; ".join(lf + info["flags"] + flags + sflags)})
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "train":
        pdf, truth, bank_path = sys.argv[2:5]
        T = load_truth(truth)
        bank = Bank.load(bank_path) if os.path.exists(bank_path) else Bank()
        for i, path in enumerate(render_pdf(pdf), 1):
            rows = [t for t in T if int(t["page"]) == i]
            if rows:
                info = page_rows(path)
                if len(info["rows"]) != len(rows):
                    print(f"page {i}: {len(info['rows'])} rows found vs {len(rows)} in truth - skipped"); continue
                add_to_bank(bank, info, rows)
        bank.fit().save(bank_path)
        print(f"bank: {len(bank.y)} glyphs, labels {''.join(sorted(set(bank.y)))}")
    elif cmd == "read":
        pdf, bank_path = sys.argv[2:4]
        rows = read_scan(pdf, Bank.load(bank_path))
        dest = sys.argv[4] if len(sys.argv) > 4 else None
        if dest:
            with open(dest, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        for r in rows:
            print(json.dumps(r))
    else:
        print(__doc__)
