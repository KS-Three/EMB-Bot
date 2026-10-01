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
      // What the operator must hoop. Stated on the worksheet, never read by
      // the stitch planner — and kept field-for-field identical to
      // `digitizer/digitizer_core/fabrics.py` by `test_fabric_wire.py`,
      // which is what stops the two lanes printing different advice for the
      // same garment. See that table's comment for why these are trade
      // categories rather than gate-1 constants.
      assumedBacking: "cap_buckram",
      needsTopper: false,
      // The needle the operator loads. Advice like the two above; see
      // `hoopingAdvice` below for the source and the basis it prints.
      needle: "75/11 sharp",
    },
    // fillUnderlay was "edge_lattice" on both knits until corpus law 26
    // (docs/corpus-laws-round3-2026-08-01.md, ruled SHIPPED 2026-08-05): under
    // a fill the professional corpus runs a walk, not a crosshatch -- sparse-
    // grid tatami underlay is 7 cases in 507, and "the shipped edge_lattice
    // default is not what this corpus does" is that law verbatim. It landed in
    // digitizer/digitizer_core/fabrics.py and NOT here, so for a month the two
    // engines sewed different underlay on left_chest, beanie and sleeve.
    // Lattice stays where the law leaves it -- the pile presets below.
    // digitize.js keeps a bare `|| "edge_lattice"` for the no-fabric-at-all
    // case; that answers "no garment chosen", not "this garment", and is a
    // separate question left alone here.
    {
      id: "pique_knit",
      label: "Pique knit (polo)",
      pullCompMm: 0.3,
      fillUnderlay: "edge_run",
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Polo pique; moderate stretch.",
      assumedBacking: "cutaway",
      needsTopper: false,
      needle: "75/11 ballpoint",
    },
    {
      id: "jersey_tee",
      label: "Jersey / t-shirt",
      pullCompMm: 0.35,
      fillUnderlay: "edge_run",   // law 26, with pique_knit above
      satinUnderlay: "center_run",
      densityAdjust: 1.0,
      trimAtMm: 3.0,
      notes: "Stretchy knit; needs solid underlay.",
      assumedBacking: "cutaway",
      needsTopper: false,
      needle: "75/11 ballpoint",
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
      assumedBacking: "cutaway",
      needsTopper: true,
      needle: "75/11 ballpoint",   // sweatshirt fleece is a knit
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
      assumedBacking: "tearaway",
      needsTopper: false,
      // docs/specialty-techniques-2026-08-01.md says 80/12 for "denim /
      // canvas"; Law 21 says 75/11 and escalate for heavy goods. This preset
      // is also the patch and the tote, so it takes Law 21 (Kent, 2026-10-01).
      needle: "75/11 sharp",
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
      assumedBacking: "cutaway",
      needsTopper: true,
      needle: "75/11 sharp",   // terry is a WOVEN loop pile, not a knit
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
      assumedBacking: "tearaway",
      needsTopper: false,
      needle: "75/11 sharp",
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

  // --- Calibration profiles (2026-09-30, Kent's call) -----------------------
  //
  // A hand-port of `digitizer_core/fabrics.py`'s profile section — same three
  // keys, same arithmetic, same clamp — and `test_fabric_wire.py` RUNS both
  // and compares, because this is exactly the class of copy that drifted
  // for a month on `fillUnderlay`. Read that file's comment for the why;
  // the short form: a profile is a delta or a scale on the preset's own
  // value, clamped to the span the shipped table already sews, so it can
  // re-slot a garment within known physics and never invent a new regime.
  const PROFILE_FIELDS = ["pull_comp_delta_mm", "density_scale", "trim_at_delta_mm"];
  const PROFILE_NOOP = { pull_comp_delta_mm: 0, density_scale: 1, trim_at_delta_mm: 0 };
  const PROFILE_ROUND = 4;

  function profileClamps() {
    const span = (k) => [Math.min(...FABRICS.map((f) => f[k])), Math.max(...FABRICS.map((f) => f[k]))];
    return { pullCompMm: span("pullCompMm"), densityAdjust: span("densityAdjust"), trimAtMm: span("trimAtMm") };
  }

  // The canonical profile, or null when it changes nothing. Throws on a
  // malformed one — callers that hold persisted data catch and ignore.
  function normalizeFabricProfile(profile) {
    if (profile == null) return null;
    if (typeof profile !== "object" || Array.isArray(profile)) throw new Error("fabric profile must be an object");
    const unknown = Object.keys(profile).filter((k) => !PROFILE_FIELDS.includes(k)).sort();
    if (unknown.length) throw new Error("fabric profile: unknown field(s) " + unknown.join(", "));
    const out = {};
    for (const k of PROFILE_FIELDS) {
      const v = profile[k];
      if (v == null) continue;
      if (typeof v !== "number" || !Number.isFinite(v)) throw new Error("fabric profile." + k + " must be a finite number");
      if (v === PROFILE_NOOP[k]) continue;
      out[k] = v;
    }
    return Object.keys(out).length ? out : null;
  }

  function clamp(v, lo, hi) {
    const c = Math.min(hi, Math.max(lo, v));
    return Math.round(c * 10 ** PROFILE_ROUND) / 10 ** PROFILE_ROUND;
  }

  // `fabric` adjusted by `profile`, clamped — or the SAME object when the
  // profile is absent or a no-op, so a design that never asked for one is
  // byte-identical (test/fabrics.test.js). `profile` on the result records
  // what was applied, for whoever states which fabric is in force.
  function applyFabricProfile(fabric, profile) {
    const p = normalizeFabricProfile(profile);
    if (!fabric || !p) return fabric;
    const c = profileClamps();
    const d = p.pull_comp_delta_mm || 0;
    const sc = p.density_scale == null ? 1 : p.density_scale;
    const t = p.trim_at_delta_mm || 0;
    return {
      ...fabric,
      pullCompMm: clamp(fabric.pullCompMm + d, c.pullCompMm[0], c.pullCompMm[1]),
      densityAdjust: clamp(fabric.densityAdjust * sc, c.densityAdjust[0], c.densityAdjust[1]),
      trimAtMm: clamp(fabric.trimAtMm + t, c.trimAtMm[0], c.trimAtMm[1]),
      profile: p,
    };
  }

  // --- Hooping advice (2026-10-01, Kent's call) ------------------------------
  //
  // What the operator must hoop — stabilizer, topper, needle — from ONE
  // function, read by the Studio's hooping card and by the PDF worksheet, so
  // the screen and the sheet cannot state different advice for one design.
  // Advice to a person: no stitch planner reads any of it.
  //
  // `needle` on each preset above is playbook Law 21 [P — Tajima, Madeira,
  // Groz-Beckert, A&E]: 75/11 is the standard for 40wt thread, ballpoint on
  // knits, sharp on wovens and caps. A trade category like the backing class,
  // not a gate-1 constant — no sew-out settles whether a polo is a knit. Kent
  // left needle size OFF the sheet on 2026-09-20 and put it back on
  // 2026-10-01 with the basis printed beside it (DOCTRINE); the basis is
  // NEEDLE_BASIS, and it rides with the figure everywhere the figure goes.
  const NEEDLE_BASIS = "standard for 40wt thread";

  // Stitch count past which the advice prescribes cutaway whatever the goods
  // would otherwise take: a design this heavy needs permanent support or it
  // distorts when the hoop comes off. Craft rule [P — OESD, via docs/photo-
  // digitizing-plan-2026-07-31.md §2 row 15]. Twin of the digitizer
  // preflight's STITCHES_CUTAWAY_MIN (digitizer/digitizer_core/preflight.py)
  // — duplicated deliberately: this also serves designs that never pass
  // through the service (lettering, imports, combined multi-element
  // designs). Change one and change both. Lived in pdfsheet.js until the
  // card needed the same rule.
  const CUTAWAY_STITCHES = 25000;

  // "cap_buckram" is an id, not a sentence. The advice is read by a person.
  function backingLabel(id) {
    return String(id || "").replace(/_/g, " ");
  }

  // The advice for a garment and a finished design's stitch count, or null
  // when the garment is not one we ship — no basis, no claim.
  // `fabricForGarment` is NOT used on purpose: its pique_knit fallback is
  // right when you are about to sew and wrong when you are about to advise.
  function hoopingAdvice(garmentId, stitchCount) {
    const fabric = garmentId ? getFabric(GARMENT_FABRIC[garmentId]) : null;
    if (!fabric) return null;
    const count = stitchCount || 0;
    // The 25k rule is an ESCALATION of the garment's own backing, not the
    // only trigger: the backing class is a property of the goods.
    const escalated = count > CUTAWAY_STITCHES && fabric.assumedBacking !== "cutaway";
    const backing = escalated ? "cutaway" : fabric.assumedBacking;
    return {
      fabricId: fabric.id,
      fabricLabel: fabric.label,
      backing,
      escalated,
      topper: fabric.needsTopper,
      needle: fabric.needle,
      rows: [
        {
          label: "Stabilizer",
          value: backingLabel(backing),
          // Explicit "en-US": a PDF's text should not change with the machine
          // that generated it, and the card says the same sentence.
          note: escalated
            ? "escalated - " + count.toLocaleString("en-US") +
              " stitches; tear-away releases under this much thread"
            : "",
        },
        // Stated either way: an operator cannot tell a considered "no topper"
        // from an oversight.
        { label: "Topper", value: fabric.needsTopper ? "yes" : "no", note: "" },
        { label: "Needle", value: fabric.needle, note: NEEDLE_BASIS },
      ],
    };
  }

  // One advice row as one line of text — the worksheet's spelling.
  function hoopingLine(row) {
    return row.label + ": " + row.value + (row.note ? " (" + row.note + ")" : "");
  }

  return {
    FABRICS,
    getFabric,
    fabricForGarment,
    hoopingAdvice,
    hoopingLine,
    NEEDLE_BASIS,
    CUTAWAY_STITCHES,
    PROFILE_FIELDS,
    profileClamps,
    normalizeFabricProfile,
    applyFabricProfile,
    // Exported for callers that must tell "this garment uses the default
    // preset" from "I have never heard of this garment" — `fabricForGarment`
    // deliberately conflates them behind a pique_knit fallback, which is the
    // right answer when you are about to SEW something and the wrong one when
    // you are about to PRINT advice about it. The worksheet takes the second
    // case: no known garment, no stabilizer claim.
    GARMENT_FABRIC,
  };
});
