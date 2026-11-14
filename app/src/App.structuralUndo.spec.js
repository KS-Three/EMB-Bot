// Every App.svelte handler that ADDS or REMOVES an element must record it as
// a discrete undo step (persistStructural), never through a bare persist().
//
// A bare persist() lets history.js coalesce the edit into whatever was
// recorded inside the previous 500 ms. For a drag that is the point; for a
// delete made right after an add it overwrote the add's snapshot, so Undo
// went back past both and the deleted element never came back (pinned as a
// test.fail() in e2e/undo-redo.spec.js from 2026-10-08 until 2026-11-12).
//
// Like App.projectReplacement.spec.js this pins the RULE rather than the call
// sites, so a new handler that adds or removes an element cannot quietly
// repeat the bug. It is a source-level pairing check, not a behavioural one:
// the behaviour is the e2e spec above and lib/history.spec.js.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const SRC = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "App.svelte"), "utf8");

// Matched as `= X(` so the import line and prose mentions do not count.
const STRUCTURAL = /= (addElement|addSeededTextElement|removeElement)\(/g;

function enclosingFunction(src, index) {
  const start = src.slice(0, index).lastIndexOf("\n  function ");
  expect(start, "call site is not inside a top-level function").toBeGreaterThan(-1);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) {
      return { name: /function\s+(\w+)/.exec(src.slice(start, start + 60))[1], body: src.slice(start, i + 1) };
    }
  }
  throw new Error("unbalanced braces");
}

test("every handler that adds or removes an element records a discrete undo step", () => {
  const seen = new Set();
  for (let m = STRUCTURAL.exec(SRC); m; m = STRUCTURAL.exec(SRC)) {
    const fn = enclosingFunction(SRC, m.index);
    seen.add(fn.name);
    expect(fn.body, `${fn.name}() calls ${m[1]}() but never persistStructural()`).toMatch(/\bpersistStructural\(\)/);
    expect(fn.body, `${fn.name}() calls ${m[1]}() and still has a bare persist()`).not.toMatch(/\bpersist\(\)/);
  }
  // Guard the guard: a rename must not leave this asserting nothing.
  expect([...seen].sort()).toEqual(["onAddElement", "onArtFile", "onConvertClusterToText", "onRemoveElement"]);
});

test("persistStructural records discretely, and one task's second record continues the first", () => {
  expect(SRC).toMatch(/function persistStructural\(\) \{\s*persist\(true, true\);\s*\}/);
  // The cluster "Undo — remove text element" click is a patch then a remove
  // in one task; persist() must not split them (see its comment).
  // (`gesture` rides after it since 2026-11-13: a field drag's token.)
  expect(SRC).toMatch(/history\.record\(project, undefined, discrete && !recordedThisTask, gesture\)/);
});

// One level down: a hand-drawn element's SHAPES. ManualPanel flags a shape
// added or removed as `discrete` (ManualPanel.spec.js pins that), and the
// flag only means anything if App passes it on to history. The field's
// binding always did; the panel's dropped it until 2026-11-12, which is why
// a shape deleted right after it was drawn could not be undone.
test("both elupdate bindings pass the discrete flag through to elUpdate", () => {
  const bindings = SRC.match(/on:elupdate=\{\(e\) => elUpdate\([^\n]*\)\}/g) || [];
  expect(bindings, "expected the field's binding and the panel's").toHaveLength(2);
  // The field's also passes its drag's gesture token (2026-11-13).
  for (const b of bindings) expect(b).toMatch(/!!e\.detail\.discrete(, e\.detail\.gesture)?\)\}$/);
});

// One pointer gesture is one undo step (2026-11-13): the field stamps every
// drag flush with its press's token, and App must hand it to history on both
// the single-element and the group path, or the 500 ms clock decides again.
test("the field's drag flushes pass their gesture token through to history", () => {
  expect(SRC).toMatch(/on:elupdate=\{\(e\) => elUpdate\(e\.detail\.id, e\.detail\.patch, !e\.detail\.quiet, !!e\.detail\.discrete, e\.detail\.gesture\)\}/);
  expect(SRC).toMatch(/on:elupdatemanygesture=\{\(e\) => elUpdateMany\(e\.detail\.patches, true, false, e\.detail\.gesture\)\}/);
  expect(SRC).toMatch(/function elUpdate\(id, patch, record = true, discrete = false, gesture = null\) \{[^}]*persist\(record, discrete, gesture\);/);
  expect(SRC).toMatch(/function elUpdateMany\(patchById, record = true, discrete = false, gesture = null\) \{[^}]*persist\(record, discrete, gesture\);/);
});
