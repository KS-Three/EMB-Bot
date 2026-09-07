# The five parked flags, measured together — 2026-09-06

A decision sheet for the flags that are built, measured and still OFF. Every
number is one pass of `digitizer/tools/flip_sheet.py` over the scorecard's own
26 fixtures at 80 mm / `left_chest`. **Twelve arms**: the shipped default,
each flag alone, all five together, the combinations someone would actually
ship (`rec3`, `rec4`, `rec4_mask`, `halo_patch`), and a **sixth parked flag**,
`resnap_mask_matches_grader`, which did not exist when this sheet was written
— all five added 2026-09-07.

**Every number below is post-fix**, on `20fa551` for the six original arms and
`50f103e` for the combinations added 2026-09-07; the two trees are verified
identical wherever they overlap (see "Provenance" at the end — 104 rows
compared, 0 differ). The sheet found a regression in `dissolve_phantom_blends`
on its first pass; that flag is fixed and re-measured, and the history is in
"What this sheet went through" at the end rather than interleaved with the
numbers. Read the tables as current.

**Two things the first version of this sheet asserted are settled below rather
than in a changelog**, because a reader deciding a flip needs them where the
claim was. One was WRONG: the yardstick finding it drew from
`logo_gaulke_roofing` — retracted 2026-09-07, it was the bug's artifact, not
the metric's preference. One was merely UNMEASURED: its own three-flag
recommendation, which the sheet's own header warns cannot be read off three
rows. Measured now, and it holds — better than it claimed.

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
| `resnap_mask_matches_grader` † | 7/26 | −1,715 | +2 | −5 | −4 | gaulke F 4 → **D 46** |

† **The sixth flag, added 2026-09-07 and NOT part of "all five" above.** The
thread re-validation was scoring its argmin on a raw `cv2.fillPoly` footprint
while the grader erodes one pixel and drops the background, so on a thin shape
the re-snap picked a thread for the anti-alias halo — `logo_gaulke_roofing`'s
`Se6eddd27` reads **11.4 dE00** to stage 4 and **63.6** to preflight, a 52.2
gap on one polygon. It is also a second cause of the resnap escape: gaulke's
plan palette goes 4 → 2 because `1375` and `3971` were only ever reached for
halo pixels. No grade moves down anywhere. MASTER_SCOPE 28.

**No grade moves down in any SINGLE-flag arm.** The combination is the
exception, and finding it is what the `all` arm is for: with all five on,
`logo_script_tires` goes **A 100 → B 88** (trims 8 → 12) — a fixture no single
flag takes below A. Fourteen of 26 are byte-identical even with all five on.
**It is a two-flag interaction and it is named below** — `halo` +
`satin_patch`, which alone reproduces the all-five result exactly.

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

### The one grade that falls is a PAIR, and it is nameable

All ten pairs of the five, measured on `logo_script_tires`
(2026-09-07): **exactly one moves it, and it reproduces the all-five result
exactly** — `dissolve_phantom_blends` + `satin_patch_junctions`, B 88, 12
trims, 2,394 stitches, the same three numbers the five-flag arm produces. The
other three flags contribute nothing to it. So this is a two-flag
interaction, not an emergent five-way, and the mechanism is visible in the
run set rather than inferred:

| arm | satin runs | fill runs | underlay | trims | stitches |
|---|---:|---:|---:|---:|---:|
| off | 7 | 1 | 12 | 8 | 2,340 |
| `dissolve_phantom_blends` | **9** | 1 | 14 | 9 | 2,256 |
| `satin_patch_junctions` | 7 | 1 | 12 | 8 | 2,340 — byte-identical to off |
| both | 9 | **5** | 14 | **12** | 2,394 |

`satin_patch_junctions` is not inert on this fixture — **it is inert on the
geometry `off` produces.** The halo pass splits the script into two more satin
strokes, and the patch pass then finds junctions between strokes that do not
exist without it: four extra fill runs, three of them carrying a trim.

**The patches are real work, not waste.** Preflight's own coverage instrument
puts the worst uncovered patch at **2.8 mm² under `halo` alone and 0.8 mm²
under both** — the halo pass opens a small hole at the new junction and the
patch pass closes it.

**And the grade fall is a threshold crossing that `halo` alone sets up.**
`TRIM_HEAVY` fires on trims per 1,000 stitches against a ceiling of 4.1:

    off    8 / 2,340  = 3.42   0.68 under
    halo   9 / 2,256  = 3.99   0.11 under
    both  12 / 2,394  = 5.01   OVER

`dissolve_phantom_blends` alone spends **96.5% of this fixture's trim budget**
and still reads A 100. Anything that adds a trim after it trips the warn;
`satin_patch_junctions` is simply the flag that does. Read the risk as
"`halo` leaves tires with no headroom", not "these two flags are
incompatible".

**What it costs to take both anyway:** 4 trims and 138 stitches on one
fixture, to close a 2 mm² hole and drop a warn-level finding. Small either
way — but it is the only grade any arm takes down, so it should be a choice
rather than a surprise.

## Costs named rather than netted

The −28 net trims on the all-five arm hides `photo_chrome_specular` at
84 → 116. `satin_patch_junctions` costs becker +383 stitches, which *is* the
fix. `logo_script_tires` is the only fixture any arm takes down a grade.

## The combinations someone would actually ship — measured 2026-09-07

Nobody flips all five. **This sheet's own recommendation was three flags
nobody had run together**, which is precisely the error the header above warns
against, so they are arms now:

| arm | flags | moved | stitches | trims | blocks | cones | grades |
|---|---|---:|---:|---:|---:|---:|---|
| **`rec3`** | patch + bind + resnap | 9/26 | +413 | **+1** | **−18** | **−17** | **4 up, 0 down** |
| **`rec4`** | `rec3` + `satin_per_stroke` | 11/26 | **−2,814** | +34 | −18 | −17 | **5 up, 0 down** |
| `halo_patch` | halo + patch | 6/26 | −1,997 | −55 | −8 | −7 | 2 up, **1 down** |
| all five | | 12/26 | −5,719 | −28 | −21 | −20 | 5 up, **1 down** |

**`rec3` costs +413 stitches and ONE trim across the whole corpus** — **+0.13%**
of its 315,371 stitches — and buys −18 blocks, −17 cones and four grades up: becker
B 76 → B 88, gaulke F 4 → F 16, `photo_dof_meadow` D 52 → C 64,
`photo_scene_stub` B 76 → B 88. Nothing anywhere goes down.

**`rec4` adds `satin_per_stroke` and is still regression-free**: it turns the
+413 into **−2,814 stitches** (−0.89%), lifts `photo_chrome_specular`
C 64 → B 76, and carries `photo_dof_meadow` further than `rec3` does —
**D 52 → B 76** against `rec3`'s D 52 → C 64. The cost is +33 trims,
concentrated on chrome (84 → 116). Five grades up, none down.

**Everything that falls, falls because of `dissolve_phantom_blends`.** It is
the only flag not in `rec4`, and adding it (= all five) buys a further −2,905
stitches and −62 trims — bridge_bar's 125 → 62 is most of it — at the cost of
the one grade in the corpus that any arm takes down. That is now a two-row
read rather than a judgement call.

## What I would do

**Flip `rec4_mask`** — `rec4` plus the sixth flag, measured 2026-09-07 as its
own arm rather than inferred:

| arm | moved | stitches | trims | blocks | cones | grades |
|---|---:|---:|---:|---:|---:|---|
| `rec4` | 11/26 | −2,814 | +34 | −18 | −17 | 5 up, 0 down |
| **`rec4_mask`** | 11/26 | **−2,965** | **+32** | **−22** | **−21** | **5 up, 0 down** |

The sixth flag is **strictly additive on top of the recommendation**: the same
eleven fixtures move, every axis improves, and `logo_gaulke_roofing` goes
F 4 → **D 46** instead of stopping at F 16. Nothing goes down anywhere.

Seven fixtures are moved by both parts, so this could not have been read off
the two rows — which is why it is an arm.

### The mask and the floor are a matched pair — priced

`resnap_mask_matches_grader` shrinks the re-snap's footprint below its own
200-px floor (gaulke 247 → 54, bridge_bar 240 → 156), so **on its own it makes
the pass DECLINE regions rather than re-snap them better.**
`revalidate_small_shapes` is what lets it act. Measured as its own arm
2026-09-07, because `rec4_mask` carries three other flags and cannot price it:

| arm | moved | stitches | trims | blocks | cones | grades |
|---|---:|---:|---:|---:|---:|---|
| `resnap_mask_matches_grader` | 7/26 | −1,715 | +2 | −5 | −4 | gaulke F 4 → D 46 |
| `revalidate_small_shapes` | 5/26 | +313 | +6 | +1 | +1 | meadow D 52 → C 64 |
| **`mask_small`** | 8/26 | −1,181 | **+0** | −5 | −4 | **both, 0 down** |

The pair collects **both** grade improvements and the two trim costs cancel to
**exactly zero**. Nothing goes down.

**But read the last column honestly: the pair buys no grade the two do not
buy separately.** Its distinctive win is mechanical and invisible here —
`logo_bridge_bar`'s `S880e5dff` is the one region only the pair reaches, and it
re-snaps `6156 Olive` → `5866`, **21.3 → 16.2 dE00**, on a fixture that scores
**exactly 0 either way**. That is `yardstick-disagreements` row 6 again: the
design is hundreds of points under water, so a real thread fix has nowhere to
show. Judge this pair on the ΔE00 and the cone list, not on its grade column.

If the chrome trim cost (84 → 116) is unwelcome, drop `satin_per_stroke` and
keep four grades up for +1 trim corpus-wide.

**Hold `dissolve_phantom_blends` a little longer, but not for its own sake.**
On its own it is the cleanest of the five (−67 trims, no grade moving either
way, bridge_bar 125 → 62). What argues for waiting is that it is the flag that
makes `logo_script_tires` trip `TRIM_HEAVY` once anything else is on, and the
sheet can now say exactly why (3.99 against a 4.1 ceiling). Flipping it
together with `rec4` is a defensible call with that number in hand — it is
one warn on one fixture against −62 trims corpus-wide — but it should be
chosen, not inherited.

All of it is Kent's call. `docs/renders/flip-sheet-2026-09-06/` has off-vs-all
sheets for gaulke, bridge_bar, chrome_specular and becker, plus a four-arm
lettering crop.

## Provenance — verified, not assumed

The first pass of this sheet was cached before `dissolve_phantom_blends` was
fixed; the two affected arms were re-measured into a second directory, and the
table above draws rows from both. That was sound, and it is now **measured
rather than inferred**: all 26 `off` rows are byte-identical across the two
trees (so the flag gate provably holds), and re-measuring the four
fix-unaffected single arms on the current tree reproduces the old cache
exactly — **104 rows compared, 0 differ**. `flip_sheet.py` stamps `head` into
every row from 2026-09-07 so the next reader does not have to take this on
trust.

---

## What this sheet went through

Kept because the sequence is the useful part, and because two of its three
steps were wrong in ways worth not repeating.

### The yardstick finding, which did NOT stand

**Retracted 2026-09-07 — kept because the retraction is the finding.** Read
this table as a measurement of the PRE-FIX tree, which is what it was.

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
thread — **the metric rewards not sewing the hard part.**

**On the fixed tree that disagreement is gone.** `dissolve_phantom_blends` is
byte-identical to `off` on gaulke now (F 4, `1375 Dark Charcoal`), and the two
arms that load `0020 Black` grade F 16 — every arm loading real Black grades
HIGHER than every arm that does not. The C 64 rows were the dropped ink, not
the metric's preference. Swept across all seven arms × 26 fixtures on the fixed
tree, **ten (arm, fixture) pairs remove a cone and not one scores higher**, and
all ten sit on fixtures scoring exactly 0 in both arms — so row 6's floor is
now why this question cannot be asked of this corpus at all.
`yardstick-disagreements` row 7 is retracted with that trail.

What survives is the rule that caught the bug: **on a fixture where a flag
removes a cone, the grade is not evidence of anything and the cone list is.**

It also forced a retraction in MASTER_SCOPE defect 27, which had read *"gaulke
F 0 → C 64 … the difference between 'do not sew' and a usable design"* about a
design that had dropped its ink.

**So this table did its job twice over and was wrong about why.** Measuring
cones instead of grades found a real bug; the conclusion drawn from it — that
the metric prefers a dropped cone — was the bug's own artifact. The habit is
sound, the ruling was not.

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
