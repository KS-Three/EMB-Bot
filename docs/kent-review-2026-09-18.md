# Kent's review, 2026-09-18 — six pending flags, labelled before | after

**Result: at full-design view, the six pending default-OFF flags do not change
how any of the nine real logos look.** Kent called 29 of 34 pairs "no
difference". **Kent's ruling: record it and stop.** All six flags stay OFF,
which is their default, so no config changes.

## What was shown

- **Logos:** the nine `tools.thin_strokes.corpus_cases()` real logos, each at
  its `REAL_ART` width and garment, `max_colors=6` (Studio default).
- **Pairs:** left was always shipped, right was always one flag ON, and the
  flag was named. Six flags were rendered. A pair was shown only where the
  flag changed the stitches, which gave 34 pairs; 20 flag × logo combinations
  were byte-identical and not shown.
- **Rendering:** `stitchviz.render_design` at 14 px/mm, lit-thread model, in a
  claude.ai artifact with synced zoom. The page had no pointer to where each
  pair changed.
- **Pace:** all 34 were judged between 17:44 and 17:50 UTC, about 10 s a pair.
  This was an at-a-glance read, not a close inspection.

## Verdicts

| flag | pairs shown | after better | before better | no difference | both bad | identical, not shown |
|---|---|---|---|---|---|---|
| `satin_polygon_axis="artwork"` | 9 | – | – | 8 | 1 (enthusiast) | 0 |
| `satin_rails_follow_edge` | 9 | 1 (tires) | – | 8 | – | 0 |
| `design_angle` | 9 | – | 1 (tires) | 8 | – | 0 |
| `satin_per_stroke` | 3 | – | – | 3 | – | 6 |
| `satin_patch_junctions="satin"` | 2 | – | – | 2 | – | 7 |
| `classify_area_weighted` | 2 | – | – | – | 2 (drone, screenshot) | 7 |

"Did the flag do what it claims?" was answered "yes" once (rails, tires) and
"can't tell" on the other 33. No note text was written, and no per-flag ruling
was set.

## What the pixels say

"No difference" does not mean the renders are identical. Measured after a
0.6 mm Gaussian blur (which removes the stitch-line texture and keeps shape,
coverage and shade), the share of the design that changed ranges from 0.05%
to 38%, with a median of 2.5%. Several "no difference" pairs changed a lot:
bridge `polygon_axis` 38%, gaulke 26%, golden_tee 20%. On bridge the change
is local stitch quality: zoomed in, the anchor's satin columns are cleaner and
more even with the flag ON. At full size it does not read.

So these flags do change stitch quality at close range, but not how a logo
reads. **That makes them the wrong lever for the "60% of Ember" gap** in
`.claude/memory/kent-eye-vs-instruments-2026-08-27.md`. Whatever holds that number down is visible at
arm's length, and these six flags are not.

## The three "both bad" pairs

enthusiast (`polygon_axis`), drone and screenshot (`area_weighted`) were
judged bad under both settings, with no note on what is wrong. These are the
lead to follow if quality work resumes from this review.

**Re-render them before chasing them.** These renders came from the renderer
as it stood before #513 ("draw jump runs — they sew, and skipping them faked
bare letters"). Both sides of every pair were drawn by the same renderer, so
the before/after comparisons stand. But a logo judged bad on both sides may
have been partly judged on bare-looking letters that actually sew.

## Side effects recorded elsewhere

- **Blinding:** this review showed five of PR #506's ten blind-sitting arms
  labelled. [A comment on #506](https://github.com/KS-Three/EMB-Bot/pull/506#issuecomment-5733890226)
  names them, so that sitting reads those five as seen-labelled.
- **An earlier `design_angle` note,** left on a throwaway preview artifact
  without a render in front of him, is still held; see the pointer in
  `docs/superpowers/plans/2026-09-17-eye-pairs-gallery.md`. Today's
  `design_angle` verdicts are on renders: 8 no difference, 1 before better.
