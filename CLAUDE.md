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
   - Do not carry forward issues for materials in `checks.REPLACED` (e.g. Q1203K, XO-256): the checks note them as Info.
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
8. Run `python -m pytest -q`, then commit the packet JSON, the manual issues and `data/published_manifest.json`.
9. Handoff: add the day's notes (as in §7.10) and a revision-history row.

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
