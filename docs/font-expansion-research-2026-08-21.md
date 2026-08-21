# Font library expansion — upstream sweep, 2026-08-21

**Question asked:** are there more free, commercially-sellable satin fonts we can
add to the library? Then: can we get to 150?

**Answer: 7 added (55 → 62). Upstream is now exhausted for satin fonts under
current policy — 0 remain addable. 150 is not reachable from Ink/Stitch; §8
gives the real ceiling (~101) and what each step would cost.**

**ShareAlike is permanently closed** (Kent, 2026-08-21 — §8). The single
remaining large lever is a fill / run-based lettering path: +35 fonts that are
already licensed and in hand.

Measured against upstream `inkstitch/embroidery-fonts` @ `8c660c4` (2026-08-06),
the source of record for the existing library. Reproduce with §6.

> **Revised after implementation.** The first pass of this doc reported 8
> additions and "9 CC-BY-4.0 eligible" fonts. Both were wrong, and both were
> caught by building the fonts rather than trusting the sweep: `cyrillic` has a
> geometry defect (§4) and 9 of those 10 "CC-BY-4.0" fonts are actually
> NonCommercial or NoDerivatives (§5). Numbers below are the corrected ones.

## 1. What the sweep covered

| | count |
|---|---|
| Fonts upstream | 142 |
| Shipping in EMB-Bot after this work | 62 |
| License-eligible (`OFL-1.1` / `CC-BY-4.0` / `CC0`) and not shipping | 41 |
| ...minus standing PULLs, holds and refusals | 35 |
| ...of which pass the satin QC gate | **0** |

Eligibility is `ALLOWED_LICENSES` **as the code defines it** — `OFL-1.1`,
`CC-BY-4.0`, `CC0`. Note `.claude/skills/add-font/SKILL.md` still lists
`CC-BY-SA-4.0`; that is **stale** and was not used. Excluded by license: 23
CC-BY-SA-4.0, 8 CC-BY-NC-4.0, 3 GPL-3.0, 2 CC-BY-SA-2.5, 1 CC-BY-ND-4.0, 1
no-license-file (`fold_inkstitch`), 1 unresolvable (`nick_ainley`).

## 2. Shipped: 7 fonts (55 → 62)

All `OFL-1.1`, all with hand-authored satin columns, all verified end to end —
QC gate, `.embf` round-trip, and a real `buildLetteringDesign` run producing
stitches.

| key | from | A–Z / a–z / 0–9 | satin cols | mm | stitches @40mm |
|---|---|---|---|---|---|
| `montecarlo` | MonteCarlo (Google Fonts) | 26/26/10 | 2674 | 35 | 1157 |
| `art_nouveau` | Apollo ASM, Peter Wiegel | 26/26/10 | 706 | 20 | 1153 |
| `magnolia_bicolor` ✱ | Magnolia Script | 26/26/10 | 726 | 30 | 1869 |
| `colorful` ✱ | Spicy Rice (Google Fonts) | 26/26/10 | 241 | 31 | 1365 |
| `kum_tsoan_tartan` ✱ | Namskout, gluk | 26/0/10 | 357 | 83 | 1276 |
| `apesplit` | Gilda Display (Google Fonts) | 26/0/0 | 478 | 120 | 4404 |
| `perspective_tricolore_KOR` ✱ | Merriweather (Google Fonts) | 26/0/10 | 265 | 36 | 900 |

### ✱ Multicolor caveat — 4 of the 7

`build-font.mjs` emits satin columns as `{railA, railB, rungs}` with **no color
field**. All four report `colorCount=1` from a real lettering run, confirming
it: they stitch single-thread and will not match their upstream previews.
`perspective_tricolore_KOR` is worst-hit — its 3D effect *is* the color
separation. Carrying color through the import is the fix; until then these four
are monochrome interpretations of multicolor designs.

## 3. Why the rest fail — they are not satin fonts

Not a parser defect: a control rebuild of five *already-shipping* fonts
(`alchemy`, `allegria55`, `venezia`, `cats`, `neon`) from the same clone passed.
The rejects carry **zero `inkstitch:satin_column` attributes**:

| technique | n | evidence |
|---|---|---|
| Cross-stitch | 18 | `inkstitch:cross_stitch_method` |
| Fill | 7 | `inkstitch:fill_method`, no satin |
| Bean / redwork | 7 | `inkstitch:bean_stitch` |
| Running stitch | 6 | `running_stitch_length_mm` only |
| No Latin glyphs | 1 | `honoka` |

**This is a latent asset, not waste.** ~38 already-licensed fonts unlock with no
new legal work the day a fill or run-based lettering path exists. Three
(`ondulamarif_XL/Medium/S`) are the bean-stitch family behind the known
`ondulamarif_XL` demotion — same root cause, now confirmed across all three.

## 4. `cyrillic` — held, and why it took building it to see

It passes the QC gate and stitches. But 6 of its 466 glyphs (`ñ ù ú û ü ű`) have
**detached accents**: plain `u` has bbox `y[687,758]`, while `ú` is `y[33,758]`
— the accent marooned ~650 units from the letter body, with x running to −44,
outside the glyph box.

The lettering path derives its line box from font-wide glyph extents, so those 6
inflate every string: `"Emb"` clamps to **19.8 mm against a 40 mm target**, and
stays there no matter the target, while all 7 shipped fonts reach 40 mm.

All 252 Cyrillic glyphs and all 62 basic-Latin glyphs are clean, so dropping the
6 salvages the font — but that silently breaks `ñ` for Spanish and Portuguese
text. **That is a product call, not a QC one — Kent's.**

`qc-font.mjs` now has a bbox-outlier check for this class (it produced stitches
and passed every existing check, so nothing caught it). Scoped to
single-character glyph names so deliberate non-letters — `art_nouveau`'s
`frame1`, `montecarlo`'s `C.alt6`, `.notdef` — do not trip it; threshold 4×
calibrated against the shipping library, whose worst single-char ratio is
`small_font`'s `&` at 3.11×.

## 5. `licenseId()` labelled NonCommercial fonts as sellable

**The most serious finding, and it goes straight at the paid-launch goal.**

`"CC-BY-NC-SA 4.0"` does not match the `CC-BY-SA` branch (the `NC` sits between
`BY` and `SA`), so it fell through to bare `CC-BY` and returned **`CC-BY-4.0` —
an `ALLOWED_LICENSES` id**. Every NonCommercial and NoDerivatives font upstream
was being reported as freely sellable:

- **8 fonts are CC-BY-NC-4.0**: `flowery_crosses`, `flowery_multicolor`,
  `handkerchief`, `ladies_present`, `magic_crosses`, `nautical`, `priscilla`,
  `very_crossy`
- **1 is CC-BY-ND-4.0**: `infinipicto`
- `cogs_KOR` is the library's **one genuine CC-BY-4.0**, correctly shipping

**No shipped font was ever affected** — all 9 fail QC as cross-stitch/fill
fonts, and all 62 shipping fonts keep their existing `licenseId` under the fix.
This was a landmine, not a breach. But the four open upstream PRs (§7) are
exactly these fonts, so the next sweep would have walked into it.

Fixed in `tools/font-license.mjs`, with `test/font-license.test.js` pinning it —
including a test that every shipped sidecar still resolves to its manifest id,
so a future widening of the policy set breaks a test rather than a launch.

## 6. Reproducing

```bash
git clone --filter=blob:none --no-checkout https://github.com/inkstitch/embroidery-fonts.git
# sparse-checkout src/*/{LICENSE,font.json,ltr.svg,ltr/*.svg}
node tools/build-font.mjs <clone>/src/<key> scratch_ink/_out/<key>.json
node tools/qc-font.mjs scratch_ink/_out/<key>.json
```

Control (must pass — proves the harness reads current upstream markup):
`alchemy`, `allegria55`, `venezia`, `cats`, `neon`.

**Rebuilding needs a full `scratch_ink/`.** Only 17 of the 62 shipped fonts have
a `src/fonts/<key>.json`; the other 45 live only as `.embf`. A build with a
partial `scratch_ink/` writes a 25-font manifest and orphans the rest. Regenerate
all 45 from the upstream clone before running `build-embf.mjs`. Drift was audited
on this rebuild: **53 of 55 existing `.embf` came back byte-identical**; the 2
that changed are upstream improvements, not regressions — `alchemy`'s embedded
`glyphCount` corrected 471 → 469 (it has 469), and `barstitch_textured`'s `Ä`/`Ë`
had degenerate zero-length runs (`[[57.5,35.25],[57.5,35.25]]`) replaced with
real geometry.

Two build defects were found and fixed doing this:

- `build-embf.mjs` did not trim the **embedded** font name, only the manifest
  entry, so any rebuild silently reverted `initials_medium` to
  `"Initials Medium "` — undoing the July audit's in-place fix. The audit
  worried about exactly this "fix that silently reverts" shape for `dejavufont`;
  here it had already happened.
- `apesplit` and `kum_tsoan_tartan` upstream LICENSE files are CRLF, but
  `.gitattributes` pins `*.LICENSE.txt` to LF. Embedding the CRLF text passes
  locally and fails `embf-guard`'s sidecar comparison on a fresh checkout.

## 7. Sources that are not sources

- **The four open upstream PRs.** `kalinux` (#72) passes QC with 874 satin
  columns and full coverage, but is **Ubuntu Font License 1.0** (from Ubuntu
  Mono) — not in the allowed set. `fornow` (#75), `rigart` (#76) and `therese`
  (#77) are **CC-BY-NC-SA** cross-stitch fonts — NonCommercial *and* zero satin
  columns. None addable.
- **The Ink/Stitch main repo.** Its `fonts/` is a git submodule pointing at
  `embroidery-fonts` — the same 142, no extras.
- **BX / PES / DST font sites** (AnnTheGran, Embrilliance, Five Star, Bunnycup).
  Pre-stitched binaries, not satin vector sources — importing one means tracing
  stitched output, the auto-trace path this project already rejected
  (COOKBOOK.md). Most are personal-use-only, fatal for a paid product.
- **Independent satin-SVG font projects.** Searched; none found. The
  `inkstitch:satin_column` rails+rungs format is effectively Ink/Stitch-only.

## 8. Getting to 150 — the honest math

**Not reachable from Ink/Stitch.** Every lever, stacked:

| lever | fonts | what it costs |
|---|---:|---|
| **Shipping today** | **62** | — |
| ~~Clear the ShareAlike question~~ | ~~+25~~ | **ruled out 2026-08-21 — see below** |
| Build a fill / run-based lettering path | +35 | engineering; no new licensing |
| `cyrillic` minus its 6 broken glyphs | +1 | product call — loses `ñ` (§4) |
| `inkstitch_masego` | +1 | get real OFL text from the designer |
| Admit LPPL/GUST (`roman_ags_bicolor`) | +1 | policy call — see §9 |
| Admit Ubuntu Font License (`kalinux`) | +1 | policy call |
| **Ceiling** | **~101** | dominated by the new engine path |

GPL-3.0 (3 fonts) stays hard-excluded. NonCommercial (8) and NoDerivatives (1)
can never ship in a paid product.

### ShareAlike is closed — Kent's decision, 2026-08-21

**Do not re-propose the ShareAlike route.** Asked directly, Kent's call was that
ShareAlike "seems sketchy, you should avoid that." That makes the 2026-08-04
removal permanent policy rather than a hold pending counsel, and it retires the
restore path `docs/lawyer-brief-cc-by-sa-2026-08-04.md` describes.

The reasoning holds up independently: the unresolved question was never whether
CC-BY-SA is a free license — it is — but whether ShareAlike **propagates through
the compiled `.embf` onto the stitch files customers generate**. If it does,
every paying customer's design inherits a copyleft obligation they never agreed
to. That is an unbounded liability attached to the product's core output, and
25 fonts is a cheap price to make it go away. A legal opinion could only ever
have said "probably fine."

Practical effect: 23 CC-BY-SA-4.0 fonts plus the 2 CC-BY-SA-2.5 Geneva fonts are
permanently out, and `CC-BY-SA-*` stays absent from `ALLOWED_LICENSES`. The
`add-font` skill still lists `CC-BY-SA-4.0` as allowed — that line is stale
twice over now and should be corrected the next time that file is touched.

### So how do we actually grow the library

**150 needs net-new digitizing, not more searching.** Three routes, ranked:

1. **Build the fill / run-based lettering path — the only large lever left
   (+35, 62 → 97).** Every one of those fonts is already licensed and already
   in hand; nothing is blocked on a third party. This is now the single
   highest-leverage item by a wide margin, and it needs no lawyer.
2. **Wait.** Upstream added ~16 fonts in v3.1 and ~21 in v3.2.1 — roughly
   20/release, free, a few years to matter. Worth a periodic re-sweep (§6),
   which is cheap now that the tooling exists.
3. **Commission or hand-digitize.** Hand-authoring satin columns over an OFL
   outline font is how every font here was made. It is the only route that
   reaches 150 on a schedule we control, and it is a labor cost, not a
   licensing one — auto-tracing remains rejected.

## 9. Still open: `roman_ags` ships mislabeled

Unchanged from the first pass and **not fixed here**. `roman_ags` is in the
manifest as `OFL-1.1`, but its sidecar shows the base font is Latin Modern Roman
under the **GUST e-foundry License / LPPL 1.3c**, via fontsquirrel. The label
comes from the adapter's header line, which `licenseId()` matches before
reaching the real license block — the same detector gap that got `dejavufont`
pulled (`docs/font-license-audit-2026-07-31.md` §7).

Note the §5 fix does **not** close this one: §5 fixes CC modifiers, while this
is a non-CC license body sitting under a CC/OFL header claim. GUST/LPPL is free
and commercially redistributable, so this is much milder than the NC hole — the
defect is that the manifest asserts a license the source does not support.
Options remain the audit's: teach `licenseId()` to prefer a recognized license
*body* over a bare adapter claim, or decide LPPL/GUST joins the allowed set.
**Kent's call.**
