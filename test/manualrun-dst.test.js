// A drawn line, read back from the .dst it exports by an independent reader
// (pystitch), and measured in millimetres (plan
// docs/superpowers/plans/2026-10-11-manual-open-runs.md, Task 6).
//
// The chain is the Studio's own: a `kind: "run"` shape -> shapesToRegions ->
// buildQualityDesign -> encodeDST -> pystitch. Needs a Python with pystitch
// (the digitizer venv; a worktree uses the main checkout's). Skips locally
// without one and FAILS on CI, the same posture as
// crossval-stitch-formats.test.js and for the same reason: a skip nobody sees
// is not a check.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const DG = require("../src/digitize.js");
const DST = require("../src/dst.js");
const SF = require("../src/satinfont.js");

test("a drawn line sews along its path: pystitch reads every stitch on it, end to end, as a 0.73 mm bean", async (t) => {
  const harness = await import("../tools/crossval-stitch-formats.mjs");
  const python = harness.resolvePython();
  if (!python) {
    if (process.env.CI) throw new Error("no python with pystitch available, and CI is set");
    t.skip("no python with pystitch available");
    return;
  }
  const MS = await import("../app/src/lib/manualShapes.js");
  // A bent line with one curved segment, the way Line mode records it.
  const line = { id: "s1", kind: "run", points: [{ x: 50, y: 300 }, { x: 300, y: 100 }, { x: 550, y: 250 }], curves: { 1: { x: 450, y: 60 } }, colorRgb: [20, 20, 20] };
  const { regions, pxPerMm } = MS.shapesToRegions([line]);
  const d = DG.buildQualityDesign(regions, { garment: { widthIn: 8, heightIn: 8 }, pxPerMm, targetWidthMm: 60, underlay: true, darkOnTop: false });
  assert.deepStrictEqual(d.runs.map((r) => r.kind), ["run"]);

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "manualrun-dst-"));
  const file = path.join(dir, "line.dst");
  fs.writeFileSync(file, Buffer.from(DST.encodeDST(d)));
  const decoded = harness.pyDecode(python, [file])["line.dst"];
  assert.ok(decoded && !decoded.error, JSON.stringify(decoded && decoded.error));

  // pystitch: 0.1 mm units, +Y down. The path: authored px through the
  // engine's own fit into field mm (+Y up).
  const sts = decoded.stitches.filter((s) => s[2] === "STITCH").map(([x, y]) => ({ x: x / 10, y: -y / 10 }));
  const f = d.fit;
  const pathMm = MS.runPath(line).map((q) => ({ x: (q.x - f.cxPx) * f.mmPerPx + f.offsetXMm, y: (f.cyPx - q.y) * f.mmPerPx + f.offsetYMm }));
  const distTo = (p) => {
    let best = Infinity;
    for (let i = 0; i < pathMm.length - 1; i++) {
      const a = pathMm[i], b = pathMm[i + 1];
      const dx = b.x - a.x, dy = b.y - a.y, L2 = dx * dx + dy * dy;
      const u = L2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2)) : 0;
      best = Math.min(best, Math.hypot(p.x - (a.x + u * dx), p.y - (a.y + u * dy)));
    }
    return best;
  };
  let pathLen = 0;
  for (let i = 1; i < pathMm.length; i++) pathLen += Math.hypot(pathMm[i].x - pathMm[i - 1].x, pathMm[i].y - pathMm[i - 1].y);
  assert.ok(pathLen > 50, "a real line: " + pathLen.toFixed(1) + " mm");

  // On the path: every stitch within 0.15 mm (the 0.1 mm grid's rounding).
  const worst = Math.max(...sts.map(distTo));
  assert.ok(worst <= 0.15, "worst stitch off the path: " + worst.toFixed(3) + " mm");
  // End to end: the bean starts on the path's start and finishes on its end.
  const near = (p, q) => Math.hypot(p.x - q.x, p.y - q.y);
  assert.ok(near(sts[0], pathMm[0]) <= 0.15, "starts at the start: " + near(sts[0], pathMm[0]).toFixed(3));
  assert.ok(near(sts[sts.length - 1], pathMm[pathMm.length - 1]) <= 0.15, "ends at the end");
  // A true bean: three passes, so the thread laid is three path lengths.
  let sewn = 0;
  const lens = [];
  for (let i = 1; i < sts.length; i++) { const l = near(sts[i], sts[i - 1]); sewn += l; if (l > 0) lens.push(l); }
  assert.ok(Math.abs(sewn / (3 * pathLen) - 1) <= 0.02, "thread laid " + sewn.toFixed(1) + " mm vs 3 x " + pathLen.toFixed(1));
  // At the corpus stitch length.
  lens.sort((a, b) => a - b);
  const median = lens[Math.floor(lens.length / 2)];
  assert.ok(Math.abs(median - SF.LETTERING_GUARDS.BEAN_STITCH_MM) <= 0.1, "median stitch " + median.toFixed(3) + " mm");
  // One unbroken line: no trim anywhere in it.
  assert.strictEqual(decoded.counts.TRIM || 0, 0);
  t.diagnostic(`stitches=${sts.length} path=${pathLen.toFixed(2)}mm sewn=${sewn.toFixed(2)}mm median=${median.toFixed(3)}mm worst=${worst.toFixed(3)}mm`);
});
