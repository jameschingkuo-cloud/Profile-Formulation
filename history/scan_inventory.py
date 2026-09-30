"""What is in the copier scans on this PC (James Kuo, 30 Sep 2026: "any production schedule you can get your hands on, go
through and update your data base"; "if its scan, OCR them"). Each page's title strip is read (Tesseract) and the page is
sorted: EXT (extrusion schedule, with its line and Run Date), CNV (converting schedule), FRM (Tech's formulation report)
or OTHER. Nothing else is read here.

    python history/scan_inventory.py [folder ...]     -> work/history/scan_pages.csv
"""
import csv
import hashlib
import io
import re
import sys
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
FOLDERS = [Path(r'C:\Users\JamesKuo\Downloads'), Path(r'C:\Users\JamesKuo\OneDrive - Inteplast-WPJK')]
SCAN = re.compile(r'^doc\d{6}(\d{8})(\d{6})', re.I)          # copier file name: doc + counter + scan date + time


def page_images(path):
    """Each page as a grey PIL image."""
    d = pymupdf.open(path)
    for pno in range(d.page_count):
        page = d[pno]
        imgs = page.get_images()
        if len(imgs) == 1:
            im = Image.open(io.BytesIO(d.extract_image(imgs[0][0])['image'])).convert('L')
        else:
            pix = page.get_pixmap(dpi=150)
            im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples).convert('L')
        yield pno + 1, im


def words(t):
    return len(re.findall(r'\b[A-Z]{4,}\b', t))


def classify(im):
    """-> (kind, line, date, text, turn). Tries the page in all four orientations (the copier takes the stack any way
    round); the turn that reads as words is kept."""
    first, fw, turn = '', -1, 0
    for rot in (0, 270, 90, 180):
        r = im.rotate(-rot, expand=True) if rot else im
        w, h = r.size
        s = 1600 / w
        strip = r.resize((1600, max(1, int(h * s))), Image.BILINEAR).crop((0, 0, 1600, int(h * s * 0.16)))
        t = pytesseract.image_to_string(strip, config='--psm 6').upper()
        if words(t) > fw:
            first, fw, turn = ' '.join(t.split())[:160], words(t), rot
        kind = ''
        if re.search(r'PRODUCTION\s+INSTRUCTION', t) and re.search(r'EXTRUS', t):
            kind = 'EXT'
        elif re.search(r'PRODUCTION\s+INSTRUCTIONS?\W+(GUILLOTINE|DIE\s*CUT|BOBST|FLAT|FOLDER|SLITTER|ROTARY)', t):
            kind = 'CNV'                                 # converting schedules; a converting QC form is not one
        elif re.search(r'FORMULATIONS?\b', t) and re.search(r'\bLINE\b', t):
            kind = 'FRM'
        elif re.search(r'WORK\s+IN\s+PROGRESS|FINISHED\s+GOODS|QC\s+TECHNICIAN|VOID\s*FORM|IWPFT', t):
            kind = 'QC'                                  # pallet QC tags and QC forms: not schedules
        if kind:
            line = re.search(r'LINE\s*N[O0]\W*(S[A-Z0-9]{3})', t)
            m = re.search(r'\b(SE\d\d)\b', t) if kind == 'FRM' else None
            rd = re.search(r'RUN\s*DATE\W*(\d{1,2}/\d\d/\d\d)', t) or re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', t)
            return kind, (line.group(1) if line else (m.group(1) if m else '')), (rd.group(1) if rd else ''), ' '.join(t.split())[:160], rot
    return 'OTHER', '', '', first, turn


def main(folders):
    out = config.WORK_DIR / 'history' / 'scan_pages.csv'
    out.parent.mkdir(parents=True, exist_ok=True)
    files, seen = [], {}
    for f in folders:
        for p in sorted(Path(f).rglob('doc0*.pdf')):
            if not SCAN.match(p.name):
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            if h in seen:                                # the same scan saved twice: read once
                continue
            seen[h] = p
            files.append((p, h))
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['file', 'path', 'sha', 'scan_date', 'page', 'kind', 'line', 'date', 'turn', 'text'])
        for p, h in files:
            m = SCAN.match(p.name)
            sd = f'{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}'
            try:
                for pno, im in page_images(p):
                    kind, line, rd, t, turn = classify(im)
                    w.writerow([p.name, str(p), h, sd, pno, kind, line, rd, turn, t])
            except Exception as e:
                w.writerow([p.name, str(p), h, sd, 0, 'ERROR', '', '', '', repr(e)[:160]])
            fh.flush()
    return len(files), out


if __name__ == '__main__':
    print(main([Path(a) for a in sys.argv[1:]] or FOLDERS))
