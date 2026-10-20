// The text lane's two flags, OFF beside ON, drawn from the stitch stream
// buildLetteringDesign hands the writers (MASTER_SCOPE 25 and 40, 2026-10-20).
//
//   node tools/text-lane-flags-sheet.mjs [outDir] [--fonts a,b,c] [--text WORD] [--widths 40,100]
//   node tools/text-lane-flags-sheet.mjs [outDir] --census
//
// Default: medium_font (the Studio's default), mai_en_fleur, pixel10, the
// word FRITSCH at 40 and 100 mm wide on a 5 x 2.25 in garment with the
// underlay ladder deciding the underlay, into docs/renders/text-lane-flags/.
// Writes one PNG per font and size for `dedupeHoles` (OFF on the left, ON on
// the right), one for the `underlayDirection` ring case (colorful, Stitches,
// 100 mm), counts.json with every number the README quotes, and prints the
// table. Nothing is written to a .dst: the md5s are of the stream itself,
// which is what the pins in test/text-lane-flags.test.js hold.
//
// --census: no pictures. Every font in src/fonts/bin, the words FRITSCH and
// Stitches, 40 and 100 mm (340 pairings, 332 of which lay anything; about a
// minute), OFF against each
// flag ON, into census.json: the doubled records and the designs carrying
// them, the spans a run that laid nothing loses, the columns after an
// underlay and how many the first-and-last-STITCH rule would turn against
// how many the cross rule does, the designs ON leaves byte-identical, the
// largest change in needle-down thread, and the fonts with the most doubled
// records by count and by share. The README's library-wide numbers come
// from here.
//
// Key: thread between two stitches in a row is a dark line, needle-up a
// light grey one; every needle hole a dot. Left (OFF): a RED ring round a
// hole the needle goes down in twice (two stitch records on one point, one
// straight after the other). Right (ON): a GREEN ring where that hole is
// laid once. Underlay direction panels: a green dot is the underlay's last
// stitch and a magenta dot the satin's first, for every column that follows
// its underlay with the needle down; a turned column has its magenta dot at
// the other end of the ring.
import "./_help.mjs";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { encodePNG } from "./png.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const DG = require(path.join(ROOT, "src", "digitize.js"));
const fb = require(path.join(ROOT, "src", "fontbin.js"));
const BIN = path.join(ROOT, "src", "fonts", "bin");

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const FONTS = opt("--fonts", "medium_font,mai_en_fleur,pixel10").split(",");
const TEXT = opt("--text", "FRITSCH");
const WIDTHS = opt("--widths", "40,100").split(",").map(Number);
const CENSUS = args.includes("--census") ? (args.splice(args.indexOf("--census"), 1), true) : false;
const outDir =path.resolve(args[0] || path.join(ROOT, "docs", "renders", "text-lane-flags"));
fs.mkdirSync(outDir, { recursive: true });

const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, underlay: true };
const load = (key) => fb.decodeFontBin(fs.readFileSync(path.join(BIN, key + ".embf")));
const build = (font, text, w, extra) => DG.buildLetteringDesign(font, text, { ...base, targetWidthMm: w, ...(extra || {}) });
const md5 = (d) => crypto.createHash("md5").update(JSON.stringify(d.stitches)).digest("hex");
const same = (p, q) => p.x === q.x && p.y === q.y;

// The doubled holes: index of every stitch whose record comes straight after
// a stitch on its point, by the kind of span it is in ("none": in no span).
function doubled(d) {
  const kindAt = [];
  for (const r of d.runs || []) for (let i = r.i0; i <= r.i1; i++) kindAt[i] = r.kind;
  const at = [], byKind = {};
  for (let i = 1; i < d.stitches.length; i++) {
    const a = d.stitches[i - 1], b = d.stitches[i];
    if (a.type === "stitch" && b.type === "stitch" && same(a, b)) { at.push(i); const k = kindAt[i] || "none"; byKind[k] = (byKind[k] || 0) + 1; }
  }
  return { at, byKind };
}
// Every satin column entered needle-down from its own underlay: where the
// underlay ends, the midpoints of the column's first and last crosses, and
// whether the column starts at the cross nearer the thread.
function columnsAfterUnderlay(d) {
  const st = d.stitches, spans = d.runs || [], out = [];
  const mid = (p, q) => ({ x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 });
  for (let k = 1; k < spans.length; k++) {
    const s = spans[k];
    if (s.kind !== "satin") continue;
    let j = k - 1;
    if (spans[j].kind === "travel") j--;
    if (j < 0 || spans[j].kind !== "underlay" || spans[j].shape !== s.shape) continue;
    let jumped = false;
    for (let i = spans[j].i1 + 1; i < s.i0; i++) if (st[i].type !== "stitch") jumped = true;
    if (jumped) continue;
    const from = st[spans[j].i1], first = mid(st[s.i0], st[s.i0 + 1]), last = mid(st[s.i1], st[s.i1 - 1]);
    out.push({ span: k, from, firstStitch: st[s.i0], nearEnd: Math.hypot(from.x - first.x, from.y - first.y) <= Math.hypot(from.x - last.x, from.y - last.y) });
  }
  return out;
}
const threadMm = (d) => { let t = 0; for (let i = 1; i < d.stitches.length; i++) { const a = d.stitches[i - 1], b = d.stitches[i]; if (a.type === "stitch" && b.type === "stitch") t += Math.hypot(b.x - a.x, b.y - a.y); } return t / 10; };
const travelMm = (d) => { let t = 0; for (const r of (d.runs || []).filter((r) => r.kind === "travel")) { let p = d.stitches[r.i0 - 1]; for (let i = r.i0; i <= r.i1 + 1 && i < d.stitches.length; i++) { t += Math.hypot(d.stitches[i].x - p.x, d.stitches[i].y - p.y); p = d.stitches[i]; } } return t / 10; };

// ---- drawing -------------------------------------------------------------
function panelBounds(designs) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const d of designs) for (const s of d.stitches) { minX = Math.min(minX, s.x); maxX = Math.max(maxX, s.x); minY = Math.min(minY, s.y); maxY = Math.max(maxY, s.y); }
  return { minX, maxX, minY, maxY };
}
function sheet(panels, scale, file) {
  // panels: [{ design, marks: [{x, y, rgb, ring}], label }], side by side
  const PAD = 24, GAP = 16;
  const b = panelBounds(panels.map((p) => p.design));
  const pw = Math.ceil((b.maxX - b.minX) / 10 * scale) + 2 * PAD, ph = Math.ceil((b.maxY - b.minY) / 10 * scale) + 2 * PAD;
  const W = pw * panels.length + GAP * (panels.length - 1), H = ph;
  const rgba = new Uint8Array(W * H * 4).fill(255);
  const put = (x, y, c) => { x = Math.round(x); y = Math.round(y); if (x < 0 || y < 0 || x >= W || y >= H) return; const i = (y * W + x) * 4; rgba[i] = c[0]; rgba[i + 1] = c[1]; rgba[i + 2] = c[2]; rgba[i + 3] = 255; };
  const line = (x0, y0, x1, y1, c) => { const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) * 2)); for (let k = 0; k <= n; k++) { const t = k / n; put(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, c); } };
  const dot = (x, y, c, r) => { for (let a = -r; a <= r; a++) for (let b2 = -r; b2 <= r; b2++) if (a * a + b2 * b2 <= r * r) put(x + a, y + b2, c); };
  const ring = (x, y, c, r) => { for (let a = -r - 1; a <= r + 1; a++) for (let b2 = -r - 1; b2 <= r + 1; b2++) { const q = a * a + b2 * b2; if (q <= (r + 1) * (r + 1) && q >= (r - 1) * (r - 1)) put(x + a, y + b2, c); } };
  panels.forEach((p, k) => {
    const ox = k * (pw + GAP);
    const tx = (u) => ox + PAD + (u - b.minX) / 10 * scale, ty = (u) => PAD + (b.maxY - u) / 10 * scale;
    if (k > 0) for (let y = 0; y < H; y++) for (let g = 0; g < GAP; g++) put(ox - GAP + g, y, [235, 235, 235]);
    const st = p.design.stitches;
    for (let i = 1; i < st.length; i++) {
      const a = st[i - 1], s = st[i];
      if (s.type === "stitch" && a.type === "stitch") line(tx(a.x), ty(a.y), tx(s.x), ty(s.y), [40, 40, 60]);
      else if (s.type === "jump" || a.type === "jump") line(tx(a.x), ty(a.y), tx(s.x), ty(s.y), [200, 200, 200]);
    }
    for (const s of st) if (s.type === "stitch") dot(tx(s.x), ty(s.y), [120, 120, 140], 0);
    for (const m of p.marks) (m.ring ? ring : dot)(tx(m.x), ty(m.y), m.rgb, m.ring ? Math.max(3, Math.round(scale * 0.3)) : Math.max(2, Math.round(scale * 0.15)));
  });
  fs.writeFileSync(file, encodePNG(W, H, rgba));
  return { W, H };
}

// ---- --census: the whole library, no pictures -------------------------------
if (CENSUS) {
  const fonts = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf")).map((f) => f.replace(/\.embf$/, "")).sort();
  const WORDS = ["FRITSCH", "Stitches"], SIZES = [40, 100];
  const rows = [];
  const c = { designs: 0, doubled: 0, designsWithDoubled: 0, spansLost: 0, designsLosingSpans: 0, columnsAfterUnderlay: 0,
    pointRuleWouldTurn: 0, turned: 0, designsTurned: 0, identicalUnderDirection: 0, maxThreadDeltaMm: 0, maxThreadDeltaDesign: null };
  for (const key of fonts) {
    const font = load(key);
    for (const text of WORDS) for (const w of SIZES) {
      const off = build(font, text, w);
      if (!off.runs) continue;   // nothing laid (the font has no glyph for the word)
      const dd = build(font, text, w, { dedupeHoles: true }), dir = build(font, text, w, { underlayDirection: true });
      c.designs++;
      const D = doubled(off);
      c.doubled += D.at.length; if (D.at.length) c.designsWithDoubled++;
      const lost = off.runs.length - dd.runs.length;
      c.spansLost += lost; if (lost) c.designsLosingSpans++;
      const cols = columnsAfterUnderlay(off), colsOn = columnsAfterUnderlay(dir);
      c.columnsAfterUnderlay += cols.length;
      // the shape lane's own test, first and last STITCH against the thread
      for (const k of cols.map((x) => x.span)) {
        const s = off.runs[k], from = off.stitches[(off.runs[k - 1].kind === "travel" ? off.runs[k - 2] : off.runs[k - 1]).i1];
        const a = off.stitches[s.i0], b = off.stitches[s.i1];
        if (Math.hypot(b.x - from.x, b.y - from.y) < Math.hypot(a.x - from.x, a.y - from.y)) c.pointRuleWouldTurn++;
      }
      let turned = 0;
      for (let i = 0; i < cols.length; i++) if (!same(cols[i].firstStitch, colsOn[i].firstStitch)) turned++;
      c.turned += turned; if (turned) c.designsTurned++;
      if (md5(off) === md5(dir)) c.identicalUnderDirection++;
      const delta = Math.abs(threadMm(dir) - threadMm(off));
      if (delta > c.maxThreadDeltaMm) { c.maxThreadDeltaMm = +delta.toFixed(2); c.maxThreadDeltaDesign = `${key} ${text} ${w} mm`; }
      rows.push({ font: key, text, widthMm: w, records: off.stitches.length, doubled: D.at.length, byKind: D.byKind, share: +(D.at.length / off.stitches.length).toFixed(4), spansLost: lost, columnsAfterUnderlay: cols.length, turned });
    }
  }
  const top = (by) => rows.slice().sort((a, b) => b[by] - a[by]).slice(0, 5).map((r) => ({ font: r.font, text: r.text, widthMm: r.widthMm, doubled: r.doubled, records: r.records, share: r.share }));
  const census = { generated: new Date().toISOString().slice(0, 10), garment: base.garment, pxPerMm: base.pxPerMm, underlay: "ladder", words: WORDS, widthsMm: SIZES, fonts: fonts.length, totals: c, mostDoubled: top("doubled"), largestShare: top("share"), designs: rows };
  fs.writeFileSync(path.join(outDir, "census.json"), JSON.stringify(census, null, 1) + "\n");
  console.log(JSON.stringify({ totals: c, mostDoubled: census.mostDoubled, largestShare: census.largestShare }, null, 1));
  console.log(`written to ${path.join(outDir, "census.json")}`);
  process.exit(0);
}

// ---- the dedupeHoles pairs --------------------------------------------------
const counts = { generated: new Date().toISOString().slice(0, 10), garment: base.garment, pxPerMm: base.pxPerMm, underlay: "ladder", text: TEXT, dedupeHoles: [], underlayDirection: [] };
const row = (f) => console.log(f);
row(`dedupeHoles — "${TEXT}"`);
row("font | width | cap | OFF md5 | records | stitches | doubled holes (by span kind) | ON md5 | records | doubled");
for (const key of FONTS) {
  const font = load(key);
  for (const w of WIDTHS) {
    const off = build(font, TEXT, w), on = build(font, TEXT, w, { dedupeHoles: true });
    const dOff = doubled(off), dOn = doubled(on);
    const scale = w <= 50 ? 12 : 6;
    const marksOff = dOff.at.map((i) => ({ x: off.stitches[i].x, y: off.stitches[i].y, rgb: [220, 30, 30], ring: true }));
    // ON: the same holes, laid once — found by the point, since the index moved
    const marksOn = marksOff.map((m) => ({ ...m, rgb: [30, 160, 60] }));
    const file = `${key}_${TEXT}_${w}mm_dedupeHoles.png`;
    sheet([{ design: off, marks: marksOff }, { design: on, marks: marksOn }], scale, path.join(outDir, file));
    const r = { font: key, text: TEXT, widthMm: w, capMm: +off.lettering.capMm.toFixed(2), off: { md5: md5(off), records: off.stitches.length, stitches: off.stitchCount, doubled: dOff.at.length, byKind: dOff.byKind }, on: { md5: md5(on), records: on.stitches.length, stitches: on.stitchCount, doubled: dOn.at.length }, png: file };
    counts.dedupeHoles.push(r);
    row(`${key} | ${w} mm | ${r.capMm} mm | ${r.off.md5} | ${r.off.records} | ${r.off.stitches} | ${r.off.doubled} ${JSON.stringify(dOff.byKind)} | ${r.on.md5} | ${r.on.records} | ${r.on.doubled}`);
  }
}

// ---- the underlayDirection pairs -------------------------------------------
row(`\nunderlayDirection`);
row("font | text | width | columns after an underlay | starting at the near cross (OFF) | turned by ON | OFF md5 == ON md5 | travel OFF/ON mm | thread OFF/ON mm");
const DIR_CASES = [...FONTS.flatMap((key) => WIDTHS.map((w) => [key, TEXT, w])), ["colorful", "Stitches", 100]];
for (const [key, text, w] of DIR_CASES) {
  const font = load(key);
  const off = build(font, text, w), on = build(font, text, w, { underlayDirection: true });
  const cOff = columnsAfterUnderlay(off), cOn = columnsAfterUnderlay(on);
  let turned = 0;
  for (let i = 0; i < cOff.length; i++) if (!same(cOff[i].firstStitch, cOn[i].firstStitch)) turned++;
  const r = { font: key, text, widthMm: w, columnsAfterUnderlay: cOff.length, nearStartOff: cOff.filter((c) => c.nearEnd).length, nearStartOn: cOn.filter((c) => c.nearEnd).length, turned, identical: md5(off) === md5(on), travelMm: [+travelMm(off).toFixed(1), +travelMm(on).toFixed(1)], threadMm: [+threadMm(off).toFixed(1), +threadMm(on).toFixed(1)], stitches: [off.stitchCount, on.stitchCount] };
  if (turned) {
    const marks = (cols) => cols.flatMap((c) => [{ x: c.from.x, y: c.from.y, rgb: [30, 160, 60] }, { x: c.firstStitch.x, y: c.firstStitch.y, rgb: [200, 30, 200] }]);
    r.png = `${key}_${text}_${w}mm_underlayDirection.png`;
    sheet([{ design: off, marks: marks(cOff) }, { design: on, marks: marks(cOn) }], 6, path.join(outDir, r.png));
  }
  counts.underlayDirection.push(r);
  row(`${key} | ${text} | ${w} mm | ${r.columnsAfterUnderlay} | ${r.nearStartOff} | ${r.turned} | ${r.identical} | ${r.travelMm.join("/")} | ${r.threadMm.join("/")}`);
}
fs.writeFileSync(path.join(outDir, "counts.json"), JSON.stringify(counts, null, 1) + "\n");
row(`\nwritten to ${outDir}`);
