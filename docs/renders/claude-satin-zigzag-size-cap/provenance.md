# Provenance: satin zigzag width cap renders (2026-10-14)

Every PNG here is a stitch-path render made by `tools/satin-zigzag-cap.mjs --render`.
No artwork, photo or client file is involved. The input is the shipped font
`src/fonts/bin/manga_impact.embf` setting the text "AB". That is PR #904's own
measurement call: full_back, pxPerMm 8, emMm 18, pullCompMm 0.2. Each sewn
segment is drawn as a 0.4 mm thread on cream.

- `before-*`: origin/main at 929bd126, where the zigzag sews every column.
- `after-*`: branch `claude/satin-zigzag-size-cap`, where the zigzag sews only
  columns under `SATIN_ZIGZAG_MAX_WIDTH_MM` (5.0 mm).

| file suffix | design width | px/mm | stitches before / after |
|---|---|---|---|
| `5mm` | 5 mm | 120 | 112 / 112 |
| `50mm`, `50mm-closeup` | 50 mm | 16 / 40 | 1,779 / 1,431 |
| `198mm`, `198mm-closeup` | 198 mm (auto-fit) | 4 / 16 | 21,070 / 12,492 |

Each close-up is a window cut from left of centre, through the "A". It is
12 mm square at 50 mm and 30 mm square at 198 mm.
