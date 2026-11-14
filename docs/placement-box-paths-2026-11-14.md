# Placement boxes: which path clamps to which (2026-11-14)

Why this exists: PR #1493/#1495 recorded an open mismatch. The box
`buildImportedDesign` clamps a stitch file to is not the box auto-fit and the
Studio's typed/drag clamps use. This maps every path per garment x placement,
measures the gap, and recomputes the #1495 overflow table under one box.
**No behaviour changes in this PR**; `test/placement-box-paths.test.js` pins
today's boxes so a later change is deliberate. The numbers below are generated
by `tools/placement-box-paths.mjs` (`node tools/placement-box-paths.mjs`), which
probes the engine rather than copying a table.

## Answer

- **The paths disagree on 3 of 28 placements**, all of them the *default*
  placement of a garment the pro measured: `hat_front` (import clamp 127.0 x
  57.15, everything else 113.5 x 64.0), `left_chest` (101.6 x 101.6 vs 96.0 x
  76.5, area cap 5,800 mm2) and `beanie` (114.3 x 63.5 vs 94.5 x 56.0). The other
  25 placements (every non-default placement, and the seven garments with no pro
  box) agree to 0.1 mm on every path. `resolvePlacement` rewrites `widthIn/heightIn`
  from the PLACEMENTS box for any non-default placement, so the inch pair *is* the
  PLACEMENTS box there.
- **The inch pair is not a hoop field, and it is not a deliberate second box.**
  `GARMENTS[].widthIn/heightIn` (`src/garments.js:13-24`) is the original
  round-inch *placement* table. The physical hoops are `HOOPS` (`:217-222`, 100 to
  200 mm fields), a ceiling check, never a clamp (`app/src/lib/hoop.js`). When the
  pro boxes arrived (`PRO_PLACEMENT_MM`, `:72-76`, PR #1110/#1118, 2026-10-26) and
  `PLACEMENTS` after them (PR #1159, 2026-10-27), the Studio's clamps were moved
  to the new box (`SizePanel.svelte:69`, `EmbroideryField.svelte:499` both carry
  the comment "Until then this read the garment's round-inch pair"). The engine's
  builders were not: the memory note for #1159 lists "`digitize.js`'s typed-width
  clamp still reads the inch pair for default placements" under *Not done*, and
  `dstimport.js` is the same leftover. Its doc comment still calls the box "hoop
  clamp" (`dstimport.js:251`), which is the old name.
- **It is not only the starters.** A digitized upload on the hat front is
  auto-fitted into 113.5 x 64.0, the service sews it at that size, and the result
  then re-enters `buildImportedDesign` (`generate.js:129`) and meets the 57.15 mm
  height clamp. A square logo is fitted at 64.0 mm and drawn at 57.2 mm, 10.7%
  smaller than the fit says, with no note. (Measured through `buildImportedDesign`,
  the call `generateElement` makes; not re-run in the running Studio.) The same
  logo on the left chest and beanie is unchanged, because their inch box is
  bigger than the pro box.
- **Recomputed #1495 table** (12 starters x 28 placements = 336 combinations):
  overflows go from **77 to 78** if `buildImportedDesign` read the PLACEMENTS box.
  11 combinations change overflow (1 now fits, 4 better, 4 worse, 2 new), and 16
  more fit both ways but are drawn at a different scale. Hat front improves
  everywhere; the beanie and the left chest get worse (below).

## Where each number comes from

| Path | What it reads | Source |
|---|---|---|
| Stitch-file import, digitized result, outline lettering | the placed garment's inch pair | `src/dstimport.js:269-270` (`garment.widthIn/heightIn * 25.4`), clamp `:324-326`; callers `app/src/lib/generate.js:105` (stitch file, with `autoScaleRange` `:109`), `:129` (digitized), `:300` (outline lettering) |
| Engine typed-width clamp (image lane, satin lettering) | the placed garment's inch pair | `src/digitize.js:1260` (`buildQualityDesign`), `:2081` (`buildLetteringDesign`) |
| Digitized upload default width, lettering auto-fit | PLACEMENTS box, capped to the 200 mm hoop field less 1 mm a side, left chest also area-capped | `app/src/lib/placement.js:53-62` `fitTargetWidthMm` -> `src/garments.js:199-208` `fitScale` -> `:190-197` `autoFitBoxMm` -> `:172-179` `placementBoxMm`; engine auto-fit `src/digitize.js:1250`, `:2070` |
| Studio typed width, drag, nudge, resize | PLACEMENTS box | `app/src/lib/placement.js:38-43` `placementBoxOf`; `app/src/ui/SizePanel.svelte:69-72`; `app/src/ui/EmbroideryField.svelte:499-502` (and `:3424`); `app/src/App.svelte:738-741`; `app/src/lib/hoop.js:84` |
| Outline-lettering width | PLACEMENTS box width | `app/src/lib/outlineFonts.js:131-155` |
| Preview box, worksheet box, node-edit predicted fit | the placed garment's inch pair | `app/src/lib/preview.js:867-868`, `app/src/lib/exporters.js:260`, `app/src/lib/fieldNodeEdit.js:322-326` (typed branch; its auto branch calls `autoFitBoxMm`) |
| PLACEMENTS entry | the pro's `PRO_PLACEMENT_MM` by reference for hat front, left chest, beanie; every other row `seeded` (inch table, or an industry chart: cap side 2.5 x 1.5 in, rear 3.5 x 1.5 in, front panel 2.25 x 2 in, yoke 10 x 3 in, cuff 4 x 1.75 in; right chest = the pro's left chest mirrored) | `src/garments.js:72-76`, `:103-126` |

The preview, worksheet and node-edit readers sit on the inch side too, so a
decision to unify has five engine/app readers to move, not one (the table in
`docs/placement-boxes-2026-10-28.md` stays correct either way: it reads
`placementBoxMm`).

## Generated tables

Rows are measured by probe: a design thousands of mm wide (then tall) through
`buildImportedDesign`; a 5,000 mm typed width through `buildQualityDesign`;
`fitScale` on the same extremes; and `placementBoxMm`. The probe's engine output
rounds to 0.1 mm stitch units.

**Paths disagree on 3 of 28 placements**: hat_front, left_chest, beanie.

### Path table (measured by probe, mm, W x H)

| Garment | Placement | PLACEMENTS entry (source) | Import clamp `buildImportedDesign` | Engine typed clamp | Auto-fit (hoop-capped) | App typed/drag clamp | Paths disagree? |
|---|---|---|---|---|---|---|---|
| hat_front | hat_front (default) | 113.5 x 64.0 (pro) | 127.0 x 57.2 | 127.0 x 57.2 | 113.5 x 64.0 | 113.5 x 64.0 | **YES**: import +13.5 w / -6.9 h mm |
| hat_front | hat_front_left | 57.2 x 50.8 (seeded) | 57.2 x 50.8 | 57.2 x 50.8 | 57.2 x 50.8 | 57.2 x 50.8 | no |
| hat_front | hat_front_right | 57.2 x 50.8 (seeded) | 57.2 x 50.8 | 57.2 x 50.8 | 57.2 x 50.8 | 57.2 x 50.8 | no |
| hat_front | hat_side_left | 63.5 x 38.1 (seeded) | 63.5 x 38.1 | 63.5 x 38.1 | 63.5 x 38.1 | 63.5 x 38.1 | no |
| hat_front | hat_side_right | 63.5 x 38.1 (seeded) | 63.5 x 38.1 | 63.5 x 38.1 | 63.5 x 38.1 | 63.5 x 38.1 | no |
| hat_front | hat_rear | 88.9 x 38.1 (seeded) | 88.9 x 38.1 | 88.9 x 38.1 | 88.9 x 38.1 | 88.9 x 38.1 | no |
| left_chest | left_chest (default) | 96.0 x 76.5 (pro) | 101.6 x 101.6 | 101.6 x 101.6 | 96.0 x 76.5, area 5800 | 96.0 x 76.5 | **YES**: import +5.6 w / +25.1 h mm |
| left_chest | right_chest | 96.0 x 76.5 (seeded (pro mirrored)) | 96.0 x 76.5 | 96.0 x 76.5 | 96.0 x 76.5, area 5800 | 96.0 x 76.5 | no |
| left_chest | full_back | 304.8 x 304.8 (seeded) | 304.8 x 304.8 | 304.8 x 304.8 | 198.0 x 198.0 | 304.8 x 304.8 | no |
| left_chest | upper_back | 254.0 x 76.2 (seeded) | 254.0 x 76.2 | 254.0 x 76.2 | 198.0 x 76.2 | 254.0 x 76.2 | no |
| left_chest | sleeve | 76.2 x 76.2 (seeded) | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | no |
| full_back | full_back (default) | 304.8 x 304.8 (seeded) | 304.8 x 304.8 | 304.8 x 304.8 | 198.0 x 198.0 | 304.8 x 304.8 | no |
| full_back | left_chest | 96.0 x 76.5 (pro) | 96.0 x 76.5 | 96.0 x 76.5 | 96.0 x 76.5, area 5800 | 96.0 x 76.5 | no |
| full_back | right_chest | 96.0 x 76.5 (seeded (pro mirrored)) | 96.0 x 76.5 | 96.0 x 76.5 | 96.0 x 76.5, area 5800 | 96.0 x 76.5 | no |
| full_back | upper_back | 254.0 x 76.2 (seeded) | 254.0 x 76.2 | 254.0 x 76.2 | 198.0 x 76.2 | 254.0 x 76.2 | no |
| full_back | sleeve | 76.2 x 76.2 (seeded) | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | no |
| beanie | beanie (default) | 94.5 x 56.0 (pro) | 114.3 x 63.5 | 114.3 x 63.5 | 94.5 x 56.0 | 94.5 x 56.0 | **YES**: import +19.8 w / +7.5 h mm |
| beanie | beanie_cuff | 101.6 x 44.5 (seeded) | 101.6 x 44.5 | 101.6 x 44.6 | 101.6 x 44.5 | 101.6 x 44.5 | no |
| sleeve | sleeve (default) | 76.2 x 76.2 (seeded) | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | no |
| tote | tote (default) | 203.2 x 203.2 (seeded) | 203.2 x 203.2 | 203.2 x 203.2 | 198.0 x 198.0 | 203.2 x 203.2 | no |
| jacket_back | jacket_back (default) | 304.8 x 254.0 (seeded) | 304.8 x 254.0 | 304.8 x 254.0 | 198.0 x 198.0 | 304.8 x 254.0 | no |
| jacket_back | left_chest | 96.0 x 76.5 (pro) | 96.0 x 76.5 | 96.0 x 76.5 | 96.0 x 76.5, area 5800 | 96.0 x 76.5 | no |
| jacket_back | right_chest | 96.0 x 76.5 (seeded (pro mirrored)) | 96.0 x 76.5 | 96.0 x 76.5 | 96.0 x 76.5, area 5800 | 96.0 x 76.5 | no |
| jacket_back | upper_back | 254.0 x 76.2 (seeded) | 254.0 x 76.2 | 254.0 x 76.2 | 198.0 x 76.2 | 254.0 x 76.2 | no |
| jacket_back | sleeve | 76.2 x 76.2 (seeded) | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | 76.2 x 76.2 | no |
| patch | patch (default) | 88.9 x 88.9 (seeded) | 88.9 x 88.9 | 88.9 x 88.9 | 88.9 x 88.9 | 88.9 x 88.9 | no |
| towel | towel (default) | 152.4 x 152.4 (seeded) | 152.4 x 152.4 | 152.4 x 152.4 | 152.4 x 152.4 | 152.4 x 152.4 | no |
| blanket | blanket (default) | 254.0 x 203.2 (seeded) | 254.0 x 203.2 | 254.0 x 203.2 | 198.0 x 198.0 | 254.0 x 203.2 | no |

### Square logo through the digitized upload path

Auto-fit sizes a square logo into the PLACEMENTS box; the service result then re-enters `buildImportedDesign` at native size and meets the inch-pair clamp.

| Placement | Fitted side (auto-fit) | Drawn side after import clamp |
|---|---|---|
| hat_front | 64.0 | 57.2 (shrunk) |
| left_chest | 76.2 | 76.2 |
| beanie | 56.0 | 56.0 |

### Starter overflow at the 75% stop: inch pair (today) vs PLACEMENTS box

Overflowing starter x placement combinations: **77** today, **78** if `buildImportedDesign` read the PLACEMENTS box. 11 of 336 combinations change.

| Placement | Box today | Box PLACEMENTS | Starter | Today (scale, overflow w/h) | PLACEMENTS (scale, overflow w/h) | Verdict |
|---|---|---|---|---|---|---|
| hat_front | 127.0 x 57.2 | 113.5 x 64.0 | Shamrock | 75%, 0.0 / 1.8 | 81%, fits | now fits |
| hat_front | 127.0 x 57.2 | 113.5 x 64.0 | Bur oak leaf | 75%, 0.0 / 10.8 | 75%, 0.0 / 3.9 | better |
| hat_front | 127.0 x 57.2 | 113.5 x 64.0 | Christmas tree | 75%, 0.0 / 10.6 | 75%, 0.0 / 3.7 | better |
| hat_front | 127.0 x 57.2 | 113.5 x 64.0 | Monarch butterflies | 75%, 0.0 / 7.1 | 75%, 0.0 / 0.3 | better |
| hat_front | 127.0 x 57.2 | 113.5 x 64.0 | Lighthouse | 75%, 0.0 / 12.8 | 75%, 0.0 / 5.9 | better |
| beanie | 114.3 x 63.5 | 94.5 x 56.0 | Heart | 84%, fits | 75%, 0.0 / 0.6 | NEW overflow |
| beanie | 114.3 x 63.5 | 94.5 x 56.0 | Shamrock | 81%, fits | 75%, 0.0 / 2.9 | NEW overflow |
| beanie | 114.3 x 63.5 | 94.5 x 56.0 | Bur oak leaf | 75%, 0.0 / 4.4 | 75%, 0.0 / 11.9 | worse |
| beanie | 114.3 x 63.5 | 94.5 x 56.0 | Christmas tree | 75%, 0.0 / 4.2 | 75%, 0.0 / 11.7 | worse |
| beanie | 114.3 x 63.5 | 94.5 x 56.0 | Monarch butterflies | 75%, 0.0 / 0.8 | 75%, 0.0 / 8.3 | worse |
| beanie | 114.3 x 63.5 | 94.5 x 56.0 | Lighthouse | 75%, 0.0 / 6.4 | 75%, 0.0 / 13.9 | worse |

Tally: now fits 1, better 4, worse 4, NEW overflow 2.

Fits under both boxes but drawn at a different scale: 16 combinations.

| Placement | Starter | Scale today | Scale PLACEMENTS |
|---|---|---|---|
| hat_front | Jack-o'-lantern | 79% | 88% |
| hat_front | Heart | 76% | 85% |
| hat_front | Owl | 93% | 100% |
| hat_front | American football | 95% | 100% |
| hat_front | Baseball | 77% | 86% |
| hat_front | Turtle | 92% | 100% |
| left_chest | Shamrock | 100% | 97% |
| left_chest | Bur oak leaf | 100% | 84% |
| left_chest | Christmas tree | 100% | 85% |
| left_chest | Monarch butterflies | 100% | 89% |
| left_chest | Lighthouse | 100% | 82% |
| beanie | Jack-o'-lantern | 88% | 77% |
| beanie | Owl | 100% | 92% |
| beanie | American football | 100% | 93% |
| beanie | Baseball | 86% | 75% |
| beanie | Turtle | 100% | 91% |

## Options for Kent (not decided; sent to the foreman)

The three disagreeing rows are all pro-measured rows, so "unify only where a
pro box exists" and "unify everything" change exactly the same three placements.
The real choice is how many of the three.

1. **Unify all three on the PLACEMENTS box.** One box per placement everywhere.
   Cost: `buildImportedDesign`, the two `digitize.js` clamps, `preview.js`, the
   worksheet and `fieldNodeEdit.js` read `placementBoxMm`; the starter-pack pin
   "default placement is not resized" (`starterPack.spec.js:251`) changes.
   Catch: the 12 starters land worse on the beanie (6 combinations worse or new
   overflow, 5 more shrink) and on the left chest (5 of 12 shrink 3 to 18% on
   the default placement the starter pack lands on); the beanie width (94.5) is
   the least firm pro number (his two wide beanies disagree, 93.8 vs 110.5); the
   left chest area cap cannot be expressed in a clamp.
2. **Keep both, document why.** Zero risk; this doc plus the pinning test is the
   whole change. Catch: the hat front keeps shrinking digitized art past what
   auto-fit promised (square logo 64.0 fitted, 57.2 drawn), and hat-front stitch
   files keep overflowing by up to 12.8 mm where 64 mm of height would hold more of them.
3. **Unify the hat front only; leave beanie and left chest on the inch pair.**
   Fixes the one place a customer sees a wrong size today: hat front overflows
   drop (1 now fits, 4 better, none worse), 6 more starters shrink less. No
   regressions. Catch: two placements stay inconsistent, pinned by the test;
   the beanie and left chest wait for their own call (a beanie sew-out, or Kent
   ruling the box numbers).

**Pick: 3.** The 64 mm hat height is Kent's own ruling (2026-10-26, "64 mm (2.5
in) or more"), and the import clamp contradicts it; the beanie and left chest
moves make starters worse for a consistency win the pro numbers do not yet earn.
