// Every path that WHOLLY REPLACES the project must clear `runtime`.
//
// `runtime` holds { flats, workImages } keyed by ELEMENT ID. A whole-project
// replacement mints fresh elements, and template patches hard-code the id
// "e1" -- so a replacement that leaves runtime alone hands the new element the
// previous design's flattened artwork. Pick "Logo patch", upload a logo, go
// Back, pick a template again: the fresh e1 says _hasImage false and the user
// uploaded nothing, but runtime.flats.e1 still holds the old logo.
//
// enterProject always cleared it. pickTemplate, its sibling, did not, for as
// long as both have existed. Found by a sibling-pattern sweep 2026-08-26.
//
// So this pins the RULE rather than the one call site: the bug was precisely
// that a second path did not follow a rule the first one did, and a test that
// only checked pickTemplate would leave a third path free to repeat it.
//
// What it does NOT prove: that clearing runtime produces the right screen. It
// is a source-level pairing check, not a behavioural one -- honest about being
// the cheap guard rather than the complete one. The behavioural version is a
// Playwright round trip (pick template -> upload -> back -> pick template ->
// assert no artwork), which belongs in e2e/ if this ever regresses in a way
// this misses.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const SRC = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "App.svelte"), "utf8");

// The ASSIGNMENTS that mean "the element set is now entirely different".
//
// Matched as `project = X(`, not as a bare `X(`: the bare form also hits
// resetHasImage's own definition and the `let project = resetHasImage(...)`
// module-level initialiser, neither of which is a replacement of a live
// project (runtime is initialised empty right below that line anyway). The
// first draft of this test matched the bare form and reported the definition
// as a violation -- correctly refusing to pass, but for the wrong reason.
//
// Deliberately NOT listed: applyHistorySnapshot's `project = truthHasImage(p)`.
// Undo/redo restores elements that legitimately still own their flats, so
// clearing runtime there would throw away artwork the user is undoing BACK to.
const REPLACERS = [/^\s+project = applyTemplate\(/gm, /^\s+project = resetHasImage\(/gm];
const CLEAR = /runtime\s*=\s*\{\s*flats:\s*\{\s*\}\s*,\s*workImages:\s*\{\s*\}\s*\}/;

// The body of the `function NAME(...) { ... }` containing `index`, by brace
// matching from the signature.
function enclosingFunction(src, index) {
  const before = src.slice(0, index);
  const start = before.lastIndexOf("\n  function ");
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

test("every whole-project-replacement path clears the element-keyed runtime", () => {
  const seen = [];
  for (const re of REPLACERS) {
    re.lastIndex = 0;
    for (let m = re.exec(SRC); m; m = re.exec(SRC)) {
      const fn = enclosingFunction(SRC, m.index + m[0].length - 1);
      seen.push(fn.name);
      expect(CLEAR.test(fn.body), `${fn.name}() replaces the project but never clears runtime`).toBe(true);
    }
  }
  // Guard the guard: if the calls are ever renamed, this test must not quietly
  // start asserting nothing.
  expect(seen.length, "found no project-replacement call sites at all").toBeGreaterThanOrEqual(2);
  expect(seen).toContain("pickTemplate");
  expect(seen).toContain("enterProject");
});
