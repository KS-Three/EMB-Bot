# Photo corpus scoreboard

Kent's better / same / worse verdicts per photo PR, read off the side-by-side page `python -m tools.photo_corpus sxs` builds over the Commons corpus (`digitizer/testdata/photo/corpus/corpus.json`, 18 photo genres + 21 logo styles, 39 rows). Each json here is one exported verdict set; the table has one line per before/after pair. `baseline-<sha>.json` files are the instrument numbers of a `main` capture (no verdicts, no images). `grades-<sha>-<date>.json` files are Kent's ABSOLUTE grades (Great / Good / Okay / Bad / Terrible) on one tree's renders, his words verbatim; the first, `grades-5ff48c5-2026-10-28.json`, grades the 21 logo rows at tree 5ff48c56 (Great 3 / Good 8 / Okay 2 / Bad 3 / Terrible 5) and is the ground truth a logo PR's better/worse verdicts move against.

All numbers are instrument readings, not quality claims (ROADMAP gate 4). The verdict column is Kent's.

| date | before | after | photo better / same / worse | logo better / same / worse | unjudged | worse slugs |
|---|---|---|---|---|---|---|
| 2026-10-28 | `a71fd5c` | `b6ec26a` | 4 / 6 / 8 | 1 / 15 / 5 | 0 | night_neon, architecture, landscape_lake, fireworks, flower_macro, underwater_reef, watercolor, night_skyline, duotone_poster, comic_halftone, outline_lineart_logo, kanji_brush, chalkboard_lettering |
| 2026-10-29 | `75efec5` | `be1c718` | 6 / 0 / 0 | 0 / 0 / 0 | 33 | – |
