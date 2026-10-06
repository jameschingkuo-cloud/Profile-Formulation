"""The first and, most of the time, only step of the scheduled email run (James Kuo, 6 Oct 2026: "Check the email. Only
run the rest of the program if there is new email. If not, no need to run the rest of the pipeline").

    python daily/schedule_gate.py            check: last line "gate: run ..." or "gate: skip (<why>)"
    python daily/schedule_gate.py --done     at the end of a run that went on: its emails are handled, lock removed

Check, in this order, and stop at the first that says skip:
  - after 16:20 local: skip (the 16:30 tick of the */30 11-16 schedule);
  - work/schedule_run.lock less than 90 minutes old: skip (a run is working);
  - the mail check itself failed (Outlook): "gate: error (...)";
  - the emails from Johanna Vallejo received today or on the previous weekday (daily/fetch_schedule_mail.ps1, which also
    saves their PDFs to Downloads): every one already in work/schedule_mail_handled.json -> skip.
Otherwise: "gate: run", the new emails and each date's daily/schedule_status.py line, and the lock is written (it holds
the new emails). An email counts as handled only when the run that took it says --done, so a run that died half-way is
tried again once its lock is 90 minutes old; a run that stopped on purpose (a new High, something for James) says --done
too, and is not repeated. An email that comes in while a run is working is left for the next tick.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'daily'))
import config  # noqa: E402

LOCK = config.WORK_DIR / 'schedule_run.lock'
LEDGER = config.WORK_DIR / 'schedule_mail_handled.json'
LATE = datetime.time(16, 20)
LOCK_MINUTES = 90


def dates(today=None):
    """Today and the previous weekday (Friday for a Monday)."""
    today = today or datetime.date.today()
    prev = today - datetime.timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= datetime.timedelta(days=1)
    return [prev.isoformat(), today.isoformat()]


def fetch(ds, wait=30):
    """-> [(status, file, subject, received)] for the schedule emails' PDF attachments on those dates."""
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'daily' / 'fetch_schedule_mail.ps1'), '-Date', ','.join(ds), '-WaitSeconds', str(wait)],
                       capture_output=True, text=True, errors='replace', timeout=240)
    rows = []
    for line in r.stdout.splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) == 4 and parts[0] in ('saved', 'saved-resent', 'already'):
            rows.append(tuple(parts))
        elif parts and parts[0] == 'warning':
            print(line)
    if r.returncode:
        raise SystemExit(f'gate: error (the mail check failed, exit {r.returncode}: {r.stderr.strip()[:300]})')
    return rows


def key(row):
    status, f, subject, received = row
    return f'{received} | {subject.strip()} | {Path(f).name}'


def ledger():
    return json.loads(LEDGER.read_text(encoding='utf-8')) if LEDGER.exists() else {}


def check(now=None):
    now = now or datetime.datetime.now()
    if now.time() > LATE:
        return 'gate: skip (after 16:20)'
    if LOCK.exists() and (now.timestamp() - LOCK.stat().st_mtime) < LOCK_MINUTES * 60:
        return f'gate: skip (a run is working since {json.loads(LOCK.read_text(encoding="utf-8"))["started"]})'
    ds = dates(now.date())
    rows = fetch(ds)
    seen = ledger()
    new = [r for r in rows if key(r) not in seen]
    if not new:
        return f'gate: skip (no new schedule email; {len(rows)} attachment(s) on {ds[0]}..{ds[1]} already handled)'
    from schedule_status import status
    for r in new:
        print(f'new email: {r[2]} ({r[3]}) -> {r[1]} [{r[0]}]')
    for d in ds:
        print(f'{d}: next {status(d)["next"]}')
    LOCK.write_text(json.dumps({'started': now.strftime('%Y-%m-%d %H:%M'), 'emails': [key(r) for r in new]}, indent=1),
                    encoding='utf-8')
    return 'gate: run'


def done():
    """Marks the emails this run's gate let through (kept in the lock) as handled; one that came in during the run
    stays new for the next tick."""
    if not LOCK.exists():
        print('no lock: nothing to mark'); return
    emails = json.loads(LOCK.read_text(encoding='utf-8')).get('emails', [])
    seen = ledger()
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    for k in emails:
        seen.setdefault(k, stamp)
    LEDGER.write_text(json.dumps(seen, indent=1, sort_keys=True), encoding='utf-8')
    LOCK.unlink()
    print(f'handled: {len(emails)} email attachment(s); lock removed')


if __name__ == '__main__':
    if '--done' in sys.argv[1:]:
        done()
    else:
        print(check())
