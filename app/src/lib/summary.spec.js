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

// --- the whole design, not just the element the user last clicked -----------

import { designSummary } from "./summary.js";

test("a single-element project reads exactly as it did before numbering existed", () => {
  const p = { elements: [{ ...defaultTextElement("e1"), text: "EMB TEST", fontKey: "medium_font" }] };
  expect(designSummary(p)).toEqual([
    { label: "Content", value: 'Text — "EMB TEST"' },
    { label: "Font", value: "Medium Font" },
  ]);
  // wizard-smoke.spec.js asserts `Text — "EMB TEST"` and "Logo / image" on
  // this screen; an unconditional "Content 1" would break it elsewhere.
  expect(designSummary(p)[0].label).toBe("Content");
});

test("a name plus a logo names BOTH — the commonest real job", () => {
  // Measured 2026-09-07 in a browser: left chest, "FRITSCH'S" plus
  // enthusiast_logo.png, 3542 stitches across three cones. The recap keyed
  // off the selected element and said only "Auto-digitized artwork".
  const p = { elements: [
    { ...defaultTextElement("e1"), text: "FRITSCH'S", fontKey: "medium_font" },
    // `result` set: designSummary lists what will SEW, so a digitized element
    // that has not run yet is not part of the recap.
    { ...defaultDigitizedElement("e2"), name: "enthusiast_logo.png", result: { design: {} } },
  ]};
  expect(designSummary(p)).toEqual([
    { label: "Content 1", value: 'Text — "FRITSCH\'S"' },
    { label: "Font", value: "Medium Font" },
    { label: "Content 2", value: "Auto-digitized artwork" },
    { label: "Artwork", value: "enthusiast_logo.png" },
  ]);
});

test("numbering follows sew order, and every element is present exactly once", () => {
  const p = { elements: ["e1", "e2", "e3", "e4"].map((id, i) =>
    ({ ...defaultTextElement(id), text: "T" + i })) };
  const rows = designSummary(p);
  expect(rows.filter((r) => r.label.startsWith("Content")).map((r) => r.label))
    .toEqual(["Content 1", "Content 2", "Content 3", "Content 4"]);
  expect(rows).toHaveLength(8);
});

test("an empty or missing project falls back to the text empty state, never throws", () => {
  for (const p of [null, undefined, {}, { elements: [] }]) {
    expect(() => designSummary(p)).not.toThrow();
    expect(designSummary(p)[0].value).toBe("Text — nothing typed yet");
  }
});

test("a placeholder that sews nothing is left out, and does not push real content down the list", () => {
  // Every project is born with an empty text element. Listing elements
  // verbatim recapped a digitized logo as "Content 1: Text — nothing typed
  // yet / Content 2: Auto-digitized artwork" — the real content numbered
  // second, behind something that sews nothing. `flow.js`'s isSewable is the
  // rule, so this can never disagree with the Next button or the headline.
  const p = { elements: [
    defaultTextElement("e1"),                                    // untouched default
    { ...defaultDigitizedElement("e2"), name: "logo.png", result: { design: {} } },
  ]};
  expect(designSummary(p)).toEqual([
    { label: "Content", value: "Auto-digitized artwork" },
    { label: "Artwork", value: "logo.png" },
  ]);
});

test("a project with nothing sewable still describes itself", () => {
  // The state "Nothing to stitch yet" sits above — the recap must not go
  // blank there, or the screen says nothing at all about the design.
  const p = { elements: [defaultTextElement("e1")] };
  expect(designSummary(p)).toEqual([
    { label: "Content", value: "Text — nothing typed yet" },
    { label: "Font", value: "Medium Font" },
  ]);
});

// ---- the Colors row reports what SEWS, not what the slider says (2026-09-08)
//
// Measured in a browser that day, on the shipped "Logo patch" starter with its
// default 4-colour slider, driving the browser flatten lane (which is what a
// phone always gets, and what any machine gets with the service down). The
// review card — the last screen before Download — read:
//
//     Colors          4 · background removed
//     Stitches        3,011
//     Thread changes  1
//
// Colors and Thread changes are two rows apart and contradict each other: one
// thread change is two colour blocks. The panel one click back rendered two
// swatches, 70.1% and 29.9%. `Thread changes` is counted from the design's own
// {type:"color"} records (estimate.js); `Colors` alone was asserted from
// `element.nColors`, the slider, and never looked at the design at all.
//
// This matters in money, not tidiness: a colour is a cone to buy and, on a
// single-needle machine, a re-thread mid-job.

// `sewnColorCount` itself is proven against a real flattened palette in
// flatten.spec.js (a two-colour image reports 2 at every slider value from 2
// to 8). What is proven HERE is the wiring: that the row reports that number
// and not the element's own field.

test("the review recap counts the colours that sew, not the slider setting", () => {
  const el = { ...defaultImageElement("e1"), nColors: 4, removeBg: true, _hasImage: true };
  // Plant the shipped defect back and this reads "4 · background removed".
  expect(contentSummary(el, 2)[1].value).toBe("2 · background removed");
  // The slider is untouched — it is still the ceiling the customer chose, and
  // ImagePanel still shows 4 there. Only the recap's claim changed.
  expect(el.nColors).toBe(4);
});

test("the recap follows the art, not a fixed number", () => {
  // Two colours reported whether the customer asked for 2 or 8: the row is
  // about the artwork, so it must not track the slider in either direction.
  for (const asked of [2, 4, 8]) {
    const el = { ...defaultImageElement("e1"), nColors: asked, removeBg: false, _hasImage: true };
    expect(contentSummary(el, 2)[1].value, `asked=${asked}`).toBe("2");
  }
});

test("with nothing flattened the recap falls back to the ceiling rather than claiming zero", () => {
  // designSummary reaches an image element with no image only through its
  // "nothing sewable" branch, under the "Nothing to stitch yet" headline.
  // "Colors 0" there would be a confident lie about an empty element.
  const el = { ...defaultImageElement("e1"), nColors: 4, removeBg: true };
  for (const nothing of [null, undefined]) {
    expect(contentSummary(el, nothing)[1].value).toBe("4 · background removed");
  }
  expect(contentSummary(el)[1].value).toBe("4 · background removed");
  // Zero is a real answer and must survive the fallback, not be swallowed as
  // "no value" — `||` here would print the slider over a genuine zero.
  expect(contentSummary(el, 0)[1].value).toBe("0 · background removed");
});

test("designSummary looks each element's count up by ITS id", () => {
  const a = { ...defaultImageElement("a"), nColors: 6, removeBg: false, _hasImage: true };
  const b = { ...defaultImageElement("b"), nColors: 6, removeBg: false, _hasImage: true };
  const rows = designSummary({ elements: [a, b] }, { a: 2 });
  // Two image elements: the one with a flattened palette reports its sewn 2,
  // the one without falls back to its own ceiling. A lookup keyed on the wrong
  // id, or one that reused the first hit, would give both the same answer.
  const colors = rows.filter((r) => r.label === "Colors").map((r) => r.value);
  expect(colors).toEqual(["2", "6"]);
});
