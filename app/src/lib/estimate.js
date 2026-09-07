// What a design will cost to sew, computed in the browser from the design the
// browser already has.
//
// It exists because the two lanes told the customer different amounts. An
// auto-digitized design comes back from the service with `preflight`/`stats`,
// and `QualityReport` prints "N stitches · N thread changes · N trims · N m of
// thread" — the four facts an operator needs before loading a machine. A
// lettering, hand-drawn, shape or imported-DST design never reaches the
// service, so the review screen for it showed the garment, the hoop, the
// content and the font, and **not one number**. Measured 2026-09-07 by walking
// the Review step with a text design: `section.quality` absent, no mention of
// thread, metres or trims anywhere on the page.
//
// ---- the basis, and why it is exactly this ------------------------------
//
// THREAD PATH is the sum of the distances between consecutive sewn stitches
// with the chain broken at every jump, trim and colour change — the same walk
// `designToStrands` does, and the same quantity Python's `StitchRun.length_mm`
// sums per run. Multiplying by `EMB.THREAD_LENGTH_FACTOR` (machine.py's 1.35
// rule of thumb, hand-ported and guarded by test/digitize.test.js) gives the
// metres the operator buys, on the same basis the service quotes.
//
// **Measured against the service, and it does not agree exactly.** On the
// enthusiast_logo job the browser walk gives 3.42 + 1.53 = 4.95 m where the
// service reports 3.35 + 1.51 = 4.87 — **1.6% high**. The cause is real and
// not fixable from here: `plan_to_design` emits a run the machine reaches
// WITHOUT travelling as plain consecutive stitches, so the design records
// carry no marker for that run boundary and this walk joins the two, counting
// one segment the plan does not. The design has lost information the plan had.
//
// That is why this is used ONLY where the service has said nothing. The
// browser lane's own designs do not have the problem — `buildLetteringDesign`
// SEWS its short travel as running stitch, so every segment counted there is
// thread that really goes down.
import { EMB } from "./emb.js";

// One walk, four facts, so they cannot drift apart. Chain-breaking rule is
// designToStrands's, deliberately.
export function sewFacts(design) {
  const out = { stitches: 0, threadChanges: 0, trims: 0, pathMm: 0, threadM: null };
  if (!design || !Array.isArray(design.stitches)) return out;
  let prev = null;
  for (const s of design.stitches) {
    if (s.type === "color") { out.threadChanges++; prev = null; continue; }
    if (s.type === "trim") { out.trims++; prev = null; continue; }
    if (s.type !== "stitch") { prev = null; continue; }
    out.stitches++;
    if (prev) out.pathMm += Math.hypot(s.x - prev.x, s.y - prev.y) / 10;
    prev = s;
  }
  // NOT `|| 1`. A missing factor is a stale `app/public/engine/` copy (the
  // constant lives in the engine, which copy-engine.mjs syncs on predev and
  // prebuild), and falling back to 1 turns that into a plausible wrong number:
  // measured 2026-09-07 against a stale copy, the review read "1.5 m
  // (estimate)" for the design that actually needs 2.1. No factor, no metres —
  // sewSummary drops the row rather than quote a path length as thread.
  const factor = EMB.THREAD_LENGTH_FACTOR;
  out.threadM = typeof factor === "number" && factor > 0 ? (out.pathMm * factor) / 1000 : null;
  return out;
}

// The review rows, in the order an operator uses them: how big, how long it
// runs, how many times they have to touch it, how much thread to have on hand.
// Returns [] for a design with nothing sewn — there is no fact to state, and
// "0 stitches · 0 m of thread" under "Nothing to stitch yet" is noise.
export function sewSummary(design) {
  const f = sewFacts(design);
  if (!f.stitches) return [];
  const rows = [
    { label: "Size", value: `${design.widthMM.toFixed(0)} × ${design.heightMM.toFixed(0)} mm` },
    { label: "Stitches", value: f.stitches.toLocaleString() },
  ];
  // A single-colour design has no change to report, and printing "0 thread
  // changes" invites the reader to look for the control that sets it.
  if (f.threadChanges > 0) {
    rows.push({ label: "Thread changes", value: String(f.threadChanges) });
  }
  // Zero trims IS worth printing — it says there is nothing to clip, which is
  // the same reason QualityReport prints it.
  rows.push({ label: "Trims", value: String(f.trims) });
  if (f.threadM != null) rows.push({ label: "Thread", value: `${f.threadM.toFixed(1)} m (estimate)` });
  return rows;
}
