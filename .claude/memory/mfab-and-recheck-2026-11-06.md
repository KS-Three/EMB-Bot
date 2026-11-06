---
name: mfab-and-recheck-2026-11-06
description: A 10-25-dated brief asked to fix MFab LC's hollow bean A under a new OFF flag; on main 7ee2d98a the fault is gone (0 bean tags, A/N/D satin 126/110/120 points) because bean_ink_outlined_letters and bean_only_lines both went ON 10-27. No flag built. Outlined lettering among the pairs = MFab (keyline) and Becker (too tall to matter)
metadata:
  type: project
---

# MFab AND re-check: the brief was stale (2026-11-06)

Full record: `docs/mfab-and-recheck-2026-11-06.md`.

**The ask.** Fix, under a new OFF flag, the AND of "AND WELDING LLC" on MFab
left chest (96.7 mm, pair `mfab_lc`), whose A sewed as a hollow bean outline
on 2026-10-25 (`docs/text-cluster-part-touching-2026-10-25.md`).

**Why nothing was built.** Two flips on 2026-10-27 each close it alone:

- `bean_ink_outlined_letters` ON ([[outlined-bean-ink-2026-10-27]]): the
  reader grounds on the black body, reads the WHITE keyline as ink; a read
  under half inside its letter is no read.
- `bean_only_lines` ON ([[bean-census-2026-10-27]]): `tag_bean_letters`
  returns before any read. No letter is a bean on main.
- `text_cluster_part_touching` ON too (the flag the brief said must wait).

**Measured on main 7ee2d98a.** `tools.pro_pair.digitize`, LC at 96.7,
`CLASSIFIED_GRADIENT`, 8.0 px/mm: 0 bean-tagged regions in the design; A
`Sbd0d3e9f` satin 126 points, N `S81d1d4a6` 110, D `S6815bbe5-2` 120, all
thread 0020 in one text cluster; plan md5 `7e924603`, 18,145 stitches, 21
trims. Art/ours crop committed; the sheet with the pro's tile is local in
`pro_renders/mfab-and-recheck-2026-11-06/`.

**Outlined lettering census (18 pairs, 42 board lines, read by eye).** MFab
hat and LC: every line is black on a black body with a white keyline. Becker
x5: white faces in a black outline, 12.8-28.5 mm tall, never near the bean
line. Drone's PRECISION is bevelled (the `INK_SHAPE_MAX_RATIO` case), not
keylined. Fremont, ProSeal, Gaulke, Tires: solid letters, not outlined.

**How to apply.** Before building a fix from a dated brief, digitize the job
on today's main first: three flips landed in the two days after this one was
measured. A crop-rim ground is NOT the reader's ground (it grounds 0.8 mm off
the traced members), so a census of "what the reader sees" needs the traced
regions, not the art alone. See also [[next-work-from-main-not-handoffs]].
