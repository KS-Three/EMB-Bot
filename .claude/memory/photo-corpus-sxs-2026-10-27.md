---
name: photo-corpus-sxs-2026-10-27
description: The 39-row Commons corpus and the side-by-side verdict page (PR #1171) — how a photo PR is judged across every genre, and what the first main baseline read
metadata:
  type: project
---

# The photo corpus and its side-by-side page (2026-10-27, PR #1171)

**What exists.** `digitizer/tools/photo_corpus.py`: `fetch` (Commons by
title, LIVE licence re-checked, 503s retried, resumable), `capture --label L
--base origin/main` (every row in its own subprocess, cwd = the merge-base
tree, 1200 s timeout, faulthandler stack per row, resume; re-summarises from a
saved `<slug>.json` instead of re-running), `sxs --before --after` (one HTML:
source · before · after · numbers · better/same/worse + note, localStorage,
export), `tally` (files verdicts, one line per sha pair), `summary` (the
`baseline-<sha7>.json` record). 39 rows: 18 photo genres + 21 logo styles.
Images are gitignored; the repo is public. The Desktop browser pane refuses
`file://`: serve `digitizer/corpus_runs/` with the `corpus-sxs` launch.json entry.

**Why:** Kent 10-27 — the photo lane was tuned on the photos on hand; "this
digitizer needs to be building tools that help and improve ALL photos", and
he judges a photo PR by eye: "Sxs comparison w/ an Artifact that I can say
better or worse."

**What main (5ff48c56) read — instrument readings, gate 4:**
- 38 of 39 done; stained_glass timed out at 1200 s in `stage5_overlap.resolve_overlaps` (shapely difference).
- Stage 0 called only 3 of the 18 photo genres `photo_scene`; 11 went `gradient`, 3 `flat`. The photo lane fired on 3 photos.
- `max_colors` 6 kept on 32 of 38; flower_macro sewed 13 distinct threads, food_plate/night_skyline 8, watercolor/duotone_poster/isometric_icon 7.
- `fidelity_cc` above 0 on 8 of 38 — most renders agree with the photo less than blank fabric does. SSIM on a stitch render is a weak ruler; the page is the ruler.
- Two traps the capture itself taught: `design.colors` is the colour-BLOCK sequence (count distinct rgb for threads; architecture 14 blocks / 6 threads), and a tool that names a `.md` in code must be listed in `test_tools_console.py` or the full suite goes red.

**How to apply:** a photo-lane PR captures its tree (`capture --label mine`),
builds `sxs` against `corpus_runs/main-<sha7>`, and Kent's exported verdicts go
through `tally`. Quote the baseline json, never a number from a chat.
Open scope questions for Kent (PRODUCT.md silent): QR/barcodes; texture art
(halftone, engraving, grunge) — simplify or defect?
