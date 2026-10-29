---
name: dark-ink-bean-2026-10-28
description: "2026-10-28 — `dark_ink_bean` built OFF (Kent on the Pooh pot: \"No holes + bean (Recommended)\"): a dark read on a ground within 50 dE00 (thread to thread) sews as a bean along its skeleton and the ground sews through under it; the pot's starbursts were its satin edge round every letter hole"
metadata:
  type: project
---

# Dark-read strokes as a bean on their ground (`dark_ink_bean`) — 2026-10-28

Kent, after `keep_dark_thin_strokes` went ON: HUNNY "showed up but the quality
was not great" (thin/broken, blobby, strays). Rendered on main d8769ab6 at
80 mm: the pot (`S7de88924`, fill + border) cut a hole per letter and sewed its
satin edge round each one (the starbursts); the letters were 0.5-0.75 mm satin.
`dark_ink_refuse_strays` ON was byte-identical on the cartoon (not the cure).
Kent picked **"No holes + bean (Recommended)"**.

**Built OFF** (`thin_ink.bean_dark_ink` at the dark-ink tag in `run_stages`,
`thin_ink.ink_after_ground` after the under-fill in `_plan_stitches`): a
`dark_ink` region on "auto" whose ground (`_ground_of`: the shape whose OUTLINE
covers at least half of it) is within `BEAN_MAX_GROUND_DE00` 50.0 gets its
skeleton (`textcluster._skeleton_chains_mm`) as `bean_letter_spines`; stage 7
sews it as a bean letter and stage 5's `ground_under` sews the ground through.
The ground gets `lettering_group = False`. A stroke whose ground sews in the
same or a later layer moves to its own layer right after it.

**Three traps, one run each.**
1. `meta["tier"] = "run"` traces the polygon's OUTLINE (two lines round each
   stroke), not its centre. The bean-letter key is the centreline path, and
   only on `tier == "auto"`.
2. Closing the ground's holes at generation time: stage 5 "never grows back
   over a colour already down" (`earlier[L]`) and clipped every letter to
   nothing (`SHAPE_NOT_STITCHED`, 8 shapes). Leave the hole; `ground_under`
   already closes it under a bean letter.
3. The house-angle group tags the POT `lettering_group`; its letter holes
   only made the Column lane fail. Closed, it sewed one 37 mm satin.

**The gate.** Ungated, Fremont's wordmark (Black on White, 22 reads) sewed as
hairline skeletons. Width does not separate (wordmark 0.73-1.08 mm skeleton,
HUNNY 0.50-0.79); contrast does, but thread pairs are noisy: HUNNY reads 9.0
at the tag (0454 on 0763; the cap later moves it to 1233, 17.8), the synthetic
pen 27.7 though its pixels are 21.5 apart, so the merge's 26.0 was too tight.
50.0 is a CANDIDATE in the gap (pens <= 27.7, wordmark 100); owl 24.5-65.3 and
Bridge 43.9 sit inside it.

**Measured** (`tools.dark_ink_flip_sheet --flag dark_ink_bean`, 80 mm left
chest, 20 fixtures): 16 byte-identical; owl stitches 36,552 -> 34,574, trims
147 -> 113 (the white body's starbursts gone); Fremont 13,105 -> 12,894, trims
23 -> 25 (Wild Rice rope + tagline bean, wordmark satin as before); Fremont
patch 18,952 -> 19,014; Bridge 15,238 -> 15,222. Pooh (not committed, Disney)
23,912 -> 21,883 stitches, trims 47 -> 43. Sheet:
`docs/renders/dark-ink-bean-2026-10-28/`. Layout, judged in the preview; the
flip is Kent's.

Related: [[dark-thin-strokes-2026-10-27]], [[dark-read-refusal-2026-10-28]],
[[bean-census-2026-10-27]], [[layering-census-2026-10-26]].
