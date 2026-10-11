// What a saved design IS, small enough to live on its index entry — so "My
// designs" can be filtered by stitch count, colours, size and hoop without
// loading and regenerating every project (a digitized record is ~190 KB and
// text needs its font fetched first).
//
// The facts object, as stored (projects.js `facts`):
//   st   needle-down stitches — the same count as estimate.js's sewFacts and
//        the summary bar's "Stitches"
//   col  SPOOLS, the customer-facing meaning of "colors" (digitizer.js
//        spoolCount) — the caller counts them and passes the number in,
//        because that is counted from the design's own colour records and
//        this module has no business re-deriving it
//   w,h  the combined design's size in mm, to 0.1
//
// Deliberately NOT stored: which hoop it fits. That is a function of w/h and
// the hoop table, so it is derived on read — a hoop preset added later then
// applies to every design already saved.
//
// Engine-free on purpose: the hoop table and the fit rule (EMB.HOOPS,
// EMB.hoopFit — src/garments.js) are passed in by the caller.

function isNum(v) {
  return typeof v === "number" && Number.isFinite(v);
}

function round1(v) {
  return Math.round(v * 10) / 10;
}

function validFacts(f) {
  return !!f && isNum(f.st) && isNum(f.col) && isNum(f.w) && isNum(f.h);
}

// null when there is nothing to measure — an empty design has no facts, and a
// row without facts reads "not measured" rather than "0 stitches".
export function designFacts(design, spools) {
  if (!design || !Array.isArray(design.stitches)) return null;
  if (!isNum(design.widthMM) || !isNum(design.heightMM)) return null;
  let st = 0;
  for (const s of design.stitches) if (s && s.type === "stitch") st++;
  if (!st) return null;
  return { st, col: isNum(spools) ? spools : 0, w: round1(design.widthMM), h: round1(design.heightMM) };
}

// First preset the design fits, turned or not; null when it exceeds them all.
// `hoops` is ordered smallest-first (garments.js: "the order IS the
// preference order").
export function smallestHoop(facts, hoops, hoopFit) {
  if (!facts || !isNum(facts.w) || !isNum(facts.h)) return null;
  return (hoops || []).find((h) => hoopFit(facts.w, facts.h, h) !== "exceeds") || null;
}

// The line under a drawer row's name. "" for an unmeasured entry.
export function factsLine(facts, hoops, hoopFit) {
  if (!validFacts(facts)) return "";
  const hoop = smallestHoop(facts, hoops, hoopFit);
  return [
    `${facts.st.toLocaleString()} ${facts.st === 1 ? "stitch" : "stitches"}`,
    `${facts.col} ${facts.col === 1 ? "color" : "colors"}`,
    `${facts.w.toFixed(0)} × ${facts.h.toFixed(0)} mm`,
    hoop ? `fits ${hoop.label}` : "larger than every hoop",
  ].join(" · ");
}

// Does the filter ask anything only a measured design can answer?
export function hasFactCriteria(criteria) {
  const c = criteria || {};
  return isNum(c.maxStitches) || isNum(c.maxColors) || !!c.hoop;
}

// criteria: { text, maxStitches, maxColors, hoop } — every part optional.
// Returns { shown, unmeasured }: `unmeasured` is how many entries passed the
// name text but could not be judged on the fact criteria because they carry
// no facts (saved before facts existed, and not opened since). They are left
// out of `shown` and COUNTED, so the drawer can say so instead of presenting
// a short list as the whole answer.
export function filterProjects(entries, criteria, hoopFit) {
  const c = criteria || {};
  const text = typeof c.text === "string" ? c.text.trim().toLowerCase() : "";
  const byFacts = hasFactCriteria(c);
  const shown = [];
  let unmeasured = 0;
  for (const e of entries || []) {
    if (text && !String(e.name || "").toLowerCase().includes(text)) continue;
    if (byFacts) {
      const f = e.facts;
      if (!validFacts(f)) {
        unmeasured++;
        continue;
      }
      if (isNum(c.maxStitches) && f.st > c.maxStitches) continue;
      if (isNum(c.maxColors) && f.col > c.maxColors) continue;
      if (c.hoop && hoopFit(f.w, f.h, c.hoop) === "exceeds") continue;
    }
    shown.push(e);
  }
  return { shown, unmeasured };
}
