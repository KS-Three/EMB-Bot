# Commons corpus for the photo side-by-side scorecard

Kent, 2026-10-27, after the 18-genre census (`docs/photo-style-census-2026-10-27.md`):
"This digitizer needs to be building tools that help and improve ALL photos."
This folder is the standing cross-genre input set that every photo PR is judged
on, side by side, before and after.

`corpus.json` is the only input that is committed: one row per image with its
Wikimedia Commons title, page URL, author and licence (CC0 / public domain /
CC BY / CC BY-SA only -- this repo is public). The images themselves are
fetched into this folder and stay local; the repo-root `.gitignore` keeps
everything here but this README and the list out of git.

From `digitizer/` (all numbers the tool prints are instrument readings, not
quality claims -- ROADMAP gate 4; the verdict column is Kent's):

```
python -m tools.photo_corpus fetch                               # images + manifest.json, live licence re-check
python -m tools.photo_corpus capture --label base --base origin/main
python -m tools.photo_corpus capture --label head
python -m tools.photo_corpus sxs --before corpus_runs/base --after corpus_runs/head
python -m tools.photo_corpus tally verdicts-<a>-<b>.json        # files Kent's clicks under docs/scoreboards/photo-corpus
```

Runs land in `digitizer/corpus_runs/` (gitignored). Capture takes hours (the
census had 7 of 18 rows over 600 s), so it is a by-hand step, never CI.
A label is one tree: each row records the `tree_sha` that made it, and a
folder holding another tree's rows is refused -- name labels after the sha
(`main-5ff48c5`) or delete the folder. To retry a timed-out row delete both its
`<slug>.json` and `<slug>.row.json`; a saved `<slug>.json` is re-summarised,
never re-run. Authors in `corpus.json` are the manifest's plain-text
`Artist` strings (no HTML; `test_corpus_authors_are_plain_text`).
