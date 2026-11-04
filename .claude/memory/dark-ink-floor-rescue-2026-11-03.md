---
name: dark-ink-floor-rescue-2026-11-03
description: "2026-11-03 — `dark_ink_floor_rescue` built OFF: Pooh's fifth HUNNY letter at 54.6 mm was lost to the dark read's `min_detail_mm` KERNEL, not stage 3; second read at `dark_ink_read_floor_mm` 1.0 unioned on, plus protect + crumb drop; Kent flips"
metadata:
  type: project
---

# Dark-ink floor rescue (`dark_ink_floor_rescue`) — 2026-11-03

Kent, on his Pooh pot ("HUNNY" on a honey pot): at left-chest 54.6 mm a letter is
gone, at 45.6 mm only two survive. He picked "a lettering rescue from the floor"
over lowering `min_detail_mm` (gate 1) or nothing.

**The trap (the reason this note exists).** The brief blamed stage 3's absorb. It
is not: the missing letter never reaches `resolve_small_regions`.
`min_detail_mm` feeds `thin_ink.find_dark_thin_ink`'s black-hat KERNEL
(`2*round(min_detail_mm*ppm)+1`, 25 px at 54.6 mm / 1.5 mm), which closes the
fifth letter's three short strokes into the ground. So **lowering
`min_detail_mm` tests two mechanisms at once** (the kernel and every stitch
floor). Hold them apart: spy `resolve_small_regions` and the dark labels first.

**What was built (OFF; byte-identical OFF on every sheet fixture).**
`dark_ink_read_floor_mm` 1.0 beside the flag: a SECOND dark read at that floor
whose components are ADDED when they touch none of the first read's (a UNION, so
ON reads a superset). A replace-the-floor first design moved Fremont, drone and
Bridge because the width test lowered too. Plus a stage-3 `protect_layers` at the
absorb/drop point and a stage-4 crumb drop of an unclaimed rescue. The floor is a
RASTER READ THRESHOLD (which strokes count as pen ink), not a stitch value, so
gate 1 does not apply; `min_detail_mm` never moves.

**Pooh, OFF -> ON (fixed code):** 80 mm 21,419 st/40 trims -> 21,474/41 (md5
5b0d52d3 -> 67cac76b; the added 43.5 mm2 read is the cheek stroke, already a bean
OFF; it shifts its ink group's pooled colour and the spool re-snaps 131 -> 115, a
darker brown); 54.6 mm 12,009/37 -> 12,059/34 (letters clustered 4 -> 5, dark
regions 5 -> 6); 45.6 mm 7,697/15 -> 7,910/20 (clustered letters stay 3, dark
regions 5 -> 7). **At 45.6 mm half the word sews in the cluster and half as
unclaimed beans.** The 1.5 x 6.4 mm read is 0.61 of the cluster's ~3.9 mm
height, under `LETTER_HEIGHT_RATIO` 0.8; the other two (3.2 x 3.9, 2.0 x 3.4)
pass height and aspect, so spacing or stroke CV refuses them (not measured).

**Protect and crumb drop never fire on Pooh at any width** (nor on drone or
Fremont); they rest on `tests/test_dark_ink_floor_rescue.py`'s synthetic tests.

**Flip sheet (80 mm left_chest, `tools/dark_ink_flip_sheet.py`):** only Fremont
moves: patch 18,072 -> 17,908 st, 38 -> 35 trims; webp 12,894 -> 11,307, 25 -> 21.
The second read adds three rope-border marks (1.22, 1.25, 2.08 mm2; two at the
art's top edge) that join an existing ink group; two small thread-0873 shapes
(32 and 31 stitches) stop being sewn and many satin shapes re-tile by a few
stitches. Drone read 19,134 on one loaded sheet run and 19,133 (OFF's number) on
every rerun: load noise, not the flag (second read adds 0 components there).

**General rule:** ON reads EVERY dark thin stroke at 1.0 mm, not only letters, so
a row with no lettering can still move. Confining the second read to components
near a text cluster would have kept the Pooh cheek stroke out but also the
rescue of a letter whose neighbours are all lost; not built (Kent's call).

**Never again:** bare `python -` on this box (see
[[bash-heredoc-python-repl-trap-2026-11-02]]); Pooh art and renders stay in
gitignored `scratch_kent/` and are never committed.

Related: [[dark-ink-bean-2026-10-28]], [[dark-thin-strokes-flip-2026-10-28]].

Flipped ON 2026-11-04 (Kent), the PR that flipped it (#1232 built it). `PRE_FLIP` pins the OFF arm.

**Sheet gap (found on the flip, 2026-11-04).** `dark_ink_flip_sheet` runs only the shipped path (80 mm left_chest), where the texture gate and the glyph mask hide two movers: the owl forced onto the gradient plan (`stage0_texture_gate=False`) reads +2 feather streaks (6 -> 8), and the bare glyph-less reader on Summit reads 1 -> 5 (the dark notches in the Ms). Shipped outputs are identical on both. A test that forces a gate or calls a reader bare moves on a flip; the sheet never exercises it.
