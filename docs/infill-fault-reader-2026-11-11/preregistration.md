# In-fill reader: what is fixed before any score (2026-11-11)

The third reader scored against Kent's defect-marks pins, for **the same kind
of feature stitched in some places and not in others** ("extra in-fill, some
empty spaces have it while others don't"). Committed in its own commit BEFORE
the reader was run on any item that holds a selected pin. The harness is
`digitizer/tools/fault_reader_harness.py` (`--fault infill`), the reader
`digitizer/tools/infill_fault_reader.py`. Results go in
`docs/infill-fault-reader-2026-11-11.md`. Where this page says nothing new,
the letter reader's page (`docs/defect-marks-2026-11-10/letter-reader-preregistration.md`)
holds.

## This is not a hold-out: what was looked at first

The brief asked for the fault to be found in the stitches before the reader
was designed, so two pinned items were read at the pins (a probe on tree
`950855bf`, the stored designs, Kent's pin positions):

- `C_kanji_seal`, all 28 pins: the top thread is **white satin** (`0015
  White`, run kind `satin`) over pixels the source PNG leaves **transparent**.
  Stage 1's `bg_mask` reads those pixels as foreground (0.0 inside a 1 mm
  window at every pin); its prepped raster is one flat red, so the only thing
  telling ink from empty there is the alpha channel stage 1 did not follow
  into enclosed spaces.
- `C_devanagari_logo` pins 1, 5, 6: the same, white satin over transparent
  art with `bg_mask` 0.0 (pin 1 the bowl of the large "yu", 5 and 6 small
  counters of the grey line). Its pins 2, 3, 4, 7, 8 (pen_flow) sit on the
  letters' own satin.

In plain words: **"extra in-fill" is thread laid in a space the art leaves
empty, because the background mask never reached a space the ink encloses,
so the pipeline sewed it as a white shape, while the art's other empty spaces
stay bare fabric.** The reader was designed to find that, from the art's own
emptiness, never from `bg_mask`. Because the concept was read off the two
largest notes, a hit there shows the reader implements what was seen; the
candidate-pick null below asks the only question this record can: among the
places it could flag, does it flag the ones Kent pinned. A replication needs
a third sitting.

No other pinned item was opened at the stitches or the render. One more
look, also before any design: the run-kind COUNTS of the five sitting-2
designs with selected pins, to learn what "bean stitch" is in the stored
runs. `C_pixel_art_sprite` has 7 `border` runs (role `border`), no `run` or
`bean`; `C_gradient_mascot` has none of the three, so its "extra bean
stitch" is something the run kinds do not name (a predicted miss for the
rim rule unless the cover rule catches it). The reader's
constants were set and its bugs fixed on items with NO selected pin only
(listed under "Dev runs").

## Which pins count

The NOTE decides, the kind is a hint. Items `L_*` (sitting 1) and `C_*`
(sitting 2). Case-insensitive, `fault_reader_harness.infill_reason`:

1. **A contrast between places** in the note: "some ... while/others", "only",
   "doesn't/don't/does not/do not match", "different from", "inconsistent
   from", "look/be the same", "select spots" — and the note does not name the
   pro ("pro"/"pros": a comparison with the pro's file, not between places;
   MFab 3 "doesnt match the pros" is out).
2. **OR the fault's own name**: "in-fill" / "infill".
3. **A thread-colour note is out** ("color"/"colour"): different colours on
   two like features is a colour fault (`C_gradient_mascot` 2, "feet are
   different colors, they should be the same").
4. **Pins the edge or letter rule claims stay with that reader** (none of the
   admitted pins is claimed; the test checks).
5. **Shorthand.** (a) A range in an admitted note ("#1-#28", "(#5-#6)",
   "for 7-8", spaces allowed) covers those pins of that item that carry no
   note of their own, whatever kind they carry. (b) The edge rule's "same
   issue / same for" inheritance, for bare pins (no note, no kind), when the
   donor is admitted. Each pin records `note_pin`, the pin whose note
   admitted it.

The kind `extra` alone admits nothing: `C_low_poly`'s seven "Random Black
Spot" pins (strays) and `C_isometric_icon` 7 ("does not portray the image
definition") are out; so is `L_becker_hat_large` 17 ("directions ... very
inconsistent here": one place, no other named).

Lists (`pins-sitting-1.json`, `pins-sitting-2.json`, pinned by
`digitizer/tests/test_infill_fault_reader.py`):

| item | pins | notes | note (abridged) | can the reader see it? |
|---|---|---|---|---|
| `L_bridge_hat` | 1 | 1 | wheel handles look different from each other | no: shape |
| `L_bridge_hat` | 4 | 1 | the only letter thinly stitched | no: width |
| `C_kanji_seal` | 1-28 | 1 | extra in-fill, some empty spaces have it | yes: cover |
| `C_devanagari_logo` | 1 | 1 | the only lettering in-fill | yes: cover |
| `C_devanagari_logo` | 5, 6 | 1 | in-fill only in select spots | yes: cover |
| `C_pixel_art_sprite` | 1 | 1 | bean round some openings, not others | yes: rim, if those openings are empty in the art |
| `C_gradient_mascot` | 1 | 1 | extra bean stitch, unlike the right nostril | maybe: rim (its design has no run/bean/border run) |
| `C_flat_emoji_icon` | 3 | 1 | right leg infill doesn't match left | no: fill direction |

**36 pins, 6 items, 8 notes.** Three notes (Bridge 1, Bridge 4, emoji 3) name
features this reader does not read; they stay in the score as predicted
misses rather than be dropped after the fact.

## What the reader flags

Candidate features: the art's **empty spaces**. Empty = alpha under 128 where
the art carries a real alpha channel; otherwise within 32 RGB of the median
colour of the art's outer 2-pixel frame. Read from the source art, resized
onto the prepped raster (refused unless the resize is isotropic within 1%),
warped into the render's 12 px/mm grid through the plan's frame (the letter
reader's warp; outside the art counts as empty). An item is refused unless at
least 90% of stage 1's `bg_mask` is empty in that raster (registration).
Spaces are 4-connected; a space is judged when its interior (pixels more than
half a thread, 0.2 mm, inside it) is at least 0.25 mm2.

Rasters of our render: every filament of the stored design at
`render_design`'s width and endpoints, in sew order, as its thread class and
as its run's kind (`fill`, `satin`, `run`, `bean`, `border`, `travel`,
`underlay`), no anti-alias: the top of each pixel is known.

1. **Cover.** `infill` = at least half the interior carries thread AND its
   commonest thread class differs from the commonest class on the ring within
   0.6 mm outside it; `closed` = covered in the surrounding ink's own colour
   (a counter lost: the letter reader's fault, not judged here); `matched` =
   an `infill` whose thread is within 32 RGB of the art's empty colour (a
   white field on a white page; alpha art has no empty colour, so never),
   not judged; `bare` = under half carries thread. The group is all judged
   spaces of the design; its treatment is whichever of `infill` / `bare` has
   more interior area (in practice the outer background, bare). Each judged
   space treated otherwise is flagged; strength = its interior area, mm2. In
   practice this flags every empty space filled in a colour the art does not
   show there.
2. **Rim.** For BARE enclosed spaces (openings showing fabric; not touching
   the render frame, not the largest): `outlined` = at least 25% of the band within 0.4 mm of its edge
   (both sides) is topped by a line run (`run`, `bean`, `border`); `plain` =
   at most 5%. The group's treatment is the one with more rim length; the
   others are flagged; strength = rim length, mm.

Flags sit at the space's deepest interior point, in the pins' frame. Not read:
fill direction, stitch type inside ink, thread colour, shape, width.

## Scoring

- **Radius 3.0 mm** (the earlier readers' verdict radius; kept so the three
  are comparable). 2.0 and 5.0 reported, never the verdict.
- **Candidate set** (written by the reader beside its flags): every judged
  space (`infill` or `bare`) except the design's largest, which sets the
  cover group's treatment and is never flagged in practice. One anchor per
  space (its flag point), plus a mask of their interiors.
- **Nulls**, each the hit rate the SAME flags would get from random pins:
  - `chance_pick` (**the verdict's null**): each pin placed on a candidate
    anchor drawn uniformly. Exact (mean over all anchors). It cannot be
    fooled by a band: it asks whether, among the places this reader could
    flag, Kent's pins fall on the flagged ones.
  - `chance_cand`: random points uniform over the candidate interiors.
  - `chance_area`: random points on all thread (the earlier readers' null).
  - `chance_edge`: random points on thread within 1 mm of fabric. Reported,
    not used: it is the right null only for faults at fabric edges, and is 0
    by definition when every flag is deeper than the radius inside a sewn
    field (the 0.00 on `L_bridge_hat` and `C_silhouette_logo`; explained in
    `edge_band`'s docstring and pinned by a test; #1388 and #1389's figures
    do not move).
- **Precision**: the share of flags (items with selected pins only) within
  3 mm of a selected pin, beside `precision_pick`, the share of candidate
  anchors within 3 mm of one (what a reader flagging the same number of
  candidates at random would get), flag-weighted, item-bootstrapped.
- **Weighting**: per pin (the harness's pool, pin-weighted, as before) AND
  per note (each note weighs one: its pins' hit rate against its item's
  null). 28 pins from one note are one judgement; **the per-note figure is
  the verdict's figure**.
- Intervals: 95% bootstrap over ITEMS (5,000 draws, seed 20261110), an item
  drawn brings all its notes.

## What counts as shown

All of, at 3.0 mm, against `chance_pick`:

1. at least **4 items with selected pins** scored (not refused);
2. per-note hit rate above `chance_pick` with the item-bootstrap 95% lower
   bound above 0;
3. the per-pin pool's lower bound above 0 as well.

**Expected at this n.** Selected pins sit on 6 items, 3 of whose notes are
predicted misses, and one item (kanji) holds 28 of 36 pins. The interval will
be wide. If fewer than 4 items are scored, or the interval crosses 0, the
verdict is **"cannot tell at this n"**, and the page reports instead: the
per-item and per-note rows, how many of the 8 notes beat their item's
`chance_pick`, precision beside `precision_pick`, the misses, and the
strongest unpinned flags. No constant is changed after the first scored run.

## Runs

Reader on every item of both kits that has a stored design and a job (the 11
`L_` pro jobs of sitting 1, the 21 `C_` corpus rows of sitting 2), tree
`950855bf` (the primary checkout, untouched), each refused unless its
re-run's stitches equal the stored design's. Items without a selected pin
are not scored; their flag counts are reported to show what the reader says
where Kent did not point at this fault.

## Dev runs (no selected pin)

Six items with no selected pin, run while the reader was built
(`C_outline_lineart_logo`, `C_neon_outline_sign`, `C_heraldic_crest`,
`C_arabic_calligraphy`, `L_toat_machine_hat`, `L_becker_hat_large`). All six
re-ran to the stored stitches and registered (`bg_mask` empty share 0.983 to
1.0). Two changes came out of them, both before this page:

- **`matched`.** On `C_outline_lineart_logo` (white page, white thread, Kent:
  Great) the first version called the sewn white eye field and the white
  letter counters "in-fill" (8 flags). A space sewn in a thread within 32 RGB
  of the art's own empty colour now reads `matched` and is not judged. Alpha
  art has no empty colour, so this cannot touch a transparent-art item.
- **Rim on openings only.** The same item's letter counters carry the art's
  own grey keyline and were flagged as "outlined" against the plain eye field
  (3 flags). The rim rule now reads only BARE enclosed spaces (openings that
  show fabric), which is what "interior openings" are.

After the changes the six carry: lineart 4 flags (small white gaps filled by
the grey keyline thread, 0.35-0.51 mm2), neon 1 (the counter of the "d"
sewn white while the "a"'s is bare: the kanji pattern, on an item whose pins
the rule does not select), heraldic 1 (one of two mirror-image spaces sewn
in another colour, its twin closed in the surrounding colour), arabic 0, TOAT
machine 0 (its white field is `matched`), Becker 5 (its five large
transparent interiors, all sewn white).

**A known false-alarm class, left in on purpose:** Becker fills EVERY
enclosed transparent space with white, consistently, and Kent pinned none of
it. The cover rule flags it because the art's own treatment of empty is bare
and Kent's words for this family call the PRESENCE the fault ("extra
in-fill", "the only lettering in-fill", "extra bean stitch"). Comparing
enclosed spaces only among themselves would spare Becker, but its direction
would then depend on whether filled or bare spaces are the majority on each
design, which could not be checked on the pinned items without reading the
answer. Becker carries no selected pin, so this class costs no precision
figure here; it is reported in the flag counts.
