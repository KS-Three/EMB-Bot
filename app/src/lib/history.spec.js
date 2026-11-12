import { test, expect } from "vitest";
import { createHistory } from "./history.js";

const snap = (n) => ({ n }); // stand-in immutable snapshots

test("record/undo/redo walk the timeline; can-flags track position", () => {
  const h = createHistory(snap(0), { coalesceMs: 0 });
  expect(h.canUndo()).toBe(false);
  expect(h.canRedo()).toBe(false);

  const a = snap(1), b = snap(2);
  h.record(a, 1000);
  h.record(b, 2000);
  expect(h.canUndo()).toBe(true);

  expect(h.undo()).toBe(a);
  expect(h.canRedo()).toBe(true);
  expect(h.undo()).toEqual(snap(0));
  expect(h.canUndo()).toBe(false);
  expect(h.undo()).toBeNull(); // bottom of the stack

  expect(h.redo()).toBe(a);
  expect(h.redo()).toBe(b);
  expect(h.redo()).toBeNull(); // top of the stack
});

test("a new edit after undo truncates the redo branch", () => {
  const h = createHistory(snap(0), { coalesceMs: 0 });
  h.record(snap(1), 1000);
  h.record(snap(2), 2000);
  h.undo();
  const c = snap(3);
  h.record(c, 3000);
  expect(h.canRedo()).toBe(false);
  expect(h.undo()).toEqual(snap(1));
  expect(h.redo()).toBe(c);
});

test("records within coalesceMs merge into ONE undo step (drag storms)", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  // simulate a drag: many patches 16ms apart
  let t = 1000;
  for (let i = 1; i <= 20; i++) h.record(snap(i), (t += 16));
  const final = snap(99);
  h.record(final, t + 16);
  // one gesture -> one entry: a single undo returns to the pre-drag state
  expect(h.undo()).toEqual(snap(0));
  expect(h.redo()).toBe(final);
});

test("a pause longer than coalesceMs starts a NEW undo step", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  h.record(snap(1), 1000);
  h.record(snap(2), 1100); // merged into the same step
  h.record(snap(3), 5000); // separate gesture
  expect(h.undo()).toEqual(snap(2));
  expect(h.undo()).toEqual(snap(0));
});

test("an edit right after undo never coalesces into the restored snapshot", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  h.record(snap(1), 1000);
  h.undo();
  h.record(snap(2), 1001); // 1ms later, but must be its own step
  expect(h.undo()).toEqual(snap(0));
});

test("identical-reference records are no-ops", () => {
  const a = snap(1);
  const h = createHistory(a, { coalesceMs: 0 });
  h.record(a, 1000);
  expect(h.canUndo()).toBe(false);
});

test("the stack caps at `limit`, dropping the oldest entries", () => {
  const h = createHistory(snap(0), { coalesceMs: 0, limit: 5 });
  for (let i = 1; i <= 10; i++) h.record(snap(i), i * 1000);
  let steps = 0;
  while (h.undo()) steps++;
  expect(steps).toBe(4); // 5 entries = 4 undoable steps
});

test("reset starts a fresh single-entry history (project switch)", () => {
  const h = createHistory(snap(0), { coalesceMs: 0 });
  h.record(snap(1), 1000);
  h.reset(snap(7));
  expect(h.canUndo()).toBe(false);
  expect(h.canRedo()).toBe(false);
  expect(h.undo()).toBeNull();
});

test("a discrete record never merges into the entry before it, however fast", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  h.record(snap(1), 1000);                // first edit
  h.record(snap(2), 1100, true);          // an arrow press 100 ms later
  h.record(snap(3), 1200, true);
  h.record(snap(4), 1300, true);
  expect(h.undo()).toEqual(snap(3));
  expect(h.undo()).toEqual(snap(2));
  expect(h.undo()).toEqual(snap(1));
  expect(h.undo()).toEqual(snap(0));
  // and an ordinary drag storm still coalesces
  const g = createHistory(snap(0), { coalesceMs: 500 });
  g.record(snap(1), 1000);
  g.record(snap(2), 1100);
  g.record(snap(3), 1200);
  expect(g.undo()).toEqual(snap(0));
});

// Structural edits (element added / removed) are recorded `discrete` by
// App.svelte's persistStructural. These pin what that buys at this level; the
// wired version is e2e/undo-redo.spec.js "deleting an element right after
// adding it can still be undone".
test("an add then a delete inside the coalesce window undo in TWO steps, and redo mirrors them", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  const base = snap(1), added = snap(2), deleted = snap(3);
  h.record(base, 1000);                   // some earlier edit
  h.record(added, 5000, true);            // add an element
  h.record(deleted, 5100, true);          // delete it 100 ms later
  expect(h.undo()).toBe(added);           // the delete alone: the element is back
  expect(h.undo()).toBe(base);            // then the add
  expect(h.redo()).toBe(added);
  expect(h.redo()).toBe(deleted);
  expect(h.redo()).toBeNull();
});

test("a discrete record does not merge into a drag that ended a moment before it", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  let t = 1000;
  for (let i = 1; i <= 10; i++) h.record(snap(i), (t += 16)); // a drag
  const dragged = snap(10);
  const deleted = snap(11);
  h.record(deleted, t + 50, true);        // Delete pressed 50 ms after release
  expect(h.undo()).toEqual(dragged);      // the delete alone
  expect(h.undo()).toEqual(snap(0));      // the whole drag, still one step
  expect(h.redo()).toEqual(dragged);
  expect(h.redo()).toBe(deleted);
});

test("a drag still coalesces into ONE step beside discrete edits, and redo mirrors it", () => {
  const h = createHistory(snap(0), { coalesceMs: 500 });
  const added = snap(1);
  h.record(added, 1000, true);            // add an element
  let t = 5000;                           // ...later, drag it: 30 patches
  for (let i = 2; i <= 30; i++) h.record(snap(i), (t += 16));
  const dropped = snap(31);
  h.record(dropped, t + 16);
  expect(h.undo()).toBe(added);           // one undo for the whole drag
  expect(h.undo()).toEqual(snap(0));      // one for the add
  expect(h.redo()).toBe(added);
  expect(h.redo()).toBe(dropped);         // redo lands on the drag's END state
  expect(h.redo()).toBeNull();
});

test("a continuous record right after a discrete one stays inside its step (an upload's follow-up patches)", () => {
  // Deliberately one-directional -- see the header of history.js. Uploading
  // artwork is an add followed by the panel's own asynchronous patches; one
  // Undo must remove the upload, not strand an empty artwork element.
  const h = createHistory(snap(0), { coalesceMs: 500 });
  h.record(snap(1), 1000);
  h.record(snap(2), 5000, true);          // add the artwork element
  const loaded = snap(3);
  h.record(loaded, 5040);                 // its sourcePng lands 40 ms later
  expect(h.undo()).toEqual(snap(1));
  expect(h.redo()).toBe(loaded);
});
