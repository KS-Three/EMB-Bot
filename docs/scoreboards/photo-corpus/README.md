# Photo corpus scoreboard

Kent's better / same / worse verdicts per photo PR, read off the side-by-side page `python -m tools.photo_corpus sxs` builds over the Commons corpus (`digitizer/testdata/photo/corpus/corpus.json`, 18 photo genres + 21 logo styles, 39 rows). Each json here is one exported verdict set; the table has one line per before/after pair. `baseline-<sha>.json` files are the instrument numbers of a `main` capture (no verdicts, no images).

All numbers are instrument readings, not quality claims (ROADMAP gate 4). The verdict column is Kent's.

| date | before | after | photo better / same / worse | logo better / same / worse | unjudged | worse slugs |
|---|---|---|---|---|---|---|
