# The spine cure beside today's `main` (2026-10-11)

The sheets in [`../satin-spine-2026-10-04/`](../satin-spine-2026-10-04/README.md)
were drawn against `main` of 2026-10-04. By the time the cure was ported
(PR #817), `main` had taken the first part of it on its own (`7bb83e9b`,
2026-10-08), so their "before" no longer existed. These three are the same
tool on the same kinds of shape, with `main` at `af7dfaba` on the left and
the port on the right. Kent armed the PR on them.

Grey is the drawn shape, black is thread as the DST bytes say, red is a
needle-up move. Left chest, underlay on. Nothing here was sewn.

```
git archive af7dfaba src app/package.json app/src/lib | tar -x -C <dir>
node tools/satin-walk-census.mjs --against <dir> --sheet bars.png  --shape rect:3:0:30 --shape rect:3:1.5:30 --shape rect:1.9:0:38 --shape rect:5:2.5:20
node tools/satin-walk-census.mjs --against <dir> --sheet stars.png --shape star:12:0.15:20 --shape star:6:0.4:15 --shape star:8:0.15:20 --shape star:5:0.3:18
node tools/satin-walk-census.mjs --against <dir> --satin --sheet arcs.png --shape arc:12:3:330:270 --shape arc:12:2:180:0 --shape arc:8:3:90:45
```

| Shape | Stitches | Longest stitch | Sewn size or cover |
|---|---|---|---|
| C, 330 degrees, radius 12, 3 wide | 6,047 → 304 | 18.3 → 3.4 mm | 64% → 95% under thread |
| Half arc, 2 wide | 170 → 174 | 2.4 → 2.4 mm | 95% → 96% |
| Quarter arc, 3 wide | 86 → 59 | 3.4 → 3.4 mm | 90% → 91% |
| Bar 30 x 3, square | 159 → 165 | 3.4 → 3.4 mm | 28.9 → 30.0 mm long |
| Bar 30 x 3, round | 159 → 165 | 3.4 → 3.4 mm | 28.8 → 30.0 mm long |
| Bar 38 x 1.9 | 205 → 209 | 2.2 → 2.2 mm | 37.4 → 38.0 mm long |
| Bar 20 x 5, round | 265 → 265 | 4.0 → 4.0 mm | the same design |
| Star, 12 points, 20 mm | 769 → 530 | 10.8 → 9.3 mm | 98% → 98% |
| Star, 6 points, 15 mm | 472 → 255 | 14.9 → 14.2 mm | 99% → 99% |
| Star, 8 points, 20 mm | 594 → 390 | 12.0 → 12.0 mm | 99% → 97% |
| Star, 5 points, 18 mm | 444 → 444 | 4.0 → 4.0 mm | the same design (a fill) |

What they show:

- **The C is what the port is for.** On `main` a C drawn by hand and set to
  satin has its mouth sewn solid. On the port it is one column.
- **A bar gains about a millimetre.** `7bb83e9b` had already taken the long
  stitch out; the port carries the column to the bar's end.
- **The needle-up move between a bar's underlay and its column is on both
  sides** (27.8 mm and 28.5 mm on the 30 mm bar). The 10-04 README prices it
  as a cost of the cure; against today's `main` it is not one.
- **A star sews a third fewer stitches and keeps its long ones.** 9 to 14 mm
  either side. That is the star's tier, still open (MASTER_SCOPE "Waiting on
  Kent" 26), and the 8-point star loses two points of cover.
- **The last cross of an arc's end can stand outside it** (quarter arc,
  right-hand side).

Not drawn: the image lane's logos, strokes that meet (`--kind joint`), any
garment but left chest.
