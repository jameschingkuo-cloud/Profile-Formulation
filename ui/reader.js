// ==== The scan reader of the Daily run tab (inlined into the page by ui/build.py at /*__READER__*/). ================
// Mirrors ui/ocr_eval.py (audit3), which is the reference: tested there on every scan on file (25, 28, 29 Sep) and here
// by tests/test_scan_reader_page.py (node, same page images) and by the Chrome load test (the 29 Sep PDF must give the
// engineer's 29 Sep formulation). Hard rules (James Kuo, 30 Sep 2026): "these need to be hard rule. If anything odd is
// spotted, recheck the OCR again"; "the production sheet always have boarder lines to divide up data. Use it to isolate
// data"; "ignore hand writing. thats just notes from production team".
//
// Each order row is cut into two cells at the printed bars ("| Y | H67A164 - 1 | RPP63KS1 | PB405"), so a bar can never
// be read as a character (H69A203-17 on 29 Sep). A row band that holds one of the sheet's solid border lines with notes
// written above it is cut along the line and only the printed side is read. Each cell is read by two independent readers:
// Tesseract on a cleaned cell (ruled lines and bars erased; up to four settings) and the plant's own glyph bank
// (scan_reader/glyph_bank.npz, printed characters from earlier scans, shipped as glyph-bank.js). A row is taken only when
// it matches an order + product on file or both readers agree on both values (0 wrong in 227 such agreements on 28/29
// Sep); otherwise it is boxed for a person. The line code must be read the same two ways (page header, footer, glyph
// bank; or a page that continues its neighbour's line); otherwise the page's rows are boxed. The Word document cannot be
// downloaded while a row is boxed.
const CELL_WL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-';
const CELL_TRIES = [[3, 7], [2, 7], [3, 13], [4, 8]];
async function ocrCell(src, x0, x1, y0, y1, scale, psm){
  const {api} = await loadTess();
  api.SetVariable('tessedit_char_whitelist', CELL_WL);
  try { return (await ocr(cropPx(src, x0, y0, x1, y1, scale, 8), psm)).toUpperCase().replace(/\s+/g, ''); }
  finally { api.SetVariable('tessedit_char_whitelist', WL); }
}
const PAIRS = new Set(['0O', '0D', 'OD', '0Q', '1I', '1T', '1L', 'IT', 'IL', '1J', '5S', '8B', '4A', '4G', '6G', '6E', '2Z', '3S', '8S', 'BE', 'MN', '7/', '71', '3B', '8E',
  '4Z', '6G', '0Q', 'WN', '8R', 'BR', 'EF'].flatMap(p => [p, p[1] + p[0]]));
const SOFT = new Set('OSIZTE/:.-');
const TO_D = {O: '0', D: '0', Q: '0', U: '0', I: '1', L: '1', T: '1', J: '1', Z: '2', S: '5', G: '6', E: '6', B: '8', A: '4', '/': '7'};
const dig = s => [...s].map(c => TO_D[c] || c).join('');
function strictDist(a, b){               // look-alike swap 0.3, stray OCR mark 0.5, any other difference 1.5 / 10
  const n = a.length, m = b.length, D = [];
  for (let i = 0; i <= n; i++) { D.push(new Array(m + 1).fill(0)); if (i) D[i][0] = D[i - 1][0] + (SOFT.has(a[i - 1]) ? 0.5 : 1.5); }
  for (let j = 1; j <= m; j++) D[0][j] = D[0][j - 1] + (SOFT.has(b[j - 1]) ? 0.5 : 1.5);
  for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) {
    const x = a[i - 1], y = b[j - 1], sub = x === y ? 0 : (PAIRS.has(x + y) ? 0.3 : 10);
    D[i][j] = Math.min(D[i - 1][j - 1] + sub, D[i - 1][j] + (SOFT.has(x) ? 0.5 : 1.5), D[i][j - 1] + (SOFT.has(y) ? 0.5 : 1.5));
  }
  return D[n][m];
}
const ocrDist = strictDist;
function matchPair(oRaw, pRaw, pairs){
  let b1 = [Infinity], b2 = Infinity;
  for (const [o, p] of pairs) {
    const c = strictDist(oRaw, o) + strictDist(pRaw, p);
    if (c < b1[0]) { b2 = b1[0]; b1 = [c, o, p]; } else if (c < b2) b2 = c;
  }
  return b1[0] <= 2.5 && b2 - b1[0] >= 1 ? {order: b1[1], prod: b1[2], cost: b1[0]} : null;
}
// ---- the order number and the product code, as hard rules (order_number.py, product_code.py; James Kuo, 30 Sep 2026).
// Order: H + year digit + month + A + 3 digits (H69A039), SH + year digit + month + A + 2 digits (SH69A04), RP + 2-digit
// year + month + 2 digits (RP26821); month 1-9, A, B, C; suffix 1-2 digits. Read from the system's own schedules
// 2020-2026: never dated after the schedule; H/SH always under 2 years old.
const MONTHS = '123456789ABC';
const ORDER_RULE = /^(H\d[1-9A-C]A\d{3}|SH\d[1-9A-C]A\d\d|RP\d\d[1-9A-C]\d\d)-\d{1,2}$/;
const ORD_CELL = /^[^A-Z0-9]*(H[0-9A-Z]{6}|SH[0-9A-Z]{5}|RP[0-9A-Z]{5})-*([0-9ITLJZSOD]{1,2})[^A-Z0-9]*$/;
const mon = c => MONTHS.includes(c) ? c : (TO_D[c] || c);          // a B stays a B: November
function fixOrder(base, suf){
  const A = c => c === '4' ? 'A' : c;
  const b = base.startsWith('SH') ? 'SH' + dig(base[2]) + mon(base[3]) + A(base[4]) + dig(base.slice(5, 7))
          : base[0] === 'H' ? 'H' + dig(base[1]) + mon(base[2]) + A(base[3]) + dig(base.slice(4, 7))
          : 'RP' + dig(base.slice(2, 4)) + mon(base[4]) + dig(base.slice(5, 7));
  const o = `${b}-${dig(suf)}`;
  return ORDER_RULE.test(o) ? o : null;
}
function orderProblems(o, on){            // on: the schedule date 'YYYY-MM-DD' (order_number.problems)
  if (!ORDER_RULE.test(o || '')) return ['order number does not fit H + year + month + A + 3 digits, SH + year + month + A + 2 digits, or RP + 2-digit year + month + 2 digits (month 1-9, A, B, C), then -suffix'];
  if (!on) return [];
  const [Y, M] = on.split('-').map(Number), k = o.startsWith('SH') ? 2 : 1;
  const y = o.startsWith('RP') ? 2000 + +o.slice(2, 4) : Y - (((Y - +o[k]) % 10) + 10) % 10;
  const m = MONTHS.indexOf(o.startsWith('RP') ? o[4] : o[k + 1]) + 1;
  if (y * 12 + m > Y * 12 + M) return [`order dated ${y}-${String(m).padStart(2, '0')}, after the schedule date ${on}`];
  if (!o.startsWith('RP') && (Y - y) * 12 + M - m >= 24) return [`order dated ${y}-${String(m).padStart(2, '0')}: an H/SH order two years or more before the schedule (${on})`];
  return [];
}
function parseOrderCell(t){
  const m = ORD_CELL.exec(t);
  return m ? fixOrder(m[1], m[2]) : null;
}
function parseOrderCell2(t, marks){       // marks: characters printed after the dash, counted on the image
  const m = ORD_CELL.exec(t);
  if (!m) return null;
  let suf = m[2];
  if (marks && suf.length > marks) suf = suf.slice(0, marks);        // a bar or a split '1' read as an extra character
  if (marks && suf.length < marks) return null;
  return fixOrder(m[1], suf);
}
const CODE_RULE = /^([A-Z]{3})([1-9A-Z])([0-9])([A-Z]{2})([0-9]{1,5})$/;
const TO_L = {'0': 'O', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '6': 'G', '8': 'B', '7': 'T'};
const LOOK_L = {B: 'RE8', R: 'B', W: 'NM', N: 'WM', M: 'NW', O: 'DQ0', D: 'O0', S: '5', E: 'FB', F: 'E', I: '1LT', G: '6C', C: 'G'};
const COLOURS = new Set(D.code_rule.colours), FAMILIES = new Set(D.code_rule.families);
function codeProblems(c){
  const m = CODE_RULE.exec(c || '');
  if (!m) return ['does not fit family (3 letters) + thickness (digit 1-9 or letter, then a digit) + colour (2 letters) + number (digits)'];
  return [...(FAMILIES.has(m[1]) ? [] : [`family ${m[1]} not in use`]), ...(COLOURS.has(m[4]) ? [] : [`colour ${m[4]} not in the colour list`])];
}
function repairCode(tok){
  const t = (tok || '').toUpperCase().replace(/[^A-Z0-9/]/g, '');
  if (t.length < 8) return null;
  const fam = [...t.slice(0, 3)].map(c => TO_L[c] || c).join(''), th2 = TO_D[t[4]] || t[4], num = dig(t.slice(7));
  const cr = [...t.slice(5, 7)].map(c => TO_L[c] || c).join('');
  let cands = COLOURS.has(cr) ? [cr] : [];
  if (!cands.length) for (const a of [cr[0], ...(LOOK_L[cr[0]] || '')]) for (const b of [cr[1], ...(LOOK_L[cr[1]] || '')]) if (COLOURS.has(a + b)) cands.push(a + b);
  cands = [...new Set(cands)];
  if (cands.length !== 1) return null;
  const code = fam + t[3] + th2 + cands[0] + num;
  return CODE_RULE.test(code) ? code : null;
}
function takeProd(t2){                   // a product is taken only when it (or its rule-based repair) is in the Product Master
  const tok = (t2 || '').replace(/[^A-Z0-9/]/g, '');
  for (const c of [tok, tok.slice(1), tok.slice(0, -1), tok.slice(1, -1)]) {
    if (PRODUCTS.has(c)) return c;
    const r = repairCode(c);
    if (r && PRODUCTS.has(r)) return r;
  }
  return null;
}
function nearestOnFile(o, p, pairs){      // a hint for a boxed row: the closest order + product on file (never used by itself)
  let best = null, bc = Infinity;
  for (const [po, pp] of pairs) {
    const oc = o ? strictDist(o, po) : 20, pc = p ? strictDist(p, pp) : 20;
    const c = Math.min(oc + (pp === p ? 0 : 3), pc + (po === o ? 0 : 3));
    if (c < bc) { bc = c; best = [po, pp]; }
  }
  return bc <= 11 ? best : null;
}
const READRANK = {'read': 0, 'read by both readers': 1, 'matched to schedule history': 1, 'new order': 2, 'check': 3};
const isMatched = r => r.status === 'read' || r.status === 'matched to schedule history' || r.status === 'read by both readers';
// one reading from Claude (viewers that can send images) through the same hard rules
function judge(oText, pText, pairs, raw){
  const oRaw = (oText || '').replace(/[^A-Z0-9-]/g, '').replace(/^-+|-+$/g, ''), pRaw = (pText || '').replace(/[^A-Z0-9]/g, '');
  const m = oRaw && pRaw ? matchPair(oRaw, pRaw, pairs) : null;
  if (m) return {order: m.order, prod: m.prod, status: m.cost === 0 ? 'read' : 'matched to schedule history', raw};
  const o = parseOrderCell(oText || ''), p = takeProd(pText || '');
  if (o && p) return {order: o, prod: p, status: 'new order', raw, hint: nearestOnFile(o, p, pairs)};
  return {order: o || oRaw, prod: p || pRaw, status: 'check', raw, hint: nearestOnFile(o || oRaw, p || pRaw, pairs)};
}
function historyPairs(){                  // every order + product on file: the daily packets and the last two years of the
  const seen = new Map();                 // system's own schedules (Extrusion Production Record)
  Object.values(D.sched_by_date || {}).forEach(rows => rows.forEach(([, o, p]) => seen.set(o + '|' + p, [o, p])));
  (D.hist_pairs || []).forEach(k => { if (!seen.has(k)) seen.set(k, k.split('|')); });
  return [...seen.values()];
}

// ---- the page as grey pixels (as PIL 'L'), and small binary-image tools (as OpenCV)
function greyOf(src){
  const W = src.width, H = src.height, px = src.getContext('2d', {willReadFrequently: true}).getImageData(0, 0, W, H).data, g = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) g[i] = (px[4 * i] * 19595 + px[4 * i + 1] * 38470 + px[4 * i + 2] * 7471 + 0x8000) >> 16;
  return {W, H, g};
}
function cropGrey(P, x0, x1, y0, y1){     // numpy-style slice P[y0:y1, x0:x1] (clamped)
  x0 = Math.max(0, Math.trunc(x0)); x1 = Math.min(P.W, Math.trunc(x1)); y0 = Math.max(0, Math.trunc(y0)); y1 = Math.min(P.H, Math.trunc(y1));
  const w = Math.max(0, x1 - x0), h = Math.max(0, y1 - y0), a = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) a.set(P.g.subarray((y0 + y) * P.W + x0, (y0 + y) * P.W + x0 + w), y * w);
  return {a, w, h};
}
const roundHE = x => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 === 0 ? f : f + 1); };   // Python round()
const modP = (a, b) => ((a % b) + b) % b;
const openH = (m, w, h, L) => morph(morph(m, w, h, 1, L, true), w, h, 1, L, false);   // OpenCV MORPH_OPEN, a 1 x L line
function morph(m, w, h, kh, kw, erode){   // OpenCV erode / dilate: rectangle, anchor at (kw/2, kh/2); outside never counts
  const ax = kw >> 1, ay = kh >> 1, t = new Uint8Array(w * h), o = new Uint8Array(w * h), hit = erode ? 0 : 1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let v = 1 - hit;
    for (let k = Math.max(0, x - ax); k < Math.min(w, x - ax + kw); k++) if (m[y * w + k] === hit) { v = hit; break; }
    t[y * w + x] = v;
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let v = 1 - hit;
    for (let k = Math.max(0, y - ay); k < Math.min(h, y - ay + kh); k++) if (t[k * w + x] === hit) { v = hit; break; }
    o[y * w + x] = v;
  }
  return o;
}
function components(m, w, h){             // 8-connected; per component x, y, w, h, area and centre (as OpenCV's stats)
  const lab = new Int32Array(w * h), st = [null], stack = [];
  for (let i = 0; i < w * h; i++) {
    if (!m[i] || lab[i]) continue;
    const id = st.length; let x0 = w, y0 = h, x1 = -1, y1 = -1, area = 0, sx = 0, sy = 0;
    lab[i] = id; stack.push(i);
    while (stack.length) {
      const p = stack.pop(), x = p % w, y = (p - x) / w;
      area++; sx += x; sy += y;
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
      for (let dy = -1; dy <= 1; dy++) {
        const yy = y + dy; if (yy < 0 || yy >= h) continue;
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx; if (xx < 0 || xx >= w) continue;
          const q = yy * w + xx; if (m[q] && !lab[q]) { lab[q] = id; stack.push(q); }
        }
      }
    }
    st.push({x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1, area, cx: sx / area, cy: sy / area});
  }
  return {lab, st};
}

// ---- rows, bars and cells
function bandsOf(P){                       // order rows: dark-pixel runs in the order-number column
  const {W, H, g} = P, x0 = Math.trunc(W * 0.086), x1 = Math.trunc(W * 0.13), y0 = Math.trunc(H * 0.07), out = [];
  let start = null, last = null;
  for (let r = y0; r < H; r++) {
    let ink = 0; for (let x = x0; x < x1; x++) if (g[r * W + x] < 140) ink++;
    if (ink > 5) { if (start === null) start = r; last = r; }
    else if (start !== null && r - last > 4) { if (last - start >= 12) out.push([start, last]); start = null; }
  }
  if (start !== null && last - start >= 12) out.push([start, last]);
  return out.filter(([a]) => a > H * 0.10);
}
function barsOf(P, y0, y1){                // the printed bars run below the text: suffix bar, die bar 0.064 W later, 'Y' bar 0.073 W before
  const {W, H, g} = P, xs = [];
  for (let x = Math.trunc(W * 0.03); x < Math.trunc(W * 0.26); x++) {
    let ink = 0, n = 0;
    for (let r = y1 + 2; r < Math.min(H, y1 + 8); r++) { n++; if (g[r * W + x] < 140) ink++; }
    if (n && ink / n >= 0.8) xs.push(x);
  }
  const near = (t, tol) => { let b; for (const x of xs) if (Math.abs(x - t) <= tol && (b === undefined || Math.abs(x - t) < Math.abs(b - t))) b = x; return b; };
  for (const suf of xs) {
    if (suf < W * 0.11 || suf > W * 0.19) continue;
    const die = near(suf + W * 0.064, W * 0.005);
    if (die === undefined) continue;
    const yb = near(suf - W * 0.073, W * 0.006);
    return [yb !== undefined ? yb : Math.trunc(suf - W * 0.073), suf, die];
  }
  return null;
}
const cellsX = ([yb, sb, db], W) => { const g = Math.trunc(W * 0.003); return [[yb + g, sb - g], [sb + g, db - g]]; };   // clear of the bars

function interpNaN(a){                    // np.interp over the known points; the end values beyond them
  const k = []; for (let i = 0; i < a.length; i++) if (!Number.isNaN(a[i])) k.push(i);
  const o = new Float64Array(a.length);
  for (let i = 0, j = 0; i < a.length; i++) {
    if (i <= k[0]) o[i] = a[k[0]];
    else if (i >= k[k.length - 1]) o[i] = a[k[k.length - 1]];
    else { while (k[j + 1] < i) j++; const x0 = k[j], x1 = k[j + 1]; o[i] = a[x0] + (a[x1] - a[x0]) * (i - x0) / (x1 - x0); }
  }
  return o;
}
function lineGroups(st, W){               // the sheet's solid lines from pieces of long runs; a line broken where notes cross
  const fr = [];                          // it is joined again (ui/ocr_eval.py line_groups)
  for (let i = 1; i < st.length; i++) if (st[i] && st[i].h < 18 && st[i].w >= 40) fr.push(i);
  fr.sort((a, b) => st[a].x - st[b].x || a - b);
  const grp = new Map(fr.map(i => [i, [i]]));
  for (const a of fr) for (const b of fr) {
    if (a >= b || grp.get(a) === grp.get(b)) continue;
    const A = st[a], B = st[b], gap = Math.max(B.x - (A.x + A.w), A.x - (B.x + B.w));
    if (gap < 60 && Math.abs((A.y + A.h / 2) - (B.y + B.h / 2)) <= 8) { const g = [...grp.get(a), ...grp.get(b)]; for (const k of g) grp.set(k, g); }
  }
  const out = [];
  for (const g of new Set(grp.values())) {
    const x0 = Math.min(...g.map(i => st[i].x)), x1 = Math.max(...g.map(i => st[i].x + st[i].w));
    const top = Math.min(...g.map(i => st[i].y)), bot = Math.max(...g.map(i => st[i].y + st[i].h));
    if (x1 - x0 > 0.6 * W && bot - top < 24) out.push(g.slice().sort((a, b) => a - b));
  }
  return out.sort((a, b) => Math.min(...a.map(i => st[i].y)) - Math.min(...b.map(i => st[i].y)));
}
function isolateRow(P, bars, y0, y1, pad = 10, thr = 150){
  // A band holding a solid border line with ink on both sides (notes written above a block's top border) is cut along the
  // line, column by column (a page tilted on the glass still cuts cleanly), and only the side holding the printed '|' bars
  // is kept; the rest and the line are whited out in a copy of the page. Unchanged when there is nothing to cut.
  const {W, H, g} = P, xa = Math.max(0, bars[0] - 6), xb = Math.min(W, bars[2] + 6), ya = Math.max(0, y0 - pad), yb = Math.min(H, y1 + pad);
  const w = xb - xa, h = yb - ya, reg = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) reg[y * w + x] = g[(ya + y) * W + xa + x] < thr ? 1 : 0;
  const op = openH(reg, w, h, 60), cl = morph(morph(op, w, h, 5, 25, false), w, h, 5, 25, true);
  const {lab, st} = components(cl, w, h);
  const lines = lineGroups(st, w);
  if (!lines.length) return {P, y0, y1};
  const edges = lines.map(grp => {
    const top = new Float64Array(w).fill(NaN), bot = new Float64Array(w).fill(NaN), ids = new Set(grp);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (ids.has(lab[y * w + x]) && op[y * w + x]) { if (Number.isNaN(top[x])) top[x] = y; bot[x] = y; }
    return [interpNaN(top), interpNaN(bot)];
  });
  const onLine = new Uint8Array(w * h);
  for (const [top, bot] of edges) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (y >= top[x] - 1 && y <= bot[x] + 1) onLine[y * w + x] = 1;
  const bounds = [null, ...edges, null], bx = bars.map(b => b - xa);
  const inSeg = (k, x, y) => { const lo = bounds[k] && bounds[k][1], hi = bounds[k + 1] && bounds[k + 1][0]; return (!lo || y > lo[x] + 1) && (!hi || y < hi[x] - 1); };
  const cands = [];
  for (let k = 0; k < bounds.length - 1; k++) {
    const e = new Uint8Array(w * h); let r0 = -1, r1 = -1;
    for (let y = 0; y < h; y++) {
      let c = 0;
      for (let x = 0; x < w; x++) if (reg[y * w + x] && !onLine[y * w + x] && inSeg(k, x, y)) { e[y * w + x] = 1; c++; }
      if (c > 2) { if (r0 < 0) r0 = y; r1 = y; }
    }
    if (r0 < 0 || r1 + 1 - r0 <= 6) continue;
    let nb = 0;
    for (const x of bx) {                 // the printed '|' bars: a tall stroke at the bar column
      let run = 0, best = 0;
      for (let y = 0; y < h; y++) {
        let any = false; for (let xx = Math.max(0, x - 4); xx < Math.min(w, x + 5); xx++) if (e[y * w + xx]) { any = true; break; }
        run = any ? run + 1 : 0; if (run > best) best = run;
      }
      if (best >= 12) nb++;
    }
    cands.push({k, nb, r0, r1: r1 + 1});
  }
  if (cands.length < 2) return {P, y0, y1};
  let best = cands[0];
  for (const c of cands.slice(1)) if (c.nb > best.nb || (c.nb === best.nb && -Math.abs(c.r1 - c.r0 - 24) > -Math.abs(best.r1 - best.r0 - 24))) best = c;
  if (!best.nb) return {P, y0, y1};
  const g2 = g.slice();
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (!inSeg(best.k, x, y) || onLine[y * w + x]) g2[(ya + y) * W + xa + x] = 255;
  return {P: {W, H, g: g2}, y0: ya + best.r0, y1: ya + best.r1};
}
function cleanCell(P, x0, x1, y0, y1, scale, pad = 10, thr = 150, margin = 12){
  // Crop; split at the sheet's ruled lines and keep the part holding the printed text; erase ruled lines and edge bars;
  // trim; enlarge (Lanczos, as PIL); binarize; white border. -> {width, height, grey} for ocr().
  x0 = Math.trunc(x0); x1 = Math.trunc(x1);
  const ya = Math.max(0, Math.trunc(y0) - pad), yb = Math.trunc(y1) + pad;
  let w = Math.max(0, x1 - x0), h = Math.max(0, yb - ya), a = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const Y = ya + y, X = x0 + x; a[y * w + x] = Y < P.H && X >= 0 && X < P.W ? P.g[Y * P.W + X] : 0; }
  const rowDark = y => { let c = 0; for (let x = 0; x < w; x++) if (a[y * w + x] < thr) c++; return c; };
  const ruled = []; for (let y = 0; y < h; y++) if (w && rowDark(y) / w > 0.5) ruled.push(y);
  for (const y of ruled) a.fill(255, y * w, y * w + w);
  if (ruled.length) {
    const cuts = [0, ...ruled, h], parts = [];
    for (let i = 0; i < cuts.length - 1; i++) if (cuts[i + 1] - cuts[i] > 4) parts.push([cuts[i], cuts[i + 1]]);
    const inkH = ([s, e]) => { let r0 = -1, r1 = -1; for (let y = s; y < e; y++) if (rowDark(y) > 1) { if (r0 < 0) r0 = y; r1 = y; } return r0 < 0 ? 0 : r1 - r0 + 1; };
    const texty = parts.filter(p => { const k = inkH(p); return k >= 16 && k <= 34; });
    if (texty.length && parts.length > 1 && parts.filter(p => inkH(p) > 6).length > 1) { const [s, e] = texty[texty.length - 1]; a = a.slice(s * w, e * w); h = e - s; }
  }
  for (let x = 0; x < w; x++) {
    let c = 0; for (let y = 0; y < h; y++) if (a[y * w + x] < thr) c++;
    if (h && c / h > 0.85) for (let y = 0; y < h; y++) a[y * w + x] = 255;
  }
  let r0 = -1, r1 = -1;
  for (let y = 0; y < h; y++) if (rowDark(y) > 1) { if (r0 < 0) r0 = y; r1 = y; }
  if (r0 >= 0) { const s = Math.max(0, r0 - 2), e = Math.min(h, r1 + 3); a = a.slice(s * w, e * w); h = e - s; }
  let c0 = -1, c1 = -1;
  for (let x = 0; x < w; x++) { let c = 0; for (let y = 0; y < h; y++) if (a[y * w + x] < thr) c++; if (c > 0) { if (c0 < 0) c0 = x; c1 = x; } }
  if (c0 >= 0) {
    const s = Math.max(0, c0 - 2), e = Math.min(w, c1 + 3), b = new Uint8Array((e - s) * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < e - s; x++) b[y * (e - s) + x] = a[y * w + s + x];
    a = b; w = e - s;
  }
  if (!w || !h) { a = new Uint8Array(1).fill(255); w = h = 1; }
  let W2 = w, H2 = h, o = a;
  if (scale !== 1) { W2 = Math.max(1, Math.trunc(w * scale)); H2 = Math.max(1, Math.trunc(h * scale)); o = resizeGray(a, w, h, W2, H2); }
  const OW = W2 + 2 * margin, OH = H2 + 2 * margin, grey = new Uint8Array(OW * OH).fill(255);
  for (let y = 0; y < H2; y++) for (let x = 0; x < W2; x++) grey[(y + margin) * OW + x + margin] = Math.round(o[y * W2 + x]) < 160 ? 0 : 255;
  return {width: OW, height: OH, grey};
}
async function ocrClean(P, x0, x1, y0, y1, scale, psm){
  const {api} = await loadTess();
  api.SetVariable('tessedit_char_whitelist', CELL_WL);
  try { return (await ocr(cleanCell(P, x0, x1, y0, y1, scale), psm)).toUpperCase().replace(/\s+/g, ''); }
  finally { api.SetVariable('tessedit_char_whitelist', WL); }
}
function suffixMarks(P, x0, x1, y0, y1){  // printed characters after the dash in an order cell (marks grouped by overlap)
  const c = cleanCell(P, x0, x1, y0, y1, 1, 10, 150, 4), w = c.width, h = c.height, bw = new Uint8Array(w * h);
  for (let i = 0; i < w * h; i++) bw[i] = c.grey[i] < 128 ? 1 : 0;
  const comps = components(bw, w, h).st.filter(s => s && s.area >= 8);
  if (!comps.length) return null;
  const hmax = Math.max(...comps.map(s => s.h)), dashes = comps.filter(s => s.h < 0.45 * hmax && s.w >= s.h);
  if (!dashes.length) return null;
  const dx = Math.max(...dashes.map(s => s.x + s.w));
  const right = comps.filter(s => s.x > dx && s.h >= 0.45 * hmax).sort((a, b) => a.x - b.x), groups = [];
  for (const s of right) {
    const G = groups[groups.length - 1];
    if (G && s.x <= G[1] + 1) G[1] = Math.max(G[1], s.x + s.w); else groups.push([s.x, s.x + s.w]);
  }
  return groups.length;
}

// ---- reader 2 of each cell: the plant's glyph bank (as scan_reader/ext_scan_reader.py: segment, feature, Bank)
let GB = null;
async function glyphBank(){
  if (GB) return GB;
  if (!window.GLYPH_BANK) await loadScript('glyph-bank.js');
  GB = unpackBank(window.GLYPH_BANK, await gunzip(window.GLYPH_BANK.data));
  return GB;
}
async function gunzip(b64){
  const bin = atob(b64), gz = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) gz[i] = bin.charCodeAt(i);
  return new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
}
function unpackBank(B, q){                // int8 x q[0] shape values, uint8 x q[1] size values (ui/build.py quantize_bank)
  const n = B.n, d = B.d, X = new Float32Array(n * d);
  for (let i = 0; i < n * d; i++) { const v = q[i], j = i % d; X[i] = j < 560 ? (v > 127 ? v - 256 : v) / B.q[0] : v / B.q[1]; }
  const labs = [...new Set(B.labels)], li = Uint8Array.from(B.labels, c => labs.indexOf(c));
  return {n, d, X, labs, li};
}
function gdists(f){                       // distance to the nearest bank sample of each character
  const {n, d, X, labs, li} = GB, best = new Float64Array(labs.length).fill(Infinity);
  for (let i = 0; i < n; i++) {
    const o = i * d, lim = best[li[i]]; let s = 0;
    for (let j = 0; j < d && s < lim; j++) { const t = X[o + j] - f[j]; s += t * t; }
    if (s < lim) best[li[i]] = s;
  }
  const out = {}; labs.forEach((c, k) => { out[c] = Math.sqrt(best[k]); });
  return out;
}
function binarizeG(a, w, h){
  const bw = new Uint8Array(w * h); for (let i = 0; i < w * h; i++) bw[i] = a[i] < 140 ? 1 : 0;
  const cols = []; for (let x = 0; x < w; x++) { let c = 0; for (let y = 0; y < h; y++) c += bw[y * w + x]; if (c >= 0.75 * h) cols.push(x); }
  for (const x of cols) for (let xx = Math.max(0, x - 2); xx < Math.min(w, x + 3); xx++) for (let y = 0; y < h; y++) bw[y * w + xx] = 0;
  const rows = []; for (let y = 0; y < h; y++) { let c = 0; for (let x = 0; x < w; x++) c += bw[y * w + x]; if (c >= 0.5 * w) rows.push(y); }
  for (const y of rows) for (let yy = Math.max(0, y - 1); yy < Math.min(h, y + 2); yy++) bw.fill(0, yy * w, yy * w + w);
  const hz = openH(bw, w, h, 38);    // underlines: horizontal runs longer than 2.5 characters
  if (hz.some(v => v)) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
    if (hz[y * w + x] || (y > 0 && hz[(y - 1) * w + x]) || (y < h - 1 && hz[(y + 1) * w + x])) bw[y * w + x] = 0;
  return bw;
}
function estimatePitch(crops){
  const diffs = [];
  for (const {a, w, h} of crops) {
    const xs = components(binarizeG(a, w, h), w, h).st.filter(s => s && s.w >= 9 && s.w <= 16 && s.h >= 14).map(s => s.cx).sort((p, q) => p - q);
    for (let i = 1; i < xs.length; i++) { const d = xs[i] - xs[i - 1]; if (d > 10 && d < 24) diffs.push(d); }
  }
  if (diffs.length <= 10) return 15.0;
  diffs.sort((p, q) => p - q);
  const m = diffs.length >> 1;
  return diffs.length % 2 ? diffs[m] : (diffs[m - 1] + diffs[m]) / 2;
}
function segmentG(a, w, h, pitch){        // fixed-pitch character cells; components go to the cell holding their centre
  const bw = binarizeG(a, w, h);
  let xf = -1;
  for (let x = 0; x < w && xf < 0; x++) for (let y = 0; y < h; y++) if (bw[y * w + x]) { xf = x; break; }
  if (xf < 0) return [];
  const {lab, st} = components(bw, w, h);
  const cs = st.filter(s => s && s.w >= 8 && s.w <= 16 && s.h >= 14).map(s => s.cx);
  let phase;
  if (cs.length) {
    let sn = 0, cn = 0; for (const c of cs) { const t = c / pitch * 2 * Math.PI; sn += Math.sin(t); cn += Math.cos(t); }
    phase = modP(Math.atan2(sn / cs.length, cn / cs.length) / (2 * Math.PI) * pitch, pitch);
  } else phase = modP(xf + pitch / 2, pitch);
  let start = phase - pitch / 2;
  start -= pitch * Math.ceil((start - (xf - pitch)) / pitch);
  const pieces = new Map(), add = (k, p) => { if (!pieces.has(k)) pieces.set(k, []); pieces.get(k).push(p); };
  for (let i = 1; i < st.length; i++) {
    const s = st[i]; if (s.area < 6) continue;
    if (s.w <= 1.3 * pitch) { add(Math.floor((s.cx - start) / pitch), {id: i, lo: 0, hi: w}); continue; }
    for (let k = Math.floor((s.x - start) / pitch); k <= Math.floor((s.x + s.w - 1 - start) / pitch); k++) {
      const lo = Math.max(0, roundHE(start + k * pitch)), hi = Math.min(w, Math.max(0, roundHE(start + (k + 1) * pitch)));
      let c = 0; for (let y = 0; y < h; y++) for (let x = lo; x < hi; x++) if (lab[y * w + x] === i) c++;
      if (c >= 8) add(k, {id: i, lo, hi});
    }
  }
  const cells = [];
  for (const k of [...pieces.keys()].sort((p, q) => p - q)) {
    const m = new Uint8Array(w * h); let x0 = w, x1 = -1, y0 = h, y1 = -1, c = 0;
    for (const p of pieces.get(k)) for (let y = 0; y < h; y++) for (let x = p.lo; x < p.hi; x++) if (lab[y * w + x] === p.id) m[y * w + x] = 1;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (m[y * w + x]) { c++; if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    if (c < 8) continue;
    const cw = x1 - x0 + 1, ch = y1 - y0 + 1;
    if (cw <= 3 && ch < 18) continue;       // sliver of a neighbour
    if (cw <= 4 && ch >= 18) continue;      // remains of a '|' bar
    const gm = new Uint8Array(cw * ch);
    for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) gm[y * cw + x] = m[(y0 + y) * w + x0 + x];
    cells.push({k, g: gm, box: [x0, y0, cw, ch]});
  }
  return cells;
}
function areaTab(ss, ds, scale){           // OpenCV computeResizeAreaTab
  const tab = [];
  for (let dx = 0; dx < ds; dx++) {
    const f1 = dx * scale, f2 = f1 + scale, cw = Math.min(scale, ss - f1), t = [];
    let s1 = Math.ceil(f1), s2 = Math.floor(f2);
    s2 = Math.min(s2, ss - 1); s1 = Math.min(s1, s2);
    if (s1 - f1 > 1e-3) t.push([s1 - 1, (s1 - f1) / cw]);
    for (let s = s1; s < s2; s++) t.push([s, 1 / cw]);
    if (f2 - s2 > 1e-3) t.push([s2, Math.min(Math.min(f2 - s2, 1), cw) / cw]);
    tab.push(t);
  }
  return tab;
}
function cvResizeArea(src, sw, sh, dw, dh){  // OpenCV INTER_AREA: area averaging when shrinking, its linear weights when enlarging
  if (sw === dw && sh === dh) return Uint8Array.from(src);
  const out = new Uint8Array(dw * dh), sx = sw / dw, sy = sh / dh;
  const sat = v => Math.min(255, Math.max(0, roundHE(v)));
  if (sx >= 1 && sy >= 1) {
    const tx = areaTab(sw, dw, sx), ty = areaTab(sh, dh, sy);
    for (let Y = 0; Y < dh; Y++) for (let X = 0; X < dw; X++) {
      let s = 0; for (const [yy, wy] of ty[Y]) for (const [xx, wx] of tx[X]) s += src[yy * sw + xx] * wy * wx;
      out[Y * dw + X] = sat(s);
    }
    return out;
  }
  const lin = (ss, ds, scale) => {
    const inv = ds / ss, t = [];
    for (let d = 0; d < ds; d++) {
      const s0 = Math.floor(d * scale); let f = (d + 1) - (s0 + 1) * inv;
      f = f <= 0 ? 0 : f - Math.floor(f);
      t.push([Math.min(s0, ss - 1), Math.min(s0 + 1, ss - 1), f]);
    }
    return t;
  };
  const tx = lin(sw, dw, sx), ty = lin(sh, dh, sy);
  for (let Y = 0; Y < dh; Y++) {
    const [ya, yb, fy] = ty[Y];
    for (let X = 0; X < dw; X++) {
      const [xa, xb, fx] = tx[X];
      const r0 = src[ya * sw + xa] * (1 - fx) + src[ya * sw + xb] * fx, r1 = src[yb * sw + xa] * (1 - fx) + src[yb * sw + xb] * fx;
      out[Y * dw + X] = sat(r0 * (1 - fy) + r1 * fy);
    }
  }
  return out;
}
function featureG({g, box: [x, y, w, h]}, lineH = 22){
  const GH = 28, GW = 20, s = Math.max(h / GH, w / GW, 1e-6), nh = Math.max(1, roundHE(h / s)), nw = Math.max(1, roundHE(w / s));
  const r = cvResizeArea(Uint8Array.from(g, v => v * 255), w, h, nw, nh), v = new Float64Array(GH * GW), oy = (GH - nh) >> 1, ox = (GW - nw) >> 1;
  for (let yy = 0; yy < nh; yy++) for (let xx = 0; xx < nw; xx++) v[(oy + yy) * GW + ox + xx] = r[yy * nw + xx] / 255;
  let mean = 0; for (const t of v) mean += t; mean /= v.length;
  let nrm = 0; for (let i = 0; i < v.length; i++) { v[i] -= mean; nrm += v[i] * v[i]; }
  nrm = Math.sqrt(nrm) || 1;
  const f = new Float32Array(GH * GW + 3);
  for (let i = 0; i < v.length; i++) f[i] = v[i] / nrm;
  f[560] = h / lineH * 1.5; f[561] = w / lineH * 1.5; f[562] = (y + h / 2) / lineH * 1.5;
  return f;
}
function glyphCells(P, x0, x1, y0, y1, pitch, pad = 6){
  // a 1-px ruling scrap is not a character, nor is a short mark at either end (the dash is always inside an order number)
  const {a, w, h} = cropGrey(P, x0, x1, Math.max(0, y0 - pad), y1 + pad);
  let cells = segmentG(a, w, h, pitch).filter(c => c.box[3] > 1);
  if (cells.length) {
    const hmax = Math.max(...cells.map(c => c.box[3]));
    while (cells.length && cells[0].box[3] < 0.45 * hmax) cells = cells.slice(1);
    while (cells.length && cells[cells.length - 1].box[3] < 0.45 * hmax) cells = cells.slice(0, -1);
  }
  return cells.map(c => ({k: c.k, f: featureG(c), box: c.box}));
}
const DIG = '0123456789';
const pick = (d, allowed) => [...allowed].map(ch => [d[ch] ?? 9.0, ch]).sort((p, q) => p[0] - q[0] || (p[1] < q[1] ? -1 : p[1] > q[1] ? 1 : 0));
function decodeOrder(cells){              // base of 7 characters, a dash (a short mark), 1-2 suffix digits
  if (cells.length < 9) return null;
  const hmax = Math.max(...cells.map(c => c.box[3])), dash = cells.map((c, i) => [c, i]).filter(([c]) => c.box[3] < 0.45 * hmax);
  if (dash.length !== 1) return null;
  const i = dash[0][1], base = cells.slice(0, i), suf = cells.slice(i + 1);
  if (base.length !== 7 || suf.length < 1 || suf.length > 2) return null;
  let best = null;
  for (const pat of [['H', DIG, MONTHS, 'A', DIG, DIG, DIG], ['S', 'H', DIG, MONTHS, 'A', DIG, DIG], ['R', 'P', DIG, DIG, MONTHS, DIG, DIG]]) {
    let s = '', tot = 0;
    base.forEach((c, k) => { const r = pick(gdists(c.f), pat[k]); s += r[0][1]; tot += r[0][0]; });
    if (!best || tot < best[1]) best = [s, tot];
  }
  let sfx = '';
  for (const c of suf) sfx += pick(gdists(c.f), DIG)[0][1];
  return `${best[0]}-${sfx}`;
}
let BYLEN = null;
function decodeProduct(cells){            // the nearest Product Master code with the same number of characters
  if (!BYLEN) { BYLEN = {}; for (const c of PRODUCTS) (BYLEN[c.length] = BYLEN[c.length] || []).push(c); }
  const opts = BYLEN[cells.length];
  if (!opts || !cells.length) return null;
  const ds = cells.map(c => gdists(c.f));
  let best = null, bs = Infinity;
  for (const o of opts) {
    let s = 0; for (let k = 0; k < o.length; k++) s += ds[k][o[k]] ?? 9.0;
    if (s < bs || (s === bs && o < best)) { bs = s; best = o; }
  }
  return best;
}
async function readRow(P, pitch, y0, y1, bars){
  const [[ox0, ox1], [px0, px1]] = cellsX(bars, P.W);
  ({P, y0, y1} = isolateRow(P, bars, y0, y1));
  const marks = suffixMarks(P, ox0, ox1, y0, y1);
  let to = null, tp = null; const raws = [];
  for (const [scale, psm] of CELL_TRIES) {  // "if anything odd is spotted, recheck the OCR again"
    const t = to === null ? await ocrClean(P, ox0, ox1, y0, y1, scale, psm) : '';
    const t2 = tp === null ? await ocrClean(P, px0, px1, y0, y1, scale, psm) : '';
    raws.push([t, t2]);
    if (to === null) to = parseOrderCell2(t, marks);
    if (tp === null) tp = takeProd(t2);
    if (to && tp) break;
  }
  const go = decodeOrder(glyphCells(P, ox0, ox1, y0, y1, pitch)), gp = decodeProduct(glyphCells(P, px0, px1, y0, y1, pitch));
  return {to, tp, go, gp, raws};
}
const LOOK_MONTH = {B: '8', 8: 'B', A: '4', 4: 'A'};
function monthFix(o, on){                 // a reading the schedule date rules out is no reading, unless its month is a look-alike
  if (!o || !orderProblems(o, on).length) return o;           // (B/8, A/4) and the look-alike is possible (ui/ocr_eval.py month_fix)
  const [base, suf] = o.split('-'), k = base.startsWith('RP') ? 4 : base.startsWith('SH') ? 3 : 2;
  const alt = base.slice(0, k) + (LOOK_MONTH[base[k]] || base[k]) + base.slice(k + 1) + '-' + suf;
  return alt !== o && !orderProblems(alt, on).length ? alt : null;
}
function decide(to, tp, go, gp, pairSet, on){ // taken: an order + product on file, or both readers agree; else boxed
  let bothFixed = false;                  // two look-alike fixes agreeing is no agreement
  if (on) { const t2 = monthFix(to, on), g2 = monthFix(go, on); bothFixed = !!(to && go && t2 !== to && g2 !== go); to = t2; go = g2; }
  for (const [o, p] of [[to, tp], [go, gp], [to, gp], [go, tp]]) if (o && p && pairSet.has(o + '|' + p)) return {order: o, prod: p, status: 'read'};
  if (to && to === go && tp && tp === gp && !bothFixed) return {order: to, prod: tp, status: 'read by both readers'};
  return {order: to === go ? to : (to || go), prod: tp === gp ? tp : (tp || gp), status: 'check'};
}

// ---- the line code: a known line, read two independent ways (header word, footer, glyph bank), else the page is boxed
const LINES = Object.keys(D.linemeta || {}).sort();
function fitLine(t){                      // a word -> the known line it can only be (look-alikes only), else null
  t = (t || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  const m = /S[EF5][0-9A-Z]{2}$/.exec(t) || /S[EF5][0-9A-Z]{2}/.exec(t);   // S, E, two characters: nothing missing is guessed
  if (!m) return null;
  const w = 'SE' + m[0].slice(-2);
  const sc = LINES.map(L => [strictDist(w, L), L]).sort((p, q) => p[0] - q[0] || (p[1] < q[1] ? -1 : 1));
  return sc.length && sc[0][0] <= 0.6 && (sc.length < 2 || sc[1][0] - sc[0][0] >= 0.3) ? sc[0][1] : null;
}
function tsvLines(tsv){                   // Tesseract TSV -> lines of words [left, top, width, height, text]
  const by = new Map();
  for (const row of tsv.split('\n')) {
    const c = row.split('\t');
    if (c.length < 12 || c[0] !== '5' || !c[11].trim()) continue;
    const k = c[2] + '|' + c[3] + '|' + c[4];
    if (!by.has(k)) by.set(k, []);
    by.get(k).push([+c[6], +c[7], +c[8], +c[9], c[11]]);
  }
  return [...by.values()].sort((p, q) => Math.min(...p.map(t => t[1])) - Math.min(...q.map(t => t[1])));
}
async function pageHead(P){               // -> null (not an extrusion page) or {reads: [[kind, line|null, raw]]}
  const c = cropGrey(P, 0, P.W * 0.75, 0, P.H * 0.10);
  const {api} = await loadTess();
  api.SetVariable('tessedit_char_whitelist', '');
  let tsv; try { tsv = await ocr({width: c.w, height: c.h, grey: c.a}, 6, true); } finally { api.SetVariable('tessedit_char_whitelist', WL); }
  const lines = tsvLines(tsv), U = lines.map(l => l.map(t => t[4]).join(' ')).join('\n').toUpperCase();
  if (!/LINE\s*N[O0]/.test(U) || !/EXTRUS|WPPPOPRC|PRODUCTION\s*INSTRUCTION\s*-\s*EXT/.test(U) || /LINE\s*N[O0]\W*S[DC]\d/.test(U)) return null;
  const reads = [];
  for (const ln of lines) {
    if (!/LINE\s*N[O0]/.test(ln.map(t => t[4]).join(' ').toUpperCase())) continue;
    const no = ln.findIndex(t => /^N[O0]/.test(t[4].toUpperCase()));
    if (no < 0 || no + 1 >= ln.length) continue;
    reads.push(['header', fitLine(ln[no + 1][4]), ln[no + 1][4]]);
    const [x, y, ww, hh] = ln[no], cr = cropGrey(P, x + ww + 5, x + ww + 150, Math.max(0, y - 12), y + hh + 12);
    const cells = segmentG(cr.a, cr.w, cr.h, 15.0);
    if (cells.length >= 4) {
      const ds = cells.slice(0, 4).map(cc => gdists(featureG(cc)));
      const sc = LINES.map(L => [[...L].reduce((s, ch, k) => s + (ds[k][ch] ?? 9.0), 0), L]).sort((p, q) => p[0] - q[0]);
      reads.push(['glyph', sc[1][0] - sc[0][0] >= 0.15 ? sc[0][1] : null, `${sc[0][1]} ${(sc[1][0] - sc[0][0]).toFixed(2)}`]);
    }
    break;
  }
  return {reads};
}
function footerRead(t){                   // 'LINE NO. SE22 Total' at the end of a line's list
  const m = /LINEN[O0]\W*([A-Z0-9]{2,6}?)\W*T[O0]TAL/.exec(t || '');
  return m ? ['footer', fitLine(m[1]), t] : null;
}
function lineOf(reads){
  const vals = reads.map(r => r[1]).filter(Boolean);
  if (!vals.length) return null;
  const best = vals.slice().sort((p, q) => vals.filter(v => v === q).length - vals.filter(v => v === p).length)[0];
  return vals.filter(v => v === best).length >= 2 && vals.every(v => v === best) ? best : null;
}
function settleLines(pages){              // a line's pages run on until its footer: a page without one continues on the next
  pages.forEach((p, i) => {
    if (p.line) return;
    const own = new Set(p.lineReads.filter(r => r[1] && (r[0] === 'header' || r[0] === 'glyph')).map(r => r[1]));
    const foot = q => q.lineReads.some(r => r[0] === 'footer'), nxt = pages[i + 1], prv = pages[i - 1];
    if (own.size !== 1) return;
    if (nxt && !foot(p) && nxt.line && own.has(nxt.line)) { p.line = nxt.line; p.lineHow = 'continues on the next page'; }
    else if (prv && prv.line && !foot(prv) && own.has(prv.line)) { p.line = prv.line; p.lineHow = 'continued from the previous page'; }
  });
  return pages;
}
async function ocrPage(p, pairs, pairSet, on){
  const src = p.canvas, P = greyOf(src);
  await glyphBank();
  const head = await pageHead(P);
  if (!head) return null;                                   // not an extrusion page (CNV, FRM, blank)
  const lineReads = head.reads, orders = [], unread = [], rows = [];
  for (const [y0, y1] of bandsOf(P)) {
    const bars = barsOf(P, y0, y1);
    if (bars) { rows.push([y0, y1, bars]); continue; }
    if (ctl.signal.aborted) throw {code: 'cancelled'};
    const t = await ocrCell(src, src.width * 0.06, src.width * 0.24, y0, y1, 2, 7);   // no bars: not an order row, unless it carries numbers
    const f = footerRead(t); if (f) { lineReads.push(f); continue; }
    if (!/LINE|TOTAL|REPORT|SI|SPECIAL/.test(t) && /\d{3}/.test(t))
      unread.push({text: t, img: cropPx(src, src.width * 0.05, y0, src.width * 0.30, y1, 1, 14).toDataURL('image/png')});
  }
  const pitch = rows.length ? estimatePitch(rows.map(([y0, y1, b]) => cropGrey(P, b[0] + 4, b[2] - 4, Math.max(0, y0 - 6), y1 + 6))) : 15.0;
  for (const [y0, y1, bars] of rows) {
    if (ctl.signal.aborted) throw {code: 'cancelled'};
    const r = await readRow(P, pitch, y0, y1, bars), txt = r.raws.map(x => x.join('')).join('');
    if (/LINE|TOTAL|REPORT/.test(txt)) { const f = footerRead(txt); if (f) lineReads.push(f); continue; }
    const d = decide(r.to, r.tp, r.go, r.gp, pairSet, on);
    const o = {...d, raw: `${r.to || '?'} | ${r.tp || '?'} (text) · ${r.go || '?'} | ${r.gp || '?'} (glyphs)`};
    if (d.status === 'check') {
      o.hint = nearestOnFile(d.order, d.prod, pairs);
      o.img = cropPx(src, bars[0] - 20, y0, bars[2] + src.width * 0.05, y1, 1, 12).toDataURL('image/png');
    }
    orders.push(o);
  }
  return {page: p.label, line: lineOf(lineReads), lineReads, orders, unread};
}
function boxUncertainLines(reads){        // after settleLines: rows of a page whose line is still not certain are boxed
  reads.forEach(r => {
    if (r.line) return;
    const guess = r.lineReads.map(x => x[1]).filter(Boolean);
    r.lineGuess = [...new Set(guess)];
    r.line = r.lineGuess.length === 1 ? r.lineGuess[0] : 'SE??';
    r.orders.forEach(o => { o.status = 'check'; o.lineCheck = true; o.line = r.line; });
  });
  return reads;
}
