# Font library expansion — upstream sweep, 2026-08-21

**Question asked:** are there more free, commercially-sellable satin fonts we can
add to the library?

**Answer: 8 to add, 1 to verify, 1 to refuse — and the sweep found a live
mislabel in a font that already ships (`roman_ags`, §4).**

Measured against upstream `inkstitch/embroidery-fonts` @ `8c660c4` (2026-08-06),
the source of record for the existing library. Reproduce with the commands in §6.

## 1. What the sweep covered

| | count |
|---|---|
| Fonts upstream | 142 |
| Already shipping in EMB-Bot | 55 |
| Not shipping | 87 |
| ...license-eligible (`OFL-1.1` / `CC-BY-4.0` / `CC0`) | 57 |
| ...minus standing PULLs (`milli_marif_bold`, `tt_directors`, `tt_masters`) | 54 |
| ...built + QC'd through `tools/build-font.mjs` + `tools/qc-font.mjs` | 49 |
| **...passed QC** | **10** |

License eligibility is `ALLOWED_LICENSES` **as the code defines it** —
`OFL-1.1`, `CC-BY-4.0`, `CC0`. Note `.claude/skills/add-font/SKILL.md` still
lists `CC-BY-SA-4.0` as allowed; that is **stale** and was not used here. The
2026-08-04 ShareAlike pull removed it from `build-embf.mjs`, which excluded 23
otherwise-buildable upstream fonts from this sweep. Also excluded: 3 GPL-3.0, 2
CC-BY-SA-2.5, 1 no-license-file (`fold_inkstitch`), 1 unresolvable
(`nick_ainley`, "see license file").

## 2. Why 39 of 49 failed QC — they are not satin fonts

Not a parser defect. A control rebuild of five *already-shipping* fonts
(`alchemy`, `allegria55`, `venezia`, `cats`, `neon`) from the same clone passed,
so the harness reads current upstream markup correctly. The 39 rejects carry
**zero `inkstitch:satin_column` attributes**; they are authored in techniques the
satin lettering path cannot stitch:

| technique | n | evidence |
|---|---|---|
| Cross-stitch | 18 | `inkstitch:cross_stitch_method` |
| Fill | 7 | `inkstitch:fill_method`, no satin |
| Bean / redwork | 7 | `inkstitch:bean_stitch` |
| Running stitch | 6 | `running_stitch_length_mm` only |
| No Latin glyphs | 1 | `honoka` |

These are a **latent asset, not waste**: if a fill or run-based lettering path is
ever built, ~38 already-licensed fonts unlock without new legal work. Three
(`ondulamarif_XL/Medium/S`) are the bean-stitch family behind the known
`ondulamarif_XL` demotion — the same root cause, now confirmed across all three.

## 3. The 10 that passed

All `OFL-1.1`, all with genuine hand-authored satin columns.

| key | from | glyphs (A–Z / a–z / 0–9) | satin cols | mm | note |
|---|---|---|---|---|---|
| `montecarlo` | MonteCarlo (Google Fonts) | 26/26/10 | 2674 | 35 | 800 glyphs — widest coverage found |
| `cyrillic` | Roboto (Google Fonts) | 26/26/10 | 1444 | 25 | 466 glyphs, Latin **and** Cyrillic |
| `art_nouveau` | Apollo ASM, Peter Wiegel | 26/26/10 | 706 | 20 | clean provenance, own site |
| `magnolia_bicolor` | Magnolia Script | 26/26/10 | 726 | 30 | ✱ multicolor; family already ships |
| `apesplit` | Gilda Display (Google Fonts) | 26/0/0 | 478 | 120 | caps-only, very large |
| `colorful` | Spicy Rice (Google Fonts) | 26/26/10 | 241 | 31 | ✱ multicolor; RFN "Spicy Rice" |
| `kum_tsoan_tartan` | Namskout, gluk | 26/0/10 | 357 | 83 | ✱ multicolor; RFN "Namskout" |
| `perspective_tricolore_KOR` | Merriweather (Google Fonts) | 26/0/10 | 265 | 36 | ✱ multicolor; RFN "Merriweather" |
| `inkstitch_masego` | Masego, madebydebo | 26/26/10 | 277 | 14 | ⚠ see §5 — do not add yet |
| `roman_ags_bicolor` | Latin Modern Roman | 26/26/10 | 628 | 25 | ✘ refuse — see §4 |

### ✱ Multicolor caveat — affects 4 of the 8

`tools/build-font.mjs` emits satin columns as `{railA, railB, rungs}` only. There
is **no color field**, so a bicolor/tricolor/tartan font imports as
single-thread. All four still stitch valid geometry and pass QC, but they will
not match their upstream previews. `perspective_tricolore_KOR` is the one most
degraded by this — its 3D effect *is* the color separation. Recommend tiering
these four separately from the 4 monochrome ones, or holding them until the
import carries color.

## 4. Live finding: `roman_ags` ships mislabeled

`roman_ags` is in the shipping manifest today as `licenseId: "OFL-1.1"`. Its own
sidecar (`src/fonts/roman_ags.LICENSE.txt`) says otherwise: the underlying font
is **Latin Modern Roman under the GUST e-foundry License / LPPL 1.3c**, sourced
via fontsquirrel. The `OFL-1.1` label comes from the *adapter's* header line —
`licenseId()` matches it before ever reaching the real license block below.

**This is the exact detector gap the audit documented for `dejavufont`**
(`docs/font-license-audit-2026-07-31.md` §7), which was pulled for it. That gap
was left unfixed, and `roman_ags` has been sitting on it. `roman_ags_bicolor`
(§3) is the same font family and is refused here for the same reason.

Fairness note: GUST/LPPL is a free license permitting commercial
redistribution, so this is materially *less* risky than the ShareAlike question
— and GUST's rename request is already satisfied ("Roman AGS"). The defect is
that the manifest asserts a license the source does not support, and
`ALLOWED_LICENSES` does not include GUST/LPPL. **Kent's call**, with the same
options the audit gave for `dejavufont`: fix `licenseId()` to prefer a
recognized license block over a bare adapter claim, or decide whether
LPPL/GUST joins the allowed set.

## 5. `inkstitch_masego` — unverified OFL claim

The LICENSE asserts "licensed under the Open Font License" with only a Gumroad
link as its source. Independent search found Masego (Adebowale Adegoke) on
freebie aggregators — Behance, Pixel Surplus, EpicPxls — described as "free for
personal and commercial use," but **no primary-source OFL text anywhere**.

That is the `tt_directors` / `tt_masters` pattern verbatim: an OFL claim
traceable only to aggregator listings. Under the standing policy this is not
eligible for a *new* font. Held out of the recommendation. Resolvable by
obtaining the actual license from the designer.

## 6. Reproducing

```bash
git clone --filter=blob:none --no-checkout https://github.com/inkstitch/embroidery-fonts.git
# sparse-checkout src/*/{LICENSE,font.json,ltr.svg,ltr/*.svg}
node tools/build-font.mjs <clone>/src/<key> /tmp/out/<key>.json
node tools/qc-font.mjs /tmp/out/<key>.json
```

Control (must pass, proves the harness reads current upstream markup):
`alchemy`, `allegria55`, `venezia`, `cats`, `neon`.

## 7. Not a source: BX / PES / DST font sites

Checked, and deliberately not pursued. AnnTheGran, Embrilliance, Five Star
Fonts, Bunnycup et al. distribute *pre-stitched binaries*, not satin-column
vector sources. Importing one means tracing stitched output — the auto-traced
outline path this project already rejected as lower quality than hand-authored
satin (COOKBOOK.md). Most are also personal-use-only, which is fatal for a paid
product. The Ink/Stitch ecosystem remains the only viable source of
hand-authored satin fonts.

## 8. Recommendation

**Add 4 now** (monochrome, clean provenance, no caveats):
`montecarlo`, `cyrillic`, `art_nouveau`, `apesplit`.

**Add 4 with the color caveat understood** (§3):
`magnolia_bicolor`, `colorful`, `kum_tsoan_tartan`, `perspective_tricolore_KOR`.

**Hold:** `inkstitch_masego` (§5). **Refuse:** `roman_ags_bicolor` (§4).

That is 55 → 63 fonts, or 59 if only the monochrome four go in.

Per `.claude/skills/add-font/SKILL.md` step 4, tiering is Kent's decision and
was **not** taken here — nothing was written to `scratch_ink/_tiers.json` and no
`.embf` was built. On approval: add `{"pack": "<key>", "tier": "verified"}` per
font, save each full `LICENSE` as a `src/fonts/<key>.LICENSE.txt` sidecar from
the start (audit item 5), keep the Reserved Font Name notices for `colorful`,
`kum_tsoan_tartan`, and `perspective_tricolore_KOR`, then
`build-embf.mjs` → `build-previews.mjs` → `node --test`, and remember the
engine-file list lives in **three** places (`copy-engine.mjs`, `emb.js`,
`app/index.html`) — a green `node --test` alone will not prove the fonts load in
the Studio.
