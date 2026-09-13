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
  // An empty manifest would walk this loop zero times and report green. The
  // library is 85 fonts; a handful means something upstream of this test broke.
  assert.ok(man.fonts.length > 50, `only ${man.fonts.length} fonts in the manifest`);
  for (const f of man.fonts) {
    const sidecar = fs.readFileSync(path.join(FONT_DIR, f.key + ".LICENSE.txt"), "utf8");
    assert.strictEqual(await id(sidecar), f.licenseId, "licenseId drift for " + f.key);
    assert.ok(ALLOWED.has(f.licenseId), "shipped font outside license policy: " + f.key);
  }
});

// A font's own licence is not the whole story: it may DERIVE from a font under
// a different licence family, whose conditions then ride along. 78 of the 85
// shipped fonts declare a derivative base, but for all but one that base is
// itself OFL, so shipping the OFL text discharges everything.
// *(re-measured 2026-08-22; it read "71 of the 80" while the library was 85)*
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
  assert.ok(man.fonts.length > 50, `only ${man.fonts.length} fonts in the manifest`);
  // Every path below is a `continue`, so this test can reach zero assertions
  // and still report green — and it HAS: with a plain \bfrom\b it matched
  // nothing and passed on the very font it exists for. Recording who was
  // actually checked, and demanding the known case be among them, is what
  // makes a future regex tweak fail here instead of going quiet.
  const asserted = [];
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
      asserted.push(f.key);
      assert.ok(
        new RegExp(base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(f.attribution || ""),
        `${f.key} ships ${f.licenseId} but derives from "${base}" under ${fam}; ` +
        `its attribution must name that base so the credit line stands alone ` +
        `(add an ATTRIBUTION_OVERRIDES entry in tools/font-license.mjs)`);
    }
  }
  // Measured 2026-08-22: exactly one font reaches the assert — roman_ags,
  // OFL-1.1 over Latin Modern Roman under LPPL. If it stops being checked,
  // either the font was pulled (update this) or the detection silently broke
  // (fix that); either way it must not pass quietly.
  assert.ok(asserted.includes("roman_ags"),
    `the cross-family check asserted on [${asserted.join(", ") || "nothing"}], and ` +
    `roman_ags is the case it exists for — it is not being checked any more`);
});

// OFL-1.1 clause 3 — Reserved Font Names. The clause reads: "No Modified
// Version of the Font Software may use the Reserved Font Name(s) unless
// explicit written permission is granted by the corresponding Copyright
// Holder. This restriction only applies to the primary font name as presented
// to the users." Every font here IS a Modified Version by the licence's own
// definition — "changing formats" is named in it, and .embf is a format
// change over the adapter's SVG — so the manifest `name`, which is the string
// the font browser shows, is exactly the "primary font name as presented to
// the users" the clause governs.
//
// This matters more than most licence checks because it is the one OFL
// condition that survives commercial bundling. OFL lets you sell the font
// inside a larger product; it does not let you keep the reserved name while
// doing it. PRODUCT.md calls font-licence compliance "a hard gate before the
// first dollar".
//
// Measured 2026-09-12, on this commit and against the live upstream:
//   - 82 of the 85 shipped fonts carry OFL sidecars. 80 contain the phrase
//     "Reserved Font Name" but only 46 DECLARE one — the other 34 are matching
//     OFL's own DEFINITIONS boilerplate, which uses the phrase to define it.
//     Counting the phrase instead of the declaration is a 46-vs-80 error, and
//     the assertion below pins the right one.
//   - Of those 46, ONE ships a display name that uses its own reserved name:
//     fold_inkstitch, "Fold Ink/Stitch" over Reserved Font Name "Fold".
//   - The other 45 are correctly renamed derivatives, which is the compliant
//     pattern this clause is designed to produce — Lobster -> Stebor, Abril ->
//     Mai en Fleur, Espresso Dolce -> Caffeine, Limelight -> Roaring Twenties.
//   - It is NOT an EMB-Bot packaging error. The same scan over upstream
//     inkstitch/embroidery-fonts (clone at c7e3a05) finds 1 hit in 102 OFL
//     fonts — the same font. Our sidecar is byte-identical to upstream's
//     src/fold_inkstitch/license but for a trailing newline, and upstream's
//     own font.json carries "name": "Fold Ink/Stitch", "original_font":
//     "Fold". We inherited the name; we did not coin it.
//   - No permission is on record anywhere. The only files naming Kilfiger in
//     the upstream repo are fold_inkstitch's own three, i.e. the attribution
//     itself. And upstream demonstrably DOES record permission when it has
//     it: bluenesia_satin's LICENSE cites the PR carrying the copy, and
//     emilio_20's reads "used and distributed with permission from the
//     author". Fold's says nothing of the kind.
//
// KNOWN_UNRESOLVED is a record of a live exposure, NOT a grant. An entry here
// says "we found this, we measured it, and the call is pending" — it does not
// say the use is licensed. Resolving it is deleting its line (and renaming the
// font). Growing it requires the same deliberate act, which is the point.
const RESERVED_NAME_KNOWN_UNRESOLVED = new Map([
  ["fold_inkstitch", "ships as \"Fold Ink/Stitch\" over Reserved Font Name \"Fold\" " +
    "(James Kilfiger). Inherited verbatim from upstream; no permission on record " +
    "there or here. Awaiting Kent's rename decision — found 2026-09-12."],
]);

test("no shipped font's display name uses its own OFL Reserved Font Name", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  assert.ok(man.fonts.length > 50, `only ${man.fonts.length} fonts in the manifest`);

  // Upstream writes the declaration five ways across the 80 sidecars that
  // carry one: bare ("...Name Fold."), double-quoted, single-quoted, curly
  // -quoted, HTML-escaped (&quot;), and plural with "and" ("Names Namskout
  // and NamskoutIn"). A parser that handles only the quoted form misses
  // fold_inkstitch, which is the one that matters — it is the bare form.
  const decode = (s) => s.replace(/&quot;/g, '"').replace(/&amp;/g, "&");
  const reservedNames = (text) => {
    const out = new Set();
    const re = /with\s+Reserved\s+Font\s+Names?\s+([^\n]*)/gi;
    let m;
    while ((m = re.exec(decode(text)))) {
      // Cut at whatever ends the name list: a following clause, a sentence
      // break, or a second "with Reserved" on the same line (neon does this).
      const tail = m[1].split(/,\s*licensed|\.\s|\swith\s+Reserved/i)[0];
      const quoted = [...tail.matchAll(/["'“‘]([^"'”’]+)["'”’]/g)].map((q) => q[1]);
      if (quoted.length) { quoted.forEach((q) => out.add(q.trim())); continue; }
      for (const part of tail.split(/\s+and\s+/i)) {
        const v = part.trim().replace(/[.,]+$/, "");
        if (v.length > 1) out.add(v);
      }
    }
    return [...out];
  };
  // Letter boundaries, not \b: "Fold Ink/Stitch" must hit on "Fold", while
  // "Glacial Tiny" must NOT hit on the reserved "glacial-indifference", and
  // "Marifenda" must not hit on "Merienda".
  const usesName = (displayName, reserved) =>
    new RegExp(`(^|[^\\p{L}])${reserved.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^\\p{L}]|$)`, "iu")
      .test(displayName);

  const hits = [];
  let scanned = 0;
  let declaring = 0;
  for (const f of man.fonts) {
    const p = path.join(FONT_DIR, f.key + ".LICENSE.txt");
    if (!fs.existsSync(p)) continue;
    const text = fs.readFileSync(p, "utf8");
    if (!/SIL Open Font License|\bOFL\b/i.test(text)) continue;
    scanned++;
    const names = reservedNames(text);
    if (names.length) declaring++;
    for (const rn of names) {
      if (usesName(f.name, rn)) hits.push({ key: f.key, name: f.name, reserved: rn });
    }
  }

  // Vacuous-pass guard, the roman_ags lesson one test up: every branch above
  // is a `continue`, so a broken regex reports green on an empty sweep. Pin
  // the population this was measured on.
  assert.ok(scanned > 50, `only ${scanned} OFL sidecars scanned — the sweep broke, it did not come back clean`);
  assert.ok(declaring > 30, `only ${declaring} sidecars DECLARED a Reserved Font Name (measured 2026-09-12: 46 of the 80 that merely contain the phrase) — the parser broke`);

  const unexpected = hits.filter((h) => !RESERVED_NAME_KNOWN_UNRESOLVED.has(h.key));
  assert.deepStrictEqual(unexpected, [],
    "a shipped font's display name uses a Reserved Font Name from its own licence, " +
    "which OFL-1.1 clause 3 forbids without written permission from the copyright " +
    "holder: " + unexpected.map((h) => `${h.key} ships as "${h.name}" over reserved "${h.reserved}"`).join("; ") +
    ". Rename the font in src/fonts/manifest.json (and rebuild, so the name embedded " +
    "in the .embf moves with it), or add a KNOWN_UNRESOLVED entry citing where the " +
    "permission is filed.");

  // The same anti-quiet rule the cross-family test uses: an entry that stops
  // being DETECTED is either a fixed font (delete the line) or a broken
  // detector (fix it). It must not pass silently either way.
  for (const key of RESERVED_NAME_KNOWN_UNRESOLVED.keys()) {
    assert.ok(hits.some((h) => h.key === key),
      `${key} is recorded as an unresolved Reserved Font Name case but the check no ` +
      `longer detects it — if it was renamed, delete its KNOWN_UNRESOLVED entry; if ` +
      `the parser regressed, fix that. Do not leave this passing quietly.`);
  }
});
