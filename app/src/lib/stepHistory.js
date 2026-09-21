// The wizard's steps as browser history entries.
//
// The Studio used to push nothing — `history.length` was still 2 after three
// steps — so Back left the app instead of stepping back a step. Work was not
// lost (Forward restored the page), but Back is the primary gesture on a
// phone and both the lettering and the artwork lanes work on a phone.
// (measured 2026-09-07 — MASTER_SCOPE open item 15)
//
// **Getting this wrong is worse than the bug it fixes.** Push an entry for
// the FIRST step and Back from it lands on the Studio again, so someone who
// opens the app and immediately presses Back is trapped. The one rule this
// module exists to keep: the first step REPLACES the entry the browser
// already has, and only a step AFTER it ever pushes. n visited steps cost
// n-1 entries, never n — every count in stepHistory.spec.js is a delta
// against that.
//
// No URL is ever passed to pushState/replaceState, so the address bar never
// moves and this is NOT routing: there is no deep link to serve, a reload
// still boots the flow at its first step, and no other part of the app has
// to know history exists. Restoring the step across a reload from the
// entry's own state is deliberately left out — landing on a step whose
// canAdvance() gate no longer passes is a different question from Back.

export const STEP_KEY = "embStep";

// The entry's own position in the trail, so a Back/Forward that skips
// several entries at once (a long-press on the Back button) re-syncs the
// mirror below instead of guessing.
const INDEX_KEY = "embStepIndex";

export function stepFromState(state) {
  const s = state && typeof state === "object" ? state[STEP_KEY] : undefined;
  return typeof s === "string" ? s : null;
}

// `history` is injected rather than read off `window` so a spec can hand in
// a double and assert which verb a navigation chose — push vs. back is the
// whole behavioural difference between the in-app Back button stacking a
// near-duplicate entry and it being the same gesture as the browser's.
// A null `history` (no DOM) degrades to plain step changes.
export function createStepHistory({ history = null, onStep = () => {} } = {}) {
  // Our mirror of the entries this module created: trail[pos] is the step on
  // screen. The browser will not tell us which step sits one entry back, and
  // that is exactly the fact that decides whether Back can hand over to
  // history.back(), so we keep the trail ourselves.
  let trail = [];
  let pos = 0;

  function write(step, replace) {
    if (!history) return;
    // Only a REPLACE keeps whatever else is on the entry — it is overwriting
    // an entry someone else may have written. A push is a new entry and
    // starts clean.
    const state = replace ? { ...(history.state || {}) } : {};
    state[STEP_KEY] = step;
    state[INDEX_KEY] = pos;
    if (replace) history.replaceState(state, "");
    else history.pushState(state, "");
  }

  return {
    // Boot. The step the app opens on owns the entry the browser already
    // has — see the trap above.
    start(step) {
      trail = [step];
      pos = 0;
      write(step, true);
    },

    // A deliberate move through the flow: Next, Back, a step tab, the
    // topbar's Download shortcut.
    go(step) {
      if (!step || step === trail[pos]) return;
      if (history && pos > 0 && trail[pos - 1] === step) {
        // Stepping back onto the entry we came from: reuse it instead of
        // stacking a third entry for a step already behind us, so the in-app
        // Back button and the browser's own Back are one gesture rather than
        // two that disagree. popstate does the step change.
        history.back();
        return;
      }
      trail = trail.slice(0, pos + 1);
      trail.push(step);
      pos = trail.length - 1;
      write(step, false);
      onStep(step);
    },

    // Same position in the flow, different project. Switching designs
    // replaces what the panel shows; it is not a move through the flow, and
    // an entry for it would make Back rewind the step of a project that is
    // no longer open.
    replace(step) {
      trail[pos] = step;
      write(step, true);
      onStep(step);
    },

    // window's popstate.
    pop(event) {
      const step = stepFromState(event && event.state);
      // Not one of ours: either the entry before the app's own (the user is
      // leaving, and there is nothing to do) or something else on the origin.
      // Moving the wizard on a state we did not write would be a guess.
      if (!step) return;
      const i = event.state[INDEX_KEY];
      if (Number.isInteger(i) && i >= 0) pos = i;
      trail[pos] = step;
      onStep(step);
    },
  };
}
