// @vitest-environment jsdom
//
// The size field has to tell the truth about the design, including when the
// number it was given could not be used.
//
// `value={wDisplay}` is ONE-WAY and Svelte only touches the DOM when that
// expression's value changes. Two out-of-range entries in a row produce the
// same clamped design, so the second left the customer's typed text sitting
// in a field whose whole job is to say how big the design is. Measured
// 2026-09-07 on Left Chest (4 x 4 in = 101.6 mm), asking in mm:
//
//   100 -> field "100", sews 100   honoured
//   105 -> field "102", sews 102   clamped, and the field said so
//   110 -> field "110", sews 102   clamped, and the field did NOT
//   115, 120, 125, 127, 130, 150, 200 -> same, all the way up
//
// A customer asking for a 6-inch left-chest design saw "150" over a 102 mm
// design, with checkValidity() true and no message anywhere. The engine and
// the clamp are both correct — `buildLetteringDesign` honours every width up
// to the placement box and clamps above it, verified directly — so this is
// the display alone.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

// SizePanel pulls in the engine for getGarment, and emb.js throws unless the
// engine global is already up — the same stub DownloadStep.spec.js uses.
// left_chest's real placement box, 4 x 4 in, is what every bound below is.
vi.mock("../lib/emb.js", () => ({
  EMB: { getGarment: () => ({ label: "Left Chest", widthIn: 4, heightIn: 4 }) },
}));

let Harness;
beforeAll(async () => {
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./SizePanel.testHarness.svelte"));
});

// left_chest is 4 x 4 in — 101.6 mm, the bound every case below is about.
const project = { garmentId: "left_chest", sizeMm: null, elements: [] };

function renderPanel(designDims) {
  const updates = [];
  const utils = render(Harness, { project, designDims, onUpdate: (u) => updates.push(u) });
  return { updates, ...utils };
}

async function typeWidth(getByLabelText, mm) {
  const w = getByLabelText("Width");
  await fireEvent.change(w, { target: { value: String(mm) } });
  return w;
}

test("a width inside the placement box is passed through untouched", async () => {
  const { updates, getByLabelText, getByRole } = renderPanel({ widthMM: 60, heightMM: 9 });
  await fireEvent.change(getByRole("combobox", { name: "Size unit" }), { target: { value: "mm" } });
  await typeWidth(getByLabelText, 80);
  expect(updates.at(-1).sizeMm).toBeCloseTo(80, 5);
});

test("an over-box width is clamped AND the field is corrected — every time, not just the first", async () => {
  const { updates, getByLabelText, getByRole } = renderPanel({ widthMM: 102, heightMM: 15 });
  await fireEvent.change(getByRole("combobox", { name: "Size unit" }), { target: { value: "mm" } });
  // Three out-of-range entries in a row. The design cannot change between
  // them — that is exactly the case the one-way binding used to leave stale.
  for (const asked of [110, 150, 200]) {
    const w = await typeWidth(getByLabelText, asked);
    expect(updates.at(-1).sizeMm).toBeCloseTo(101.6, 3);
    expect(w.value).toBe("102");
  }
});

test("an under-minimum width is clamped and shown as clamped too", async () => {
  const { updates, getByLabelText, getByRole } = renderPanel({ widthMM: 60, heightMM: 9 });
  await fireEvent.change(getByRole("combobox", { name: "Size unit" }), { target: { value: "mm" } });
  const w = await typeWidth(getByLabelText, 1);
  expect(updates.at(-1).sizeMm).toBeCloseTo(5, 5);
  expect(w.value).toBe("5");
});

test("the correction is written in the unit the customer is working in", async () => {
  // Inches is the default. 101.6 mm is exactly 4 in.
  const { updates, getByLabelText } = renderPanel({ widthMM: 102, heightMM: 15 });
  const w = getByLabelText("Width");
  await fireEvent.change(w, { target: { value: "6" } });
  expect(updates.at(-1).sizeMm).toBeCloseTo(101.6, 3);
  expect(Number(w.value)).toBeCloseTo(4, 2);
});

test("a height that solves to an over-box width is clamped and corrected", async () => {
  // Height is solved through the design's aspect ratio; 102 x 15 is ~6.8:1,
  // so asking for 30 mm tall means ~204 mm wide, well over the 101.6 bound.
  const { updates, getByLabelText, getByRole } = renderPanel({ widthMM: 102, heightMM: 15 });
  await fireEvent.change(getByRole("combobox", { name: "Size unit" }), { target: { value: "mm" } });
  const h = getByLabelText("Height");
  await fireEvent.change(h, { target: { value: "30" } });
  expect(updates.at(-1).sizeMm).toBeCloseTo(101.6, 3);
  expect(Number(h.value)).toBeCloseTo(101.6 / (102 / 15), 0);
});

test("a non-numeric entry changes nothing", async () => {
  const { updates, getByLabelText } = renderPanel({ widthMM: 60, heightMM: 9 });
  await fireEvent.change(getByLabelText("Width"), { target: { value: "" } });
  expect(updates).toHaveLength(0);
});

test("a design change after an edit does NOT reach the field — recorded, not fixed", async () => {
  // The same one-way binding's second failure mode, measured 2026-09-07 and
  // pinned as CURRENT BEHAVIOUR rather than as something desirable: start at
  // 80 mm, type 90, let the engine come back at its pull-compensated 90.2,
  // and the field keeps showing 90.
  //
  // Left alone because the residual is ~0.2 mm on plain lettering and the
  // number shown is the one the customer just typed. An effect re-asserting
  // the DOM on every wDisplay change was tried and did not measurably fix it,
  // so it was reverted rather than shipped undemonstrated. The severe case —
  // the clamp biting, so the design does not change at all and the field kept
  // "150" over a 102 mm design — is fixed above.
  //
  // Pinned as the real thing, not asserted true: if this starts FAILING the
  // binding began syncing, which is good news — delete it, and the caveat in
  // SizePanel's header comment with it.
  const { getByLabelText, getByRole, rerender } = renderPanel({ widthMM: 80, heightMM: 12 });
  await fireEvent.change(getByRole("combobox", { name: "Size unit" }), { target: { value: "mm" } });
  await typeWidth(getByLabelText, 90);          // honoured — 90 < the 101.6 bound
  expect(getByLabelText("Width").value).toBe("90");

  await rerender({ project, designDims: { widthMM: 90.2, heightMM: 13.5 }, onUpdate: () => {} });
  expect(getByLabelText("Width").value).toBe("90");   // ...not "90.2"
});
