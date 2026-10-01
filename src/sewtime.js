(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // How long the machine is busy — the missing half of the cost card.
  //
  // The worksheet and the review screen have always been able to say how many
  // stitches, how many stops and how many metres of thread a design costs,
  // and never how long it takes. That is the number a shop schedules on, and
  // the one that decides whether a stop-heavy design is worth re-digitizing:
  // machine-physics playbook law 36 puts trims and colour stops in the
  // "unbilled margin loss" column precisely because they cost time that the
  // stitch count does not show.
  //
  // PLANNING FIGURE, NOT A MEASUREMENT. Both constants below are trade
  // tables, and the playbook rates them "high confidence on mechanism, medium
  // on constants" — so everything that prints this number prints its basis
  // beside it ("at 650 spm, incl. trims") rather than letting it read as
  // something this repo measured. Nothing here touches geometry: like
  // `THREAD_LENGTH_FACTOR`, it changes what the operator is told and never
  // where a needle goes, so ROADMAP gate 1 does not apply.

  // Planning speed, not the nameplate. A machine rated 1,000-1,200 spm does
  // not hold it: firmware slows for stitches over 3-4 mm, and top speed
  // spikes thread tension. [P] Tajima TMEZ, HAPPY workbook; [T] Embroidery
  // Legacy. Twin of `machine.PLAN_SPM` in the Python engine.
  const PLAN_SPM = 650;

  // What one trim costs, in stitch-equivalents: the trimmer fires, the
  // machine repositions, and the operator's colour-stop handling rides on
  // top. ~120 stitches at the plan rate is ~11 s. Twin of
  // `machine.TRIM_COST_STITCHES`.
  const TRIM_COST_STITCHES = 120;

  // -> whole minutes, or null when the inputs cannot support a figure.
  //
  // `null` rather than 0 on bad input, deliberately, and for the same reason
  // `estimate.js` returns null metres without a thread factor: a plausible
  // wrong number on a sheet an operator schedules from is worse than a row
  // that is simply absent. Callers drop the line.
  //
  // `spm` is the speed the OPERATOR runs at, when they have said (2026-10-01,
  // the quote settings); omitted, it is the plan rate and the figure is the
  // one this has always returned. It divides the stitches and NOT the stops:
  // a trim is a stretch of clock — trimmer, reposition — and "120
  // stitch-equivalents" is that clock expressed at the plan rate (~11 s).
  // Dividing it by a faster speed would say the trimmer got quicker because
  // the head did. A speed that is present and not a positive number is a bad
  // input like any other: null.
  //
  // `trims` is every stop the caller counted. A colour change is one too —
  // law 36: "a color change ≈ trim + constant" — and no maker publishes the
  // constant (searched 2026-10-01: Tajima, Barudan, Melco, Happy, Brother,
  // SmartStitch give no seconds for either), so a change is counted as a trim
  // and nothing more. That under-counts it. It is still closer than the zero
  // it was counted as before.
  function sewTimeMin(stitches, trims, spm) {
    if (typeof stitches !== "number" || !isFinite(stitches) || stitches < 0) return null;
    if (typeof trims !== "number" || !isFinite(trims) || trims < 0) return null;
    const rate = spm === undefined ? PLAN_SPM : spm;
    if (typeof rate !== "number" || !isFinite(rate) || rate <= 0) return null;
    const minutes = stitches / rate + (trims * TRIM_COST_STITCHES) / PLAN_SPM;
    if (minutes <= 0) return 0;
    // Floor of one minute once there IS work: a 200-stitch monogram is 18
    // seconds, and printing "0 min" for it reads as "nothing to do" rather
    // than "under a minute".
    return Math.max(1, Math.round(minutes));
  }

  // Bobbin (under) thread per 1,000 stitches, in metres. [P] Madeira: "For
  // standard length stitches the general rule for underthread requirement is
  // approximately 3m per 1000 stitches" (madeira.co.uk/bobbins-underthreads;
  // madeira.com's FAQ gives 3-3.5). Coats puts it at 2.3. Playbook law 38
  // carries the same 3. Same standing as the two constants above: a thread
  // maker's table, printed with its basis, never measured here. No Python
  // twin — the service quotes no bobbin figure.
  const BOBBIN_M_PER_1000 = 3;

  // -> metres of bobbin thread, or null. Metres and not "bobbin changes":
  // how much a bobbin holds depends on whose it is (Fil-Tec's L is 130 yd,
  // Madeira's 123 m, and black holds less than white), and at 3 m per 1,000
  // one piece is almost never a whole bobbin anyway.
  function bobbinM(stitches) {
    if (typeof stitches !== "number" || !isFinite(stitches) || stitches < 0) return null;
    return (stitches / 1000) * BOBBIN_M_PER_1000;
  }

  return { PLAN_SPM, TRIM_COST_STITCHES, BOBBIN_M_PER_1000, sewTimeMin, bobbinM };
});
