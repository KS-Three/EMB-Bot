---
name: underfill-ground-guard-2026-11-16
description: silhouette_underfill_ground_guard built OFF 11-16 — a ring whose host would jump ahead of the ground bordering its outer edge reads no ring; NASA insignia 80-150 mm white sewed under the blue ground (orbit buried, stars gone); 22 paired jobs unmoved; flip is Kent's
metadata:
  type: project
---

Autonomy trial, Kent 2026-11-16: "Choose a logo from the internet, have emb bot
digitize it, then YOU use your better judgement on what's needed to fix it."
Logo: the NASA insignia, 960 x 803 px PNG from Wikimedia Commons (public
domain, US government work). Kept out of the repo: neither the art nor its
renders are committed; the tests use synthetic shapes.

**Fault, by eye beside the art (100 mm, Studio request):** the white orbit
line sewn only along its right arc, the six sparkle stars missing, the letter
edges under blue. Stage 5's geometry was right; the sew order was white, blue,
red where the layer pass had left blue, red, white.

**Cause:** `silhouette_underfill.plan` read the white S + second A + orbit weld
(330 mm2, over the 200 mm2 ring floor only because the orbit joins the
letters) as a silhouette ring: its one hole is the A's 9 mm2 blue counter
(holes 0.03 of the outline; real silhouettes on the paired jobs 0.23-0.69).
The ring hosted itself and `apply` moved the WHOLE white layer ahead of the
blue layer, the ground the weld lies on. 4,246 mm2 of blue then sewed over
every white shape.

**Fix (`silhouette_underfill_ground_guard`, built OFF, PR on
`claude/underfill-ground-guard`):** a ring whose host would move ahead of
layers bordering `GROUND_EDGE_MIN` (0.5) of the ring's OUTER edge reads no
ring (`_on_jumped_ground`). A host that does not move is never asked.

**Measured:**

- NASA, guard OFF -> ON: 100 mm patch 24,543 -> 22,383 stitches, 38 -> 25
  trims, order white/blue/red -> blue/red/white/red; 120 mm left chest
  39,456 -> 35,099 stitches, 36 -> 42 trims (twelve stars now sew).
- The ring reads at 80, 90, 100, 120, 150 mm (outer-edge contact 0.86-1.00,
  two white rings from 120 mm); at 60-70 mm it is under the ring floor and
  both arms are the same stitches.
- 22 pro-paired jobs (`pro_baseline.JOBS`): 15 rings, 14 with a host that does
  not move, one that does (MFab LC's band, contact 0.00). MFab LC's design is
  md5-identical with the guard ON. No ring between 0.00 and 0.86.

**Why:** the under-fill's layer move is global and its evidence is local; a
counter is enough to reorder a whole thread.

**How to apply:** the flip is Kent's, from the art | before | after pictures.
Left open on the same logo, not built: the orbit sews at the satin floor
(about 1.5 mm for a 0.6 mm line); a 1.8 mm2 re-snapped red piece in the first
A's counter sews as its own fourth colour block; the round star dots under
1 mm are dropped by stage 3 (Kent 11-15: tiny marks not built, see
[[small-marks-2026-11-14]]). Related: [[launch-not-near-rulings-2026-11-12]],
[[eye-first-diagnosis-2026-11-13]].
