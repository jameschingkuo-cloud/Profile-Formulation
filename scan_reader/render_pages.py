"""Render a packet scan for reading by eye (or by Claude): one 300-dpi PNG per page, turned upright, plus four
overlapping quarter tiles per page for zoomed reading of small print.

    python scan_reader/render_pages.py <scan.pdf> [out_dir]      (default out_dir: work/pages/<scan name>/)

Needs only PyMuPDF (pip install pymupdf) and OpenCV, both in requirements.txt.
"""
import os, sys
import cv2, numpy as np, pymupdf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import config


def render(pdf, out_dir=None, dpi=300, overlap=0.08):
    out = config.WORK_DIR / 'pages' / os.path.splitext(os.path.basename(pdf))[0] if out_dir is None else config.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    config.record_read(pdf, 'packet scan')
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        im = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
        if im.shape[0] > im.shape[1]:                       # the reports are landscape; scans often come in portrait
            im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
        cv2.imwrite(str(out / f'p{i:02d}.png'), im)
        h, w = im.shape
        oh, ow = int(h * overlap), int(w * overlap)
        for r, (y0, y1) in enumerate(((0, h // 2 + oh), (h // 2 - oh, h))):
            for c, (x0, x1) in enumerate(((0, w // 2 + ow), (w // 2 - ow, w))):
                cv2.imwrite(str(out / f'p{i:02d}_{"tb"[r]}{"lr"[c]}.png'), im[y0:y1, x0:x1])
    print(f'{len(doc)} pages -> {out}')
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
