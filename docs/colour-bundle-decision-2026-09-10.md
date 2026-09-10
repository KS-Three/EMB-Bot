# The colour bundle — one decision sheet for five flags (2026-09-10)

**Status: MEASURED 2026-09-10, nothing flipped — Kent's to default from.**
Quality review 2026-09-08 item 8, his pick after #440. Five built, default-OFF flags that each fix a piece of one problem —
cones and colour stops the customer did not ask for — priced TOGETHER on
one tree, with the render beside the number. Plan:
`docs/superpowers/plans/2026-09-10-colour-bundle.md`. Every number is one
pass of `digitizer/tools/flip_sheet.py` over the scorecard's 26 fixtures at
80 mm / `left_chest`, tree `920ebcd`; the one-flag evidence each row is
read against is `docs/pending-flag-decisions-2026-09-06.md`, itself a
reading aid for the MASTER_SCOPE defect entries (5, 15, 27, 28, 31), which
win where anything here disagrees.

**Two things are settled before any number.** `dissolve_phantom_blends` is
Kent's ruling (OFF, banked 2026-09-04); the review says *re-present, do not
re-open*, so it appears in `colour5` beside `colour4` and nowhere argues
the ruling. And a flag that removes a cone cannot be judged on its grade
(DOCTRINE: the grade is per thread on its worst patch, so deleting a cone
deletes the thread that was scoring badly) — cones and stops sit beside
every grade here, and the render beside both.

## 1. The bundle, measured as a set

**Two colour budgets, two answers.** `flip_sheet.py` prices every arm under
`PipelineConfig`'s own `max_colors` (12) — the published 2026-09-06 sheet's
yardstick — while the Studio ships **6** ("Colors (max 6)"), and for the
colour flags that is a different question: `drone_render` at 12 sews 17
cones OFF and 12 under the cap; at the Studio's 6 it sews **23 OFF and 6
under the cap**, with `COLOR_CAP_APPLIED` firing (25 → 6 region threads,
19 dropped). The tables below say which budget they are at; §1.1 is the
engine default, §1.2 the shipped one.

### 1.1 At the engine default, `max_colors` 12 — tree `920ebcd`

Net over the 26 fixtures against `off` (a fixture counts as moved when its
stitch digest differs); the singles first, then the two bundles:

| arm | moved | stitches | trims | blocks | cones | stops | grades |
|---|---:|---:|---:|---:|---:|---:|---|
| `enforce_color_cap` | 4 | −42 | −6 | −11 | **−18** | −11 | none move |
| `resnap_mask_matches_grader` | 7 | −1,151 | +7 | −6 | −5 | −6 | gaulke F 34 → D 46 |
| `revalidate_small_shapes` | 5 | +178 | −5 | +1 | +1 | +1 | meadow D 52 → C 64 |
| `bind_resnap_all_classes` | 5 | −843 | −11 | **−18** | −17 | −18 | gaulke F 34 → D 46 |
| `dissolve_phantom_blends` (ruled OFF) | 4 | **−2,874** | **−64** | −8 | −7 | −8 | none move |
| **`colour4`** (the four not ruled) | **9** | −995 | −11 | **−22** | **−22** | **−22** | chrome D 52 → C 64; meadow D 52 → C 64; gaulke F 34 → D 46; **none down** |
| **`colour5`** (`colour4` + the ruled one) | **10** | **−4,023** | **−77** | −26 | −25 | −26 | the same three up, none down |

**The bundle is not the sum of its rows, in the direction that matters.**
The cap alone removes 18 cones and the bind alone 17; together with the
mask and the floor they remove 22, not 40 — the cap and the bind take
largely the SAME cones (drone: −5 under either, −5 under both; the cone
lists differ, the count does not). Read the bundle's −22 cones / −22
stops, not the singles added up.

Per fixture, OFF and the change each arm makes (a bare `=` is
byte-identical to OFF):

| fixture (class) | OFF | colour4 | colour5 |
|---|---|---|---|
| `drone_render` (gradient) | F 0; 16,131 st, 96 tr, 17 bl, 17 cones, 16 stops | +276 st, -4 tr, -5 bl, -5 cones, -5 stops | +276 st, -4 tr, -5 bl, -5 cones, -5 stops |
| `photo_chrome_specular` (photo_scene) | D 52; 34,950 st, 89 tr, 7 bl, 7 cones, 6 stops | -101 st, +0 tr, +0 bl, +0 cones, +0 stops → C 64 | -101 st, +0 tr, +0 bl, +0 cones, +0 stops → C 64 |
| `photo_dof_meadow` (photo_scene) | D 52; 19,845 st, 40 tr, 5 bl, 5 cones, 4 stops | +47 st, -6 tr, +0 bl, +0 cones, +0 stops → C 64 | +47 st, -6 tr, +0 bl, +0 cones, +0 stops → C 64 |
| `photo_scene_stub` (photo_scene) | B 76; 16,076 st, 41 tr, 4 bl, 4 cones, 3 stops | +7 st, +3 tr, +0 bl, +0 cones, +0 stops | +7 st, +3 tr, +0 bl, +0 cones, +0 stops |
| `summit_badge` (gradient) | F 0; 17,890 st, 38 tr, 12 bl, 12 cones, 11 stops | -8 st, -1 tr, +0 bl, +0 cones, +0 stops | -8 st, -1 tr, +0 bl, +0 cones, +0 stops |
| `logo_script_tires` (photo_scene) | A 100; 2,300 st, 10 tr, 1 bl, 1 cones, 0 stops | = | -33 st, -1 tr, +0 bl, +0 cones, +0 stops |
| `logo_bridge_bar` (gradient) | F 0; 14,451 st, 127 tr, 18 bl, 18 cones, 17 stops | +109 st, +0 tr, -5 bl, -6 cones, -5 stops | -2972 st, -63 tr, -9 bl, -9 cones, -9 stops |
| `logo_gaulke_roofing` (gradient) | F 34; 10,319 st, 23 tr, 4 bl, 4 cones, 3 stops | -1241 st, +0 tr, -2 bl, -2 cones, -2 stops → D 46 | -1241 st, +0 tr, -2 bl, -2 cones, -2 stops → D 46 |
| `logo_golden_tee` (gradient) | F 0; 6,693 st, 58 tr, 15 bl, 15 cones, 14 stops | -16 st, +1 tr, -4 bl, -4 cones, -4 stops | +82 st, +3 tr, -4 bl, -4 cones, -4 stops |
| `screenshot_phone_ui_golke` (gradient) | F 0; 7,633 st, 71 tr, 17 bl, 16 cones, 16 stops | -68 st, -4 tr, -6 bl, -5 cones, -6 stops | -80 st, -8 tr, -6 bl, -5 cones, -6 stops |
| **moved / net** | 26 | **9**: -995 st, -11 tr, -22 bl, -22 cones, -22 stops | **10**: -4,023 st, -77 tr, -26 bl, -25 cones, -26 stops |

### 1.2 At the Studio's shipped `max_colors` 6 — the customer's yardstick

Same tree, same 26 fixtures, `--max-colors 6` — what the Studio's slider
promises (`build/flip_sheet_item8_mc6`):

| arm | moved | stitches | trims | blocks | cones | stops | grades |
|---|---:|---:|---:|---:|---:|---:|---|
| `enforce_color_cap` | 5 | +119 | −5 | **−38** | **−45** | **−38** | bridge F 0 → F 4; **summit F 16 → F 0** |
| `resnap_mask_matches_grader` | 8 | −1,304 | +9 | −8 | −8 | −8 | gaulke F 34 → D 46 |
| `revalidate_small_shapes` | 3 | +30 | −3 | 0 | 0 | 0 | meadow D 52 → C 64 |
| `bind_resnap_all_classes` | 6 | −1,233 | −5 | −34 | −34 | −34 | gaulke F 34 → D 46; **summit F 16 → F 0** |
| `dissolve_phantom_blends` (ruled OFF) | 4 | **−3,075** | **−62** | −2 | −2 | −2 | none |
| `mask_small` (the pair) | 9 | −1,555 | −4 | −7 | −7 | −7 | chrome D → C; meadow D → C; gaulke F → D |
| **`colour4`** | **9** | −1,352 | −14 | **−43** | **−47** | **−43** | chrome, meadow, gaulke up; **summit down** |
| **`colour5`** | **10** | **−4,509** | **−80** | −43 | −47 | −43 | the same |

**The slider becomes true.** OFF, six of 26 designs sew more cones than
the promised 6 — drone 23, Bridge Bar 13, Golden Tee 14, screenshot 14,
summit 11, and `region_blobs` 15. Under the cap alone, under `colour4`,
under `colour5`: **one of 26**, `region_blobs`, whose 15 are built in
stage-6 blend bands after the cap (defect 16's open half, on a generated
fixture no client artwork produces). Every real logo lands on exactly 6.
The cap does the lifting at this budget (−45 cones alone) and the bind
(−34) overlaps it again: −47 together.

**The one grade that falls.** `summit_badge` (a generated gradient badge)
F 16 → F 0 under the cap, under the bind, and under both: 11 → 6 cones
and a new blocking `THREAD_MATCH_POOR` — a band merged into a cone that
reads poorly on its worst patch. DOCTRINE says a cone-removing flag
cannot be judged on its grade; the new block is still a real colour
error, on synthetic art, and the only new block in the table. No client
artwork gains one (Bridge Bar gains a warning and loses
`COLOR_STOPS_HEAVY`).

Per fixture at 6:

| fixture (class) | OFF | color_cap | resnap_mask | resnap_small | resnap_bind | halo | colour4 | colour5 |
|---|---|---|---|---|---|---|---|---|
| `drone_render` (gradient) | F 0; 16,280 st, 96 tr, 23 bl, 23 cones, 22 stops | +78 st, +1 tr, -12 bl, -17 cones, -12 stops | -161 st, +1 tr, -2 bl, -2 cones, -2 stops | = | -141 st, -4 tr, -11 bl, -11 cones, -11 stops | = | -179 st, -5 tr, -15 bl, -17 cones, -15 stops | -179 st, -5 tr, -15 bl, -17 cones, -15 stops |
| `photo_chrome_specular` (photo_scene) | D 52; 34,985 st, 85 tr, 6 bl, 6 cones, 5 stops | = | = | = | = | = | -101 st, +0 tr, +0 bl, +0 cones, +0 stops → C 64 | -101 st, +0 tr, +0 bl, +0 cones, +0 stops → C 64 |
| `photo_dof_meadow` (photo_scene) | D 52; 19,845 st, 40 tr, 5 bl, 5 cones, 4 stops | = | +119 st, +5 tr, +0 bl, +0 cones, +0 stops | +52 st, +0 tr, +0 bl, +0 cones, +0 stops → C 64 | = | = | +47 st, -6 tr, +0 bl, +0 cones, +0 stops → C 64 | +47 st, -6 tr, +0 bl, +0 cones, +0 stops → C 64 |
| `photo_scene_stub` (photo_scene) | B 76; 16,076 st, 41 tr, 4 bl, 4 cones, 3 stops | = | +7 st, +3 tr, +0 bl, +0 cones, +0 stops | = | = | = | +7 st, +3 tr, +0 bl, +0 cones, +0 stops | +7 st, +3 tr, +0 bl, +0 cones, +0 stops |
| `summit_badge` (gradient) | F 16; 17,596 st, 41 tr, 11 bl, 11 cones, 10 stops | +37 st, -4 tr, -5 bl, -5 cones, -5 stops → F 0 | +33 st, +1 tr, +0 bl, +0 cones, +0 stops | = | +37 st, -4 tr, -5 bl, -5 cones, -5 stops → F 0 | = | +37 st, -4 tr, -5 bl, -5 cones, -5 stops → F 0 | +37 st, -4 tr, -5 bl, -5 cones, -5 stops → F 0 |
| `logo_script_tires` (photo_scene) | A 100; 2,300 st, 10 tr, 1 bl, 1 cones, 0 stops | = | = | = | = | -33 st, -1 tr, +0 bl, +0 cones, +0 stops | = | -33 st, -1 tr, +0 bl, +0 cones, +0 stops |
| `logo_bridge_bar` (gradient) | F 0; 14,553 st, 122 tr, 13 bl, 13 cones, 12 stops | -24 st, -3 tr, -7 bl, -7 cones, -7 stops → F 4 | -14 st, +0 tr, -3 bl, -3 cones, -3 stops | +15 st, +1 tr, +0 bl, +0 cones, +0 stops | +57 st, +3 tr, -4 bl, -4 cones, -4 stops | -3038 st, -58 tr, -2 bl, -2 cones, -2 stops | +35 st, +2 tr, -6 bl, -7 cones, -6 stops | -3082 st, -59 tr, -6 bl, -7 cones, -6 stops |
| `logo_gaulke_roofing` (gradient) | F 34; 10,319 st, 23 tr, 4 bl, 4 cones, 3 stops | = | -1241 st, +0 tr, -2 bl, -2 cones, -2 stops → D 46 | = | -1233 st, +1 tr, +0 bl, +0 cones, +0 stops → D 46 | = | -1241 st, +0 tr, -2 bl, -2 cones, -2 stops → D 46 | -1241 st, +0 tr, -2 bl, -2 cones, -2 stops → D 46 |
| `logo_golden_tee` (gradient) | F 0; 6,439 st, 59 tr, 14 bl, 14 cones, 13 stops | +39 st, +4 tr, -7 bl, -8 cones, -7 stops | +3 st, +3 tr, -1 bl, -1 cones, -1 stops | = | +107 st, +3 tr, -7 bl, -7 cones, -7 stops | +17 st, +1 tr, +0 bl, +0 cones, +0 stops | +107 st, +3 tr, -7 bl, -8 cones, -7 stops | +102 st, +3 tr, -7 bl, -8 cones, -7 stops |
| `screenshot_phone_ui_golke` (gradient) | F 0; 7,594 st, 73 tr, 14 bl, 14 cones, 13 stops | -11 st, -3 tr, -7 bl, -8 cones, -7 stops | -50 st, -4 tr, +0 bl, +0 cones, +0 stops | -37 st, -4 tr, +0 bl, +0 cones, +0 stops | -60 st, -4 tr, -7 bl, -7 cones, -7 stops | -21 st, -4 tr, +0 bl, +0 cones, +0 stops | -64 st, -7 tr, -8 bl, -8 cones, -8 stops | -66 st, -11 tr, -8 bl, -8 cones, -8 stops |
| **moved / net** | 26 | **5**: +119 st, -5 tr, -38 bl, -45 cones, -38 stops | **8**: -1,304 st, +9 tr, -8 bl, -8 cones, -8 stops | **3**: +30 st, -3 tr, +0 bl, +0 cones, +0 stops | **6**: -1,233 st, -5 tr, -34 bl, -34 cones, -34 stops | **4**: -3,075 st, -62 tr, -2 bl, -2 cones, -2 stops | **9**: -1,352 st, -14 tr, -43 bl, -47 cones, -43 stops | **10**: -4,509 st, -80 tr, -43 bl, -47 cones, -43 stops |

## 2. Each flag, alone and inside the set

Each flag's one-flag evidence is in `docs/pending-flag-decisions-2026-09-06.md`
and the defect entries; this is what the SET says about each, on this
tree, at the engine default budget (the shipped budget's rows are in
§1.2 and change the cap's line most).

- **`enforce_color_cap`** — buys cones on exactly the four gradient-lane
  real logos over budget (drone −5, bridge −6, golden tee −3, screenshot
  −4) at −42 stitches and no grade move; inside `colour4` its cones are
  mostly the bind's cones too (drone: −5 either way, −5 together), so the
  set credits the pair once. **Its promise is the shipped budget's (§1.2):
  at 12 it merges 17 → 12 on drone; at the Studio's 6, 23 → 6.** Not moot
  under item 1: forced flat it still takes 21 cones off drone and Golden
  Tee (§3). The catch is the one
  the 2026-09-07 render showed: it merges colours a customer can see.
- **`resnap_mask_matches_grader`** — the widest single (7 fixtures);
  gaulke's F 34 → D 46 is its (and the bind's — either alone gets there,
  by different geometry). −1,151 stitches, +7 trims, −5 cones. It survives
  item 1: the mask gap is lane-independent. Inside the set it is one of
  the two flags that move `photo_dof_meadow`; see the pair below.
- **`revalidate_small_shapes`** — the only single that costs cones (+1,
  drone: a shard lands on a cone the shipped pass vacates) and the only one
  that moves a photo grade alone (meadow D 52 → C 64). +178 stitches. It
  survives item 1. Inside the set the +1 cone disappears (drone −5 under
  `colour4`) because the bind takes the shard's escape with the others.
- **`bind_resnap_all_classes`** — the biggest single on blocks and stops
  (−18 / −18, five gradient-lane fixtures), gaulke F 34 → D 46, −843
  stitches; drone pays +401 stitches for it alone and +276 inside the set.
  Not moot under item 1: it is the flat lane's main worker, −26 cones on
  five logos forced flat (§3). The price the 2026-09-06 sheet named — "+2 blocks net" — is not
  on this tree: −18 blocks, nothing up anywhere.
- **`dissolve_phantom_blends`** — ruled OFF; re-presented, not re-opened.
  On this tree it is the stitch and trim lever: Bridge Bar −2,936 stitches
  and **−63 trims** alone, and `colour5` over `colour4` is −3,028 stitches,
  −66 trims, −4 blocks, −3 cones for the one ruled flag. `logo_script_tires` moves
  under it (−33 stitches, −1 trim, A 100 kept). Its two mild negatives
  from 2026-09-04 are not re-argued here; the number is beside the ruling
  so the ruling can be re-read against the current tree, which is what
  "re-present" means.

**The pair that moves a fixture no single moves.** `photo_chrome_specular`
goes D 52 → C 64 under `colour4` (−101 stitches) while every single leaves
it byte-identical — the flip sheet's own thesis in one row. It is the pair the published sheet isolated
as `mask_small`: `resnap_mask_matches_grader` shrinks a footprint below
`revalidate_small_shapes`' 200 px floor, so alone it declines the shape;
the lowered floor lets it act. Run here on this tree, `mask_small` alone
reproduces chrome's move byte for byte (−101 stitches, D 52 → C 64) and
meadow's bundle geometry too (+47 stitches, −6 trims, where the mask
alone is +119 / +5 and the floor alone +52 / 0). The two flags are one
decision: flip both or neither.

**Nothing goes down.** No fixture loses a grade letter under `colour4` or
`colour5`, and no single takes any fixture down; the 2026-09-06 sheet's one
falling grade (`logo_script_tires` under `halo` + `satin_patch`) needed
the satin patch, which is not in this bundle.

## 3. What item 1 would make moot — the lane question, stated then measured

Item 1 (the real-logo lane, designed and gate-2 blocked in
`docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`)
would route real logos to the FLAT lane. From each flag's own docstring,
which lane it acts on:

| flag | acts on | under item 1 (real logos on the flat lane) |
|---|---|---|
| `enforce_color_cap` | the SLIC+RAG (gradient/photo) lane, whose `max_k` is a clustering parameter and not a cap; `stage2_quantize` (flat) has always capped hard | the docstring says moot (the flat lane caps its REGION threads) — but the sewn count escapes past that cap on the flat lane too; measured below |
| `dissolve_phantom_blends` | the gradient/photo lane's merged labels; the flat lane has always dissolved them | moot for real logos — measured: byte-identical on all nine forced flat |
| `bind_resnap_all_classes` | `revalidate_threads`' argmin on every class; every counted escape was on the gradient lane (34 cones, 25 outside the palette) | the docstring says moot in practice — the count was over ROUTED fixtures; forced flat the escape is there (Golden Tee 24 cones under 12); measured below |
| `resnap_mask_matches_grader` | the pixels `revalidate_threads` scores, on any lane | survives — the mask gap is lane-independent |
| `revalidate_small_shapes` | `revalidate_threads`' pixel floor, on any lane | survives |

Measured by proxy — `forced_class=flat` on every fixture, the bundle
against that baseline rather than against `off` (`flat_colour5` vs
`flat_off`). The proxy is NOT item 1: forcing flat drops the thin strokes
item 1 lands with (`keep_thin_strokes`), so it answers one question only —
does the bundle still have work to do on the flat lane?

`flat_colour5` against `flat_off`, the nine real-logo fixtures (the
seven client logos, drone and ENTHUSIAST), engine budget 12:

| fixture | `flat_off` | `flat_colour5` |
|---|---|---|
| `drone_render` | F 0; 25,449 st, 361 tr, 21 cones, 20 stops | +11 st, −3 tr, **−9 cones**, −9 stops |
| `logo_bridge_bar` | F 0; 15,778 st, 170 tr, 9 cones, 8 stops | −43 st, −7 tr, −1 cone, −1 stop |
| `logo_gaulke_roofing` | F 0; 9,964 st, 32 tr, 5 cones, 4 stops | −8 st, −1 tr, −2 cones, −2 stops → F 16 |
| `logo_golden_tee` | F 0; 9,082 st, 134 tr, **24 cones**, 23 stops | +34 st, +4 tr, **−13 cones**, −13 stops |
| `screenshot_phone_ui_golke` | F 0; 10,336 st, 115 tr, 11 cones, 10 stops | −40 st, +0 tr, −3 cones, −3 stops |
| ENTHUSIAST, Becker, script tires, Fremont | — | byte-identical |
| **net, 9 logos** | | **5 moved: −46 st, −7 tr, −28 blocks, −28 cones, −28 stops** |

**The lane story above is wrong on its bind row, and the measurement is
what says so.** Forced flat, Golden Tee sews **24 cones under a budget of
12** and drone 21: the flat lane's hard cap holds stage 2's REGION threads
to the budget, and the re-snap then escapes past it exactly as on the
gradient lane — "every counted escape was on the gradient lane" was a
count over ROUTED fixtures, where every real logo is gradient. So item 1
does not make the bundle moot: on the flat lane it still takes 28 cones
and 28 stops off five of the nine logos, and the customer's slider is
still not true there without it. Which of the five does that work on the
flat lane —

| fixture (forced flat) | `flat_off` | `flat_color_cap` | `flat_resnap_mask` | `flat_resnap_small` | `flat_resnap_bind` | `flat_halo` | `flat_colour5` |
|---|---|---|---|---|---|---|---|
| `drone_render` | 21 cones, 20 stops | **−9 cones** | +1 cone | = (+8 st) | −7 cones | = | −9 cones |
| `logo_bridge_bar` | 9 / 8 | = | −1 cone, −7 tr | = | −1 cone, −7 tr | = | −1 cone, −7 tr |
| `logo_gaulke_roofing` | 5 / 4 | = | −1 cone | = | −2 cones → F 16 | = | −2 cones → F 16 |
| `logo_golden_tee` | **24** / 23 | **−12 cones** | −3 cones | = | **−13 cones** | = | −13 cones |
| `screenshot_phone_ui_golke` | 11 / 10 | = | = | = | −3 cones | = | −3 cones |
| **net, 9 logos** | | **2 moved, −21 cones** | 5 moved, −4 | 1 moved, 0 | **5 moved, −26 cones** | **0 moved** | 5 moved, −28 |

the singles say (engine budget 12, the five logos the bundle moves; the
other four are byte-identical under every arm): **the bind does most of
the flat-lane work** (−26 cones on five logos) and **the cap does the
rest** (−21 on drone and Golden Tee — so the cap is NOT the flat lane's
own behaviour: forced flat, drone sews 21 cones under a budget of 12
and the flag takes nine off), overlapping to −28 together; the mask
takes four, the floor none, and **`dissolve_phantom_blends` is the one
flag item 1 retires** — byte-identical on all nine forced flat, exactly
as its docstring says (the flat lane has always dissolved them).

(Forced flat is also the expensive lane on these logos — drone 25,449
stitches and 361 trims against 16,131 and 96 routed — which is item 1's
own problem, the one its thin-stroke half exists for; it does not change
the cone reading.)

The same pair at the Studio's 6 — the flat lane's own cap holds region
threads to six, and the sewn count still escapes to 23 and 28:

| fixture (class) | OFF | flat_colour5 |
|---|---|---|
| `drone_render` (flat) | F 0; 21,367 st, 168 tr, 23 bl, 23 cones, 22 stops | -33 st, -10 tr, -16 bl, -17 cones, -16 stops |
| `logo_bridge_bar` (flat) | F 0; 13,305 st, 108 tr, 8 bl, 8 cones, 7 stops | -23 st, -3 tr, -2 bl, -2 cones, -2 stops |
| `logo_gaulke_roofing` (flat) | F 34; 9,745 st, 24 tr, 5 bl, 5 cones, 4 stops | -8 st, -1 tr, -2 bl, -2 cones, -2 stops → F 16 |
| `logo_golden_tee` (flat) | F 0; 8,328 st, 111 tr, 28 bl, 28 cones, 27 stops | -115 st, -7 tr, -21 bl, -22 cones, -21 stops |
| `screenshot_phone_ui_golke` (flat) | F 0; 10,339 st, 129 tr, 8 bl, 8 cones, 7 stops | +52 st, +7 tr, -2 bl, -2 cones, -2 stops |
| **moved / net** | 26 | **5**: -127 st, -14 tr, -43 bl, -45 cones, -43 stops |

## 4. Renders — looked at

`docs/renders/colour-bundle-2026-09-10/<fixture>_off-colour4-colour5.jpg`:
for each of the ten fixtures `colour5` moves, the design drawn in the
thread colours it sews (`tools/thread_color_render.py`'s panel, the
artwork faded behind), OFF beside `colour4` beside `colour5`, every shape
whose cone changed circled and labelled `old -> new`. Looked at, at the
engine default budget:

- **Bridge Bar** (18 → 12 → 9 cones; 127 → 127 → 64 trims). `colour4`
  takes the six escaped greys off the wheel without changing what you
  see; `colour5` is the visible one: the pale-pink phantom outline around
  the red *Bridge* script is gone, the script sews solid red, and the
  bottom-right spoke that OFF sews in a grey ghost thread sews black like
  its seven siblings. That is `dissolve_phantom_blends` doing on this
  JPEG exactly what its docstring says (the ringing around the black
  spokes sewn as grey threads), and it is the render Kent's 2026-09-04
  ruling was made without — the flag was broken then (#380).
- **drone** (17 → 12 cones, 16 shapes re-coned). The blue, orange and
  black body is untouched; what moves is the grey of the PRECISION
  lettering and the AND DRONE tagline (`1565 → 2564`, `0145 → 3971`), one
  grey for another. Reads the same at 80 mm.
- **screenshot** (16 → 11 cones, 19 shapes). The phone chrome — the
  battery glyph, the blue toolbar icons, the truck's small white and grey
  parts — lands on neighbouring cones; the truck and the two lines of
  lettering are the same. The `3971` spool loaded twice under OFF is
  loaded once.
- **gaulke** (4 → 2 cones). Two greys instead of four on the same
  grey-on-white card; nothing separates at this scale. (Its lettering
  sews grey where the artwork is black because the black frame makes
  stage 1 call the inside "enclosed background" — review item 9, not
  this bundle's.)
- **golden tee, summit badge, the three photo fixtures, script tires**:
  cone swaps inside shapes of the same hue family, or (script tires) a
  halo dissolve that changes no cone; none reads differently.

Nothing in the ten sheets looks like a colour a customer would miss; the
one visible change (Bridge Bar's halo) is an improvement. That is a
reading at 80 mm on a screen — the sheets are there for Kent's eye, which
is the part of this decision that is his.

## 5. Recommendation, one line per flag — Kent's to accept or refuse

One line per flag, the catch beside it, at the Studio's shipped budget:

1. **`enforce_color_cap` — flip ON.** The only flag with a broken promise
   behind it, and at 6 it keeps that promise alone: 45 cones off five
   designs, every real logo on exactly 6, `COLOR_CAP_APPLIED` telling the
   customer why. Catch: it merges colours a customer can see (the sheets
   in §4, at 12; the 6-budget sheets below them once rendered), and it
   puts one new `THREAD_MATCH_POOR` block on a synthetic badge. The
   residual (`region_blobs`, blend bands) is defect 16, not this flag.
2. **`resnap_mask_matches_grader` + `revalidate_small_shapes` — flip
   TOGETHER or not at all.** The pair moves chrome and meadow D → C and
   gaulke F → D, −7 cones at 6, nothing down; either alone is half of it
   or declines. Catch: a scorecard recapture (the phase-4 spec pins the
   flat and gradient goldens byte for byte) — on ubuntu CI, never here.
3. **`bind_resnap_all_classes` — flip ON.** −34 cones / −34 stops at 6
   across six fixtures, gaulke F 34 → D 46, `3971` loaded once instead
   of twice on screenshot; and item 1 does not retire it (§3). Catch:
   the same synthetic block as the cap; the 2026-09-06 sheet's "+2 blocks
   net" price is not on this tree (−34).
4. **`dissolve_phantom_blends` — Kent's ruling stands; the render it
   lacked is on file.** At 6 it is −3,082 stitches and −59 trims on
   Bridge Bar and −4,509 / −80 over the set; the sheet shows the phantom
   halo gone. The 2026-09-04 negatives are unchanged and not re-argued.
   Re-read, or leave banked.
5. **Order against item 1: nothing here waits.** If the real-logo lane
   lands first, only the dissolve becomes the flat lane's own behaviour
   on real logos; the cap, the bind and the mask keep their work there
   (§3: −21, −26 and −4 cones forced flat).

**What I would do:** flip the four not ruled as one set (`colour4`) and
put the fifth to Kent's re-read of the Bridge Bar sheet — not because
the number is small (it is the largest stitch and trim lever here) but
because it is his ruling to re-read.

*(measured 2026-09-10 — `digitizer/build/flip_sheet_item8` on `920ebcd`;
`tools/flip_sheet.py report`; the plan doc's §4 carries the same numbers)*
