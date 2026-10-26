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
  // DEFAULT ON since 2026-10-26. Kent, on the hat's 64 mm height against his
  // cap frames: "64 mm (2.5 in) or more" -- his frames sew it (gate 1 for hat
  // height, settled by his frames). `{ proSized: false }` is the round-inch
  // box as it was.
  const PRO_PLACEMENT_MM = {
    hat_front: { w: 113.5, h: 64.0 },
    left_chest: { w: 96.0, h: 64.5 },
    beanie: { w: 94.5, h: 56.0 },
  };

  function placementBoxMm(garment, opts) {
    const pro = opts && opts.proSized === false ? null : PRO_PLACEMENT_MM[garment.id];
    return pro
      ? { w: pro.w, h: pro.h }
      : { w: inToMm(garment.widthIn), h: inToMm(garment.heightIn) };
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
    const scale = Math.min(boxW / bboxWmm, boxH / bboxHmm);
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
    placementBoxMm,
    PRO_PLACEMENT_MM,
    HOOP_FIT_MARGIN_MM,
    TYPICAL_HOOP_MM,
    HOOPS,
    getHoop,
    hoopFit,
    suggestHoop,
    exceedsHoop,
  };
});
