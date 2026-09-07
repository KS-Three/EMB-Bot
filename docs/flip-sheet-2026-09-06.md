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
| **all five** | **12/26** | **−6,070** | −24 | **−23** | **−22** | **5 up** |

**No grade moves DOWN in any arm, on any fixture.** Fourteen of 26 fixtures are
byte-identical even with all five on.

## The finding that changes the decision

**On `logo_gaulke_roofing` the grade ranks the arms backwards, and it is my
own flag that it rewards for the wrong thing.**

The artwork is black lettering on a white label. What each arm actually loads:

| arm | cones (L\*) | darkest thread | grade |
|---|---|---:|---|
| off | White 100, Ghost White 91.8, **Dark Charcoal 15.9**, Silver 82.0 | **L\* 15.9**, 288 st | F 4 |
| `dissolve_phantom_blends` | White 100, Glacier Green 96.7, Skylight 85.7 | L\* 85.7 | **C 64** |
| `bind_resnap_all_classes` | White 100, Skylight 85.7, Charcoal 36.1, **Black 0.0** | **L\* 0.0** | F 16 |
| all five | White 100, **Silver 82.0** | L\* 82.0 | **C 64** |

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

**The OUTCOME is verified; the MECHANISM offered for it is NOT, and the probe
argues against it.** Re-measured on `main` at `258f8e1` (a different main from
the sheet's `8c7edf7`, so the outcome holds twice): OFF sews `1375 Dark
Charcoal` (L* 15.9, 288 st) and ON sews nothing below `0145 Skylight`
(L* 85.7). But the first explanation — that `_blend_ramp` mistakes
anti-aliased black text for ringing — does not survive instrumenting the pass.
At gaulke's 16 px/mm the fold takes **9 labels, every one 0.4-0.6 mm²**, while
every lettering label (L* 28-47, the largest 21 mm²) survives stage 2, and
`result.palette` carries `0020 Black` in BOTH arms. **The dark cone is lost
between stage 2 and the sewn block list, not by the fold.** Where, is open.
Do not repeat the anti-aliasing story as fact until someone finds it.

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

**`dissolve_phantom_blends`** — the one I would now hold. Its corpus numbers
are the best in the table (−76 trims, bridge_bar 125 → 62) and its gaulke
result is a regression the grade calls a win. What the fix IS remains open —
the fold itself is not doing it (retraction above), so the next step is
finding where between stage 2 and the block list gaulke's dark cone goes.

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
**Hold `dissolve_phantom_blends`** — not for the reason first given (that
guess is retracted above) but because the outcome is real and unexplained:
something between stage 2 and the block list drops gaulke's dark cone when
this flag is on. Strike its gaulke grade from the record either way.

All of it is Kent's call. `docs/renders/flip-sheet-2026-09-06/` has off-vs-all
sheets for gaulke, bridge_bar, chrome_specular and becker, plus the
four-arm lettering crop.
