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
export function createHistory(initial, opts) {
  const o = opts || {};
  const limit = o.limit || 100;
  const coalesceMs = o.coalesceMs == null ? 500 : o.coalesceMs;

  let stack = [initial];
  let idx = 0;
  let lastRecordAt = -Infinity;

  return {
    // `now` is injectable for tests; defaults to the wall clock.
    record(snapshot, now) {
      if (snapshot === stack[idx]) return; // identical reference: nothing changed
      const t = now == null ? Date.now() : now;
      const coalesce = idx > 0 && t - lastRecordAt < coalesceMs;
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
