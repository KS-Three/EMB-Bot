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
`docs/renders/colour-bundle-2026-09-10/` holds OFF vs `colour4` vs
`colour5` for every fixture the bundle moves — the look is the part of
this decision that is Kent's.

## 4. Results — to be measured
## 5. The decision doc — to be written
