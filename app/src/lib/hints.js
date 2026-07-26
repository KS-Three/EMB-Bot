// First-run onboarding hints (Slice 7 Task 3).
//
// Semantics (plan amendment A7): each hint is show-UNTIL-dismissed, not
// show-once — it stays visible (across reloads) until the user dismisses it
// via its ✕ or its own auto-dismiss action (see the hosts in App.svelte /
// GarmentStep.svelte / ContentStep.svelte / EmbroideryField.svelte). Merely
// having been rendered does NOT dismiss it.
//
// At most one hint is ever shown at a time, by priority:
//   drag-field  >  add-elements  >  templates
// (A7). This module only implements the pure priority pick (visibleHint) —
// callers (App.svelte) are responsible for computing which keys are
// CONTEXTUALLY eligible right now (templates ⇔ on the garment step;
// add-elements ⇔ on the content step with < 2 elements; drag-field ⇔ the
// generated design has stitchCount > 0, A8) and for excluding anything
// already dismissed (shouldShow(key)) BEFORE calling visibleHint() — that
// last exclusion is what makes "lower-priority hidden while a higher one is
// eligible" also correctly stop applying once that higher one gets
// dismissed (it drops out of the eligible list you hand to visibleHint).
//
// Storage: a single JSON object at `embstudio:hints`, `{ [key]: true }` for
// every dismissed key. Try/catch-safe throughout, per this module's two
// failure contracts:
//   - a READ failure (missing key, corrupt JSON, disabled/denied storage,
//     private-mode quirks, ...) is treated as "nothing dismissed yet" —
//     shouldShow() defaults to SHOW for every key.
//   - a WRITE failure (quota exceeded, denied, ...) makes dismiss() a no-op
//     for PERSISTENCE, but a module-level Set mirrors every dismissed key in
//     memory for the lifetime of this page load, so the hint still
//     disappears for the rest of THIS session — it just won't stay
//     dismissed after an actual reload, since the write never landed.

const STORAGE_KEY = "embstudio:hints";

// Priority order, highest first (A7).
const PRIORITY = ["drag-field", "add-elements", "templates"];

// Session-level fallback for write failures — see the module doc above.
// Never cleared except by a fresh module instance (i.e. a real page load).
const sessionDismissed = new Set();

function readDismissed() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const obj = JSON.parse(raw);
    return obj && typeof obj === "object" && !Array.isArray(obj) ? obj : {};
  } catch (e) {
    return {};
  }
}

export function shouldShow(key) {
  if (sessionDismissed.has(key)) return false;
  return !readDismissed()[key];
}

export function dismiss(key) {
  // Applied unconditionally, regardless of whether the storage write below
  // succeeds — this is what keeps a dismiss "sticky" for the rest of the
  // current session even under a fully-denied/quota-exceeded storage.
  sessionDismissed.add(key);
  try {
    const dismissed = readDismissed();
    dismissed[key] = true;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dismissed));
  } catch (e) {
    // Storage write failed — sessionDismissed above already covers this
    // session; nothing further to do (see the WRITE failure contract above).
  }
}

// Pure priority pick: given the list of keys currently ELIGIBLE to show
// (contextually valid AND not dismissed — see the module doc above for who's
// responsible for that filtering), returns the single highest-priority one,
// or null if none are eligible. Keys outside the known three are ignored
// (never returned), so a typo'd/unknown key can never "win" by omission.
export function visibleHint(eligibleKeys) {
  const eligible = new Set(eligibleKeys || []);
  for (const key of PRIORITY) {
    if (eligible.has(key)) return key;
  }
  return null;
}
