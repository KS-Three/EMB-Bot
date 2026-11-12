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
  expect(SRC).toMatch(/history\.record\(project, undefined, discrete && !recordedThisTask\)/);
});
