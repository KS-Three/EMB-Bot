# The gradient-lane colour bundle, decided as one set — item 8

**Status: IN MEASUREMENT 2026-09-10, Kent's pick after #440. No engine
change: five built, default-OFF flags priced TOGETHER, one decision doc.**

## 0. What already governs this — read before changing the plan

- **The five flags** (review §8), each built, byte-identical off, measured
  alone, DEFAULT OFF: `enforce_color_cap` (MASTER_SCOPE 31),
  `resnap_mask_matches_grader` (28), `revalidate_small_shapes` (28),
  `bind_resnap_all_classes` (15), `dissolve_phantom_blends` (27). Their
  one-flag evidence is gathered in `docs/pending-flag-decisions-2026-09-06.md`;
  the defect entries win where they disagree.
- **`dissolve_phantom_blends` is RULED, not pending.** Kent saw the render
  and banked it OFF 2026-09-04 on two mild negatives and the five-of-six
  residual; the one datum that looked like it re-opened the ruling (gaulke
  F 0 → C 64) was the flag deleting the lettering and is retracted (#380,
  DOCTRINE 2026-09-07). The review's instruction is *re-present, do not
  re-open*: the bundle is priced WITH and WITHOUT it, and the doc says so
  beside the number. Nothing here argues the ruling.
- **`tools/flip_sheet.py` is the instrument this asks for.** It already
  prices arms across the scorecard's 26 fixtures at 80 mm / `left_chest`
  in stitches, trims, blocks, cones and grade, caches one JSON per
  (fixture, arm), stamps the tree into every row, and has the interaction
  and combination tables (a combination is not the sum of its rows — its
  own thesis, proven on `halo + satin_patch`). Its published sheet is
  `docs/flip-sheet-2026-09-06.md`. What it lacks for this item: a
  `color_cap` arm (the cap landed the same day the sheet did, priced by
  `tools/color_cap.py` instead), the colour bundle as arms, and the colour
  STOP count in the report (`changes` is recorded, never printed — and it
  is the number the operator pays: a stop is a re-thread on a single-needle
  machine, a cone is a spool to buy).
- **The grade floor.** Twelve of the corpus's combos score exactly 0 with
  unclamped scores from −272 to −38, and `THREAD_MATCH_POOR` grades per
  thread on its worst patch — so a flag that deletes a cone deletes the
  thread that was scoring badly. DOCTRINE: *a flag that removes a cone
  cannot be judged on its grade; check the cone list.* Every table here
  carries cones and stops beside the grade, and the render beside both.
- **Item 1 (the real-logo lane) is DESIGNED and BLOCKED, not built**
  (`docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`;
  gate 2). It would route real logos to the FLAT lane. Which of the five
  that makes moot is a fact about lanes, stated from the flags' own
  docstrings and then MEASURED (§2): the flat lane already caps colours
  hard (`stage2_quantize`) and has always dissolved phantom blends; every
  counted re-snap escape is on the gradient lane; the mask and the
  small-shape floor act in `revalidate_threads` on any lane.
- **Gate 4.** Grades ride beside stitches, trims, blocks, cones and stops;
  no claim rests on the grade alone.

## 1. The gap

Five flags fix five pieces of one customer-visible problem — cones and
stops the customer did not ask for (`drone_render` sews 22 cones against a
promised 6; `screenshot` loads `3971` twice) — and each has been decided,
or parked, on its own row. Nobody has priced the set: four of the five
move the region set or the thread assignment on the same lane, so the
bundle is not the sum of its rows, in either direction. A decision needs
one table, one render per fixture, and one sentence per flag about what
item 1 would do to it.

## 2. The measurement

Arms added to `flip_sheet.py` (every other arm untouched, so the published
sheet's rows stay comparable):

| arm | flags |
|---|---|
| `color_cap` | `enforce_color_cap` — the missing single |
| `colour4` | cap + mask + small + bind — the four NOT ruled |
| `colour5` | `colour4` + `dissolve_phantom_blends` — the review's table, re-presented |
| `flat_off` | `forced_class=flat`, nothing else — the item-1 proxy's baseline; PROXIES, not ARMS |
| `flat_colour5` | `forced_class=flat` + all five — what survives once real logos take the flat lane |
| `mask_small` (existing) | mask + floor — the pair the published sheet isolated; run here because one bundle-only grade move needed attributing |

The report gains `stops` (colour changes) in every net line and reads the
proxy pair against `flat_off`, never against `off`. Per fixture and per
arm the sheet prints stitches, trims, blocks, cones, stops and grade; the
interaction table says where the bundle is not the union of its parts.

**Two things the measurement changed on contact.** (1) The proxy pair
runs on the NINE real-logo fixtures only (`--fixture`, added for it):
forcing the flat lane on a photograph took ten minutes a fixture and
answers nothing about item 1, which is a question about logos. (2) Every
arm runs at TWO colour budgets: `PipelineConfig`'s own `max_colors` (12,
the published sheet's yardstick) and the Studio's shipped 6
(`--max-colors`, added for it; every row records its budget). For the
colour flags the two are different questions — drone at 6 sews 23 cones
OFF and 6 under the cap; at 12, 17 and 12.

**Forced flat is a proxy for item 1, not item 1**: it drops Fremont's
rope and EST 1895 (`DROPPED_SMALL_SHAPES`) where item 1 lands with the
thin-stroke flag. The proxy answers one question only — *does the flag
still have work to do on the flat lane?* — and the doc says that beside
every flat row.

## 3. The render

`tools/thread_color_render.py` draws a design in the thread colours it
sews and circles the shapes whose cone a flag changes; it takes one flag.
It grows a repeatable `--flag` so the bundle renders as one ON panel, and
`docs/renders/colour-bundle-2026-09-10/` holds one contact sheet per
fixture the bundle moves — OFF beside `colour4` beside `colour5`, each
changed cone circled, downscaled to a JPEG of a few hundred KB (the full
panels stay out of the repo) — because the look is the part of this
decision that is Kent's.

## 4. Results — measured 2026-09-10 (the decision doc carries the tables)

Tree `920ebcd` (main with #439 and #440), 26 fixtures at 80 mm /
`left_chest`, `build/flip_sheet_item8` (engine budget 12) and
`build/flip_sheet_item8_mc6` (the Studio's 6).

- **At the engine default (12)**: the five singles move 4–7 fixtures
  each; `colour4` moves 9 for −995 stitches, −11 trims, **−22 blocks,
  −22 cones, −22 stops**, three grades up and none down; `colour5` moves
  10 for −4,023 stitches, **−77 trims**, −26 / −25 / −26 — the ruled flag
  is the stitch and trim lever (Bridge Bar alone −2,936 / −63). The
  bundle is not the sum of its rows: the cap's −18 cones and the bind's
  −17 overlap to −22 together (drone −5 under either, −5 under both).
- **The pair that moves a fixture no single moves**: `photo_chrome_specular`
  D 52 → C 64 under `colour4` is `mask_small` — the mask plus the lowered
  floor — reproduced byte for byte by that pair alone. Flip both or
  neither.
- **The colour-budget finding**: the sheet prices at `max_colors` 12 while
  the Studio ships 6, and for the cap those are different questions —
  drone at 6 sews 23 cones OFF and **6** under the cap (`COLOR_CAP_APPLIED`,
  25 → 6 region threads); at 12, 17 and 12. At the Studio's shipped 6 the set is the bigger lever: `colour4` takes **−47 cones / −43 stops / −43 blocks** off nine fixtures (drone 23 → 6, Bridge Bar 13 → 6, Golden Tee 14 → 6, screenshot 14 → 6 — the slider's promise kept on every real logo), `colour5` adds −4,509 stitches and −80 trims; one grade falls, `summit_badge` (synthetic) F 16 → F 0 on a new `THREAD_MATCH_POOR` block from the cap's merge.
- **The item-1 proxy corrects the lane story**: forced flat, `colour5`
  still takes **28 cones and 28 stops** off five of the nine real logos
  (Golden Tee sews 24 cones under a budget of 12 forced flat — the flat
  lane's hard cap holds region threads, and the re-snap escapes past it
  there too; "every escape was on the gradient lane" was a count over
  routed fixtures). The flat-lane singles say the bind does most of that work (−26 cones on five logos) and the cap the rest (−21 on drone and Golden Tee); the dissolve is the one flag item 1 retires (byte-identical on all nine forced flat).
- **Renders** (`docs/renders/colour-bundle-2026-09-10/`, ten contact
  sheets): the one visible change is Bridge Bar under `colour5` — the
  pink phantom outline around the script and the grey ghost spoke gone —
  the render the 2026-09-04 ruling was made without (the flag was broken
  then, #380). Every other move is a cone swap inside a hue family.

## 5. The decision doc

`docs/colour-bundle-decision-2026-09-10.md` — the tables, the renders,
the lane question measured, and one recommendation per flag with its
catch (§5 there). Kent's to accept or refuse; nothing here flips a
default.
