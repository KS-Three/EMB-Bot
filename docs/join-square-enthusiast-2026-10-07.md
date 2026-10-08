# `satin_join_square`'s lost ENTHUSIAST element, named and fixed — 2026-10-07

Kent flipped `satin_join_square` ON on 2026-10-06 on Hotel Fremont renders.
Merged with main and run on the lettering guard set (PR #663), ON lost one
artwork element of at least 1 mm² on the ENTHUSIAST wordmark — a fixture that
had never lost one — and tipped three sibling bars; Kent held the flip the same
day and asked for the element to be NAMED, and for a fix only if one nameable
rule misreads the fixture. This is that trail. Everything below is at 80 mm,
`left_chest`, `max_colors=6`, on `testdata/photo/enthusiast_logo.png`, the
tree of PR #663's head plus the cap.

## 1. The element

The region set is identical OFF and ON (31 regions, same ids, same polygons);
only four shapes' stitches change. Bare artwork per shape, the guards' own
instrument (`tools/bare_anatomy.components` / `tools/dropped_elements`):

| shape | what it is | ink mm² | OFF bare mm² (largest) | ON bare mm² (components) |
|---|---|---|---|---|
| `Sd1c37da7` | the S of ENTHUSIAST, half-width 0.87 mm | 28.77 | 0.67 (0.20) | **2.17 — 1.18 at (11.0, −2.6), 0.79 at (15.9, 1.5)** |
| `S6959709e` | the other S, half-width 0.87 mm | 29.19 | 0.49 (0.07) | 1.50 — 0.75 at (27.8, −2.6), 0.20, 0.14 |
| `S2eb316ce` | — | 48.31 | 0.49 | 0.49 (unchanged) |
| `Sa9b7eef9` | the i | 12.13 | 0.10 | 0.10 (unchanged) |

The lost element is the **1.18 mm² wedge in the lower bowl of `Sd1c37da7`** at
(11.0, −2.6) mm — the only component over 1 mm² the fixture has ever produced.
Its mirror in the upper bowl (0.79) and the other S's lower bowl (0.75) are the
same thing under the 1 mm² line.

Crops, OFF beside ON, the stitches drawn over the shape's polygon:

- `docs/renders/join-square-enthusiast-2026-10-07/crop_Sd1c37da7_off_on.png`
- `docs/renders/join-square-enthusiast-2026-10-07/crop_S6959709e_off_on.png`
- the whole wordmark: `enthusiast_off.png` / `enthusiast_on.png` in the same folder

## 2. The mechanism

`_split_sharp_corners`' join rule cuts a stroke where the spine turns at least
45° within 1.0 mm of a reflex artwork corner. At 80 mm a pull-comped inner bowl
of an S is exactly that — a sharp reflex vertex — so **each S is cut at both
bowls in BOTH arms**; the cut is not this flag's. What the flag changes is the
cut members' ends:

- **OFF**, each member keeps its medial axis's bend into the apex, the two bent
  ends meet, and the S sews as one continuous satin run.
- **ON**, `_straighten_member_end` fits a line over the stretch 1.5–4
  half-widths from the corner and projects the apex onto it. On the S the apex
  sits 0.80 / 0.82 mm off that line — **0.92 half-widths** — so both members'
  ends are moved almost a column's width, they no longer meet, the S breaks
  into 2–3 runs (+2–3 trims on the letter) and the bowl's wedge between the
  parted ends sews bare.

On Fremont's E the same projection moves an apex about 0.2 half-widths: the
arm's skeleton rounds its L-corner, it does not bend around a bowl. **A bend
is not a corner, and the flag could not tell them apart.**

### The three sibling bars are the same wedges

Enthusiast at 80 mm, the guard tests' own measurements (`tests/test_lettering_
coverage_regression.py`, `tests/test_satin_tip_caps.py`, `tests/test_rail_comp.py`):

| reading | bar | OFF | ON, no cap | ON, cap 0.6 |
|---|---|---|---|---|
| lost elements ≥ 1 mm² | 0 | 0 | **1** | 0 |
| uncovered ink fraction | ≤ 0.02 | 0.0184 | **0.0226** | 0.0185 |
| fine `lost_frac` (0.1 mm registration) | ≤ 0.17 | 0.1651 | **0.1702** | 0.1654 |
| tip-caps end bare, mm² | ≤ 9.5 | 7.77 | **10.53** | 7.77 |
| rail-comp worst mid-rail gap, mm² | ≤ 0.55 | 0.21 | **1.24** | 0.21 |
| satin bare %, all regions (`rail_edge`) | — | 3.44 | 4.26 | 3.44 |
| stitches / trims | — | 2614 / 15 | 2630 / 19 | 2612 / 15 |

The "mid-rail hole" of 1.24 mm² is the S wedge read by `bare_anatomy` as a
side component; the "end bare" rise is the parted ends. One mechanism, four
readings.

## 3. The cure reached for first was wrong

The obvious discriminator — a real corner is one sharp vertex, a bowl is a
spread of gentle ones — was measured over every accepted join corner on the
seven-logo set (`scratch_jse/vertex_census.py`; peak single-vertex turn, deg):

| logo | accepted corners | min | p25 | p50 | under 20° |
|---|---|---|---|---|---|
| enthusiast | 5 | 59.9 | 71.6 | 71.6 | 0 |
| fremont | 8 | 5.6 | 5.6 | 8.2 | 4 |
| becker | 6 | 60.7 | 64.5 | 87.5 | 0 |
| gaulke | 7 | 48.8 | 63.1 | 67.0 | 0 |
| drone | 18 | 52.7 | 83.8 | 90.6 | 0 |
| bridge | 32 | 28.6 | 107.7 | 142.6 | 0 |
| tires | 3 | 27.0 | 27.0 | 43.0 | 0 |

It separates enthusiast from Fremont perfectly and would refuse Becker's,
gaulke's and drone's REAL corners along with it: Fremont's corners are soft at
the vertex because its letters come through the raster skeleton of a 92.5 mm
patch, not because they are corners. Refuted; not built.

## 4. The discriminator that holds: how far the apex moves

Census of every `_straighten_member_end` call under the flag, apex move in
half-widths (`scratch_jse/offsets.py`):

| logo | calls | acted | p50 | p90 | max | > 0.5 h | > 0.75 h | half-width p50 mm |
|---|---|---|---|---|---|---|---|---|
| becker | 12 | 12 | 0.12 | 0.47 | 1.06 | 2 | 1 | 1.80 |
| bridge | 60 | 55 | 0.55 | 1.17 | 1.58 | 30 | 18 | 0.47 |
| gaulke | 14 | 14 | 0.72 | 1.20 | 1.35 | 10 | 7 | 0.61 |
| drone | 34 | 34 | 0.41 | 0.99 | 1.70 | 12 | 7 | 0.93 |
| **enthusiast** | 10 | 10 | **0.92** | 1.18 | 1.22 | 8 | 7 | 0.87 |
| **fremont** | 16 | 13 | **0.22** | 0.63 | 1.21 | 3 | 1 | 0.45 |
| tires | 4 | 4 | 0.25 | 0.92 | 0.96 | 2 | 2 | 1.63 |

The fixture the flip was made on sits at 0.22, the fixture it broke at 0.92.
The cap is set at **0.6 half-widths** between them. With it the census reads:
acted becker 11 / 12, bridge 28 / 60, gaulke 5 / 14, drone 22 / 34,
enthusiast 2 / 10, fremont 10 / 16, tires 2 / 4; the largest move that still
acts is 0.55 h. So the cap refuses about half the straightenings corpus-wide,
every one of them an apex over 0.6 half-widths off its own member's line.

## 5. The fix

`_STRAIGHT_MAX_MOVE_HALVES = 0.6` in `digitizer_core/stage6_satin.py`:
`_straighten_member_end` returns the member unchanged when the projection
would move its apex further than that. Under the cap the straightening is
byte-for-byte what it was. Tests: `tests/test_join_corner_bend_cap.py` (3) —
a bowl at 1.3 half-widths' radius keeps its bend, the same bend straightens
with the cap lifted and its shift is over the cap, an L's rounding at 0.45
half-widths still squares with its end on the line; `tests/test_join_corner_
straight.py` still pins Fremont's E (fans OFF, square ON, slab corners covered)
and now pins the default ON. The verification set with the default ON and the
cap — the lettering coverage guards, the tip-caps and rail-comp readings, the
join-corner, bend-cap, slab-serif and scope-budget files — reads
`32 passed in 125.90s`, `EXIT=0` (`scratch_jse/verify_on.log`, logged with
its own exit code, never piped).

## 6. Price — seven logos, flag ON, cap off against cap on

Corpus widths (`tools/thin_strokes.corpus_cases`): becker 100 mm, fremont
92.5 mm patch, the rest 80 mm left_chest. Satin bare is `rail_edge.bare_area`
over the text shapes; over-long is the pull-aware fan census from the n-fan
lane (`tools/fan_census.py`).

| logo | stitches | trims | satin bare % | over-long crosses |
|---|---|---|---|---|
| becker | 10,924 → 10,969 | 61 → 60 | 4.37 → **2.94** | 56 → 56 |
| bridge | 18,456 → 18,482 | 103 → 102 | 8.93 → **7.79** | 7 → 7 |
| gaulke | 4,559 → 4,569 | 34 → 34 | 5.28 → **4.59** | 2 → 2 |
| drone | 19,297 → 19,343 | 139 → 139 | 3.91 → **2.47** | 9 → 9 |
| enthusiast | 2,630 → 2,612 | 19 → 15 | 5.20 → **4.06** | 0 → 0 |
| fremont | 20,177 → 20,175 | 58 → 58 | 5.56 → 5.60 | 2 → 2 |
| tires | 2,869 → 2,864 | 8 → 7 | no text satin | 0 → 0 |

Bare falls on five of the six text logos and rises 0.04 points on Fremont;
trims never rise. **The promise the flip was made for is kept:** Fremont at
80 mm on this tree reads 18 fan ends over 33 text columns OFF and **16** ON,
with the cap and without it, at 13,731 stitches / 38 trims all three ways
(`tools/letter_band.fan_ends`; the 7 → 5 over 36 in the config docstring is
the pre-merge serif lane's reading of the same letters).

## 7. What this does not settle

- **Not sewn.** 0.6 half-widths is set on the census, between the two
  fixtures, not on fabric.
- The cap refuses 71 of 150 straightenings corpus-wide. Whether each refused
  one was a bend like the S's or a true corner the flip should have squared is
  not read per corner — only the price above (bare fell, trims did not rise)
  and the guards. A per-corner read is the next instrument if a render says
  otherwise.
- The join rule still cuts the S at its bowls in both arms; that cut is the
  corner rule's, and under `lettering_columns` the letter is cut from its
  outline instead, so it is not pursued here.
