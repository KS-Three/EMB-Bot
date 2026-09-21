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
  function sewTimeMin(stitches, trims) {
    if (typeof stitches !== "number" || !isFinite(stitches) || stitches < 0) return null;
    if (typeof trims !== "number" || !isFinite(trims) || trims < 0) return null;
    const equivalent = stitches + trims * TRIM_COST_STITCHES;
    if (equivalent <= 0) return 0;
    // Floor of one minute once there IS work: a 200-stitch monogram is 18
    // seconds, and printing "0 min" for it reads as "nothing to do" rather
    // than "under a minute".
    return Math.max(1, Math.round(equivalent / PLAN_SPM));
  }

  return { PLAN_SPM, TRIM_COST_STITCHES, sewTimeMin };
});
