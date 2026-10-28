# Photo corpus scoreboard

Kent's better / same / worse verdicts per photo PR, read off the side-by-side page `python -m tools.photo_corpus sxs` builds over the Commons corpus (`digitizer/testdata/photo/corpus/corpus.json`, 18 photo genres + 21 logo styles, 39 rows). Each json here is one exported verdict set; the table has one line per before/after pair. `baseline-<sha>.json` files are the instrument numbers of a `main` capture (no verdicts, no images). `grades-<sha>-<kind>-<date>.json` files are Kent's ABSOLUTE grades (Great / Good / Okay / Bad / Terrible) on one tree's renders, read off the `grades` page (`python -m tools.photo_corpus grades RUN_DIR --kind K`) or, for the first logo set, given by hand verbatim. At tree 5ff48c56 (2026-10-28): `grades-5ff48c5-logo-2026-10-28.json`, 21 logo rows, Great 3 / Good 8 / Okay 2 / Bad 3 / Terrible 5; `grades-5ff48c5-photo-2026-10-28.json`, 18 photo rows, Great 0 / Good 2 / Okay 4 / Bad 5 / Terrible 7. They are the ground truth a PR's better/worse verdicts move against.

All numbers are instrument readings, not quality claims (ROADMAP gate 4). The verdict column is Kent's.

| date | before | after | photo better / same / worse | logo better / same / worse | unjudged | worse slugs |
|---|---|---|---|---|---|---|
