// Compile-level guard on ONE bug shape, found three times in this app now:
// a Svelte 5 legacy `$:` statement whose behaviour depends on state it does
// not TEXTUALLY name.
//
// Svelte builds a legacy statement's dependency list from the identifiers the
// statement itself mentions. A read that happens inside a called helper is
// invisible to it, so the statement never re-runs when that state changes.
// The repo's idiom is to pass the state in as an argument -- ManualPanel's
// alphaIn(map, id), render()'s "ghost argument" list, and now ContentStep's
// shared(members, field).
//
// This asserts on the COMPILED OUTPUT rather than on behaviour, deliberately.
// The bug is invisible to a logic test: `shared()` computes the right answer
// either way, and what breaks is only whether it is ever called again. A
// component test would need a real multi-select round trip through App's
// elupdatemany, which is a lot of machinery to pin one dependency list.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { compile } from "svelte/compiler";

const HERE = dirname(fileURLToPath(import.meta.url));

function compiled(name) {
  const src = readFileSync(join(HERE, name), "utf8");
  return compile(src, { generate: "client", filename: name }).js.code;
}

// The `$.legacy_pre_effect(() => (deps), () => { body })` pair for the
// statement that assigns `varName`, as [depsText, bodyText].
function effectFor(code, varName) {
  const lines = code.split("\n");
  const i = lines.findIndex((l) => l.includes(`$.set(${varName},`));
  expect(i, `no legacy effect assigns ${varName}`).toBeGreaterThan(-1);
  // The dependency thunk is the nearest legacy_pre_effect line above it.
  let j = i;
  while (j >= 0 && !lines[j].includes("legacy_pre_effect")) j--;
  expect(j, `no legacy_pre_effect above $.set(${varName})`).toBeGreaterThan(-1);
  return { deps: lines.slice(j, i).join("\n"), body: lines[i] };
}

test("ContentStep's shared-field statements track the members they actually read", () => {
  // The bug: all three named only `multi` -- a BOOLEAN. Once multi-select is
  // entered it is true and stays true, safe_not_equal(true, true) is false, so
  // the effects never re-ran. Ctrl+click two text elements with different
  // weights, click Bold: the elements really change, but the panel keeps
  // reading "Weight · mixed" and no button lights up, so the user's own edit
  // looks like it did nothing. Found 2026-08-26.
  const code = compiled("ContentStep.svelte");
  for (const v of ["sharedColor", "sharedWeight", "sharedFont"]) {
    const { deps } = effectFor(code, v);
    expect(deps, `${v} does not track selTextMembers`).toContain("selTextMembers");
  }
});

test("ManualPanel's selectedAlpha tracks shapeAlpha, not just the selection", () => {
  // The same shape, fixed in PR #264: the Dim slider and its Reset button
  // froze at whatever value the shape had when it was selected. Pinned here
  // too so the two live under one rule rather than one being remembered and
  // the other rediscovered.
  const code = compiled("ManualPanel.svelte");
  const { deps } = effectFor(code, "selectedAlpha");
  expect(deps).toContain("shapeAlpha");
});

test("DigitizePanel's cluster member list tracks the shapes, not just the cluster id", () => {
  // Same shape again, in an {@const} instead of a `$:`. The each is keyed by
  // clusterId -- a string that never changes for a surviving block -- so a
  // wrapper that read liveReviewShapes from the closure was computed once and
  // never again. Delete one member of a 4-shape "looks like text" cluster and
  // the banner kept reading "4 shapes". Found 2026-08-26.
  const code = compiled("DigitizePanel.svelte");
  const lines = code.split("\n");
  const i = lines.findIndex(
    (l, k) => /derived_safe_equal/.test(l) && lines.slice(k, k + 5).join(" ").includes("textClusterMembers"),
  );
  expect(i, "no derived computes the cluster member list").toBeGreaterThan(-1);
  const deps = lines.slice(i, i + 5).join("\n");
  expect(deps, "the cluster member list does not track liveReviewShapes").toContain("$.get(liveReviewShapes)");
});
