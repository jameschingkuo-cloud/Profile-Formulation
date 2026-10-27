"""The rules' answer for every schedule on file, for the page's Generate box (James Kuo, 24 Oct 2026, open item "Small
fixes pending": the Generate box showed the rules' answer only for the day the page was built).

    python ui/rules_days.py [day ...]        -> work/rules/FRM Draft <day>.xlsx for every packet date (or the days given)

Each day is the daily run's resolve.py on that day's schedule with the rules and settings as they are now (always the
latest formulation, even for a past schedule), written to work/rules/ so out/ and the issued copies stay as they are.
About 30 s a day; run it after a rule change, then ui/build.py. The page says which rules date each answer is from.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

RULES_DIR = ROOT / 'work' / 'rules'


def main(days):
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config.OUTPUT_DIR / 'Formulation Calc Library.xlsx', RULES_DIR / 'Formulation Calc Library.xlsx')
    if not days:
        days = sorted(json.loads(p.read_text(encoding='utf-8'))['packet_date'] for p in config.PACKETS_DIR.glob('packet_*.json'))
    env = dict(os.environ, PYTHONUTF8='1', OUTPUT_DIR=str(RULES_DIR))
    env.pop('HISTORY_BEFORE', None)
    for d in days:
        r = subprocess.run([sys.executable, str(ROOT / 'daily' / 'resolve.py')], env=dict(env, PKT_DATE=d),
                           capture_output=True, text=True, cwd=ROOT)
        print(d, (r.stdout.strip().splitlines() or [''])[0] if r.returncode == 0 else 'FAILED: ' + (r.stderr.strip().splitlines() or [''])[-1])


if __name__ == '__main__':
    main(sys.argv[1:])
