import { test, expect } from "vitest";
import {
  buildProjectFile,
  parseProjectFile,
  projectFileName,
  PROJECT_FILE_FORMAT,
  PROJECT_FILE_VERSION,
} from "./projectFile.js";
import { defaultProject, migrateProject, updateElement, addElement } from "./project.js";

// --- round trip ---------------------------------------------------------

test("buildProjectFile -> parseProjectFile round-trips a project and its name losslessly", () => {
  let project = defaultProject();
  const el = project.elements[0];
  project = updateElement(project, el.id, { text: "Fritsch's Stitches", letterSpacingMm: 2.5 });

  const text = buildProjectFile(project, "Hat name #2");
  const parsed = parseProjectFile(text);

  expect(parsed).not.toBeNull();
  expect(parsed.name).toBe("Hat name #2");
  // The parsed project must equal what the registry itself would produce
  // from this project (parse runs migrateProject, which is idempotent on a
  // current-version project).
  expect(parsed.project).toEqual(migrateProject(project));
});

test("a manual hoop pick survives the .embproj round trip (launch item 2)", () => {
  const project = { ...defaultProject(), hoopId: "6x10" };
  const parsed = parseProjectFile(buildProjectFile(project, "Hooped"));
  expect(parsed.project.hoopId).toBe("6x10");
  // and a pre-hoop-picker file (no hoopId key at all) parses to the
  // "use the suggestion" default rather than undefined
  const pre = { ...defaultProject() };
  delete pre.hoopId;
  expect(parseProjectFile(buildProjectFile(pre, "Old")).project.hoopId).toBeNull();
});

test("a preset shape element survives the file round-trip with its kind/params intact", () => {
  let project = addElement(defaultProject(), "shape", 100);
  const id = project.selectedId;
  project = updateElement(project, id, {
    kind: "star",
    params: { points: 7, innerRatio: 0.35 },
    sizeMm: 42,
    colorRgb: [200, 30, 30],
  });

  const parsed = parseProjectFile(buildProjectFile(project, "Star patch"));
  expect(parsed).not.toBeNull();
  const el = parsed.project.elements.find((e) => e.id === id);
  expect(el.type).toBe("shape");
  expect(el.kind).toBe("star");
  expect(el.params).toEqual({ points: 7, innerRatio: 0.35 });
  expect(el.sizeMm).toBe(42);
  expect(el.colorRgb).toEqual([200, 30, 30]);
});

test("the envelope carries format/version stamps", () => {
  const parsed = JSON.parse(buildProjectFile(defaultProject(), "x"));
  expect(parsed.format).toBe(PROJECT_FILE_FORMAT);
  expect(parsed.version).toBe(PROJECT_FILE_VERSION);
  expect(typeof parsed.savedAt).toBe("string");
});

test("a missing/blank name falls back sensibly on both ends", () => {
  const parsed = parseProjectFile(buildProjectFile(defaultProject(), ""));
  expect(parsed.name).toBe("Untitled design");
  const noName = JSON.stringify({ format: "embproj", version: 1, project: defaultProject() });
  expect(parseProjectFile(noName).name).toBe("Imported design");
});

// --- rejection: the shape gate is load-bearing --------------------------
// migrateProject never throws (it normalizes ANYTHING into a valid
// project), so parseProjectFile's own gate is the only thing standing
// between "imported a random .json" and "silently created a blank design".

test("parseProjectFile rejects non-JSON, non-object JSON, and unrecognized objects", () => {
  expect(parseProjectFile("not json at all")).toBeNull();
  expect(parseProjectFile("42")).toBeNull();
  expect(parseProjectFile("[1,2,3]")).toBeNull();
  expect(parseProjectFile("null")).toBeNull();
  expect(parseProjectFile(JSON.stringify({ foo: "bar" }))).toBeNull();
});

test("parseProjectFile rejects an embproj envelope whose project payload is missing or malformed", () => {
  expect(parseProjectFile(JSON.stringify({ format: "embproj", version: 1 }))).toBeNull();
  expect(parseProjectFile(JSON.stringify({ format: "embproj", version: 1, project: "nope" }))).toBeNull();
  expect(parseProjectFile(JSON.stringify({ format: "embproj", version: 1, project: [1] }))).toBeNull();
});

// --- bare-record leniency ------------------------------------------------

test("parseProjectFile accepts a bare v2 project record (hand-rescued from localStorage)", () => {
  const bare = defaultProject();
  const parsed = parseProjectFile(JSON.stringify(bare));
  expect(parsed).not.toBeNull();
  expect(parsed.name).toBe("Imported design");
  expect(parsed.project).toEqual(migrateProject(bare));
});

test("parseProjectFile accepts a bare v1 blob and migrates it", () => {
  const v1 = { mode: "text", text: "KENT", fontKey: "medium_font" };
  const parsed = parseProjectFile(JSON.stringify(v1));
  expect(parsed).not.toBeNull();
  expect(parsed.project.version).toBe(2);
  expect(parsed.project.elements.length).toBeGreaterThan(0);
});

// --- filenames -----------------------------------------------------------

test("projectFileName sanitizes to a safe kebab-case .embproj name", () => {
  expect(projectFileName("Fritsch's Stitches: Hat #2")).toBe("fritsch-s-stitches-hat-2.embproj");
  expect(projectFileName("  ---  ")).toBe("design.embproj");
  expect(projectFileName("")).toBe("design.embproj");
  expect(projectFileName("Simple")).toBe("simple.embproj");
});
