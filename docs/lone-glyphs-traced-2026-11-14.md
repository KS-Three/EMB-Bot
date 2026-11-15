# Small glyphs that vanish a little below their judged size: traced (2026-11-14)

The evening's eye sweep (`eye_pairs_out/eye-sweep-1114/REPORT.md`) logged
four faults where a small glyph turns to a speck, or goes, a little below
the size it was judged at:
- 8: Jakarta's word "a" at 70.9 mm;
- 11a: Ahora's gear teeth at 70.9;
- 11b: "Seriously" reading "Senaudy" at 70.9;
- 13: neon's ®.

Each glyph was instrumented on main `5a647125`, beanie, at the failing size
and at the judged one: its region at each stage (area, width, height,
inscribed width, tags) and what sewed for it. The pictures (gitignored, in
the primary checkout) are under `eye_pairs_out/detail-1114/lone/` and
`sheets/lone_*`.

n = 1 per design; counts and readings, no quality claim (gate 4).

## What each one is

| fault | glyph at the failing size | first stage it goes | the rule and its number | inside a word? |
|---|---|---|---|---|
| 11b "Seriously" | the i's dot: 0.74 x 0.96 mm, 0.54 mm² at 70.9; 0.84 x 1.09 at 80.2 | **stage 3**, `resolve_small_regions` | the run tier's loop proxy, 2 x max(w, h) = 1.92 mm (2.18 at 80.2), is under `RUN_MIN_LOOP_MM` 2.2. The dot rung would admit it (perimeter 2.6 mm, over 1.35), but its lettering scope needs a separate same-colour stem under the dot (`has_stem_below`), and a cursive i's stroke is one region with the whole word | **no:** Jakarta's printed i's (dots 0.23-0.25 mm² over their own stems) keep theirs via the rung. **Missing at 80.2 too on tonight's main;** "clean at 80.2" was Kent's older kit tree |
| 8 Jakarta "a" | a 2.66 mm² region in the same text cluster as its line, sewn as 24 satin points about 1.3 x 1 mm: the speck | **the small-text re-set:** at 70.9 both tagline clusters skip `no_room` (cap 2.25 mm against the 4.0 target); at 80.9 the line is raised (the "a" 7.2 mm²) | `_place_line_reset` finds no scale down to `MIN_SCALE` whose grown line fits the design box clear of obstacles. #1532's `small_text_reset_ground_ring` does not clear it | **not a lone-glyph rule:** the whole line stays at art size, and every "a" on it splits its top arc off (0.38 mm²) and sews short. The re-set lane's (#1532's) |
| 11a Ahora | the gear's 0.6-0.75 mm teeth | stage 6 satin rails | `outline_inlets_kept` + `outline_inlets_teeth` (#1528, #1536) fire (inlet share 0.048 over 0.03) and split it, but the teeth sit under the ring's satin and its pull | **not covered** by the teeth flag at 70.9 (it is at 80) |
| 13 neon ® | not run tonight | | | |

**`speck_prune` and `tiny_detail_keep` (both OFF):** byte-identical to OFF
on "Seriously" at 70.9. The i-dot stays dropped:
- `speck_prune` removes specks;
- `tiny_detail_keep` keeps multi-colour details inside a host, and a dot on
  the page has no host.

## The fix: `cfg.extra["lone_glyph_keep"]`, built OFF

`stage3_segment.resolve_small_regions`, the dot rung's lettering scope. A
TITTLE over a joined word is admitted as a printed i's dot is. The dot must
pass the rung's own area and perimeter floors, unchanged, and:
- lie inside the box of a region of its own colour;
- that region reaches at least `_STEM_MIN_DOTS` (3) dot heights below it;
- that region is at least `_TITTLE_MIN_AREA_DOTS` (10) times the dot's area;
- that region has ink in the dot's own columns within `_TITTLE_GAP_DOTS` (6)
  dot heights under it.

"Seriously" measures ink 4.85 dot heights under the dot, in a word 17 tall.
The flag runs on the flat lane only (`chain_rescue`), because a photo's
specks sit inside big same-colour regions everywhere.

The dot then sews in the smallest tier that draws it: the dot rung's tack.
Below the rung's floors it is dropped as before, by the same rule and the
same count. The thresholds are read off the letter's shape, like the stem
constants beside them; no stitch value moves (gate 1 does not apply).

**ON:**
- "Seriously" at 70.9 and 80.2: the i's dot sews (a 0.5 mm² region, a
  17-point rung tack) (`sheets/lone_seriously_idot*.png`).
- Jakarta at 70.9: byte-identical.
- k_line and Becker: see the PR body.

## Not built, and whose

- **Jakarta's "a" at 70.9:** the re-set's `no_room`. A line that cannot take
  its full raise gets none. A partial raise that fits, or room found past the
  design box's edge, is the re-set lane's.
- **Ahora's teeth at 70.9:** sub-millimetre teeth under a satin ring. Either
  the ring's pull is held off them (the satin push lane, #1529's
  `satin_push_keeps_gaps`), or the teeth sew last on top.
- **"Never sewn as a dot":** the "a" is a glyph sewn as a speck, and nothing
  measures that today. A check of a text glyph's sewn cover against its art
  would catch it.
