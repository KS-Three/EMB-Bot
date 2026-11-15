# `photo_work_grid`: the evidence for Kent's ruling (2026-11-14)

**What the flag does.** `cfg.photo_work_grid` (default OFF since 2026-11-05)
lets the photo classes take the 8 px/mm working grid that line art takes.
OFF, a `photo_scene` / `photo_subject` design stays on its source line
(`config.work_grid_px_per_mm`). Stage 1 only ever ENLARGES to the grid, so
the flag can move a design only where the source delivers under 8 px/mm at
the chosen size.

**Why it matters.** MFab's hat logo classes `photo_scene` at every size.
At some sizes its small line "AND WELDING LLC" loses W, E (and L) under a
white slab: on the source line the W-E(-L) letters fuse into one untagged
black region, which is no rider, so the under-fill merges it into the black
host and the white panel sews over it (memory `mfab-photo-route-2026-11-04`;
`eye_pairs_out/eye-sweep-1114/REPORT.md` Trace 2).

**Answer.**
- **MFab:** ON fixes the slab where OFF has it (60, 85.1, 96, 100.8 mm). But
  it **puts a slab over the E at 113.5 mm**, where OFF was clean. The W at
  85.1 and 96 comes back as a broken black zigzag, not a W, and a white blob
  appears on the left of the A at 100.8 and 105.3. The fault moves with
  where the resample lands: neither grid is safe at every size.
- **Every other photo-lane design in the kits and the scorecard set: 19.**
  16 are byte-identical by construction (their source is already 9.5-26
  px/mm at the size used). Three move: chrome specular, owl pale and
  region blobs (6.2-7.2 px/mm at 80 mm). Chrome reads clearly better ON,
  the owl is the same, and **region blobs reads worse ON**.
- **Recommendation: do not flip on this evidence.** The flag trades
  MFab's 100.8 slab for a new one at 113.5, the pro's own hat size. The
  cause is upstream of the grid: a small-line letter that reaches stage 5
  untagged is swallowed by the under-fill. A guard there (an untagged black
  region that the white panel would cover with no hole) would fix every
  size on either grid.
- **The spike under the M** is in BOTH arms (a black wedge from the M's V
  down into the A-N junction of "AND"), larger ON. It is NOT geometry:
  traced at 85.1 ON (`sheets/mfab_85.1_ON_spike_trace.png`), the stage-4
  and stage-5 polygons keep the white keyline between the V and the N, and
  the black thread is laid across it in the stitches (stage 6/7: black
  sewn over the white keyline). No fix in this PR; OFF is untouched.

Instrument readings, n = 1 per arm, on a laptop shared with about ten other
sessions. Seconds are wall clock and move 2-4x with load; CPU seconds are
the steadier reading.

## MFab: art | OFF | ON | pro

Sheets: `digitizer/eye_pairs_out/photo-grid-1114/sheets/mfab_<width>_*` in
the primary checkout. `*_off_on_pro.png` holds the whole design (pro at its
own size); `*_smallline_off_on.png` zooms on "AND WELDING LLC".

| width (garment) | px/mm OFF -> ON | small line OFF | small line ON | text-tagged OFF / ON | stitches OFF / ON | trims OFF / ON | CPU s OFF / ON | wall s OFF / ON | grade OFF / ON |
|---|---|---|---|---|---|---|---|---|---|
| 60.0 (hat) | 6.73 -> 8 | letters hollow, white over W, E, L | **readable** | 4 / 13 | 7882 / 8819 | 9 / 15 | 7.8 / 25.3 | 19.8 / 89.9 | B 76 / B 76 |
| 85.1 (hat) | 4.75 -> 8 | **W, E under a slab** | E back, W a broken zigzag | 14 / 18 | 14983 / 15418 | 22 / 20 | 20.5 / 31.4 | 57.6 / 64.3 | A / A |
| 96.0 (left chest) | 4.21 -> 8 | **W, E under a slab** | E, L back, W a broken zigzag | 14 / 18 | 17422 / 17881 | 21 / 19 | 30.4 / 41.3 | 75.0 / 89.4 | A / A |
| 100.8 (hat) | 4.01 -> 8 | **W, E, L under a slab** | **readable**; white blob on the A | 15 / 15 | 19369 / 19173 | 25 / 21 | 26.3 / 40.5 | 87.0 / 138.9 | A / A |
| 105.3 (hat) | 4.0 -> 8 | readable | readable; white blob on the A | 17 / 16 | 20579 / 20140 | 28 / 21 | 50.9 / 39.4 | 249.5 / 186.6 | B 88 / A 100 |
| 113.5 (hat) | 4.0 -> 8 | readable | **E under a slab** | 16 / 24 | 22789 / 24106 | 20 / 26 | 48.0 / 54.8 | 194.4 / 140.9 | **A 100 / D 58** (+ DENSITY_STACKED, LETTERING_TOO_SMALL) |

Grades mostly miss the slab: at 85.1, 96 and 100.8 OFF sews "A" with W and
E gone, which is its own preflight gap. At 113.5 ON the grade does fall,
A 100 to D 58, on density stacking and lettering too small.

**Seconds.** ON costs CPU where it adds regions (60 mm: 24 -> 36 regions,
7.8 -> 25.3 CPU s; 96 mm 30 -> 41) and saves it at 105.3 (51 -> 39). The
sweep's 213 -> 52.5 s at 85.1 did not reproduce: 57.6 -> 64.3 s wall here.

## The other photo-lane designs

Classified at stage 0 (`tools/photo_grid_compare classify`): 62 candidates.
They are the 26 scorecard fixtures, the 11 pro jobs and 4 photos of the
11-10 kit, and the 21 Commons items of the 11-11 kit. 20 take the photo
lane. Working px/mm at the size each kit or the scorecard uses (`prep`,
OFF and ON):

| design | source px/mm | OFF -> ON | moves |
|---|---|---|---|
| fur_ramp, photo_dof_meadow, photo_grass_macro, photo_scene_stub, photo_subject_stub, photo_sunset_backlit (scorecard, 80 mm) | 9.5-12.5 | same | no |
| bw_street, night_neon, architecture, landscape_lake (11-10 kit) | 23.8-26.2 | same | no |
| halftone_dots, duotone_poster, comic_halftone, vintage_engraved_badge, kanji_brush, chalkboard_lettering (11-11 kit) | 13.9-24.7 | same | no |
| photo_chrome_specular (scorecard, 80 mm) | 6.5 | 6.5 -> 8 | **yes** |
| photo_owl_pale (scorecard, 80 mm) | 6.25 | 6.25 -> 8 | **yes** |
| region_blobs (scorecard, 80 mm) | 7.15 | 7.15 -> 8 | **yes** |

"Same" is byte-identical by construction. The flag reaches the engine only
through `work_grid_px_per_mm`, whose three readers compare the source
against the grid: stage 1's enlargement, the alpha extension gate and
preflight's lettering note. At 9.5 px/mm and up each comparison reads the
same against 4 or 8.

The three that move, at 80 mm left chest:

| design | stitches OFF / ON | trims OFF / ON | grade (score) OFF / ON | CPU s OFF / ON | by eye |
|---|---|---|---|---|---|
| photo_chrome_specular | 36052 / 32375 | 85 / 53 | B 76 / B 88 | 95.6 / 68.8 | ON better: OFF cuts a dark slit into the sphere's right and a ragged hexagon into the background; ON one clean sphere. ON loses the two small highlights. |
| photo_owl_pale | 24873 / 24471 | 9 / 8 | A 100 / A 100 | 19.0 / 13.1 | the same; only the fill direction changes (diagonal OFF, level ON). Both sew a pale rectangle, not the owl's silhouette. |
| region_blobs | 18954 / 18956 | 28 / 17 | A 100 / A 100 (+ SATIN_GAPS_TIGHT) | 29.1 / 30.6 | **ON worse:** green's halo floods the space between the blobs and red's core darkens. OFF keeps three distinct blobs. |

## Not done

- **The spike under the M** (both arms; larger ON) enters at stage 6/7, not
  in the polygons. Which emitter lays the black across the keyline, and in
  what order against the white, is the next step.
- **The real fix:** keep an untagged small-line region from being swallowed.
  Either tag it (the text cluster's own rule fails on the fused W-E-L), or
  give the white panel a hole wherever the under-fill merges a black region
  that the panel covers. Either one would settle MFab on both grids.
- Hat-front arms for the three photo movers: only left chest was run, for
  time.
