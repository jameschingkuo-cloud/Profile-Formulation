"""The first and, most of the time, only step of the scheduled email run (James Kuo, 6 Oct 2026: "Check the email. Only
run the rest of the program if there is new email. If not, no need to run the rest of the pipeline"; "make sure the run
time is set to 30 minutes. So if there is email that is within the previous and the current 30 minutes run, that's when
the email attachment need to be pulled. But if ... there's no email between the 30 minutes, then the program ...
automatically ended with" "No new email in system").

    python daily/schedule_gate.py            check: last line "gate: run" or "gate: skip (...)"
    python daily/schedule_gate.py --done     at the end of a run that went on: its emails are handled, lock removed
    python daily/schedule_gate.py --test-at "2026-10-06 13:30" [--since "2026-10-06 13:00"]
                                             a check as if made then (no 16:20 cut-off, nothing recorded, no lock)

Check, in this order, and stop at the first that says skip:
  - after 16:20 local: skip (the 16:30 tick of the */30 11-16 schedule);
  - work/schedule_run.lock less than 90 minutes old: skip (a run is working);
  - Johanna Vallejo's emails received since the previous check (work/schedule_last_check.txt; 30 minutes back when there
    is none), through daily/fetch_schedule_mail.ps1 -Since/-Until, which saves only those emails' PDFs to Downloads.
    None: "gate: skip (No new email in system ...)". The check's time is recorded, so the next window starts here: every
    email falls in exactly one window, also those that came in after 16:20 or overnight (the 11:00 check takes them).
    The mail check failed (Outlook): "gate: error (...)", and the window is not moved on.
Otherwise: "gate: run", the new emails and their dates' daily/schedule_status.py lines, and the lock is written (it holds
the new emails). The run ends with --done (also when it stops on purpose): its emails go in work/schedule_mail_handled.json,
so one that a window caught twice is not run twice. A lock-skipped check does not move the window: an email that comes
in while a run is working is taken by the next check.
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
LAST = config.WORK_DIR / 'schedule_last_check.txt'
LATE = datetime.time(16, 20)
LOCK_MINUTES = 90
WINDOW = datetime.timedelta(minutes=30)
FMT = '%Y-%m-%d %H:%M:%S'
NONE = 'No new email in system'


def window_dates(since, until):
    d, out = since.date(), []
    while d <= until.date():
        out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def fetch(since, until, wait=30):
    """-> [(status, file, subject, received)] for the PDF attachments of the emails received in [since, until)."""
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'daily' / 'fetch_schedule_mail.ps1'), '-Date', ','.join(window_dates(since, until)),
                        '-Since', since.strftime(FMT), '-Until', until.strftime(FMT), '-WaitSeconds', str(wait)],
                       capture_output=True, text=True, errors='replace', timeout=240)
    rows = []
    for line in r.stdout.splitlines():
        parts = [p.strip() for p in line.split('|')]
        if len(parts) == 4 and parts[0] in ('saved', 'saved-resent', 'already'):
            rows.append(tuple(parts))
        elif parts and parts[0] == 'warning':
            print(line)
    if r.returncode:
        raise RuntimeError(f'exit {r.returncode}: {r.stderr.strip()[:300]}')
    return rows


def key(row):
    status, f, subject, received = row
    return f'{received} | {subject.strip()} | {Path(f).name}'


def ledger():
    return json.loads(LEDGER.read_text(encoding='utf-8')) if LEDGER.exists() else {}


def last_check(now):
    try:
        return datetime.datetime.strptime(LAST.read_text(encoding='utf-8').strip(), FMT)
    except (OSError, ValueError):
        return now - WINDOW


def check(now=None, since=None, test=False):
    now = now or datetime.datetime.now().replace(microsecond=0)
    if not test and now.time() > LATE:
        return 'gate: skip (after 16:20)'
    if not test and LOCK.exists() and (now.timestamp() - LOCK.stat().st_mtime) < LOCK_MINUTES * 60:
        return f'gate: skip (a run is working since {json.loads(LOCK.read_text(encoding="utf-8"))["started"]})'
    since = since or last_check(now)
    try:
        rows = fetch(since, now)
    except RuntimeError as e:
        return f'gate: error (the mail check failed, {e})'
    if not test:
        LAST.write_text(now.strftime(FMT), encoding='utf-8')
    span = f'{since:%Y-%m-%d %H:%M} to {now:%H:%M}'
    if not rows:
        return f'gate: skip ({NONE}: no email from Johanna Vallejo {span})'
    seen = ledger()
    new = [r for r in rows if key(r) not in seen]
    for r in rows:
        print(f'email {r[3]}: {r[2]} -> {r[1]} [{r[0]}]' + ('' if r in new else ' (handled before)'))
    if not new:
        return f'gate: skip ({NONE}: the email(s) {span} were handled already)'
    from schedule_status import status
    for d in sorted({r[3][:10] for r in new}):
        print(f'{d}: next {status(d)["next"]}')
    if test:
        return 'gate: run (test: nothing recorded, no lock)'
    LOCK.write_text(json.dumps({'started': now.strftime(FMT), 'emails': [key(r) for r in new]}, indent=1),
                    encoding='utf-8')
    return 'gate: run'


def done():
    """Marks the emails this run's gate let through (kept in the lock) as handled, and removes the lock."""
    if not LOCK.exists():
        print('no lock: nothing to mark'); return
    emails = json.loads(LOCK.read_text(encoding='utf-8')).get('emails', [])
    seen = ledger()
    stamp = datetime.datetime.now().strftime(FMT)
    for k in emails:
        seen.setdefault(k, stamp)
    LEDGER.write_text(json.dumps(seen, indent=1, sort_keys=True), encoding='utf-8')
    LOCK.unlink()
    print(f'handled: {len(emails)} email attachment(s); lock removed')


def main(argv):
    if '--done' in argv:
        return done()
    at = lambda s: datetime.datetime.strptime(s if len(s) > 16 else s + ':00', FMT)  # noqa: E731
    if '--test-at' in argv:
        now = at(argv[argv.index('--test-at') + 1])
        since = at(argv[argv.index('--since') + 1]) if '--since' in argv else now - WINDOW
        print(check(now=now, since=since, test=True))
    else:
        print(check())


if __name__ == '__main__':
    main(sys.argv[1:])
