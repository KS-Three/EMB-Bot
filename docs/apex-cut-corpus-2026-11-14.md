# `lettering_columns_apex_cut`, OFF | ON over the lettering corpus (2026-11-14)

The flip table for `lettering_columns_apex_cut` (built OFF 2026-10-25). ON,
where two strokes of a letter meet at an acute tip (the M's V, a W's apexes,
a pointed A or N, a Z's corners), the tip sews as ONE column whose crosses
span both strokes, the way the pro's DSTs sew it. OFF, the Column lane mitres
the tip into two fanning half-width columns or pivots one column through it.
`docs/satin-flat-ends-2026-11-14.md` found it cures Kent's four Z-joint pins
on and_pizza. This page covers every other design it touches.

**Verdict: 43 designs, 25 moved. By eye, 10 better, 10 the same, 1 mixed,
4 worse.** One of the worse is a large regression (outline_lineart_logo).
Not a clean flip as built.

## Method

- Tree: origin/main d0b4981a, default config; the only change is the flag.
- Designs:
  - every 1112 lettering logo (`lt_*`, 80 mm left chest);
  - every pro job at the pro's own size and garment (Becker x5, Bridge x2,
    Gaulke x3, Hotel Fremont x2, MFab x2, Precision Drone, ProSeal x2,
    Tires, Golden Tee, To-a-T x3);
  - the 12 Commons corpus pictures (80 mm left chest).
- One digitize at a time (`tools/jag_strips.py capture`).
- **Skip rule:** a design whose OFF run tags no lettering shape
  (`text_candidate` / `lettering_group`) never reaches the Column lane, so
  apex_cut cannot act there. Its ON run is skipped and counted "same":
  tires_hat_3d, devanagari_logo, kanji_seal, neon_outline_sign.
- "Moved" = the md5 of the stitch list differs.
- Each moved design gets two pictures (primary checkout, gitignored,
  `digitizer/eye_pairs_out/jag-source-1113/apex-corpus/sheets/`):
  - `<name>_off_apex.png`: the whole design OFF | ON at 16 px/mm, with its
    three most-changed 8 mm windows boxed and zoomed 2x;
  - `<name>_dir.png`: the same windows lit, beside a direction view (each
    stitch one line, hue = its angle). Black thread on black thread hides
    the change in a lit render; the direction view shows it.

## What moved

| design | stitches OFF -> ON | trims | verdict | why |
|---|---|---|---|---|
| becker_hat_large | 16289 -> 16320 | 12 -> 12 | **better** | MARINE's M: the V sews as one even column, not two fans. |
| becker_lc_large | 14951 -> 14700 | 13 -> 13 | **better**, one catch | The fan and stray line at the M's top-left are gone. Catch: three small slits on the M's right V edge. |
| becker_hat_small | 10576 -> 10574 | 12 -> 13 | **better** | The white slits across the M's top are gone; the top is solid. |
| becker_chest_small | 10339 -> 10364 | 12 -> 13 | **better** | Same as hat small. |
| becker_beanie | 13902 -> 13921 | 16 -> 17 | **better** | Same as hat small. |
| bridge_lc | 10998 -> 10990 | 13 -> 13 | **better** | Two teal ring letters lose crossed blocks; each sews as one column. |
| bridge_hat | 8569 -> 8581 | 12 -> 13 | **better** (slight) | One teal ring letter's crossed block becomes one column; the rest is unchanged. |
| proseal_hat | 6434 -> 6485 | 46 -> 46 | **better** | The A's apex is one column across both legs, as the pro sews it; the seam at the top is gone. |
| proseal_beanie | 7785 -> 7805 | 39 -> 39 | **better** | Same A. |
| duotone_poster | 52310 -> 52288 | 195 -> 196 | **better** | The N in "JUN" lost a long bar stitch on its diagonal; the diagonal now sews as a column. |
| gaulke_roofing_hat | 7494 -> 7512 | 33 -> 32 | same | Black on black, no change readable. The direction view shows each N's diagonal sewn with level crosses plus a short zigzag at its top join. |
| gaulke_roofing_lc | 5852 -> 5870 | 24 -> 24 | same | As the hat. One small gain: the slanted spur at the N's foot is gone. |
| gaulke_roofing_beanie | 7679 -> 7675 | 26 -> 26 | same | As the hat. |
| hotel_fremont_hat | 16106 -> 16106 | 28 -> 28 | same | The M's V and the N's foot re-sew as one column; nothing reads differently. |
| hotel_fremont_patch | 15061 -> 15068 | 23 -> 23 | same | As the hat. |
| mfab_hat | 20849 -> 20882 | 17 -> 17 | same | The W and N tips re-sew; black on black, no visible change. |
| goldentee_hat | 13636 -> 13642 | 45 -> 45 | same | One script join fans slightly differently. |
| chalkboard_lettering | 28285 -> 28293 | 109 -> 109 | same | No visible change. |
| silhouette_logo | 25036 -> 25032 | 39 -> 37 | same | The white A's apex is a little tidier; nothing readable. |
| vintage_engraved_badge | 33241 -> 33243 | 237 -> 238 | same | No visible change. |
| lt_and_pizza | 2454 -> 2539 | 5 -> 6 | mixed | Kent's Z pins cured: joints and bottoms flat and square. But the first Z's top-right corner rounds into a fan, and there is a small stub at the second Z's top-left. |
| mfab_lc | 17897 -> 17832 | 20 -> 20 | **worse** (slight) | A rounded lump on the W's middle apex where OFF ran straight, and a pin-hole gap at the N's foot. |
| lt_k_line | 3372 -> 3341 | 10 -> 10 | **worse** | The K's lower leg-to-foot junction becomes a messy fan. The N's diagonal ends on a step of level crosses. |
| precision_drone | 14984 -> 14957 | 93 -> 93 | **worse** | The N's diagonal turns to level crosses, which is fine, but two long stitches now lie across the left stem's top join. |
| outline_lineart_logo | 14496 -> 14183 | 37 -> 39 | **worse** (badly) | The white outline strokes are line art tagged as text. ON, they turn into long single bars across the black. |

**Unchanged (md5 same), 18:** the four skips above, lt_ahora, lt_bukit_asam,
lt_but_seriously, lt_dot_music, lt_hed_p_e, lt_jakarta, lt_n_sync,
arabic_calligraphy, comic_halftone, distressed_grunge, kanji_brush,
toat_beanie, toat_machine_beanie, toat_machine_hat.

Seen in passing: three lettering logos tag no lettering shape at all
(lt_ahora, lt_but_seriously, lt_hed_p_e: 0 text shapes), so no lettering
flag can reach them.

## What it means for the flip

The gains are real: the M's V on all five Becker sizes, ProSeal's A, Bridge's
ring letters, and Kent's own Z pins on and_pizza. They line up with what
the flag was read off, the pro's one column through every tip.

The losses are not noise:
- **outline_lineart_logo** is the largest change in the table, and for
  the worse. The tip rule acts on line art the lettering tagger took for
  text, and makes crosses far longer than any stroke.
- **k_line**: the K's leg junction.
- **drone**: two stitches laid across a stem.
- **mfab_lc**: small.

Each would want a guard before a flip, for example refusing a merged tip
whose crosses run past some multiple of the stroke width, or reading only
tips whose two strokes are both column-width. Those guards are not built
here.
