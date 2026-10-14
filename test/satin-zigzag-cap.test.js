// The satin zigzag's width cap — Kent's ruling 2026-10-14.
//
// PR #904 turned `satinZigzag` ON for Studio lettering. On a wide column the
// zigzag's return leg is a full cross and carries its own split comb, so big
// text nearly doubled: manga_impact "AB" 12,492 -> 21,070 stitches at the
// 198 mm auto-fit, 27,033 -> 48,079 on a Full Back. The ruling: the zigzag
// stays only on columns narrower than satinfont.SATIN_ZIGZAG_MAX_WIDTH_MM;
// wider ones sew the pre-#904 alternating-rail stream. Small text must not
// move a stitch.
const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
global.window = global;
const SF = require("../src/satinfont.js");

const tool = () => import(pathToFileURL(path.join(__dirname, "..", "tools", "satin-zigzag-cap.mjs")).href);

// One straight column, `wMm` wide and 36 mm long at emMm 18 (100 units = 18 mm).
const colFont = (wMm) => {
  const u = (wMm / 18) * 100;
  return { unitsPerEm: 100, leading: 120, glyphs: { I: { adv: u + 20, cols: [{ railA: [[0, 0], [0, 200]], railB: [[u, 0], [u, 200]], rungs: [] }], runs: [] } } };
};
// Lay the column out at `fitScale` (the column is drawn wMm / fitScale wide, so
// it SEWS wMm), and read the satin back in final mm.
function satinSegs(wMm, fitScale, extra) {
  const lay = SF.layoutText(colFont(wMm / fitScale), "I", Object.assign({
    emMm: 18, pxPerMm: 8, spacingMm: 0.4 / fitScale, pullCompMm: 0, fitScale,
    crossFloor: true, satinZigzag: true, splitSatin: false, underlay: false,
  }, extra || {}));
  const segs = [];
  for (const r of lay.runs) if (r.kind === "satin") for (let i = 1; i < r.pts.length; i++) segs.push((Math.hypot(r.pts[i].x - r.pts[i - 1].x, r.pts[i].y - r.pts[i - 1].y) / 8) * fitScale);
  return { segs, L: lay.lettering };
}
// Zigzag: every stitch crosses the column. Alternating rails: half of them are
// 0.4 mm steps along a rail.
const railSteps = (segs) => segs.filter((l) => l < 1).length;

test("the cap is a named, exported value, and it is the split point", () => {
  assert.strictEqual(typeof SF.SATIN_ZIGZAG_MAX_WIDTH_MM, "number");
  assert.strictEqual(SF.SATIN_ZIGZAG_MAX_WIDTH_MM, 5.0, "reuses SPLIT_SATIN_ABOVE_MM; retune it in satinfont.js");
});

test("a column just under the cap zigzags; one just over it sews alternating rails", () => {
  const cap = SF.SATIN_ZIGZAG_MAX_WIDTH_MM;
  for (const fitScale of [1, 4]) {
    const under = satinSegs(cap * 0.98, fitScale), over = satinSegs(cap * 1.02, fitScale);
    assert.ok(under.segs.length > 100 && over.segs.length > 100, "both columns must sew");
    assert.strictEqual(railSteps(under.segs), 0, `fitScale ${fitScale}: under the cap every stitch crosses`);
    assert.deepStrictEqual([under.L.zigzagColumns, under.L.zigzagCapped], [1, 0]);
    assert.ok(railSteps(over.segs) > over.segs.length * 0.4, `fitScale ${fitScale}: over the cap the rail steps are back (${railSteps(over.segs)} of ${over.segs.length})`);
    assert.deepStrictEqual([over.L.zigzagColumns, over.L.zigzagCapped], [0, 1]);
  }
});

test("the switch follows the cap: a number moves it, false lifts it", () => {
  const cap = SF.SATIN_ZIGZAG_MAX_WIDTH_MM;
  // The same over-the-cap column zigzags once the cap is raised past it...
  assert.strictEqual(railSteps(satinSegs(cap * 1.02, 1, { satinZigzagMaxMm: cap * 1.1 }).segs), 0);
  // ...and the under-the-cap one stops when the cap is lowered under it.
  assert.ok(railSteps(satinSegs(cap * 0.98, 1, { satinZigzagMaxMm: cap * 0.9 }).segs) > 50);
  // `false` lifts the cap: the 2026-10-13 stream, zigzag on every column.
  assert.strictEqual(railSteps(satinSegs(cap * 3, 1, { satinZigzagMaxMm: false }).segs), 0);
  // Asking for the named value explicitly is the default, stitch for stitch.
  const f = colFont(cap * 1.02), o = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, fitScale: 1, crossFloor: true, satinZigzag: true };
  assert.deepStrictEqual(SF.layoutText(f, "I", { ...o, satinZigzagMaxMm: cap }).runs, SF.layoutText(f, "I", o).runs);
  // And with the zigzag off there is nothing to cap.
  const off = satinSegs(cap * 0.5, 1, { satinZigzag: false });
  assert.deepStrictEqual([off.L.zigzagColumns, off.L.zigzagCapped], [0, 0]);
});

test("big text sews its pre-#904 stitch counts again", async () => {
  const T = await tool();
  const f = T.loadFont(T.BIG_FONT);
  // PR #904's own rows (test/wide-columns.test.js's call): auto-fit lands at
  // 198 mm, and 1e4 is clamped to the 304.8 mm Full Back.
  const auto = T.buildBig(f, undefined), fullBack = T.buildBig(f, 1e4);
  assert.strictEqual(Math.round(auto.widthMM), 198);
  assert.strictEqual(auto.stitchCount, 12492, "21,070 with the uncapped zigzag");
  assert.strictEqual(fullBack.stitchCount, 27033, "48,079 with the uncapped zigzag");
  // Not just the count: every column there is over the cap, so the stream IS
  // the alternating-rail stream.
  for (const d of [auto, fullBack]) {
    assert.strictEqual(d.lettering.zigzagColumns, 0);
    assert.deepStrictEqual(d.stitches, T.buildBig(f, d === auto ? undefined : 1e4, { satinZigzag: false }).stitches);
  }
  // Lifting the cap gives #904's numbers back, so the harness is the same one.
  assert.strictEqual(T.buildBig(f, undefined, { satinZigzagMaxMm: false }).stitchCount, 21070);
});

// md5 of JSON.stringify(design.stitches), captured on origin/main at 929bd126
// (the 2026-10-13 zigzag-everywhere stream) BEFORE the cap existed, with
// tools/satin-zigzag-cap.mjs's census call ("Hamburgefonstiv 0123", full_back,
// weightPreset normal, cap height calibrated like tools/small-cap-census.mjs).
const SMALL_MAIN = {
  "alchemy 3": "cb30e53d0210eb91da4f233dfd598437",
  "alchemy 4.5": "fcc37cebf0472c42a08e2f77f68bf78b",
  "alchemy 6": "f828e6bc7ae97f20d1c965a23abe4b35",
  "montecarlo 3": "c25548b338a69e2edb64a5acd0630faa",
  "montecarlo 4.5": "7c4e926f3a71ab2a286d5a176a0149f5",
  "montecarlo 6": "f4f0ec4f7538ef6917e955ad16155a3b",
  "manga_impact 3": "629b4b5d2b3ba3fb9396bf3579879b19",
  "manga_impact 4.5": "3731351402471f42c255bd21e6c0a3a5",
  "manga_impact 6": "d6b10fe9059a84ec7f3e3c64f7521d1e",
};

test("small text (3 to 6 mm caps) is byte-identical to the stream before the cap", async () => {
  const T = await tool();
  for (const name of T.SMALL_FONTS) {
    const f = T.loadFont(name);
    for (const cap of T.SMALL_CAPS) {
      const d = T.buildAtCap(f, cap);
      assert.ok(Math.abs(d.lettering.capMm - cap) < 0.05, `${name} landed at ${d.lettering.capMm} mm, not ${cap}`);
      assert.ok(d.lettering.zigzagColumns > 0 && d.lettering.zigzagCapped === 0, `${name} ${cap}: every column under the cap`);
      assert.strictEqual(T.streamMd5(d), SMALL_MAIN[`${name} ${cap}`], `${name} at a ${cap} mm cap moved`);
    }
  }
});
