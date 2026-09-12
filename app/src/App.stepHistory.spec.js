// Every step change has to go through lib/stepHistory.js.
//
// A bare `step = ...` anywhere in App.svelte moves the panel without moving
// the browser, and from then on the two disagree about where Back lands: the
// customer presses Back expecting the step they can see behind them and gets
// the one the history stack still thinks is current — or, on the entry the
// app booted on, leaves the Studio a step early. The bug this whole change
// fixes (MASTER_SCOPE open item 15) is exactly "the panel moved and history
// did not", so a second site quietly reintroducing it is the regression worth
// a guard.
//
// Source-level, in the same idiom as App.projectReplacement.spec.js next to
// it: a cheap pairing check, honest about not being the behavioural one. The
// behavioural half is lib/stepHistory.spec.js, which drives a real jsdom
// session history including Back off the first step.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const SRC = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "App.svelte"), "utf8");

// `step`, not `targetStep`/`nextStep`/anything ending in one: a preceding
// word character or dot means a different identifier.
const ASSIGNMENTS = /(?<![\w.$])step\s*=\s*/g;

// The two the rule allows, matched on their whole line so a third site
// cannot pass by resembling one:
//   - the declaration
//   - the onStep callback, which is stepHistory's own way of applying a step
const ALLOWED = [/^\s*let step = "garment";$/, /^\s*onStep: \(s\) => \(step = s\),$/];

test("no step assignment bypasses the history helper", () => {
  const offenders = [];
  ASSIGNMENTS.lastIndex = 0;
  for (let m = ASSIGNMENTS.exec(SRC); m; m = ASSIGNMENTS.exec(SRC)) {
    const lineStart = SRC.lastIndexOf("\n", m.index) + 1;
    const lineEnd = SRC.indexOf("\n", m.index);
    const line = SRC.slice(lineStart, lineEnd === -1 ? SRC.length : lineEnd);
    // A line of prose about the rule is not a breach of it — including the
    // one in App.svelte that states it. (`//` only: this file's script has
    // no block comments, and anything after a `//` on a code line is prose
    // too.)
    if (/^\s*\/\//.test(line)) continue;
    // `step === "garment"` and friends are reads, not assignments.
    if (/step\s*===?\s*/.test(line.slice(m.index - lineStart))) continue;
    if (ALLOWED.some((re) => re.test(line))) continue;
    offenders.push(line.trim());
  }
  expect(
    offenders,
    "assign the step through stepHistory.go()/replace() instead — a bare assignment leaves the browser's Back on the wrong entry",
  ).toEqual([]);
});

test("the two allowed assignments are both still there", () => {
  // Guard the guard: if the declaration or the callback is renamed away, the
  // test above starts asserting nothing rather than failing.
  for (const re of ALLOWED) {
    expect(SRC.split("\n").some((l) => re.test(l)), `no line matches ${re}`).toBe(true);
  }
});

test("boot seeds the history with start(), and exactly once", () => {
  // start() is the replaceState — the first step reusing the entry the
  // browser already has. Called twice, or replaced by a go(), and Back from
  // the first step lands back on the Studio.
  expect(SRC.match(/stepHistory\.start\(/g)).toHaveLength(1);
  expect(SRC).toMatch(/stepHistory\.start\(step\);/);
});

test("popstate is wired to the helper on window", () => {
  expect(SRC).toMatch(/<svelte:window[^>]*on:popstate=\{\(e\) => stepHistory\.pop\(e\)\}/);
});
