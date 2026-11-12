// history.js — undo/redo over immutable project snapshots.
//
// The project model is already fully immutable (every project.js op returns a
// fresh object), so history is just an array of references — element payloads
// (including a design element's dstBase64 string) are SHARED across
// snapshots, never copied, which keeps 100 entries cheap.
//
// Coalescing: a drag/resize/slider gesture patches the project dozens of
// times per second (EmbroideryField's rAF-throttled elupdate storm). Any
// record() landing within `coalesceMs` of the previous one REPLACES the top
// entry instead of pushing, so one continuous gesture undoes as ONE step.
// undo()/redo() reset the coalescing clock — an edit made right after an
// undo must never merge itself into the restored snapshot.
//
// The window is for CONTINUOUS gestures only. A `discrete` record — a
// keyboard nudge, a committed point edit, an element added or removed —
// always pushes, so the state before it stays reachable: a delete made 100 ms
// after an add must not overwrite the add's snapshot (it did until
// 2026-11-12, and Undo then skipped past both without restoring the element).
// The rule runs BACKWARDS only, on purpose: a continuous record landing right
// after a discrete one still merges into it. Uploading artwork is an add
// followed by the panel's own asynchronous patches (sourcePng, _hasImage);
// those must stay inside the add's step, or one Undo would leave an empty
// artwork element behind instead of removing the upload.
export function createHistory(initial, opts) {
  const o = opts || {};
  const limit = o.limit || 100;
  const coalesceMs = o.coalesceMs == null ? 500 : o.coalesceMs;

  let stack = [initial];
  let idx = 0;
  let lastRecordAt = -Infinity;

  return {
    // `now` is injectable for tests; defaults to the wall clock. `discrete`
    // (a keyboard nudge, a committed point edit, an element added or removed)
    // never merges into the entry before it: each is its own undo step
    // however fast they come.
    record(snapshot, now, discrete = false) {
      if (snapshot === stack[idx]) return; // identical reference: nothing changed
      const t = now == null ? Date.now() : now;
      const coalesce = !discrete && idx > 0 && t - lastRecordAt < coalesceMs;
      stack = stack.slice(0, idx + 1); // any redo branch dies on a new edit
      if (coalesce) {
        stack[idx] = snapshot;
      } else {
        stack.push(snapshot);
        idx++;
        if (stack.length > limit) {
          stack.shift();
          idx--;
        }
      }
      lastRecordAt = t;
    },
    undo() {
      if (idx === 0) return null;
      idx--;
      lastRecordAt = -Infinity;
      return stack[idx];
    },
    redo() {
      if (idx >= stack.length - 1) return null;
      idx++;
      lastRecordAt = -Infinity;
      return stack[idx];
    },
    canUndo() {
      return idx > 0;
    },
    canRedo() {
      return idx < stack.length - 1;
    },
    // Project switch: history is per-project and in-memory only.
    reset(snapshot) {
      stack = [snapshot];
      idx = 0;
      lastRecordAt = -Infinity;
    },
  };
}
