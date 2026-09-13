# `cfg.keep_thin_strokes` — the flip sheet, re-measured 2026-09-13

**Status: evidence, not a change.** Nothing was flipped on this branch.
`cfg.keep_thin_strokes` is still `False` and `cfg.dissolve_phantom_blends` is
still `False`. The flip is Kent's.

**Why this exists.** Four default-OFF flags that got a render
(`enclosed_by_garment`, `robust_region_colour`, `legibility_check`,
`subpixel_edges`) were each decided within days. `keep_thin_strokes` is built
on both lanes, measured, and has sat since 2026-09-08 as the only waiting flag
with **no render** — while being the one that targets Kent's own "whole
elements missing" complaint (taglines, `EST 1895`, small caps). So: a render,
and a sheet re-measured on today's tree.

**Tree:** `8a94bfe`. Every row carries its own engine stamp
(`tools/flip_sheet.py::_head`), and **six of them read `8a94bfe-dirty`** — the
attribution rows in §1, measured after this file existed as an untracked
document. The only working-tree difference is this `docs/` file and the render
directory; **no engine, test or tool file was modified on this branch** (`git
status` shows it). Saying so is the point of the stamp. **Renders:**
[`docs/renders/thin-strokes-2026-09-13/`](renders/thin-strokes-2026-09-13/).

**How each row was measured.** One `digitize` per (fixture, arm) at the
fixture's *own* Studio parameters — the widths and garments
`tools/thin_strokes.py::REAL_ART` carries, at the Studio's shipped
`max_colors` 6 — so the thin-stroke recall and the flip-sheet columns come off
the **same plan** instead of two runs at two sizes. Everything that reads that
plan is a shipped instrument, called not copied:

- `tools/thin_strokes.py` — `find_thin_strokes` / `score_strokes` / `measure`
  (the p90-width definition, shared with the engine's own `thin_ink.py`).
- `tools/flip_sheet.py` — `_stitch_digest` (so "byte-identical" is proved, not
  asserted) and `_head` (so a row names the engine it ran on).
- `digitizer_core.preflight.run_preflight` — grade, `raw_score`, findings.

**Why `tools/flip_sheet.py` was not run as a whole.** `keep_thin_strokes` is
not one of its `ARMS`, and adding an arm is an edit to a tool this branch is
not allowed to change. Its harness also runs every fixture at one size
(`WIDTH_MM = 80`, `GARMENT = "left_chest"`), and Fremont's own case is
**92.5 mm on a patch** — the size the tagline question is asked at. Its
functions are reused; its `run`/`report` are not.

---

## 1. The discrepancy: today's tree agrees with the 09-12 audit, and the 09-08 table is superseded

Two recorded readings of Fremont ROUTED, OFF → ON, disagreed on the **sign** of
the stitch cost. Re-measured today:

| reading | lost thin strokes | recall | stitches | trims |
|---|---|---|---|---|
| MASTER_SCOPE / scope-history, 2026-09-08 | 18 → 3 | 84.8% → 92.5% | 17,400 → **16,006** | 114 → **66** |
| audit run, 2026-09-12 | 18 → 3 | 85.2% → 92.5% | 18,316 → **19,881** | 103 → 76 |
| **this run, 2026-09-13, tree `8a94bfe`** | **18 → 3** | **85.2% → 92.5%** | **18,316 → 19,881** | **103 → 76** |

**My run supports the 2026-09-12 audit, digit for digit** — both arms, both
counts, both recalls. The 2026-09-08 figures are **superseded**: neither of
that day's baselines exists on this tree, and the sign of the stitch cost is
the opposite of what it records.

**So the MASTER_SCOPE line is stale.** It reads:

> Fremont ROUTED 18 → **3** lost (84.8% → 92.5%) at **fewer** stitches and
> trims (17,400 → 16,006; 114 → 66)

Today it is **more** stitches (+1,565, +8.5%) and **fewer** trims (−27). The
"fewer trims" half survives; the "fewer stitches" half is now false and is the
claim a flip would be sold on. *(Not corrected in place here — this branch may
only write under `docs/`. It is the first thing to fix in MASTER_SCOPE.)*

### What moved it — and what did NOT

Between 09-08 and today `main` gained `subpixel_edges` (ON 09-09), the colour
bundle and `robust_region_colour` and `enclosed_by_garment` (ON 09-10),
`edge_cap="bean"` (ON 09-11), and `layer_palette_from_regions` (ON 09-12).
The obvious suspect was the edge cap: it outlines every fill edge that ends in
open air, and ON there are 110 more regions to outline. **Measured, it is not
the cause.**

| Fremont arm | stitches | trims | regions | lost | recall |
|---|---|---|---|---|---|
| `off` (shipped) | 18,316 | 103 | 54 | 18 | 85.2% |
| `keep_thin_strokes` | 19,881 | 76 | 164 | 3 | 92.5% |
| `edge_cap="none"` | 17,374 | 102 | 54 | — | — |
| `edge_cap="none"` + `keep_thin_strokes` | 18,900 | 75 | 164 | — | — |
| **the seven post-09-08 defaults put back**, OFF | **17,326** | 108 | 55 | 19 | 84.5% |
| **the same, + `keep_thin_strokes`** | **15,996** | 66 | 164 | 3 | 92.5% |

- **The edge cap is not it.** ON − OFF is **+1,565** stitches with the cap and
  **+1,526** without it. The cap costs both arms about the same (+942 on OFF,
  +981 on ON), so of the ~2,950-stitch swing between the 09-08 reading and
  today's it accounts for 39.
- **`layer_palette_from_regions` is not it either** — `False` is
  **byte-identical** to the shipped engine on Fremont in both arms (same
  `_stitch_digest`), so the newest flip is inert here.
- **The whole sign change comes back when the post-09-08 defaults do.** With
  `subpixel_edges`, the four colour-bundle flags, `robust_region_colour` and
  `layer_palette_from_regions` set `False` and `edge_cap="none"` — the way they
  stood on 2026-09-08 — Fremont reads **17,326 → 15,996 stitches and 108 → 66
  trims**, i.e. the SAVING, and within 0.4% of what the 09-08 entry recorded
  (17,400 → 16,006; 114 → 66). The thin-stroke code did not change; the engine
  under it did.
- **And the cost lands almost entirely on the ON arm.** Against that
  pre-09-08 engine, today's defaults add **48** stitches to Fremont's OFF plan
  and **2,904** to its ON plan. Whatever the mechanism, it is an interaction
  with the 110 extra regions the flag creates, not a flat tax.

**It is `cfg.subpixel_edges`, on its own.** One more pair isolates it —
`subpixel_edges=False` and nothing else changed from today's engine:

| Fremont arm | stitches | trims | regions | lost | recall |
|---|---|---|---|---|---|
| `subpixel_edges=False` | 18,337 | 114 | 54 | 18 | 84.5% |
| `subpixel_edges=False` + `keep_thin_strokes` | **16,974** | 67 | 164 | 3 | 92.5% |

ON − OFF is **−1,363 stitches and −47 trims**: the saving, back, from turning
off one flag. Read the other way round, switching `subpixel_edges` on *saves*
Fremont's OFF plan **21** stitches and *costs* its ON plan **2,907**. That
2,928-stitch asymmetry is the whole swing, and the
mechanism is the one its own flip recorded: sub-pixel vertices grow stage 4's
vertex counts 45–155% on real logos (Fremont 1,501 → 2,170), and ON there are
110 more small regions whose boundaries get that treatment — every rescued
hairline is outlined by a denser polygon.

**Nothing here is an argument against `subpixel_edges`** (Kent flipped it
2026-09-09 on edge-fidelity evidence, and it is nearly free on the arm that
ships today). It is an argument about how to price *this* flip: on today's
engine the rescued lettering costs about 8.5% more stitches, and the old
"fewer stitches" line is an artefact of a tree that no longer exists.

**Consequence for anyone re-reading the 09-08 numbers:** they were true on the
engine of their day and are not transferable. Quote this sheet, or re-measure.

---

## 2. Per-fixture OFF → ON, today's tree

Every row: one plan, `max_colors` 6, the fixture's own width and garment.
"Thin (mm)" is the artwork's thin-stroke population and its total skeleton
length — the same population in both arms, because it is read off the artwork,
not off the regions. "Lost" is a stroke under 50% sewn in its own colour.
`(rescued)` is the `rescued_small_shape` count among the regions. Grade is
preflight's letter and clamped score, with the **unclamped** `raw_score` in
brackets, because ten of this corpus's designs sit on the clamped 0 and a real
move there shows only in the raw number.

| fixture | class | thin (mm) | lost | recall | regions (rescued) | stitches | trims | blocks | cones | grade (raw) |
|---|---|---|---|---|---|---|---|---|---|---|
| `logo_hotel_fremont` @ 92.5 / patch | gradient | 162 (975) | **18 → 3** | **85.2% → 92.5%** | 54 (0) → 164 (138) | 18,316 → 19,881 | 103 → **76** | 4 both | 3 both | **C 64 → B 76** |
| `drone_render` | gradient | 45 (349) | **11 → 4** | **79.5% → 95.5%** | 74 (8) → 107 (29) | 17,250 → 18,551 | 97 → **140** | 9 both | 6 both | F 0 (−68) both |
| `logo_gaulke_roofing` | gradient | 18 (163) | 15 both | 42.0% both | 56 (1) → 62 (9) | 11,131 → 11,034 | 40 → 43 | 3 → 5 | **2 → 4** | B 76 both |
| `logo_golden_tee` | gradient | 3 (8) | 1 → 0 | 74.4% → 88.1% | 37 (1) → 39 (4) | 6,846 → 6,843 | 61 → 67 | 8 → 9 | 6 both | F 0 (−32 → **−50**) |
| `screenshot_phone_ui_golke` | gradient | 28 (201) | 8 → 7 | 93.0% → 94.0% | 153 (83) → 158 (88) | 8,396 → **8,243** | 75 → **71** | 7 → 8 | 6 both | F 0 (−56 → **−8**) |
| `logo_bridge_bar` | gradient | 2 (3) | 0 both | 100% → 54.6% | 49 (4) → **78 (26)** | 13,820 → 14,600 | 96 → **124** | 6 both | 6 both | F 0 (−8) → F 4 (4) |
| `becker_marine_logo` @ 100 | flat | 0 | — | — | 17 (0) → 18 (1) | 17,697 → 17,699 | 40 → 41 | 2 → 3 | **1 → 2** | B 88 both |
| `enthusiast_logo` | flat | 14 (59) | 1 both | 94.8% both | 31 (18) both | 2,492 both | 25 both | 3 both | 2 both | B 88 both |
| `logo_script_tires` | photo_scene | 0 | — | — | 6 (0) both | 2,345 both | 12 both | 2 both | 1 both | B 88 both |

`enthusiast_logo` and `logo_script_tires` are **byte-identical** ON
(`_stitch_digest` equal), not merely close: the flat lane's absorb rule finds
nothing to change on one, and `photo_scene` is gated out of the population by
construction (`pipeline.build_generation`, `thin_population=` reads
`keep_thin_strokes and class_ == "gradient"`).

**Fremont's bands** — this is the part that says the recall is the flag's doing
and not a side effect of sewing 8.5% more thread:

| band | strokes | lost OFF → ON | recall OFF → ON |
|---|---|---|---|
| < 0.5 mm (under the satin cross floor) | 47 | 14 → **3** | 52.2% → **92.0%** |
| 0.5–1.0 mm | 110 | 4 → 0 | 90.0% → **87.9%** |
| 1.0–1.5 mm | 5 | 0 → 0 | 97.2% → 100% |

The band that rises is the band the flag targets; the band beside it clears its
last four lost strokes but its aggregate recall dips 2.1 points. A plan that
simply painted more thread would lift every band at once, and this one does
not.

**Cone lists** (the repo's rule: where a change moves a cone, read the list,
not the grade):

- `logo_hotel_fremont`: unchanged — `0015, 0020, 0862, 0015`, 3 cones, 4 blocks.
- `logo_gaulke_roofing`: `0015, 4174, 0015` → `0015, 2564, 0111, 0145, 0015`.
  **One spool dropped and three added, for no recall change at all.** The
  fixture's own defect is elsewhere: its line-art is enclosed background, so
  with no garment colour neither arm sews it. Given one (`garment_rgb` white,
  so `enclosed_by_garment` acts) the bodies do sew — 14,011 st / 67 tr OFF
  against 13,665 / 65 ON — and `C GOLKE INDUSTRIES` still does not read on
  either arm.
- `becker_marine_logo`: `1776, 1776` → `1776, 0020, 1776`. **A black cone added
  to a one-cone design**, for one rescued region, +2 stitches, +1 trim.
- `drone_render`: `1776, 3335, 1102, 3971, 1305, 1776, 0145, 3971, 3971` →
  `1776, 1305, 0111, 0108, 3971, 1305, 1776, 2564, 3971` — six cones both ways,
  but three spools swapped; the whole-design render shows the drone's blue
  canopy panel going grey.
- `logo_golden_tee`: six cones both ways, one more colour STOP (8 → 9 blocks).
- `screenshot_phone_ui_golke`: six cones both ways, `0108 → 0142`,
  `3630 → 3900`, one more block.
- `logo_bridge_bar`: `5866` out, `1375` in; six cones both ways.

---

## 3. Fremont's preflight reading

| | OFF (shipped) | ON |
|---|---|---|
| grade / score / raw | **C 64 / 64** | **B 76 / 76** |
| `LETTERING_TOO_SMALL` | warn — 36 of **45** satin shapes below readable size | warn — 17 of **19** |
| `STITCHES_TOO_SHORT` | warn — **66%** of satin stitches under the 1 mm needle minimum | warn — **72%** |
| `TRIM_HEAVY` | warn — 5.6 trims per 1,000 stitches (pro range 0.1–4.1) | **gone** (76 trims on 19,881 = 3.8) |
| stitches / trims / jumps / thread | 18,316 / 103 / 96 / 33.46 m | 19,881 / 76 / 145 / 35.26 m |
| blocks / cones | 4 / 3 | 4 / 3 |

Two things to read carefully here.

1. **The grade move is real and it is the trims.** Both scores are off the
   clamped floor (raw = clamped on this design), so C 64 → B 76 is not the
   floor artefact row 6 of the yardstick doc warns about. What cleared is
   `TRIM_HEAVY`: 138 strokes that SEEDS used to shatter into fragments now
   arrive as their own regions and chain, so the plan cuts 27 fewer times.
2. **`STITCHES_TOO_SHORT` gets worse, and that is the honest cost.** 66% → 72%
   of satin stitches under the needle minimum. The rescued strokes are
   0.3–0.5 mm of ink and sew as three-pass hairline bean runs — thread on
   thread. This is the same defect `cfg.lettering_min_column_mm` exists to fix
   and has not yet fixed (measured negative, 2026-09-09; its 1.0 mm column is
   a ROADMAP gate-1 number). **A flip ships more sub-minimum stitches on
   Fremont, and only a sew-out can say whether they break thread.**

The "satin shapes 45 → 19" line is not a loss of satin: it is the rescued
population arriving at the run tier instead of being absorbed into shapes that
were then classified satin.

**OCR was not available in this container** (no `tesseract` binary), so
`legibility_check`'s `LETTERING_ILLEGIBLE` could not fire on either arm and no
legibility number is quoted here. The renders are the legibility evidence.

---

## 4. The `logo_bridge_bar` negative, and the new evidence on it

Bridge Bar is the fixture where this flag costs and buys nothing: its "thin
strokes" are 400px-JPEG compression ringing around the black spokes, not
artwork. Measured today, all four arms on the same plan:

| arm | regions | stitches | trims | blocks | cones | grade (raw) | thin recall (2 strokes, 2.9 mm) |
|---|---|---|---|---|---|---|---|
| `off` (shipped) | 49 | 13,820 | 96 | 6 | 6 | F 0 (−8) | 100% |
| `keep_thin_strokes` | **78** | 14,600 | **124** | 6 | 6 | F 4 (4) | 54.6% |
| `dissolve_phantom_blends` | 32 | 11,438 | 64 | 7 | 6 | F 16 (16) | 100% |
| **both** | **33** | 11,669 | **65** | 7 | 6 | F 16 (16) | 81.7% |

**The flip's price on this fixture: +29 regions and +28 trims on its own;
+1 region and +1 trim when `dissolve_phantom_blends` is also on.** That
reproduces the 2026-09-12 audit's pairing exactly.

**This is new evidence bearing on a ruling Kent banked, and it is presented as
that and nothing more.** `cfg.dissolve_phantom_blends` was ruled OFF and banked
2026-09-04 — deliberately parked, not pending — on two mild negatives and a
five-of-six residual, and `docs/pending-flag-decisions-2026-09-06.md` records
that the ruling stands. Nothing here re-opens it and nothing here recommends
flipping it. What is new is only this: **nobody knew the banked flag was also
the guard that makes `keep_thin_strokes` nearly free on the worst-case
fixture.** That is a fact about the pair, and what to do about it is Kent's.

Two further facts about the pair, measured the same way and worth having
because they bound it:

- **On Fremont and gaulke the dissolve is byte-identical** — `off` and `halo`
  produce the same `_stitch_digest`, and so do `kts` and `kts_halo`. It only
  acts on the JPEG. So the pairing is not a general remedy for this flip's
  cost; it is a remedy on compressed sources.
- **Bridge Bar's own lettering is not what is at stake.** BAR & RESTAURANT is
  unsewn on every one of the four arms (see the render) — it is 3 mm blue text
  on yellow that the design never sews at all. This flag does not rescue it.

---

## 5. The renders

[`docs/renders/thin-strokes-2026-09-13/`](renders/thin-strokes-2026-09-13/),
with `numbers.txt` beside them. Every panel is
`tools/thread_color_render.py`'s own panel — the re-read source pixels faded to
35%, each run drawn in its block's cone RGB, the same mm frame preflight uses
— OFF on the left, at the fixture's real size and the Studio's `max_colors` 6.
Only the crop boxes and the stacking are new; the drawing is the shipped
renderer's.

**Know what this renderer can and cannot adjudicate before reading them.** At
16 px/mm the polylines pile up and small text looks more solid than it is; at
26–34 px/mm you see individual stitches. Neither view is a good judge of **tan
thread on a tan glyph over a white ground**, which is exactly Fremont's
tagline — for those rows the per-cone stitch counts below are the evidence.
The panels where the eye genuinely decides are `THE` (black on white), drone's
`AND DRONE` (grey on grey-white, but unsewn OFF so the difference is
presence/absence), and Bridge Bar's half-sewn spoke.

| panel | what it answers |
|---|---|
| `logo_hotel_fremont_whole_off-on.jpg` | the design, both arms, 16 px/mm |
| `logo_hotel_fremont_the_off-on.jpg` | **the clearest gain.** OFF, `THE` carries two stray black marks and is otherwise unsewn artwork; ON, the letterforms are stitched |
| `logo_hotel_fremont_est-1895_off-on.jpg` | `EST 1895` and the Wisconsin, 34 px/mm |
| `logo_hotel_fremont_eat-stay-play_off-on.jpg` | the tagline Kent named, 34 px/mm |
| `logo_hotel_fremont_rope-and-frame_off-on.jpg` | **the one thing that goes the other way.** OFF, the rope carries scattered tan zigzags; ON, that corner of the rope has none — even though the tan cone overall more than doubles (see the per-cone table below) |
| `drone_render_lettering_off-on.jpg` | **the headline gain.** OFF, `AND DRONE` is not sewn at all; ON, the subline is stitched and reads |
| `drone_render_whole_off-on.jpg` | the price beside it: the canopy's blue panel goes grey as three spools swap |
| `logo_gaulke_roofing_golke-industries_off-on.jpg`, `_steel-roofing_`, `_roof-line-art_` | **nothing moves.** Both arms leave the lettering unsewn |
| `logo_gaulke_roofing_on-white_whole_off-on.jpg`, `_on-white_golke-industries_` | **the fair test for gaulke**, and it fails too: with a garment colour set (`garment_rgb` white) `enclosed_by_garment` acts and the black bodies sew — 14,011 st / 67 tr OFF against 13,665 / 65 ON — and `C GOLKE INDUSTRIES` still does not read on either arm |
| `logo_bridge_bar_whole_off-on.jpg` | three arms: OFF, ON, ON+dissolve |
| `logo_bridge_bar_ringing-se_off-on.jpg` | **the negative in one picture.** ON, a spoke is left half-unsewn with ringing shards beside it; with the dissolve also on, the spoke is whole again |
| `logo_bridge_bar_bridge-script_off-on.jpg` | stray marks appearing inside the `Bridge` script ON |
| `logo_bridge_bar_bar-restaurant_off-on.jpg` | `BAR & RESTAURANT` unsewn on all three arms — this flag does not rescue it |
| `logo_golden_tee_whole_off-on.jpg` | a null result, kept as one: 6,846 → 6,843 stitches and no visible change |

### Where Fremont's +1,565 stitches go, per cone

Counted off `iter_machine_commands` — the same stream `StitchPlan.stats` and
the DST encoder read — and beside it the thin-stroke recall split by the
stroke's OWN artwork colour:

| | OFF | ON |
|---|---|---|
| `0015` white (ground) | 12,412 | 11,968 |
| `0020` black (`HOTEL FREMONT`, frame) | 3,484 | 3,504 |
| **`0862` tan (`EST 1895`, `EAT STAY PLAY`, rope)** | **1,478** | **3,428** |
| `0015` white (second block) | 942 | 981 |
| **total** | 18,316 | 19,881 |

| strokes by artwork colour | length | recall OFF → ON | lost OFF → ON |
|---|---|---|---|
| black, 22 strokes | 581.3 mm | 96.0% → **99.3%** | 2 → **0** |
| **tan, 136 strokes** | 387.4 mm | **69.6% → 82.8%** | **14 → 2** |
| white, 4 strokes | 6.1 mm | 48.4% → 67.4% | 2 → 1 |

**The extra stitches are the lettering, in its own colour.** The tan cone more
than doubles (+1,950) while the white ground gives back 444, and the tan
strokes — which is what `EST 1895` and `EAT | STAY | PLAY` are — go from 14
lost to 2. This is the answer to the gate-4-shaped worry in §2 from the other
direction: the added thread is not spread over the design, it is on the cone
that carries the missing elements.

**One thing the picture shows that I could not fully explain, recorded as
such.** In `logo_hotel_fremont_rope-and-frame_off-on.jpg`, the scattered tan
marks lying along the rope OFF are **absent ON**, while the tan cone overall
sews more than twice as much. So within the tan cone the thread moves toward
the lettering and away from the rope's own texture. Whether that is a loss
worth caring about is an eye question on a sew-out, not one this sheet
settles; it is flagged rather than smoothed over.

---

## 6. ROADMAP gates — my own reading

Checked against `ROADMAP.md` on this tree, not against the audit's summary of
it. **No gate blocks this decision.** The audit's reading is right; here is
mine, with the one thing it does not say.

**Gate 1 — "No sew-out, no physical constants." Does not apply to the flip.**
`keep_thin_strokes` introduces no constant. Every number it uses already
governs today's engine: `cfg.merge_delta_e` (6.0 CIE76, the flat lane's own
merge tolerance), `cfg.min_detail_mm` (1.5 mm), `machine.RUN_MIN_LOOP_MM` and
`RUN_MIN_AREA_MM2` (the run tier's floors, which decide what it keeps),
`THIN_INK_MIN_PX` (3) and `THIN_INK_WIDTH_PCT` (90) in the shared population
finder. The gate's own test settles it: *"If every source you would consult to
settle it owns no machine, this gate does not apply."* Whether a 0.4 mm mark
in a raster is a stroke or a sliver is answered by the raster and by floors
that already ship; no cloth is consulted.

**But gate 1 owns the question standing right behind the flip, and the sheet
should say so rather than let it arrive later.** ON, Fremont's
`STITCHES_TOO_SHORT` goes 66% → 72%: the rescued strokes are thinner than the
satin cross floor and sew as three-pass hairline beans. Whether that is a mark
a machine makes on a knit, or thread on thread and a break, is exactly the
kind of thing only a sew-out answers — and the flag that would widen them
(`cfg.lettering_min_column_mm`, 1.0 mm = `PHOTO_MIN_SATIN_WIDTH_MM`) is itself
a gate-1 number, still OFF, and measured as not moving the tier when it was
first tried. So: the flip is not gated, the *quality of what it sews* is a
sew-out question, and flipping it does not create that question — the run
tier's existing `small_shape_rescue` (ON by default) already sews sub-floor
shapes this way. It enlarges it.

**Gate 2 — "No stage-0 recalibration without real tonal artwork." Does not
apply.** The flip moves no classifier boundary and adds no signal. It *reads*
stage 0's verdict — `pipeline.build_generation` passes the population as
`keep_thin_strokes and classification.class_ == "gradient"` — which is a
consumer of the classifier, not a recalibration of it.

**Gate 3 — "No default-OFF tier flipped on until its instrument is rebuilt
(chaining and contour)." Does not apply, and I agree with the audit.** This is
not a tier. It changes which regions reach stage 4; the tier that sews them —
the run/bean tier — is already default-ON through `cfg.small_shape_rescue`.
And the gate's actual worry, that a green suite can hide needle-down thread on
bare fabric, is the case the instrument here answers rather than dodges:
`tools/thin_strokes.py` reads the STITCHES, through
`stitches.iter_machine_commands`, and a stroke covered by thread of the wrong
colour counts as lost. That instrument exists, and it has already been
rebuilt once under fire (the median→p90 width correction, 2026-09-08, after
its first version counted Fremont's white ground as a 1,758 mm stroke).

**Gate 4 — "No quality claim on a raw agreement number." Complied with, and it
bites here in a specific way.** Thin-stroke recall is not an agreement
statistic between two raters, so it has no chance-corrected counterpart to
quote: it is sewn skeleton length over total skeleton length, matched by
colour within `TEXT_CLUSTER_DELTA_E_MAX`. But the gate's *reason* — a "gain"
can be the floor moving — applies directly, because the ON arm sews 8.5% more
thread on Fremont and more thread covers more skeleton by accident. The
control is the per-band split in §2: the targeted band goes 52.2% → 92.0%
while the band beside it goes 90.0% → 87.9%. No raw agreement or `direction`
number is quoted anywhere in this sheet, and no quality claim rests on one.

---

## 7. What a flip would also cost, in work

`tests/test_keep_thin_strokes.py` **passes, 8/8, on this tree** — including
the pair that pins the primary golden holding OFF and the teal patch being
kept ON. Nothing here breaks it, because nothing here changes a default.

Flipping does move goldens, and this is measured rather than assumed (engine
default `max_colors` 12, OFF → ON):

| golden fixture | OFF | ON | |
|---|---|---|---|
| `logo_whitebg.png` @ hat_front | 6,148 st / 10 tr / 6 blocks / 5 cones / 7 regions | 6,175 / 11 / 7 / **6** / 8 | **moves** |
| `logo_alpha.png` | 5,774 / 9 / 6 / 5 / 7 | 5,784 / 10 / 7 / **6** / 8 | **moves** |
| `ribbon_curve.png` | 991 / 1 / 1 / 1 / 1 | identical | byte-identical |
| `bg_uncertain.png` | 10,384 / 2 / 2 / 1 / 1 | identical | byte-identical |

So a flip is a golden recapture on **two** flat-lane keys — each gaining one
region, one block and one cone, the teal-patch mechanism
`tests/test_keep_thin_strokes.py` already documents — plus whatever the
photo-lane snapshot golden does on the gradient fixtures (not measured here;
the flat pair was the cheap half). Per the repo's rule, a recapture lands on
ubuntu CI with the pre-change proof and every mover attributed.

---

## 8. The read

**The flag does the job it was built for, on the two designs where Kent's
complaint actually lives, and it is not free — and the line it used to be sold
on is gone.** Fremont keeps its small lettering (18 → 3 lost thin strokes, the
sub-0.5 mm band 52% → 92%, `THE` stitched where it was two stray marks) and
grades C 64 → B 76 because `TRIM_HEAVY` clears at 27 fewer cuts; drone's
`AND DRONE` subline goes from not sewn at all to sewn and readable
(11 → 4 lost, 79.5% → 95.5%); the phone screenshot gets strictly cheaper and
better (−153 stitches, −4 trims, raw −56 → −8). **And the extra stitches are
the missing elements themselves**, not spread cost: Fremont's tan cone — the
one carrying `EST 1895` and `EAT | STAY | PLAY` — goes 1,478 → 3,428 while the
white ground gives back 444, and its tan strokes go from 14 lost to 2.
Against that: Fremont costs
**+1,565 stitches (+8.5%)** and pushes its sub-needle-minimum share 66% → 72%;
drone costs +1,301 stitches and +43 trims and swaps three spools, losing the
canopy's blue panel; **gaulke pays two extra cones for nothing at all** (15 of
18 strokes lost either way, on either garment); **becker takes a second cone on
a one-cone design** for a single rescued region; Golden Tee takes an extra
colour stop and drops raw −32 → −50; and Bridge Bar pays +29 regions and +28
trims unless `dissolve_phantom_blends` — banked — is on beside it, where the
bill falls to +1 and +1. Two flat goldens need recapturing.

**So: three designs clearly better, three clearly worse, three unmoved, and the
better ones are better in exactly the place the customer complains about while
the worse ones are worse in cones and stitches.** That is a trade I would take,
and it is Kent's to take. What I would NOT let it be sold on is cost: the
"keeps more and sews less" line was true on 2026-09-08's engine and is false on
this one, and anyone re-reading MASTER_SCOPE will otherwise believe it.

**If it were mine to sequence**, I would flip it and treat gaulke's two extra
cones and becker's one as the price — they land on designs this flag cannot
help, and `enforce_color_cap` is already ON to hold the Studio's promised six
— and I would raise the hairline question separately rather than let it
block this: 72% of Fremont's satin stitches under the 1 mm needle minimum is a
real risk of thread breaks, it is what `cfg.lettering_min_column_mm` exists to
fix and has not yet fixed, and **it is a sew-out's question (gate 1), not a
measurement's**. The flip enlarges that question; it does not create it, since
`small_shape_rescue` already sews sub-floor shapes as hairline beans by
default today.

**If Kent would rather not enlarge it before a sew-out, holding is a coherent
position and the sheet does not argue against it** — but then the thing worth
doing is the sew-out, not more measurement: every number in this sheet is now
on today's tree, and the next fact that would move the decision is what a
0.3–0.5 mm bean stroke does on a knit.
