# The five parked flags, measured together — 2026-09-06

A decision sheet for the flags that are built, measured and still OFF. Every
number is one pass of `digitizer/tools/flip_sheet.py` over the scorecard's own
26 fixtures at 80 mm / `left_chest`. Seven arms: the shipped default, each flag
alone, and **all five together — the combination nobody had measured.**

**Every number below is post-fix**, on `main` at `20fa551`. The sheet found a
regression in `dissolve_phantom_blends` on its first pass; that flag is fixed
and re-measured, and the history is in "What this sheet went through" at the
end rather than interleaved with the numbers. Read the table as current.

Two flags are deliberately absent. `edge_cap` is gate 1 (cloth settles which
cap, if either — defect 19) and `chain_links` is barred permanently under gate
3. Measuring either would produce a number that cannot be acted on.

## The table

| arm | moved | stitches | trims | blocks | cones | grades |
|---|---:|---:|---:|---:|---:|---|
| `dissolve_phantom_blends` | 4/26 | −2,865 | **−67** | −8 | −7 | none |
| `revalidate_small_shapes` | 5/26 | +313 | +6 | +1 | +1 | meadow D 52 → C 64 |
| `bind_resnap_all_classes` | 5/26 | −614 | −13 | **−18** | **−17** | gaulke F 4 → F 16 |
| `satin_per_stroke` | 6/26 | −3,021 | +33 | 0 | 0 | chrome C 64 → B 76; meadow D 52 → C 64 |
| `satin_patch_junctions` | 3/26 | +789 | +10 | 0 | 0 | scene_stub B 76 → B 88; becker B 76 → B 88 |
| **all five** | **12/26** | **−5,719** | −28 | **−21** | **−20** | **5 up, 1 down** |

**No grade moves down in any SINGLE-flag arm.** The combination is the
exception, and finding it is what the `all` arm is for: with all five on,
`logo_script_tires` goes **A 100 → B 88** (trims 8 → 12) — a fixture no single
flag takes below A. Fourteen of 26 are byte-identical even with all five on.

**Read the grade with the floor in mind.** `yardstick-disagreements-2026-09-06.md`
row 6: twelve of the corpus's 52 combos score exactly 0 with unclamped scores
from −272 to −38, so on those designs a real improvement moves no grade and the
grade is not evidence either way. That is why the table leads with stitches,
trims, blocks and cones — those are not saturated.

## Per flag

**`satin_patch_junctions`** — smallest blast radius of the five (3 fixtures),
two grades up, and the cost *is* the fix: becker +383 st for the K's crotch,
the 37.2 mm² of bare cloth that is the whole reason that fixture graded B.
Nothing else in the corpus notices.

**`bind_resnap_all_classes`** — the biggest structural win: **−18 blocks and
−17 cones** across five fixtures, screenshot alone 17 → 11 blocks and 16 → 11
cones. It closes a documented escape where the operator loads a cone the plan
never names. On gaulke it is the only arm that puts real `0020 Black` on a
black logo, and it grades F 16 for doing so — see the yardstick note below.

**`revalidate_small_shapes`** — cheapest of the five (+313 stitches over the
whole corpus), fixes sewn colour the scorecard admits it cannot rank
(yardstick row 1), one grade up. Costs: meadow +165 st / +5 trims, bridge_bar
+155 st / +1 trim.

**`satin_per_stroke`** — two grades up and −3,021 stitches, but the trim cost
is real and concentrated: **`photo_chrome_specular` 84 → 111 trims** alone,
84 → 116 under all five. Worth it on that fixture's own grade (C 64 → B 76),
and worth seeing before it becomes a default.

**`dissolve_phantom_blends`** — on the measurements the cleanest of the five:
4 fixtures moved, **−67 trims**, no grade moving in either direction, and
`logo_bridge_bar` alone goes 14,338 → 11,506 stitches and **125 → 62 trims**,
18 → 12 blocks and cones. `screenshot_phone_ui` 71 → 66 trims, 17 → 15 blocks.
`logo_golden_tee` and `logo_script_tires` are inert (+24 st, +1 trim).

## Interaction — `all` is not the sum of the parts

| fixture | singles that move it | all five |
|---|---|---|
| `photo_dof_meadow` | `resnap_small` → C 64; `satin_stroke` → C 64 | **B 76** — better than either |
| `photo_chrome_specular` | `satin_stroke` only | different result from that flag alone |
| `logo_script_tires` | `halo` only (inert) | **A 100 → B 88** — the one grade that falls |

So "flip these three" cannot be read off three rows, which is what this arm
existed to establish. `summit_badge`, `becker_marine_logo` and
`logo_hotel_fremont` do behave as the single flag that moves them.

## Costs named rather than netted

The −28 net trims on the all-five arm hides `photo_chrome_specular` at
84 → 116. `satin_patch_junctions` costs becker +383 stitches, which *is* the
fix. `logo_script_tires` is the only fixture any arm takes down a grade.

## What I would do

Flip `satin_patch_junctions`, `bind_resnap_all_classes` and
`revalidate_small_shapes` — small, structural, and none of them depends on a
grade to justify it. Take `satin_per_stroke` with the chrome trim cost stated.
`dissolve_phantom_blends` was the one to hold and its regression is now fixed,
so it is a candidate again — on the numbers, the cleanest of the five.

All of it is Kent's call. `docs/renders/flip-sheet-2026-09-06/` has off-vs-all
sheets for gaulke, bridge_bar, chrome_specular and becker, plus a four-arm
lettering crop.

---

## What this sheet went through

Kept because the sequence is the useful part, and because two of its three
steps were wrong in ways worth not repeating.

### The yardstick finding, which stands

`logo_gaulke_roofing` is black lettering on a white label. Measured on the
CONES rather than the grade, on the pre-fix tree:

| arm | darkest cone | grade |
|---|---:|---|
| off | `1375 Dark Charcoal`, **L\* 15.9**, 288 st | F 4 |
| `dissolve_phantom_blends`, pre-fix | `0145 Skylight`, L\* 85.7 | **C 64** |
| `bind_resnap_all_classes` | `0020 Black`, **L\* 0.0** | F 16 |

**The best grade loaded no thread you would see on a white ground; the only arm
that loads Black graded second-worst.** `THREAD_MATCH_POOR` grades per thread
on its worst patch, so deleting the dark cone deletes the badly-scoring
thread — **the metric rewards not sewing the hard part.** That is
`yardstick-disagreements` row 7, and a different shape from rows 1–6: those are
the metric failing to *see* an improvement, this is it preferring a regression.

It also forced a retraction in MASTER_SCOPE defect 27, which had read *"gaulke
F 0 → C 64 … the difference between 'do not sew' and a usable design"* about a
design that had dropped its ink.

### Three steps to the cause, two of them wrong

1. **"Anti-aliased text reads as ringing."** A guess, published as a mechanism.
2. **A probe seemed to clear the fold**, so the guess was retracted — and the
   retraction was itself wrong. The probe looked for labels whose pixels
   changed LABEL, and this pass has a **second exit**: a label sent to the page
   keeps its label and leaves through `base_valid`. It saw 9 of 42.
3. **Counting both exits found it.** Every dark label on that fixture went to
   the page: 12,961 px, 50.3 mm², the 21.0 mm² wordmark included.

**The bug was one line.** `valid` inside the pass is `base_valid`, ENCLOSED
pixels already removed, so its complement is not the page — it is also donut
holes, letter counters and the inside of a label. Gaulke is black lettering on
a white label on a *black* canvas, so every letter read as bordering the
near-black page; its colour genuinely lies between that and the label's
L\* 98.8 ground, and the page endpoint DELETES rather than recolours.
`page_mask` now carries stage 1's real background.
`test_an_INTERIOR_band_is_never_sent_to_the_page` pins it both ways: 80 band
pixels survive with the true mask, **0** without.

The fix cost the flag nothing — bridge_bar's win is intact and gaulke is
byte-identical — and gaulke's all-five grade now reads F 4 → **F 16**, agreeing
with the arm that actually loads Black. The C 64 was the dropped cone.

### What it left in DOCTRINE

- A flag that removes a cone cannot be judged on its grade; machine units do
  not save you either (the same change reads "blocks 4→3, trims 30→18").
- A pass that can DELETE as well as relabel needs a probe that counts both.
- `~base_valid` is not the page.
