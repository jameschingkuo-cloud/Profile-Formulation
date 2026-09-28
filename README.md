# Formulation pipeline: setup

This is the code for the Production Formulation Automation project, packaged on 28 Sep 2026 so that Claude Code can
work on it in a folder on your PC. What the project does, the rules and the open questions are in the handoff
document in the SharePoint folder. `CLAUDE.md` is the short version that Claude Code reads at the start of every
session.

## 1. Install (once)

| What | Why | Where |
|---|---|---|
| Python 3.11 or newer | Runs the scripts | python.org → Downloads → Windows installer. Tick **"Add python.exe to PATH"** |
| Git for Windows | Version history. Claude Code on Windows also needs it | git-scm.com |
| Claude Code | Works on this folder | The **Code** tab of the Claude desktop app (or the installer on claude.com/code) |
| Tesseract OCR (optional) | Only for the scan reader's independent EXT check | The Windows installer from UB Mannheim (github.com/UB-Mannheim/tesseract). If it isn't at `C:\Program Files\Tesseract-OCR`, fix `TESSERACT_CMD` in `local_settings.json` |

No PDF tools are needed: pages are rendered with PyMuPDF, which pip installs.

If Inteplast IT has to approve installs, the first three are the ones to ask for.

## 2. Put the folder in place

1. Unzip to **`C:\Users\JamesKuo\dev\formulation-pipeline`**, or any folder **outside** OneDrive and SharePoint.
   Syncing and git don't mix. The finished workbooks still go to SharePoint, through `publish.py`.
2. Open PowerShell in that folder and run:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
git init
git config user.name "James Kuo"
git config user.email "JKUO@wpjk.inteplast.com"
git add -A
git commit -m "Starter from Cowork, 28 Sep 2026"
```

3. Check `local_settings.json`. It already points at your SharePoint-synced
   `...\Engineering Pipeline\Production Formulation Automation` folder.
4. Copy Tech's calc workbooks (the 14 `.xls` you uploaded on 25 Sep) into `inputs\calc`. Once we know where Tech saves
   them (handoff §10 Q14), set `CALC_DIR` to that folder instead.
5. Test:

```powershell
.venv\Scripts\python -m pytest -q
```

All tests should pass: 8 with the calc workbooks in `inputs\calc`, 7 plus 1 skipped without them.

## 3. Open it in Claude Code

In the Claude desktop app, go to **Code**, choose this folder, and approve the folder when Claude Code asks you to
trust it. That's what lets it read the SharePoint folder named in `.claude/settings.local.json`.

A good first message:

> Read CLAUDE.md and the handoff. Run the tests. Then tell me what is open in §10 and what you would do first.

## Everyday use

- **Daily packet:** give Claude Code the day's scan and say "run the daily packet for <date>". It follows the steps
  in `CLAUDE.md`: transcribe, cross-check, build, check, publish, commit.
- **Tech changed a calc workbook:** say "rebuild the Formulation Master". The hard rule makes it list what changed and
  wait for your OK before anything is published.
- **Nothing reaches SharePoint** until `publish.py` runs. If someone has edited a published file, `publish.py` refuses
  and says which one.
- SharePoint, Outlook and the claude.ai Project mirror stay in Cowork.

## What is where

| Path | Contents |
|---|---|
| `daily/` | Packet → EXT / CNV / FRM workbooks and Product Master |
| `calc/` | Calc workbooks → Formulation Master; auger rules |
| `scan_reader/` | EXT scan reader and page renderer |
| `data/` | Transcribed packets, verified EXT rows, publish manifest |
| `tests/` | Regression tests |
| `publish.py`, `config.py` | Publishing with the hard-rule guard; paths |
