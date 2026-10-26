// The Studio's /digitize request, pinned as a fixture both sides read.
//
// Every flip-sheet and pro_pair number runs on `tools.fremont_triage.
// studio_request()`, a hand-kept Python copy of `buildDigitizeConfig`. Before
// this file the copy was pinned by source-TEXT checks (test_fremont_triage.py
// greps project.js and digitizer.js), which catch a changed default but not
// a changed key, a new unconditional key, or a branch that begins to fire for
// a fresh upload. This pins the OUTPUT instead: `buildDigitizeConfig` over a
// fresh digitized element, per garment and width, with the project's default
// fabric colour and no thread brand picked.
//
// The other end is digitizer/tests/test_studio_request_contract.py, which
// reads the SAME fixture and asserts the Python request equals it. Change a
// key here and this goes red; regenerate the fixture and the pytest goes red
// until `studio_request` is brought in line. Neither side passes alone.
//
//   UPDATE_STUDIO_REQUEST_FIXTURE=1 npx vitest run src/lib/studioRequest.contract.spec.js
//
// rewrites the fixture from the live function. Do that only on purpose, with
// the diff in the PR: an earlier flip number described the OLD request.
import { test, expect, beforeEach } from "vitest";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import fixture from "./fixtures/studio-request.json";
import { buildDigitizeConfig } from "./digitizer.js";
import { defaultDigitizedElement, defaultProject } from "./project.js";

const FIXTURE_PATH = fileURLToPath(new URL("./fixtures/studio-request.json", import.meta.url));

// The garments the flip sheets and pro pairs run on, at the Studio's default
// width (80 mm) and at the 81 mm of Kent's Hotel Fremont hat job, which is
// `studio_request()`'s own default.
const GARMENTS = ["hat_front", "left_chest", "beanie"];
const WIDTHS_MM = [80, 81];

// localStorage does not exist in the node env. digitizer.js and threads.js
// read it through try/catch, so an EMPTY store is the customer who never
// picked a brand or turned the SAM2 seam on.
function emptyStorage() {
  globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  };
}

beforeEach(emptyStorage);

function requestFor(garmentId, widthMm) {
  const element = defaultDigitizedElement("e1");
  element.params = { ...element.params, target_width_mm: widthMm };
  const project = { ...defaultProject(), garmentId };
  return buildDigitizeConfig(element, project);
}

function live() {
  const cases = [];
  for (const garment_id of GARMENTS) {
    for (const target_width_mm of WIDTHS_MM) {
      cases.push({
        name: `${garment_id}_${target_width_mm}`,
        garment_id,
        target_width_mm,
        config: requestFor(garment_id, target_width_mm),
      });
    }
  }
  return { fabric_rgb: defaultProject().fabricRgb, cases };
}

if (process.env.UPDATE_STUDIO_REQUEST_FIXTURE) {
  test("rewrite the studio-request fixture from buildDigitizeConfig", () => {
    const body = {
      _about:
        "buildDigitizeConfig over a fresh digitized element, per garment and width, " +
        "default fabric colour, no thread brand, SAM2 seam off. Written by " +
        "studioRequest.contract.spec.js (UPDATE_STUDIO_REQUEST_FIXTURE=1); read by " +
        "digitizer/tests/test_studio_request_contract.py. Do not hand-edit.",
      ...live(),
    };
    writeFileSync(FIXTURE_PATH, JSON.stringify(body, null, 2) + "\n", "utf8");
    expect(JSON.parse(readFileSync(FIXTURE_PATH, "utf8")).cases).toHaveLength(GARMENTS.length * WIDTHS_MM.length);
  });
}

test("the fixture covers every garment at every width, once", () => {
  const names = fixture.cases.map((c) => c.name).sort();
  const want = GARMENTS.flatMap((g) => WIDTHS_MM.map((w) => `${g}_${w}`)).sort();
  expect(names).toEqual(want);
});

test("buildDigitizeConfig's output for a fresh upload is the fixture, key for key", () => {
  expect(fixture.fabric_rgb).toEqual(defaultProject().fabricRgb);
  for (const c of fixture.cases) {
    expect(requestFor(c.garment_id, c.target_width_mm), c.name).toEqual(c.config);
  }
});

test("a fresh upload sends no key the customer did not choose", () => {
  // The keys a default request carries, as a closed list: a new unconditional
  // key is a new default every earlier flip number did not run under.
  const allowed = new Set([
    "target_width_mm", "max_colors", "satin", "detail_layer", "edge_cap",
    "detect_photographic", "faces_route_flat", "garment_id", "garment_rgb",
  ]);
  for (const c of fixture.cases) {
    for (const k of Object.keys(c.config)) expect(allowed.has(k), `${c.name} sends ${k}`).toBe(true);
    expect(c.config.garment_id).toBe(c.garment_id);
    expect(c.config.target_width_mm).toBe(c.target_width_mm);
    expect(c.config.garment_rgb).toEqual(fixture.fabric_rgb);
    expect(c.config).not.toHaveProperty("thread_brand");
  }
});

test("a thread brand the customer picked is the one key that changes the request", () => {
  // Not part of the fixture: the default request has no brand. Pinned here so
  // the arm the flip sheets do not run is not silently different either.
  globalThis.localStorage = {
    getItem: (k) => (k === "embstudio:threadPalette" ? "isacord" : null),
    setItem: () => {},
    removeItem: () => {},
  };
  const base = fixture.cases.find((c) => c.name === "hat_front_81").config;
  expect(requestFor("hat_front", 81)).toEqual({ ...base, thread_brand: "isacord" });
});
