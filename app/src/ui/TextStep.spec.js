// @vitest-environment jsdom
//
// Component-level coverage for TextStep.svelte's OCR-suggested-text advisory
// badge (see digitizer.js's textClusterSeed for where `textSource` comes
// from): the badge must appear exactly when `element.textSource ===
// "ocr-suggested"`, and must disappear the instant the user edits the
// textarea — an unconfirmed machine guess must never keep looking
// unconfirmed-but-trustable after a human has touched it, and must never
// render for ordinary user-typed text.
//
// Uses the same render-through-a-real-parent-component harness pattern
// ManualPanel.spec.js established (Svelte 5's mounted-instance `$on` gap —
// see that file's own comment and TextStep.testHarness.svelte here).
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

// TextStep renders FontSelect, which imports "../lib/emb.js" at module load
// time — that module throws synchronously if `window.EMB` (the engine,
// normally attached by index.html's <script> tags) isn't already set (see
// emb.js). A plain top-level `import Harness from "./TextStep.testHarness
// .svelte"` would trigger that whole chain before any beforeAll/beforeEach
// in THIS file gets to run (static imports are hoisted ahead of all other
// top-level code) — so the stub has to go in first, and the harness has to
// be loaded dynamically, after it, the same "stub before importing"
// ordering digitizer.spec.js's stubStorage()-then-`await import(...)`
// pattern already uses for localStorage.
let Harness;
beforeAll(async () => {
  globalThis.EMB = { buildLetteringDesign: () => { throw new Error("not used by this spec"); } };
  // FontSelect (rendered by TextStep) also eagerly kicks off a manifest
  // fetch on mount; jsdom's `fetch` has nothing to reach and the
  // component's own `.catch()` already handles that (falls back to
  // "Loading fonts…"/"Choose a font") — nothing here asserts on FontSelect's
  // own state, only silences the otherwise-noisy rejected-promise console
  // output during the test run.
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./TextStep.testHarness.svelte"));
});

function baseElement(patch = {}) {
  return {
    id: "e1",
    type: "text",
    text: "",
    fontKey: null,
    colorRgb: [20, 20, 20],
    colorRanges: [],
    weightPreset: "normal",
    slantDeg: 0,
    letterSpacingMm: 0,
    arcDeg: 0,
    rotationDeg: 0,
    align: "center",
    ...patch,
  };
}

function renderStep(patch = {}) {
  const patches = [];
  const utils = render(Harness, {
    props: { element: baseElement(patch), onPatch: (d) => patches.push(d) },
  });
  return { ...utils, patches };
}

test("no advisory badge for an ordinary user-typed element (textSource unset)", () => {
  const { queryByText } = renderStep({ text: "Hello" });
  expect(queryByText(/Suggested from image/i)).toBeNull();
});

test("advisory badge renders when textSource is ocr-suggested", () => {
  const { getByText } = renderStep({ text: "ENTERPRISES", textSource: "ocr-suggested" });
  expect(getByText(/Suggested from image.*verify before saving/i)).toBeInTheDocument();
});

test("editing the textarea clears textSource in the same patch, and the badge disappears", async () => {
  const { getByPlaceholderText, queryByText, patches } = renderStep({
    text: "ENTERPRISES",
    textSource: "ocr-suggested",
  });
  expect(queryByText(/Suggested from image/i)).not.toBeNull();

  const textarea = getByPlaceholderText("Type a name or word");
  await fireEvent.input(textarea, { target: { value: "ENTERPRISES INC" } });

  // The dispatched patch clears provenance in the SAME edit, not a follow-up.
  expect(patches.at(-1)).toEqual({
    id: "e1",
    patch: { text: "ENTERPRISES INC", textSource: null },
  });
  // The harness re-renders TextStep off the merged element, so the badge
  // reflects the post-edit state without a second interaction.
  expect(queryByText(/Suggested from image/i)).toBeNull();
});
