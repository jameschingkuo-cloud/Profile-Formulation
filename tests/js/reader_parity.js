// node tests/js/reader_parity.js <dump dir> : the page's reader (ui/reader.js) on the same page images as ui/ocr_eval.py
// (dumped by tests/test_scan_reader_page.py). Prints one line per row and '<n> rows, <k> differences' at the end.
const fs = require('fs'), path = require('path'), zlib = require('zlib');
const ROOT = path.resolve(__dirname, '../..'), DUMP = path.resolve(process.argv[2]);
const tpl = fs.readFileSync(path.join(ROOT, 'ui/page.template.html'), 'utf8');
const html = fs.readFileSync(path.join(ROOT, 'out/profile-formulation.html'), 'utf8');
const D = JSON.parse(/<script type="application\/json" id="data">([\s\S]*?)<\/script>/.exec(html)[1]);
const PRODUCTS = new Set(D.products);
const a = tpl.indexOf('function lanczosWeights('), b = tpl.indexOf('function crop(src');
const src = tpl.slice(a, b) + fs.readFileSync(path.join(ROOT, 'ui/reader.js'), 'utf8');
eval(src.replace(/^const /gm, 'var ').replace(/^let /gm, 'var '));
const gbs = fs.readFileSync(path.join(ROOT, 'out/glyph-bank.js'), 'utf8');
const B = JSON.parse(gbs.slice(gbs.indexOf('=') + 1, gbs.lastIndexOf(';')));
GB = unpackBank(B, zlib.gunzipSync(Buffer.from(B.data, 'base64')));
let bad = 0, n = 0;
for (const f of fs.readdirSync(DUMP).filter(f => f.endsWith('.json'))) {
  const R = JSON.parse(fs.readFileSync(path.join(DUMP, f), 'utf8'));
  const P = {W: R.W, H: R.H, g: new Uint8Array(fs.readFileSync(path.join(DUMP, f.replace('.json', '.bin'))))};
  const bands = bandsOf(P).map(([y0, y1]) => [y0, y1, barsOf(P, y0, y1)]);
  if (JSON.stringify(bands) !== JSON.stringify(R.bands)) { bad++; console.log(f, 'BANDS DIFFER', JSON.stringify(bands).slice(0, 200), JSON.stringify(R.bands).slice(0, 200)); }
  const rows = bands.filter(r => r[2]);
  const pitch = estimatePitch(rows.map(([y0, y1, b]) => cropGrey(P, b[0] + 4, b[2] - 4, Math.max(0, y0 - 6), y1 + 6)));
  if (Math.abs(pitch - R.pitch) > 1e-6) { bad++; console.log(f, 'PITCH', pitch, R.pitch); }
  R.rows.forEach((r, i) => {
    n++;
    const [[ox0, ox1], [px0, px1]] = cellsX(r.bars, P.W);
    const iso = isolateRow(P, r.bars, r.y0, r.y1);
    const marks = suffixMarks(iso.P, ox0, ox1, iso.y0, iso.y1);
    const go = decodeOrder(glyphCells(iso.P, ox0, ox1, iso.y0, iso.y1, pitch)), gp = decodeProduct(glyphCells(iso.P, px0, px1, iso.y0, iso.y1, pitch));
    const cc = cleanCell(iso.P, ox0, ox1, iso.y0, iso.y1, 3); let dark = 0; for (const v of cc.grey) if (v < 128) dark++;
    const got = {iso: [iso.y0, iso.y1], marks, go, gp, clean_shape: [cc.height, cc.width]}, want = {iso: r.iso, marks: r.marks, go: r.go, gp: r.gp, clean_shape: r.clean_shape};
    const same = JSON.stringify(got) === JSON.stringify(want);
    if (!same) bad++;
    console.log(same ? 'same' : 'DIFF', f, i, JSON.stringify(got), same ? '' : 'python ' + JSON.stringify(want), `dark ${dark} vs ${r.clean_dark}`);
  });
}
console.log(`${n} rows, ${bad} differences`);
