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
