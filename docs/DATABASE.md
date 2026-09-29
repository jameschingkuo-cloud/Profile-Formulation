# Formulation database: structure and flow

Proposed 28 Sep 2026 for James Kuo to confirm. The database is a set of Excel workbooks (James: Excel only) in
the SharePoint folder **General › Engineering Pipeline › Production Formulation**, one subfolder per kind. The
column-by-column reference is [`DATABASE_TABLES.md`](DATABASE_TABLES.md), generated from `db/schema.py`, which is the
single description of every workbook. The same description makes the blank templates and checks any workbook.

## 1. What goes where

```
Production Formulation\
  Product Master\
    Product Master.xlsx ................. MASTER   one row per product (exists; 2,086 products)
  Formulation Data Base\
    Formulation Master.xlsx ............. MASTER   approved formulas: recipe (weight %), line settings,
                                                   product -> formula, materials, lines, Change Log   [NEW]
    Auger Calibration.xlsx .............. MASTER   hoppers, current slopes, catch tests, Change Log   [NEW]
    Formulation Calc Library.xlsx ....... EVIDENCE everything read from Tech's SExx Formulation.xls
                                                   (today's "Formulation Master.xlsx", renamed)
  Daily Formulation Report\
    FRM Draft <date>.xlsx ............... DAILY    what the pipeline proposes + Exceptions             [NEW]
    FRM Formulation Report <date>.xlsx .. DAILY    the formulation as issued (exists)
    Formulation Report Record.xlsx ...... RECORD   every formulation issued, by day/order/feeder     [NEW]
  Extrusion Schedule\
    EXT Extrusion Schedule <date>.xlsx .. DAILY    the day's EXT print, transcribed (exists)
    Extrusion Production Record.xlsx .... RECORD   each order's progress by day                      [NEW]
  Converting Schedule\
    CNV Converting Schedule <date>.xlsx . DAILY    the day's converting sheets (exists)
    Converting Production Record.xlsx ... RECORD   each converting order's progress by day           [NEW]
```

These are the six files agreed on 25 Sep (HANDOFF §7.13), plus the daily draft, the calc evidence and a converting
history (James, 28 Sep 2026). Converting has its own record instead of living inside the extrusion one.

| Kind | Rule |
|---|---|
| **Master** | Approved reference data. Changes **only** through its Change Log sheet, with who asked, who approved and why. A row starts as Draft; the pipeline uses only Approved rows. |
| **Record** | Append-only history. Rows are added, never edited. |
| **Daily** | One workbook per day, kept as issued. `publish.py` refuses to replace an earlier day. |
| **Evidence** | Rebuilt from Tech's files whenever they change. Never edited. Used to seed and check the masters. |

## 2. How the tables connect

```
Product Master ── Product Code ──> Product to Formula <── Line Code ── Lines (dosing: WEIGHT / AUGER)
                                          │
                                   Formula Code + Variant
                                          v
                                       Formulas ──> Recipe (weight % per material, per extruder; = 100)
                                          │                  │
                                          │            Material ID ──> Materials (IWPFT062 codes)
                                          v                  │
                                    Line Settings <──────────┘
                                   (what the floor sets)
                                          ^
                    AUGER lines: Set = % x T / slope ── Auger Calibration (line + hopper + material)
                    WEIGHT lines: Set = %; 'Auto' = balance
```

- **The recipe is the weight %.** The same formula gives different settings on different lines because the
  hoppers and slopes differ (HANDOFF §7.16). So `Recipe` holds one row per material, and `Line Settings` holds what
  each line actually sets, with the % those settings give and the deviation from the recipe.
- **Variants** (reclaim run-out, VOIDFORM, sign blank, corn box, roll) are rows in `Formulas`, not separate codes.
- **Materials are keyed on the plant's material code list (IWPFT062)**, so the four spellings of the virgin resin
  become one Material ID.

## 3. Daily flow

```
 1  Scan of the day's packet  ─────────────────────────────────────────────────────────────────────┐
 2  Transcribe → data/packets/packet_<date>.json (+ scan reader cross-check)                     [exists]
 3  PRE-FLIGHT (hard rule): re-read every master and Tech's calc workbooks where they live;
    compare with the published manifest and the Change Logs. Unlogged change → STOP, list it.   [part built]
 4  EXT / CNV / FRM <date>.xlsx  (as printed)                                                    [exists]
 5  Merge into Product Master (new products = Draft)                                             [exists]
 6  RESOLVE each EXT order:  RUN WITH partner → its formula;  else Product to Formula (Approved)
    for that line → Line Settings.  Anything not matched exactly → Exceptions.                  [to build]
      = FRM Draft <date>.xlsx
 7  Tech reviews the draft + Exceptions, decides each exception, signs.
 8  Issue: render the FRM pages from the signed draft [to build]; append to Formulation Report Record;
    append the day's orders to Extrusion and Converting Production Records (daily/record.py).   [records exist]
 9  publish.py → each file to its subfolder, verified by content; commit the manifest.         [exists; routing to add]
```

Until step 8 is trusted, Tech keeps issuing the FRM by hand and the pipeline runs beside it: the draft is compared
with Tech's page every day for two weeks (HANDOFF §8 phase 3).

## 4. When Tech changes a formula or a slope

```
 Tech edits a calc workbook  →  calc rebuild (Formulation Calc Library)  →  differences from the masters
 listed as proposed changes  →  James/Tech approve  →  Change Log row  →  master updated  →  publish
```

Nothing reaches a master without a Change Log row that names an approver. That is the hard rule made permanent.

## 5. Order of building

1. **Structure** (this document, `db/schema.py`, blank templates). *Done 28 Sep 2026.*
2. **Seed the masters as Draft** from what we have: Lines (settled), Hoppers (draft rules), Materials (from the
   calc and FRM spellings, keyed on IWPFT062), Formulas + Recipe + Line Settings + Calibration from the Calc
   Library, Product to Formula from the calcs and the two packets. Every seeded row is Draft.
3. **Tech approves** the formulas that run most (the ones on the daily packets first).
4. **Resolve step + FRM Draft**, run beside Tech's FRM.
5. **Records** (Formulation Report Record, Extrusion and Converting Production Records) and `publish.py` routing to the subfolders.
   *Records built 28 Sep 2026 from the 23, 24, 25 and 28 Sep packets (`daily/record.py`, HANDOFF §7.26).*
6. **Interface**: the page where people upload the schedule and download the formulation, on top of steps 4–5.

## 6. Decisions (James Kuo, 28 Sep 2026: "Yes to all")

1. **Renamed:** the calc-derived workbook is `Formulation Data Base\Formulation Calc Library.xlsx` (published 28 Sep,
   same content); `calc/build_formulation_master.py` now writes that name. `Formulation Master.xlsx` is the approved master.
2. **Approval:** formulas and slopes by Tech; rules (dosing, R1/R2, hopper roles) by James. Names go in Approved By.
3. **Material ID** = the IWPFT062 Material No. (e.g. `50-1560-050`), from IWPFT062 (Rev 17.0 at the seed; Rev 18.0 added PC5050 on 29 Sep 2026). Plant materials with no
   number get `INT-` IDs (reclaims, premix); materials used on the FRM but not on IWPFT062 get `NL-` IDs and a High issue.
4. **Variants:** Primary, Reclaim run-out, VOIDFORM, Sign blank, Corn box, Roll, Other.
5. **Folders:** the published files live in their database folders (done 28 Sep). The stale copies in the workspace
   folder (`Product Master.xlsx`, `Daily6\`, the old `Formulation Master.xlsx`) were checked identical to the
   published or superseded files; James deletes them (SharePoint recycle bin keeps them 93 days).

## 7. Maintaining the masters (James, 28 Sep 2026: "lets build it this way")

```
 Tech / James edit the master in Excel (SharePoint)  ->  add a Change Log row (Why, Requested By, Approved By)
        |                                                  drop-down lists stop typos; sheets can't be renamed/deleted
        v
 Every pipeline run:  python db/preflight.py check "Formulation Master.xlsx"
        |  compares with the last accepted version (data/snapshots/, in git)
        |-- every change has an approved Change Log row -> accept -> run continues
        '-- any change without one -> STOP, listed for James; nothing is built
```

- The pipeline **never rewrites a master**. `db/seed_master.py` seeded the Draft once (28 Sep 2026); later data from
  Tech's calcs or new packets is *proposed* (Issues / a proposals sheet) and applied by people through the Change Log.
- `publish.py` also refuses to overwrite a master that changed since the pipeline read it.
- Claude is for the heavy changes: a new line, new slopes after a catch test, bulk updates from the calc workbooks,
  and "what changed" reports.
