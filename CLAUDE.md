# Production Formulation Automation (Inteplast Profile Plant, WPJK)

This repo automates the plant's daily production formulation work for **James Kuo**, Technical Process Engineer.
It is the code. The spec and running state live in the **handoff document**, at the `HANDOFF` path in
`local_settings.json`, in Claude's workspace folder (`DOCS_DIR`). The § numbers below refer to it.

**Two SharePoint folders (James, 28 Sep 2026):**
- `PUBLISH_DIR` = `General\Engineering Pipeline\Production Formulation`: **the database only**, one subfolder per kind
  (Product Master, Formulation Data Base, Daily Formulation Report, Extrusion Schedule, Converting Schedule;
  `db/schema.py` says which file goes where).
- `DOCS_DIR` = `General\Claude MD, PY Pipeline File\Engineering Pipeline\Production Formulation Automation`: Claude's
  workspace, *"where you will put all the MD, PY etc etc that is not data base related file"*: the handoff, `.md`, `.py`,
  code snapshots.
**Before changing anything, read its Standing instructions, §7.13–§7.16 and §10.**

Moved here from a Cowork (claude.ai) session on 28 Sep 2026; handoff Rev 1.4 describes the move.
This repo is now the master copy of the code. The copies in the claude.ai Project are snapshots.

## HARD RULE: verify the sources before making anything

James, 25 Sep 2026: *"there need to be hard rule set that you must check the data before making anything. As change
may have occur by engineer."*

On every run, before building or updating any file:
1. Re-read every source where it lives now: the calc workbooks (`CALC_DIR`), the day's scan, and the published masters
   in `PUBLISH_DIR`. Never build from a cached copy.
2. Compare them with the masters and the Change Log.
3. If something differs and has no Change Log entry, it is an unlogged change. **Stop**, list it for James, and
   overwrite nothing.
4. Only after James confirms: log it (date, who, why, old → new), then build.
5. Every output's Read Me lists its source files, their modified times and the pre-flight result.

How the code enforces it:
- Every input goes through `config.record_read()`, which writes it to `work/reads.json`.
- `publish.py` is the **only** way anything reaches `PUBLISH_DIR` or `DOCS_DIR`. It routes each file (database
  workbooks to their folder, the rest to the workspace) and refuses to replace a file unless that file's content is
  either what this build read or what we last published (`data/published_manifest.json`).
- There is no override. Never copy into `PUBLISH_DIR` by hand or edit files there directly. The one exception is
  the handoff `.md`, which you edit in place in `DOCS_DIR`.

## Hardcoded rules

Change these only with James's explicit say-so, and log the change in the handoff revision history.

- **R1**: an extrusion line code is 2 letters + 2 digits.
- **R2**: a material spec is letter + number (`R1R1R1`); `RD`/`RM` are accepted but always flagged.
- R1 and R2 live in the "DO NOT REMOVE" block of `scan_reader/ext_scan_reader.py`, and must match the §7.6 table.
- **Dosing (James, 26 Sep 2026).**
  - Weight blenders: SE24, SE42, SE43, SE61 (Lines 7, 12, 13, 16). Set is weight %, each extruder adds to 100, and
    `Auto` is the balance.
  - Auger lines: every other line. Set is motor speed 0–100 with no RPM feedback, it never adds to 100, and weight %
    exists only as slope × setting.
  - The `DOSING` table is in both `daily/load.py` and `calc/auger_rules.py`. The tests fail if the two differ.
- **Auger hopper roles** are a draft awaiting James (§10 Q13): `RULES` in `calc/auger_rules.py`, checks A1–A7
  (§7.14, §7.16).
  - *Read the function, not the number*: hopper numbers mean different things on different lines.
  - The slope follows the material and the hopper together.
- **Every formulation, in order (James, 29 Sep 2026).** When the pipeline gives an order its formulation (FRM Draft,
  interface, any later renderer), it gives **all** of that order's formulas in the listed order: reclaim versions
  first, the virgin-resin fallback last. Never just the primary. Test `test_draft_keeps_every_formulation`.
- **Customer-specific formulas get their own codes (James, 29 Sep 2026)**, instead of a shared code plus a note
  (VOIDFORM, sign blank, corn box, roll). The list is parked in `ui/customer_formulas.json` until James names them;
  do not invent codes.
- **Always the up-to-date formulation (James, 30 Sep 2026).** *"Always provide up to date formulation. even if someone
  give you an past schedule. If someone need an revision, they will put in an old schedule (usually previous day or if
  weekend, friday schedule)"*. The draft, the Word document and the interface use the **latest** issued formulation on
  file for each order on its line, whatever the schedule's date (`resolve.issued_history` with no cut-off).
  `HISTORY_BEFORE` is for backtests only. Test `test_past_schedule_gets_the_latest_formulation`.
- **Product code and order number are hard rules (James, 30 Sep 2026)**, in `product_code.py`, used by the checks,
  the Product Master build, the scan readers and the interface. Product code = family (3 letters) + thickness (digit 1-9
  or letter, then a digit: 10 = 1 mm, 90 = 9 mm, 63 = 6.3 mm, A0 = 10 mm, B0 = 11 mm; *"AQ is incorrect from the
  start"*) + colour (2 letters from the colour list; *"WB. WR dont exist"*) + product number (*"just number ... No english
  characters"*). Order number = H + 2 digits + letter + 3 digits, or RP + 2 digits + (digit or A-C) + 2 digits, then
  -suffix. A code breaking the rule never enters the Product Master (`build_master.py` refuses it; a letter O read for
  a zero is repaired and merged, as DPPAOKS27 -> DPPA0KS27). *"these need to be hard rule. If anything odd is spotted,
  recheck the OCR again"*: a reader re-reads an odd cell with other settings; what stays odd is never taken, it is boxed
  for a person, and the interface's Word download stays locked until every boxed row is confirmed (a correction must keep
  the rules and the product must be in the Product Master). Tests `test_product_code.py`; the real-scan reader test
  `OCR_TESTS=1 python -m pytest tests/test_scan_reader_page.py` (run it whenever the reader changes).
- **Never auto-issue a formula the pipeline guessed.** Anything not matched exactly goes to an engineer. Every
  output is a draft until Tech signs it.

## Never

- Edit Tech's calc workbooks, the Word formula books, or the Technical controlled documents (IWPFT…, IWPFM…).
  They are read only.
- Open files that hold passwords (e.g. "Blending system Weight Calibration Password.doc"). `.claude/settings.json`
  denies `*Password*`.
- Rewrite past records: `data/packets/*.json`, `daily/manual/manual_issues_<date>.py` and published daily
  workbooks stay as issued. `publish.py` refuses an earlier day's workbook; use `--reissue` only if James asks.
- Write a guessed identifier (order, product, formula code, material) as fact. Flag it instead.
- Pick spreadsheet columns by position. Always select by header name.
- Build the six target files (§7.13) before James says go. (Go given 28 Sep 2026 for the three records and the
  Formulation Master; the Auger Calibration master waits for Tech's calc workbooks.)
- Rewrite a master (`Formulation Master.xlsx`, later `Auger Calibration.xlsx`). People edit it in Excel and log each
  change in its Change Log; `db/preflight.py` checks. The pipeline only proposes changes (Issues), never applies them.
  `db/seed_master.py` was the one-time Draft seed (28 Sep 2026): do not run it against a published master.

## Layout

| Path | What |
|---|---|
| `config.py` | Paths (env var → `local_settings.json` → default in repo); `record_read`, `content_hash` |
| `publish.py` | out/ → PUBLISH_DIR/<folder> (database) or DOCS_DIR (workspace), with the hard-rule guard and verify-after-copy |
| `daily/` | Packet JSON → EXT / CNV / FRM workbooks (`build_xlsx.py`, `checks.py`) and Product Master merge (`build_master.py`) |
| `daily/manual/` | Hand-found issues per day (`manual_issues_<date>.py`) |
| `daily/cfg/` | Read Me notes per day (`cfg_<date>.json`) |
| `calc/` | Tech's `SExx Formulation.xls` → `Formulation Calc Library.xlsx` (`parse_fcal.py` → `export_calc_products.py` → `build_formulation_master.py`); `auger_rules.py` |
| `db/` | `schema.py`: the database described once (workbooks, sheets, columns, keys); `templates` / `check <file>` / `doc`. `preflight.py`: master change control (`check` / `accept`; accepted versions in `data/snapshots/`). `seed_master.py`: one-time Draft seed. Flow and maintenance in `docs/DATABASE.md` (§3, §7) |
| `product_master/` | `prepare.py`: Product Master → `Product Master - Prepared <date>.xlsx` (code-derived columns, Issues, Verify First, Colour Codes, Import Map; §7.18). A working file, not published |
| `scan_reader/` | `ext_scan_reader.py` (EXT scan reader, R1/R2 hardcoded, `glyph_bank.npz`); `render_pages.py` (page PNGs + quarter tiles for reading) |
| `data/packets/` | Transcribed daily packets `packet_YYYY-MM-DD.json` (`packet_date`, `source_scan`, `ext`, `cnv`, `frm`) |
| `data/` | `ext_truth_2026-09-23.csv` (82 verified EXT rows), `published_manifest.json` |
| `tests/` | `python -m pytest -q` (regression against the 23 and 24 Sep packets) |
| `inputs/`, `work/`, `out/` | Not in git: local inputs, intermediate files, staged outputs |

## Daily run (James sends the day's scan)

Commands are for Claude Code's shell (Git Bash). In PowerShell use `$env:PKT_DATE="2026-09-28"` instead of the prefix.
**Use the repo's virtual environment:** on Windows, `python` below means `.venv/Scripts/python`
(e.g. `.venv/Scripts/python -m pytest -q`).

0. **Pre-flight the masters:** `python db/preflight.py check "Formulation Master.xlsx"`. Exit 1 = someone changed the
   master without an approved Change Log row: **stop**, list the changes for James, build nothing. When every change
   is logged and approved, `python db/preflight.py accept "Formulation Master.xlsx"` and commit `data/snapshots/`.
   Then `python db/sync_iwpft062.py`: **IWPFT062 is the authority for materials** (James, 29 Sep 2026: *"doc T062 is
   correct. Master should match it"*). Any difference -> `--apply` (logged under James's standing rule), publish,
   pre-flight, accept. If IWPFT062 is locked (open in Word), say so and run it again later.
1. Put the scan in `SCAN_DIR`, then run `python scan_reader/render_pages.py <scan.pdf>`.
   - Read every page image (use the quarter tiles for small print).
   - Transcribe EXT, CNV and FRM into `data/packets/packet_YYYY-MM-DD.json`, using the previous day's file as the
     schema.
   - **Take every value from today's image; never carry one over.** Copy values exactly as printed; nothing is
     corrected.
   - Set `packet_date` and `source_scan`.
2. Run an independent check of the EXT key fields:
   `python scan_reader/ext_scan_reader.py read <scan.pdf> scan_reader/glyph_bank.npz work/ext_read_<date>.csv`.
   Every difference from your transcription gets settled by looking at the page again.
3. Hand-found issues:
   - Copy yesterday's `daily/manual/manual_issues_<date>.py` to today's date.
   - Do not carry forward issues for materials in `checks.REPLACED` (Q1203K, F1102K): the checks note them as Info.
   - Do not add manual issues for one code with several recipes ("two formulas with no note"): reclaim first, then
     the next listed, is the plant's rule (James, 29 Sep 2026); `checks.py` marks these Info.
   - Keep only what is still true on today's pages, then add the new issues.
   - Optional Read Me notes go in `daily/cfg/cfg_<date>.json`.
4. Build the workbooks: `PKT_DATE=<date> python daily/build_xlsx.py`. This makes the EXT, CNV and FRM workbooks in
   `out/` and runs every check.
5. Merge into the Product Master: `PKT_DATE=<date> python daily/build_master.py`. It merges into the *published*
   master and records what it read.
6. Read the Issues sheets. Tell James about anything **High** before publishing.
7. Publish: `python publish.py "EXT Extrusion Schedule <date>.xlsx" "CNV Converting Schedule <date>.xlsx" "FRM Formulation Report <date>.xlsx" "Product Master.xlsx"`.
   Then append the day to the three records and publish them:
   `python daily/record.py <date>` and
   `python publish.py "Formulation Report Record.xlsx" "Extrusion Production Record.xlsx" "Converting Production Record.xlsx"`.
   The records are append-only: a date already recorded is skipped if identical; if it differs the script stops.
8. When Tech's FRM pages are in the packet: `python db/import_frm.py --date <date> --by .. --why ..` adds the formulas,
   line settings and product-to-formula rows the Formulation Master lacks, as Draft rows logged in its Change Log
   (James, 29 Sep 2026: *"update your data base with it"*). It never changes a setting (differences are listed) and
   never writes an unmapped material (add the spelling in Materials with `db/edit_master.py` first). Then publish,
   `db/preflight.py check` / `accept`.
9. Interface copy (James, 29 Sep 2026: *"lets keep a copy create a separate folder in the fomulation record for now to
   hold these file. No Tech sign off require"*): `PKT_DATE=<date> python ui/build.py`, then
   `python publish.py "Profile Formulation <date>.html"` (Daily Formulation Report/Interface Copy) and republish the
   artifact from `out/profile-formulation.html`.
10. Run `python -m pytest -q`, then commit the packet JSON, the manual issues and `data/published_manifest.json`.
11. Handoff: add the day's notes (as in §7.10) and a revision-history row.

## Print formulation for the floor (an engineer sends the schedule scan)

James, 29 Sep 2026: *"operator will use the paper copy. So whenever i or any other engineer scan you the production
schedule. you will product a word formulation document for us to print out"*.

1. Transcribe the EXT schedule into the packet (Daily run step 1; FRM pages are not needed for this).
2. `PKT_DATE=<date> python daily/resolve.py` (FRM Draft: every order as last issued on its line, or an Exception).
3. `PKT_DATE=<date> python daily/auger_check.py`: every hopper setting on an auger line against the draft hopper
   rules (Q13); list anything outside them for James. Slopes are not checked until the Auger Calibration master exists.
   Then `PKT_DATE=<date> python daily/render_frm.py` -> `out/FRM Formulation <date>.docx`. Send it to the engineer.
   - It is a **DRAFT** while any order is an Exception: that row prints "ENGINEER TO COMPLETE", never a suggestion.
   - IWPFO055 §5.3: Technical issues it (cover issue block); a copy goes in the Schedule binder (§5.4).
   - Every formulation of an order, in run order (reclaim first); replaced materials printed as what to load.
4. The engineer completes each Exception **in the database** (James, 29 Sep 2026: *"this allow the engineer to update
   the data base and trigger a re run"*): approved Product to Formula rows in the Formulation Master, in Excel with a
   Change Log row, or through `python db/assign_formula.py --line .. --product .. --by .. --why .. --formula CODE VARIANT ...`
   (run order: reclaim first, run-out last). Then publish the master, `db/preflight.py check` / `accept`, and re-run
   steps 2-3: `resolve.py` uses the last issue for the order first, then **approved** Product to Formula rows (never
   Draft ones). When no Exception is left the document reads READY TO ISSUE; publish the issued copy with
   `python publish.py "FRM Formulation <date>.docx"` (Daily Formulation Report folder).
5. The Formulation Report Record takes a day only when its formulation is issued. On a schedule-only packet
   (no Tech FRM pages) `record.py` appends EXT and CNV and skips FRM; the FRM rows follow once the document is issued.

## Calc workbooks → Formulation Master (when Tech's workbooks change)

1. `python calc/parse_fcal.py` reads every `*Formulation*.xls` in `CALC_DIR` and records each one.
2. `python calc/export_calc_products.py`.
3. `PKT_DATE=<latest packet date> python calc/build_formulation_master.py`.
4. Check the Issues sheet, then run `python publish.py "Formulation Master.xlsx"`.
5. To bring the calc data into the Product Master:
   `PKT_DATE=<date> CALC_JSON=work/calc_products.json python daily/build_master.py`.

## Before you finish any change

- `python -m pytest -q` passes.
- The handoff is updated:
  - write what changed and why in plain words;
  - quote James verbatim when he sets a rule;
  - add a revision-history row;
  - update the §11 checksum manifest when published files changed.
- Tell James the handoff changed; Cowork sessions mirror it to the claude.ai Project.
- Commit with a message that says why.

## Output conventions

- `.xlsx` for tables.
- Every workbook has two sheets beyond the data:
  - a **Read Me**: sources, modified times, pre-flight result;
  - an **Issues** sheet with columns Severity (High / Medium / Low / Info), Document, Line, Order, Check, Detail,
    Source and "James / Tech response".
- Values are copied as printed. Problems are listed, never silently fixed.
- Arial 10; header fill `1F3864` with white bold text.
- `.xlsx` files are compared by cell content (`config.content_hash`), because SharePoint rewrites their metadata on
  upload.

## Where other work happens

Cowork (claude.ai) keeps SharePoint and Outlook through the Microsoft 365 connector, the claude.ai Project mirror of
the handoff, and design discussions with James. Open questions are in §10 (Q2–Q21).
