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

// A font's own licence is not the whole story: it may DERIVE from a font under
// a different licence family, whose conditions then ride along. 71 of the 80
// shipped fonts declare a derivative base, but for all but one that base is
// itself OFL, so shipping the OFL text discharges everything.
//
// roman_ags is the exception, and the reason this test exists: it ships
// OFL-1.1 over Latin Modern Roman, which is under the GUST e-foundry Licence
// (LPPL 1.3c). That relicensing is legitimate — LPPL 1.3c clause 10a allows a
// Derived Work under a different licence — but clause 10b requires the Derived
// Work to carry enough documentation for recipients to honour clause 6, whose
// operative condition (6d) is "information sufficient to obtain a complete,
// unmodified copy of the Work". Until 2026-08-22 that information existed only
// in the sidecar's SECOND paragraph, which extractAttribution never reaches, so
// the credit line named neither the base nor the URL.
//
// The invariant, stated generally so a future import of another cross-family
// derivative trips it too: if the licence text names a licence family the
// font does not itself ship under, the user-visible attribution must name the
// base work. Anything surfacing attribution alone stays self-sufficient.
test("a font deriving from another licence FAMILY names that base in its attribution", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  // Families a licence body can name, and how to spot each.
  const FAMILIES = [
    ["OFL-1.1", /SIL Open Font License|\bOFL\b/i],
    ["GPL-3.0", /GNU General Public License|\bGPL\b/i],
    ["LPPL", /LaTeX Project Public License|GUST e-foundry/i],
    ["Apache", /Apache License/i],
    ["Ubuntu", /Ubuntu Font Licence/i],
  ];
  for (const f of man.fonts) {
    const p = path.join(FONT_DIR, f.key + ".LICENSE.txt");
    if (!fs.existsSync(p)) continue;
    const text = fs.readFileSync(p, "utf8");
    // A base under CC0 / public domain carries no downstream conditions, so
    // it needs no credit-line provenance (cats, from a CC0 original).
    for (const [fam, re] of FAMILIES) {
      if (fam === f.licenseId || !re.test(text)) continue;
      // The body names a foreign family. Find what it says the base IS.
      // "from\w*" not "from": roman_ags's upstream text reads "a derivative
      // work fromm Latin Modern Roman". With a plain \bfrom\b this test
      // matched nothing and passed vacuously on the very font it exists for.
      const m = /deriv\w*\s+(?:work\s+)?from\w*\s+(?:the\s+)?([A-Za-z][^\n(,:]{2,50})/i.exec(text);
      if (!m) continue;
      const base = m[1].trim().replace(/\s*fonts?\s*$/i, "");
      if (!base) continue;
      assert.ok(
        new RegExp(base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(f.attribution || ""),
        `${f.key} ships ${f.licenseId} but derives from "${base}" under ${fam}; ` +
        `its attribution must name that base so the credit line stands alone ` +
        `(add an ATTRIBUTION_OVERRIDES entry in tools/font-license.mjs)`);
    }
  }
});
