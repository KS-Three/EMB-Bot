// Short stitches on the inside of tight satin curves (src/satin.js, opt-in).
const test = require("node:test");
const assert = require("node:assert");
const S = require("../src/satin.js");
const { LETTERING_GUARDS: G } = require("../src/satinfont.js");

const PX = 10;
// A 180-degree annular arc: inner radius rMm, width wMm.
function arc(rMm, wMm) {
  const R0 = rMm * PX, R1 = (rMm + wMm) * PX, ring = [], n = 120;
  for (let i = 0; i <= n; i++) { const a = (Math.PI * i) / n; ring.push({ x: R1 * Math.cos(a), y: R1 * Math.sin(a) }); }
  for (let i = n; i >= 0; i--) { const a = (Math.PI * i) / n; ring.push({ x: R0 * Math.cos(a), y: R0 * Math.sin(a) }); }
  return ring;
}
// Same-rail gaps (mm) between consecutive stations' penetrations.
function sameRailGaps(out) {
  const d = [];
  for (let k = 0; k + 3 < out.length; k += 2) {
    if (out[k + 2].travel) continue;
    const h = (p, q) => Math.hypot(p.x - q.x, p.y - q.y) / PX;
    const [a, b, c, e] = [out[k], out[k + 1], out[k + 2], out[k + 3]];
    const m1 = [h(a, c), h(b, e)], m2 = [h(a, e), h(b, c)];
    d.push(Math.min(...(m1[0] + m1[1] <= m2[0] + m2[1] ? m1 : m2)));
  }
  return d;
}
const SS = { atMm: G.SHORT_STITCH_AT_MM, pull: G.SHORT_STITCH_PULL, maxMm: G.SHORT_STITCH_MAX_MM };

for (const fn of ["medialSatin", "satinColumn"]) {
  test(`${fn}: short stitches thin the stacked inner-rail penetrations on a tight arc`, () => {
    const base = { spacingMm: 0.4, pxPerMm: PX };
    for (const [r, w] of [[1, 3], [3, 4]]) {
      const off = sameRailGaps(S[fn](arc(r, w), base)).filter((g) => g < G.SHORT_STITCH_AT_MM).length;
      const stats = {};
      const on = sameRailGaps(S[fn](arc(r, w), Object.assign({ shortStitch: Object.assign({ stats }, SS) }, base)))
        .filter((g) => g < G.SHORT_STITCH_AT_MM).length;
      assert.ok(off >= 8, `${fn} r=${r}: expected stacking without the option, got ${off}`);
      assert.ok(on * 4 <= off, `${fn} r=${r}: ${off} -> ${on} crowded penetrations`);
      assert.ok(stats.shortStitches > 0);
    }
  });

  test(`${fn}: default (no shortStitch) output is byte-identical`, () => {
    const base = { spacingMm: 0.4, pxPerMm: PX, pullCompMm: 0.2 };
    const a = JSON.stringify(S[fn](arc(1, 3), base));
    assert.strictEqual(JSON.stringify(S[fn](arc(1, 3), Object.assign({ shortStitch: null }, base))), a);
    assert.strictEqual(JSON.stringify(S[fn](arc(1, 3), Object.assign({ shortStitch: { atMm: 0 } }, base))), a);
  });
}

test("short stitch never pulls a cross under minCrossMm", () => {
  const out = S.satinColumn(arc(1, 0.8), { spacingMm: 0.4, pxPerMm: PX, minCrossMm: 0.7, shortStitch: SS });
  const base = S.satinColumn(arc(1, 0.8), { spacingMm: 0.4, pxPerMm: PX });
  for (let k = 0; k + 1 < out.length; k += 2) {
    const c = Math.hypot(out[k].x - out[k + 1].x, out[k].y - out[k + 1].y) / PX;
    const c0 = Math.hypot(base[k].x - base[k + 1].x, base[k].y - base[k + 1].y) / PX;
    assert.ok(c >= Math.min(c0, 0.7) - 1e-6, `cross ${k / 2}: ${c} from ${c0}`);
  }
});
