# HANDOFF — Production Formulation Automation

**Status: Rev 1.53 (7 Oct 2026); work continues on James's PC (§7.23).** The code is in git (James's PC + private GitHub repo, §7.17–§7.18). The database
structure and flow are designed (§7.19, `docs/DATABASE.md`); database workbooks live in `Engineering Pipeline\Production
Formulation\<kind>`, this folder is Claude's workspace (§7.21). Four packets processed (23, 24, 25, 28 Sep; §7.20 adds a
three-way accuracy check; §7.22 the first FRM Draft). Earlier: Tech's calc workbooks read (§7.12), auger rules drafted (§7.14), dosing per line
confirmed (§7.16). Not built yet: the Formulation Master, Auger Calibration and the three records, and the FRM renderer. The daily packet has been read end to end
(§2–§5). The proposed pipeline is in §7. §6 lists what the paper shows but I can't confirm yet;
James needs to answer §10 before anything is built. **The input stays a scan of the printed
report (§7.5):** the AS400 can't produce the report as text (James, 23 Sep 2026).

Built for Inteplast Group Profile Plant, WPJK (James Kuo, Technical Process Engineer).
**Established 23 September 2026** in `Claude MD, PY Pipeline File\Engineering Pipeline\Production Formulation Automation\`.

**Source read for this revision:** James's scan `doc05228320260923140823.pdf` (39 pages, 23 Sep 2026):
the production packet issued for that day. It contains three documents:

| # | Document | Scan pages | Made by | Format |
|---|---|---|---|---|
| **EXT** | *PP Profile Production Instruction — Extrusion* (program `BPN9PFR`, report `WPPPOPRC`) | 1–16 | System report, Run Date 9/23/26 13:15:36 | Fixed-width system print, one section per line |
| **CNV** | *PP Profile Production Instructions — <converting line>* | 17–26 | Planning, Excel, "Issue Date 9/23/2026" | Spreadsheet print, one sheet per converting line |
| **FRM** | *Line N (SExx) Formulations* | 27–39 | **Tech. Department**, dated 9/23/26 | Word/Excel table, one page per extrusion line |

---

## Standing instructions

- **HARD RULE — VERIFY THE SOURCES BEFORE MAKING ANYTHING (James, 25 Sep 2026: *"there need to be hard rule
  set that you must check the data before making anything. As change may have occur by engineer."*).**
  Every run, before building or updating any file:
  1. Re-read every source from where it lives now (calc workbooks, formula books, calibration records, the day's
     packet, the current masters). Never build from a cached or earlier copy.
  2. Compare them with the masters and the Change Log.
  3. Any difference with no Change Log entry = **unlogged change**: stop, list it for James/Tech, overwrite nothing.
  4. Only after James/Tech confirms: log it (date, who, why, old → new), then build.
  5. Every output's Read Me lists the source files with their modified time and the pre-flight result.
  Never skip this because "nothing changed yesterday". Engineers edit the calcs and books directly.
- **Write findings here while you work on them, not at the end.** This document is the running state.
- **Verify state. Do not trust these notes.** A scan is a snapshot of one day. The formulation
  master (§6) has to come from Tech's own files, not be rebuilt from scans.
- **The formulation decides what goes into the extruder. Never auto-issue a formula the pipeline
  guessed.** Anything not matched exactly goes to an engineer (§7.4). Output is a draft until Tech signs it.
- **Read columns by name, never by position** (house rule, `Claude MD, PY Pipeline File\README.md`).
- **Re-stage the live file immediately before every build, and verify every device write by content.** Stage it back
  and compare cell values (`.xlsx`) or bytes (`.md`, `.py`). SharePoint adds metadata parts to `.xlsx`, so the file
  hash changes on upload. Update the checksum manifest (§11) in the same pass.
- **Dosing type decides every formulation check (James, 26 Sep 2026; §7.16).** Lines 7, 12, 13, 16 weigh
  (Set = weight %, adds to 100 per extruder, `Auto` = balance). All other lines are auger lines: Set is motor speed
  0–100 with no RPM feedback, it never adds to 100, and weight % exists only through the calibration slope.
  Hardcoded in `load.py` and `auger_rules.py` (`DOSING`); change both together, only with James's say-so.
- **Hoppers: read the function, not the number.** Hopper numbering differs by line (§7.14). The slope follows the
  material and the hopper together; never carry a slope to another material or another hopper.
- **The code lives in the `formulation-pipeline` git repo on James's PC (§7.17).** That repo is the master for code.
  The copies under `claude/formulation/` in the claude.ai Project are a snapshot from 28 Sep 2026. Change code in
  the repo, not in Cowork.
- **Publishing:**
  - From Claude Code, outputs reach this folder only through `publish.py`. It refuses to replace a file whose content
    is neither what the build read nor what the pipeline last published.
  - From Cowork, use `SendUserFile` → `device_commit_files`. Never base64-upload a workbook (Void Form §11/§16,
    MR §8).
  - A file Cowork publishes is unknown to the repo's manifest, so `publish.py` will refuse to overwrite it until
    someone checks it. That is on purpose.
- **This document stays in this SharePoint folder (Claude's workspace, `DOCS_DIR`) and is edited in place** by Claude Code and Cowork alike. After a
  Cowork session changes it, mirror it to the Claude Project `Engineering Pipeline`
  (`claude/HANDOFF - Production Formulation Automation.md`).

---

## 1. What the three documents are and how they connect

```
             Order entry / scheduling system
                          |
                          v
  EXT  Extrusion Production Instruction  (system, per line SE11…SE61)
       order · product code · material spec · thickness · GSM · qty · special instructions
          |                                   |
          | order # per line                  | semi-finished pallets → converting
          v                                   v
  FRM  Line N Formulations (Tech)       CNV  Converting Production Instructions (Planning)
       order # → formula code →              order # · product · "Extrusion Status  X OF Y"
       material + setting per hopper/feeder   · die · plate · ink · pack · req. date
```

- **The order number is the join key across all three.** EXT prints `Mfg# / Ord#` as `H69A237 - 3`.
  FRM and CNV write it as `H69A237-3`. Normalise to `<Mfg#>-<Ord#>`.
- **Line names.** FRM uses both a line number and a line code. The mapping, from the FRM page titles:

| FRM line | Code | Feeder layout on the FRM page |
|---|---|---|
| Line 1 | SE11 | Hopper 1–5 (Material · Set), header `AC = 1` |
| Line 2 | SE12 | Hopper 1–5, `AC = 90` |
| Line 3 | SE13 | Hopper 1–5, `AC = 90` |
| Line 4 | SE21 | Hopper 1–5, no AC value |
| Line 5 | SE22 | Hopper 1–5, no AC value |
| Line 6 | SE23 | Hopper 1–5, `AC = 1` |
| Line 7 | SE24 | Extruder A V1–V5, B V1–V4, C V1–V4 |
| Line 8 | SE31 | Extruder A V1–V5, B V1–V4, C V1–V4 |
| Line 9 | SE32 | Extruder A V1–V5, B V1–V4, C V1–V4 |
| Line 10 | SE25 | Hopper 1–5, `AC = 1` |
| Line 12 | SE42 | V1–V9 |
| Line 13 | SE43 | V1–V9 |
| Line 16 | SE61 | Extruder A 1–6, B 1, C 1–6, D 1 (co-ex; some feeders set to `Auto`) |

Lines 11, 14 and 15 are not in this packet (not scheduled that day, or they don't exist; §10 Q6).

---

## 2. EXT: Extrusion Production Instruction

One section per extrusion line, `LINE NO: SExx Company: WP`, then a line total (PCs, LBs). The
report ends `Final Total: ** END OF REPORT **`.

**Columns:** `T` · `Mfg# / Ord#` · `Prod Code` · `Die` · `Actual Order Size (Width, Length)` ·
`Mat A Sp. Req.` · `Color` · `Thk` · `GSM` · `Cut Dimensions (Width, Length)` · `Total Sheets` ·
`pack Code` · `# Plt` · `PCs./Stack` · `Stk./Plt.` · `Weight (LBs)` · `In-str Date` · `Web Width`,
then a free-text `Special Instructions:` block.

**The `Mat A Sp. Req. / Color` field carries what the formula depends on.** Example:
`PPP P R1R1R1 WB WB WB 3.0 602`

| Part | Example | Meaning (from the data; confirm, §10 Q2) |
|---|---|---|
| Material | `PPP` / `BBB` | Resin family per layer (BBB only on SE61) |
| Grade | `P` / `A` | Two grades; **`A` orders get `FUA…` formulas** (§6.2) |
| Spec per layer | `R1R1R1` · `R4R4R4` · `R2R2R2` · `S1S1S1` · `RDRDRD` · `RMR6R6` | **`R4` orders get reclaim-only `RU…` formulas** |
| Color per layer | `WB WB WB` · `KS KS KS` · `BL` · `WM` · `WB GT WB` · `EB KS EB` | Color code; becomes the formula's color suffix |
| Thk | `2.0`–`13.0` | mm |
| GSM | `504`–`3,014` | Target basis weight |

**Special instructions matter to the formulation:** `VOIDFORM, PLEASE WATCH WEIGHT (RANGE IS 582-600
GSM)`, `CORN BOX`, `RUN WITH RPA40WB3051` / `RUN WITH NEXT` / `RUN WITH ABOVE`, `ULTRA SMOOTH`,
`GENESIS, TARGET THICKNESS 10 (RANGE IS 9.50-10.50)`, `Bradford, treat both sides minimum 42 dynes`,
`Rolls. Rolled material…`, `DO NOT RUN`. They also carry the pallet progress note `NNN PLTS DONE`.

**Scan observations:**
- Report page numbers run 1–17. **Page 11 is missing from the scan** (between SE31 p.12–13 and SE25
  p.10). It is probably a second SE25 page.
- The scan is out of order: SE25 (report p.10) comes after SE32 (p.14).
- Handwriting on the print: `591,328#` on SE25, `1044` beside H64A244, and die `PC405` written over
  RP26410 on SE42. **The printout gets marked up by hand after it runs.**

---

## 3. CNV: Converting Production Instructions

One sheet per converting line, 10 scan pages:

| Scan p. | Converting line |
|---|---|
| 17–18 | SD31 Bobst die cutter (2 pp.) |
| 19 | SD11/SD12 Rotary / printing |
| 20–21 | SD22 Baysek (Bobst die cutter form) (2 pp.) |
| 22–23 | SD41/SD42 Guillotine (2 pp.) |
| 24–25 | SD51 Slitter (2 pp.) |
| 26 | SC31 Folder gluer |

**Columns:** `Order #` · `Product Code` · `Extrusion Status` · `Semi pc/plt` · `Semi-Size` · `Color` ·
`Apl.` · `MM` · `Flute` · `Die #` · `Die Description` · `Die Status` · `Plate Status` · `Ink Color` ·
`Total Sheets` · `Pack Code` · `# of Plts` · `Pc./Plt.` · `Req. Date`. The slitter adds `Semi Start`.
Standing notes are typed between rows: weight targets such as `Target wt is 0.2891. Acceptable range
is 0.2746 - 0.3035`, pallet rules, VoidForm pallet-ticket rules.

**`Extrusion Status` = `X OF Y` extruded pallets, and someone types it by hand.** It drifts from EXT:

| Order | EXT (same day) | CNV (same day) |
|---|---|---|
| H63A200-1 | `343 PLTS DONE` | `368 OF 374` |
| H64A244-1 | `822 PLTS DONE` (1044 handwritten) | `823 OF 1044` |

CNV is **not an input to the formulation**. It matters here because it is the second consumer of the
same order list, and its `Extrusion Status` is a second automation candidate (§8, Phase 4).

---

## 4. FRM: Line Formulations (what we automate)

One page per extrusion line, title `Line N (SExx) Formulations`, date top right, footer
`Tech. Department` + `Effective Date: 06/06/00` (L1, L2, L3), `5/30/00` (L4, L5, L6, L10) or `6/15/00`
(L7, L8, L9, L12, L13, L16). Those are form revision dates.

**One row group per formula.** `Order #` (one or several orders sharing a formula) · `Formula Code` ·
per feeder `Material` + `Set` · `Note`. Standing footers: *"CaCO3 means calcium carbonate"* and, on
L1 and L4, *"For KS orders, increase Hopper N setting if the board looks too gray, because the PP Mix
Reclaim from the boxes/silo 8 might be too much WB (or others) colored."*

**An order can carry more than one formula**, a primary and one or more alternates:

| Note on the row | Meaning | Example |
|---|---|---|
| *Use this formula in case PP WB Reclaim is run out* | Backup formula with no reclaim | H68A007-1: FU0042WB3 main, FU0022WB3 backup |
| *For VOIDFORM order only* | VoidForm-specific formula | H66A116-1: FU0011WB5 |
| *For sign blank orders only* / *New formulation for sign blank* / *SIGN BLANK* | Application variant | L3 FUA152WB4 at 60/33/45/16 vs 48/25/48/15 |
| *CORN BOX FORMULA* | Application variant | RP26731-2 on L6 |
| *For roll material only. Check weight* | Rolled-material variant | H68A111-4/-5 on L10 |
| *Match color and opacity with QC sample* | Colour check | H69A206-1 (BL), H69A066 (WM) |
| *WB : EA = 9 : 1, WB – W26038A, GT – D26002M* | Premix recipe | H68A127-1 (`WB GT WB`) |

**Materials seen** (a substitute in brackets):

| Material on FRM | Role |
|---|---|
| PP Virgin-silo 3 (6502A / F6502A), PP Virgin-silo 4 (6502A / F6502A), PP Virgin (F6502A) | Base resin, virgin |
| PP WB Reclaim, PP Mix Reclaim, White Reclaim | In-house reclaim |
| F1203K, F1102K, Q1203K | Resin grades |
| HiTalc ZS (or N40109A) | Talc filler |
| CaCO3 – Heritage HM-10MAX / HM-10HP | Calcium carbonate filler |
| WB-W26038A · WM-W26329M · BL-B26003A (or NPC-B60387) · OG-D26074A · WB GT Premix | Colour masterbatch |
| KS-MDI PE-500 (or Spartech B60009 / NPC PE90000F / PolyOne LD-250) | KS colour / PE carrier |
| Exxon Vistamaxx 6102FL | Elastomer modifier |
| FOAM – Bergen XO-256 | Foaming agent |
| PP Yungsox 5050S | Skin layer resin (L16 Extruders B, D) |

**What `Set` means depends on the line's dosing (James, 26 Sep 2026; §7.16).** On the weight lines (7, 12, 13, 16)
it is the weight % per extruder. On every other line it is the auger motor speed, 0–100, with no RPM feedback:
g/min = calibration slope × setting and % = g/min ÷ total (Tech's calc workbooks, §7.12). That is why Lines 1–6,
8, 9 and 10 never add to 100.
(Original note:) **`Set` is a feeder setting, not always a percentage.** L7, L12 and L13 add to 100 per extruder
(2.7 + 9 + 73.3 + 15; 5 + 78 + 15 + 2). L1–L6 and L10 do not (L1 FU0042WB3 = 41 + 10 + 31 + 30 + 23
= 135). **The same formula code has different settings on different lines**: FUA152WB4 is
50/27/14/71 on L2 but 99/18/54/43 on L6. So a setting belongs to *(line, formula code, variant)*, not
to the formula code alone (§10 Q3).

---

## 5. Cross-check: EXT orders vs FRM orders, 23 Sep 2026

Every order on EXT has a formula row on FRM for the same line. **13 lines, 82 order lines, 0 missing.**
That is the check the pipeline has to run every day.

| Line | EXT orders | On FRM |
|---|---|---|
| SE11 | H68A007-1, H69A039-1, H68A088-1, H63A200-1, RP26811-1, H69A180-1/-2, H69A206-1 | 8/8 |
| SE12 | H69A099-1, RP26821-1, RP26511-1 | 3/3 |
| SE13 | H69A237-1, RP26618-3/-2, RP26506-5, RP25522-4, H69A158-1, H69A105-3, RP26717-1, RP26327-1, RP24C18-4 | 10/10 |
| SE21 | H69A090-2, H69A238-1…-5, H69A206-2, H69A139-1, RP26810-1, RP26424-2, RP26527-1, RP25818-2, RP26512-1 | 13/13 |
| SE22 | RP26311-1, H68A053-1 | 2/2 |
| SE23 | H69A166-1, H68A091-1, RP26821-2, RP26731-2, RP26902-1, RP26202-1 | 6/6 |
| SE24 | H69A237-3/-2, RP26901-1, RP26803-2, RP26514-1, RP25710-1 (*DO NOT RUN*) | 6/6 |
| SE31 | H69A105-4, H69A197-1, H69A100-13, H69A066-1/-2/-3/-5, H69A062-4, H69A225-1, RP26413-1, RP26120-1 | 11/11 |
| SE32 | RP26731-1, RP26525-3 | 2/2 |
| SE25 | H68A111-4/-5, H69A097-1, H68A127-1, H66A116-1, RP26717-2, H64A244-1 (+ missing p.11) | 7/7 seen |
| SE42 | H68A080-1, RP26410-1 | 2/2 |
| SE43 | RP26915-1, RP26415-1, RP26218-1, RP26526-2 | 4/4 |
| SE61 | RP26910-1, H68A020-1, H64A178-1, H64A289-1…-4, RP26826-1 | 8/8 |

Read by eye from the scan. Re-verify with the §7.5 reader and its checksums once it is built.

---

## 6. The formulation rule: what the data suggests

### 6.1 Formula code structure (my reading; not confirmed)

`F U A 152 WB 4`

| Pos | Values seen | Seems to mean | Evidence |
|---|---|---|---|
| 1–2 | `FU` · `FS` · `RU` · `BF` | Formula family: standard / ultra-smooth (`S1S1S1`) / reclaim-only (`R4R4R4`) / BBB co-ex (SE61) | RP26514 `S1S1S1` → FSA200WB4 · RP25710 `R4` → RU0000WB4 · RP26717-2 `R4` → RU0001WB4 · SE61 → BF0000EBA |
| 3 | `A` or `0` | Grade A, or not | `PPP A` → FUA…; `PPP P` → FU0… (exception: *RUN WITH*, §6.3) |
| 4–6 | `000`–`200` | Formula number | |
| 7–8 | `WB` `KS` `BL` `WM` `EB` `GT…` | Colour | matches EXT colour; H68A127 `WB GT WB` → FU001**GTW**4 breaks the pattern |
| last | `2` `3` `4` `5` `A` `D` | Thickness: digit = mm, letter = 10 + n (`A` = 10 mm, `D` = 13 mm) | RP26311 10.0 → FUA060WB**A** · H68A053 13.0 → FU0001WB**D**. Same letter rule as the product code (Void Form handoff, `parse_target_thickness_mm`) |

### 6.2 What decides the formula for an order

From the 82 order lines, the formula follows from **line + grade + spec + colour + thickness +
application** (VoidForm, sign blank, corn box, rolls). **The formula number itself (e.g. 152 vs
151 vs 041) can't be derived from the order.** It is Tech's choice and has to come from a master
table: product code → formula, or a Tech rule (§10 Q3).

### 6.3 Exceptions the pipeline must handle

- **RUN WITH.** H69A237-3 and -2 are `PPP P` but get FUA152WB4, the formula of the `PPP A` order
  they run with (`RUN WITH RPA40WB3051`). An order that runs with another inherits that order's formula.
- **One formula, several orders.** Orders that share a formula are grouped into one row block.
- **Alternates.** A backup formula for when reclaim runs out, plus VoidForm, sign-blank and corn-box variants (§4).
- **DO NOT RUN** orders still get a formula row (RP25710-1).
- **Substitute materials** (`HiTalc ZS (or N40109A)`) are part of the material text, not a separate row.

---

## 7. Proposed pipeline (design; not built)

### 7.1 Inputs

| Input | Best source | Fallback |
|---|---|---|
| EXT order list | **Scan of the printed `WPPPOPRC`** (§7.5). No text export: the AS400 report is tied to the printer (James, 23 Sep 2026) | A text/spool export, if IT ever fixes the AS400 (future) |
| Formulation master | Tech's existing formula files per line (§10 Q3/Q4) | Built up from past FRM pages, reviewed by Tech |
| Yesterday's FRM | Last issued output | — |

### 7.2 Master tables (`Formulation Master.xlsx`)

| Sheet | Key | Columns |
|---|---|---|
| `Lines` | Line code | Line no · feeder layout (hopper 1–5 / A–C V1–V5 / V1–V9 / A–D co-ex) · AC value · form effective date |
| `Formulas` | Line + Formula Code + Variant | per-feeder Material and Set · Note · Status (active / retired) · Last approved by/date |
| `Product → Formula` | Product code (or grade + spec + colour + thickness) + Line | Primary formula · alternates + when to use |
| `Materials` | Material text | Resin/additive · approved substitutes |
| `Standing Notes` | Line | Footer notes (CaCO3, KS gray) |

### 7.3 Daily run

1. **Parse EXT** into rows: line, order, product code, grade, spec, colour, thickness, GSM,
   special instructions, `RUN WITH` target, `PLTS DONE`.
2. **Resolve the formula** for each order: `RUN WITH` inherits from its partner; otherwise
   look up product → formula for that line; then add the alternates.
3. **Group** orders that share a formula and variant into one row block, in EXT order.
4. **Render FRM** in the current layout, one sheet/page per line with the line's feeder layout,
   date, notes, footers. Output `Formulations YYYY-MM-DD.xlsx` + PDF.
5. **Exceptions sheet** (§7.4), for Tech to resolve before the formulation goes out.
6. **Diff against yesterday**: new orders, dropped orders, changed formulas or settings.

### 7.4 Exceptions (nothing guessed goes out)

- Product not in the master, or no formula for that line → **engineer must assign**.
- A formula number that doesn't match what the code implies (grade/colour/thickness mismatch).
- `RUN WITH` partner not found on the same line.
- New special instruction text the rules don't recognise.
- A feeder layout that doesn't match the line (e.g. a V-layout formula on a hopper line).
- A feeder-% line (L7/L12/L13) where an extruder doesn't total 100.
- An EXT line whose read totals don't match its printed `LINE NO. SExx Total` (§7.5).

### 7.5 Reading the EXT scan (no text export)

**James, 23 Sep 2026:** *"our AS400 has a lot of problem and cant really make report as text. Its tie
into the printer."* So the input is the scanned printout, now and for the foreseeable future.

**Plain OCR is not good enough on its own. Tested on scan page 1 (SE11) with Tesseract 5.3.4 at 300 dpi:**

| Printed | Tesseract read |
|---|---|
| `H68A007 - 1` | `H68A007 - I` |
| `31 5/8` | `31 578` |
| `R1R1R1` | `RIRIRI` |
| `RPP30KS1143` | `RPPSOKSII43` |
| `R4R4R4` | `RARARS` |
| `H63A200` / `27,465` / `03-Oct` | lost entirely |

**James, 23 Sep 2026:** *"we may be able to improve with some logic… Extrusion line is always two
english alphabet follow by two number. The Spec requirement for R is alphabet follow by number."*
And: *"make sure these are hardcode so we never forget these instruction."* So OCR stays, and
logic makes it reliable. What was built is in §7.6 (the hardcoded rules) and §7.7 (the reader and
its test results). The checks below still apply on top:

1. **Checksums from the printout itself.** Each line ends `LINE NO. SExx Total: N PCs  N LBs`.
   - **PCs = the sum of every printed `Total Sheets` value, counting each cut-dimension row.** SE11:
     12,810×2 + 34,675×2 + 18,460×2 + 1,080×2 + 4,000 + 1,750 + 700 + 1,750×4 = **147,500** ✓
   - **LBs = the sum of `Weight (LBs)`.** SE11: 27,465 + 67,270 + 22,558 + 3,041 + 13,160 + 6,913 +
     3,171 + 2,520 = **146,098** ✓

   A line whose rows don't add up to its printed totals has been misread or has a missing row.
   Re-read it; never pass it on.
2. **Field patterns.** Order `[HR][A-Z0-9]{6} - \d+` (e.g. `H68A007`, `RP24C18`); product code
   `[DRSCB][A-Z]{2}[0-9A-Z]{2}[A-Z]{2}\d+`; the material field `(PPP|BBB) [PA] (R\d|S\d|RD|RM|R6|OP){3} …`;
   Thk in the product code (chars 4–5) must equal the `Thk` column.
3. **Report page numbers** 1…N with none missing (the 23 Sep scan was missing p.11).
4. **Line list** matches the lines on yesterday's FRM, give or take lines starting or stopping.
5. **Handwriting on the print** (die changes, pallet counts) is reported as a note, never read as data.

**What the formulation actually needs from EXT is small:** line, order #, product code, material
field, Thk, GSM, special instructions. Sizes, pallets and weights are read only for the checksum.

**Scanning practice that helps:** scan the report in page order, one side, at 300 dpi or more, and
before anyone writes on it.

### 7.6 HARDCODED READING RULES (James, 23 Sep 2026 — never drop these)

These are written into the top of `ext_scan_reader.py` as constants, in a block marked *DO NOT REMOVE
OR LOOSEN WITHOUT JAMES KUO'S SAY-SO*. **This table and that block must always match.** Change both
together, and log the change in the revision history.

| # | Rule | Source | How the reader uses it |
|---|---|---|---|
| **R1** | **Extrusion line code is always 2 letters + 2 digits** (`SE11`, `SE61`) | **James** | Positions 1–2 can only be letters and 3–4 only digits. Three readings must agree: the header word, the `LINE NO. xxxx Total` word, and the glyph read |
| R1b | Known lines: SE11 SE12 SE13 SE21 SE22 SE23 SE24 SE25 SE31 SE32 SE42 SE43 SE61 | FRM 23 Sep | A code that fits R1 but isn't listed is flagged as a possible new line |
| **R2** | **Material spec is a letter + a number**, three layers (`R1R1R1`, `R4R4R4`, `S1S1S1`) | **James** (rule and exception handling **confirmed 24 Sep 2026**) | Odd positions can only be letters, even positions only digits. **Exceptions:** `RD`, `RM` (seen on SE61 only: `RDRDRD`, `RMR6R6`) and `OP` (**added by James 28 Sep 2026**: H68A153-1 on SE31, `OPOPOP`, "WHITE OPAQUE") are accepted from that list and **always flagged** for confirmation |
| R3 | Mfg# is 7 characters, shaped `LDDLDDD` (H68A007), `LLDDDDD` (RP26811) or `LLDDLDD` (RP24C18); Ord# is digits | Data | Each position read as letter or digit only |
| R4 | Product code = 3 letters + thickness (2 digits, or letter + 0) + 2-letter colour + digits | Data | Same |
| R5 | Die = letter, letter, digit, letter-or-digit, digit (`PB204`, `PA3B5`) | Data | Same |
| R6 | Material ∈ {PPP, BBB}; grade ∈ {P, A} | Data | Read as a whole word from the list |
| R7 | Colour ∈ {WB, KS, BL, WM, GT, EB, NS, OF, BD} (OF = fade-resistant orange, BD = dark blue; James 28 Sep 2026) | Data | Read as a whole two-letter word from the list **and** letter by letter; any difference is flagged (a colour outside the list, e.g. BD, never snaps silently; §7.22). Meanings in `data/colour_codes.csv` |
| R8 | Thickness in the product code = the Thk column (`30` = 3.0, `A0` = 10, `D0` = 13) | Data + Void Form rule | Mismatch is flagged |
| R9 | Line totals: PCs = Σ Total Sheets, LBs = Σ Weight | Printout | Checksum (§7.5 check 1). Not yet in the glyph reader, see §7.7 |
| R10 | Fixed character columns of WPPPOPRC (span A: Mfg# 0–6, `-` 8, Ord# ends 12, Prod from 16, Die 30–34; span B: material 0–2, grade 4, spec 6–11, colours 13/16/19, Thk ends 26, GSM ends 32) | Measured on 82 rows | Each field is read from its own columns, so stray marks can't shift it |

Rules marked **James** are his standing instructions. Rules marked *Data* were taken from the
23 Sep scan; confirm or correct them with James (§10 Q2).

### 7.7 The reader: `ext_scan_reader.py` (built 23 Sep 2026)

**How it reads a page:** Tesseract is used only to find the title, the header row and the line/page
words. Every data character is read by a glyph classifier built for this printer font:

1. Deskew the scan using the table's ruling lines (the scans lean 0.5–0.8°).
2. Find each record line from the ink in the Mfg# column. On the 23 Sep scan this found all
   82 rows on all 16 pages, and never merged or dropped one.
3. Cut the line into **fixed-pitch character cells** (~15 px at 300 dpi; the report is monospace).
   The grid is lined up on the centres of the characters, and each stroke goes to the cell holding
   its centre, so the leg of an `R` isn't cut off into a `P` and touching letters (`BB`) still split.
4. Classify each cell against a **bank of labelled glyphs from real scans** (`glyph_bank.npz`,
   3,894 glyphs from the 82 verified rows, nearest neighbour).
5. Decode each field **under the §7.6 rules**: each position may only be what its rule allows, and
   colours, materials and line codes are read as whole words from their lists.
6. **Flag, never guess:** a glyph unlike anything trained (distance > 0.65), a near-tie between two
   readings, an R2 exception, an R8 mismatch, or line-code readings that disagree.

**Tested honestly: leave-one-page-out.** Each page was read with a bank built only from the *other*
15 pages, so every page was a page it had never seen:

| Result, 82 rows × 10 fields | Rows |
|---|---|
| Every field correct | **69** |
| Something wrong, **but flagged** for review | 13 |
| **Something wrong and not flagged (silent)** | **0** |

For comparison, plain Tesseract plus text rules got about half the order numbers right and several
fields silently wrong (e.g. `RPP40WB1853` → `RPP40WB1653`, die `PA3B5` → `PA6B5`).

**What the 13 flagged rows were:**

- 8 are on SE61, whose `D` and `M` (in `RDRDRD` / `RMR6R6`) appear on no other page.
- 2 are colour codes that each appear on only one page (`BL`, `GT`).
- 1 is RP26410, with the handwritten `PC405` over it.
- 2 had a character too faint to read with confidence (a Thk; an `8` in RP26811).

With the only page holding a character left out of training, that character had never been seen,
so it was flagged as unfamiliar. In daily use the bank holds all 16
pages, so these characters are known. A brand-new character still gets flagged the same way.

**Daily-use run (bank from all 16 pages, whole 39-page scan):** the reader skipped the 23 CNV/FRM
pages by itself and returned 82 rows. **80 were fully correct.** The other 2 were flagged: the faint
Thk on H69A062-4 and the handwriting over RP26410-1. 0 were silent. 10 rows carry a flag; 8 of those
are the SE61 R2 exceptions (`RD`/`RM`), which are flagged every time by design. This isn't a
blind test, since the bank has seen these pages; the leave-one-page-out table above is the honest
figure.

**False alarms:** 21 of the 69 correct rows also carry a flag (mostly "unfamiliar glyph"). That is
deliberately cautious. The bank grows with every day Tech confirms, and false alarms should fall.

**Growing the bank:** after Tech checks a day's read (or corrects its flags), add it:
`python3 ext_scan_reader.py train <scan.pdf> <verified.csv> glyph_bank.npz`.

**Second-day test (24 Sep scan, bank from the 23 Sep scan only):** 80 orders. **76 fully correct;
4 wrong but flagged** (a GSM, a colour, the RD spec on RP26826-1, and RP26410-1 under the
handwritten `-PC405`); the handwriting also produced one phantom row, flagged. **0 silent.** Caveat:
most of the 24 Sep orders are the same printout content as 23 Sep, so this is a new scan of largely
known text, not a fully new page set. Output: `ext_read_2026-09-24.csv` (project).

**Bank grown, 28 Sep 2026 (James: yes):** the verified 25 and 28 Sep rows (`data/ext_truth_2026-09-25.csv`,
`data/ext_truth_2026-09-28.csv`; two independent reads + printed totals + every difference settled by eye) were added:
3,894 → **10,844 glyphs**, now including F and N. **Blind test first** (bank + 25 Sep only, reading 28 Sep, never seen):
same accuracy, **0 silent errors**, flagged rows 35 → 29 (fewer false alarms). With both days in, OF / BD / NS read
correctly and unflagged. Pages whose row count differs from the truth (rows under handwriting) are skipped by `train`.

**Not done yet:** R9 checksum in the glyph reader (Total Sheets and Weight columns, plus
continuation cut rows); the special-instructions text is still read by Tesseract (fine for
`RUN WITH` / `VOIDFORM` keywords, not for numbers); rows under handwriting.

**Files** (this folder and the Claude Project):

| File | What |
|---|---|
| `ext_scan_reader.py` | The reader. The hardcoded rules are at the top. `train` / `read` commands |
| `ext_truth_2026-09-23.csv` | 82 verified rows from the 23 Sep scan: the training labels |
| `glyph_bank.npz` | Built from the scan + truth file with the `train` command (1 MB; rebuild if missing) |
| Source scan | `doc05228320260923140823.pdf` (James's upload, 23 Sep 2026). **Save it to `Source\`**: the bank is rebuilt from it |

---

## 7.8 Full transcription of the 23 Sep packet (24 Sep 2026)

James: *"extract and product 3 excel file. lets see if there are any other issue."* Every field of all
three documents was transcribed from the page images: 82 EXT orders with 130 cut rows, 70 CNV rows on
10 sheets, and 55 FRM formula rows / 250 feeder settings on 13 pages. Scripts then cross-checked them.
The EXT key fields match `ext_truth_2026-09-23.csv` exactly.

| Workbook | Sheets |
|---|---|
| `EXT Extrusion Schedule 2026-09-23.xlsx` | Orders · Cut Rows · Line Totals (formulas) · Issues · Pages · Read Me |
| `CNV Converting Schedule 2026-09-23.xlsx` | Orders (status split into X / Y / left, sheets check) · Banner Notes · Issues · Read Me |
| `FRM Formulation Report 2026-09-23.xlsx` | Formulations (long: one row per feeder) · Order to Formula · Set Sums (formulas) · Pages · Materials · Issues · Read Me |

**Checks that passed:** every printed line total and the Final Total (6,141,058 PCs / 20,802,359 LBs)
equal the rows. Missing report page 11 held no orders. Every EXT order has a formula on its line, and
every FRM order is on the EXT schedule. Every EXT weight is within 2% of sheets × size × GSM.

**Issues found** (full list on each workbook's Issues sheet):

- **EXT `# Plt` is capped at 999.** H68A091-1 needs 1,880 pallets and H64A244-1 needs 1,044; both
  were corrected by hand. Any order over 999 pallets is understated on the printout.
- **VOIDFORM orders carry two different weight targets.** For all seven with a stated range, the GSM column is about 7%
  above the "RANGE IS … GSM" in the special instructions (e.g. 631 vs 582–600).
- **CNV SD22 H64A244-1:**
  - Total Sheets 1,431,000 ≠ 560 × 2,700.
  - Semi size 60 4/16 × 36 4/16 ≠ the EXT size of 31 5/8 × 38 1/2.
- **CNV H65A163-1:** Total Sheets prints "201.6" (it should be 201,600), and status 145 OF 141.
- **CNV H5BA121-1:** status 53 OF 52.
- **CNV RP26731-2:** listed twice on SD31, with blank quantities.
- **FRM Line 8/9:** settings add to 107/102/104/107 and 91/85, while Line 7 (same layout) adds to exactly 100. *Explained 25 Sep (§7.12): on SE31/SE32 Set is an auger setting, not a %.*
- **FRM `Q1203K` on Line 12:** F1203K everywhere else, so probably a typo.
- **FRM backup codes:** H69A097-1's backup formula has the same code as its main formula.
- **FRM codes reused:** the same formula code has different recipes on 8 lines.
- **FRM spellings:** the virgin resin is written four ways.
- **EXT `# Plt` meaning:** sometimes the remaining pallets and sometimes the full order. The EXT
  "PLTS DONE" notes lag the CNV status.

Build scripts and the transcribed JSON: Claude Project `claude/formulation/packet_extract/`.

## 7.9 Product Master (material master), started 24 Sep 2026, simplified in Rev 0.8

James: *"I want to maintain a master data list as well … Product Code as first column. Product Code
is basically our material master number."* Then (Rev 0.8): *"let product master stay as product
master. no need to keep history or line. just a column that said when is the last update. the
product master should have the basic data from extrusion and converting. I will give you
formation data after."*

The workbook is `Product Master.xlsx`, built by `build_master.py` from the 23 Sep packet. It has two sheets:
- **Product Master:** one row per Product Code (after 24 Sep: 96 codes; 65 with EXT data, 51 with CNV data).
- **Read Me:** notes and a live summary.

| Column group | Columns |
|---|---|
| Key | **Product Code** (col A, never duplicated) |
| Extrusion (green) | Material, Grade, Spec, Colours (3 layers), Thk, GSM, GSM Range (VOIDFORM), Width, Length, Cut Size, EXT Pack Code, PCs/Stack, Stk/Plt, Handling Tags |
| Converting (brown) | CNV Die #, Die Description, Semi Size, Semi pc/plt, Colour, Apl., MM, Flute, Plate, Ink, CNV Pack Code, Pc/Plt, Piece Wt Target / Min / Max, Marking |
| Formulation (olive, Rev 1.0) | Formula Code(s) (daily FRM primary + calc codes within a year of the last run), Formula Last Run; also End Use (Packaging / Graphic Arts, from the calcs) in the extrusion group |
| Control | Source (Packet / Formulation calc), Check (orange = product disagrees with itself or with its code; 12 rows on 23 Sep), Status (Draft / Verified / Needs Review / Obsolete), **Last Updated** (date of the packet that last added or changed a value on the row) |


**Rules:**
- The sheet holds no order history and no line assignments. Extrusion line, die and formula by
  line, order history, and first/last seen were removed in Rev 0.8.
- 1-up/2-up cutting and web width are per-order choices, so they are not kept.
- If a product shows two values, the cell lists both (`A | B`) and Check names the field.
- **Daily merge (Rev 0.9):** `build_master.py` reads the prior master (`PRIOR_MASTER`) and merges one
  packet into it. A new code is added as Draft. A new value for an existing code is added beside the
  old one (`A | B`), Check names it with the date, and Last Updated changes; a Verified row that
  changes goes back to Needs Review. A code missing from a packet is never deleted.
- 24 Sep merge: 96 codes (5 new: RPP40WB1689, RPA40KS824, RPP40WB1186 from EXT; DPP40KS409,
  DPP40WB1552 from the new SD21 Flat-Bed sheet). No existing product had a changed value.
- **Formulation data:** James will provide it separately. Columns for it will be added after that.

The 7-sheet version (Rev 0.7) is kept locally as `build_master_v1_7sheet.py` for reference only.

## 7.10 Daily run, as done for 24 Sep 2026

James sent the 24 Sep packet (`doc05237220260924134843.pdf`, 41 pages) with *"todays data"* and
*"update your 4 excel sheet"*. The run:

1. Render pages at 300 dpi, rotate to landscape, cut each page into quarter tiles.
2. Find the documents from the page titles: EXT p1–16, CNV p17–28, FRM p29–41 (page ranges change day to day).
3. Transcribe to JSON with yesterday's files as the schema (8 parallel readers, each told to take every
   value from today's image). Spot-checked by eye: FRM Line 4, CNV SD21.
4. Run `ext_scan_reader.py read` on the scan as an independent check of the EXT key fields (§7.7).
5. `PKT_OUT=<json dir>/ PKT_DATE=YYYY-MM-DD PKT_SRC=<scan> PKT_CFG=cfg_<date>.json python3 build_xlsx.py`
   → EXT / CNV / FRM workbooks. The day's hand-found issues go in `manual_issues.py` (saved per day
   as `manual_issues_<date>.py`); the day's Read Me notes go in `cfg_<date>.json`.
6. `PRIOR_MASTER=<Product Master.xlsx> python3 build_master.py` → merge into the Product Master.
7. Recalculate every workbook (0 errors required).

**24 Sep results:**
- 80 EXT orders, 69 CNV rows, 51 FRM formula rows.
- Every printed line total matches its rows. SE25 again has no total, because report page 11 is
  missing again. The Final Total matches all rows on LBs (20,752,083). PCs are 160,080 short, which is
  exactly the two H64A244-1 cut rows (2 × 80,040) on the missing page. **Ask for report page 11 to be
  scanned:** it has now been missing two days running.
- Every EXT order has a formula on its line, and every FRM order is on EXT.
- **No formula setting changed from 23 Sep.** Only the order lists changed. New orders: H69A242-3
  (L2), H69A255-1 (L4), RP26923-1 (L10). Gone: H68A007-1, H69A099-1, H69A105-4, H69A197-1, RP26910-1.
- **New converting sheet SD21 Flat-Bed** (2 orders).
- **Slitter page 1 was scanned twice** (p25 = p26). `load.py` now drops an identical second scan.
- **New issue:** RP26618-3 board use 202 OF 200. The issues carried over from 23 Sep are still open
  (999-pallet cap, VOIDFORM GSM ~7% over the stated range, Q1203K, Line 8/9 sums, H64A244-1
  converting sheets/size, H65A163-1 201.6, RP26731-2 listed twice).
- Pen dots in the left margin now sit beside the new orders only (H69A242-3, H69A255-1). They may
  mark new orders; ask James.

## 7.11 Formulation records on SharePoint (surveyed 24–25 Sep 2026)

James: *"start going through the formulation record"* — site ProfileProcessManagement-TechnicalFormulation,
folders `Daily Formulation` and `Profile Formulation - 2023`. Inventory of all 581 files:
Claude Project `claude/formulation/records/formulation_records_inventory.csv`.

| Folder | What it holds |
|---|---|
| `Daily Formulation/Old Formulations` | **Current per-line formula books**: one Word file per line, L01–L16 (`L##-form-1.doc` / `-01.doc`), each listing every formula used on that line (orders, materials, settings, notes) back to ~2009. Edited 30 Jul–3 Sep 2026. |
| `Daily Formulation/PDF 2026/2026-01 … 2026-07` | 134 daily FRM PDFs, 2 Jan–31 Jul 2026. **Image-only scans** (no text). Nothing after July. |
| `Daily Formulation/06302026`, `07172026` | Snapshots of the daily line sheets (`L##-form.doc`) plus the formula books. |
| `Profile Formulation - 2023/FORMUL` | Legacy 1997–2015: auger speed–weight tables (`Formul01–10.xls`), die gaps, calibration, 2012–15 files. 249 folders, most empty. |

- Lines 11 (SE41, last edited Mar 2018), 14 (SE44, May 2015) and 15 (SE51, polystyrene foam with N-butane,
  Jun 2016) have formula books but look idle (§10 Q6).
- Only 6 of 16 formula books convert to text through the SharePoint connector (L07, L09, L11, L12, L14, L15);
  the other 10 fail Graph's conversion. The Technical Formulation library is **not** synced to James's PC
  (only Converting Team, Process Control and Production Data Control are), so the originals can't be read
  locally yet. The calc workbooks (§7.12) supersede most of this need.

## 7.12 Tech's formulation calc workbooks → `Formulation Master.xlsx` (25 Sep 2026)

James sent 14 workbooks: *"Here are the formulation calculation which also has our Auger Crew rotation
calibration"*: `SE11/12/13/21/22/23/24/25/31/32/43/61 Formulation.xls` (+ an older `Copy of SE25`, left
out: every block in it is also in SE25) and `Production Formula Item-092226.xls`. **No SE42 workbook.**

**Layout:** one sheet per product type (e.g. `3.0 mm WB-P (28)`); each sheet holds calc blocks, one per
order: order(s), product code(s), formula code, Prod. Period, Thk, GSM, line speed, output lb/hr, grade
(end use), size, then per hopper `H n (gear ratio, screw)` → material, **calibration slope (g/min per
setting unit)**, formula setting, g/min, formulation %. SE24/SE43 blocks hold % only; SE61 has
extruders A–D plus a Total; SE24/SE31 co-ex blocks have A/B/C groups.

**Read:** 5,125 blocks (2015–2026), 28,289 block × feeder rows, 2,083 product codes, 346 line + formula
codes, 1,264 recipe variants, 519 calibrations. g/min = slope × setting on every block but 4.
Parser `parse_fcal.py`, builder `build_formulation_master.py` (Claude Project `claude/formulation/calc/`).

**Dates:** the Prod. Period on the block where given, else read from the order number (inferred:
`RP26811` = 2026-08-11; `H69A…` = Sep 2026; older `H` + letter year, K = 2009 … W = 2021). The two agree
on all but 29 of ~1,700 blocks.

**`Formulation Master.xlsx` sheets:** Formula Library (line + code + recipe; Current/Earlier) · Current
Recipes (one row per feeder — what the automation reads) · Auger Calibration (current slope per line,
hopper, material; earlier slopes) · Calibration History · Product to Formula · FRM 24 Sep vs Calc ·
Formula Item Log · Issues · Calc History (raw extract).

**Findings:**
- **The FRM page is copied from these calcs:** 22 of 94 FRM rows on 24 Sep match a calc block exactly
  (same settings, same code), e.g. SE11 FU0022WB3 50/15/16/45/6 = WB 4.8%, talc 6.0%, 1203K 22.6%,
  virgin 63.7%, CaCO3 2.9%.
- **Formula codes disagree between FRM and calc for the same settings (32 rows):** FRM `FUA152WB4` is
  `FUA012WB4` in the SE13 calc, `FUA062WB4` in SE21/SE23, `FU062WB4` in SE12; `FUA152KS4` ↔ `FUA032KS4`;
  `FU0021WB4` ↔ `FU0041WB4` (SE23); `FUA151WM4` ↔ `FUA152WB4` (SE31); `RU0000KS3` ↔ `RU0001KS3`;
  `FU0001WBD` ↔ `FUA001WBD`; `FU001GTW4` ↔ `FU0014WB4`. Which one is the real code? (§10 Q9)
- **Settings differ (24 primary rows):** e.g. SE21 RU0000KS4 (FRM: H3 Mix Reclaim 99, H4 KS 10; calc: H1
  Mix Reclaim 65, H4 KS 10); SE32 RP26731-1/RP26525-3 (1203K 16/18 on FRM vs 24/27 in calc); SE23 FU0021WB4
  (FRM reclaim recipe 45/10/60/20 vs calc 85/12/28/24); SE25 H68A111/RP26923/H69A097/H66A116; SE61.
- **Two calibration slopes in use for the same hopper + material in the last year (8 cases)**, e.g.
  SE21 H1 6502A 219.1497 vs 231.7782; SE32 H2 1203K 92.2099 vs 82.3269. Sheets copied from old sheets carry
  old slopes, so their % is off.
- 140 blocks use `FU062WB4` (8 characters) and other codes break the pattern (`FX020WB4`, `HU000WB5`).
- Hopper setups: SE11/SE12 H1 1:36 15x25, H2 1:36 39x39, H3/H4 1:36 69x69, H5 1:36 39x39; SE13 same but
  H4 1:14; SE21/22/23/25/31/32 H1 1:14 69x69, H2/H3 1:36 69x69, H4 1:100 or 1:70 45–49, H5 1:36.
- `Production Formula Item` = a log by date/shift of line, order and "Formula Item #" (1–8). Meaning of
  the item # unknown (§10 Q10).

**Product Master (§7.9) now carries formulation data:** Formula Code(s), Formula Last Run, End Use,
Source; the 1,990 products found only in the calcs were added with their basic data (Thk, GSM, cut size,
end use — GSM/size only from blocks naming that product alone). 2,086 products in total.

## 7.13 Target file set and design review (25 Sep 2026)

**Agreed with James (25 Sep):** six files: (1) **Real Formulation Master**: weight % per formula code + lb/hr
by line (13 active lines: SE11 12 13 21 22 23 24 25 31 32 42 43 61) + a line-deviation flag, with a
**Change Log tab** (every recipe or slope change: date, who, why, old → new); (2) **Auger Calibration**
(most recent record); (3) **Formulation Report Record** (what was issued each day, per order and feeder);
(4) **Daily Formulation Report** (generated, never hand-edited); (5) **Extrusion Production Record**
(converting kept inside it); (6) **Product Master** (auto-populates; a new product with no formula goes
to exceptions). Not built yet: James asked for this review of disconnects first.

**Disconnects found (evidence from the 23–24 Sep packets and the 5,125 calc blocks):**

*A. Which source wins*
1. Three formula sources disagree: calc workbooks, Word formula books, daily FRM. On 24 Sep: 32 FRM rows
   have the same settings as the calc but a different code; 24 primary rows have different settings. In
   SE12 H69A242-3, SE23 RP26731-2 and SE25 H68A111 the FRM issues the WB-reclaim recipe while the calc holds
   the no-reclaim one. Need a rule: FRM as issued = record; Real Formulation Master = target; calc = derived.
2. Alternate formulas (reclaim run-out, VOIDFORM, sign blank, corn box) are not in the calcs at all (8 of 8
   on 24 Sep). They exist only on the FRM and in the Word books, 10 of which the SharePoint connector can't read.
3. The calc workbooks' home folder is unknown (they are not in Daily Formulation or Profile Formulation -
   2023). The hard rule needs them read where Tech saves them, every run.
4. 8 of 80 orders on 24 Sep have no calc block (including both SE42 orders; there is no SE42 workbook).
   50 of the 72 that do have no Prod. Period, so the calc can't say which block is current.

*B. Formula code (the key everything hangs on)*
5. Same settings, different code (e.g. FUA152WB4 ↔ FUA012WB4 / FUA062WB4 / FU062WB4).
6. Same code, different recipe by line: FUA152WB4 is consistent (73–74% virgin, 15% 1203K, 8.4–9.2% talc,
   2.5–2.7% WB), but FU0041WB4 ranges 76–85% virgin with CaCO3 on some lines only. Is a code a recipe or a family?
7. The code does not describe the product in many blocks: thickness digit ≠ order thickness in 557 of 4,696
   (e.g. FU0041WB4 on 5 mm); colour ≠ product colour in 300 (WB code on BL, FW, WM, NS products); grade-P
   products on A formulas in 689 (RUN WITH explains some). Either these are errors or §6.1 is wrong, and
   then new codes can't be derived by rule.
8. Malformed codes: FU062WB4 ×140, FX020WB4 ×37, HU000WB5, RO000WB4, FUA102lY4; blocks with no code.
9. What the formula number (152 / 151 / 041 / 062) means is still unknown, so the system can only reuse codes.

*C. Calibration and the weight math ("real formulation")*
10. Slopes are per hopper, not per material, for colour and additives: SE11 H1 uses 5.6139 for every colour
    MB and antistat; every virgin grade (6502A, PC416, Braskem, Basell, Total 4252, HDPE) shares the virgin
    slope. Different pellets have different bulk density, so their weight % is approximate.
11. **Calc material names lag the FRM:** the 2026 calcs say `Talc MB-TL460` on SE11 12 13 24 25 31 32 43 61
    (only SE21 22 23 say `HiTalc ZS`), `CaCO3MB-CA410`, `KS MB-CR401K`. The FRM says `HiTalc ZS (or N40109A)`,
    `CaCO3 – Heritage HM-10MAX/HP`, `KS-MDI PE-500`. If the material changed, was the auger recalibrated?
12. Two slopes in use for one hopper + material (8 cases): sheets copied from older sheets.
13. No calibration date or owner anywhere; "most recent" can only be inferred from use.
14. **Absolute rates don't reconcile:** auger total g/min is 1.3–3.5× the calc's Output lb/hr on every line
    (median ≈ 2×). Unit of the slope (g/min vs g/30 s as in the 1997 tables) or the output formula is off.
    Until solved, lb/hr per material = weight % × line lb/hr, not auger g/min.
15. **Output lb/hr uses a fixed width per line group:** 1.996 m (78.6") on SE11–13, 2.634 m (103.7") on
    SE21–SE43, 2.295 m on SE61, whatever the order's web width (0.64–2.74 m on 24 Sep), at the planned line
    speed. So it is gross die-width throughput. Confirm that is the lb/hr wanted.
16. Feeder naming: FRM SE31/SE32 shows "A V1–V4" while the calc uses H1–H5 with gear ratios (matched by
    position on 24 Sep); SE24/SE43 are % only (no calibration); SE61 has `Auto` feeders.

*D. Materials*
17. 210 material spellings in the calcs vs FRM text; virgin resin in the calc (PC416, Total 4252, PC5050)
    differs from the FRM text ("PP Virgin-silo 3 (6502A)"). A material master (item no., name, bulk
    density, slope per hopper) is needed before weight % can be trusted.

*E. Products and orders*
18. Product Master conflicts between calc and packet (e.g. RPP40KS2136 GSM 651 vs 1003; RPA40WB3142 Thk 4 vs
    4.3); 48 products coded thickness 33 carry Thk 3.0.
19. VOIDFORM: EXT GSM is ~7% above the instruction range. Which GSM drives lb/hr and the formula?
20. Calc blocks covering several products carry one GSM/size; RUN WITH orders take another product's formula.
21. Order-number dates are inferred (agree with Prod. Period on all but 29 of ~1,700 blocks); confirm.

*F. Records and timing*
22. Daily FRM PDFs stop at 31 Jul 2026, are image-only and miss 14 weekdays; our records start 23 Sep.
    Backfill Aug–Sep from scans?
23. Report page 11 missing two days running.
24. Formula Item # meaning unknown; Item Log sheet names don't match the dates inside.
25. Timing: the system only sees the packet after it is printed (~13:30). To draft the FRM it needs the EXT
    scan before Tech starts.

**Status after the sibling documents were read (Rev 1.2, §7.15):** #13 partly settled (the calibration
records exist: `Process tech/CALIB`, IWPFM031, the 2024 calibration screen; no current per-hopper table found
yet). #15 settled as the house convention (throughput is calculated, not measured, and the plant wrote so in
1998); what is still open is gross die width vs net order width. #17 partly settled (IWPFT062 is the material
code list; `PC416` = F6502A). #10 and #12 are now hard checks A2/A3 in §7.14. #16: the archive adds that
hopper numbers don't carry between Lines 8 and 9 either. **Rev 1.3 (§7.16):** #14 has a likely explanation (the augers
run on demand and the settings only set the ratio; Q20). #16 is settled: Lines 8/9 are auger lines laid out like
Line 7's weight blender. #10 and #12: the slopes are one shared set per hardware + material, copied to every line.

## 7.14 Auger (hopper) preference rules — DRAFT, 25 Sep 2026 (James to confirm)

**James (25 Sep 2026), verbatim:** *"I think we also need to set some preference with Auger. Take line 6 as
example. Auger 1 2 and 3 are larger so 1 and 3 are usually the main PP that feed Co poly (6502A) or Homo
(1203K) or Reclaim while 2 feed our main additive (Talc). 4 Feed our color (W26038A blue white) and 5 feed
caco3 additive."*

The 2025–26 calc blocks for SE23 agree with that exactly: H1 (1:14, 69×69) virgin 48 / WB reclaim 7; H2
(1:36, 69×69) talc 53; H3 (1:36, 69×69) 1203K 27 / WB reclaim 26; H4 (1:70, 49×49) WB colour 54; H5 (1:36,
39×43) CaCO₃ 51. **Once confirmed, this becomes a hardcoded rule set like R1/R2 (§7.6), in `auger_rules.py`.**

**The pattern holds within a line but not across lines. Read the function, not the number** (the archive's
standing warning: the plant's *Hopper Auger Ratios* master table has lines 1–3 running #1 colour → #4 virgin
and lines 4–10 running #1 virgin → #4 colour).

| Line | Code | H1 | H2 | H3 | H4 | H5 | Differs from Line 6 |
|---|---|---|---|---|---|---|---|
| 1, 2 | SE11, SE12 | **Colour** (1:36 15×25) | Talc (1:36 39×39) | Homo / reclaim (1:36 69×69) | **Virgin** (1:36 69×69) | CaCO₃ / Vistamaxx (1:36 39×39) | Colour and virgin swap ends; large augers are H3 + H4, H2 is small |
| 3 | SE13 | Spare small additive (CaCO₃, UV; 9 uses) | Talc | Homo / reclaim | **Virgin** (1:14 since 2019) | **Colour** (1:36 39×39) | Colour on H5, not H1 as on Lines 1–2 |
| 4 | SE21 | Main PP (1:14 69×69) | Talc | Second PP | Colour (1:100 45×49) | CaCO₃ (1:36 39×43) | Same as Line 6 |
| 5 | SE22 | Main PP | Talc | Second PP (mostly reclaim) | Colour (1:100 49×49) | CaCO₃ (**1:36 69×69**) | H5 is a large auger |
| **6** | **SE23** | **Main PP** | **Talc** | **Second PP** | **Colour** (1:70) | **CaCO₃** | **the reference** |
| 7 | SE24 | Weight blender, set in %, per extruder A/B/C: V1 colour · V2 CaCO₃ (or FA additive) · V3 talc · V4 virgin · V5 homo | | | | | No slope; check is Σ = 100 per extruder |
| 8, 9 | SE31, SE32 | Virgin | **Homo** (or WB reclaim on SE32) | **Talc** | Colour (1:70) | CaCO₃ / Vistamaxx / white NPC | Talc and second PP swap (H2 ↔ H3) |
| 10 | SE25 | Main PP | Second PP (homo, reclaim or virgin) | **CaCO₃** | Colour (1:70) | **Talc** (1:36 39×43) | Talc and CaCO₃ swap (H3 ↔ H5): talc on the small auger |
| 12 | SE42 | **Weight blender** (V1–V9, set in %); no calc workbook, probably because a weight line needs no slope | | | | | No slope; Σ = 100 |
| 13 | SE43 | Set in %: V1 talc · V2 talc / Vistamaxx · V3 minor additive · V5 virgin · V7 homo · V8 WB colour · V9 KS colour | | | | | No slope |
| 16 | SE61 | **Weight blender**, co-ex, per extruder: A1 virgin / homo · A2 reclaim · A3 talc · A5 black MB; B1 virgin; C1 virgin · C2 reclaim · C3 talc · C5 colour · C6 antistat; D1 virgin | | | | | No slope; `Auto` = balance to 100 |

On Lines 4–6, H1 and H3 carry either PP. The main (largest) stream goes on H1, the fast 1:14 auger. For
example, SE21 KS formulas (FU0051KS4) put mix reclaim on H1 and 6502A on H3, and SE23 FU0041WB4 in Jan 2025
put WB reclaim on H1 and 6502A on H3. **So the rule that has to follow the material is the slope, not the
hopper.**

**Hard checks (proposed; every calc block and every FRM row on the auger lines, every run; weight lines get the Σ = 100 / `Auto` checks in §7.16 instead):**

| # | Check | Action |
|---|---|---|
| **A1** | Material's role is allowed on that line's hopper (table above) | Outside the role = **stop** unless the Change Log has it |
| **A2** | **The slope must be that hopper's calibration for that material.** A slope that belongs to another material on the same hopper is an error | **Stop**. This is the RP25711-2 case below |
| **A3** | Material has no calibration of its own on that hopper and borrows another's | Flag, unless James/Tech approve a **calibration family** (e.g. all WB/KS colour MBs share one H4 slope) |
| **A4** | Hopper hardware (gear ratio, screw) in the block header matches the line's hardware table | A change voids every slope on that hopper until it is recalibrated (Line 3 H4 went 1:36 → 1:14 in 2019, 2.57× at the same dial) |
| **A5** | Setting inside the calibrated range | Flag settings under ~5 or at the dial maximum: the archive curves are unusable near zero, and saturation sets in at the top |
| **A6** | When two PP streams swap between H1 and H3, their slopes swap too | Otherwise A2 |
| **A7** | **Slope fits the hardware:** slope × gear ratio (grams per auger turn, up to a constant) within ~8% of the norm for that screw size and kind of pellet (§7.16) | Flag: slope copied from another hopper, or the header's gear ratio is wrong |

**Evidence (calc workbooks, all years):**

- **The case in James's screenshot:** SE23 sheet `4 mm WB-P (61)`, RP25711-2, FU0041WB4, 11 Jul 2025. H1 is
  `PP WB Reclaim` at slope **219.1497**, which is the H1 **6502A** slope (48 uses). The same line's Jan 2025
  sheets `(57)` and `(58)` carry an **H1 reclaim slope of 232.1703**. If 232.1703 is right, the sheet
  under-counts H1 reclaim by 5.6% (219.1497 / 232.1703 = 0.944). The reclaim-only R4 sheets (RP25424-1,
  H54A247-1, H59A059-1, RP25910-1, last 10 Sep 2025) do the same thing.
- **A2 across all lines: 258 feeder rows (34 hopper + material pairs) use another material's slope although
  that material has its own on the hopper. 33 rows are in the last 12 months.** The ones that move the
  numbers: SE21 H1 virgin at reclaim's 231.7782 vs its own 219.1497 (33 rows, last 1 Jul 2026, 5.8%); SE32 H4
  WB colour at 17.5191 vs 19.8612 (16 rows, last May 2026, 13%); SE13 H4 reclaim at virgin's 219.1497 (9 rows,
  last Aug 2026); SE21/SE22 H3 UV at 1203K's 82.3269 vs its own 74.6577 (10%). Pairs 0.2% apart (82.3269 vs
  82.4662) are copy-over noise, not errors.
- **A3: 3,319 rows (342 in the last 12 months) borrow a sibling's slope because the material has none of its
  own on that hopper**: KS ↔ WB colour, 1102K → 1203K (1203K replaced 1102K on the old 1102K slope, 82.3269),
  WB ↔ mix reclaim, and most colour, UV and antistat MBs. That is either an approved family or a missing
  calibration. James/Tech to say which (§10 Q13).
- **A1 on the draft table: 82 of 5,988 feeder rows in 2025–26 (1.4%) fall outside it.** Mostly: SE21 H3
  antistat (21), HDPE on SE21/SE13 H1/H3/H4 (32, trials?), SE22 H5 1102K (3), SE25 H3 colour / homo / UV (7),
  SE23 H5 talc (2), SE23 H2 reclaim (2), SE31 H1 reclaim (2). Each is either a rule to widen or a sheet to fix.

**Why it matters for the "real formulation":** weight % = slope × setting ÷ total. A wrong slope makes a wrong
%, and nothing on the sheet shows it. The archive also shows the calc's model is simpler than the hardware.
The plant's curves are cubic with intercepts (−4.5 g to +33.2 g at zero), the blending system is volumetric
at ±5%, and the one verification that states a target (19 Jul 2024) measured colour at 3.7% against 2.1%.
**So the Real Formulation Master must label calc % as *target by calibration*, never *measured*.**

**Files:** `auger_rules.py` (draft role table and the `role()` classifier; saved to the Project under
`claude/formulation/calc/` and to this folder). Checks A2/A3 extend the existing "two slopes" check in
`build_formulation_master.py` (§7.12). Nothing is enforced until James confirms the table.

## 7.15 What the other pipeline documents settle (read 25 Sep 2026)

James: *"if you havent read other process MD go through them"*. Read: `README.md`, `ARCHIVE-HANDOVER.md`
(materials, plant map, controlled documents, parts 25, 26, 32, 35), `OEMS Management/INDEX.md`, the Void Form, QC
Digital Record, Management Review, MR BI, Physical Inventory and CAS handoffs, and the archive's
`auger_dose_from_setting.py` / `auger_phantom_origin_check.py`.

**Settled or strengthened:**

1. **`PC416` = Formosa F6502A** (IWPFT062: `50-1560-050 · PC416 · F6502A`). `PC419` (`50-1560-809`) and
   `PC716` (`50-1560-060`) are multi-vendor copolymer codes. **IWPFT062 is the material master** to key the
   material table on. On file it is Rev 13, while Rev 16 was approved in Mar 2024. Vistamaxx 3588FL is
   `50-1560-405 · PC3588`.
2. **IWPFT057 formula code system (Rev 2) is obsolete except for the colour letters**; its reclaim letters J/K/L/M
   (WB, dark mix, light mix, blue-white) have 1997–2006 auger calibrations. Today's FU/FS/RU/BF codes (§6.1)
   are not documented anywhere found so far.
3. **Output lb/hr is calculated, not measured, and has been since at least 1998.** A process record says it at
   source: *"The through put is based on line speed, average 950GSM for 2.64 M line."* That is the calc's
   formula (§7.13 #15).
4. **Calibration records exist:** `Process tech/CALIB` on the Technical Formulation site (13 files: `CALDATA.XLS`,
   a 33-page PPT-E-7 set for 1999–2001, `CALIB-SE12-102208.XLS`, `CALIB-SE25-051809.XLS`, three MathCAD sources).
   Also **IWPFM031** *Standard Calibration Procedure for the OMRON Blending System*, Rev 9, with per-line
   attachments (controlled, **read only**), the `Blending System Calibration Screen 2024-09-25` folder, and
   `Auger Throughput Verification Records 2010-2024` (33 forms, last 17 Sep 2024). **None of these has been read
   for current slopes yet.** The Auger Calibration file (§7.13 file 2) should come from whichever is current,
   not only from the calc sheets.
5. **Hopper hardware:** the plant's *Extruder Blender — Hopper Auger Ratios* master table (revisions 2011, Mar
   2019, Aug 2019) gives ratio, OD × pitch and tube colour for lines 1–10. The only change in eight years is
   Line 3 H4, 1:36 → 1:14 (2019), which the SE13 calc header matches. The 1999 table notes that the B and C
   extruder blenders on Lines 8 and 9 are numbered oppositely; nothing records this being checked.
6. **Calibration maths:** the plant's curves are cubic, not through the origin, and unusable below dial ~5. The
   1997 Line 1 and Line 3 fits carry a phantom point at the origin (43 fits). The dial is 0–999 on Lines 1–4
   and 0–100 on Lines 6, 8 and 9 (1997 hardware; Lines 8/9 re-driven in 2009). The calc's slope × setting is a
   linear simplification. That is acceptable for targets, but it is one reason the auger total doesn't match
   the output (§7.13 #14).
7. **Extrusion Production Record source:** the plant's **paperless production system on AS400** (extrusion live
   late 2024, converting 2025, packing mid-2025; documented in `OEMS\8. Software, ERP, IT System\Bar Coding\SYSTEM\`)
   is the likely source of actual production, rather than the printed EXT plan (§10 Q17).

**House rules adopted from the sibling pipelines (added to the standing instructions):** re-stage the live file
immediately before every build; after every device write, stage it back and verify it **by content**, not by
size. SharePoint adds `customXml` and metadata parts to every `.xlsx` on upload, so file hashes never match the
built file; compare cell values. Keep a checksum manifest (§11). Controlled Technical documents are read-only.
Never open the plaintext password files flagged in the OEMS index.

## 7.16 Dosing: weight lines vs auger lines (James, 26 Sep 2026)

**James (26 Sep 2026), verbatim:** *"correct line 7,12,13, and 16 use more modern weight based dosing. The rest of the
lines use old Auger dosing. What make it even worst is that the motor rotation speed is no RPM or some measurement.
It is simply speed setting 0 to 100. You can probably tell when you see that the formulation dont even add up to 100
for those lines"*

| Dosing | Lines | What `Set` is | Adds to 100? | Weight % comes from |
|---|---|---|---|---|
| **Weight blender** | 7 (SE24), 12 (SE42), 13 (SE43), 16 (SE61) | Weight % per extruder | Yes, per extruder; one feeder may be `Auto` = the balance | The setpoint itself (weighed) |
| **Auger** | 1–6 (SE11 12 13 21 22 23), 8 (SE31), 9 (SE32), 10 (SE25) | Motor speed 0–100, whole numbers, **no RPM feedback** | No | Calibration slope × setting ÷ total (a calculated target) |

**Hardcoded** as `DOSING` in `load.py` (daily pipeline) and `auger_rules.py` (formulation), in a block marked
*DO NOT CHANGE WITHOUT JAMES'S SAY-SO*, the same way as R1/R2.

**What the data shows, and what this settles:**

1. **FRM sums, 24 Sep:** the weight lines add to 100. SE24 is 100 per extruder (FSA200WB4 100/100/100); SE42 and
   SE43 are 100. On SE61, extruder A is 61 fixed + `Auto` (F6502A) = 39, extruder C is 7–8 + `Auto` = 92–93, and B
   and D are 100. So `Auto` is the balance. The auger lines don't add to 100: Line 8 is 102/104/107, Line 9 is 91/85,
   Line 1 FU0042WB3 is 135. The 23/24 Sep question "Are V settings percentages?" is answered: no. Lines 8/9 only
   borrow Line 7's A/B/C page layout.
2. **Same code, different settings by line, explained.** FUA152WB4 is 50/27/14/71 on L2 and 99/18/54/43 on L6, but its
   weight % is the same everywhere (73–74% virgin, 15% 1203K, 8.4–9.2% talc, 2.5–2.7% WB, §7.13 #6). The settings
   differ because the hoppers, gear ratios and slopes differ. **So the recipe is the weight %; settings are derived
   per line.** That is the core of the Real Formulation Master.
3. **The calc workbooks already follow the split:** SE24, SE43 and SE61 hold % only, with 0 slopes in 6,559 feeder
   rows. SE61 adds extruder shares (e.g. A and C 41%, B and D 9%) and lb/hr per material. All nine auger lines carry
   slopes. No SE42 workbook: a weight line needs no slope calc (Q11).
4. **IWPFM031** (*Standard Calibration Procedure for the OMRON Blending System*) has attachments for lines 1–2, 3,
   4, 5 and 6/8/9/10: exactly the auger lines. The weight lines are not in it. So IWPFM031 is the auger lines'
   procedure (controlled, read only).

**What it adds (new disconnects on the auger lines):**

5. **Nothing measures what an auger actually does.** With a 0–100 speed setting and no RPM feedback, a drifting drive
   or a worn screw is invisible. The 1997 drive cards differed by ±4% for the same output. The only measurement is a
   timed catch test. The last one on record is 17 Sep 2024, and the one test that states a target failed: colour
   3.7% against 2.1%. **The Auger Calibration file needs a "last verified" date per hopper and an overdue flag.**
6. **The slopes are one shared set, not per-line calibrations.** The same number sits on every line with the same
   hardware:
   - 82.3269 (1203K, 1:36 69×69) on 8 lines;
   - 219.1497 (virgin, 1:14 69×69) on 6 lines;
   - 148.7313 (talc, 1:36 69×69) on 5 lines;
   - 17.5191 (colour, 49×49) on 5 lines.

   Each was calibrated once and copied. **Only SE32 has its own set** (92.2099 / 141.0847 / 19.8612 / 27.493, ±11–13%):
   either a newer calibration the other lines lack, or errors (Q19).
7. **New check A7, the slope must fit the hardware.** The auger turns at setting/100 × motor speed ÷ gear ratio, so
   slope × gear ratio is grams per auger turn (up to a constant). For one screw size and one kind of pellet it should
   be the same on every line, and it is, within 3%:

   | Screw | Material | Grams per turn index (2025–26 calcs) |
   |---|---|---|
   | 69×69 | PP pellets | 2,969 (1:36), 3,068 (1:14) |
   | 69×69 | Reclaim | 3,140 (1:36), 3,245 (1:14) |
   | 69×69 | Talc | 5,354 |
   | 69×69 | CaCO₃ | 6,380 |
   | 39×43 | CaCO₃ | 1,106 |
   | 39×39 | CaCO₃ | 1,003 |
   | 39×39 | Talc | 842 |
   | 49×49 | Colour | 1,226 |
   | 15×25 | Colour | 202 |

   69×69 vs 39×39 is 6.4× for both talc and CaCO₃, which is consistent geometry. **192 of 5,743 auger feeder rows in
   2025–26 fall more than 8% outside the norm:**
   - **SE22 H4 colour: the header says 1:100 but the slope is the 1:70 slope, 17.5191** (+43%, 97 rows, last 9 Sep 2026).
     If the gearbox really is 1:100, Line 5 runs about 30% less colour than its calc shows. SE21 H4 (1:100, 45×49,
     16.089) gives more per turn than the larger 49×49 screw at 1:70, the same question. The archive says Lines 4–6
     drifted from the design ratios on colour, additive and flake. A catch test settles it (Q18).
   - SE13 H4 (1:14) reclaim at 87.2183, the 1:36 slope: −61% (2 rows, Feb 2025).
   - **The screenshot case, settled by physics:** reclaim on a 1:14 69×69 auger should be ≈ 231.8–232.2 (3,245 ÷ 14).
     RP25711-2's 219.1497 is the wrong slope, and the Jan 2025 sheets' 232.1703 is right.
   - SE32's own set (±11–13%); SE21 H3 antistat 93.3676 (+13%); SE21 H1 virgin at reclaim's 231.7782 (+9%).
8. **Old sheet copies carry old hardware.** The calc was updated when Line 3 H4 went 1:36 → 1:14 in 2019 (header and
   slope 219.1497 from 2019), but 2 blocks in 2021 still carry 1:36 / 82.4662. That is check A4.
9. **Dial resolution.** Settings are whole numbers. 838 of 5,309 auger feeder rows in 2025–26 (16%) run below 10:
   talc 39%, CaCO₃ 34%, additives 35%, colour 10%. At setting 4 (148 rows) one step is 25% of that feeder's dose, and
   the plant's own curves are unreliable below ~5. Check A5: flag settings under 10.
10. **Auger total vs extruder output (§7.13 #14): likely explained.** On 1,233 of 1,239 blocks the augers' total
    rate is above the extruder output (median 1.4–2.5× by line); only 6 are below 1. A continuously running blender
    would have to match the output. A blender that starts and stops on a level switch needs spare capacity, and then
    the settings only fix the ratio. Confirm (Q20). If so, lb/hr per material = weight % × line lb/hr, never auger
    g/min, and all settings on a line can be scaled together to lift low settings off the bottom of the dial.
11. **The weight lines can measure.** A weight blender weighs every component, and most can total usage per
    component. That would be the only measured formulation and material consumption in the plant: a real
    "real formulation" for Lines 7, 12, 13, 16 and an input to the Extrusion Production Record (Q21).

**Design consequences (for the six files, when James says go):**
- **Real Formulation Master:** weight % per formula (per extruder for co-ex), each line tagged WEIGHT (setpoint,
  weighed) or AUGER (target by calibration).
- **Settings on auger lines are derived, never stored as the recipe:** setting = weight % × T ÷ slope, rounded to a
  whole number. The weight % is then recomputed after rounding and shown. T is chosen so the largest setting stays
  ≤ 99 and additives stay ≥ 10 where possible.
- **Daily Formulation Report:** auger lines print setting and calculated weight %; weight lines print % with the
  `Auto` balance.
- **Checks:** A1–A7 on auger lines; Σ = 100 / one `Auto` / `Auto` balance between 0 and 100 on weight lines.

**Code changed (daily pipeline, `claude/formulation/packet_extract/`):**
- `load.py`: the `DOSING` table.
- `checks.py`, FRM section, now by dosing type:
  - weight lines: must add to 100 per extruder, with `Auto` = balance (impossible balance or two `Auto`s flagged);
  - auger lines: setting outside 0–100 → High; `Auto` on an auger line → High; non-numeric setting → Medium.
- `build_xlsx.py`: Set Sums gains Dosing, Auto = balance (%) and Adds to 100? columns, and a Read Me note.
- `manual_issues.py`: the template drops the Line 8/9 "percentages?" question.

Re-ran the checks on the 23 and 24 Sep packets: identical issue lists (82 and 71). A synthetic auger setting of
105 and an impossible `Auto` balance are both caught. The 23/24 Sep workbooks were not rebuilt; they stay as issued.
`auger_rules.py` gains `DOSING`, `rev_index()` (A7) and notes.

## 7.17 Moved to Claude Code (28 Sep 2026)

**James (27–28 Sep 2026):** *"with such major project. Should this be done by claude code instead?"* Answer: yes for
the build phase. The code, the data and the checksum manifest had been kept in step across three places by hand
(this session's temporary cloud workspace, the Project, this folder), and the link to James's PC drops. Then:
*"yes lets do it"*.

**What was handed over:** `formulation-pipeline starter 2026-09-28.zip` in this folder. Unzip it to a local folder
(not synced) and follow its `README.md`: Python 3.11+, Git for Windows, Claude Code, and Tesseract (optional).
It contains:
- `CLAUDE.md`: the standing rules for Claude Code — the hard rule, R1/R2, `DOSING`, the auger rules, the never
  list, the daily and calc runs, and output conventions. It is built from this document's Standing instructions,
  §7.6, §7.14 and §7.16.
- All pipeline code:
  - `daily/`: from `packet_extract/`;
  - `calc/`: parser, Formulation Master builder, `auger_rules.py`;
  - `scan_reader/`: reader, glyph bank, new `render_pages.py`.
- The two transcribed packets, the verified EXT rows and the hand-found issues per day.
- `publish.py` and `config.py`.
- `tests/`.
- `.claude/settings.json`: denies reading `*Password*` files and editing `inputs/`; sets `PYTHONUTF8=1`.
- `.claude/settings.local.json`: gives Claude Code access to this folder.

**What changed in the code (behaviour kept the same):**
- **One `config.py`** for every path, read from an env var, then `local_settings.json`, then a default in the repo.
  The hard-coded `/home/claude/...` and `/mnt/...` paths are gone. Builds write to `out/`, and only `publish.py`
  writes here.
- **The hard rule is now enforced by code:**
  - every input goes through `config.record_read()` (size, modified time, SHA-256, content hash → `work/reads.json`);
  - `publish.py` refuses to replace a published file whose cell content is neither what the build read nor what was
    last published (`data/published_manifest.json`, in git, seeded 28 Sep from the files in this folder: all eight
    workbooks matched §11);
  - an earlier day's daily workbook is refused unless James asks for `--reissue`;
  - after copying, each file is re-read and compared by content.
- The daily scripts read the packet from `data/packets/packet_<date>.json` (`packet_date` and `source_scan` added to
  the 23 Sep file; its content is unchanged).
- The day's hand-found issues and Read Me notes are picked up by date. `RUN_DATE` is used instead of a fixed
  "transcribed" date.
- **The superseded-copy rule is general** (`common.superseded_copies`): a line's "Copy of …" workbook is left out when
  the line has another one. SE25's copy is dropped; SE21's only workbook, itself a "Copy of", is kept.
- Upload-name prefixes are stripped by pattern, not by position.
- The FRM-vs-Calc sheet takes its date from the packet instead of "24 Sep".
- A missing Formula Item log no longer stops the build.
- **Windows:** explicit UTF-8 on every text file. No `%-d` date formats. `TESSERACT_CMD` setting. The PDF rendering
  falls back to **PyMuPDF** (pip only) when poppler's `pdftoppm` isn't installed.

**Regression (rebuilt everything from the starter in a clean folder and compared cell by cell with the published files):**

| Output | Result |
|---|---|
| EXT and CNV 2026-09-24 | **Identical** |
| FRM 2026-09-24 | Identical except the Rev 1.3 dosing columns in Set Sums and one Read Me line |
| 23 Sep workbooks | Data identical. Some Read Me and notes text differs, because the published 23 Sep files came from the 23 Sep version of the code |
| Product Master | **Identical** (and a rebuild from the published master is idempotent: 0 changed) |
| Formulation Master | Identical except the Read Me source line and floats beyond the 15th digit (the published copy was recalculated in LibreOffice, which rounds to 15 digits) |
| Daily checks | 82 issues for 23 Sep, 71 for 24 Sep, as before |
| EXT scan reader, 24 Sep scan | Same result with PyMuPDF as with pdftoppm: 76 of 80 fully correct, 3 wrong but flagged, **0 silent**. PyMuPDF raises 4 more false alarms (21 vs 17) |
| `pytest` | 8 passed with the calc workbooks, 7 + 1 skipped without; same in a fresh unzip |
| `publish.py` | Tested on a copy of this folder: an edited published file is refused, an unchanged one republishes and verifies, and an earlier day's workbook is refused without `--reissue` |

**Where the Project files went in the repo:**

| Project (`claude/formulation/`) | Repo |
|---|---|
| `packet_extract/load.py`, `checks.py`, `build_xlsx.py`, `build_master.py`, `manual_issues.py` | `daily/` |
| `packet_extract/manual_issues_<date>.py`, `cfg_<date>.json` | `daily/manual/`, `daily/cfg/` |
| `packet_extract/packet_<date>.json` | `data/packets/` |
| `calc/*.py` | `calc/` |
| `ext_scan_reader.py` | `scan_reader/` |
| `ext_truth_2026-09-23.csv`, `ext_read_2026-09-24.csv` | `data/` |

The Project copies were refreshed on 28 Sep to the starter's code, so the two match at hand-over. From here on the
repo leads.

**What stays in Cowork:** SharePoint and Outlook through the Microsoft 365 connector, the Project mirror of this
document, and design discussions.

**Still needed from James before the first Claude Code daily run:**
1. Where Tech saves the calc workbooks, so `CALC_DIR` points at the live files (§10 Q14). Until then, copy the 14
   uploaded workbooks into `inputs\calc`.
2. Whether IT allows the installs.

## 7.18 Product Master prepared as the base table (28 Sep 2026)

James: *"we need to prepare the data base"*, then Excel workbooks only, Product Master first, and *"Do what you can for
now, I am working on pulling full data."* The full data pull (AS400 item master or similar) will fill the thin rows.

**Read:** the live `Product Master.xlsx` from SharePoint. The connector returns only the first **1,608 of 2,086 rows**
(through `RPP40WB718`), so this pass covers those. Upload the file, or run the script on James's PC, for all rows.

**James's answers (28 Sep 2026):**
- **Thickness:** *"we have product that is in between such as 3.3mm. Unfortunately our product code doesnt capture that
  and one will have to look at the spec."* The code's thickness is nominal; the **product spec decides**. A code/data
  difference under 1 mm is "confirm from spec", not an error; 1 mm or more is a conflict. Neither is auto-corrected.
- **Letter O for zero:** `DPPAOKS27`, `RBPAOKS14`, `RBPAOKS37`, `RBPAOKS40` are `…A0…` (10 mm), typed wrong in the calc
  sheets. *Confirmed.* Three of the corrected codes (`RBPA0KS14/37/40`) are already in the master, so those rows merge.

**Repo on GitHub (28 Sep 2026):** the starter zip (1,123,527 bytes, SHA-256 `7f2972634fc7e62b`, matches §11) is committed
to `jameschingkuo-cloud/Profile-Formulation`, without `local_settings.json` and `.claude/settings.local.json` (machine
paths). In the cloud session: `pytest` 7 passed + 1 skipped (no calc workbooks), as in §7.17; the 24 Sep EXT and CNV
rebuilt with `RUN_DATE=2026-09-24` are identical by content to the published files, and FRM differs only by the Rev 1.3
dosing columns. GitHub is the code's backup with history; the code's working copy stays outside the synced folder.
James's new output folder, `General\Engineering Pipeline\Production Formulation` (subfolders Product Master, Formulation
Data Base, Daily Formulation Report, Extrusion Schedule, Converting Schedule), is to become `PUBLISH_DIR` once
`publish.py` routes each file to its subfolder. Not moved yet.

**Built:** `product_master/prepare.py` (repo) → `Product Master - Prepared <date>.xlsx`. The Product Master itself is not
changed. Sheets: Product Master with grey code-derived columns (material, grade, nominal thickness, colour; *not
verified*), completeness and activity · Issues sheet · Verify First (run in the last 12 months) · Colour Codes · Import Map
(fill in the source field of the full data pull) · Read Me (source file, modified time, hash, pre-flight).

**Results on the 1,608 rows:**
- All 8 core fields filled on only **30** products. Activity: 462 run in the last 12 months, 465 in 1–3 years, 681 older.
- The code letters agree with the packet data: material 52/53, grade 53/53, colour 53/53 (P = PPP, B = BBB; 3rd letter =
  grade; 6–7 = colour, the outer layer on co-ex `EB KS EB`). Exception: `RBPA0KS70` has a BBB code but PPP data.
- Issues sheet: 46 High (42 thickness conflicts ≥ 1 mm, 4 letter-O codes), 13 Medium, 70 Low (in-between thickness).
- `RBPP0EB1/2`: code `P0` decodes to 25 mm by the letter rule, data says 20 mm. **Does the letter rule hold past `D`?**
- 31 colour codes in product codes; only 7 are on the EXT list (R7). The other 24 (EA, JG, GS, YF, BD, …) need names (Q2).

## 7.19 Database structure and flow (28 Sep 2026)

James: *"lets build the data base structure and flow first, then we design the interface"*. The final goal (James):
*"create an artifact where people can upload production schedule and download formation"*.

**Built (structure only, no data):** `db/schema.py` describes every workbook of the database (folder, kind, sheets,
columns, keys, allowed values, references). From it: blank templates (`python db/schema.py templates`), a checker for
any workbook (`check`), and the column reference `docs/DATABASE_TABLES.md` (`doc`). The structure and the daily flow are
written up in `docs/DATABASE.md`.

- Folders: James's `General\Engineering Pipeline\Production Formulation` subfolders (Product Master, Formulation Data
  Base, Daily Formulation Report, Extrusion Schedule, Converting Schedule).
- Kinds: **master** (changes only through its Change Log, with an approver; rows Draft → Approved), **record**
  (append-only), **daily** (kept as issued), **evidence** (rebuilt from Tech's calcs, never edited).
- New workbooks: Formulation Master (Lines, Materials, Formulas, Recipe = weight %, Line Settings, Product to Formula,
  Standing Notes, Change Log), Auger Calibration (Hoppers, Calibration, Verification Log, Change Log), FRM Draft
  <date> (Draft + Exceptions), Formulation Report Record, Extrusion Production Record, Converting Production Record.
- James (28 Sep 2026): *"add a history file for converting as well. may be useful in the future"*. So converting has
  its own append-only record (one row per date × converting line × order row), and is no longer kept inside the
  Extrusion Production Record as §7.13 file 5 had it.
- The templates carry only settled reference data: Lines (DOSING) and Hoppers (auger_rules.RULES, still James's draft).
- Nothing was published. Decisions for James are in `docs/DATABASE.md` §6 (rename the calc-derived workbook to
  `Formulation Calc Library.xlsx`; who approves; Material ID = IWPFT062 item no.; the variant list; moving the
  published files to the new folders).

## 7.20 Daily run, 25 Sep 2026 packet (processed 28 Sep 2026)

James: *"this is what a production schedule look like. add these data to your data base and find a way to get this data off
the print sheet accurately always. future upload will look like this"*. Scan `doc05252320260928124922.pdf` (41 pages,
14,551,491 bytes, scanned 28 Sep): the **25 Sep** packet (Run Date 9/25/26 14:32:43). The chat upload failed twice and the
SharePoint connector returns no content for an image-only PDF; it came in through a GitHub upload and was moved out of the
tree into `work/scans`.

**Getting it off the print accurately, every day (three independent checks):**
1. Transcription from the page images (7 parallel readers, every value read at zoom).
2. The glyph reader (`ext_scan_reader.py`), which flags what it is unsure of.
3. The printout's own arithmetic: every line total and the Final Total must equal the rows (R9).
`scan_reader/crosscheck.py` (new) compares 1 and 2 field by field and checks 3; every difference is settled by eye, never
automatically. Result: 67 of 71 orders identical; the glyph reader misread 4 fields and **flagged all 4** (0 silent); all
13 line totals and the Final Total (6,131,179 PCs / 20,771,336 LBs) tie exactly.

**Results:** EXT 71 orders on 13 lines, CNV 69 rows on 11 sheets, FRM 50 formula rows on 13 pages. All 17 report pages are
on the scan for the first time (report pages 11-12 hold the end of H64A244-1). Every EXT order has a formula on its line.
New: **H68A153-1 spec `OPOPOP`** (breaks R2; "WHITE OPAQUE"), its new formula FXA020WB4 with WB-W40020M; **RP26923-1
formula changed** FU0021WB4 → RU0001WB4; H69A139-1 on FRM but no longer on EXT. Full list in
`daily/manual/manual_issues_2026-09-25.py` and the workbooks' Issues sheets. Workbooks built in `out/`, not published.
**Product Master not merged yet:** the merge reads the published master, which this cloud session can't open in full.

## 7.21 Two folders: the database and Claude's workspace (28 Sep 2026)

James: *"put it here C:\Users\JamesKuo\Inteplast-WPJK\Profile Production Data Control - Documents\General\Engineering
Pipeline\Production Formulation\Product Master"*, then *"this is where you will put all the MD, PY etc etc that is not data
base related file C:\...\General\Claude MD, PY Pipeline File\Engineering Pipeline\Production Formulation Automation"* and
*"its basically your work space"*.

| Setting | Folder | Holds |
|---|---|---|
| `PUBLISH_DIR` | `General\Engineering Pipeline\Production Formulation\<kind>` | The database workbooks only (`db/schema.py` says which folder) |
| `DOCS_DIR` | `General\Claude MD, PY Pipeline File\Engineering Pipeline\Production Formulation Automation` | This handoff, `.md`, `.py`, code snapshots: Claude's workspace |

- **Copied (SharePoint server-side copy, same bytes, sizes checked against §11):** `Product Master.xlsx` → `Product
  Master\`; EXT / CNV / FRM 2026-09-23 and -24 → `Extrusion Schedule\`, `Converting Schedule\`, `Daily Formulation
  Report\`. The originals are still in the workspace folder; delete them there once James is happy.
- `Formulation Master.xlsx` (calc-derived) stays in the workspace until the rename to `Formulation Calc Library.xlsx`
  is decided (`docs/DATABASE.md` §6.1).
- Code: `config.DOCS_DIR`, `config.published_path()`; `publish.py` routes every file; `daily/build_master.py` reads
  the prior master from `Product Master\`. `data/published_manifest.json` moved to the new paths (workspace files
  keyed `workspace/...`). On James's PC, `local_settings.json` needs the new `PUBLISH_DIR` and a `DOCS_DIR` (see
  `local_settings.example.json`).
- The 25 Sep scan sits in `Extrusion Schedule\` (James put it there). Scans are source files, not database; they could
  have their own `Scans` folder.

## 7.22 Daily run, 28 Sep 2026 packet, and the first FRM Draft

Scan `doc05253620260928134035.pdf` (25 pages, 9.8 MB) **arrived through the chat upload** (the 14.5 MB 25 Sep scan did
not). EXT pages 1-14 (Run Date 9/28/26 13:56:14; report page 8, SE23's total, missing) and CNV pages 15-25. **No FRM pages.**

- **Three-way check:** transcription (5 parallel readers) vs glyph reader vs printout arithmetic. 68 of 75 orders identical;
  every printed line total ties, and the Final Total (6,277,751 PCs / 22,103,174 LBs) equals all 75 orders.
- **First silent error of the glyph reader:** RP26925-1's new colour **BD** was read as **BL with no flag**. R7 decoded a
  colour as the nearest word of its 7-colour list, so a colour outside the list snapped silently. The crosscheck caught
  it. **Fixed:** `colour_word()` also reads every colour letter by letter and flags any difference (the comment in the
  R7 block already promised this). 28 Sep: BD, OF, NS rows now flagged; 25 Sep scan: identical values, same flag count.
- New colours: **OF = fade-resistant orange** (James, 28 Sep 2026: *"OF Fade-resistant orange"*), and **BD = dark blue**
  (*"BD Dark blue"*), both added to R7 and to `data/colour_codes.csv`.
- **FRM Draft (`daily/resolve.py`, new):** each scheduled order gets the formulation last issued for the same order on the
  same line; everything else goes to Exceptions with a suggestion that is never used automatically. Backtest on 25 Sep:
  **68 of 69 orders identical to Tech's issued FRM**; the one difference is the formula Tech changed that day (RP26923-1);
  the 2 new orders went to Exceptions. **28 Sep: 59 of 75 proposed, 16 exceptions** (new orders, 2 orders moved line:
  H68A127-1 SE25 → SE23, H68A080-1 SE42 → SE43, 5 new SE61 BA253 orders). Draft only; Tech signs.
- `build_xlsx.py` now skips the FRM workbook when a packet has no FRM pages.

## 7.23 Back to James's PC (28 Sep 2026)

James: *"please change it to local. I dont see much value in cloud right now"*. The cloud session stops here. Everything
is on GitHub, branch `claude/new-session-6wgvkd` (not yet merged into `main`). **Open items for the local session:**

1. **This document:** the repo copy (`docs/HANDOFF - Production Formulation Automation.md`, Rev 1.12) is newer than the
   one in the workspace folder (Rev 1.8). Copy it over the workspace copy (`HANDOFF` in `local_settings.json`).
2. **`local_settings.json`:** set `PUBLISH_DIR` to `...\General\Engineering Pipeline\Production Formulation` and add
   `DOCS_DIR` (see `local_settings.example.json`); then `pip install -r requirements.txt` in `.venv`.
3. **Publish 25 and 28 Sep** (EXT, CNV, FRM 25 Sep, FRM Draft 28 Sep) once James has seen the High issues: rebuild them
   locally (`PKT_DATE=... python daily/build_xlsx.py`, `python daily/resolve.py`), then `python publish.py ...`.
4. **Product Master merge** for 25 and 28 Sep (`PKT_DATE=... python daily/build_master.py`; it reads the published master
   in `Product Master\`, which the cloud session could not open in full).
5. **Scans:** 25 Sep is in `Production Formulation\Extrusion Schedule\`; 28 Sep is `doc05253620260928134035.pdf` in
   James's Downloads. Put both in `inputs\scans` to re-run the reader.
6. **Decisions waiting for James:** `docs/DATABASE.md` §6 (rename the calc-derived workbook, who approves, Material ID,
   variants); ~~H68A153-1 spec `OPOPOP` (R2)~~ accepted by James 28 Sep 2026 (Rev 1.13); FXA020WB4's WB-W40020M; RP26923-1's formula change; delete the old copies
   of the database workbooks from the workspace folder.
7. **Next build:** the three records (Formulation Report, Extrusion and Converting Production Records) from the 23, 24,
   25 and 28 Sep packets; then the Formulation Master (needs Tech's calc workbooks in `CALC_DIR`).

Cost note (James asked what uses the cloud credit): most of it was the parallel transcription readers (5–7 per packet,
~150k tokens each). Growing the glyph bank reduces how much of each page needs a second reader.

## 7.24 28 Sep FRM pages arrive; the FRM Draft is checked against them (28 Sep 2026, local)

James sent Tech's 28 Sep formulation pages as a separate scan, `doc05254620260928150919.pdf` (13 pages, SE11–SE61,
dated 9/28/26). They are transcribed into `data/packets/packet_2026-09-28.json` (`frm`, 53 formula rows) with a new key
`frm_source_scan`; `build_xlsx.py` names both scans in the Read Me. Transcribed from the page images only; the 25 Sep
packet was used afterwards just to pick cells to re-check at zoom (all new rows re-checked).

- **EXT vs FRM:** every one of the 75 scheduled orders is on its line's page. The 74 "Order has no formulation" Highs
  (they came from the missing pages) are gone; 28 Sep EXT now has 4 Highs (999-pallet cap ×2, CNV semi size ×2).
- **FRM Draft vs what Tech issued:** all 59 drafted orders identical (codes, materials, sets). Of the 16 exceptions,
  the 4 with a suggestion (RP26928-1; H69A290-3, H69A291-10, RP26826-3 by RUN WITH) got exactly the suggested formula.
  H68A080-1 kept FU0151KS3 on its new line (SE43) but the recipe differs from SE42 (virgin 77 vs 78, F1203K vs
  F1102K, KS 3 in V9 vs 2 in V8), which confirms a formula is per line. The history lookup is a sound first cut
  for resolve (docs/DATABASE.md §3 step 6).
- **New today:** FUA152BD4, FUA152OF4 ("New NPC orange color"), FUA011NS4 on SE21; FU0021GT4 for H68A127-1 on SE23
  (was FU001GTW4 on SE25); BF0000EB3 (Adsyl 5C30F) on SE61; F1102K on SE43 RP26911-2. H68A153-1 / FXA020WB4 is no
  longer on the pages, so the WB-W40020M question is moot for now.
- 25 Sep FRM issues still visible on today's pages were carried into `manual_issues_2026-09-28.py`.

## 7.25 25 and 28 Sep published; Product Master merged (28 Sep 2026, local)

James: *"yes"* (publish both days, merge the Product Master, push). §7.23 items 3 and 4 are done.

- **Published** (`publish.py`, verified by content, `data/published_manifest.json`; §11): EXT, CNV, FRM Formulation
  Report for 25 Sep and 28 Sep. The FRM Draft 2026-09-28 was not published: Tech's FRM replaces it.
- **Product Master:** merged 25 Sep (51 products changed: 50 Formula Last Run, DPP40WB1670 and SPA40WB953 filled
  from the packet, the latter with spec `OPOPOP`), published, then 28 Sep merged into that (1 new product
  RBP30EB22; 8 filled, including RPA40BD59; 50 Formula Last Run), published. 2,087 products.
- **Transcription fix before publishing:** six 25 Sep CNV rows (SD22, scan p22) had `\"` in `row_notes` (`12\" 9 Slot`),
  a quote escaped twice during transcription; not on the paper. It made Marking show twice on 5 products. Fixed in
  `packet_2026-09-25.json` (the 24 and 28 Sep packets print the same notes without it). 25 Sep was not yet published.
- **Code fix:** `build_master.py` rebuilds the Check column every run, and `calc …` notes only come from
  `CALC_JSON`. Without Tech's calc workbooks on this PC the two calc notes (`calc Thk 4.3` RPA40WB3142,
  `calc GSM 1003` RPP40KS2136) would have been dropped; the merge now keeps the prior master's `calc …` notes when
  no calc data is loaded.

## 7.26 The three history records built (28 Sep 2026, local)

James: *"the three history records (Formulation Report, Extrusion and Converting Production Records) from the four
packets. build them"*. New `daily/record.py <date> ...` writes them from `data/packets/`, columns taken by name from
`db/schema.py`. Built for 23, 24, 25 and 28 Sep and **published** (James: *"yes"*; verified by content, §11). A re-run on the published copies skipped all four dates as identical.

| Record | Rows | Per day | One row per |
|---|---|---|---|
| Formulation Report Record (`Daily Formulation Report\`) | 1,656 | 429 / 415 / 376 / 436 | issue date × line × order × formula row × feeder |
| Extrusion Production Record (`Extrusion Schedule\`) | 308 | 82 / 80 / 71 / 75 | schedule date × line × order |
| Converting Production Record (`Converting Schedule\`) | 270 | 70 / 69 / 69 / 62 | schedule date × converting line × order × row |

- **Append-only, enforced:** each run starts from the published record (read and recorded). A date already in it is
  skipped if the rows are identical and **stops the run** (nothing written) if they differ. Test
  `test_records_append_only`.
- **Schema additions** (`db/schema.py`, `docs/DATABASE_TABLES.md` regenerated): `Formula Row` in the Formulation
  Report Record key (FUA060WBA is printed twice for the same orders with different sets), plus `Note` and
  `Source Scan`; `Handwritten` and `Source Scan` on the EXT and CNV records.
- **Values as printed.** `Plts Ordered` keeps the printed 999 (the field caps there; about 16 orders a day) with any
  hand correction in `Handwritten`. CNV overflow totals stay `######`. `Plts Done (EXT)` is read from "NNN PLTS DONE".
  CNV `X OF Y` parsed on all 270 rows.
- **Weight %** only on weight lines (SE24, SE42, SE43, SE61): Set, and the balance to 100 for `Auto`; all 190
  extruder groups add to 100. Blank on auger lines. `Variant` uses the FRM Draft's rules (`resolve.variant`).
- **H69A139-1 (25 Sep):** on the FRM page but not on that day's EXT, so its product code is taken from the 24 Sep EXT
  (DPP40KS303) and the row's `Source Scan` says so.
- `Material ID` blank until the Materials table exists; `Signed By/At` blank (these are Tech's pages as transcribed).
- `resolve.py`: the `PKT_DATE` check moved into `main()` so `record.py` can reuse `variant()` / `split_feeder()`.
- Daily run (CLAUDE.md step 7): after publishing the day, `python daily/record.py <date>` and publish the three records.

## 7.27 Decisions, the Draft Formulation Master and change control (28 Sep 2026, local)

James asked how to maintain the formulation long term: *"is it through direct excel update in share point? or i should
update it through claude?"*. Answer agreed (*"Yes to all. lets build it this way"*): **the master is Excel in
SharePoint; Tech/James edit it there; every edit gets an approved Change Log row; the pipeline checks every run and
stops on any change without one. Claude is for heavy changes** (new line, new slopes, bulk calc updates, reports).
DATABASE.md §6 (decisions) and §7 (maintenance) record it.

- **Decisions:** calc workbook renamed `Formulation Calc Library.xlsx` (published to `Formulation Data Base\`, same
  content as the old file); approval = Tech for formulas/slopes, James for rules; Material ID = IWPFT062 Material No.;
  variants as listed. RP26923-1: no action (history is in the Formulation Report Record). Old workspace copies
  (`Product Master.xlsx`, `Daily6\`, old `Formulation Master.xlsx`) verified identical to the published or
  superseded files; **deleting them was blocked by Claude Code's permission check, so James deletes them.**
- **IWPFT062 is at Rev 17.0** (14 Sep 2026; Rev 16.0 = Kevin Sung's vendor revision of 9 Sep, see
  `ISO and Process Management\IWPFT062 Rev 16 - vendor list revision.md`). Read only.
- **`Formulation Master.xlsx` seeded as Draft and published** (`db/seed_master.py`, one time): 73 Materials (every
  IWPFT062 row + Q1203K withdrawn + `INT-` plant reclaims/premix + `NL-` not-listed), 46 Formulas, 275 Line Settings
  (as printed), 107 Product to Formula, 72 Recipe rows (weight lines only; auger recipes need Tech's slopes),
  Standing Notes. Drop-down lists on every coded column; workbook structure locked (no password).
- **What IWPFT062 settles / raises** (master Issues sheet):
  - FXA020WB4's WB-W40020M = CR480WB Blue white, **approved** (closes that question); PE-W22151 = CR415WB.
  - **High:** Q1203K withdrawn at Rev 16.0 but printed on SE42 every packet; F1102K (PH401) In-active but in
    FUA151WB3 (SE43, 28 Sep); PP Yungsox 5050S (SE61) and Heritage HM-10HP (SE24/SE25) not on the list.
  - FU0151KS3 has different weight % on SE42 (25 Sep) and SE43 (28 Sep): the recipe may be per line, not per code.
- **Change control:** `db/preflight.py check|accept` compares the published master with the accepted version in
  `data/snapshots/` (git). Baseline accepted after publishing. Test `test_master_change_control`. Daily run step 0.

## 7.28 Interface design started as a claude.ai Artifact (28 Sep 2026)

James: *"also start designing the UI as well for Artifacts"*. First design published (private):
**https://claude.ai/artifact/1kSFUwuS1GUeiG13twAw5j** (*Profile Formulation*). A **design prototype on a snapshot** of
the 28 Sep files, not live and not editable. Source: `ui/page.template.html`, data from `ui/build.py`.

- **Line board:** the 13 lines in plant order, each line's formulation drawn as its feeder layout (hoppers H1-H5 with
  a 0-100 speed gauge on auger lines; per-extruder weight % bars on weight lines, Auto shown as the balance). Material
  tiles carry the IWPFT062 number and flag Withdrawn / In-active / Not listed.
- **Look up:** order, product or formula code across all packets.
- **Master health:** the master's Issues, and the Excel + Change Log + pre-flight flow.
- **Daily run:** the steps from scan to records; a scan drop zone that is **not connected**.
- **Next design decisions** (for James): who uses it (Tech on the floor, engineers, managers); whether the page reads
  the live SharePoint files (Microsoft 365 connector) or a snapshot published after each run; whether Tech signs the
  draft on the page (needs the `db` and `user` capabilities: a sign-off record per day).

## 7.29 First master change through the Change Log: HM-10HP = CA410 (29 Sep 2026)

James pointed to IWPFT062 *"50-7002-034 CA410 CaCO3 / HM10 MAX Heritage Active"* and *"thats the CACO3"*, and chose
"Same material as CA410" for the FRM's "Heritage HM-10HP". Applied the way every master change goes (§7.27): the
published master was copied to `out/`, edited, and **Changes 1-7** logged (Requested/Approved By James Kuo):
Line Settings SE24 FSA200WB4 A V3 and SE25 FU0011WB5 VOIDFORM Hopper 3 -> 50-7002-034; the Recipe row re-keyed
(removed + added); CA410 gains the spelling; `NL-HM-10HP` retired (kept, not deleted). Published; pre-flight matched
all 7 to approved rows; accepted (`data/snapshots/`). The High issue is now Info. `db/seed_master.py` MAP updated to
agree. Interface republished. Three High material issues remain: Q1203K, F1102K, PP Yungsox 5050S.

Note: IWPFT062 could not be read on 29 Sep (permission denied: open in Word or syncing); the change did not need it.
`test_master_change_control` skips while it is locked.

## 7.30 Q1203K replaced by F1203K (29 Sep 2026)

James: *"yes. Q1203K is replaced by F1203K"*. Master **Changes 8-12** (approved by James Kuo) through the new reusable
`db/replace_material.py OLD NEW --by --why`: SE42 FU0021WB4 V3 Material ID 50-3963-301 -> 50-3963-019 (F1203K,
PH1203); the Recipe row re-keyed; Q1203K retired with "Replaced by 50-3963-019". Published, pre-flight matched all 5,
accepted. The issue stays open as **Medium** until Tech corrects the SE42 FRM page (it still prints Q1203K).
High material issues left: F1102K (In-active, SE43 FUA151WB3) and PP Yungsox 5050S (SE61, not on IWPFT062).

## 7.31 Foam agent spelling and White Reclaim (29 Sep 2026)

Two more master changes, each logged and approved by James Kuo, published, matched by pre-flight and accepted:
- **CF400 is X0-256 (digit zero)**. James: *"yes please correct that"*, *"should be X0"*. **Changes 13-14** via the new
  `db/edit_master.py` (logged cell edits): CF400's FRM Text -> "FOAM – Bergen X0-256"; the page's "XO-256" kept under
  Other Spellings so today's pages still map. Issue stays Low until Tech corrects the SE24 page.
- **White Reclaim = PP WB Reclaim**. James: *"yes same as PP WB Reclaim"*. **Changes 15-20** via
  `db/replace_material.py INT-RCL-WHITE INT-RCL-PP-WB`: SE42 FU0021WB4 V7 and its Recipe row now PP WB Reclaim;
  "White Reclaim" added as a spelling; INT-RCL-WHITE retired.

`db/seed_master.py` MAP agrees with the master. Change Log now holds Changes 1-20.

## 7.32 "PP Virgin" is F6502A (29 Sep 2026)

James: *"PP Virgin is F6502A"*. **Changes 21-23** (approved by James Kuo) via `db/edit_master.py`: SE23 FU0021WB4 corn
box and its reclaim run-out row, Hopper 1, Material ID -> 50-1560-050 (PC416 F6502A); "PP Virgin" added to F6502A's
spellings. Published, pre-flight matched all 3, accepted. The master now passes `db/schema.py check` with **0 problems**.

Master issues still open for Tech: **High** F1102K In-active (SE43 FUA151WB3) and PP Yungsox 5050S not on IWPFT062
(SE61); **Medium** SE42 page still prints Q1203K, KS alternate sources not on IWPFT062, FU0151KS3 weight % differs on
SE42 vs SE43; **Low** SE24 page prints XO-256, BL-B26003A and "HiTalc ZS" names not on IWPFT062.

## 7.33 IWPFT062 Rev 18.0 adds PP YungSox 5050S (29 Sep 2026)

James revised IWPFT062: *"Doc T062 revised. Take a look and update accordingly for 5050S"*. Read (read only): **Rev 18.0,
9.29.2026, James Kuo, "Add PP YungSox to the list"**; new row **50-1560-163 | PC5050 | Formosa PP YungSox 5050S |
Formosa | Active**. The Rev 18.0 row's MOC cell is blank (every earlier row has NA or an MOC number).

Master **Changes 24-44** (approved by James Kuo) via `db/replace_material.py ... --create` (new option: adds the material
row first, logged as "(new row)"): Materials gains 50-1560-163; SE61 extruders B and D on BF0000EB5, BF0000EBA and
BF0000KSA (6 Line Settings) move to it; 6 Recipe rows re-keyed; NL-YUNGSOX-5050S retired. Published, pre-flight
matched all 21, accepted; schema check 0 problems. The High issue is now Info.

**One High material issue left:** F1102K (PH401) is In-active on IWPFT062 yet in FUA151WB3 (SE43, RP26911-2).

## 7.34 Q1203K closed; daily checks read known substitutions (29 Sep 2026)

James: *"Correct this for me. Q1203K is replaced by F1203K"* and *"take it off the Open items list"*. The master already
carried F1203K (Changes 8-12); the printed SE42 page comes from Tech's formula book, which the pipeline does not edit.
So: the master's Issues row is now **Info, resolved**; the item is off the interface's Open items list (kept under
`resolved` in `ui/open_items.json`); and `daily/checks.py` gains `REPLACED` (printed text -> what it is now, and
James's decision): a page that still prints **Q1203K** or **Bergen XO-256** gets one **Info** row ("read as F1203K /
X0-256"), so the hand-written Medium no longer has to be carried from day to day. Regression counts +2 on 23 and 24
Sep (exactly those two Info rows). Add to `REPLACED` only on James's word, with the master change it refers to.

## 7.35 HiTalc ZS recorded as TL460's trade name (29 Sep 2026)

James asked why the "HiTalc ZS" item was still Low when the mapping already worked: the data was right (every
"HiTalc ZS (or N40109A)" row carries TL460, Active), only the name was missing from IWPFT062. James chose to record it
in the master rather than revise IWPFT062 (*"go with 1"*): **Change 45**, TL460 Other Spellings = "HiTalc ZS",
approved by James; issue now Info; off Open items. Interface: issue lists sort High -> Medium -> Low -> Info; Open
items opens by severity (switch to "By owner").

## 7.36 IWPFT062 is the authority; the master follows it (29 Sep 2026)

James: *"doc T062 is correct. Master should match it"*. New `db/sync_iwpft062.py` compares every IWPFT062 row with the
master's Materials (Material No., code, name, supplier, status, further approved sources) and, with `--apply`, makes the
master match through Change Log rows under this standing rule; a row dropped from IWPFT062 becomes "Withdrawn", never
deleted. Master-only columns (Role, FRM Text, Other Spellings) and INT-/NL- rows are left alone, so Change 45
("HiTalc ZS" as a spelling of TL460) stands: TL460's Name stays IWPFT062's "Talc / N40109A". Daily run step 0 now runs it.

IWPFT062 was locked (open in Word) on 29 Sep, so the live check could not run; a preview against the Rev 18.0 text read
at 09:43 (file unchanged since) found **0 differences** across 67 rows. Run the live check once the file is closed.

## 7.37 XO-256 disregarded (29 Sep 2026)

James: *"disregard this issue. Unless you have more XO then change them to X0"*. The master had one XO left: CF400's
Other Spellings "FOAM – Bergen XO-256" (added in Change 14 so the misprint mapped). **Change 46** clears it (the FRM
Text is already X0-256); the Change Log's history rows keep their text. Issue closed (Info, "Disregarded by James"),
off Open items; the daily checks no longer note XO-256 (`checks.REPLACED` keeps Q1203K only; regression counts 83 / 72).
The code map in `db/seed_master.py` still links a printed XO-256 to CF400 but raises nothing.

## 7.38 F1102K replaced by F1203K (29 Sep 2026)

James looked at the 28 Sep SE43 page (scan p12: RP26911-2 FUA151WB3 V7 F1102K 15) and decided: *"F1102k is obsolete
and replaced by F1203K by formosa. Change all 1102 to 1203 and close out the issue"*. **Changes 47-52** (approved by
James) via `db/replace_material.py`: Line Settings SE43 FUA151WB3 V7 and SE42 FU0151KS3 V7 -> 50-3963-019; FUA151WB3's
Recipe row re-keyed; FU0151KS3's F1102K Recipe row removed (the seed had already added F1203K 15 from SE43, the same %);
F1102K's master Status Retired. Its IWPFT062 row (PH401, In-active) and Approved Substitutes are untouched: IWPFT062
owns those (§7.36). `replace_material.py` now (a) drops the old Recipe row when the new material is already there at the
same %, stopping if it differs, and (b) leaves Approved Substitutes alone on IWPFT062 rows. `checks.REPLACED` gains
F1102K (every packet prints it: Info note; regression counts 84 / 73). **No High material issue is left.**

## 7.39 One code, several recipes: reclaim first (29 Sep 2026)

James: *"Some product can use reclaim as well as virgin resin. Whenever we have product like this, we will display both
or more formulation so if we have reclaim in the silo, we will use it up first before going to virgin resin."*

- `daily/checks.py`: "Same formula code, different recipes on one line" is now **Info** ("One code, several recipes
  (reclaim first / variants)") when each recipe is told apart by its reclaim content or a noted variant (run-out,
  VOIDFORM, sign blank, corn box, roll); it stays **Medium** only when neither explains the difference. On all four
  packets every case is explained (e.g. SE22 FUA060WBA reclaim 90; reclaim 75; SE23 FU0021WB4 VOIDFORM; corn box;
  run-out). Issue counts unchanged (severity only).
- The published 25 / 28 Sep workbooks keep their Medium rows as issued; the manual "two formulas with no note" rows are
  not carried forward (CLAUDE.md step 3). DATABASE.md §6.4 records the rule; off Open items.

## 7.40 Customer-specific formulas get their own codes; every formulation is always given (29 Sep 2026)

James: *"Some formula code as customer specific. which the past engineer add it into the notes like "void from" or sign
blank"*; *"We should use this oppotunity to fix their mistake and create new fomulation code instead"*; *"put all
customer specific list on the side and let me think so we can name these"*.

- **Parked, nothing renamed:** `ui/customer_formulas.py` -> `ui/customer_formulas.json`, shown on the interface's
  *Customer formulas* tab: 12 formulas (VOIDFORM x4: FU0022WB3 SE11, FU0001WBD SE22, FU0021WB4 SE23, FU0011WB5 SE25;
  sign blank: FUA152WB4 on SE12/SE13/SE31/SE32; corn box FU0021WB4 SE23 and its run-out row; roll FU0021WB4 / FU0001WB4
  SE25), with products, settings, whether the same code is also printed plainly on that line, and the sequence numbers
  already taken in each code family (Calc Library + FRM codes).
- **IWPFT057 vs practice:** IWPFT057 Rev 4.0 describes a 7-digit monoextrusion code; 222 of 236 codes in use have 9
  characters: [base][requirement][blend][sequence, 3 digits][colour, 2][thickness, 1] (FUA152WB4 = F U A 152 WB 4 mm).
  New codes should follow the 9-character form, with IWPFT057 revised to match (James's document). 14 codes fit neither.
- James: *"for the reclaim to vigin, when the material is requested, make sure you provide both formulation"*. The FRM
  Draft already copied every formula of the order in the listed order; now a rule in CLAUDE.md and a test
  (`test_draft_keeps_every_formulation`: all 59 drafted orders match their last issue exactly, incl. the multi-formula ones).

## 7.41 Interface for operators and the production manager; # Plt 999 confirmed (29 Sep 2026)

James: *"its for extrusion production operator and production manager"*. The interface now opens on two views:
- **Operator:** pick a line (large buttons), then today's orders in schedule order. Each order shows product, colour,
  thickness, size, GSM, pallets, die and the special instructions (weight ranges, VOIDFORM, corn box highlighted), then
  **every formulation**, labelled "Run first · uses reclaim" / "Next · less reclaim" / "If PP WB Reclaim runs out",
  with large set values (auger: speed 0-100; weight: %, Auto shown as its balance). Where the page prints a replaced
  material (Q1203K, F1102K) it shows what to load. An order with no formulation says "Ask Tech before starting".
- **Production manager:** every line: dosing, orders, pallets, weight, formulas in use, and what needs attention;
  a row opens that line's operator view.
- The engineering tabs (Open items, Line board, Look up, Master health, Daily run, Customer formulas) sit behind them.

**# Plt 999:** James confirmed the AS400 caps # Plt at 999 (*"correct"*). `daily/checks.py` now reports it as **Info**
with the real count (sheets / (pcs x stacks)); the operator and manager views show the real count ("AS400 prints
999"); the records keep the printed 999 and the hand correction (values as printed). Open: live SharePoint data vs a
copy after each run, and Tech sign-off on the page.

## 7.42 The print-ready Word formulation for the floor (29 Sep 2026)

James: *"operator will use the paper copy. So whenever i or any other engineer scan you the production schedule. you
will product a word formulation document for us to print out"*; *"you can use the current one (and maybe improve a
little) as template"*. Tech's per-line Word formula books are not synced to this PC, so the template is the FRM page
as scanned. Read (read only) **IWPFO055** Formulation and Instruction Issue Procedure (§5.3 Technical issues the
formulation; §5.4 copy in the "Schedule" binder; records under IWPFO112) and **IWPFT018** Formulation System.

New `daily/render_frm.py` (python-docx; `requirements.txt`) -> `FRM Formulation <date>.docx`, routed to
`Daily Formulation Report\` (`db/schema.py`, `publish.py` daily guard). US Letter landscape, Times New Roman like
Tech's page:
- **Cover:** status (DRAFT while any order has no formulation, else READY TO ISSUE), how to read the pages, the orders
  an engineer must complete (with the reason and the draft's suggestion, marked "not used"), and the **issue block**
  (Issued by (Technical), signature, date/time, copy in Schedule binder, per IWPFO055 §5.3-5.5).
- **One page per line**, as Tech's: "Line N (SExx) Formulations", AC and date, Order # | Formula Code | feeders | Note,
  the line's footnotes, "Tech. Department / Effective Date". Improvements: a line saying what Set means on that line;
  the product under each order; every formulation of an order with "Run first / Next / If reclaim runs out";
  replaced materials printed as what to load ("F1203K (replaces Q1203K)"); James's naming decisions printed
  (X0-256, "PP Virgin (F6502A)", "PP WB Reclaim (White Reclaim)"); weight-line Auto shown with its balance; an order
  without a formulation gets one wide shaded row "ENGINEER TO COMPLETE" to write in, never a suggestion.
- Rendered for 28 Sep from the draft (75 orders, 16 for an engineer) and checked page by page through Word's own PDF
  export. Test `test_print_formulation_docx`. Not published (28 Sep already has Tech's issued FRM).
- **Next:** a way to record an engineer's decision for an Exception (e.g. "use the suggestion" / "same as order X")
  so the re-render fills it in; today the engineer writes it on the printed row.

## 7.43 Engineer completes an Exception in the database; the re-run fills it (29 Sep 2026)

James: *"yes this allow the engineer to update the data base and trigger a re run"*. Built the loop:
- `daily/resolve.py`: after "last issued for this order on this line", it now looks up **approved** Product to Formula
  rows in the Formulation Master (with that line's Line Settings), in run order (Primary, then more reclaim before
  less, run-out last). Draft rows are never used. The master is pre-flighted first (unlogged edit: STOP; no accepted
  version: not used). Such rows show How Resolved "Product to Formula", source "Formulation Master, approved by ...".
- New `db/assign_formula.py`: records the engineer's decision (product, line, formulas in run order), approving
  existing Draft rows or adding new ones, each logged in the Change Log; stops if a formula has no settings on that line.
- Test `test_engineer_decision_fills_the_rerun` (on a copy of the published master): RP26928-1 is an Exception until
  RPAA0WB318 on SE22 is approved for FUA060WBA / FUA060WBA / FUA010WBA; the re-run then fills it with all three in order.
- CLAUDE.md "Print formulation for the floor" step 4 describes the loop.

## 7.44 First end-to-end daily run from a schedule-only scan (29 Sep 2026)

James: *"today schedule. Lets do a test. Using this, run it through the process. It should follow checking product
master (if missing update product master), checking formulation, then check auger calibration, create daily
formulation, update formulation record, extrusion record and converting record"*. Scan doc05261220260929142225.pdf,
26 pages: EXT 15 (report pages 1-8, 10, 12-15, plus SE25 and SE61 printed as separate one-page reports), CNV 11, no
FRM pages.
- **Transcribed** to `data/packets/packet_2026-09-29.json`: 76 EXT orders, 62 CNV rows. All 12 printed line totals
  equal their rows; SE23's total is on the missing report page 9 (handwritten 3,939,487# = its page weights).
- **Glyph reader**: Tesseract was not installed on James's PC; James: *"do it"*. Installed Tesseract 5.4.0 (winget
  UB-Mannheim.TesseractOCR, `C:\Program Files\Tesseract-OCR`). 5.4 reads the 'Prod' header as 'ROD' on pages 1, 5, 9, so
  the reader found no columns there; `ext_scan_reader.anchors` now fixes the columns from any three header words (Prod
  or Weight among them). Test `test_reader_header_anchor_survives_rod`. Crosscheck: 67 of 76 orders identical; the rest
  settled by eye at 600 dpi for the transcription: H67A164-2 is RF (reader: OF; the letter matches the R of R1R1R1),
  the SE61 page (reader misreads specs and GSM there, as before) and the handwriting over H68A080-1. No packet change.
- **New today**: SE21 H69A203-1 RPP50BL1501, H67A164-1 RPP63KS1, H67A164-2 RPP63RF1 (colour **RF**, not seen before;
  asked James); SE24 RP26604-1 SPA40WB755 (handwritten "Run with RPA40WB3051"). Gone: H69A290-3, H69A291-10, H68A111-4.
- **Product Master**: 0 missing; the three new SE21 products were known only from Tech's calc workbooks and now carry
  the EXT fields. RPP63RF1 Thk: calc 6 vs printed 6.3 (flagged in Check). Published.
  Fixed on the way: `daily/build_master.py` line 284 had a straight apostrophe in a quoted string (from the Calc Library
  rename in 15ca587) and did not compile.
- **Formulation**: the Formulation Master was open in James's Excel (file locked) and the run waited for it; the
  pre-flight then showed 0 changes since the accepted version. IWPFT062 sync: 0 differences. `resolve.py`: 72 of 76
  orders from the last issued FRM (28 Sep); 4 Exceptions = the four new orders. Calc-workbook hints for the engineer
  (not used): RPP50BL1501 FU0011BL5 / FUA011BL5; RPP63KS1 RU0000KS4; RPP63RF1 FU0000RF6.
- **Auger calibration**: no Auger Calibration master yet (Tech's calc workbooks not in `inputs/calc`). New
  `daily/auger_check.py` checks each auger-line hopper setting in the FRM Draft against `auger_rules.RULES` (draft Q13):
  144 settings / 38 formulas, 0 outside the rules (28 Sep: 124 / 34, 0). Slopes not checked.
- **Daily formulation**: `out/FRM Formulation 2026-09-29.docx`, 15 pages, DRAFT (4 orders for an engineer). Not
  published: only the issued copy goes to Daily Formulation Report.
- **checks.py**: on a packet with no FRM pages the "Order has no formulation" check flagged all 74 orders High; it now
  adds one Info instead and skips the per-order comparison.
- **Records**: Extrusion (+76) and Converting (+62) appended and published. Formulation Report Record: nothing appended
  (no issued formulation yet); today's rows follow when the document is issued (CLAUDE.md step 5).

## 7.45 Tech's 29 Sep FRM reviewed and loaded; interface copy decided (29 Sep 2026)

James sent Tech's FRM pages (doc05261320260929142259.pdf, 13 pages): *"excellent. I didnt see any mistake. Here are the
missing data. Review to see if there is anything wrong. also update your data base with it"*.
- **Transcribed** into `packet_2026-09-29.json` (`frm`, `frm_source_scan`); all 76 scheduled orders are on the pages.
- **Draft vs Tech**: the pipeline's draft (made before the pages came) equals Tech's issue field for field on 71 of 72
  proposed orders. RP26810-1 differs: Tech added a second formula FU0041KS4 (PP Mix Reclaim 70). The 4 Exceptions are
  the 4 new orders; Tech wrote FU0012BL5 (H69A203-1), FU0001RF6 (H67A164-2), FU0070KS6 (H67A164-1) and grouped
  RP26604-1 on SE24 FUA152WB4 (as the handwritten "Run with RPA40WB3051" said).
- **Review findings** (manual issues and interface Open items): H69A203-1 FU0012BL5 prints "PP Virgin-silo 3 (DOW-C104)"
  (not on IWPFT062; nearest PC104 = TI4015F Braskem; asked James), F1102K on a new formula (read as F1203K), and
  "CaCO3 -Heritage HM-10HP (BayShore BI-113)" (BayShore not on IWPFT062); RP26810-1 lists the virgin formula before the
  reclaim one with no note (asked James which runs first). RF = red: IWPFT062 50-7002-601 CR400RF "Red / R26006A".
  A pen loop on the SE11 page: James, *"disregard the loop. someone had a question so i circle it while explaining"*.
  Auger hopper rules: 180 settings on Tech's auger-line pages, none outside them.
- **Database updated**: FRM Formulation Report 2026-09-29, EXT/CNV (issue lists), Product Master (formula codes, now most
  recent first as its header says; `daily/build_master.py` fixed) published; Formulation Report Record +441 rows.
  Formulation Master: Materials spellings (Changes 53-55: RF-R26006A, "BL-B26003A (or NPC-B60387)", the BayShore CaCO3
  text) and new `db/import_frm.py` (Changes 56-82: 4 formulas, 18 line settings, 5 product-to-formula rows, all Draft).
  FU0012BL5 Hopper 1 (DOW-C104, 63) is NOT in the master until James names the resin. Test
  `test_import_frm_adds_only_what_is_missing`.
- **Interface (§7.28)**: James, *"lets keep a copy create a separate folder in the fomulation record for now to hold these
  file. No Tech sign off require"*. `ui/build.py` now reads the published, pre-flighted master and records (no longer
  out/ or typed-in figures), computes draft-vs-Tech from the day's FRM Draft, and writes `Profile Formulation <date>.html`,
  published to **Daily Formulation Report/Interface Copy** (new `schema.Book`, daily, kept as issued). The "Tech signs"
  step is off the page. Artifact republished (version 16).

## 7.46 The interface reads a schedule scan and downloads the Word formulation (29 Sep 2026)

James: *"let me put the same production file in the artifact. see if it generate the right formulation"*; the page could
not send images to Claude on his account (claude.ai in Chrome and the app); James: *"i prefer chrome. Since i want to
share this in the future with other engineer"*, then *"run a load test using chrome with PDF file. and make sure you
receive the word by via download"*.
- **Reader in the page** (Daily run tab): Claude reads the page images where the viewer allows it; otherwise Tesseract
  5 runs inside the page (tesseract.js-core 5.1.1 from jsDelivr; English *fast* model shipped with the artifact as
  `eng-data.js`, because an artifact page may load CDN scripts but cannot fetch data). A copier PDF is one JPEG per page:
  the page takes the JPEGs straight out of the file (pdf.js stalled drawing these scans in an artifact frame).
- **How a row is read** (tuned against the 28 and 29 Sep transcriptions; harness `ui/ocr_eval.py`, `evaluate11`): left
  strip of each page, grey, Lanczos 2x; line code from the title strip; the whole strip in one pass plus each printed
  order row (found from ink in the Mfg#/Ord# column) with up to four settings; a reading is taken only when it matches an
  order + product already on a schedule (look-alike characters: 0/O, 1/I/T, 4/A, 5/S, 8/B ...). New orders are boxed
  "check the number"; rows it cannot read are shown as pictures to type in; every printed row must be explained.
  Result: 29 Sep 71/76 right, 28 Sep 64/75 right, **no wrong order taken and no row missed without a flag** on either day.
- **Chrome test** (Claude in Chrome, the page served from 127.0.0.1 because the artifact frame blocks automated uploads):
  the 29 Sep PDF (26 pages, 9.9 MB) read in 86 s; 15 extrusion pages found with the right line codes, 11 CNV pages
  skipped; 71 rows matched, 4 boxed, 3 pictures (2 orders under handwriting, the SE25 "Final Total"). After typing
  those in: 76/76 as transcribed, 72 with a formulation, 71 the same as Tech (RP26810-1: Tech added FU0041KS4), 4 for
  an engineer.
- **Word download**: the page builds `FRM Formulation <date>.docx` itself (docx 8.5.0 from jsDelivr), the layout of
  `daily/render_frm.py`, and saves it through the artifact's `downloads` capability (declared). The file the page built
  in Chrome opened in Word: 15 pages, same pages as the pipeline's. Chrome would not save a download started by the
  automation (not even a test .txt), so James has not yet had the file through the Save prompt: first real use is his.
- Interface copy republished; artifact version 22.

## 7.47 Always the latest formulation, even for a past schedule (30 Sep 2026)

James, on the 29 Sep test that left the four new orders blank: *"ok dont do that in the future. Always provide up to date
formulation. even if someone give you an past schedule. If someone need an revision, they will put in an old schedule
(usually previous day or if weekend, friday schedule)"*. Before, `resolve.py` and the interface looked only at FRMs issued
**before** the schedule's date (a blind backtest). Now both use every issue on file, the latest winning. The 29 Sep
schedule now resolves 76/76 (H69A203-1 FU0012BL5, H67A164-2 FU0001RF6, H67A164-1 FU0070KS6, RP26604-1 FUA152WB4), 0 for
an engineer. `HISTORY_BEFORE=<date>` keeps the old view for the backtests only (`test_resolve.py`, the 28 Sep tests).
New test `test_past_schedule_gets_the_latest_formulation`. Interface republished (version 23).

## 7.48 Scan reader and product codes made hard rules (30 Sep 2026)

James found two misreads in the page's Word document: H69A203-1 read as **H69A203-17** (the printed bar after the suffix
read as a 7) and RP26826-3's product printed as **RPAQWRAN72**. James: *"OCR check process needs to improve"*, *"make sure
all these improvement are code in so we dont make the same mistake again"*, *"make sure these mistake does not make it
into Product master"*, then the code rules (*"10 means 1mm and 90 means 9mm. A0 is 10mm and B0 is 11mm"*, *"AQ is
incorrect from the start"*, *"the color code is WB. WR dont exist"*, *"after that is just number for the product. No
english characters"*, *"these need to be hard rule. If anything odd is spotted, recheck the OCR again"*, *"DPPAOKS27 is A0
instead of AO"*).
- **`product_code.py`** (new): the product-code rule (family, thickness, colour, number; families and colours in use),
  `thickness_mm`, `problems`, `repair` (letters where letters belong, digits where digits belong, a listed colour).
- **Product Master**: `build_master.py` refuses a code breaking the rule and repairs only letter O for zero: DPPAOKS27 ->
  DPPA0KS27 (formula kept), RBPAOKS14/37/40 merged into RBPA0KS14/37/40 (all four came from Tech's calc workbooks; Rev 1.5
  had already confirmed they are A0). 2,087 -> 2,084 products, none breaking the rule; published.
- **Daily checks**: a packet product code breaking the rule is High; code thickness vs the Thk column is Medium.
- **Interface reader** (mirrors `ui/ocr_eval.py` `read_page15`): each order row is cut into cells at the printed bars
  (found by their spacing, so a page shifted on the copier glass works); each cell is read with up to four settings; a
  row is taken only when it matches an order + product on file by look-alike characters only (8 vs 9 is not a
  look-alike: 28 Sep H69A038-1 was wrongly matched to H69A039-1 before); a new order is boxed; anything odd is boxed with
  its picture, what was read and the closest order on file. The Word download is locked while a row is boxed; a
  correction must keep the rules. Result on the scans, history before the day only: 29 Sep 66 taken / 0 wrong / 10
  boxed; 28 Sep 54 / 0 / 21; every printed row shown. Chrome test (29 Sep on file): 76 rows, 69 taken, 7 boxed with the
  right hints, a wrong correction stayed boxed, the right ones unlocked the download; the Word file holds exactly the 76
  scheduled orders and 53 real products.
- Tests `tests/test_product_code.py` (rules in Python and in the page's JavaScript) and `tests/test_scan_reader_page.py`
  (real scans, `OCR_TESTS=1`).

## 7.49 Two readers, border lines, handwriting ignored: every scan on file read right (30 Sep 2026)

James, after more boxed rows (HSA0S-1, H67A164-1, RP25818-2, RP26512-1, H68A080-1 under a handwritten note): *"the
production sheet always have boarder lines to divide up data. Use it to isolate data"*, *"ignore hand writing. thats just
notes from production team"*, *"repeat the test with SEP 29 production until you can produce identical product"*, *"use
this opportunity to check every scan file you currently have. see if anything else is missed"*.
- **Border lines isolate the printed row** (`isolate_row`): a row band holding one of the sheet's solid border lines with
  ink on both sides is cut along the line, column by column (a page tilted on the glass still cuts cleanly), and only the
  side holding the printed '|' bars is read; notes written above a block's top border are whited out. 29 Sep p14:
  H68A080-1 / CPP30KS215 under "-PA205" now reads by both readers.
- **Cells**: ruled lines and edge bars erased, the text-height part kept, binarized; the characters after the dash are
  counted on the image, so a bar can never become a suffix digit (H69A203-17).
- **Two independent readers per cell**: Tesseract on the cleaned cell (up to four settings) and the plant's glyph bank
  (`scan_reader/glyph_bank.npz`, nearest printed character; order decoded by position rules, product = nearest Product
  Master code of the same length). A 1-px ruling scrap is no longer a character (29 Sep SPA40WM8 had been read as a
  9-character code; Tesseract alone read WM5, which is also a real code). A row is **taken** only when an order +
  product on file matches (any reader) or **both readers agree on both values**; otherwise it is boxed.
- **Line code**: a known line read two independent ways (page header word, "LINE NO. SExx Total" footer, glyph bank on
  the header), with no reading disagreeing; a line word must be S, E and two characters (nothing missing is guessed).
  A line's pages run on until its footer, so a page without a footer takes its next page's line when its own header says
  the same (28 Sep p3: header SE13, glyph unsure SE12/SE13 by 0.03, p4 certain SE13 with footer). Otherwise every row of
  the page is boxed, with a Line box to correct.
- **The page runs the same reader**: `ui/reader.js` (inlined by `ui/build.py`), glyph bank shipped as `glyph-bank.js`
  (quantized int8, 1.65 MB, published beside the page like `eng-data.js`). `tests/js/reader_parity.js` runs it under
  node on the same page images as `ui/ocr_eval.py`: bands, bars, pitch, row isolation, suffix marks, glyph readings and
  cleaned cells identical on all 222 rows of the three scans (after matching OpenCV's opening exactly: borders count and
  an even kernel shifts one pixel).
- **Every scan on file** (`ui/ocr_eval.py audit3`, history from schedules before the day only, the page's bank):
  25 Sep 71/71, 28 Sep 75/75, 29 Sep 76/76 taken; **0 wrong, 0 boxed, no printed row missed**. Every row taken equals the
  transcription, so no transcription mistake was found in the three packets.
- **Chrome load test** (local copy of the page, the scan PDFs, the Word file sent back to a local receiver because
  Chrome refuses automated downloads): 29 Sep in 54 s: 76 orders, **0 to check, 76/76 same as Tech's 29 Sep issue**,
  76/76 as transcribed; the Word file has the same pages, orders, formulas and settings as the pipeline's `FRM
  Formulation 2026-09-29.docx` (only the source line and a "generated in the page" note differ). 25 Sep in 58 s: 71/71,
  0 to check; 28 Sep in 54 s: 75/75, 0 to check (p3 line by continuation). Same as Tech's issue that day 70/71 and 74/75:
  RP26810-1 (SE21) now gets the 29 Sep issue (FUA152KS4 then FU0041KS4), as the latest-formulation rule requires (§7.47).
- **Caveat**: the glyph bank was built on 28 Sep from the 25 and 28 Sep scans, so on those two days the glyph reader is
  partly in-sample; 29 Sep is out of sample. New scans will show how it holds; a disagreement is always boxed, never
  guessed.
- Tests: `tests/test_scan_reader_page.py` (`OCR_TESTS=1`: every row of the three scans right and taken; page reader =
  reference on every row), `tests/test_product_code.py` (the page's decision, suffix, line-code and continuation rules).
- Artifact republished: version 25, with `glyph-bank.js` beside the page (and `eng-data.js`, unchanged).

## 7.50 The system's own past schedules: order rule fixed, masters refined (30 Sep 2026)

James: *"i got the past production schedule and put it into this folder. Go through and refine your data base"* (SharePoint
`Profile Process Control - Documents/Technical Engineering Team/Production Instruction`, synced on James's PC).
- **What the folder holds**: 1,204 files; 1,167 named MMDDYY(.pdf) are the AIX report "PP PROFILE PRODUCTION INSTRUCTION -
  EXTRUSION" (WPPPOPRC) printed straight to PDF: the text itself, Courier, so no OCR is needed. `history/prod_instr.py`
  rebuilds each page as its line-printer text and reads it by its '|' columns: **1,162 days, 2020-04-01 to 2026-09-24,
  62,662 order rows**, no parse errors. Not read: `405323.PDF` (a Braskem bill of lading), 050820 / 111323 / 111423 (image
  scans), 111723 (printed rotated by another mail system). A line printed again later the same day (061620-2.pdf ...) is
  that line's revision. The other files in the folder (forms, photos, customer sheets, six "Production Formula Item"
  shift logs) were not used.
- **Check of my transcriptions**: the 23 and 24 Sep packets (read from scans) equal the system's text exactly: all 82 +
  80 rows, die, thickness, GSM, weight, pack, web width and sizes.
- **Order number rule fixed** (`order_number.py`, new): H + year digit + month (1-9, A, B, C) + **A** + 3 digits; SH + year
  digit + month + A + 2 digits (sample orders, about 60 a year, still current); RP + 2-digit year + month + 2 digits;
  suffix 1-2 digits. The first rule (H + 2 digits + letter + 3 digits) had the month and the A the wrong way round: it
  refused every October-December H order (30% of H orders; H5CA... all this year) and the reader could turn a month A
  into a 4 - it would have boxed every October order from 1 Oct. Also from the history: no order is ever dated after its
  schedule (0 of 62,662), H/SH orders are always under 2 years old, RP stock orders can be old (RP20624-1 on 9 Sep 2026,
  75 months). The readers, the page (corrections too) and the daily checks use it; a reading dated impossibly is no
  reading unless its month has a possible look-alike (B/8, A/4), which is then taken only when on file or read by the
  other reader (28 Sep p14 'H6BA020-1' -> H68A020-1). 2020-21 H orders used a year letter (V, W); the last left the
  schedule on 27 Jul 2022.
- **Product code rule confirmed**: all 62,662 system codes keep it; code thickness = the Thk column on every row (A0 = 10 mm
  ...); the code colour is always one of the three layer colours; 10 families (APA not in the history), 27 colours, all
  on the lists.
- **Findings for James/Tech**: material **EEE P** (423 rows, 2020 to 3 Sep 2026, mostly RPP50.. on SE21) - added to the
  schema's list, meaning to confirm. Letter+letter spec tokens (RD, OP, RM, RS, PI, AM, DM) are in 6,826 rows (RD, OP, RM
  in 2026): rule R2 of `scan_reader/ext_scan_reader.py` flags them for confirmation - not changed (James's say-so). SE42
  first appears in 2026.
- **Product Master** (published): `build_master.py` with `HIST_CSV=`: each product's values on its latest system run fill
  what was blank, a different value is a Check note ("system <date> ..."), nothing overwritten. 2,084 -> **2,652 products**
  (568 added as Draft, Source "System history"); blanks filled in 1,464 rows (material, grade, spec, colours, width,
  length, pack, PCs/stack, Stk/plt on 1,385; GSM 731; cut 756; Thk 140); 174 Check notes (Thk 94, e.g. DBP33BL1 3 vs system
  3.3; GSM 44; cut 35; PCs/stack 1). New column **Last Scheduled**. Schema check: only the Read Me layout note the
  published copy already had.
- **Extrusion Production Record** (published): `daily/record.py --history`: 1,152 days appended (2020-04-01 to
  2026-09-21, 62,454 rows); 23 and 24 Sep stay as recorded from the scans (the system has the same lines, orders and
  products); 62,838 rows. Source Scan names the PDF, page and print time.
- **Formula coverage** (read-only): of the 805 product + line pairs scheduled in the last 12 months, 92 have a Product to
  Formula row in the Formulation Master (43% of schedule rows). The PDFs carry no formulas; Tech's past FRM pages would.
- **Page**: the reader also takes an order + product on the schedule in the last two years (3,328 pairs from the
  record); corrections must keep the order rule and the schedule date. Chrome load test again (29 Sep as a user runs it: 76 read, 0 to
  check, 76/76 same as Tech; with history before the day only: 29 / 25 / 28 Sep 76/76, 71/71, 75/75, 0 to check). Artifact version 26.
- **Reader**: a sheet line broken where notes cross it is joined again (`line_groups`: 28 Sep p14 under "-BB510").
  Tests: `tests/test_order_number.py` (rule, dates, every system order since Aug 2022, every packet),
  `tests/test_product_code.py` (page: October/December/SH orders, dates, look-alike month), `OCR_TESTS=1` all 3 scans
  right and page = reference (pass).

## 7.51 Every production schedule on the PC: missed days, the rotated print, scans OCR'd and read (30 Sep 2026)

James: *"Do it for all"* (the three schedules saved under other names, the rotated print and the three image scans), *"except
the HR fies and other business document"*, *"if it needs to be rotated, rotate them"*, *"if its scan, OCR them"*, *"any
production schedule you can get your hands on, go through and update your data base"*.
- **Parser** (`history/prod_instr.py`): a file is dated by its Run Date, so the schedules saved as `0422524.pdf`,
  `BPN9PFR$_Xs7tuhwc.PDF` and `BPN9PFR$_YQuWBVBj.PDF` are 25 Apr 2024, 14 Oct 2024 and 12 Jun 2025; a print laid on its
  side (111723, 17 Nov 2023) is rebuilt from each character's origin and writing direction (`grid_any`). The pages are read
  as one stream, so a block that runs on to the next page keeps its cut rows and instructions; Total Sheets is now every
  cut row of an order (the first run counted only the first); instruction lines printed without the label are kept.
  **Every line of every day now adds up to the line total the report prints** (1,166 schedules, 1,158 days, 0 mismatches).
- **Image scans turned upright and read** (050820, 111323, 111423 = 8 May 2020, 13 and 14 Nov 2023; every page needed a
  quarter turn, saved in `work/history/scans/`). OCR (two readers) confirmed only 35 of 163 rows, so every row was read by
  eye against the system text of the days either side (`history/image_days_manual.py`: a row equal to a neighbouring day
  takes its values; what differs on the scan is written in). **Every line and each day's final total adds up to what the
  scan prints.** 8 May 2020 is the 10:32 print with SE13 reprinted at 10:38 (the reprint is the day's SE13).
- **Copier scans on the PC** (`history/scan_inventory.py`: 165 scans in Downloads and OneDrive, 3,535 pages, each page
  turned upright and its title read): besides the daily packets already on file, one older schedule day was found - **2 Nov
  2022** (Downloads/doc05067520260827113931.pdf pages 85-116: extrusion, converting and 6 formulation pages) - and a single
  extrusion page of **24 Apr 2014** (SE25, report page 16). Both read by eye and checked against the printed totals; on
  2 Nov 2022 report page 10 (SE32) is missing from the scan and is not recorded (the final total says it is RP22630-1's
  11,000 PCs). The rest are QC pallet tags, QC forms, resin data sheets, material-system and inventory reports.
- **Converting Production Record**: 2 Nov 2022 added (28 rows: SD31, SD11/SD12, SD41/SD42, SD51, SC31; `history/cnv_scans.py`,
  `daily/record.py --history-cnv`); every order + product matches an extrusion schedule. A cell printed cut off by its
  neighbour is completed only from the same order on another sheet the same day (H2AA266-1 ink 3005Blue).
- **Extrusion Production Record** rebuilt (`--replace-history`: the rows the first history run added are taken out and built
  again; daily-scan rows untouched): 63,231 rows, 1,166 days, 24 Apr 2014 and 1 Apr 2020 to 29 Sep 2026.
- **Product Master**: 2,659 products (+7 from the 2014 page); 11 rows' Last Scheduled moved later; nothing overwritten.
- **Not read (James: not wanted)**: HR forms, photos, quotes, bills of lading, customer sheets. **Found, not loaded**:
  formulation pages - the 6 lines on 2 Nov 2022 and loose FRM pages (SE43 3 Sep 2025, SE23 15 Sep 2021 x2, SE21 17 Jan 2018,
  SE31 5 Aug 2021) and 1998 Formosa production-tracing summaries; they are formulation records, not schedules, and loading
  formulas goes through the Formulation Master's Change Log - James to say.
- Tests `tests/test_history.py`. Artifact version 27 (the page's product list and order history).

## 7.52 Tech's past formulation pages, 2021 on (30 Sep 2026)

James: *"go ahead and add everything after 2020"*, *"if the fomulation is obsolete one (replaced by something newer) put it in
the log instead"*. Pages read by eye (`history/frm_scans.py`): the 28 Oct 2022 issue (12 lines, in the 2 Nov 2022 packet),
3 Sep 2025 (SE43, SE61), 15 Sep 2021 (SE23; two copies, one with "EXXON" written over F6502A - handwriting, not data) and
5 Aug 2021 (SE31). Left out as asked: the 17 Jan 2018 SE21 page and the 1998 Formosa tracing summaries.
- **Formulation Master** (`db/import_frm_history.py`, newest issue first; Changes 83-223, approved James Kuo; published,
  pre-flight clean, accepted): a formula the master already has on that line with other settings, or a product that
  already has a later formula on that line, is **obsolete: Change Log only** (Field "(superseded - history only)", 25
  rows); SE32's first FUA152WB4 row, replaced on the same page by the row marked "(New Formula)", likewise. Added as Draft:
  11 formulas (BFR000EB3, FUA151BL4, FUA001WB6 + reclaim run-out, FUA021WB6, FU0041WBA, FU0001WBA, FU0061WBD, FU0001WBD,
  FU0110WB7), their line settings, and product-to-formula rows (Last Run = the issue date); 6 formulas were already in the
  master as printed. Materials: spellings "FR-GPP30003 MP" (50-7002-361) and "WB-NPC PE-W22151" (50-7002-393) added;
  "Vistamaxx 3588FL Pre-mix" not mapped (a pre-mix, not the pure 3588FL) - only on formulas that were obsolete anyway.
  A "run out" note about a colour (NPC PE-W22151) is not the reclaim variant.
- **Formulation Report Record** (`record.py --history-frm`): all four issues as printed, obsolete formulas included
  (the record is the log of what Tech issued): 431 rows. HW7A188-1 (5 Aug 2021) left out: no product on any schedule.

## 7.53 The page reader on the 30 Sep schedule: a tilted border and new products (30 Sep 2026)

James tested the page on the 30 Sep schedule (doc05268320260930114819.pdf, 27 pages, 16 extrusion): *"it read 11 not 1"*
(H69A330-11 shown as -1), *"it should be 1793 not 179'"* (RPP40BL1793), and the H69A330-x rows with RPP30WB1065,
RPP30BL816, 817, 815, 818 read wrong: *"still a lot of fail read"*. Then: *"test it with the production schedule. Also
remember to test it with chrome"*.
- **Tilted border** (`clean_cell` / `cleanCell`): a border printed on a slant is no full ruled row, so it stayed in the cell
  and hid the first '1' of the suffix. Every dark run of 30 px or more is now erased, taken within one row either side so
  no stub is left where the line steps (a stub over the dash first read RP26918-1 as -4 on 28 Sep).
- **New products** (not yet in the Product Master): the text reader takes any code that keeps the code rule
  (`take_prod_rule`), the glyph reader reads position by position under the rule without snapping to the master
  (`decode_product_free`). Taken only when the two read the same code **and** the order is read the same by both: status
  *new product: both readers agree* (the page shows it with its own chip; the engineer completes the formula). Otherwise
  boxed, and the box shows what the paper shows - never the nearest code on file. A correction that keeps the code rule is
  accepted for a product not yet in the master.
- **Look-alike agreement**: when the text reader's code differs from a code on file only by look-alikes (S/5, B/8, O/0 ...)
  and the glyph reader reads that code both with and without the master, it is taken as *read by both readers*
  (RPA50WB56 read RPAS0WB56).
- **Result**: 30 Sep 87/87 rows taken, every one checked by eye against the paper; 25, 28 and 29 Sep still 100% taken,
  0 wrong. Page reader = reference reader on 309 rows (`tests/js/reader_parity.js`, four scans). **Chrome**: the built page
  read the 30 Sep PDF in 88 s, 87/87, the same rows as the reference. The Chrome test also caught a page error in v28
  (a variable used before it was set) - fixed in version 29.
- Tests: `tests/test_product_code.py` (new product and look-alike rules); `OCR_TESTS=1` real-scan tests.

## 7.54 Daily run 30 Sep 2026: the schedule, Tech's issue, the 13 new orders (30 Sep 2026)

James asked whether the 13 rows the Word file left to the engineer were ever run: *"did we ever ran these product code?
These could be new or there is issues with our data base"*. Six are new products never on a schedule since 2020
(RPP40BL1793, RPP30WB1065, RPP30BL815-818, all order H69A330). Seven ran before on that line (RPA60WB240 208 times) but
our formulas come only from Tech's pages, so nothing was on file for them there (RPA60WB240's 2022 formula was on file
as Draft, which the draft does not use). He then sent Tech's FRM scan for the day (doc05271720260930140641.pdf) - *"take
a look"* - and, on the F1102K / Q1203K names Tech still prints: *"ignore that. The engineer data base is still out of
date. Your data is correct with F1203K"* (CLAUDE.md, memory). Then *"yes continue"*: record the day as on 29 Sep.
- **Comparison**: where our draft had a formula (74 of 87 orders), it matched Tech's issue field for field. Tech issued
  all 13 others: 4 joined a running group; new codes FUA152BL4 (SE21), FU0101BL3 and FUA101BL3 (SE43); RP26916-2 on
  FUA021WB6 with the same settings as the 2022 page (the run-out now carries FUA021WB6, 2022 FUA001WB6); RP25523-2 on
  FUA011WB5.
- **Packet** `data/packets/packet_2026-09-30.json` (`work/transcribe_0930.py`, `work/transcribe_frm_0930.py`): 87 EXT rows
  (16 pages), 62 CNV rows (11 pages), 13 FRM pages. Every printed line total adds up; SE23's total is on the missing report
  page 9 and SE61 prints none (the handwritten weight sums match). Independent reader: 84/87 identical, 3 settled by eye.
  Two punctuation marks read at zoom differ from the 29 Sep copy (H63A200-1 "VOIDFORM.", H68A053-1 "VOIDFORM,"): today's
  values are today's page; the 29 Sep record stays as issued.
- **Published**: EXT / CNV / FRM workbooks 2026-09-30, Product Master (2,665: the six new products as Draft), the three
  records (+87 EXT, +62 CNV, +487 FRM rows), Formulation Master (Changes 224-263, Draft, pre-flight accepted; FU0012BL5 still
  not written until DOW-C104 is named), interface copy and artifact (v30). Same six High issues as 29 Sep (partition orders
  on SD22), none new.
- **DOW-C104 = F6502A** (James Kuo, 30 Sep 2026: *"thats F6502A. just old formulation where we used to use Dow plastic"*):
  "PP Virgin-silo 3 (DOW-C104)" added to F6502A's (50-1560-050) Other Spellings (Change 264); FU0012BL5 Hopper 1 (63) then
  written from Tech's 29 Sep issue (Change 265). FU0012BL5 is now complete in the master (Draft).
- **Reclaim first, always** (James Kuo, 30 Sep 2026, on RP26810-1: *"the one with reclaim first. we always want to use up
  our scrap first before using Virgin PP"*): the draft, the Word file and the page now put an order's reclaim formulas
  first whatever order Tech's page lists them (`resolve.run_order`; page `runOrder`), a 'run out' note last; a formula
  without reclaim after one with reclaim reads "If reclaim runs out" (was "Alternative"). On 30 Sep this reorders
  RP26810-1 (FU0041KS4 first) and H68A053-1 (FU0061WBD, reclaim 99, before FU0001WBD "For VOIDFORM order only" - asked
  James whether VOIDFORM is an exception); H66A116-1 / H64A244-1 FUA011WB5 now "If reclaim runs out". The records keep
  Tech's page order (as issued). Artifact v31; tests `test_draft_keeps_every_formulation`.

## 7.55 The system PDF as ground truth: corrections and a better scan read (1 Oct 2026)

James sent the system's own PDF of the 30 Sep report (BPN9PFR$_Z6KU24Rb.PDF): *"take a look at yesterday production
schedule PDF file and confirm your scan file is rock solid"*; then *"correct what you can"* and *"but the main goal is to
improve the OCR read and logic check when OCR read failed"*.
- **Check** (`scan_reader/verify_with_system_pdf.py`): 30 Sep 1,825 of 1,827 fields identical; 23 and 24 Sep (system PDFs
  092326 / 092426 in Production Instruction) the same kind of differences: special-instruction punctuation ("VOIDFORM," read
  as "VOIDFORM."), text carried onto the next page, a printed line under handwriting, and 24 Sep H64A244-1's two cut rows
  on a page missing from the scan (80,040 -> 240,120 sheets). Every key field identical.
- **Corrected** (`scan_reader/correct_from_system_pdf.py`, each change noted on the row): 23 Sep 7 rows, 24 Sep 6 rows,
  30 Sep 2 rows; all three days now 0 differences; EXT workbooks reissued (`publish.py --reissue`), EXT record rows
  reissued (`daily/record.py --reissue "<why>"`, new, only when James asks). 24 Sep checks 73 -> 76 (H64A244-1 complete).
- **Scan read** (`scan_reader/ext_scan_reader.py`, scored by `scan_reader/score_vs_pdf.py`; a day's own text left out of
  the library when scoring it): special instructions read per record from the label down, page-top text carried to the
  previous record, and snapped to the printed lines (`scan_reader/instructions.py`: 1,648 lines from the 2020-2026 system
  schedules; numbers from the scan, wording/punctuation/case/spacing from the matching printed form; only OCR-explainable
  differences accepted, so "RUN WIHT" stays as printed). Special instructions exact: 30 Sep 70% -> 99%, 23 Sep 100%, 24 Sep 96%.
- **Logic checks** (`scan_reader/validate_read.py`): handwriting read as a row dropped (24 Sep "-PC405"); an order under
  handwriting from the previous schedule day when one order fits line + product + die (30 Sep H69A038-1, 23/24 Sep
  RP26410-1) or sits between the same neighbours (30 Sep H68A020-1 under "-BB510"); thk from the product code; a die
  look-alike to the line's die (PA385 -> PA3B5); unreadable fields of a damaged row and unread instruction numbers from the
  same order the previous day; a "PLTS DONE" line not read today flagged. **After the checks every key field (line, order,
  product, die, thk, GSM, material, grade, spec, colours) is right on all 249 rows of 23, 24 and 30 Sep.** Remaining: text
  under handwriting and pages missing from the scan - flagged, not guessed. Tests `tests/test_scan_logic.py`.

## 7.56 Two-step daily read: the formulation first, then every field for the records (1 Oct 2026)

James: *"do read all. But make it two step. Get the fomulation to production team first. then read the rest for the data
base update (Production Record)"* - *"this will reduce the wait time"*.
- **Step 1** (`daily/stage1_formulation.py <scan> --date <d>`): key fields only, pages in parallel, logic checks, a
  step-1 packet in `work/stage1` (never `data/packets`: records, masters and the reader's evaluation never see a machine
  read; `config.packet_files()` gives it only to resolve/render_frm with `PKT_STAGE1=1`), then resolve, auger check and
  the Word formulation (footer "step 1: read by the scan reader"). An order or product the checks cannot confirm is an
  Exception, never a formula. Glyph distances for the whole scan at once (`Bank.prime`): identical values, about 25x
  faster. 30 Sep: 87/87 orders as the PDF-corrected packet, about a minute (was over 10). Deskew left as is: the faster
  angle moved pages by up to 0.07 degree. `--compare <d>` after step 2.
- **Step 2** (`daily/stage2_records.py <scan> --date <d>`, about 1.5 minutes): every other EXT column by its printed
  column (`scan_reader/ext_fields.py`). The report is line-printer text: the '|' bars of each record line give every glyph's
  column (pitch voted from all bar pairs, one per page; offset per line, kept on the page's drift); further cut rows are the
  lines under it with nothing left of the cut columns, and those at a page top belong to the record before (24 Sep
  H64A244-1). Fields read in their printed forms (commas by place, fractions from the printed set, NNXNN, DD-Mon/Stock
  with a Tesseract second read for months not yet in the bank). Own bank `glyph_bank_fields.npz` (13,207 glyphs labelled
  from the 23/24/30 Sep system PDFs, added to the key bank), so the key-field and page readers are unchanged. A record line
  with handwriting written into it is found inside its tall band (30 Sep H69A038-1, H68A020-1: product and die now read).
- **Checks**: printed forms; pallets x pieces x stacks vs sheets within 1.5 pallets (the report rounds by up to one);
  999 pallets only when the sheets fill that many; weight = width x length x GSM x sheets x 1.4187e-6 lb within 3%
  (98% of 2020-26 rows within 0.6%); web = whole cut widths; cut rows alike (240/240 records); the previous transcribed
  day's same order (sizes, pack, pieces, stacks, web, in-str date; a passed in-str date moved later is accepted); the
  printed line totals.
- **Measured with a bank that had not seen the day**: 30 Sep 87/87 and 24 Sep 80/80 records, every field right except
  special instructions under handwriting (flagged); all line totals agree but one footer not read (flagged). Leave-one-
  day-out over 23/24/30 Sep: 2 field errors in 245 records, both flagged by the checks.
- Output `work/stage2/packet_<d>.json` with notes in `unclear`: settled at zoom, CNV/FRM pages added by eye (not read by
  the reader yet), then saved to `data/packets` and the Daily run continues (CLAUDE.md). Next: the converting pages.

## 7.57 Daily run 2 Oct 2026 from the system's own PDFs (run 5 Oct 2026)

James sent the day as two PDFs instead of a scan: `BPN9PFR$_Z7Ubmp3i.PDF` (extrusion report, run 10/02/26 13:14:34, 18
pages) and `Die Cutting Schedule 10-02.pdf` (converting schedule printed from Excel, 11 pages). Both carry their text.
- **Step 1** (`daily/packet_from_pdf.py --ext`): 88 records from the report text, every line equal to its printed total,
  Final Total 6,325,199 PCs / 21,541,117 LBs. `FRM Formulation 2026-10-02.docx` (DRAFT): 81 orders as last issued on
  their line, 7 new for the engineer - H68A090-1 (SE25; same product as H66A116-1, FU0011WB5 / FUA011WB5), H69A330-6
  RPP30GS130 and H69A330-10 RPP30BD58 (SE43, never scheduled; 2 new Product Master rows), H69A350-1...-4 RBP33EB.. (SE61,
  ran Jan-Aug 2026, no Tech page on file). Sent to James 2 Oct.
- **Step 2** (`daily/cnv_from_pdf.py`, `--cnv`): 64 converting rows on 11 pages. Columns are the table's own lines named
  by their headers (the slitter page's extra 'Extrusion Start' column -> semi_start); each cell's whole text comes from the
  PDF's text-drawing operations, so a cell the paper cuts off reads whole (H68A127-1 Color 'WB GT WB', printed 'B GT V';
  H68A170-2 Semi-Size '51 4/16 X 73 12/16'); notes and banners follow the transcriptions' form (done notes, a cell's second
  line, 'Line directly above' / 'Lines directly below', banners outside the table). Against the 30 Sep transcription of the
  same orders: 1,072 of 1,080 fixed fields identical, the 8 others where the PDF is more exact.
- **Published** (same six High issues as 29-30 Sep, the SD22 partition orders; none new): EXT and CNV workbooks
  2026-10-02, Product Master (2,667), Extrusion Production Record (+88), Converting Production Record (+64; no FRM rows: no
  Tech pages), interface copy, artifact v32. Read Me notes name the PDFs (`cfg` keys `source`, `transcribed_note`, new in
  `build_xlsx.py`). Tests `tests/test_pdf_packets.py`.

## 7.58 Lessons from the interface artifact, written down (5 Oct 2026)

James: *"remember you had some trouble with document uploading into artificat? Can you make sure you document it in your
MD so other can learn from you?"*. CLAUDE.md now has a section, "The interface artifact: what went wrong before". It
covers:
- **Uploads.** The drop box was blocked because the page sent images to Claude, which James's account does not allow
  for an artifact. The page now reads the scan itself.
- **Data files.** An artifact page can load CDN scripts but cannot fetch data, so the language data and the glyph bank
  ship as scripts (`eng-data.js`, `glyph-bank.js`).
- **Copier scans.** pdf.js hung on them inside the frame, so the page takes each page's JPEG straight out of the PDF.
- **Downloads.** Downloads started by automation are blocked.
- **Chrome testing.** The page is served from 127.0.0.1, the PDF is handed over with DataTransfer, and the frame's
  token address is never copied.
- **Publishing (new on 5 Oct).** In a new or compacted session the first publish is refused until the live version has
  been read: open the saved copy with the Read tool, confirm it is the last build plus the host's wrapper, then publish
  again. Resending without reading it is refused a second time.

## 7.59 Scan or PDF through one door; daily run 5 Oct 2026 (5 Oct 2026)

James: *"make sure you can read PDF word file as well. I want to be able to feed it in both way (scan and PDf doc) and
have it able to process"*. `daily/intake.py` tells the system extrusion report, the converting schedule PDF and a copier
scan apart by their content and runs step 1 (Word formulation) or step 2 (records) for each. The interface page's drop
box takes the same three: the system PDF is read from its text (pdf.js, exact), a scan by the in-page reader as before
(30 Sep scan: 87/87 in 69 s), and the converting PDF is named as not used for the formulation. Artifact v34-v35.
Also on 5 Oct: the page stopped at load on 2 Oct data (no Tech FRM pages: `D.lines` empty; v32), fixed in v33 with the
draft as the day's lines; lessons in CLAUDE.md ("The interface artifact"); SharePoint permissions in the user settings.
- **5 Oct run** (BPN9PFR$_Z7XTIDbA.PDF, run 13:42:46; Die Cutting Schedule 10-05.pdf): 81 EXT records, every line equal to
  its printed total; Word formulation sent first, 68 orders as last issued + 13 for the engineer (6 new today, 7 still
  open since 2 Oct); 63 converting rows, fixed fields unchanged from 2 Oct. Published: EXT and CNV workbooks, Product
  Master (2,668), Extrusion record +81, Converting record +63, interface copy, artifact v35. High issues: the known SD22
  partition ones only.

## 7.60 The schedule run from email; 6 Oct step 1 (6 Oct 2026)

James: *"check my email everyday for schedule from JVallejo@wpjk.inteplast.com. usually there are two, one for extrusion
and one for converting"*; files to Downloads; "Full run, stop on new High"; *"Every 30 min, 11:00-16:00"* (weekdays).
The Microsoft 365 connector finds the emails but cannot return an attachment ("Binary attachment - content cannot be
returned inline"), and the browser pane is not signed in to Outlook. The attachments come through the classic Outlook on
James's PC over COM (`daily/fetch_schedule_mail.ps1`; it starts Outlook in the background). `daily/schedule_status.py`
says what is left for a date; `daily/new_highs.py` compares the day's High issues with the previous day's ("No formula to
propose" not counted). Scheduled task `daily-schedule-run` in the Claude app (runs while the app is open); CLAUDE.md
"The scheduled email run". Artifact v36 republished on James's request (comment monitor had stopped).
- **6 Oct step 1** (BPN9PFR$_Z7Y53NYt.PDF from "SCHEDULE 10/06", run 13:42:43): 81 EXT records on 13 lines, every line
  equal to its printed total; pre-flight 0 changes, IWPFT062 0 differences. Word formulation sent: 65 orders as last
  issued + 16 for the engineer. New since 5 Oct: H66A005-1 DPP50WB307 (SE21; GSM 1,052 printed, its instruction gives
  970-1000), H69A183-1/-2/-3 RPP30WB176/883/874 (SE43). Gone: H67A164-1, H69A031-3, H69A066-2, H69A066-5. The converting
  schedule for 6 Oct had not come by 13:15.
- **The formulation by email** (James: *"whenever this happen (aka schedule from my outlook), can you email me the
  formulation for that day"*): `daily/email_formulation.ps1` sends `out/FRM Formulation <date>.docx` to James only (address
  fixed in the script) through classic Outlook, since the connector's send tool takes no attachment; once per version of
  the file (`work/emailed_<date>.txt`), `-Replaces` for a rebuilt copy. 6 Oct sent 13:37, in James's inbox with the
  attachment. The scheduled task emails it at step 1.
- **Gate on new email** (James: *"Only run the rest of the program if there is new email. If not, no need to run the
  rest of the pipeline"*; *"if there is email that is within the previous and the current 30 minutes run, that's when the
  email attachment need to be pulled"*; *"No new email in system"*; *"Just end program if there's nothing new found"*):
  each tick first runs `daily/schedule_gate.py` (time, lock, then Johanna's emails received since the previous check, read
  from James's rule folder Inbox\Complete\Production Schedule; only those PDFs are pulled). None = the run ends with "No
  new email in system". Live test 6 Oct, replaying the afternoon's ticks: 12:43 none; 13:13 pulled SCHEDULE 10/06
  (13:02:29); 13:43 pulled DIE CUT SCHEDULE (13:24:10); 14:13 none; a check at 17:26 none. 5-6 Oct emails recorded as
  handled; the window starts 6 Oct 17:29.
- **6 Oct daily run** (converting schedule "Die Cutting Schedule 10-06.pdf", e-mailed 13:24, 62 rows on 11 pages): manual
  issues and cfg written, EXT/CNV workbooks and Product Master built and published, the three records appended (81 EXT, 62
  CNV rows; no FRM rows, no Tech pages), interface copy published, artifact v37. `new_highs.py`: 3 High, all also on 5 Oct,
  0 new. Orders without a formula: 16 (H66A005-1, H69A183-1/-2/-3 new today; the rest since 2 or 5 Oct). Converting: only
  H69A062-6 gone. Special instruction of H64A178-1 (Bradford, thickness range) is blank today (Low). Tests 67 passed.

## 8. Automation plan: one step at a time

| Phase | What | Needs |
|---|---|---|
| 0 | **This document.** Read the packet and agree the rules | In progress: Rev 1.4 (R1, R2 confirmed; daily run §7.10; calcs §7.12; file set §7.13; auger rules drafted §7.14, awaiting James; dosing split §7.16; code moved to a Claude Code repo §7.17) |
| 1 | Seed formula master: **built from Tech's calc workbooks** (`Formulation Master.xlsx`, §7.12); Tech reviews the code/setting mismatches | James/Tech answer §10 Q9 |
| 2 | EXT scan reader: **built** (§7.7). 0 silent errors in the leave-one-page-out test and on the 24 Sep second-day scan. Still to do: R9 checksum, rows under handwriting | More days' scans |
| 3 | Formula resolution + FRM rendering in the current layout; run beside the manual FRM for 2 weeks, diffing them | Phases 1–2 |
| 4 | Converting `Extrusion Status` X OF Y taken from EXT instead of typed by hand | Who owns CNV (§10 Q7) |
| 5 | Formula-change log: every settings change dated, with who approved it | Tech agreement |

**Not automated, by design:** choosing a new formula or changing settings. The pipeline proposes; Tech decides.

---

## 9. Where files live (James, 28 Sep 2026; §7.21)

```
General\Engineering Pipeline\Production Formulation\         THE DATABASE (PUBLISH_DIR; only publish.py writes here)
  Product Master\            Product Master.xlsx
  Formulation Data Base\     Formulation Master.xlsx · Auger Calibration.xlsx · Formulation Calc Library.xlsx
  Daily Formulation Report\  FRM Draft / FRM Formulation Report YYYY-MM-DD.xlsx · Formulation Report Record.xlsx
  Extrusion Schedule\        EXT Extrusion Schedule YYYY-MM-DD.xlsx · Extrusion Production Record.xlsx
  Converting Schedule\       CNV Converting Schedule YYYY-MM-DD.xlsx · Converting Production Record.xlsx

General\Claude MD, PY Pipeline File\Engineering Pipeline\Production Formulation Automation\   CLAUDE'S WORKSPACE (DOCS_DIR)
  HANDOFF - Production Formulation Automation.md   (this document: the spec, edited in place)
  docs (.md), code copies (.py), formulation-pipeline starter 2026-09-28.zip
  Formulation Master.xlsx (calc-derived, until renamed) and the old copies of the database files (to delete)

github.com/jameschingkuo-cloud/Profile-Formulation (private)   the code with history (backup)
C:\Users\JamesKuo\dev\formulation-pipeline\                  the working copy of the code (local, NOT synced; git)
```

This folder also holds `HANDOFF - Monthly Complaint CA Summary.md` **Rev 0.2**, a stale copy of a
different pipeline. The current version is Rev 0.3 in the Claude Project. It belongs in
`Monthly Customer Complain Corrective Action Summary\` (CAS §7).

---

## 10. Open questions for James

1. ~~Can `WPPPOPRC` be exported as text?~~ **Answered 23 Sep 2026: no.** The AS400 report is tied to
   the printer; James will look at it later. The pipeline reads the scan (§7.5).
2. **The `Mat A Sp. Req.` codes** (§7.6 R3–R7 are taken from one day's data; please confirm): what do `P`/`A`, `R1` `R2` `R4` `S1` `RD` `RM` `R6` and the colour
   codes (`WB` `KS` `WM` `BL` `EB` `GT`) stand for?
3. ~~Where does Tech keep the formulas today?~~ **Answered 25 Sep 2026:** per-line calc workbooks
   `SExx Formulation.xls` (settings from auger calibration) and per-line Word formula books (§7.11–7.12).
   Still open: what decides the formula number (152 vs 151 vs 041)? Original question:
   **Where does Tech keep the formulas today?** Is there a master file per line, or is each day's
   FRM edited from yesterday's? What decides the formula number (152 vs 151 vs 041)?
4. **Who makes FRM each day, how long does it take, and when must it reach the floor?**
5. ~~`Set`~~ **answered 25 Sep:** auger setting; g/min = calibration slope × setting (§7.12). Still open: `AC = 1` / `AC = 90`.
   Original: **`Set` and `AC`:** what unit is `Set` (feeder %, rpm, dial)? What do `AC = 1` / `AC = 90` mean?
6. Lines 11, 14 and 15: do they exist, and do they need FRM pages?
7. **CNV:** who owns the converting sheets? Is the `Extrusion Status` X OF Y in scope?
8. Is the formula code structure in §6.1 right?
9. **FRM vs calc formula codes (§7.12):** the same settings carry different codes on the FRM page and in the
   calc workbook (e.g. FUA152WB4 vs FUA012WB4/FUA062WB4/FU062WB4). Which is the real code?
10. **Production Formula Item log:** what is the "Formula Item #" (1–8)?
11. Is there an SE42 calc workbook? *(Probably not needed: Line 12 is a weight line, §7.16. Confirm.)*
12. Two calibration slopes in use for the same hopper + material (8 cases): which is current?
13. **Auger preference table (§7.14):** is the draft right for every line? Which materials may share one
    calibration (a "calibration family", e.g. all colour MBs on H4, 1102K/1203K, WB/mix reclaim)? Are the 82
    out-of-role rows (HDPE on SE21/SE13, antistat on SE21 H3, talc on SE23 H5 …) allowed, or sheet errors?
14. **Where do the calc workbooks live** (so the hard rule can read them where Tech saves them)? *Now also `CALC_DIR` in the repo's `local_settings.json` (§7.17).*
15. **Which source wins** when calc, Word book and FRM disagree (§7.13 #1)?
16. **Slope units** (g/min per dial unit, or g/30 s as in the 1997 tables?), and were the augers recalibrated when
    talc, CaCO₃ and KS grades changed (§7.13 #11)? Which of `Process tech/CALIB`, IWPFM031 records or the 2024
    calibration screen holds the current slopes?
17. **lb/hr:** gross die width (the calc's convention since 1998) or net order width? And is the AS400
    paperless production system the source for actual output in the Extrusion Production Record?
18. **SE22 and SE21 hopper 4 (colour):** the headers say 1:100 but the slopes fit a 1:70 gearbox (§7.16 A7).
    Which is fitted? A one-minute catch test on each settles it; if 1:100 is right, Line 5 runs about 30% less colour
    than its calc shows.
19. **SE32's slopes differ from every other line's** (1203K 92.2099, talc 141.0847, WB 19.8612, CaCO₃ 27.493, all
    ±11–13% off the shared set). Was SE32 recalibrated on its own (then the others are stale), or are these errors?
20. **Do the auger blenders run continuously or on demand** (start/stop on a level switch)? The augers' total is
    above the extruder's output on 1,233 of 1,239 blocks, which only makes sense on demand. If so, the settings set
    the ratio only, and #14 in §7.13 is closed.
21. **Weight blenders (Lines 7, 12, 13, 16):** which make/model, and can they export material usage per
    component? That would give the only measured formulation and material consumption in the plant.

---

## 11. Checksum manifest (25 Sep 2026; locations updated 28 Sep 2026)

The files as published on 25 Sep. On 28 Sep, Product Master and the six daily workbooks were copied by SharePoint
(server-side, same bytes; sizes re-checked) into the database folders (§9, §7.21): `Product Master\`, `Extrusion
Schedule\`, `Converting Schedule\`, `Daily Formulation Report\` instead of the root and `Daily/2026/`. The live
record is `data/published_manifest.json` in the repo. As first staged back from the device after upload: `.xlsx` files are checked by a hash of
every sheet's cell values: SharePoint adds `customXml` / metadata parts on upload, so the file hash differs from the
built file even when every cell matches. On 25 Sep 2026 all eight workbooks matched their build copies cell for cell.
This document is not listed (it can't carry its own hash). Update this table whenever a file here changes.

| File | Bytes (device) | SHA-256 of file (first 16) | Content check |
|---|---|---|---|
| `Formulation Master.xlsx` | 3,667,095 | `4e5781f776f7b4ce` | cells sha256 `e0197d136359737a` (35916 rows) |
| `Product Master.xlsx` (25 Sep; superseded 28 Sep, below) | 277,049 | `15800f5bc34cf73e` | cells sha256 `085b7ead92283aaf` (2107 rows) |
| `Product Master/Product Master.xlsx` (28 Sep, local publish, §7.25) | 270,362 | `851941c70ef423bc` | cells sha256 `9c1561018e82f934` |
| `Extrusion Schedule/EXT Extrusion Schedule 2026-09-25.xlsx` | 42,725 | `8cd1512ae913193f` | cells sha256 `1b8a6275de498965` |
| `Converting Schedule/CNV Converting Schedule 2026-09-25.xlsx` | 38,370 | `a6ff640b7e7e5b7b` | cells sha256 `ce5d1f74d2841776` |
| `Daily Formulation Report/FRM Formulation Report 2026-09-25.xlsx` | 45,642 | `d24bd9ba19b47c3f` | cells sha256 `7e0ed8f0f7fdbb39` |
| `Extrusion Schedule/EXT Extrusion Schedule 2026-09-28.xlsx` | 44,813 | `a58645b7f2209c5e` | cells sha256 `b6ccf01509ce771a` |
| `Converting Schedule/CNV Converting Schedule 2026-09-28.xlsx` | 36,161 | `be6bc95130fc5d66` | cells sha256 `9aa7f50425b498ea` |
| `Daily Formulation Report/FRM Formulation Report 2026-09-28.xlsx` | 47,828 | `23d87a1ba57ee8b3` | cells sha256 `5e10b38ea19a1a2f` |
| `Daily Formulation Report/Formulation Report Record.xlsx` (§7.26) | 126,316 | `221b55efede0f730` | cells sha256 `de1655012b9a5193` (1,656 rows) |
| `Extrusion Schedule/Extrusion Production Record.xlsx` (§7.26) | 30,140 | `68c3d4bdcddca9c1` | cells sha256 `7755a7328ec270e2` (308 rows) |
| `Formulation Data Base/Formulation Calc Library.xlsx` (§7.27, renamed) | 3,667,095 | `4e5781f776f7b4ce` | cells sha256 `e0197d136359737a` |
| `Formulation Data Base/Formulation Master.xlsx` (§7.27, Draft seed) | 53,882 | `3da9441e7aa9fe91` | cells sha256 `ff4482f76f86e6a3` |
| `Converting Schedule/Converting Production Record.xlsx` (§7.26) | 35,507 | `5f08605a883247ba` | cells sha256 `a6992f47668109d7` (270 rows) |
| `Daily/2026/CNV Converting Schedule 2026-09-23.xlsx` | 46,840 | `05fd6755e1cf7463` | cells sha256 `6a9604c5d6643749` (170 rows) |
| `Daily/2026/CNV Converting Schedule 2026-09-24.xlsx` | 47,886 | `27c12183b4abe094` | cells sha256 `9a45c01c77e130a6` (174 rows) |
| `Daily/2026/EXT Extrusion Schedule 2026-09-23.xlsx` | 60,575 | `ebbd6648d699391c` | cells sha256 `385699de5f812b1c` (304 rows) |
| `Daily/2026/EXT Extrusion Schedule 2026-09-24.xlsx` | 60,286 | `4174cbee805fa845` | cells sha256 `93a4216a6a489dc5` (287 rows) |
| `Daily/2026/FRM Formulation Report 2026-09-23.xlsx` | 57,524 | `1c9378a17d8b1e45` | cells sha256 `05f6f7e41a141372` (491 rows) |
| `Daily/2026/FRM Formulation Report 2026-09-24.xlsx` | 56,072 | `0491a2256a5c3103` | cells sha256 `312ec9162999c34c` (460 rows) |
| `ext_scan_reader.py` | 26,947 | `b449c3c96c62ffea` | bytes |
| `ext_truth_2026-09-23.csv` | 5,385 | `94ed4d1c2b9b31f0` | bytes (CSV: LF on device, CRLF in the build copy) |
| `auger_rules.py` (Rev 1.3) | 4,885 | `644d1268af7accab` | bytes |
| `formulation-pipeline starter 2026-09-28.zip` (Rev 1.4) | 1,123,527 | `7f2972634fc7e62b` | bytes; unzips to 36 entries, tests pass in a fresh unzip |

---

## 7.62 Daily run 7 Oct 2026 (7 Oct 2026)

Scheduled run, both emails in one window (SCHEDULE 10/07 13:07, DIE CUT SCHEDULE 13:08). No code change.
- **Step 1** (BPN9PFR$_Z7Zg8XB5.PDF, run 13:43:54): 86 EXT records on 13 lines, every line equal to its printed total;
  pre-flight 0 changes, IWPFT062 0 differences. Word formulation emailed to James and sent in chat: 62 orders as last issued,
  24 for the engineer. New since 6 Oct: H69A330-8, H69A330-5 (SE11), H6AA013-1, H69A344-1, H69A345-4, H69A338-1, H69A338-2
  (SE13), H6AA036-3 (SE43). Gone: H69A158-1, H69A105-3 (SE13), H66A005-1 (SE21). Printed GSM outside the instruction's
  range: H69A039-1 and H63A200-1 (631 vs 582-600), H68A088-1 (514 vs 473-488), H68A091-1 (793 vs 729-751).
- **Step 2 and daily run**: converting schedule 54 rows on 10 pages (9 orders gone since 6 Oct, none new). Manual issues and
  cfg written, EXT/CNV workbooks and Product Master built and published, records appended (86 EXT, 54 CNV; no FRM rows),
  interface copy published, artifact v38. `new_highs.py`: 3 High, all also on 6 Oct, 0 new. pytest 68 passed, 5 skipped.

## Revision history

| Rev | Date | Editor | What changed and why |
|---|---|---|---|
| 1.53 | 2026-10-07 | Claude Code (local, with James Kuo) | **7 Oct daily run (§7.62)**: both schedule emails 13:07/13:08; formulation emailed (62 as issued, 24 for the engineer); 86 EXT + 54 CNV rows built, published and recorded; artifact v38; 0 new High. |
| 1.52 | 2026-10-06 | Claude Code (local, with James Kuo) | **6 Oct daily run (§7.60)**: converting schedule came 13:24; workbooks, Product Master, records, interface copy and artifact v37 published; 0 new High. |
| 1.51 | 2026-10-06 | Claude Code (local, with James Kuo) | **Schedule run from email (§7.60)**: the day's formulation emailed to James; schedule PDFs fetched from Johanna Vallejo's emails through Outlook, status and new-High checks, scheduled task every 30 min 11:00-16:00 weekdays; 6 Oct step 1 (81 orders, 16 for the engineer). |
| 1.50 | 2026-10-05 | Claude Code (local, with James Kuo) | **Scan or PDF through one door; 5 Oct run (§7.59)**: `daily/intake.py` and the page's drop box take the system PDF (exact text) or a scan; page fix for days without Tech pages (v33); 5 Oct published (81 EXT, 63 CNV), artifact v35. |
| 1.49 | 2026-10-05 | Claude Code (local, with James Kuo) | **Interface artifact lessons (§7.58)**: what went wrong with uploads, data files, copier PDFs, downloads, Chrome testing and republishing, written into CLAUDE.md for the next session. |
| 1.48 | 2026-10-05 | Claude Code (local, with James Kuo) | **Daily run 2 Oct from the system PDFs (§7.57)**: EXT from the AIX report text, CNV from the Excel schedule's PDF (`packet_from_pdf.py`, `cnv_from_pdf.py`); Word formulation sent first (81 + 7 for the engineer); workbooks, Product Master, EXT and CNV records, interface copy and artifact v32 published. |
| 1.47 | 2026-10-01 | Claude Code (local, with James Kuo) | **Two-step daily read (§7.56)**: step 1 sends the Word formulation in about a minute (87/87 orders on 30 Sep); step 2 reads every EXT field by printed column with arithmetic, previous-day and line-total checks (30 Sep 87/87, 24 Sep 80/80 records on a bank that had not seen the day). |
| 1.46 | 2026-10-01 | Claude Code (local, with James Kuo) | **System PDF as ground truth (§7.55)**: 23/24/30 Sep checked and corrected (reissued); scan reader special instructions 70% -> 96-100% (printed-line library); logic checks repair failed reads (every key field right on 249 rows). |
| 1.45 | 2026-09-30 | Claude Code (local, with James Kuo) | **Daily run 30 Sep (§7.54)**: the 13 engineer rows checked against history (6 new products, 7 missing formulas); Tech's issue matches every drafted order; packet, workbooks, records, PM and FM (Changes 224-263) published; F1203K rule. |
| 1.44 | 2026-09-30 | Claude Code (local, with James Kuo) | **Page reader on the 30 Sep schedule (§7.53)**: tilted border erased (H69A330-11); new products taken only when both readers agree without the master; S/5-type look-alike agreement; 87/87 on 30 Sep, tested in Chrome; artifact v29. |
| 1.43 | 2026-09-30 | Claude Code (local, with James Kuo) | **Tech's past formulation pages, 2021 on (§7.52)**: 28 Oct 2022 (12 lines), 3 Sep 2025, 15 Sep 2021, 5 Aug 2021; obsolete formulas to the Change Log only; 11 formulas added as Draft; Formulation Report Record +431. |
| 1.42 | 2026-09-30 | Claude Code (local, with James Kuo) | **Every production schedule on the PC (§7.51)**: misnamed and rotated schedules read; every line of every day adds up to its printed total; 3 image-scan days turned upright and read; 2 Nov 2022 (EXT + CNV) and 24 Apr 2014 (SE25) found in copier scans; EXT record 63,231 rows, CNV record +28; PM 2,659. |
| 1.41 | 2026-09-30 | Claude Code (local, with James Kuo) | **The system's own past schedules (§7.50)**: 1,162 days of Production Instruction PDFs read as text (62,662 rows); order-number rule fixed (month A-C, SH orders, dates); Product Master 2,652 (+568, 1,464 rows filled, Last Scheduled); Extrusion Production Record +1,152 days; page order history. |
| 1.40 | 2026-09-30 | Claude Code (local, with James Kuo) | **Two readers, border lines, handwriting ignored (§7.49)**: row cut at the sheet border line; Tesseract + glyph bank must agree; line code two ways + page continuation; page reader = reference on 222/222 rows; 25/28/29 Sep all rows right, 0 boxed; Chrome 29 Sep 76/76 same as Tech, Word file = pipeline's. |
| 1.39 | 2026-09-30 | Claude Code (local, with James Kuo) | **Scan reader and product codes made hard rules (§7.48)**: `product_code.py`; Product Master letter-O codes fixed (2,084); reader cells at the bars, no wrong take on 28/29 Sep; Word download locked until boxed rows are confirmed. |
| 1.38 | 2026-09-30 | Claude Code (local, with James Kuo) | **Always the latest formulation, even for a past schedule (§7.47)**. |
| 1.37 | 2026-09-29 | Claude Code (local, with James Kuo) | **Interface reads a schedule scan in the page and downloads the Word formulation (§7.46)**: Tesseract in the page, tuned on 28/29 Sep (no wrong order, none missed silently); Chrome load test 86 s; docx built in the page. |
| 1.36 | 2026-09-29 | Claude Code (local, with James Kuo) | **Tech's 29 Sep FRM reviewed and loaded; interface copy folder (§7.45)**: draft = Tech on 71/72; `db/import_frm.py` (master Changes 53-82); Formulation Report Record +441; Interface Copy folder, no Tech sign-off. |
| 1.35 | 2026-09-29 | Claude Code (local, with James Kuo) | **Tesseract 5.4 installed; glyph reader header anchor fixed (§7.44)**: 29 Sep crosscheck 67/76, rest settled for the transcription. |
| 1.34 | 2026-09-29 | Claude Code (local, with James Kuo) | **First end-to-end run from a schedule-only scan (§7.44)**: 29 Sep packet, Product Master, FRM Draft + docx, `daily/auger_check.py`, EXT/CNV records; build_master syntax fix; no-FRM check fix. |
| 1.33 | 2026-09-29 | Claude Code (local, with James Kuo) | **Exceptions completed in the database, re-run fills them (§7.43)**: resolve uses approved Product to Formula; `db/assign_formula.py`. |
| 1.32 | 2026-09-29 | Claude Code (local, with James Kuo) | **Print-ready Word formulation (§7.42)**: `daily/render_frm.py`, IWPFO055 issue block, one page per line, every formulation. |
| 1.31 | 2026-09-29 | Claude Code (local, with James Kuo) | **Operator and production manager views (§7.41)**; # Plt 999 confirmed as an AS400 limit (Info, real count shown). |
| 1.30 | 2026-09-29 | Claude Code (local, with James Kuo) | **Customer formulas parked for naming; every formulation always given (§7.40).** |
| 1.29 | 2026-09-29 | Claude Code (local, with James Kuo) | **Reclaim first (§7.39)**: several recipes under one code are expected; the daily check marks them Info unless unexplained. |
| 1.28 | 2026-09-29 | Claude Code (local, with James Kuo) | **F1102K replaced by F1203K (§7.38)**: master Changes 47-52; last High material issue closed. |
| 1.27 | 2026-09-29 | Claude Code (local, with James Kuo) | **XO-256 disregarded (§7.37)**: master Change 46; no XO left in the master data. |
| 1.26 | 2026-09-29 | Claude Code (local, with James Kuo) | **Master follows IWPFT062 (§7.36)**: `db/sync_iwpft062.py` in daily step 0; preview 0 differences. |
| 1.25 | 2026-09-29 | Claude Code (local, with James Kuo) | **HiTalc ZS = TL460 trade name (§7.35)**: master Change 45; interface sorts by severity. |
| 1.24 | 2026-09-29 | Claude Code (local, with James Kuo) | **Q1203K closed (§7.34)**: master issue resolved, off Open items; `checks.REPLACED` notes known substitutions as Info each day. |
| 1.23 | 2026-09-29 | Claude Code (local, with James Kuo) | **IWPFT062 Rev 18.0: PP YungSox 5050S = 50-1560-163 (§7.33)**: master Changes 24-44; `replace_material.py --create`. |
| 1.22 | 2026-09-29 | Claude Code (local, with James Kuo) | **PP Virgin = F6502A (§7.32)**: master Changes 21-23; master passes the schema check with 0 problems. |
| 1.21 | 2026-09-29 | Claude Code (local, with James Kuo) | **CF400 spelling X0-256 and White Reclaim = PP WB Reclaim (§7.31)**: master Changes 13-20; new `db/edit_master.py` for logged cell edits. |
| 1.20 | 2026-09-29 | Claude Code (local, with James Kuo) | **Q1203K replaced by F1203K (§7.30)**: master Changes 8-12 via the new `db/replace_material.py`; pre-flight accepted. |
| 1.19 | 2026-09-29 | Claude Code (local, with James Kuo) | **HM-10HP mapped to CA410 (§7.29)**: the first master change through the Change Log (Changes 1-7, approved by James); pre-flight accepted it. |
| 1.18 | 2026-09-28 | Claude Code (local, with James Kuo) | **Interface design started (§7.28):** Profile Formulation Artifact (prototype on the 28 Sep snapshot); source in `ui/`. |
| 1.17 | 2026-09-28 | Claude Code (local, with James Kuo) | **Masters maintained in Excel with change control (§7.27).** James: *"Yes to all. lets build it this way"*. Calc workbook renamed Formulation Calc Library; Draft Formulation Master seeded from IWPFT062 Rev 17.0 + the four FRMs and published; `db/preflight.py` stops on unlogged edits. IWPFT062 raises 4 High material issues (Q1203K, F1102K, Yungsox, HM-10HP). |
| 1.16 | 2026-09-28 | Claude Code (local, with James Kuo) | **The three history records built (§7.26).** James: *"build them"*. `daily/record.py` (append-only, enforced and tested); Formulation Report Record 1,656 rows, Extrusion Production Record 308, Converting Production Record 270, from the 23–28 Sep packets. Schema: `Formula Row` key, `Note`, `Source Scan`, `Handwritten`. Published (James: *"yes"*); §11 updated. |
| 1.15 | 2026-09-28 | Claude Code (local, with James Kuo) | **25 and 28 Sep published; Product Master merged (§7.25).** James: *"yes"*. Six daily workbooks and the Product Master (2,087 products) published and verified; §11 updated. Fixed a double-escaped quote in six 25 Sep CNV notes before publishing; `build_master.py` keeps prior `calc …` Check notes when run without calc data. Branch pushed to GitHub. |
| 1.14 | 2026-09-28 | Claude Code (local, with James Kuo) | **28 Sep FRM pages transcribed (§7.24)** from a separate scan James sent. The packet gains `frm` and `frm_source_scan`; the 74 missing-FRM Highs are gone; FRM Formulation Report 2026-09-28 is built. The FRM Draft matched Tech's issue on all 59 drafted orders. Nothing published. |
| 1.13 | 2026-09-28 | Claude Code (local, with James Kuo) | **R2 exception `OP` added.** H68A153-1 (SE31, 25 Sep) prints `OPOPOP`, "WHITE OPAQUE"; asked whether to accept it, James: *"yes"*. `SPEC_EXCEPTIONS` in `ext_scan_reader.py` is now D, M, P; same handling as RD/RM (accepted, always flagged); §7.6 R2 row and the field pattern updated; test `test_r2_exceptions` added. **OF/BD re-confirmed** (James: *"yes"*, already in R7 since Rev 1.10). The 25 Sep OPOPOP and 28 Sep colour-code manual issues go from High to Info with the decision recorded. Local setup done: Python 3.11.9 + `.venv`, handoff Rev 1.12 copied to the workspace folder (it matched Rev 1.8 byte for byte before), scans in `inputs\scans`; tests 23 passed, 1 skipped (no calc workbooks). Nothing published. |
| 1.12 | 2026-09-28 | Claude (cloud session with James Kuo) | **Back to James's PC (§7.23).** James: *"please change it to local"*. Open items listed for the local Claude Code session. |
| 1.11 | 2026-09-28 | Claude (cloud session with James Kuo) | **Glyph bank grown** with the verified 25 and 28 Sep rows (James: *"yes"*): 3,894 → 10,844 glyphs. Blind test on 28 Sep with 25 Sep added: 0 silent errors, 6 fewer flagged rows (§7.7). |
| 1.10 | 2026-09-28 | Claude (cloud session with James Kuo) | James: *"OF Fade-resistant orange"*, *"BD Dark blue"*. Both added to R7 (reader) and the Product Master colour list; meanings kept in `data/colour_codes.csv` (with WB = blue white). |
| 1.9 | 2026-09-28 | Claude (cloud session with James Kuo) | **28 Sep packet and the first FRM Draft (§7.22).** Scan arrived via chat. 68/75 identical; totals tie. The glyph reader's first silent error (new colour BD read as BL) caught by the crosscheck and fixed (colours also read letter by letter). `daily/resolve.py` drafts the day's formulation from the last issued FRM: backtest 68/69 identical on 25 Sep; 28 Sep 59/75 proposed, 16 to an engineer. |
| 1.8 | 2026-09-28 | Claude (cloud session with James Kuo) | **Two folders (§7.21).** Database workbooks in `Engineering Pipeline\Production Formulation\<kind>` (`PUBLISH_DIR`); handoff, `.md`, `.py` in the old folder, now Claude's workspace (`DOCS_DIR`). Product Master and the 23–24 Sep daily workbooks copied to the database folders; `publish.py` routes by `db/schema.py`; manifest moved. |
| 1.7 | 2026-09-28 | Claude (cloud session with James Kuo) | **25 Sep packet processed (§7.20)**; `scan_reader/crosscheck.py` added (transcription vs glyph reader vs printed totals). 67/71 identical, 4 reader misreads all flagged, every total ties. Converting Production Record added to the database (§7.19). |
| 1.6 | 2026-09-28 | Claude (cloud session with James Kuo) | **Database structure and flow (§7.19).** James: *"lets build the data base structure and flow first, then we design the interface"*. `db/schema.py` describes every workbook (masters with Change Logs, append-only records, daily files, calc evidence) in James's new folders; templates, a checker and `docs/DATABASE_TABLES.md` come from it; flow in `docs/DATABASE.md`. Starter code committed to GitHub (§7.18). No data built or published. |
| 1.5 | 2026-09-28 | Claude (cloud session with James Kuo) | **Product Master prepared as the base table (§7.18).** Excel only; Product Master first. James confirmed: in-between thicknesses (3.3 mm) are not in the code, the spec decides; the 4 letter-O codes are A0. `product_master/prepare.py` adds code-derived columns, completeness, an Issues sheet, Verify First, Colour Codes and an Import Map for the full data pull. Run on the 1,608 rows the SharePoint connector returns. This copy is in the GitHub repo; mirror to SharePoint. |
| 1.4 | 2026-09-28 | Claude (session with James Kuo) | **Code moved to a Claude Code repo (§7.17).** James: *"with such major project. Should this be done by claude code instead?"* then *"yes lets do it"*. Delivered `formulation-pipeline starter 2026-09-28.zip`: all pipeline code, packets and reference data, a `CLAUDE.md` built from this document's rules, a README for setup on Windows, `config.py` (paths), `publish.py` (the hard rule enforced: it refuses to overwrite a published file that changed since it was read or last published, and verifies by content after copying), and regression tests. Rebuilt every output from the starter: data identical to the published files (differences only where Rev 1.3 intended, plus Read Me text); the scan reader gives the same result with pip-only PyMuPDF. Standing instructions updated: the repo is the master for code; this document stays here and is edited in place. |
| 1.3 | 2026-09-26 | Claude (session with James Kuo) | **Dosing type per line (§7.16).** James: *"line 7,12,13, and 16 use more modern weight based dosing. The rest of the lines use old Auger dosing… It is simply speed setting 0 to 100."* Hardcoded as `DOSING` (load.py, auger_rules.py). This settles why auger lines don't add to 100, why one code has different settings by line (weight % is the recipe; settings are derived), and why SE42 has no calc; IWPFM031 covers exactly the auger lines. New: the slopes are one shared set copied to every line (SE32 alone differs); check A7 (slope × gear ratio fits the hardware) flags 192 rows, chiefly SE22 H4 colour on a 1:70 slope under a 1:100 header (+43%), and it confirms 232.17, not 219.15, for reclaim on a 1:14 auger; 16% of auger settings are below 10; the auger total above output points to on-demand blenders. Daily checks now depend on dosing type (Σ = 100 with `Auto` balance on weight lines; 0–100 range on auger lines); the 23/24 Sep issue lists are unchanged. Q18–Q21 added. |
| 1.2 | 2026-09-25 | Claude (session with James Kuo) | **Auger preference rules drafted (§7.14).** James: *"I think we also need to set some preference with Auger. Take line 6 as example…"* Per-line hopper role table built from the 2025–26 calcs, the plant's Hopper Auger Ratios table and James's Line 6 rule. It holds within a line but not across lines (Lines 1–3 reversed, 8/9 swap talc and homo, 10 swaps talc and CaCO₃). Proposed hard checks A1–A6. The key one, A2 (the slope must belong to that material on that hopper), is shown by the screenshot case RP25711-2 and by 258 rows elsewhere. **Other pipeline documents read (§7.15).** James: *"if you havent read other process MD go through them"*. PC416 = F6502A; IWPFT062 is the material master; lb/hr is calculated by design; calibration records located; AS400 paperless system as a production source. House rules adopted: re-stage before build, verify by content, checksum manifest (§11). Committed files from Rev 1.1 staged back and verified: identical. Nothing built, per James (*"Not yet about the file"*). |
| 1.1 | 2026-09-25 | Claude (session with James Kuo) | **Hard rule added: verify every source before making anything** (standing instructions). Target file set agreed (§7.13): Real Formulation Master (weight % + lb/hr by line + Change Log tab), Auger Calibration, Formulation Report Record, Daily Formulation Report, Extrusion Production Record, Product Master. Design review: 25 disconnects listed with evidence. Nothing built yet, per James. |
| 1.0 | 2026-09-25 | Claude (session with James Kuo) | **Formulation records surveyed and Tech's calc workbooks read** (§7.11–7.12). James: *"start going through the formulation record"*; *"Here are the formulation calculation which also has our Auger Crew rotation calibration"*. Built `Formulation Master.xlsx` (5,125 calc blocks; formula library, current recipes, auger calibration, product → formula, FRM vs calc). Set = auger setting (g/min = slope × setting). FRM and calc formula codes disagree for the same settings (Q9). Product Master gains Formula Code(s), Formula Last Run, End Use, Source and 1,990 calc-only products (2,086 total). |
| 0.9 | 2026-09-24 | Claude (session with James Kuo) | **Second daily packet (24 Sep) processed** (§7.10). James: *"todays data"*, *"update your 4 excel sheet"*. Built the EXT/CNV/FRM workbooks for 2026-09-24 and merged the packet into the Product Master: 96 codes, 5 new, none changed. Second-day reader test: 76/80 correct, 4 flagged, 0 silent (§7.7). The scripts now take the packet date and folder from the environment; `load.py` drops a sheet scanned twice; `build_master.py` merges into the prior master. Report page 11 missing again, and it cuts off H64A244-1. |
| 0.8 | 2026-09-24 | Claude (session with James Kuo) | **Product Master simplified** (§7.9). James: keep it as a product master only, with no history and no line data, plus a Last Updated column; basic EXT and CNV data only; formulation data to follow. The workbook is now one Product Master sheet (91 codes, Check / Status / Last Updated) and a Read Me. |
| 0.7 | 2026-09-24 | Claude (session with James Kuo) | **Product Master started** (§7.9). James: keep a master data list, with Product Code (= material master number) in the first column. 91 codes from the 23 Sep packet, plus Product x Line (the formula map), Product x Converting, Order History and Conflicts. Script `build_master.py`. |
| 0.6 | 2026-09-24 | Claude (session with James Kuo) | **Transcribed the whole 23 Sep packet into three workbooks and cross-checked it** (§7.8). All totals reconcile. The issues are listed in §7.8 and on each workbook's Issues sheet. Scripts and JSON are saved to the project. |
| 0.5 | 2026-09-24 | Claude (session with James Kuo) | **R2 confirmed by James**, as written: spec = letter + number; `RD`/`RM` accepted only from the exceptions list and flagged every time for confirmation. §7.6 table and the rules block in `ext_scan_reader.py` updated to say so. No behaviour change. |
| 0.4 | 2026-09-23 | Claude (session with James Kuo) | **Built the EXT scan reader with hardcoded rules.** James: improve OCR with logic, and *"make sure these are hardcode so we never forget"*: line code = 2 letters + 2 digits (R1), spec = letter + number (R2). Added §7.6, the rules table (R1–R10), and §7.7, the reader: deskew, fixed-pitch glyph cells, a nearest-neighbour glyph bank from the 82 verified rows, and decoding under the rules with flags for anything uncertain. Leave-one-page-out: 69/82 rows fully correct, 13 flagged, **0 silent errors**. Files: `ext_scan_reader.py`, `ext_truth_2026-09-23.csv`. |
| 0.3 | 2026-09-23 | Claude (session with James Kuo) | **§10 Q1 answered: no text export.** James: the AS400 can't produce the report as text because it is tied to the printer. Added §7.5, reading the scan: Tesseract tested on SE11 and rejected (misreads `1`→`I`, `5/8`→`578`, `R1`→`RI`, drops fields); Claude reads the page images instead, checked against the printed line totals (PCs = sum of all Total Sheets rows, LBs = sum of Weight; SE11 checks out at 147,500 / 146,098), field patterns and page numbering. §7.1, §8 Phase 2 and §9 updated to match. |
| 0.2 | 2026-09-23 | Claude (session with James Kuo) | **Read the daily production packet** (scan, 39 pp.: EXT pp. 1–16, CNV pp. 17–26, FRM pp. 27–39). Documented all three layouts, the order-number join, the line map (L1 = SE11 … L16 = SE61) and the feeder layouts; cross-checked all 82 EXT order lines against FRM (0 missing); set out how formula codes appear to be built and the exceptions (RUN WITH inheritance, alternates, variants); proposed the master tables and daily run. Renamed to the house `HANDOFF - …` convention. Earlier scan `doc05228120260923134352.pdf` was the CAS scan, not this packet. |
| 0.1 | 2026-09-23 | Claude (session with James Kuo) | Generic scaffold (`Production_Formulation_Automation.md`) before any source was seen. |
