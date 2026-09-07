# The five parked flags, measured together — 2026-09-06

Kent, 2026-09-06: a decision sheet for the flags that are built, measured and
still OFF. Every number below is one pass of `digitizer/tools/flip_sheet.py`
over the scorecard's own 26 fixtures at 80 mm / `left_chest`, on `main` at
`8c7edf7`. Seven arms: the shipped default, each flag alone, and **all five
together — the combination nobody had measured.**

Two flags are deliberately absent. `edge_cap` is gate 1 (cloth settles which
cap, if either — defect 19) and `chain_links` is barred permanently under gate
3. Measuring either would produce a number that cannot be acted on.

## The table

| arm | moved | stitches | trims | blocks | cones | grades |
|---|---:|---:|---:|---:|---:|---|
| `dissolve_phantom_blends` | 5/26 | −4,272 | **−76** | −9 | −8 | gaulke F 4 → C 64 |
| `revalidate_small_shapes` | 5/26 | +313 | +6 | +1 | +1 | meadow D 52 → C 64 |
| `bind_resnap_all_classes` | 5/26 | −614 | −13 | **−18** | **−17** | gaulke F 4 → F 16 |
| `satin_per_stroke` | 6/26 | −3,021 | +33 | 0 | 0 | chrome C 64 → B 76; meadow D 52 → C 64 |
| `satin_patch_junctions` | 3/26 | +789 | +10 | 0 | 0 | scene_stub B 76 → B 88; becker B 76 → B 88 |
| **all five** (post-fix) | **12/26** | **−5,719** | −28 | **−21** | **−20** | **5 up, 1 DOWN** |

**No grade moves DOWN in any SINGLE-flag arm.** The combination is the
exception, and finding it is what the `all` arm is for: with all five on,
`logo_script_tires` goes **A 100 → B 88** (trims 8 → 12) — a fixture no single
flag takes below A. Fourteen of 26 are byte-identical even with all five on.

The `dissolve_phantom_blends` row is **pre-fix** (see §3); its post-fix numbers
are 4/26 moved, −2,865 stitches, −67 trims, −8 blocks, −7 cones and no grade
moving either way. The all-five row is post-fix and includes that flag.

## The finding that changes the decision

**On `logo_gaulke_roofing` the grade ranks the arms backwards, and it is my
own flag that it rewards for the wrong thing.**

The artwork is black lettering on a white label. What each arm actually loads:

| arm | cones (L\*) | darkest thread | grade |
|---|---|---:|---|
| off | White 100, Ghost White 91.8, **Dark Charcoal 15.9**, Silver 82.0 | **L\* 15.9**, 288 st | F 4 |
| `dissolve_phantom_blends` | White 100, Glacier Green 96.7, Skylight 85.7 | L\* 85.7 | **C 64** |
| `bind_resnap_all_classes` | White 100, Skylight 85.7, Charcoal 36.1, **Black 0.0** | **L\* 0.0** | F 16 |
| all five, pre-fix | White 100, **Silver 82.0** | L\* 82.0 | **C 64** |
| all five, post-fix | White 100, Skylight 85.7, Charcoal 36.1, **Black 0.0** | **L\* 0.0** | F 16 |

The two arms that grade **best** load no thread darker than L\* 82 for
lettering sitting on a white ground — thread you would not see. The only arm
that loads actual **Black** grades second-worst. The render agrees with the
cone list and not with the grade:
`renders/flip-sheet-2026-09-06/gaulke_lettering_by_arm.jpg` shows black thread
in `off` and `bind_resnap_all_classes` and none in the other two.

**The mechanism is not mysterious.** `THREAD_MATCH_POOR` grades per thread on
that thread's worst patch, so deleting the dark cone deletes the thread that
was scoring badly. You cannot have a poor thread match on a thread you never
loaded. **The metric rewards not sewing the hard part.**

This is a seventh entry for `yardstick-disagreements-2026-09-06.md`, and a
different shape from the six there: those are the metric failing to *see* an
improvement. This is the metric actively *preferring* a regression.

### Two corrections it forces

1. **MASTER_SCOPE defect 27's headline is wrong.** It reads *"on
   `gaulke_roofing` the flag alone is F 0 → C 64 … the difference between 'do
   not sew' and a usable design"*. The C 64 is a design that dropped its
   lettering onto a cone 82% as light as the ground it sits on. Corrected in
   this PR. (The F 0 vs F 4 difference is separate and benign: `main` has since
   landed the `enclosed_background` fix, #364.)

2. **My own corpus check missed it, and I can say exactly how.** The 09-04 A/B
   recorded gaulke as *"a second clear win (blocks 4→3, trims 30→18)"* — both
   true, both machine units. I checked what the flag *cost* and never checked
   **which cones survived**.

**FOUND AND FIXED, same day — and my retraction of the first account was
itself wrong.** The mechanism IS the fold, by the page-drop path, and the
probe that seemed to exonerate it was miscounting: it looked for labels whose
pixels changed LABEL, and a label sent to the page keeps its label and leaves
via `base_valid`. Counting both, **every dark label on gaulke went to the
page — 12,961 px, 50.3 mm², the 21.0 mm² wordmark included.**

The cause is one line. `valid` inside the pass is `base_valid`, which already
has the ENCLOSED pixels removed, so `~valid` is not the page — it also covers
donut holes, letter counters and the inside of a label. Gaulke is black
lettering on a white label on a black canvas: reading `~valid` as the page
told every letter it bordered the near-black background, its colour genuinely
lies between that and the label's L* 98.8 ground, and the page endpoint is the
one that DELETES rather than recolours. The pass now takes stage 1's real
background (`page_mask=~valid` at the call site, before the enclosed
subtraction).

**Gaulke's grade now reads F 4 → F 16 under all five, not C 64** — the same
answer `bind_resnap_all_classes` gives alone, from the arm that actually loads
Black. The C 64 was the dropped cone all along.

**Cost of the fix: nothing.** `logo_bridge_bar` keeps the whole win — 14,338 →
11,506 stitches, **125 → 62 trims**, 18 → 12 blocks and cones, unchanged from
before the guard — `screenshot_phone_ui` still improves (71 → 66 trims,
17 → 15 blocks), and **gaulke is now byte-identical off vs on**, dark cone
intact. The arm goes 5 fixtures moved to 4, −67 trims, and **no grade moves in
either direction** — gaulke's spurious C 64 is gone, which is the correct
outcome, not a loss.

## Per flag

**`satin_patch_junctions`** — smallest blast radius of the five (3 fixtures),
two grades up, and the cost *is* the fix: becker +383 st for the K's crotch,
the 37.2 mm² of bare cloth that is the whole reason that fixture graded B.
Nothing else in the corpus notices.

**`bind_resnap_all_classes`** — the biggest structural win: **−18 blocks and
−17 cones** across five fixtures, screenshot alone 17 → 11 blocks and 16 → 11
cones. It closes a documented escape where the operator loads a cone the plan
never names. Its F 16 on gaulke is the grader being wrong, per above — this is
the arm that puts Black on a black logo.

**`revalidate_small_shapes`** — cheapest of the five (+313 stitches over the
whole corpus), fixes sewn colour the scorecard admits it cannot rank
(yardstick row 1), one grade up. Costs: meadow +165 st / +5 trims, bridge_bar
+155 st / +1 trim.

**`satin_per_stroke`** — two grades up and −3,021 stitches, but the trim cost
is real and concentrated: **`photo_chrome_specular` 84 → 111 trims** alone,
84 → 116 under all five. Worth it on that fixture's own grade (C 64 → B 76),
and worth seeing before it becomes a default.

**`dissolve_phantom_blends`** — **the regression is fixed; this row's numbers
are the pre-fix ones.** Post-fix the arm moves 4 fixtures instead of 5:
−2,865 stitches, **−67 trims**, −8 blocks, −7 cones, no grade moving either
way, bridge_bar's 125 → 62 trims intact and gaulke byte-identical. On the
measurements it is now the cleanest of the five.

## Interaction — `all` is not the sum of the parts

Three fixtures where the combination does something no single flag does:

| fixture | singles that move it | all five |
|---|---|---|
| `photo_dof_meadow` | `resnap_small` → C 64; `satin_stroke` → C 64 | **B 76** — better than either |
| `photo_chrome_specular` | `satin_stroke` only | different result from that flag alone |
| `logo_script_tires` | `halo` only | different result from that flag alone |

So "flip these three" cannot be read off three rows, which is what this arm
existed to establish. `summit_badge`, `becker_marine_logo` and
`logo_hotel_fremont` do behave as the single flag that moves them.

## What I would do

Flip `satin_patch_junctions`, `bind_resnap_all_classes` and
`revalidate_small_shapes` — small, structural, and none of them depends on a
grade to justify it. Take `satin_per_stroke` with the chrome trim cost stated.
`dissolve_phantom_blends` was the one to hold; **its regression is now fixed
and it is a candidate again** — on the numbers, the cleanest of the five.
Strike its gaulke C 64 from the record either way: that grade was the metric
rewarding a dropped cone, and the cone is back.

All of it is Kent's call. `docs/renders/flip-sheet-2026-09-06/` has off-vs-all
sheets for gaulke, bridge_bar, chrome_specular and becker, plus the
four-arm lettering crop.
