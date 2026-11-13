---
name: digitized-image-study-2026-11-13
description: Kent 11-13 "find 100 digitized images ... study and learn how the shapes were digitized and why": 108 distinct pictures of professional work read by eye (100 not AI mock-ups), 18 rules in docs/digitized-image-study-2026-11-13.md; gaps vs EMB-Bot are knock-out where pros stack on solid ground, and no contrast halo
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

- **Rule 7, the clearest gap.** Professionals sew spots, eyes, stripes and panel
  text ON TOP of a solid ground. EMB-Bot knocks a hole under every later shape
  (shrunk by pull, 0.25 mm `overlap_mm` tongue; a hole that would close is held
  open, `held_hole_bare_only` off). Read at `stage5_overlap.py:1202-1231`.
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
