---
name: digitized-image-study-2026-11-13
description: Kent 11-13 "find 100 digitized images ... study and learn how the shapes were digitized and why": 108 distinct pictures of professional work read by eye (100 not AI mock-ups), 18 rules in docs/digitized-image-study-2026-11-13.md; rule 7 measured from DSTs: pro stacks under ~5.2 mm and knocks out above, we already stack on logo/flat art (silhouette_underfill), knock-out survives on photo classes; real gap is no contrast halo
metadata:
  type: project
---

**What ran (2026-11-13).** Seven Sonnet agents plus Kent's 10 seed pictures:
119 entries, 108 distinct designs, 8 flagged as probable AI mock-ups (three of
them Kent's own seeds: Somos, giraffe, AG Digitizing). 52 real sew-out
photographs, 33 software stitch renders, 15 art-beside-result pairs. Result:
`docs/digitized-image-study-2026-11-13.md` (18 rules, each with its reason, an
approximate count, and what EMB-Bot does today).

**Where the material is.** Pictures and per-picture notes are in the gitignored
`scratch_digitized_study/` in the main checkout (`images/`, `notes/*.json`,
`notes/rules_dump.txt`). Third-party art: never commit it, and it has no backup.

**What it found that changes what we do.**

- **Rule 7, MEASURED the same day, and the first version of this note was
  wrong.** Professionals sew small shapes on top of a solid ground, and so do
  we on logo and flat art: `silhouette_underfill` closes the ground's holes
  (`stage5_overlap.py:1009-1013`, `1102`), 120 of 126 narrow pieces on seven
  paired jobs sit fully on solid ground. Kent's pro stacks everything under
  about 5.2 mm (292 of 292 pieces) and knocks out 8 of 12 wider pieces with a
  1 to 2 mm underlap; we sew wide ones solid too. Our knock-out survives only
  where the under-fill is off: photo classes (the owl), grounds not read as a
  ring, MFab's panel. The wrong claim came from reading
  `stage5_overlap.py:1202-1231` alone; read a DST before describing what we sew.
- **Rule 12.** Professionals add a contrast outline to light-on-dark and
  dark-on-mid-tone shapes. EMB-Bot adds no outline the art lacks.
- **Fill angle is a genre habit, not one rule.** Cartoon digitizers turn the
  angle between touching fills of similar colour; logo digitizers (Kent's pro,
  DOCTRINE 2026-09-09) hold one angle per design. EMB-Bot does neither on
  purpose. Kent's 11-09 sitting kept the pro-direction slant OFF, see
  [[fill-slant-sitting-2026-11-09]].
- Already matched: satin on narrow shapes, satin border on fills, hairlines as
  run on top, cloth-coloured ground left unsewn, small text raised.

**Why:** everything copied from a professional before this came from one
digitizer's files ([[pro-rules-across-jobs-2026-10-21]]); this is the wide,
shallow counterpart.

**How to apply:** it is eyes-only evidence. No size, density, underlay or order
was measured, so no threshold from it may become a constant, and no quality
claim rests on it. Use it to pick what to measure next (the doc's last section),
not what to build. Traps for a repeat run: about a third of what agents found on
digitizing-service sites was AI-generated; category agents grabbed the same
portfolio pictures (9 duplicates), so give each agent its own source list; real
sew-out photographs came mostly from Wikimedia Commons and one design shop.
