const units =
  typeof module !== "undefined" && module.exports
    ? require("./units.js")
    : (typeof globalThis !== "undefined" ? globalThis : this).EMB;

(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const { inToMm } = units;

  const GARMENTS = [
    { id: "hat_front", label: "Hat Front", widthIn: 5.0, heightIn: 2.25 },
    { id: "left_chest", label: "Left Chest", widthIn: 4.0, heightIn: 4.0 },
    { id: "full_back", label: "Full Back", widthIn: 12.0, heightIn: 12.0 },
    { id: "beanie", label: "Beanie", widthIn: 4.5, heightIn: 2.5 },
    { id: "sleeve", label: "Sleeve", widthIn: 3.0, heightIn: 3.0 },
    { id: "tote", label: "Tote", widthIn: 8.0, heightIn: 8.0 },
    { id: "jacket_back", label: "Jacket Back", widthIn: 12.0, heightIn: 10.0 },
    { id: "patch", label: "Patch", widthIn: 3.5, heightIn: 3.5 },
    { id: "towel", label: "Towel", widthIn: 6.0, heightIn: 6.0 },
    { id: "blanket", label: "Blanket", widthIn: 10.0, heightIn: 8.0 },
  ];

  function getGarment(id) {
    return GARMENTS.find((g) => g.id === id);
  }

  // Auto-fit box: the placement box capped to the largest hoop's usable
  // field (Kent's ruling 2026-10-13, "cap to hoop"). Four of ten placement
  // boxes (full_back, jacket_back, blanket, tote) are bigger than every hoop,
  // so fitting the whole box made every auto-fit design on them oversize.
  // Placement geometry is unchanged: drags and typed widths still clamp to the
  // full box (see hoop.js); only the AUTO size is capped. HOOP_FIT_MARGIN_MM per
  // side is held back because the sewn extent runs past the fit target by pull
  // compensation (defect 34), which would put a design fitted to exactly 200 mm
  // at 200.2 and trip the oversize check the cap exists to prevent.
  const HOOP_FIT_MARGIN_MM = 1;

  // The professional's placement boxes (2026-10-26, `proSized`): the box
  // that, auto-fitting each artwork's own aspect, best reproduces the width
  // he sewed it at, read from his stitch files by
  // `digitizer/tools/garment_size_census.py` (median width error 1.1% on 12
  // hats, 0.8% on 7 left chests). Our round-inch boxes missed him both ways:
  // a hat front 57.2 mm tall sewed 6 of his 12 hats smaller than he does (he
  // sews to 63.8), and 127 mm wide sewed his widest hats wider. The beanie's
  // height (56) is his; its width is the box his own designs fit, because his
  // two wide beanies disagree (93.8 and 110.5 mm). A garment with no entry
  // keeps its box.
  // The left chest is a width cap, a height cap AND an area cap (2026-10-27).
  // Kent, on the census's one LC miss, Bridge's square logo (he sews it
  // 76.6 x 76.5; a 64.5 box fitted it 64.5 wide, -15.8%): "Raise LC box to
  // 76.5 tall (Recommended)". A 96 x 76.5 box alone then over-fits Machine's
  // 1.385:1 LC (89.3 -> 96.0 wide against his 89.5, +7.3%), and Kent ruled
  // "Measure an area rule first (Recommended)". Of his 7 left-chest designs,
  // the three that no width cap holds -- Bridge, Machine, Becker's large --
  // are sewn at the same area of OUR artwork's box at his width, 5,868 /
  // 5,784 / 5,749 mm2 (w^2 / aspect; mean 5,800), and the ones that are
  // width-limited sit at 95.2-96.7 wide. So the fit is min(96 wide, 76.5
  // tall, `areaMm2` 5,800): Bridge 76.2 (his 76.6), Machine 89.6 (89.5),
  // every wide LC at 96. Held out one at a time, the area predicts the third
  // within 1% (-0.9 / +0.2 / +0.3). Two designs it does not explain, and no
  // box does either: Becker's "chest small" (76.5 wide, a variant he sized
  // smaller) and Gaulke Plowing's LC (89.4 against 96, +7.4%). Hats are not
  // area-limited (his areas run 3,580-6,328 and the height stops them at
  // 64), so only the left chest has an `areaMm2`.
  // DEFAULT ON since 2026-10-26. Kent, on the hat's 64 mm height against his
  // cap frames: "64 mm (2.5 in) or more" -- his frames sew it (gate 1 for hat
  // height, settled by his frames). `{ proSized: false }` is the round-inch
  // box as it was.
  const PRO_PLACEMENT_MM = {
    hat_front: { w: 113.5, h: 64.0 },
    left_chest: { w: 96.0, h: 76.5, areaMm2: 5800 },
    beanie: { w: 94.5, h: 56.0 },
  };

  // ---- Placements (2026-10-27) ---------------------------------------------
  // Review table of every garment x placement box, measured vs seeded: docs/placement-boxes-2026-10-28.md (node tools/placement-table.mjs).
  // WHERE on the garment the design sits, and the biggest box that location
  // takes. Kent, 2026-10-27: the Studio was showing a "suggested" size (which
  // only ever meant the hoop) when it should pick the design's size from the
  // placement — hat centred / left / right / side / rear, left chest / right
  // chest / full back / upper back / sleeve — as the maximum that fits there.
  //
  // One row per placement, `box` in mm. `pro` rows are the professional's
  // measured boxes (PRO_PLACEMENT_MM above, unchanged, by reference). Every
  // row marked `seeded` is a STARTING number, not a measurement: the inch
  // table above (for the ten garments' own boxes) or an industry placement
  // chart (cap side 2.5 x 1.5 in, cap back above the closure 3.5 x 1.5 in,
  // one front panel beside the centre seam 2.25 x 2 in, yoke 10 x 3 in,
  // beanie cuff 4 x 1.75 in; charts from decorators and print-on-demand
  // vendors, none of which owns the machine this sews on). Kent corrects them.
  // The right chest is the pro's left chest mirrored, area cap included.
  //
  // Each garment's DEFAULT placement carries the garment's own id, so a
  // project with no `placementId` (every one saved before today) resolves to
  // exactly the box it always had, and `fabric_for_garment` service-side
  // still reads the garment id it knows: the placement never reaches the
  // request, because the digitizer reads `garment_id` for the fabric preset
  // only (digitizer_service/app.py), and `target_width_mm` already carries
  // the size the placement chose.
  const PLACEMENTS = [
    // hats (structured cap)
    { id: "hat_front", label: "Hat front, centered", pill: "Centered", box: PRO_PLACEMENT_MM.hat_front }, // pro: 12 hats, median width error 1.1%
    { id: "hat_front_left", label: "Hat front left", pill: "Front left", box: { w: 57.2, h: 50.8 } }, // seeded: one front panel beside the seam, 2.25 x 2 in
    { id: "hat_front_right", label: "Hat front right", pill: "Front right", box: { w: 57.2, h: 50.8 } }, // seeded: mirror of hat_front_left
    { id: "hat_side_left", label: "Hat side left", pill: "Side left", box: { w: 63.5, h: 38.1 } }, // seeded: cap side above the ear, 2.5 x 1.5 in
    { id: "hat_side_right", label: "Hat side right", pill: "Side right", box: { w: 63.5, h: 38.1 } }, // seeded: mirror of hat_side_left
    { id: "hat_rear", label: "Hat rear", pill: "Rear", box: { w: 88.9, h: 38.1 } }, // seeded: above the closure, 3.5 x 1.5 in
    // shirts, sweatshirts, jackets (left_chest = polo, full_back = tee, jacket_back = jacket)
    { id: "left_chest", label: "Left chest", pill: "Left chest", box: PRO_PLACEMENT_MM.left_chest }, // pro: 7 left chests, width + height + area cap
    { id: "right_chest", label: "Right chest", pill: "Right chest", box: PRO_PLACEMENT_MM.left_chest }, // seeded: the pro's left chest mirrored
    { id: "full_back", label: "Full back", pill: "Full back", box: { w: 304.8, h: 304.8 } }, // seeded: inch table 12 x 12 in (charts: 11-12 in)
    { id: "upper_back", label: "Upper back", pill: "Upper back", box: { w: 254.0, h: 76.2 } }, // seeded: yoke below the collar, 10 x 3 in
    { id: "jacket_back", label: "Jacket back", pill: "Full back", box: { w: 304.8, h: 254.0 } }, // seeded: inch table 12 x 10 in
    { id: "sleeve", label: "Sleeve", pill: "Sleeve", box: { w: 76.2, h: 76.2 } }, // seeded: inch table 3 x 3 in
    // beanie
    { id: "beanie", label: "Beanie front", pill: "Front", box: PRO_PLACEMENT_MM.beanie }, // pro: height his, width the box his designs fit
    { id: "beanie_cuff", label: "Beanie cuff", pill: "Cuff", box: { w: 101.6, h: 44.5 } }, // seeded: the folded cuff, 4 x 1.75 in
    // single-placement garments: the inch table, as before
    { id: "tote", label: "Tote", pill: "Tote", box: { w: 203.2, h: 203.2 } }, // seeded: inch table 8 x 8 in
    { id: "patch", label: "Patch", pill: "Patch", box: { w: 88.9, h: 88.9 } }, // seeded: inch table 3.5 x 3.5 in
    { id: "towel", label: "Towel", pill: "Towel", box: { w: 152.4, h: 152.4 } }, // seeded: inch table 6 x 6 in
    { id: "blanket", label: "Blanket", pill: "Blanket", box: { w: 254.0, h: 203.2 } }, // seeded: inch table 10 x 8 in
  ];

  // The placements each garment offers, DEFAULT FIRST (its id is the
  // garment's own). A garment not listed offers only itself.
  const GARMENT_PLACEMENTS = {
    hat_front: ["hat_front", "hat_front_left", "hat_front_right", "hat_side_left", "hat_side_right", "hat_rear"],
    left_chest: ["left_chest", "right_chest", "full_back", "upper_back", "sleeve"],
    full_back: ["full_back", "left_chest", "right_chest", "upper_back", "sleeve"],
    jacket_back: ["jacket_back", "left_chest", "right_chest", "upper_back", "sleeve"],
    beanie: ["beanie", "beanie_cuff"],
  };

  function getPlacement(id) {
    return PLACEMENTS.find((p) => p.id === id);
  }

  function placementsFor(garmentId) {
    const ids = GARMENT_PLACEMENTS[garmentId] || [garmentId];
    return ids.map(getPlacement).filter(Boolean);
  }

  // The garment AS PLACED: the object every box reader below takes. For the
  // default placement (`placementId` null, unknown, or the garment's own id)
  // this is the garment itself, unchanged. For any other it is the garment
  // with the placement's box on it — `widthIn`/`heightIn` recomputed from the
  // box so the readers that still take the inch pair (digitize.js's typed
  // clamp, preview.js, dstimport.js, the worksheet) see the placement too,
  // and `label` the placement's, which is what SizePanel's "<label> area"
  // and the worksheet print.
  function resolvePlacement(garmentId, placementId) {
    const garment = getGarment(garmentId);
    if (!garment) return undefined;
    const ids = GARMENT_PLACEMENTS[garment.id] || [garment.id];
    const pid = placementId && ids.includes(placementId) ? placementId : garment.id;
    if (pid === garment.id) return garment;
    const row = getPlacement(pid);
    return {
      ...garment,
      placementId: pid,
      label: row.label,
      placementBox: row.box,
      widthIn: row.box.w / 25.4,
      heightIn: row.box.h / 25.4,
    };
  }

  function placementBoxMm(garment, opts) {
    // a resolved non-default placement: its own box, measured or seeded
    if (garment.placementBox) return { w: garment.placementBox.w, h: garment.placementBox.h };
    const pro = opts && opts.proSized === false ? null : PRO_PLACEMENT_MM[garment.id];
    return pro
      ? { w: pro.w, h: pro.h }
      : { w: inToMm(garment.widthIn), h: inToMm(garment.heightIn) };
  }

  // The area cap on the auto-fit (mm2 of the artwork's bounding box), or Infinity: only
  // the pro's left chest has one, and `{ proSized: false }` never does.
  function autoFitAreaMm2(garment, opts) {
    const pro = garment.placementBox
      ? garment.placementBox
      : opts && opts.proSized === false ? null : PRO_PLACEMENT_MM[garment.id];
    return pro && pro.areaMm2 > 0 ? pro.areaMm2 : Infinity;
  }

  function autoFitBoxMm(garment, opts) {
    const hoop = HOOPS[HOOPS.length - 1];
    const box = placementBoxMm(garment, opts);
    return {
      w: Math.min(box.w, hoop.widthMm - 2 * HOOP_FIT_MARGIN_MM),
      h: Math.min(box.h, hoop.heightMm - 2 * HOOP_FIT_MARGIN_MM),
    };
  }

  function fitScale(bboxWmm, bboxHmm, garment, opts) {
    const { w: boxW, h: boxH } = autoFitBoxMm(garment, opts);
    const scale = Math.min(boxW / bboxWmm, boxH / bboxHmm,
      Math.sqrt(autoFitAreaMm2(garment, opts) / (bboxWmm * bboxHmm)));
    return {
      scale,
      targetWmm: bboxWmm * scale,
      targetHmm: bboxHmm * scale,
    };
  }

  const TYPICAL_HOOP_MM = { w: 200, h: 200 }; // ~8in, a realistic common max hoop

  // Home-machine hoop presets (2026-07-29 market-parity roadmap, PRODUCT.md
  // item 2). Ordered smallest to largest — suggestHoop() walks this list in
  // order and takes the first fit, so the order IS the preference order.
  // Dimensions are the nominal embroidery-field sizes home machines ship
  // with (Brother/Janome/Baby Lock naming), not the physical hoop ring.
  const HOOPS = [
    { id: "4x4", label: "4×4 in", widthMm: 100, heightMm: 100 },
    { id: "5x7", label: "5×7 in", widthMm: 130, heightMm: 180 },
    { id: "6x10", label: "6×10 in", widthMm: 160, heightMm: 250 },
    { id: "8x8", label: "8×8 in", widthMm: 200, heightMm: 200 },
  ];

  function getHoop(id) {
    return HOOPS.find((h) => h.id === id);
  }

  // Orientation-aware fit check — a hoop can be mounted either way, so a
  // 170×120 design goes into a 130×180 hoop rotated 90°. Returns:
  //   "fits"    — fits the hoop as-is
  //   "rotated" — only fits if the design is rotated 90°
  //   "exceeds" — doesn't fit either way
  // Auto-rotation (actually rotating the design for the user) is a noted
  // follow-up; today the check just tells the user rotating would work.
  function hoopFit(wmm, hmm, hoop) {
    const w = hoop.widthMm != null ? hoop.widthMm : hoop.w;
    const h = hoop.heightMm != null ? hoop.heightMm : hoop.h;
    if (wmm <= w && hmm <= h) return "fits";
    if (hmm <= w && wmm <= h) return "rotated";
    return "exceeds";
  }

  // The sensible default hoop for a garment: the smallest preset whose field
  // admits the garment's full placement box in either orientation (so a cap
  // front suggests a smaller hoop than a jacket back). Placements bigger
  // than every preset (full back, blanket…) fall back to the largest hoop —
  // the design still fits IT, because fitScale clamps to the placement box
  // and the hoop check runs against the result.
  // The pro's placement box (PRO_PLACEMENT_MM) by default; `{ proSized: false }`
  // the round-inch box.
  function suggestHoop(garment, opts) {
    if (!garment) return HOOPS[HOOPS.length - 1];
    const { w: wmm, h: hmm } = placementBoxMm(garment, opts);
    for (const hoop of HOOPS) {
      if (hoopFit(wmm, hmm, hoop) !== "exceeds") return hoop;
    }
    return HOOPS[HOOPS.length - 1];
  }

  // Ceiling check. `hoop` is optional for back-compat with the pre-picker
  // call sites/tests (defaults to the old generic 200×200 ceiling); now
  // orientation-aware via hoopFit — identical results for the square
  // default, but a named rectangular hoop admits a rotated fit.
  function exceedsHoop(wmm, hmm, hoop) {
    return hoopFit(wmm, hmm, hoop || TYPICAL_HOOP_MM) === "exceeds";
  }

  return {
    GARMENTS,
    getGarment,
    fitScale,
    autoFitBoxMm,
    autoFitAreaMm2,
    placementBoxMm,
    PRO_PLACEMENT_MM,
    PLACEMENTS,
    GARMENT_PLACEMENTS,
    getPlacement,
    placementsFor,
    resolvePlacement,
    HOOP_FIT_MARGIN_MM,
    TYPICAL_HOOP_MM,
    HOOPS,
    getHoop,
    hoopFit,
    suggestHoop,
    exceedsHoop,
  };
});
