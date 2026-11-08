// Compile-level guard: a cursor change in EmbroideryField must never repaint.
//
// In Svelte 5's legacy mode a member write on a component variable
// (`canvas.style.cursor = "grab"`) compiles to `$.mutate(canvas, ...)`, which
// invalidates `canvas`. Three `$: if (canvas) { ... }` statements name it, so
// every such write re-ran `paint()` (the full regenerate, which also closes
// the simulator) and two `scheduleViewRepaint()`s. #1332 measured it closing
// the simulator on the first mouse move and fixed the two writes that ran
// during playback; the 23 in edit mode (hover and drag cursors) repainted on
// every pointer move until 2026-11-07. They now go through `setCanvasCursor`,
// which writes through a local alias that the compiler does not track.
//
// Asserted on the COMPILED output, like ContentStep.reactivity.spec.js,
// because the bug is invisible to a logic test: the cursor is right either
// way, and what breaks is only how much work each move does. The behaviour
// half (0 repaints per hover, per edit mode) is e2e/field-hover-repaint.spec.js.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { compile } from "svelte/compiler";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = readFileSync(join(HERE, "EmbroideryField.svelte"), "utf8");
const JS = compile(SRC, { generate: "client", filename: "EmbroideryField.svelte" }).js.code;

test("no cursor write invalidates `canvas` (each one would re-run paint())", () => {
  // `$.mutate(\n canvas, // comment\n $.get(canvas).style.cursor = x)` spans
  // lines when the source line carries a comment, so match across them.
  const hits = JS.match(/\$\.mutate\(\s*canvas\b[^;]*?\.style\b/g) || [];
  expect(hits).toEqual([]);
});

// The same bug outside cursors (#1334's Decision 2, 2026-11-07):
// fitCanvasToPane's `canvas.width = …` / `canvas.height = …` compiled to
// `$.mutate(canvas, …)` too, so every window resize re-ran paint() and closed
// the simulator, against its own comment asking for repaintView() only. Any
// member write on `canvas`, of any property, is the same invalidation, so this
// one bans them all. Fails on main 6e2f383a (2 hits: width, height).
test("no member write of any kind invalidates `canvas` (resize included)", () => {
  const hits = JS.match(/\$\.mutate\(\s*canvas\b/g) || [];
  expect(hits).toEqual([]);
});

test("the resize still sets the bitmap size, through a local alias", () => {
  expect(SRC).toMatch(/const el = canvas;\s*el\.width = bw;[^\n]*\n\s*el\.height = bh;/);
});

test("the cursor is still set, through the alias", () => {
  const calls = SRC.match(/\bsetCanvasCursor\(/g) || [];
  // One definition plus the writes (25 on 2026-11-07). The floor only says
  // they did not all vanish: a hover with no cursor would pass the test above.
  expect(calls.length).toBeGreaterThan(20);
  expect(SRC).toMatch(/function setCanvasCursor\(c\) \{\s*const el = canvas;\s*if \(el\) el\.style\.cursor = c;/);
});

// Every field render starts on a default context (freshContext). Without it,
// lineCap/lineJoin "round" left by the previous render's stitches drew the
// hoop's dashed lines differently, so one design gave two pictures depending
// on whether a resize had reset the context since (#1341, keyboard-a11y's
// undo test: 1,191 px apart).
test("every renderRealistic(canvas, …) in the field is preceded by freshContext(canvas)", () => {
  const renders = SRC.match(/renderRealistic\(canvas\b/g) || [];
  const fresh = SRC.match(/freshContext\(canvas\);\s*\n\s*renderResult = renderRealistic\(canvas\b/g) || [];
  expect(renders.length).toBeGreaterThan(0);
  expect(fresh.length).toBe(renders.length);
});
