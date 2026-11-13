# Launch starter pack (2026-11-10)

`PRODUCT.md` item 3. These are the 12 designs Kent approved on 2026-11-10 (the "Strict 12"), sourced under his rules in
[`starter-pack-sourcing-2026-11-10.md`](starter-pack-sourcing-2026-11-10.md): art must be CC0 or public
domain on its own source page, and no logo, brand mark, trademarked character or mascot is allowed.

Files are in `app/public/starter/`: the original SVG, the DST, and `manifest.json`. The manifest records
each design's page, author, licence as the page states it, check date, sha256 of the art and the DST, size,
stitches, colours and preflight grade. `test/starter-pack.test.js` checks the licence allowlist, every
sha256, and that every DST decodes with `src/dstimport.js` to the recorded counts.

## Method

- **Source.** All 12 come from Wikimedia Commons. Licences were read from each file page's own metadata
  on 2026-11-10. Where the page names an Openclipart original, that page was checked for the `pd_issue`
  tag; none of the seven checked here carries it. Kenney's packs are CC0, but they download only through a
  JavaScript donate gate, so none were taken.
- **Digitizing.** Commons' standard 1280 px PNG render of each SVG went through the live digitizer
  service (0.6.0 at `ac3d77fa`). The calls were `POST /digitize` with only `target_width_mm`, then
  `POST /export` as DST. Each width puts the design's long side at 75-93 mm for a 4x4 in hoop.
- **Checks.** Every export passed the service's read-back (`X-Export-Verified: true`). Each DST was
  re-read with pystitch, and those counts agree with `src/dstimport.js`.
- **Not sewn.** Gate 1 still applies: these are stitch-file checks, not sew-outs.

## The 12

| Design | Theme | Author | Licence (page) | Size mm | Stitches | Colours | Preflight |
|---|---|---|---|---|---|---|---|
| [Jack-o'-lantern](https://commons.wikimedia.org/wiki/File:Jack_o_lantern_Pinhead_icon.svg) | holidays | Quincy Morgan (Pinhead icons) | CC0 | 80.4 x 72.4 | 14,218 | 1 | A |
| [Heart](https://commons.wikimedia.org/wiki/File:Heart_left-highlight_jon_01.svg) | holidays | Jon Phillips (Openclipart 35965) | CC0 | 79.9 x 75.4 | 15,649 | 3 | A |
| [Shamrock](https://commons.wikimedia.org/wiki/File:Emblem-shamrock.svg) | holidays | Inductiveload | Public domain | 73.4 x 78.6 | 13,465 | 2 | A |
| [Bumblebee](https://commons.wikimedia.org/wiki/File:Bumblebee_white_eyes_clipart.svg) | animals | Mvolz | CC0 | 80.2 x 47.6 | 9,719 | 3 | A |
| [Bur oak leaf](https://commons.wikimedia.org/wiki/File:Bur_Oak_Leaf.svg) | florals and leaves | Jpness | CC0 | 55.1 x 90.6 | 12,357 | 3 | B |
| [Owl](https://commons.wikimedia.org/wiki/File:Owl_bored.svg) | animals | rones (Openclipart 166822) | CC0 | 80.5 x 61.2 | 14,941 | 5 | B |
| [American football](https://commons.wikimedia.org/wiki/File:American_football_icon.svg) | sports | gnokii (Openclipart 153043) | CC0 | 90.4 x 60.3 | 18,584 | 9 | B |
| [Baseball](https://commons.wikimedia.org/wiki/File:Baseball.svg) | sports | vedub4us (Openclipart 25258) | CC0 | 76.1 x 74.7 | 24,378 | 5 | B |
| [Christmas tree](https://commons.wikimedia.org/wiki/File:Christmas_tree_02.svg) | holidays | Aaron Spike / Anonymous (Openclipart 12713) | CC0 | 82.0 x 90.3 | 17,775 | 8 | C |
| [Turtle](https://commons.wikimedia.org/wiki/File:Turtle_clip_art.svg) | animals | badaman (Openclipart 229886) | CC0 | 92.5 x 61.8 | 17,398 | 10 | B |
| [Monarch butterflies](https://commons.wikimedia.org/wiki/File:Franzi_-_Monarch.svg) | animals | franzi (Openclipart 218815) | CC0 | 90.5 x 85.7 | 16,819 | 3 | B |
| [Lighthouse](https://commons.wikimedia.org/wiki/File:Lighthouse.svg) | nautical | matthewg42 | Public domain | 25.5 x 93.2 | 8,948 | 9 | B |

**Trademark check.** None of the 12 is a logo, brand mark or known character. The football helmet carries
stripes only, with no team mark. The owl, bumblebee and turtle are the uploaders' own cartoons. The
lighthouse is generic and names no landmark.

**Known weak spots** (rendered, not sewn). Causes and remedies are in
[`starter-pack-weak-spots-2026-11-12.md`](starter-pack-weak-spots-2026-11-12.md):
- The baseball's white shading sewed as grey rings. It was re-digitized on 2026-11-12 with `forced_class: "flat"`
  (Kent's ruling), so the row above is the new file: one white field, no grey.
- The turtle loses its shell shading. Its shell, legs and head merge into one colour on the automatic lane. Kent kept
  the shipped file.
- The monarch's white wing dots cost 86 trims. `borders_last: false` takes that to 67 at the pack's 90.0 mm target; a
  "drift" that held it was a width mistake ([correction](monarch-orange-drift-2026-11-12.md)), so it waits on Kent.
- The lighthouse is only 25 mm wide, so its windows are tiny.

## Dropped

Kent dropped three of the first recommendation:
- **Laurel wreath:** its CC0 vector was traced from a "Copyrighted free use" GIF, which is not CC0.
- **Wolf paw print:** it was traced from an iNaturalist photo whose licence could not be read.
- **Sunflower:** no author is named (a clker.com mirror credited to "OCAL"), and it resembles the MediaWiki logo.

On provenance:
- **Whale:** Commons credits only "openclipart.org".
- **Olive wreath:** Commons says it is "based off" the UN flag, whose emblem is protected.
- **Rose:** it came via Pixabay.

On how they sew (stitch render plus preflight):
- **Tulip:** the petal gradient sews as bands; F.
- **Compass rose:** thin rays are lost; F, with a THREAD_MATCH_POOR block.
- **Anchor:** the sketchy grey line art sews as a fill; D.
- **Basketball:** its shadow is sewn; D.
- **Rose:** 15 colours and 41,620 stitches.
- **Ship's wheel:** the gaps between the spokes are sewn.
- **Oval frame:** its centre is sewn solid, which defeats a monogram blank.
- **Pumpkin:** its shadow sews as a dark bar.
- **Soccer ball:** the white panels sew grey.
- **Snowflake:** see below.

Three files were screened out before digitizing because they were the wrong subject: a playing card, a
car steering wheel, and a landscape strip.

## Preflight false positives seen

- **LETTERING_TOO_SMALL and LETTERING_ILLEGIBLE** fired on 16 of the 27 candidates, though none contains
  text. They read small satin shapes (leaf veins, seams, ornaments) as lettering. Several C grades here
  come from them.
- **GROUND_SEWN (block)** fired on black icons on a transparent background (snowflake, ship's wheel). It
  calls the black shape "the same color as the artwork's own background". The likely cause is the black
  RGB behind fully transparent pixels. This is unverified. The ship's wheel did sew its spoke gaps; the
  snowflake render looked right.

Neither has been confirmed against a sew-out. Both are worth a look before preflight grades are shown on
the pack in the Studio (PR B).
