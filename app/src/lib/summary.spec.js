import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { contentSummary } from "./summary.js";
import {
  defaultProject, addElement,
  defaultTextElement, defaultImageElement, defaultDesignElement,
  defaultDigitizedElement, defaultManualElement, defaultShapeElement,
} from "./project.js";

const PROJECT_JS = fileURLToPath(new URL("./project.js", import.meta.url));

// The types `addElement` can actually build, read off project.js's own
// factory ternary rather than copied here. A copied list is a second source
// of truth that agrees on the day it is written; this one cannot.
function typesAddElementBuilds() {
  const src = readFileSync(PROJECT_JS, "utf8");
  const m = src.match(/export function addElement[\s\S]*?const factory =([\s\S]*?);\n/);
  expect(m, "addElement's factory ternary is no longer parseable").toBeTruthy();
  const types = [...m[1].matchAll(/type === "([a-z]+)"/g)].map((x) => x[1]);
  // Plus the ternary's own trailing fallback, which is text.
  expect(m[1]).toContain("defaultTextElement");
  return [...types, "text"];
}

test("the parser finds the real factory list, not an empty one", () => {
  // A regex that matches nothing would make every assertion below vacuous.
  const types = typesAddElementBuilds();
  expect(types).toEqual(expect.arrayContaining(
    ["image", "design", "digitized", "manual", "shape", "text"]));
  expect(types).toHaveLength(6);
});

// --- the defect this module was cut out of App.svelte to fix ---------------
//
// The markup ended in a `{:else}` that assumed a TEXT element. `digitized`,
// `design` and `shape` carry no `text` and no `fontKey`, so the review step —
// the screen immediately before Download — recapped an auto-digitized design,
// the commonest path in the app, as `Content: Text — "undefined"` above a
// blank `Font`. Measured in a real browser 2026-09-07.

test("every element type addElement can build gets its own recap — none falls through to text", () => {
  const factories = {
    text: defaultTextElement, image: defaultImageElement,
    design: defaultDesignElement, digitized: defaultDigitizedElement,
    manual: defaultManualElement, shape: defaultShapeElement,
  };
  for (const type of typesAddElementBuilds()) {
    const rows = contentSummary(factories[type]("e1"));
    const text = rows.map((r) => `${r.label}: ${r.value}`).join(" | ");

    // The failure mode, stated as itself: a value that reads as a bug report.
    expect(text, type).not.toMatch(/undefined|null|NaN|\[object/i);
    // A row must never be blank — `readable(undefined)` returned "" and the
    // Font row rendered as an empty cell.
    for (const row of rows) expect(String(row.value).trim(), `${type}.${row.label}`).not.toBe("");
    // And only a text element may be described as text.
    if (type !== "text") expect(text, type).not.toMatch(/^Content: Text/);
    expect(rows[0].label).toBe("Content");
    expect(rows).toHaveLength(2);
  }
});

test("a freshly added element of every type is describable straight away", () => {
  // Not the same assertion: addElement re-seeds sizeMm/offsets on non-first
  // elements, so this drives the shape the app actually holds rather than the
  // factory's own output.
  for (const type of typesAddElementBuilds()) {
    let project = addElement(defaultProject(), type, 130);
    const el = project.elements[project.elements.length - 1];
    expect(el.type, `addElement("${type}") built a ${el.type}`).toBe(type);
    const text = contentSummary(el).map((r) => r.value).join(" | ");
    expect(text, type).not.toMatch(/undefined|null|NaN|\[object/i);
  }
});

// --- the empty states, which are what a first-time customer sees -----------

test("an empty text element says so in words, not as two quote marks", () => {
  const rows = contentSummary(defaultTextElement("e1"));
  expect(rows[0].value).toBe("Text — nothing typed yet");
  expect(rows[0].value).not.toContain('""');
});

test("a text element with content quotes it, and names its font", () => {
  const rows = contentSummary({ ...defaultTextElement("e1"), text: "HELLO", fontKey: "medium_font" });
  expect(rows[0].value).toBe('Text — "HELLO"');
  expect(rows[1].value).toBe("Medium Font");
});

test("whitespace is not content", () => {
  expect(contentSummary({ type: "text", text: "   \n " })[0].value).toBe("Text — nothing typed yet");
});

test("an artwork element names the file once one is uploaded", () => {
  expect(contentSummary(defaultDigitizedElement("e1"))[1].value).toBe("not uploaded yet");
  const named = { ...defaultDigitizedElement("e1"), name: "acme-logo.png" };
  expect(contentSummary(named)).toEqual([
    { label: "Content", value: "Auto-digitized artwork" },
    { label: "Artwork", value: "acme-logo.png" },
  ]);
});

test("the image and manual branches keep the wording the e2e specs assert", () => {
  // wizard-smoke.spec.js pins "Logo / image" and "background removed" on the
  // review recap; changing them here would break it in another file.
  const img = contentSummary({ type: "image", nColors: 4, removeBg: true });
  expect(img[0].value).toBe("Logo / image");
  expect(img[1].value).toBe("4 · background removed");
  expect(contentSummary({ type: "image", nColors: 4, removeBg: false })[1].value).toBe("4");

  const man = contentSummary({ type: "manual", shapes: [{}, {}, {}] });
  expect(man[0].value).toBe("Hand-drawn shapes");
  expect(man[1].value).toBe("3");
  expect(contentSummary({ type: "manual" })[1].value).toBe("0");
});

test("a missing or malformed element never throws", () => {
  // App.svelte's `selectedElement` is `find(...) || elements[0]`, so it is
  // undefined for an empty project. The old markup dereferenced `.text` on
  // it; this must not.
  for (const bad of [undefined, null, {}, { type: "unheard_of" }]) {
    expect(() => contentSummary(bad)).not.toThrow();
    expect(contentSummary(bad)).toHaveLength(2);
  }
});
