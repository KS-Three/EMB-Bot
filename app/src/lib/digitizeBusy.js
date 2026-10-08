import { writable } from "svelte/store";

// Which elements have a digitize (Auto Digitize Image, or a restitch) in
// flight right now.
//
// The run lives in DigitizePanel (its `phase`); the place that shows it is the
// embroidery field, where the pinwheel throbs over the canvas until the
// stitches land (Kent, 2026-10-08: "bring it back"). The two components share
// no parent prop for this, so it is a store, like designChart.js.
//
// A Set of element ids rather than a boolean: two panels can be mounted over
// one session, and one finishing must not hide the other's pinwheel.
export const digitizeBusy = writable(new Set());
let current = new Set();
digitizeBusy.subscribe((s) => (current = s));

/** Mark element `id` as running (busy=true) or not. No-op without an id. */
export function markDigitizeBusy(id, busy) {
  if (id == null) return;
  // Checked before set(): a writable re-notifies on ANY object, the same Set
  // included, and DigitizePanel calls this on every reactive pass.
  if (!!busy === current.has(id)) return;
  const next = new Set(current);
  if (busy) next.add(id);
  else next.delete(id);
  digitizeBusy.set(next);
}

// ---- a run that outlives its panel ------------------------------------------
//
// The job lives in the service; the panel only polls it. A reload, or a click
// on another element (ContentStep remounts the panel per selection), tears the
// poll down and the result with it: the stitches landed nowhere and the
// element came back idle and unstitched. So a started run is remembered here,
// per element, in sessionStorage (this tab only; the undo history never sees
// it, which a flag on the element would). The next panel for that element
// finds the mark and submits again -- the service answers an identical
// image+config with the job already in flight, or its finished result, so
// resuming is a join, not a second run and not an orphan.
const KEY = (id) => "embot.digitizing." + id;

export function rememberRun(id) {
  try { if (id != null) sessionStorage.setItem(KEY(id), "1"); } catch (e) { /* storage blocked: no resume */ }
}
// A page on its way out aborts its own in-flight fetches, the poll throws, and
// the run's `finally` would forget the mark a moment before the page dies --
// exactly the reload this exists for. Once the page is leaving, nothing is
// forgotten. (A bfcache restore brings the page back alive: pageshow resets.)
let leaving = false;
if (typeof window !== "undefined") {
  window.addEventListener("pagehide", () => (leaving = true));
  window.addEventListener("pageshow", () => (leaving = false));
}

export function forgetRun(id) {
  if (leaving) return;
  try { if (id != null) sessionStorage.removeItem(KEY(id)); } catch (e) { /* ignore */ }
}
export function wasRunning(id) {
  try { return id != null && sessionStorage.getItem(KEY(id)) === "1"; } catch (e) { return false; }
}
