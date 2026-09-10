# Enclosed letter bodies decided by the garment colour — item 9

**Status: IN PLAN 2026-09-10, Kent's pick after #441. One flag,
`cfg.enclosed_by_garment`, DEFAULT OFF and byte-identical off, plus a
`garment_rgb` the Studio already knows and does not send. No new constant:
the threshold is `preflight.DELTA_E_VISIBLE` (5.0).**

## 0. What already governs this — read before changing the plan

- **The 2026-08-15 verdict** (`docs/enclosed-background-verdict-2026-08-15.md`):
  sewing every enclosed region is worth +8.0 scorecard points on the one
  design it touches and **the default must NOT flip** — the win is narrow
  (Becker alone, 41% of its area; two other designs under 5%), the colour
  is indefensible on alpha artwork (the flattened pixels under the
  transparency carry the INK's colour, so Becker's bodies would sew as
  solid black letters where the pro sewed Gray inside a Black keyline), and
  the regression is broad (goldens on `logo_alpha` 11% and `logo_whitebg`
  11%). Item 9 is not that flip: it is a rule that sews an enclosed region
  only when the garment would otherwise show through in a colour the
  artwork did not ask for.
- **Stage 1 already knows which holes have a colour.** `Prep.bg_from_alpha`
  says whether the background came from the alpha channel (then the enclosed
  pixels are TRANSPARENT and their RGB is whatever the exporter flattened
  there) or from a border-colour flood (then an enclosed hole really is that
  colour — `logo_whitebg`'s White hole). `tag_enclosed_background` marks the
  alpha kind `enclosed_colour_unknown`, the Studio shows it (contract v1.7),
  and deliberately does not invent a thread for it. What stage 1 does NOT
  keep is the flood's `bg_color` — a local in `prep()` — so the rule has to
  carry it onto `Prep`.
- **The stitched seam is one expression** (`pipeline.finish_generation`,
  after `apply_shape_edits`): a review `shape_overrides[sid]["stitched"]`
  wins, else `not enclosed_background`. The rule belongs in that expression
  and nowhere else (its own comment says why: the default half depends on a
  fact re-tagged every generation).
- **The Studio has the garment colour and does not send it.**
  `project.fabricRgb` (GarmentStep: eight swatches — White, Natural (the
  default, 235/232/223), Sand, Red, Royal, Navy, Forest, Black — or a custom
  pick) drives the preview's dark/light rendering only. `digitizer.js`
  sends `garment_id` (the fabric preset: pull, density) and nothing about
  colour. The service admits every `PipelineConfig` field but two
  (`_CONFIG_FIELDS`), so a new field needs no service change.
- **The threshold exists.** `preflight.DELTA_E_VISIBLE = 5.0` is the
  number preflight already uses for "a thread the eye can tell from the
  artwork"; the review names it, and this plan invents none.
- **Gate 1 does not apply** (no physical constant); **gate 4** applies to
  any quality number quoted (the scorecard is not the yardstick here — the
  verdict showed it rewarding the wrong thing; the yardstick is the render
  on the garment and the census below).

## 1. The gap

An enclosed region — the inside of a B, the counter of an O, the field a
frame surrounds — is unstitched by a global default, whatever the garment.
On a white polo that is right: the white body IS the garment. On a black
cap the same design sews a black outline around black cloth and the
letters vanish, while the pro fills the bodies. The Studio knows the
garment; the pipeline does not.

## 2. The design

- **`cfg.garment_rgb: tuple[int, int, int] | None = None`** — the fabric
  colour, sent by the Studio from `project.fabricRgb`. None = today.
- **`cfg.enclosed_by_garment: bool = False`** — the rule, DEFAULT OFF and
  byte-identical off. ON, in the stitched seam: an enclosed region whose
  colour is KNOWN (`Prep.bg_from_alpha` False, the flood's colour carried
  onto `Prep.bg_rgb`) is stitched when `ΔE00(bg_rgb, garment_rgb) >
  cfg.enclosed_by_garment_de00` — **10.0, `DELTA_E_CLEARLY_DIFFERENT`,
  pinned equal by test** (this section first said `DELTA_E_VISIBLE`, 5;
  §4's census moved it: at 5 the Studio's default Natural garment sews a
  white hole white at 6.4, at 10 it does not — §5.1 puts the number to
  Kent) — in the thread it already carries (stage 2 quantized it from the
  background colour, so the region's own thread is the right one;
  `revalidate_threads` keeps skipping enclosed regions). One verdict per
  design (`stage4_vectorize.garment_sews_enclosed`), because every flood
  hole is the same colour. A review override still wins either way. An
  alpha hole (`enclosed_colour_unknown`) is left exactly as it is: there
  is no colour to compare, and the 08-15 verdict's §5.2 stands until Kent
  chooses a fill colour for that case — a separate decision the census
  below sizes.
- **The colour cap reads the same verdict.** `enforce_color_cap` (ON since
  2026-09-10) ranks threads by SEWN area and lets a thread carried only by
  holes buy no slot — right while holes never sew, wrong the moment they
  do (a navy polo's white letter bodies would be merged into the nearest
  kept cone and sew cream). So the cap takes `count_enclosed=` from the
  same helper: a hole that will sew is sewn area and its cone competes.
  Alpha holes never count. False is the cap's shipped ranking byte for
  byte.
- **A warning says what happened**: the existing `BACKGROUND_ENCLOSED`
  text gains the garment reading ("N enclosed shapes sew because the
  garment is Navy; on a white garment they would not").
- **The Studio**: `digitizer.js` sends `garment_rgb` from the project (one
  line, beside `garment_id`); the flag is the engine's default, not a
  control — flipping it is Kent's after the renders.

## 3. Instrument first — `tools/enclosed_census.py`

Per fixture (the 26 scorecard fixtures at 80 mm, plus Becker at its
commissioned sizes): the enclosed regions and their area share, the colour
source (alpha / flood), the flood's background colour, and the ΔE00 from
that colour to each of the eight swatches — hence, per garment, which
enclosed shapes the rule would sew and in which thread. Then renders: the
same design on White and on Black, OFF beside ON, on a fabric-coloured
ground, for Becker, `logo_whitebg`, Golden Tee and gaulke (whose black
frame makes stage 1 call its lettering enclosed — the case where the rule
is a fix, not a look).

## 4. The census — measured 2026-09-10 (`tools/enclosed_census.py`, 26 fixtures at 80 mm)

Ten of 26 fixtures carry enclosed regions. **Six have a colour** (stage 1's
border flood) and **four are alpha** (colour unknown — the 2026-08-15
verdict's case, left alone by the rule):

| fixture | enclosed | area | share | source | background | hole sews on… (ΔE00 > 5) | (> 10) |
|---|---:|---:|---:|---|---|---|---|
| `logo_gaulke_roofing` | 46 | 438.5 mm² | 16.4% | flood | **black** (0,0,0), threads Black / Charcoal | every garment but Black | the same |
| `logo_golden_tee` | 4 | 642.8 mm² | 42.6% | flood | white, thread White | every garment but White | every garment but White and Natural |
| `logo_whitebg` | 1 | 159.6 mm² | 11.1% | flood | white | every garment but White (Natural at 6.4) | every garment but White and Natural |
| `screenshot_phone_ui_golke` | 67 | 85.8 mm² | 8.3% | flood | near-white (251) | as whitebg | as whitebg |
| `logo_script_tires` | 2 | 34.8 mm² | 4.5% | flood | near-white (252) | as whitebg | as whitebg |
| `summit_badge` | 7 | 5.2 mm² | 0.1% | flood | dark (57,53,49), Charcoal | every garment but Black | the same |
| `becker_marine_logo` | 7 | 919 mm² (1,328 at 95.7 mm) | **40.9%** | **alpha** | — | never (colour unknown) | never |
| `drone_render` | 11 | 52.0 mm² | 1.7% | alpha | — | never | never |
| `enthusiast_logo` | 4 | 2.7 mm² | 0.7% | alpha | — | never | never |
| `logo_alpha` | 1 | 160.7 mm² | 11.1% | alpha | — | never | never |

Three readings:

1. **gaulke is the fix the review described.** Its black frame makes stage 1
   flood black, so its 46 black lettering regions (16% of the design) are
   "enclosed background" and unstitched; the rule sews them in the Black and
   Charcoal cones they already carry on every garment but Black — where a
   black hole IS the garment, and staying a hole is right.
2. **The threshold is a decision, and 5 is too eager.** At
   `DELTA_E_VISIBLE` (5.0) a white hole sews in White thread on the Studio's
   DEFAULT garment, Natural (ΔE00 6.4) — Golden Tee's 643 mm² and whitebg's
   160 mm² of white on natural cloth. At `DELTA_E_CLEARLY_DIFFERENT` (10.0)
   Natural keeps the hole and Sand (16.0) sews it; the black and dark holes
   sew on every light garment either way. Both numbers exist in preflight;
   no new one.
3. **The review's headline case is out of the rule's reach by construction.**
   Becker's 41% is ALL alpha: the transparent bodies have no colour to
   compare, and the verdict's §5.2 (the flattened pixels carry the ink's
   colour) stands. Sewing them on a dark garment means CHOOSING a fill colour
   — the pro chose Gray — which is a per-design decision the review screen
   already supports (the shape's stitched toggle and a recolour), not a rule
   the pipeline can derive. Four fixtures, 1,135 mm², are in that bucket.

## 5. Decisions — Kent's

1. **The threshold**: `DELTA_E_CLEARLY_DIFFERENT` (10) — recommended, so the
   default Natural garment does not sew white into white; or
   `DELTA_E_VISIBLE` (5), the review's number, which does.
2. **Alpha holes**: leave them to the review toggle (recommended; the
   verdict's reason is unchanged), or a chosen fill colour for alpha holes on
   dark garments — a taste constant the pro's Gray suggests and nothing here
   derives.
3. **The default**: built OFF (`cfg.enclosed_by_garment`), the Studio
   sending `garment_rgb` from the project either way; flip on the renders —
   gaulke and Golden Tee on Black and on White, OFF beside ON.

## 6. Built (2026-09-10) — `cfg.enclosed_by_garment`, DEFAULT OFF

Everything in §2, on the flipped tree (#442's engine):

- **`Prep.bg_rgb`** — the border flood's colour as `(R, G, B)`; None on
  the alpha path and wherever no flood ran. whitebg (255, 255, 255),
  gaulke (0, 0, 0), logo_alpha None.
- **`cfg.garment_rgb`**, **`cfg.enclosed_by_garment`** (False),
  **`cfg.enclosed_by_garment_de00`** (10.0, pinned equal to
  `preflight.DELTA_E_CLEARLY_DIFFERENT` by test). The service refuses a
  malformed `garment_rgb` with a 400 naming the shape; `null` means not
  known.
- **`stage4_vectorize.garment_sews_enclosed(p, cfg)`** — the one verdict
  per design, `(sews, ΔE00)`; `(False, None)` when the rule cannot speak.
  Read by the stitched default in `finish_generation` and by the colour
  cap's ranking (`enforce_color_cap(count_enclosed=)`), so the two agree.
- **The stitched seam**: a flood hole sews by default when the verdict
  says so, `meta["enclosed_by_garment"] = True` (kept under a review
  override that turns it back off, so the panel can say "the garment
  would sew this; you turned it off"); the review payload echoes it,
  read-only, beside `enclosed_colour_unknown`. `BACKGROUND_ENCLOSED`'s
  sentence now says what the rule decided and why, with `garment_rgb`,
  `bg_rgb`, `delta_e00`, `sews_by_garment`, `sewn_by_garment` beside it —
  on a copy, since the Prep is shared across forks.
- **The Studio** sends `project.fabricRgb` as `garment_rgb` beside
  `garment_id` (three rounded channels; nothing when a pre-fabricRgb save
  has none). One cache-key change on existing designs, which re-digitize
  to the same bytes because the rule is off.
- Tests: `tests/test_enclosed_by_garment.py` (12), seven in
  `test_service.py`, the Studio spec pinned (`garment_rgb` in the field
  list). OFF is byte-identical with a garment colour given, on whitebg,
  gaulke and logo_alpha.

**Measured, 80 mm / `left_chest` / the engine's `max_colors` 12**
(`docs/renders/enclosed-by-garment-2026-09-10/`, OFF left, ON right, one
row per Studio swatch, the thread drawn on a ground the colour of the
fabric):

| fixture | OFF | ON White | ON Natural | ON Navy | ON Black |
|---|---|---|---|---|---|
| whitebg (1 hole, white) | 4,550 st / 6 tr / 5 cones | = (0.0) | = (6.4) | 5,121 / 7 / 6, the hole sews `0015` (75.2) | same as Navy (100) |
| golden tee (4 holes, white: the GT bodies and the arc) | 6,677 / 59 / 11 | = (0.0) | = (6.4) | 9,704 / 66 / 12, 4 of 4 sew (75.2) | same as Navy (100) |
| gaulke (46 holes, black: the roof and every letter) | 9,078 / 23 / 2 | 13,057 / 66 / 3, 46 of 46 sew (100) | same (88.6) | same (21.3) | = (0.0) |

Read off the sheets:

- **whitebg and Golden Tee are the case the review made.** On navy and
  black the ring's hole and the GT letter bodies sew white — the logo as
  drawn; on white and natural they stay fabric, and nothing changes.
  Golden Tee pays +3,027 stitches and +7 trims for four shapes and one
  cone.
- **gaulke is the case the review did not make, and it is the honest
  one.** On any light garment its 46 black bodies sew, +3,979 stitches and
  **+43 trims** (23 → 66: forty-six small shapes, each its own trim), and
  what sews is what the vectorizer kept when these were holes: the roof
  outline and STEEL ROOFING & SUPPLY read, GAULKE INDUSTRIES is fragments.
  That is the thin-stroke plan's own gaulke finding (16 of 18 thin strokes
  lost because they were enclosed background) from the other side: this
  flag makes them sew, `keep_thin_strokes` would make them whole, and
  neither alone gives the customer the lettering. On black the bodies ARE
  the fabric and the engine is byte-identical.
- **Natural never sews a white hole at 10** (6.4 both times) and always
  sews gaulke's black ones (88.6). At `DELTA_E_VISIBLE` (5) the Studio's
  default garment would sew whitebg's and Golden Tee's white holes white
  on natural — visible white on off-white, which the 08-15 verdict called
  wrong. That is §5.1, unchanged.
