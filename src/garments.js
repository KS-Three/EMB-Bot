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

  function fitScale(bboxWmm, bboxHmm, garment) {
    const boxW = inToMm(garment.widthIn);
    const boxH = inToMm(garment.heightIn);
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
  function suggestHoop(garment) {
    if (!garment) return HOOPS[HOOPS.length - 1];
    const wmm = inToMm(garment.widthIn);
    const hmm = inToMm(garment.heightIn);
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
    TYPICAL_HOOP_MM,
    HOOPS,
    getHoop,
    hoopFit,
    suggestHoop,
    exceedsHoop,
  };
});
