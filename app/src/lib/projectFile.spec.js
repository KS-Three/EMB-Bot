import { test, expect } from "vitest";
import {
  buildProjectFile,
  parseProjectFile,
  projectFileName,
  sourceKeysOf,
  encodeBase64,
  decodeBase64,
  PROJECT_FILE_FORMAT,
  PROJECT_FILE_VERSION,
  SOURCE_MAX_BYTES,
} from "./projectFile.js";
import { defaultProject, defaultDigitizedElement, migrateProject, updateElement, addElement } from "./project.js";

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

// --- the silent-blank class: an accepted import that lost the design ------
// Found 2026-09-14 (the gap audit's finding 4), reproduced on 3 of 4 envelope
// shapes before the fix. The envelope gate accepted ANY inner payload on the
// promise that "the inner project's own migration handles forward compat";
// migrateProject matched `version === 2` exactly and blanked everything else.
// The result was the worst of the three possible outcomes -- not an error, not
// the design, but an empty design wearing the customer's own file name.
// Both halves now key on the same recognizer, so they cannot drift apart.

const realProject = (version) => {
  const p = defaultProject();
  const el = p.elements[0];
  const withText = updateElement(p, el.id, { text: "FRITSCH'S STITCHES" });
  return version === undefined ? (({ version: _v, ...rest }) => rest)(withText) : { ...withText, version };
};

test("an .embproj carrying a FORWARD-version project imports its design, not a blank", () => {
  const parsed = parseProjectFile(buildProjectFile(realProject(3), "Kent's Hat #2"));
  expect(parsed).not.toBeNull();
  expect(parsed.name).toBe("Kent's Hat #2");
  expect(parsed.project.elements[0].text).toBe("FRITSCH'S STITCHES");
});

test("an .embproj whose version stamp is the string \"2\" imports its design", () => {
  const parsed = parseProjectFile(buildProjectFile(realProject("2"), "Kent's Hat #2"));
  expect(parsed.project.elements[0].text).toBe("FRITSCH'S STITCHES");
});

test("an .embproj whose project lost its version key imports its design", () => {
  const parsed = parseProjectFile(buildProjectFile(realProject(undefined), "Kent's Hat #2"));
  expect(parsed.project.elements[0].text).toBe("FRITSCH'S STITCHES");
});

test("an .embproj envelope wrapping a payload with no design in it is REJECTED, not blanked", () => {
  // The remaining half of the same fix: when there is genuinely nothing to
  // recover, the import path has somewhere to report an error, so it must
  // reject rather than hand back the blank migrateProject would produce.
  expect(parseProjectFile(JSON.stringify({ format: "embproj", version: 1, project: { foo: 1 } }))).toBeNull();
  expect(parseProjectFile(JSON.stringify({ format: "embproj", version: 1, project: {} }))).toBeNull();
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

// --- the customer's original artwork rides in the file (2026-09-20) --------
//
// A digitize sends the FILE, whose bytes live in IndexedDB under their
// SHA-256 (lib/sourceStore.js); the registry record carries only the key. So
// a design opened on another machine had the 1,200-px preview and nothing
// else. The envelope now carries the originals BESIDE the project, and only
// the ones an element points at.

function bytesOf(n, seed = 1) {
  const out = new Uint8Array(n);
  for (let i = 0; i < n; i++) out[i] = (i * 31 + seed * 7) & 0xff;
  return out;
}

function digitizedProject(keys) {
  const elements = keys.map((key, i) => ({
    ...defaultDigitizedElement("d" + (i + 1)),
    name: "logo.png",
    sourcePng: "data:image/png;base64,AAAA",
    sourceFile: key ? { key, type: "image/png", size: 3, width: 10, height: 10 } : null,
  }));
  return { ...defaultProject(), elements, selectedId: "d1" };
}

test("an original the store holds rides in the file and comes back byte for byte", () => {
  const project = digitizedProject(["abc"]);
  const bytes = bytesOf(1000);
  const text = buildProjectFile(project, "Cap", { abc: { bytes, type: "image/png", name: "logo.png" } });

  const raw = JSON.parse(text);
  expect(raw.sources.abc.size).toBe(1000);
  expect(typeof raw.sources.abc.data).toBe("string");
  // The project object itself stays byte-free: the bytes sit beside it.
  expect(JSON.stringify(raw.project)).not.toContain(raw.sources.abc.data.slice(0, 32));

  const parsed = parseProjectFile(text);
  expect(parsed.project.elements[0].sourceFile.key).toBe("abc");
  expect(parsed.sources.abc.bytes).toEqual(bytes);
  expect(parsed.sources.abc.type).toBe("image/png");
  expect(parsed.sources.abc.name).toBe("logo.png");
});

test("only originals an element points at are written, and a project with none writes the envelope it always did", () => {
  const project = digitizedProject(["abc"]);
  const text = buildProjectFile(project, "Cap", {
    abc: { bytes: bytesOf(5), type: "", name: "" },
    zzz: { bytes: bytesOf(5, 2), type: "image/png", name: "stranger.png" },
    empty: { bytes: new Uint8Array(0) },
  });
  expect(Object.keys(JSON.parse(text).sources)).toEqual(["abc"]);

  // No stored original, or nothing to embed: no `sources` member at all.
  expect("sources" in JSON.parse(buildProjectFile(defaultProject(), "x", { abc: { bytes: bytesOf(5) } }))).toBe(false);
  expect("sources" in JSON.parse(buildProjectFile(project, "x"))).toBe(false);
  expect("sources" in JSON.parse(buildProjectFile(project, "x", {}))).toBe(false);
});

test("a file without originals parses to an empty sources map, a bare record too", () => {
  expect(parseProjectFile(buildProjectFile(digitizedProject(["abc"]), "x")).sources).toEqual({});
  expect(parseProjectFile(JSON.stringify(digitizedProject(["abc"]))).sources).toEqual({});
});

test("malformed or unreferenced source entries are dropped and the design still imports", () => {
  const project = digitizedProject(["abc"]);
  const envelope = (sources) =>
    JSON.stringify({ format: PROJECT_FILE_FORMAT, version: 2, name: "x", project, sources });
  const cases = [
    "not an object",
    ["abc"],
    { abc: "not an object" },
    { abc: { data: 42 } },
    { abc: { data: "!!!!" } },                       // not base64
    { abc: { data: "abc" } },                        // not a multiple of 4
    { abc: { data: "" } },                           // decodes to nothing
    { other: { data: encodeBase64(bytesOf(9)) } },   // no element points at it
  ];
  for (const sources of cases) {
    const parsed = parseProjectFile(envelope(sources));
    expect(parsed, JSON.stringify(sources)).not.toBeNull();
    expect(parsed.project.elements[0].sourceFile.key).toBe("abc");
    expect(parsed.sources).toEqual({});
  }
  // And a good entry beside a bad one survives.
  const parsed = parseProjectFile(envelope({ abc: { data: encodeBase64(bytesOf(9)), type: 7, name: null }, bad: 1 }));
  expect(parsed.sources.abc.bytes).toEqual(bytesOf(9));
  expect(parsed.sources.abc.type).toBe("");
  expect(parsed.sources.abc.name).toBe("");
});

test("an oversize original is refused before it is decoded", () => {
  const project = digitizedProject(["abc"]);
  const text = buildProjectFile(project, "x", { abc: { bytes: bytesOf(200), type: "image/png", name: "big.png" } });
  expect(parseProjectFile(text, { maxSourceBytes: 100 }).sources).toEqual({});
  expect(parseProjectFile(text, { maxSourceBytes: 200 }).sources.abc.bytes).toEqual(bytesOf(200));
  expect(parseProjectFile(text).sources.abc.bytes).toEqual(bytesOf(200));
  expect(SOURCE_MAX_BYTES).toBeGreaterThanOrEqual(12 * 1024 * 1024);   // the service's upload limit fits
});

test("the base64 helpers round-trip every length and refuse what is not base64", () => {
  for (let n = 0; n < 7; n++) {
    const b = bytesOf(n, n);
    expect(decodeBase64(encodeBase64(b))).toEqual(b);
  }
  const big = bytesOf(100_000, 3);
  expect(decodeBase64(encodeBase64(big))).toEqual(big);
  expect(decodeBase64("abc")).toBeNull();
  expect(decodeBase64("ab=c")).toBeNull();
  expect(decodeBase64("a b=")).toBeNull();
  expect(decodeBase64(42)).toBeNull();
  expect(decodeBase64("")).toEqual(new Uint8Array(0));
});

test("the version stamp is 2 and a version-1 file parses the same as a version-2 one", () => {
  expect(PROJECT_FILE_VERSION).toBe(2);
  const project = digitizedProject(["abc"]);
  const v1 = JSON.stringify({ format: PROJECT_FILE_FORMAT, version: 1, name: "Old", savedAt: "2026-07-29T00:00:00Z", project });
  const p1 = parseProjectFile(v1);
  const p2 = parseProjectFile(buildProjectFile(project, "Old"));
  expect(p1.project).toEqual(p2.project);
  expect(p1.sources).toEqual({});
  expect(p1.name).toBe("Old");
});

test("sourceKeysOf names each original once and ignores everything that is not a digitized upload", () => {
  const project = digitizedProject(["abc", "abc", null, "def"]);
  project.elements.push({ ...defaultProject().elements[0], id: "t1" });      // a text element
  expect(sourceKeysOf(project)).toEqual(["abc", "def"]);
  expect(sourceKeysOf(defaultProject())).toEqual([]);
  expect(sourceKeysOf(null)).toEqual([]);
  expect(sourceKeysOf({ elements: "nope" })).toEqual([]);
});
