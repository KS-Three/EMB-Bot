const assert = require("node:assert");
const { test } = require("node:test");
const g = require("../src/garments.js");

test("garment list has left_chest default 4x4", () => {
  const lc = g.getGarment("left_chest");
  assert.deepStrictEqual([lc.widthIn, lc.heightIn], [4.0, 4.0]);
  assert.strictEqual(g.GARMENTS.length, 10);
});
test("fit scales down to fit box, aspect preserved", () => {
  // bbox 100x50mm into left_chest (4in=101.6mm square)
  const r = g.fitScale(100, 50, g.getGarment("left_chest"), { proSized: false });
  assert.ok(r.scale > 1.0 && r.scale < 1.02); // width-limited ~1.016
  assert.ok(Math.abs(r.targetWmm - 101.6) < 0.5);
  assert.ok(Math.abs(r.targetHmm - 50 * r.scale) < 1e-6);
  // ... and by default into the pro's 96 x 76.5 left chest, area 5,800 mm2 (2026-10-26; 2026-10-27)
  const pro = g.fitScale(100, 50, g.getGarment("left_chest"));
  assert.ok(Math.abs(pro.targetWmm - 96.0) < 1e-9 && Math.abs(pro.targetHmm - 48.0) < 1e-9);
});
test("fit scales large design down", () => {
  const r = g.fitScale(400, 400, g.getGarment("left_chest"));
  assert.ok(r.scale < 1);
  assert.ok(r.targetWmm <= 101.6 + 1e-6);
});
test("exceedsHoop", () => {
  assert.strictEqual(g.exceedsHoop(400, 100), true);
  assert.strictEqual(g.exceedsHoop(100, 100), false);
});

// ---- Hoop presets (launch checklist item 2) --------------------------------

test("hoop presets: the four home-machine sizes, smallest first", () => {
  assert.deepStrictEqual(
    g.HOOPS.map((h) => [h.id, h.widthMm, h.heightMm]),
    [
      ["4x4", 100, 100],
      ["5x7", 130, 180],
      ["6x10", 160, 250],
      ["8x8", 200, 200],
    ]
  );
  for (const h of g.HOOPS) assert.ok(h.label && h.label.includes("in"));
});

test("getHoop finds a preset by id, undefined otherwise", () => {
  assert.strictEqual(g.getHoop("5x7").widthMm, 130);
  assert.strictEqual(g.getHoop("9x9"), undefined);
  assert.strictEqual(g.getHoop(null), undefined);
});

test("hoopFit is orientation-aware: a 170x120 design goes into a 130x180 hoop rotated", () => {
  const h57 = g.getHoop("5x7");
  assert.strictEqual(g.hoopFit(120, 170, h57), "fits");
  assert.strictEqual(g.hoopFit(170, 120, h57), "rotated");
  assert.strictEqual(g.hoopFit(170, 190, h57), "exceeds");
  // exact-fit boundary counts as fitting
  assert.strictEqual(g.hoopFit(130, 180, h57), "fits");
});

test("suggestHoop picks the smallest preset that admits the placement box", () => {
  // sleeve 3x3in (76.2mm sq) -> 4x4; hat_front 5x2.25in (127x57.15) -> 5x7
  assert.strictEqual(g.suggestHoop(g.getGarment("sleeve")).id, "4x4");
  assert.strictEqual(g.suggestHoop(g.getGarment("patch")).id, "4x4");
  assert.strictEqual(g.suggestHoop(g.getGarment("hat_front")).id, "5x7");
  assert.strictEqual(g.suggestHoop(g.getGarment("towel")).id, "6x10");
});

test("suggestHoop falls back to the largest hoop for over-size placements (and no garment)", () => {
  // full_back 12x12in (304.8mm sq) exceeds every preset
  assert.strictEqual(g.suggestHoop(g.getGarment("full_back")).id, "8x8");
  assert.strictEqual(g.suggestHoop(null).id, "8x8");
});

test("exceedsHoop against a chosen hoop is the orientation-aware ceiling", () => {
  const h44 = g.getHoop("4x4");
  assert.strictEqual(g.exceedsHoop(120, 80, h44), true);
  assert.strictEqual(g.exceedsHoop(99, 99, h44), false);
  // rotated fit is NOT an excess — the message layer tells the user to rotate
  assert.strictEqual(g.exceedsHoop(170, 120, g.getHoop("5x7")), false);
});

// ---- proSized: the pro's placement boxes (2026-10-26; DEFAULT ON since Kent's
// "64 mm (2.5 in) or more", 2026-10-26) -----------------------------------------

test("proSized is the default; { proSized: false } is the round-inch box as it was", () => {
  const boxes = [[100, 50], [50, 100], [400, 400], [62.6, 63.8], [114.3, 42.2], [10, 300]];
  for (const garment of g.GARMENTS) {
    for (const [w, h] of boxes) {
      const on = g.fitScale(w, h, garment, { proSized: true });
      assert.deepStrictEqual(g.fitScale(w, h, garment), on);
      assert.deepStrictEqual(g.fitScale(w, h, garment, {}), on);
    }
    assert.deepStrictEqual(g.autoFitBoxMm(garment), g.autoFitBoxMm(garment, { proSized: true }));
    assert.strictEqual(g.suggestHoop(garment), g.suggestHoop(garment, { proSized: true }));
  }
  // the round-inch numbers, pinned: a hat front is 5.0 x 2.25 in
  const hat = g.autoFitBoxMm(g.getGarment("hat_front"), { proSized: false });
  assert.ok(Math.abs(hat.w - 127.0) < 1e-9 && Math.abs(hat.h - 57.15) < 1e-9);
  assert.deepStrictEqual(g.autoFitBoxMm(g.getGarment("hat_front")), { w: 113.5, h: 64.0 });
});

test("proSized ON: a hat sews as tall as the pro's (Becker 62.1, Drone 63.8 against our 57.2)", () => {
  const hat = g.getGarment("hat_front");
  // Becker's art (ink aspect 1.593) and the Drone's (0.97): height-limited
  const becker = g.fitScale(159.3, 100, hat);
  assert.ok(becker.targetHmm > 62 && becker.targetHmm <= 64.0 + 1e-9);
  assert.ok(Math.abs(becker.targetWmm / 101.9 - 1) < 0.02, `${becker.targetWmm}`);
  const drone = g.fitScale(97, 100, hat);
  assert.ok(Math.abs(drone.targetHmm - 64.0) < 1e-9);
  // ... and a wide one no wider than his widest (Tires 114.3, ours today 127)
  const tires = g.fitScale(270.2, 100, hat);
  assert.ok(Math.abs(tires.targetWmm - 113.5) < 1e-9);
  assert.ok(g.fitScale(270.2, 100, hat, { proSized: false }).targetWmm > 126.9);
});

test("proSized ON: left chest and beanie boxes; a garment with no pro box keeps its own", () => {
  const lc = g.autoFitBoxMm(g.getGarment("left_chest"), { proSized: true });
  assert.deepStrictEqual(lc, { w: 96.0, h: 76.5 });
  const beanie = g.autoFitBoxMm(g.getGarment("beanie"), { proSized: true });
  assert.deepStrictEqual(beanie, { w: 94.5, h: 56.0 });
  for (const id of ["full_back", "sleeve", "tote", "jacket_back", "patch", "towel", "blanket"]) {
    const garment = g.getGarment(id);
    assert.deepStrictEqual(g.autoFitBoxMm(garment, { proSized: true }), g.autoFitBoxMm(garment), id);
  }
  // still capped to the largest hoop's field
  for (const id of Object.keys(g.PRO_PLACEMENT_MM)) {
    const b = g.autoFitBoxMm(g.getGarment(id), { proSized: true });
    assert.ok(b.w <= 198 && b.h <= 198);
  }
});

test("proSized ON: the suggested hoop follows the pro's box (a 96 x 76.5 left chest fits a 4x4)", () => {
  assert.strictEqual(g.suggestHoop(g.getGarment("left_chest"), { proSized: false }).id, "5x7");
  assert.strictEqual(g.suggestHoop(g.getGarment("left_chest")).id, "4x4");
  assert.strictEqual(g.suggestHoop(g.getGarment("hat_front"), { proSized: true }).id, "5x7");
  assert.strictEqual(g.suggestHoop(g.getGarment("beanie"), { proSized: true }).id, "4x4");
});

// ---- the left chest: 96 wide, 76.5 tall, and an area cap (2026-10-27). Kent, on Bridge LC (he sews it 76.6 x 76.5; the
// 64.5 box fitted it 64.5 wide, -15.8%): "Raise LC box to 76.5 tall (Recommended)"; then, with the box alone sending
// Machine's LC to 96.0 against his 89.5: "Measure an area rule first (Recommended)" ---------------------------

const LC_JOBS = [   // [art aspect (w/h), the pro's sewn width mm]; digitizer/tools/garment_size_census.py
  ["becker_lc_large", 1.593, 95.7], ["bridge_lc", 1.0, 76.6], ["c_gaulke_plowing_lc", 2.429, 95.2],
  ["gaulke_roofing_lc", 2.352, 95.2], ["machine_lc", 1.385, 89.5], ["mfab_lc", 2.636, 96.7],
];

test("proSized ON: the left chest sews at the pro's area, 5,800 mm2, capped at 96 wide and 76.5 tall", () => {
  const lc = g.getGarment("left_chest");
  assert.strictEqual(g.autoFitAreaMm2(lc), 5800);
  assert.deepStrictEqual(g.autoFitBoxMm(lc), { w: 96.0, h: 76.5 });
  // squarish art is area-limited: a square is 76.2 x 76.2, not the box's 76.5 x 76.5
  const sq = g.fitScale(100, 100, lc);
  assert.ok(Math.abs(sq.targetWmm - Math.sqrt(5800)) < 1e-9 && Math.abs(sq.targetHmm - Math.sqrt(5800)) < 1e-9);
  // wide art is width-limited at 96, its area under the cap
  const wide = g.fitScale(240, 100, lc);
  assert.ok(Math.abs(wide.targetWmm - 96.0) < 1e-9 && wide.targetWmm * wide.targetHmm < 5800);
  // tall art is height-limited at 76.5
  const tall = g.fitScale(50, 100, lc);
  assert.ok(Math.abs(tall.targetHmm - 76.5) < 1e-9 && tall.targetWmm * tall.targetHmm < 5800);
});

test("proSized ON: Bridge LC lands at 76.2 (his 76.6; the 64.5 box gave 64.5) and Machine LC at 89.6 (his 89.5)", () => {
  const lc = g.getGarment("left_chest");
  const bridge = g.fitScale(100, 100, lc).targetWmm, machine = g.fitScale(138.5, 100, lc).targetWmm;
  assert.ok(Math.abs(bridge / 76.6 - 1) < 0.01, `bridge ${bridge}`);
  assert.ok(Math.abs(machine / 89.5 - 1) < 0.005, `machine ${machine}`);
  // the 96 x 76.5 box alone would have sewn Machine at 96.0 (+7.3%): the area is what holds it
  assert.ok(Math.abs(Math.min(96.0, 76.5 * 1.385) / 89.5 - 1) > 0.07);
});

test("proSized ON: every paired left chest is within 1% of his width, bar the two he sizes his own way (Becker's chest small, Gaulke Plowing's)", () => {
  const lc = g.getGarment("left_chest");
  for (const [id, aspect, proW] of LC_JOBS) {
    const w = g.fitScale(aspect * 100, 100, lc).targetWmm;
    assert.ok(Math.abs(w / proW - 1) < 0.01, `${id}: ${w} against ${proW}`);
  }
});

test("proSized false: the round-inch left chest has no area cap, and no other garment has one", () => {
  const lc = g.getGarment("left_chest");
  assert.strictEqual(g.autoFitAreaMm2(lc, { proSized: false }), Infinity);
  for (const garment of g.GARMENTS) {
    if (garment.id !== "left_chest") assert.strictEqual(g.autoFitAreaMm2(garment), Infinity, garment.id);
  }
  // 4 in square, unchanged: a square sews 101.6 wide
  assert.ok(Math.abs(g.fitScale(100, 100, lc, { proSized: false }).targetWmm - 101.6) < 1e-9);
  // and the area cap never touches a hat, which the height stops at 64
  assert.deepStrictEqual(g.fitScale(100, 100, g.getGarment("hat_front")), g.fitScale(100, 100, g.getGarment("hat_front"), { proSized: true }));
});

// ---- Placements (2026-10-27) ------------------------------------------------

test("every garment's default placement is its own id, first, and its box is the garment's box", () => {
  for (const garment of g.GARMENTS) {
    const rows = g.placementsFor(garment.id);
    assert.ok(rows.length >= 1, garment.id);
    assert.strictEqual(rows[0].id, garment.id);
    // the table row says what placementBoxMm has always said for the garment,
    // so the table cannot drift from the box the default placement sews to
    const box = g.placementBoxMm(garment);
    assert.ok(Math.abs(rows[0].box.w - box.w) < 1e-9 && Math.abs(rows[0].box.h - box.h) < 1e-9, `${garment.id}: ${rows[0].box.w}x${rows[0].box.h} vs ${box.w}x${box.h}`);
    // ... and the default resolves to the garment object itself: nothing changes
    assert.strictEqual(g.resolvePlacement(garment.id, null), garment);
    assert.strictEqual(g.resolvePlacement(garment.id, garment.id), garment);
    assert.strictEqual(g.resolvePlacement(garment.id, "no_such_placement"), garment);
  }
  assert.strictEqual(g.resolvePlacement("no_such_garment", "hat_rear"), undefined);
});

test("the three pro-measured boxes are the pro's, by reference", () => {
  assert.strictEqual(g.getPlacement("hat_front").box, g.PRO_PLACEMENT_MM.hat_front);
  assert.strictEqual(g.getPlacement("left_chest").box, g.PRO_PLACEMENT_MM.left_chest);
  assert.strictEqual(g.getPlacement("beanie").box, g.PRO_PLACEMENT_MM.beanie);
  assert.deepStrictEqual(g.PRO_PLACEMENT_MM.hat_front, { w: 113.5, h: 64.0 });
  assert.deepStrictEqual(g.PRO_PLACEMENT_MM.left_chest, { w: 96.0, h: 76.5, areaMm2: 5800 });
  assert.deepStrictEqual(g.PRO_PLACEMENT_MM.beanie, { w: 94.5, h: 56.0 });
});

test("placement ids are unique and every garment's list names real rows", () => {
  const ids = g.PLACEMENTS.map((p) => p.id);
  assert.strictEqual(new Set(ids).size, ids.length);
  for (const [gid, list] of Object.entries(g.GARMENT_PLACEMENTS)) {
    assert.ok(g.getGarment(gid), gid);
    for (const pid of list) assert.ok(g.getPlacement(pid), `${gid}: ${pid}`);
  }
  for (const p of g.PLACEMENTS) assert.ok(p.box.w > 0 && p.box.h > 0 && p.label && p.pill, p.id);
});

test("a hat's rear placement resolves to the hat with the rear box, in mm and in inches", () => {
  const rear = g.resolvePlacement("hat_front", "hat_rear");
  assert.strictEqual(rear.id, "hat_front"); // still the garment: fabric preset, art, request
  assert.strictEqual(rear.placementId, "hat_rear");
  assert.strictEqual(rear.label, "Hat rear");
  assert.deepStrictEqual(g.placementBoxMm(rear), { w: 88.9, h: 38.1 });
  assert.ok(Math.abs(rear.widthIn * 25.4 - 88.9) < 1e-9 && Math.abs(rear.heightIn * 25.4 - 38.1) < 1e-9);
  // proSized:false is the inch fallback for the DEFAULT placement only; a
  // non-default placement has one box
  assert.deepStrictEqual(g.placementBoxMm(rear, { proSized: false }), { w: 88.9, h: 38.1 });
  assert.strictEqual(g.autoFitAreaMm2(rear), Infinity);
  // and fitScale fits the artwork's aspect into THAT box: a 2:1 logo is width-bound at 88.9
  const fit = g.fitScale(200, 100, rear);
  assert.ok(Math.abs(fit.targetWmm - 76.2) < 1e-9, `height-bound: 38.1 * 2 = ${fit.targetWmm}`);
  const wide = g.fitScale(400, 100, rear);
  assert.ok(Math.abs(wide.targetWmm - 88.9) < 1e-9);
});

test("a tee's left chest is the pro's left chest, area cap included", () => {
  const lc = g.resolvePlacement("full_back", "left_chest");
  assert.strictEqual(lc.id, "full_back");
  assert.deepStrictEqual(g.placementBoxMm(lc), { w: 96.0, h: 76.5 });
  assert.strictEqual(g.autoFitAreaMm2(lc), 5800);
  // a square logo: area-bound at sqrt(5800) = 76.16, under both the 96 and the 76.5
  const fit = g.fitScale(100, 100, lc);
  assert.ok(Math.abs(fit.targetWmm - Math.sqrt(5800)) < 1e-9, String(fit.targetWmm));
  // the right chest mirrors it
  const rc = g.resolvePlacement("left_chest", "right_chest");
  assert.deepStrictEqual(g.fitScale(100, 100, rc), fit);
  // suggestHoop follows the placement: a tee's left chest wants the 4x4, its full back the 8x8
  assert.strictEqual(g.suggestHoop(lc).id, "4x4");
  assert.strictEqual(g.suggestHoop(g.getGarment("full_back")).id, "8x8");
});
