# Tier B5: fill and sequence flags folded into the code by flag consolidation

Kent, 2026-11-19 ("Let's do the flag sprawl", `docs/flag-audit-2026-11-19.md`, tier B), batch B5, folded
2026-11-20. Each of these 9 was ON by default and had been ON for weeks. The switch is gone: the ON
behaviour is the only behaviour, and the field names are in `digitizer_core.config.RETIRED_FIELDS` (a
request or snapshot that still names one is ignored, never an error). The fold is byte-identical:
`python -m tools.fold_check` over the 44 `flag_sweep` jobs matches the merge base on every one. Below is what
each one was and why it went on, moved verbatim from its config comment, PR pointers kept. The research
docs it cites still stand.

Function-level keyword parameters that the pipeline used to fill from these fields (`cut_bridges`,
`slant_turns`, the `cross` argument of `fabrics.fill_underlay_for`) stay in their signatures with their old
defaults, because unit tests call those emitters directly; the pipeline now passes `True`.

**Two flags in the batch were NOT folded** because a non-test caller still sets them False:

- `borders_last`: the Monarch starter's committed `digitize_config`
  (`app/public/starter/manifest.json`, redigitized 2026-11-12, Kent "Ship monarch now",
  `docs/monarch-orange-drift-2026-11-12.md`) carries `"borders_last": false`. Folding it would drop that
  key on re-digitize and re-sew Monarch with the borders last.
- `border_by_size`: `stage6_puff.puff_eligible` hands stage 7's `_sews_satin` a config with
  `border_by_size` replaced by False (puff's own width ceiling replaces the by-size rule).

## `beanie_knockdown` (field)

Last default: ON. Folded 2026-11-20 (`beanie_knockdown: bool = True`).

```text
Beanie knockdown (rule R9, `docs/pro-digitizer-rules-2026-10-21.md`;
`knockdown.py`). ON, a design on `garment_id == "beanie"` opens with
its own colour block: a sparse tatami (0.5 mm rows, 3.5 mm stitches, no
underlay) over the whole design grown 2.0 mm (on a badge: out to its
satin border's outer edge and no further), holes filled, in the cone
nearest `garment_rgb` — the professional's habit on all 6 beanie files
(5 jobs) in his zip, where it flattens the knit's pile. No garment
colour, no knockdown. Every other garment is untouched either way.
Built OFF 2026-10-21 and flipped ON the same day by Kent over the
renders (`docs/renders/beanie-knockdown-2026-10-21/`): the engine knows
what a garment needs, as with backing, so a beanie gets one. The three
constants are still the pro's, unsewn. False is the pre-flip engine
byte for byte; only a beanie with a known garment colour changes.
```

## `edge_cap_follow_adjacent` (field)

Last default: ON. Folded 2026-11-20 (`edge_cap_follow_adjacent: bool = True`).

```text
Whether the cap sews each stretch of the edge in the thread of the shape
it stands against (Kent 2026-10-06: the bean outline on the Instagram
icon did not follow the colour beside it) rather than the whole ring in
the one cone that owns the most of it. Costs a colour change per extra
thread the cap touches, so a gradient logo sews its cap in several
blocks; stretches shorter than `stage7_sequence._CAP_PIECE_MIN_MM` fold
into their neighbour so a junction never flickers. False restores the
single block.
```

## `edge_cap_skip_bean_letters` (field)

Last default: ON. Folded 2026-11-20 (`edge_cap_skip_bean_letters: bool = True`).

```text
No edge cap round a BEAN letter (2026-10-20, Proseal's two A's). A
bean letter (`beanletters.tag_bean_letters`) sews its ink's centre-line
spines as runs; its traced polygon is not what it laid. Stage 5 still
grows that polygon by the fill's pull (a bean letter is not a satin
column), so on Proseal at the pro's 85.9 mm (Hat) the tagline's two
A's -- traced as solid triangles, counters filled -- planned at 7.46
and 8.17 mm^2 against 2.95 and 3.54 traced, their edge 0.4 mm off the
thread and outside the bean runs' half-thread cover, and the cap drew a
second outline round each: 45 and 63 cap stitches, the R/Y/P beside
them none (their polygons are not grown). ON, a text member that sewed
as a bean letter -- bean meta, and no fill or satin run on it -- hands
its polygon to the cap's `omit`, as a satin letter does under the flag
above: its runs are already linear cover, and a run has no row end for
a cap to close. The silhouette is untouched, so every other ring
samples as before. Satin and fill letters are exactly as
`edge_cap_skip_lettering` leaves them. Measured on Proseal 85.9 mm:
cap 1,350 -> 1,242 points, the 108 cut all on the A's (2 of 23 runs),
the other 21 cap runs and every artwork run identical point for point;
the design 7,884 -> 7,776 stitches, trims 57 -> 55, and the cap-only
block SPRAY's A pulled onto the end gone (7 -> 6 blocks).
False is the pre-flip cap byte for byte.
```

## `edge_cap_skip_lettering` (field)

Last default: ON. Folded 2026-11-20 (`edge_cap_skip_lettering: bool = True`).

```text
No edge cap on lettering (lettering construction plan step 5,
2026-09-19). The design-silhouette cap above sews only the stretches
of the outline nothing linear already covers -- and on a satin-sewn
letter that is exactly the bare corners and junction seams the satin
decomposition leaves, so the cap was patching a defect upstream: on
the plan's traced MARINE at 80 mm, 17 of its 18 cap runs and 418 of
its 457 cap stitches stand on the letters' outlines (16 of the word's
41 trims before steps 1-3). A typed glyph gets no cap: the font
engine sews columns and nothing else. ON, a text-cluster member that
sewed SATIN -- not fill: a tatami letter's rows still end in open
air, the defect the cap exists for -- hands its whole sewn outline to
the cap's `omit`, so no cap sample stands on it, on bare fabric or as
the edge of a hole in a fill; everything else is capped as before,
and the bare corners a letter still has are now the letter's own to
show (measured as uncovered artwork, scope-history step 5). Measured
2026-09-19: the fixture 2,192 -> 1,774 stitches, trims 23 -> 7 (the
typed word: 3), uncovered 0.0 both ways; Becker at 80 mm trims 43 ->
36; fill-lettering designs byte-identical. Built OFF and FLIPPED ON
the same day -- Kent's call 2026-09-19, over the fixture's trims (23 ->
7 against the typed word's 3), the render (the hooks gone from every
letter) and the nine-logo sheet (five move: -12 trims / -319 stitches,
uncovered area unchanged on all nine). False is the pre-flip cap byte
for byte.
```

## `fill_bridge_cut` (field)

Last default: ON. Folded 2026-11-20 (`fill_bridge_cut: bool = True`).

```text
BUILT 2026-09-19 and FLIPPED ON the same day — Kent's call over the
thread renders (`docs/renders/fill-bridge-cut-2026-09-19/`, OFF above
ON: Becker's ring of travel round a finished leg, Fremont's line across
the field, the screenshot's loop, each gone), judged on a render and not
yet on cloth. False is the engine before it, plan-md5-identical on the
nine logos. What the flag above cannot
reach: `emit` sews ANY in-shape route between two fill columns, however
much of it lies on finished fill, and lifts only when no route exists;
`_score`'s ratified rate (a trim is 25 stitches, an exposed stitch 2) is
only ever asked about whole column orders, never about one bridge. ON,
a bridge that shows, spans a gap over `trim_at`, and costs more at that
same rate than the cut it avoids is lifted instead
(`stage6_fill._cut_is_cheaper`), in the emitter and the scorer alike.
No constant is added or moved. Inert without `fill_travel_under_cover`,
which is what tracks the sewn footprint, and on TWO-PASS fills
(crosshatch, the density boost): that footprint cannot tell pass-one
fill that pass two will cover from finished fill, so every pass-two
bridge read as exposed and bought a cut that hid nothing (a two-hole
plate: trims 0 -> 2). Exposure per pass is unmeasured; the photo lane's
crosshatch is where that matters.
Measured ON (nine logos, 80 mm, main's defaults after #516): exposed
travel 248.6 -> 140.9 mm by `tools/travel_cover.py`, 432.3 -> 226.2 by
`tools/fill_bridges.py`, trims 458 -> 464, stitches 76,774 -> 76,706,
uncovered unchanged on all nine; Becker's 22.9 mm leg -> 4.0. The delta
held across three engine states that day (+6 trims each time). As
thread, OFF above ON: `docs/renders/fill-bridge-cut-2026-09-19/`. OFF is
plan-md5-identical to the engine before it, all nine. Read it yourself:
`tools/travel_legs.py --set fill_bridge_cut=true`.
**Re-measured on the tree with `satin_junction_stack` and
`satin_lettering_split` ON (2026-09-19, after #520):** 232.7 -> 147.4 mm,
trims 473 -> 478, stitches 77,242 -> 77,182, uncovered and finding codes
identical. Becker is now md5-identical OFF and ON -- its leg was the
MARINE band's FILL and the band sews as satin -- so the trade is
Fremont's (58.0 -> 21.1, +4 trims), the screenshot's (60.9 -> 26.0, +4),
Bridge Bar's (+1) and drone's (-4); five of nine do not move.
`*_stack_split_tree.jpg` beside the renders above.
A lift this makes raises `report["jumps"]`, which `LONG_JUMPS_TRIMMED`
counts. Its ENGINE prose said the thread "had to be" lifted and now says
"is lifted"; the Studio's own sentence for the code ("gets cut N times
where it has to travel a long way") never made the claim. `TRIM_HEAVY`'s
in-shape share rises with it.
**The cost is trims, and one reading that looks like a cost and is
not:** Hotel Fremont gains a LETTERING_ILLEGIBLE warn (tagline OCR
0.50 -> 0.27). The tagline's own 13 runs are byte-identical either way;
what moved is two of the white FIELD's bridges that ran needle-down
through the tagline band and are now cut, and tesseract swapped one
noise string for another (`VAT] CY § Pw` at confidence 46 for `| | TL`)
on lettering lost on the thread under both. Drone's moved 0.10 -> 0.25
under the nearest order and 0.36 -> 0.05 under euler: opposite ways
from one rule, which is what noise looks like. `docs/scope-history.md`
2026-09-19, "the exposed travel legs" and its two addenda;
`tests/test_fill_bridge_cut.py`.
```

## `fill_turn_slant` (field)

Last default: ON. Folded 2026-11-20 (`fill_turn_slant: bool = True`).

```text
Fill rows turn on a slant (2026-10-21, built OFF; the settings audit's
gap #2, `docs/settings-vs-pro-2026-10-21.md` row 24). At the end of a
fill row we stepped straight across to the next: one row spacing,
0.10-0.22 mm at the 0.15 row, the needle landing beside its own hole,
and 40-90% of every sub-0.5 mm stitch on the pro's jobs. The pro's
turns land the next row's first penetration ~0.7 mm along it
(`machine.FILL_TURN_ALONG_MM`, read off his DSTs by
`tools/fill_turns.py`). True pulls in the INNER of the two boundary
points each turn joins -- the next row's entry on a narrowing edge, the
row's own exit on a widening one -- so the turn runs that far along
the row and its thread lies over the corner left bare
(`stage6_fill._slant_turns`). The outer point stays on the boundary,
so the edge keeps its line and takes a penetration every second row.
Row spacing and the interior grid are unchanged. Construction, not a fabric constant (ROADMAP gate 1 asks
which kind); the flip is Kent's. False is byte-identical.
`tests/test_fill_turn_slant.py`.
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```

## `fill_underlay_cross` (field)

Last default: ON. Folded 2026-11-20 (`fill_underlay_cross: bool = True`).

```text
The pro's fill underlay in the hat / left-chest / beanie presets (built
OFF 2026-10-21): ON, `structured_cap`, `pique_knit` and `jersey_tee`
sew `cross_tatami` (one crossing pass, `machine.UNDERLAY_CROSS_ROW_MM`
rows, `UNDERLAY_CROSS_STITCH_MM` stitches) under a fill in place of
their `edge_zigzag` / `edge_run`. Every dense fill on every job in the
pro's zip has that pass (`docs/settings-vs-pro-2026-10-21.md` rows
13-15). Only the preset FALLBACK moves: `underlay_style` above, the
per-shape override and the photo-class default still win as before.
A fabric preset is gate 1 (a physical constant), so this waits on the
sew-out card's arm and Kent's flip. OFF is the engine byte for byte.
Browser twin: `crossUnderlay` (src/digitize.js).
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```

## `tie_in_off` (field)

Last default: ON. Folded 2026-11-20 (`tie_in_off: bool = True`).

```text
No lock at the START of a run (2026-10-22, settings-vs-pro row 22).
`stitches.apply_ties` already locks only where the thread is cut (the
first run of a block, a trimmed run); the pro locks none of those
either: 1 of 68 run starts across Fremont, Becker and MFab, all after a
cut. On: every tie-in is stripped (`stitches.drop_tie_ins`), tie-offs
stay -- about four stitches per cut. Whether a start holds without its
knot is a sew-out (ROADMAP gate 1): a CANDIDATE. False is byte-identical.
Not in `SMALL_TEXT_TRUE_SIZE`.
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```

## `trim_bury_under_later` (field)

Last default: ON. Folded 2026-11-20 (`trim_bury_under_later: bool = True`).

```text
`trim_bury_under_later` (BUILT OFF 2026-10-21, the trim-economy study,
`docs/trim-economy-2026-10-21.md`): a cut hop inside a colour block is
sewn needle-down instead when thread sewn AFTER it -- the rest of the
block and every later artwork block, real stitches, not polygons --
covers the travel's whole width (`stage7_sequence.
_bury_trims_under_later`). Read with `tools/trim_classes.py` over the
ten jobs with both artwork and the pro's DST, the pro cut 9 hops that
later thread covers where we cut 43; he travels under the work. The
narrow half of `chain_links`: never on top of finished thread, never
under a predicted polygon, so no LINK_COVER_INSET_MM and no tolerance
beyond half a thread at each end. Still chaining in the ROADMAP gate 3
sense (needle-down thread a later pass is trusted to hide), so the
flip is Kent's, after the sew-out says buried travel does not show.
False, byte-identical. Tests: `tests/test_trim_bury_under_later.py`.
ON by default since 2026-10-23 (Kent's flip on the flip sheet, PR
#1047: `docs/flip-sheet-2026-10-23.md`); False is the off arm.
```
