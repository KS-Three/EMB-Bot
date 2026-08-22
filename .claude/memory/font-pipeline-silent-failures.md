---
name: font-pipeline-silent-failures
description: The font pipeline's failure mode is silent — numbers read healthy while glyphs are garbage; the 2026-08-21/22 sweep found six such defects and the tier gate was never even running
metadata:
  type: reference
---

EMB-Bot's font library went 55 → 85 sellable fonts across 2026-08-21/22. The
fonts matter less than the failure MODE that sweep exposed, because it recurs:
**every defect found reported healthy numbers.** Cell counts, QC verdicts,
lattice fit, stitch counts and a green suite all said fine while glyphs were
wrong. Rendering the output and looking at it is what found every one.

## What was actually broken

- **`build-font` dropped SVG transforms** for every single-`ltr.svg` font (most
  of the library). Harmless for a glyph with baked coordinates; catastrophic for
  one placing repeated geometry BY transform. `mimosa_large`'s "D" is one dot
  with 38 transforms: all 38 stacked on a point and it sewed **6,193 stitches
  into 40.0 × 0.0 mm** against a healthy glyph's 996. It shipped that way.
  The tell: the glyph kept its FULL column and rail-point count while landing on
  one spot — geometry present, placement wrong.
- **`parsePath` truncated every path at its first scientific-notation number**
  (unanchored `/[a-zA-Z]/`; `5.2e-4` contains an `e`). 119 of 132 upstream fonts
  contain such numbers. It hid because satin rails carry large coordinates where
  truncation lands late. There was a SECOND copy of the same parser in
  `tools/parse-inkstitch.mjs`; `src/svgpath.js` uses an explicit command set and
  is safe.
- **The tier gate was never run.** `qc-font.mjs` calls itself "the tier gate, in
  the repo, with tests", and `build-embf.mjs` never called it. Enforcement was
  one test over the 17 static `src/fonts/*.json`; the other 68 fonts arrive via
  `scratch_ink/_out` and were QC'd by nothing.
- **`roman_ags`** ships OFL-1.1 over an LPPL/GUST base. Legitimate (LPPL 1.3c
  clause 10a permits relicensing) but the credit line named only the adapter,
  so clause 6d rested on a reader opening the linked file.

## Latin assumptions — a whole class, all silent

Adding ONE Hebrew font flushed out three, none of which failed a test:

1. `build-previews`' sample fallback filtered to `[A-Za-z0-9]`, so a Hebrew font
   fell through to `"?"` — which it also lacks — and rendered zero stitches.
2. `sewsAnything()` looked only at A–Z, so it answered "no" for a font with no
   Latin. Both Hebrew faces were dropped from the PERSONAL build while the
   SELLABLE build shipped them: two libraries disagreeing about one font.
3. The lettering path skipped unrenderable characters silently — Hebrew font +
   Latin text = a valid-looking 0-stitch design with no explanation anywhere.

**A helper filtering on `[A-Za-z0-9]` is the smell.** The right test is `\p{L}`,
and the precision matters: Hebrew's `׳`/`״` are PUNCTUATION (they were being
measured as stunted letters), and `circular_3letters_monogram` / `invercelia`
name their glyphs `A.medi` / `A.init` — contextual variants the lettering path
can never address, leaving punctuation to vouch for fonts whose real letters are
unreachable.

## Rules that came out of it

- **Any importer fix invalidates the upstream census.** Every earlier judgement
  about which fonts were viable was made on collapsed geometry. Re-running all
  142 after the transform fix yielded five more fonts, including `cyrillic`
  (466 glyphs, 252 Cyrillic) whose "detached accent" defect WAS the transform bug.
- **A font can be excluded by a filename.** 141 of 142 name the licence file
  `LICENSE`; `fold_inkstitch` uses `license`. Uppercase-only lookup resolves on
  Kent's case-insensitive Windows box and reads NOTHING on Linux, so the font
  imported with an empty licence and fell outside `ALLOWED_LICENSES`. It is
  OFL-1.1.
- **QC cannot see redundant overlapping satin.** `roman_ags_bicolor` QC-passes
  and renders correctly, but carries 79 satin columns for A–H against the mono
  cut's 57 for visually identical output. A prior decision had recorded this and
  `embf-guard` pins it — the TEST caught the re-addition, not QC.
- **Arabic is impossible with the three upstream Arabic fonts**, engine or not:
  they carry only base-block letters and zero presentation forms, so the joined
  glyphs a shaper would select do not exist. Not a gap waiting on engine work.
- **Compare against upstream's own `preview.png` before judging a letterform.**
  `jaquarda_bastarda_9` looked broken (13 rings, 34 sparse cells for an H) and is
  simply an ornate blackletter drawn in single-cell cross chains.

## Guards written this way

Five tests added in that sweep would have passed VACUOUSLY on first draft. The
`roman_ags` one matched nothing because upstream's text reads "a derivative work
**fromm** Latin Modern Roman". Break every new guard on purpose and watch it go
red before trusting it — and check the level below too: a test that iterates a
list asserts nothing when the list is empty.

See [[windows-goldens-fail-locally]] for the golden-divergence correction made
in the same session.
