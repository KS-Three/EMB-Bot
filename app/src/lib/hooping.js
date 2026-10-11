// What the operator hoops under this design — stabilizer, topper, needle —
// as rows for the Download sheet's hooping card.
//
// A thin adapter and nothing more: the advice itself is the engine's
// `EMB.hoopingAdvice` (src/fabrics.js), which is also what the PDF worksheet
// prints, so the screen and the sheet state one answer. Before 2026-10-01 the
// backing and topper showed ONLY on the worksheet — a customer who never
// printed it never saw them — and the needle showed nowhere.
//
// Fed the COMBINED design, so every lane gets it: lettering, hand-drawn,
// shapes, imported DST and auto-digitized alike. `stitchCount` is the same
// field the worksheet reads, which is what keeps the 25,000-stitch cutaway
// escalation firing on both or neither.
import { EMB } from "./emb.js";

// [] when there is nothing to advise on: no design, nothing sewn, a garment
// we do not ship (no basis, no claim), or a stale engine copy without the
// function — the same "no row rather than a wrong one" posture as sewSummary.
export function hoopingRows(garmentId, design) {
  if (!design || !design.stitchCount) return [];
  if (typeof EMB.hoopingAdvice !== "function") return [];
  const advice = EMB.hoopingAdvice(garmentId, design.stitchCount);
  return advice ? advice.rows : [];
}
