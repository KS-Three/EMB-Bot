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

  function exceedsHoop(wmm, hmm) {
    return wmm > TYPICAL_HOOP_MM.w || hmm > TYPICAL_HOOP_MM.h;
  }

  return {
    GARMENTS,
    getGarment,
    fitScale,
    TYPICAL_HOOP_MM,
    exceedsHoop,
  };
});
