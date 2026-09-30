// @vitest-environment jsdom
//
// The calibration flow's panel: the card buttons gate on the service, a
// photo becomes a reading with the draft profile's before → after numbers,
// the tug-test checkbox gates Accept, and Accept writes project.fabricProfile
// and closes. The service is mocked at module scope (the numbers are the
// service's, not this panel's — digitizer/tests/test_calibration.py owns
// them); the engine's real fabric table is loaded so "before" and "after"
// are the real preset arithmetic.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

let nextReading = null;
let nextReadError = null;
const downloads = [];
vi.mock("../lib/calibration.js", async (importOriginal) => {
  const real = await importOriginal();
  return {
    ...real,
    downloadCalibrationCard: async (format) => {
      downloads.push(format);
      return { bytes: new Blob([1]), filename: `EMBBOT_CALIBRATION_CARD_V2.${format}`, mime: "x", widthMm: 82, heightMm: 103 };
    },
    readCalibrationPhoto: async () => {
      if (nextReadError) throw new Error(nextReadError);
      return nextReading;
    },
  };
});
vi.mock("../lib/download.js", () => ({ triggerDownload: () => {} }));

let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  require("../../../src/units.js");
  require("../../../src/garments.js");
  require("../../../src/fabrics.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./CalibratePanel.testHarness.svelte"));
});

const READING = {
  profile: { pull_comp_delta_mm: -0.05, density_scale: 0.9 },
  preset: { id: "pique_knit", label: "Pique knit (polo)", pull_comp_mm: 0.3, density_adjust: 1.0, trim_at_mm: 3.0 },
  in_force: { pull_comp_mm: 0.25, density_adjust: 0.9, trim_at_mm: 3.0 },
  notes: ["Satin columns pulled in 0.50 mm across on this cloth."],
  confidence: { mode: "fiducials" },
  features: [{ name: "satin-4mm", role: "bar", d_height_mm: -0.5, d_width_mm: 0.3 }],
  seam_gap_delta_mm: { "0": 0.0 },
  overlay_jpeg_base64: "",
  card_mm: [82, 103],
};

function renderPanel({ health = { status: "ok" }, project = {} } = {}) {
  const updates = [];
  let closed = 0;
  const utils = render(Harness, {
    props: {
      project: { version: 2, garmentId: "left_chest", fabricProfile: null, elements: [], ...project },
      digitizerHealth: health,
      onUpdate: (d) => updates.push(d),
      onClose: () => { closed += 1; },
    },
  });
  return { ...utils, updates, closed: () => closed };
}

async function dropPhoto(container) {
  const input = container.querySelector('[data-testid="calibrate-photo"]');
  const file = new File([new Uint8Array([1, 2, 3])], "card.jpg", { type: "image/jpeg" });
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  await fireEvent.change(input);
}

test("without the service the card buttons and the photo input are disabled and say why", () => {
  const { container, getByText } = renderPanel({ health: null });
  expect(container.querySelector('[data-testid="card-dst"]')).toBeDisabled();
  expect(container.querySelector('[data-testid="calibrate-photo"]')).toBeDisabled();
  expect(getByText(/service is not running/)).toBeInTheDocument();
});

test("the six formats download the card through the service and report its size and hoop", async () => {
  const { container } = renderPanel();
  for (const f of ["dst", "pes", "exp", "jef", "vp3", "xxx"]) {
    expect(container.querySelector(`[data-testid="card-${f}"]`)).toBeEnabled();
  }
  await fireEvent.click(container.querySelector('[data-testid="card-pes"]'));
  await waitFor(() => expect(container.querySelector('[data-testid="card-msg"]')).toHaveTextContent(/82 × 103 mm, sew it in a 5×7 hoop/));
  expect(downloads).toEqual(["pes"]);
});

test("a photo becomes a reading: the cloth's numbers, the draft before → after, and Accept gated on the tug test", async () => {
  nextReading = READING;
  nextReadError = null;
  const { container, updates, closed } = renderPanel();
  await dropPhoto(container);
  await waitFor(() => expect(container.querySelector('[data-testid="calibrate-reading"]')).toBeInTheDocument());
  const draft = container.querySelector('[data-testid="calibrate-draft"]');
  // Before → after is the engine's own arithmetic on the profile, so it agrees
  // with what the service said would be in force.
  expect(draft).toHaveTextContent("pull comp 0.3 → 0.25 mm");
  expect(draft).toHaveTextContent("rows ×1 → ×0.9");
  expect(container).toHaveTextContent("pulled in +0.50 mm across");
  const accept = container.querySelector('[data-testid="calibrate-accept"]');
  expect(accept).toBeDisabled();
  await fireEvent.click(container.querySelector('[data-testid="calibrate-check"]'));
  expect(accept).toBeEnabled();
  await fireEvent.click(accept);
  expect(updates).toContainEqual({ fabricProfile: { pull_comp_delta_mm: -0.05, density_scale: 0.9 } });
  expect(closed()).toBe(1);
});

test("a reading that changes nothing offers no profile and no Accept", async () => {
  nextReading = { ...READING, profile: null };
  const { container } = renderPanel();
  await dropPhoto(container);
  await waitFor(() => expect(container).toHaveTextContent(/changes nothing/));
  expect(container.querySelector('[data-testid="calibrate-accept"]')).toBeDisabled();
  expect(container.querySelector('[data-testid="calibrate-check"]')).toBeNull();
});

test("the service's refusal is shown as its own sentence, and Discard clears a reading", async () => {
  nextReadError = "Could not find the card in the photo (no thread found against the fabric).";
  const { container } = renderPanel();
  await dropPhoto(container);
  await waitFor(() => expect(container.querySelector("[role=alert]")).toHaveTextContent(/Could not find the card/));
  nextReadError = null;
  nextReading = READING;
  await dropPhoto(container);
  await waitFor(() => expect(container.querySelector('[data-testid="calibrate-reading"]')).toBeInTheDocument());
  await fireEvent.click([...container.querySelectorAll("button")].find((b) => b.textContent.trim() === "Discard"));
  expect(container.querySelector('[data-testid="calibrate-reading"]')).toBeNull();
});
