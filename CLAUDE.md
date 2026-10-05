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
  characters"*). Order number (`order_number.py`, read from the system's own schedules 2020-2026, 30 Sep 2026) = H +
  year digit + month (1-9, A, B, C) + A + 3 digits (H69A039, H6AA001), SH + year digit + month + A + 2 digits (SH69A04),
  or RP + 2-digit year + month + 2 digits (RP26821, RP24C18), then -suffix (1-2 digits); never dated after its schedule;
  H/SH under 2 years old. A reading dated impossibly is no reading, unless its month has a possible look-alike (B/8,
  A/4), which is then taken only on file or when the other reader read it. A code breaking the rule never enters the Product Master (`build_master.py` refuses it; a letter O read for
  a zero is repaired and merged, as DPPAOKS27 -> DPPA0KS27). *"these need to be hard rule. If anything odd is spotted,
  recheck the OCR again"*: a reader re-reads an odd cell with other settings; what stays odd is never taken, it is boxed
  for a person, and the interface's Word download stays locked until every boxed row is confirmed (a correction must keep
  the rules; a product not yet in the Product Master is accepted as a new product). Tests `test_product_code.py`; the real-scan reader test
  `OCR_TESTS=1 python -m pytest tests/test_scan_reader_page.py` (run it whenever the reader changes).
- **Scan reader: two readers must agree, border lines isolate the row, handwriting is ignored (James, 30 Sep 2026)**.
  `ui/ocr_eval.py` (`audit3`) is the reference; the page runs the same reader (`ui/reader.js`, inlined by `ui/build.py`;
  glyph bank shipped as `glyph-bank.js`). A row band holding a solid border line with notes above it is cut along the
  line and only the printed side (the one with the '|' bars) is read. Each cell is read by Tesseract (cleaned cell) and
  by the glyph bank; a row is taken only when an order + product on file matches or both readers agree on both values.
  A product not in the Product Master (a new product) is taken only when both readers read the same rule-keeping code with
  the glyph reader NOT snapped to the master, and both read the same order; a boxed row never shows a master code the
  paper does not show. A border printed on a tilt is erased as long runs (30 Sep 2026, H69A330-11). After a reader change,
  test the built page in Chrome on the day's real PDF as well (James, 30 Sep 2026: "remember to test it with chrome").
  The line code needs two independent readings (header, footer, glyph) or the page continues its neighbour's line (no
  footer); else the page's rows are boxed. Change the reference first, then the page, and keep the parity test (page =
  reference on every row) at 0 differences. Publish `glyph-bank.js` and `eng-data.js` with the page.
- **The system's own past schedules (James, 30 Sep 2026: "i got the past production schedule ... refine your data
  base")**: `Profile Process Control - Documents/Technical Engineering Team/Production Instruction/MMDDYY.pdf` are the
  AIX report as text (no OCR): `python history/prod_instr.py parse` -> `work/history/ext_history.csv`;
  `python history/analyze.py` (rules and master vs history, read-only). They feed the Product Master (`HIST_CSV=` in
  `build_master.py`: latest run fills blanks, a difference is a Check note, never an overwrite; column Last Scheduled),
  the Extrusion Production Record (`python daily/record.py --history <csv>`: days not recorded yet; recorded days stay
  as issued), and the page's order history (`hist_pairs`, last 2 years of the record). A line printed again later the
  same day is the revision. Every line must add up to the line total the report prints (`footer_check`; a file is dated
  by its Run Date; rotated prints are read by `grid_any`). Days kept only as scans are read by eye against the days either
  side and must add up to the printed totals (`history/image_days_manual.py`, converting sheets `history/cnv_scans.py` ->
  `record.py --history-cnv`). The HR forms, photos and other business documents in that folder are not opened (James).
  When new PDFs land: `prod_instr.py parse`, then
  `record.py --history work/history/ext_history.csv work/history/ext_history_scans.csv --replace-history` and
  `HIST_CSV="work/history/ext_history.csv;work/history/ext_history_scans.csv"` for `build_master.py`.
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
| `daily/` | Packet JSON → EXT / CNV / FRM workbooks (`build_xlsx.py`, `checks.py`) and Product Master merge (`build_master.py`); the two-step scan read (`stage1_formulation.py`, `stage2_records.py`) |
| `daily/manual/` | Hand-found issues per day (`manual_issues_<date>.py`) |
| `daily/cfg/` | Read Me notes per day (`cfg_<date>.json`) |
| `calc/` | Tech's `SExx Formulation.xls` → `Formulation Calc Library.xlsx` (`parse_fcal.py` → `export_calc_products.py` → `build_formulation_master.py`); `auger_rules.py` |
| `db/` | `schema.py`: the database described once (workbooks, sheets, columns, keys); `templates` / `check <file>` / `doc`. `preflight.py`: master change control (`check` / `accept`; accepted versions in `data/snapshots/`). `seed_master.py`: one-time Draft seed. Flow and maintenance in `docs/DATABASE.md` (§3, §7) |
| `product_master/` | `prepare.py`: Product Master → `Product Master - Prepared <date>.xlsx` (code-derived columns, Issues, Verify First, Colour Codes, Import Map; §7.18). A working file, not published |
| `scan_reader/` | `ext_scan_reader.py` (EXT scan reader, R1/R2 hardcoded, `glyph_bank.npz`); `ext_fields.py` (step 2: every other EXT column by printed column, `glyph_bank_fields.npz`); `validate_read.py`, `instructions.py` (logic checks); `render_pages.py` (page PNGs + quarter tiles for reading) |
| `history/` | The system's own past extrusion schedules (Production Instruction PDFs): `prod_instr.py` (parse), `analyze.py` (findings) |
| `order_number.py`, `product_code.py` | The order-number and product-code hard rules (used by checks, readers, masters) |
| `ui/` | The interface page: `build.py` (data + `page.template.html` + `reader.js` → `out/profile-formulation.html`, `eng-data.js`, `glyph-bank.js`); `reader.js` (the page's scan reader); `ocr_eval.py` (the reference reader, `audit3`, `dump_parity`) |
| `data/packets/` | Transcribed daily packets `packet_YYYY-MM-DD.json` (`packet_date`, `source_scan`, `ext`, `cnv`, `frm`) |
| `data/` | `ext_truth_2026-09-23.csv` (82 verified EXT rows), `published_manifest.json` |
| `tests/` | `python -m pytest -q` (regression against the 23 and 24 Sep packets); `OCR_TESTS=1` for the real-scan reader tests; `tests/js/reader_parity.js` (page reader vs reference) |
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
   `python scan_reader/ext_scan_reader.py read <scan.pdf> scan_reader/glyph_bank.npz work/ext_read_<date>.csv`, then the
   logic checks `python scan_reader/validate_read.py <date> work/ext_read_<date>.csv work/ext_valid_<date>.csv` (repairs
   only from a single consistent candidate, each with its reason: handwriting read as a row, an order or product under
   handwriting from the previous schedule day, thk from the product code, a die look-alike to the line's die, a number not
   read in an instruction). Special instructions are snapped to the lines the system really prints
   (`scan_reader/instructions.py`, from the system schedules). Every difference from your transcription gets settled by
   looking at the page again. With the system PDF: `python scan_reader/score_vs_pdf.py <csv> <pdf>` scores the read.
   When the system's own PDF of the day's report is available (`BPN9PFR*.PDF`, the text the paper is printed from), run
   `python scan_reader/verify_with_system_pdf.py <date> <pdf>`: the PDF is the authority for printed text, the scan adds
   only handwriting. A comma and a period cannot be told apart on the scan, and printed text under handwriting is still
   printed (James, 1 Oct 2026: *"confirm your scan file is rock solid"* - 30 Sep: 1,825 of 1,827 fields identical; the 2
   were such calls made at zoom).
3. Hand-found issues:
   - Copy yesterday's `daily/manual/manual_issues_<date>.py` to today's date.
   - Do not carry forward issues for materials in `checks.REPLACED` (Q1203K, F1102K): the checks note them as Info.
     F1203K is the material in use; Tech's FRM pages still print F1102K / Q1203K because the engineer database is out
     of date (James, 30 Sep 2026: "ignore that ... Your data is correct with F1203K"). Not a difference to report.
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
   artifact from `out/profile-formulation.html` (read "The interface artifact" below first).
10. Run `python -m pytest -q`, then commit the packet JSON, the manual issues and `data/published_manifest.json`.
11. Handoff: add the day's notes (as in §7.10) and a revision-history row.

## The interface artifact: what went wrong before (read before changing, testing or publishing it)

James, 5 Oct 2026: *"remember you had some trouble with document uploading into artificat? Can you make sure you
document it in your MD so other can learn from you?"*. The page is https://claude.ai/artifact/1kSFUwuS1GUeiG13twAw5j
(built by `ui/build.py`; handoff §7.46, §7.49, §7.53).

**Uploading a schedule PDF into the page (29 Sep 2026)**
- *The drop box went grey with a stop-sign cursor.* The page sent page images to Claude (`sample` capability), and
  James's account does not let an artifact send images to Claude, in Chrome or in the app. The reason showed only in
  small text beside the box, cut off in his screenshot. First fix: say inside the box why it is unavailable, and do not
  block on a failed capability check (`5bfdad7`). Real fix: the page reads the scan itself (Tesseract 5 through
  tesseract.js-core, plus the plant's glyph bank). Nothing is uploaded anywhere, and it works for anyone the page is
  shared with. Do not build a feature that depends on sending images to Claude from the page.
- *An artifact page may load scripts from the allowed CDNs (jsDelivr ...) but cannot fetch data files.* So Tesseract's
  language data ships as a script, `eng-data.js` (gzip + base64), and the glyph bank as `glyph-bank.js`, both published
  next to the page with the Artifact tool's `files`. Files left out of a later publish are kept: send them again only when
  they change. `eng-data.js` is built once (tessdata_fast) and does not change; `glyph-bank.js` changes with
  `scan_reader/glyph_bank.npz`.
- *pdf.js hung drawing the copier's scans inside the artifact frame.* A copier PDF is one JPEG per page, so the page takes
  the JPEGs straight out of the file and never renders the PDF.
- *Downloads.* The Word file leaves the page through the declared `downloads` capability (the viewer confirms each save).
  Chrome blocks downloads started by automation, so the first real Save prompt is the user's; to test the bytes, the page
  posted the file to a receiver on 127.0.0.1.

**Testing it in Chrome** (after every reader change; memory "test-reader-in-chrome")
- The artifact runs in a sandboxed frame. Automation cannot reach its file input, and the frame's address carries a
  private access token: never copy that address anywhere. Serve the built page (the `out/` files copied to the scratchpad)
  with `python -m http.server` on 127.0.0.1, together with a copy of the PDF.
- The upload tool takes files only from this session's folders and caps them at 10 MB. Hand the PDF to the page's file
  input from inside the page instead: fetch → `File` → `DataTransfer`.
- Python tests and the parity test do not catch page-only errors. Artifact v28 shipped broken (a variable used before it
  was set), and only the Chrome run caught it.

**Publishing a new version** (5 Oct 2026)
- Publish from the scratchpad copy: copy `out/profile-formulation.html` to `<scratchpad>/ui/profile-formulation.html` and
  publish that path with `url` set to the link above. Omit `capabilities` so the declared `sample` and `downloads` carry
  forward.
- In a new session, or after the conversation was compacted, the first publish is refused: *"You hadn't viewed the live
  version"*. The tool saves the live source to a `tool-results/artifact-*.html` file.
  1. Read that file with the Read tool, using offset/limit: one line near 350 holds the day's data (300,000-400,000
     characters).
  2. Compare it with the last build. The live copy is the last build plus the wrapper the host adds (doctype, head, a
     small style block), nothing else.
  3. Publish again.
- Checking the saved file only by script and resending is refused a second time (*"identical content already refused"*).
  The saved file must be opened with the Read tool. If someone edited the page in between, merge their changes first.

## When the day comes as the system's own PDFs (2 Oct 2026)

James sent `BPN9PFR$_*.PDF` (the AIX extrusion report itself) and `Die Cutting Schedule MM-DD.pdf` (the converting
schedule printed from Excel) instead of a scan. Both carry their text: nothing is OCR'd or transcribed by eye.
1. Step 1, formulation first: `python daily/packet_from_pdf.py <date> --ext <BPN9PFR pdf>` writes the packet's EXT part
   (refused unless every line adds up to its printed total), then pre-flight, `resolve.py`, `auger_check.py`,
   `render_frm.py` and send the Word file.
2. Step 2: `python daily/packet_from_pdf.py <date> --cnv <Die Cutting Schedule pdf>` adds the converting pages
   (`daily/cnv_from_pdf.py`: columns from the table's own lines, each cell's whole text from the PDF's drawing operations,
   also where the paper cuts it off; notes under / above a record and banners as the transcriptions record them).
   Then the Daily run from step 3 (manual issues, `cfg_<date>.json` with `source` and `transcribed_note` for the Read Me,
   workbooks, Product Master, publish, records, interface copy). No handwriting on a PDF: 'handwritten' stays empty.

## Print formulation for the floor (an engineer sends the schedule scan)

James, 29 Sep 2026: *"operator will use the paper copy. So whenever i or any other engineer scan you the production
schedule. you will product a word formulation document for us to print out"*.

**Two steps (James, 1 Oct 2026: *"do read all. But make it two step. Get the fomulation to production team first. then
read the rest for the data base update (Production Record)"* - *"this will reduce the wait time"*):**
- **Step 1, the formulation first (about a minute):** `python daily/stage1_formulation.py <scan.pdf> --date <date>`.
  The scan reader reads each EXT record's key fields (pages in parallel, no per-record instruction read), runs the
  logic checks (`validate_read.py`), writes `work/stage1/packet_<date>.json` (`"stage": 1`) and runs resolve,
  auger_check and render_frm -> `out/FRM Formulation <date>.docx` (footer: "step 1: read by the scan reader"). A row
  whose order or product the checks cannot confirm is an Exception, never a formula. Then steps 4-5 below as usual.
  The step-1 packet never goes in `data/packets`: records, masters and the reader's evaluation never read it.
- **Step 2, everything else for the database:** `python daily/stage2_records.py <scan.pdf> --date <date>` (about
  1.5 minutes) reads every EXT field: the key fields and instructions, and every other column by its printed column
  (`scan_reader/ext_fields.py`: the '|' bars of each record line place every glyph; sizes, cut rows, total sheets, pack,
  pallets, pieces, stacks, weight, in-str date, web width, the line totals; its own glyph bank `glyph_bank_fields.npz`,
  so the key-field and page readers are unchanged). Logic checks: printed forms, pallets x pieces vs sheets, weight vs
  size x GSM x sheets, web = whole cut widths, cut rows alike, 999 pallets, the previous transcribed day's same order,
  the printed line totals. Output `work/stage2/packet_<date>.json` with every note in the record's `unclear`. Settle each
  note at zoom, add the CNV (and any FRM) pages by eye (not read by the reader yet), save it as
  `data/packets/packet_<date>.json` without `"stage"`, then the Daily run from step 2 (system PDF, records).
  `--compare <date>` scores a step-2 read against a transcribed packet. Then
  `python daily/stage1_formulation.py --compare <date>`: exit 1 = step 1 read a line, order or product differently:
  re-run resolve / render_frm on the full packet and re-issue the formulation (tell James).
  Tests (1 Oct 2026): step 1 on 30 Sep, 87 of 87 orders identical to the PDF-corrected packet, about a minute. Step 2
  with a field bank that had not seen the day: 30 Sep and 24 Sep, every field of all 167 records right except special
  instructions under handwriting (flagged); the one line total not read is flagged.
  When a new day's system PDF arrives, add it to the field bank:
  `python scan_reader/ext_fields.py train <scan> <pdf> [<scan> <pdf> ...]` (all days) and measure with `loo`.

1. Transcribe the EXT schedule into the packet (Daily run step 1; FRM pages are not needed for this), or step 1 above.
2. `PKT_DATE=<date> python daily/resolve.py` (FRM Draft: every order as last issued on its line, or an Exception).
3. `PKT_DATE=<date> python daily/auger_check.py`: every hopper setting on an auger line against the draft hopper
   rules (Q13); list anything outside them for James. Slopes are not checked until the Auger Calibration master exists.
   Then `PKT_DATE=<date> python daily/render_frm.py` -> `out/FRM Formulation <date>.docx`. Send it to the engineer.
   - It is a **DRAFT** while any order is an Exception: that row prints "ENGINEER TO COMPLETE", never a suggestion.
   - IWPFO055 §5.3: Technical issues it (cover issue block); a copy goes in the Schedule binder (§5.4).
   - Every formulation of an order, in run order (reclaim first); replaced materials printed as what to load.
     Reclaim first whatever order Tech's page lists them (`resolve.run_order`, the page's `runOrder`); a formula without
     reclaim after one with reclaim prints "If reclaim runs out" (James Kuo, 30 Sep 2026: *"the one with reclaim first.
     we always want to use up our scrap first before using Virgin PP"*). Not an issue to raise when a page lists virgin first.
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
