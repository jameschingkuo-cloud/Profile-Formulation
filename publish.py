"""Copy finished files from out/ to the SharePoint-synced folder (PUBLISH_DIR) - the only way outputs reach SharePoint.

    python publish.py "Product Master.xlsx" "FRM Formulation Report 2026-09-28.xlsx" ...
    python publish.py --check            (report what would be refused, copy nothing)
    python publish.py --reissue "FRM Formulation Report 2026-09-24.xlsx"   (replace an earlier day's workbook - only when James asks)

HARD RULE (James Kuo, 25 Sep 2026): "there need to be hard rule set that you must check the data before making anything.
As change may have occur by engineer."  So before replacing a file that is already in PUBLISH_DIR, this script checks
that its content is one we know:
  - the content a build read this run (work/reads.json, e.g. the prior Product Master), or
  - the content we last published (data/published_manifest.json, kept in git).
Anything else means someone edited the published file since: the script STOPS and copies nothing. Merge or log the
edit first (handoff Change Log), rebuild, then publish again. There is no override flag on purpose.

After copying, every file is re-read from PUBLISH_DIR and compared by content (cells for .xlsx, bytes otherwise), and
data/published_manifest.json is updated. Commit that file with the build.
"""
import datetime, json, os, shutil, sys
from pathlib import Path
import config

MANIFEST = config.DATA_DIR / 'published_manifest.json'
DAILY_PREFIXES = ('EXT Extrusion Schedule ', 'CNV Converting Schedule ', 'FRM Formulation Report ')


def destination(name):
    """Daily workbooks go to Daily/<year>/, everything else to the folder root (handoff §9)."""
    if name.startswith(DAILY_PREFIXES):
        year = name.rsplit(' ', 1)[-1][:4]
        return config.PUBLISH_DIR / 'Daily' / year / name
    return config.PUBLISH_DIR / name


def rel(p):
    return Path(p).relative_to(config.PUBLISH_DIR).as_posix()


def main(argv):
    check_only = '--check' in argv
    reissue = '--reissue' in argv
    today = datetime.date.today().isoformat()
    names = [a for a in argv if not a.startswith('--')]
    if not config.PUBLISH_DIR:
        raise SystemExit('PUBLISH_DIR is not set (local_settings.json).')
    if not config.PUBLISH_DIR.exists():
        raise SystemExit(f'PUBLISH_DIR does not exist: {config.PUBLISH_DIR}')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    read_by_build = {Path(k): v for k, v in config.reads().items()}
    if check_only and not names:
        names = [p.name for p in config.OUTPUT_DIR.iterdir() if p.is_file()]
    plan, refused = [], []
    for n in names:
        src = config.OUTPUT_DIR / n
        if not src.exists():
            refused.append((n, f'not in {config.OUTPUT_DIR}')); continue
        dst = destination(n)
        if dst.exists() and n.startswith(DAILY_PREFIXES) and n.rsplit(' ', 1)[-1][:10] < today and not reissue:
            refused.append((n, f'{rel(dst)} is an earlier day\'s record and stays as issued. Use --reissue only if James asks for it.'))
            continue
        if dst.exists():
            now = config.content_hash(dst)
            known = set()
            r = read_by_build.get(dst.resolve())
            if r: known.add(r.get('content'))
            m = manifest.get(rel(dst))
            if m: known.add(m.get('content'))
            if now not in known:
                why = ('it was never published by this pipeline and no build read it' if not known else
                       'its content changed since this pipeline last read or published it')
                refused.append((n, f'{rel(dst)} exists and {why} - someone may have edited it. '
                                   'Compare it, log the change (handoff Change Log), rebuild, then publish.'))
                continue
        plan.append((src, dst))
    for n, why in refused:
        print(f'REFUSED  {n}: {why}')
    if refused:
        raise SystemExit(f'{len(refused)} file(s) refused - nothing was copied.')
    if check_only:
        for src, dst in plan: print(f'OK to publish  {src.name} -> {rel(dst)}')
        return
    for src, dst in plan:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + '.publishing')
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
        a, b = config.content_hash(src), config.content_hash(dst)
        if a != b:
            raise SystemExit(f'VERIFY FAILED {rel(dst)}: content differs from {src} after copy')
        manifest[rel(dst)] = {'content': b, 'sha256': config.sha256(dst), 'bytes': dst.stat().st_size,
                              'published_at': datetime.datetime.now().isoformat(timespec='seconds'), 'from': src.name}
        print(f'published and verified  {rel(dst)}  content {b[:16]}')
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding='utf-8')
    print(f'{len(plan)} file(s) published. Commit data/published_manifest.json with this build.')


if __name__ == '__main__':
    main(sys.argv[1:])
