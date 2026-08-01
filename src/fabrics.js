(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // Fabric presets drive pull compensation, underlay style, density, and trim
  // distance. Values encode known digitizing rules; Kent's sew-outs tune them.
  // Underlay ids: none | edge_run | center_run | edge_zigzag | edge_lattice |
  //               double_lattice | zigzag
  const FABRICS = [
    {
      id: "structured_cap",
      label: "Structured cap",
      pullCompMm: 0.4,
      fillUnderlay: "edge_zigzag",
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Foam/structured cap front; firm, sew center-out.",
    },
    {
      id: "pique_knit",
      label: "Pique knit (polo)",
      pullCompMm: 0.3,
      fillUnderlay: "edge_lattice",
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Polo pique; moderate stretch.",
    },
    {
      id: "jersey_tee",
      label: "Jersey / t-shirt",
      pullCompMm: 0.35,
      fillUnderlay: "edge_lattice",
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Stretchy knit; needs solid underlay.",
    },
    {
      id: "fleece_sweatshirt",
      label: "Fleece / sweatshirt",
      pullCompMm: 0.5,
      fillUnderlay: "double_lattice",
      satinUnderlay: "zigzag",
      // Below 1.0 on purpose: this scales row SPACING, and pile needs
      // TIGHTER rows (physics law 30) -- stitches sink into the nap. Shipped
      // inverted (1.05/1.1) until 2026-08-01; see digitizer fabrics.py.
      densityAdjust: 0.90,
      trimAtMm: 3.5,
      notes: "Thick nap; heavy underlay, topping helps.",
    },
    {
      id: "canvas_tote",
      label: "Canvas / twill",
      pullCompMm: 0.2,
      fillUnderlay: "edge_run",
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Stable woven; minimal compensation.",
    },
    {
      id: "terry_towel",
      label: "Terry towel",
      pullCompMm: 0.6,
      fillUnderlay: "double_lattice",
      satinUnderlay: "zigzag",
      densityAdjust: 0.85, // pile: tighter, not looser -- see fleece note
      trimAtMm: 4.0,
      notes: "High loops; heavy underlay + topping essential.",
    },
    {
      id: "woven_dress",
      label: "Woven dress shirt",
      pullCompMm: 0.2,
      fillUnderlay: "edge_run",
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Stable woven; minimal compensation.",
    },
  ];

  function getFabric(id) {
    return FABRICS.find((f) => f.id === id);
  }

  // Default fabric per garment id. Unknown garments fall back to pique_knit.
  const GARMENT_FABRIC = {
    hat_front: "structured_cap",
    beanie: "jersey_tee",
    left_chest: "pique_knit",
    full_back: "fleece_sweatshirt",
    sleeve: "jersey_tee",
    tote: "canvas_tote",
    jacket_back: "canvas_tote",
    patch: "canvas_tote",
    towel: "terry_towel",
    blanket: "fleece_sweatshirt",
  };

  function fabricForGarment(garmentId) {
    return GARMENT_FABRIC[garmentId] || "pique_knit";
  }

  return {
    FABRICS,
    getFabric,
    fabricForGarment,
  };
});
