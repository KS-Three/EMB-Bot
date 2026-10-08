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
