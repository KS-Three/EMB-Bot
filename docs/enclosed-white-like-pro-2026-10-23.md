# Enclosed white like the pro: the census (2026-10-23)

Kent held `sew_enclosed_white` OFF on 2026-10-23 because the flip sheet showed
MFab at 25,512 stitches ON against the pro's 17,568 (Becker 8,512 against
8,694, Fremont unchanged), and asked for ON to sew the whites the pro sews and
skip the ones he leaves to the garment. This is the census that answers which
whites those are, on every paired job in `Embroidery Files.zip`, and what the
MFab overshoot actually is.

**Method.** Each job digitized the Studio's way (`tools.pro_pair.digitize`, the
hat preset, the pro's width; Fremont at Kent's 92.5) OFF and ON. Every
`enclosed_background` region of the OFF result is one row. Our OFF DST is
registered to the pro's DST (`tools/pro_parity/pairframe.register_pair`: one
scale, a y-flip search, a translation search), the region's polygon is carried
into the pro's frame, eroded 0.35 mm, and "pro thread" is the share of that
polygon within 0.25 mm of a stitch line in his file (10 px/mm raster). The
instrument is calibrated on our own sewn, non-enclosed regions of the same job:
the pro's thread covers 98.4-100% of those on every job (`calib` below), so a
white reading 1.0 is sewn and one reading 0.1-0.4 is bare fabric with his
satin bleeding over the eroded edge (Becker's A counter reads 0.52 because his
satin is wider than ours; the crop shows it open). Registration IoU 0.64-0.98.

Crops (art | ours ON | pro, 40 px/mm): `docs/renders/enclosed-white-like-pro-2026-10-23/`.

## The census

Class is read from the tags and the crop: *hollow letter body* = the region is
itself a text-cluster letter (Becker's BECKER interiors inside the black
keyline); *letter counter* = the region's holder is a text-cluster letter;
*band* = a keyline ring; *script loop* = a hole in a connected script word the
text cluster does not tag; *speck* = under 2.5 mm² with no holder at 62.6 mm.

| job (width mm) | region | mm² | min dim mm | holder | class | ON today | pro thread |
|---|---|---|---|---|---|---|---|
| MFab (104.9) | Sfbae5fe3 | 867.8 | 3.56 | untagged ring 1082 mm², 17 holes | band | sews | 1.00 |
| MFab | S091d4ef1 | 11.0 | 2.35 | the band | field | sews | 1.00 |
| MFab | S355be2ba | 25.0 | 4.01 | letter (A) | counter in band | sews | 1.00 |
| MFab | Sc0afb937 | 14.1 | 1.78 | letter | counter in band | sews | 1.00 |
| MFab | Se7a8de74 | 8.8 | 1.13 | letter | counter in band | sews | 1.00 |
| MFab | Sf18eda3e | 8.7 | 1.16 | letter | counter in band | sews | 1.00 |
| Becker hat (76.5) | S1c041c47 | 217.8 | 5.42 | — (is a letter) | hollow letter body (B) | sews | 1.00 |
| Becker hat | S466091d1 | 216.8 | 6.06 | — | hollow letter body | sews | 1.00 |
| Becker hat | Sc32ce326 | 201.6 | 4.30 | — | hollow letter body | sews | 1.00 |
| Becker hat | Se1db73b6 | 126.4 | 4.54 | — | hollow letter body | sews | 1.00 |
| Becker hat | Sa0252bdc | 118.1 | 4.46 | — | hollow letter body | sews | 1.00 |
| Becker hat | Sf9f6e7b6 | 6.0 | 1.94 | letter (A of MARINE) | letter counter | open | 0.52 (open, his satin wider) |
| Becker hat | S38e8c06e | 5.6 | 2.45 | letter (R) | letter counter | open | 0.17 |
| Becker LC (76.5) | same seven regions | | | | | same | same (1.00 ×5; 0.53, 0.19) |
| Gaulke hat (114.2) | 10 regions | 0.6-10.6 | 0.8-3.2 | letter (O, D, R, B, …) | letter counter | open | 0.10-0.39, one 0.67 at 0.6 mm² |
| Fremont hat (92.5) | none | | | | | ON = OFF | |
| Drone hat (62.6) | 6 regions | 0.9-4.2 | 0.65-1.4 | letter | letter counter | open | 0.58-1.0 (unreadable: he relaid the text) |
| Drone hat | 4 regions | 0.4-2.1 | 0.5-1.0 | none / 2 mm² | speck | sews (+128 st) | 1.0 ×3, 0.08 |
| Tires hat (114.3) | Sdd5f3db3 | 43.1 | 5.77 | untagged script word 925 mm² | script loop | **sews** | **0.09 (open)** |
| Tires hat | Sf41eecf1 | 28.2 | 3.61 | same word | script loop | **sews** | **0.08 (open)** |

Drone is excluded from the rule's evidence: the pro redrew the whole design
(rule R15, `docs/pro-digitizer-rules-2026-10-21.md`), raised the small text and
laid his thread where ours is not, so his coverage of our 0.4-4 mm² specks says
nothing about his choice of whites.

## The pro's rule

**He sews every enclosed white that is a body or a field (a hollow letter's
interior, a keyline band, a badge field: 11 of 11, 11-868 mm², no size
threshold) and leaves open every counter of a letter (21 of 21 readable, 0.6-43
mm², 0.8-5.8 mm across), unless the white around that letter is itself sewn, in
which case the counter sews with it (MFab's four).** The decision is by ROLE, not
by size: Tires' 43 mm² loop stays open and MFab's 8.7 mm² counter sews.

That is the rule `enclosed_white.plan_enclosed_white` has carried since PR
#1031. It agrees with the pro on 32 of the 34 readable rows. **The two rows that
contradict it are Tires' script loops:** the text cluster does not tag a
connected script word as lettering (no `text_candidate`, no `lettering_group`,
no `word_id`), so its two loops read as fields and sew white where the pro
leaves fabric. The engine has no signal today that says "this 925 mm² blob is
a word"; a hole-to-holder area ratio would separate these two (3-5%) from the
sewn fields (80% and above) but would also leave a white star inside a black
badge unsewn, which is a field the pro sews, so it was not built. ON changes
Tires by +21 stitches and +3 trims; the miss is visible in the preview and
immaterial in the count.

## Where MFab's overshoot is

Not in the selection: the pro sews all six of MFab's whites. It is in the
construction of the one band. Per block, from the DSTs:

| | stitches | thread mm | median stitch | under 1 mm | trims |
|---|---|---|---|---|---|
| pro, white (blocks 2 + 4) | 6,672 | 13,813 | 2.12 / 1.46 | 468 | 6 |
| ours ON, white, less the OFF white letters | 12,470 | 21,381 | 1.46 | 5,785 | 78 |

The band (868 mm², a keyline ring with 17 holes, ribbon width 3.56 mm) already
takes the SATIN tier in our engine, and that is the cost: its medial axis
breaks at every letter corner into **253 satin columns** (median 24 points, so
about 5 mm each), each with its own zigzag underlay (203 underlay runs, 1,837
points), travel between them (159 runs, 793 points) and 34 trims. Parallel
branches of that skeleton overlap, so the band carries 11,204 stitches where a
single satin pass at 0.4 mm over a 244 mm band would carry about 1,800. The pro
sews the same band as one continuous keyline: columns running along the band
with the outer edge and the letter edge as rails, mitred at the corners
(`mfab_band_M_pro.jpg` beside `mfab_band_M_ours_on.jpg`).

So the white class that still differs is **a keyline band around lettering**,
and the difference is satin construction on a ring with holes, not which white
is chosen. A keyline satin whose rails are the band's two edges is stage-6
work (the skeleton-rail model is the known limit, memory
`lettering-architecture-2026-10-07`), not this option's.

**The other tier does not help either.** The band pinned to the FILL tier
(`shape_overrides {"Sfbae5fe3": {"tier": "fill"}}`, everything else as ON)
gives 23,564 stitches and 109 trims: the tatami is cut by the same 17 holes
into 719 fill runs (8,870 points), with 33 trims on the one shape. The holes are
the problem on either tier. And the pro's own white is not cheap: his two white
blocks are 6,672 stitches for about 930 mm² of visible white, which only fits
one layer if his white runs UNDER the black letters as one holeless shape (rule
R13, big fill first), about 1,970 mm² at 3 stitches per mm². That is the
"sewn field ignores the holes later layers cover" follow-up #1031 named, and it
would trade the 253 columns for one shape; at our stitch length (median 2.1 mm
against his 3.4 in black) it still lands near today's count, so it does not
reach the 10% on its own. Stitch length as density is gate 1.

## Stitches and trims, OFF | ON | pro

Ours from the plan, the pro's from his DST (never the PES: trims differ).

| job | width | OFF | ON | pro | ON / pro |
|---|---|---|---|---|---|
| MFab hat | 104.9 | 13,721 / 68 | 25,512 / 110 | 17,568 / 19 | 1.45 |
| Becker hat | 76.5 | 5,928 / 16 | 8,512 / 23 | 8,694 / 11 | 0.98 |
| Becker LC | 76.5 | 5,410 / 16 | 7,949 / 23 | 8,694 / 12 | 0.91 |
| Gaulke hat | 114.2 | 7,955 / 37 | 7,955 / 37 | 6,138 / 42 | — (no enclosed white sews) |
| Fremont hat | 92.5 | 18,611 / 55 | 18,611 / 55 | 17,067 / 21 | — (no enclosed region) |
| Drone hat | 62.6 | 14,802 / 122 | 14,930 / 126 | 14,552 / 59 | 1.03 |
| Tires hat | 114.3 | 8,075 / 10 | 8,096 / 13 | 5,555 / 10 | 1.46 (OFF is 1.45) |

Becker LC's pro file (`beckers logo LC 2 A.DST`) carries the same stitch count
as the hat's, so the two Becker rows are one design at two garments.

## What this changes

- **No change to the selection.** The rule the option carries IS the pro's rule
  on every readable row but Tires', and the two Tires rows need a lettering
  signal the engine does not have, not a threshold. Nothing in `src/digitize.js`
  either: the Studio sends `sew_enclosed_white` to the service, the browser
  engine has no enclosed-white selection, so there is no JS twin to keep in step.
- **The Tires miss is pinned as a strict xfail**
  (`tests/test_sew_enclosed_white.py::test_a_loop_in_an_untagged_script_word_stays_open`):
  it turns into a failure the day the tagger marks a connected script word as
  lettering, which is when the mark comes off.
- **MFab's overshoot is renamed.** It is not "sews whites the pro skips"; it is
  "sews the right band 1.9x as dense as the pro, in 253 pieces". The lever is
  a keyline satin whose rails are the band's edges (or the holeless under-fill
  of R13), and the stitch-length gap under gate 1. Neither is this option.
- OFF is untouched: no engine file changed.

## Census tooling

The census script and the registered-coverage reader are the session's
scratch (`census.py`: `pro_pair.digitize` OFF and ON, `pairframe.register_pair`,
a 10 px/mm line raster of the pro's DST, `shapely.maximum_inscribed_circle` for
the smallest dimension); not committed, because it duplicates `pro_pair` and
`flip_sheet_renders` for one question. Its per-job JSON is reproducible from
those two tools and the numbers above.
