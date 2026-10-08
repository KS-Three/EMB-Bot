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
import { profileById, threadCost, machineCost, money } from "./quote.js";

// One walk, four facts, so they cannot drift apart. Chain-breaking rule is
// designToStrands's, deliberately.
//
// `stops` (2026-10-01) is what the run time is charged for: every trim, plus
// every colour change the thread was NOT already cut for. Both of our own
// engines cut before they change ("a color change is a trim then a `color`",
// adapter.py; digitize.js says the same), so there a change is already one
// of the trims and counting it again would bill it twice. An imported DST
// need not: its colour stop can arrive with no trim record at all, and until
// now that stop cost nothing. `trims` itself is unchanged — it is the number
// of tails somebody clips, which is a different question.
export function sewFacts(design) {
  const out = { stitches: 0, threadChanges: 0, trims: 0, stops: 0, pathMm: 0, threadM: null };
  if (!design || !Array.isArray(design.stitches)) return out;
  let prev = null;
  let cut = false; // thread already cut since the last sewn stitch
  for (const s of design.stitches) {
    if (s.type === "color") { out.threadChanges++; if (!cut) out.stops++; cut = true; prev = null; continue; }
    if (s.type === "trim") { out.trims++; out.stops++; cut = true; prev = null; continue; }
    if (s.type !== "stitch") { prev = null; continue; }
    cut = false;
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
//
// `quote` (optional, lib/quote.js) is what the operator said about their own
// shop. Without it every row that existed reads exactly as it did. With it:
// the run time is computed at the speed they run and names their machine,
// and the two dollar rows appear — each only when ITS inputs are filled,
// since a price is the operator's or it is absent.
//
// The rows QualityReport's own stats line does not carry. App appends these
// even when one digitized element IS the design and the rest of this list is
// suppressed — otherwise the commonest job, one logo, got no quote at all.
export const QUOTE_ROW_LABELS = ["Run time", "Bobbin", "Thread cost", "Machine time"];

// "102 × 15 mm (4.02 × 0.59 in)": the Size panel defaults to inches and the
// worksheet prints both, so the Review/quote row carries both too. Inches use
// the sheet's 2 decimals (src/units.js mmToInch = mm / 25.4); mm stay whole.
const MM_PER_INCH = 25.4;
export function sizeLabel(design) {
  const w = design.widthMM, h = design.heightMM;
  return `${w.toFixed(0)} × ${h.toFixed(0)} mm (${(w / MM_PER_INCH).toFixed(2)} × ${(h / MM_PER_INCH).toFixed(2)} in)`;
}

export function sewSummary(design, quote) {
  const q = quote || {};
  const f = sewFacts(design);
  if (!f.stitches) return [];
  const rows = [
    { label: "Size", value: sizeLabel(design) },
    { label: "Stitches", value: f.stitches.toLocaleString() },
  ];
  // How long it runs — the row this function's own header has promised since
  // it was written, and the one a shop actually schedules on. Trims are in
  // the figure because they cost real minutes: a 12-stop logo is not its
  // stitch count divided by a speed.
  //
  // The basis rides with the number, for the same reason the worksheet prints
  // it: 650 spm is a planning rate from a trade table, not something measured
  // here, and a bare "~10 min" would read as though it were.
  //
  // Charged per STOP, not per trim (see sewFacts): a colour stop the thread
  // was not already cut for is a stop too.
  const spm = q.spm != null ? q.spm : EMB.PLAN_SPM;
  const profile = profileById(q.profileId);
  const runMin = EMB.sewTimeMin ? EMB.sewTimeMin(f.stitches, f.stops, spm) : null;
  if (runMin != null) {
    const where = profile ? ` on your ${profile.label}` : "";
    rows.push({ label: "Run time", value: `~${runMin} min${where} at ${spm.toLocaleString()} spm` });
  }
  // A single-colour design has no change to report, and printing "0 thread
  // changes" invites the reader to look for the control that sets it.
  if (f.threadChanges > 0) {
    rows.push({ label: "Thread changes", value: String(f.threadChanges) });
  }
  // Zero trims IS worth printing — it says there is nothing to clip, which is
  // the same reason QualityReport prints it.
  rows.push({ label: "Trims", value: String(f.trims) });
  if (f.threadM != null) rows.push({ label: "Thread", value: `${f.threadM.toFixed(1)} m (estimate)` });
  // Under-thread, as a share of the figure above and saying so (sewtime.js
  // has why it is not the maker's per-1,000-stitches rule). Metres, not
  // "bobbin changes" (Kent's ruling 2026-10-01): one piece is almost never a
  // whole bobbin, and how much a bobbin holds depends on whose it is. No
  // thread figure, no bobbin figure.
  const bobbin = EMB.bobbinM ? EMB.bobbinM(f.threadM) : null;
  if (bobbin != null) {
    const shown = bobbin < 0.05 ? "under 0.1" : `~${bobbin.toFixed(1)}`;
    rows.push({ label: "Bobbin", value: `${shown} m (3/5 of top thread)` });
  }
  // The dollars. Top thread only — there is no bobbin price to ask for yet.
  const tCost = money(threadCost(f.threadM, q));
  if (tCost != null) {
    rows.push({
      label: "Thread cost",
      value: `${tCost} (${f.threadM.toFixed(1)} m of a ${money(q.conePrice)} / ${q.coneM.toLocaleString()} m cone)`,
    });
  }
  const mCost = money(machineCost(runMin, q));
  if (mCost != null) {
    rows.push({ label: "Machine time", value: `${mCost} (${runMin} min at ${money(q.hourRate)}/hr)` });
  }
  return rows;
}
