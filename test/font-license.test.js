// licenseId() policy guard. The build gates on this id: anything it returns
// that sits in build-embf.mjs's ALLOWED_LICENSES ships in a product Kent
// intends to SELL, so a mislabel here is a licensing exposure, not a cosmetic
// bug. These cases pin the two failure modes the project has actually hit.
//
// 2026-08-21: "CC-BY-NC-SA 4.0" did not match the CC-BY-SA branch (the NC
// sits between BY and SA), fell through to bare CC-BY, and returned
// "CC-BY-4.0" — an ALLOWED id. Nine upstream fonts carry NC/ND terms and were
// all being reported as plain CC-BY-4.0. None had reached the shipping
// library (they fail QC as cross-stitch/fill fonts), but the next sweep would
// have walked into it.
const assert = require("node:assert");
const { test } = require("node:test");

// Mirrors ALLOWED_LICENSES in tools/build-embf.mjs. If that set changes, this
// must change with it — deliberately duplicated so a silent widening there
// breaks a test here.
const ALLOWED = new Set(["OFL-1.1", "CC-BY-4.0", "CC0"]);

const id = async (text) => {
  const { licenseId } = await import("../tools/font-license.mjs");
  return licenseId(text);
};

test("NonCommercial CC variants never resolve to an allowed id", async () => {
  const nc = [
    // verbatim from upstream embroidery-fonts PRs #75/#76/#77 (fornow,
    // rigart, therese) — note the "4 .0" spacing, which defeated the
    // version capture as well
    "This embroidery font  is licensed CC-BY-NC-SA4 .0 (http://creativecommons.org/licenses/by-sa/4.0/).",
    "Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)",
    "This work is licensed CC-BY-NC-ND 4.0",
    "Licensed under CC BY-NC-SA 3.0",
  ];
  for (const text of nc) {
    const got = await id(text);
    assert.ok(/NC/.test(got), `expected a NonCommercial id, got "${got}" for: ${text.slice(0, 60)}`);
    assert.ok(!ALLOWED.has(got), `NonCommercial font resolved to ALLOWED id "${got}"`);
  }
});

test("NoDerivatives CC variants never resolve to an allowed id", async () => {
  for (const text of ["Licensed CC-BY-ND 3.0", "Creative Commons Attribution-NoDerivatives 4.0"]) {
    const got = await id(text);
    assert.ok(!ALLOWED.has(got), `NoDerivatives font resolved to ALLOWED id "${got}"`);
  }
});

test("plain CC-BY stays allowed — the NC/ND check must not over-reject", async () => {
  // cogs_KOR is the library's one genuine CC-BY-4.0 font; over-rejecting here
  // would silently drop it from the build.
  for (const text of ["This font is licensed under CC-BY-4.0", "Licensed under CC BY 4.0"]) {
    const got = await id(text);
    assert.strictEqual(got, "CC-BY-4.0", `expected CC-BY-4.0, got "${got}"`);
    assert.ok(ALLOWED.has(got));
  }
});

test("ShareAlike, OFL, CC0 and GPL classification is unchanged", async () => {
  assert.strictEqual(await id("This font is licensed CC-BY-SA 4.0"), "CC-BY-SA-4.0");
  assert.strictEqual(await id("This Font Software is licensed under the SIL Open Font License, Version 1.1"), "OFL-1.1");
  assert.strictEqual(await id("Released into the public domain, CC0"), "CC0");
  assert.strictEqual(await id("GNU General Public License version 3"), "GPL-3.0");
});

test("every shipped font's sidecar still resolves to its manifest licenseId", async () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  for (const f of man.fonts) {
    const sidecar = fs.readFileSync(path.join(FONT_DIR, f.key + ".LICENSE.txt"), "utf8");
    assert.strictEqual(await id(sidecar), f.licenseId, "licenseId drift for " + f.key);
    assert.ok(ALLOWED.has(f.licenseId), "shipped font outside license policy: " + f.key);
  }
});
