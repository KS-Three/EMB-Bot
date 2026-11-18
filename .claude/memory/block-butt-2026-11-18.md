---
name: block-butt-2026-11-18
description: "Becker MARINE R/N/E fans are older than #1583; A counter NOT filled (5.93 vs art 5.61 mm2), R counter half closed; lettering_columns_block_butt (straight stem + butted bar/arms, heavy strokes >= 3.5 mm) built OFF #1683, ON 11-18 Kent: match the pros; hand-off in the doc"
metadata:
  type: project
---

Prime grader 11-18, `L_becker_hat_large`. Renders at a5a61d0b, 50713b25 (#1583) and main show the R/N/E fans in
all three: older than the apex family. The reader's "A counter filled" is wrong: thread-free hole area A 5.93 vs
art 5.61 vs pro 5.77 mm2; the R counter is real (3.18 vs art 6.63 vs pro 9.30).

`cfg.extra["lettering_columns_block_butt"]` (built OFF, heavy strokes >= 3.5 mm): pointed-slot tip stays cut (E
arms butt the stem), a stem-head `mitre` becomes a `butt` up the stem edge (R: stem + bowl, two straight
columns), a fan past 45 deg on a straight piece's slanted end sews square when it leaves <= 0.05 mm2 bare (N).
46 runs: only Becker moves (101.9, 80, 114), cover and bare unchanged, travel +8..19 mm. Docs
`docs/block-butt-2026-11-18.md`, pictures `docs/renders/block-butt-2026-11-18/`.

**Traps:** (1) first version applied the rescan and the fan skip to every letter: 22 of 46 moved and the A's
crossbar broke at 80 mm; gate on heavy strokes and on a block letter (butt cut or slot cuts). (2) `_MEMO.get() or {}`
is a throwaway when the memo is `{}` (falsy): test `is not None`. (3) A new `outline_cut` ContextVar must go in
`shape_memo._AMBIENT`. (4) R at 114 mm: butt built, then the fold look drops it; unchanged.
It undoes Kent's 11-14 corner_fold_apex_side E fold; flip is his, with the pictures.
Related: [[prime-grader-2026-11-17]], [[corner-turn-2026-11-14]].

**Kent 2026-11-18, shown the MARINE word at all five Becker placements and told it replaces his 11-14 E corner fold:
"Flip on, but make sure the MARINE strokes match the pros. These letters need to be perfect, release another agent
if needed."** Flipped ON as a typed field (`lettering_columns_block_butt`, PRE_FLIP arm `BLOCK_BUTT_2026_11_18_OFF`,
engine json false). Caveats: Becker is the only design with a >= 3.5 mm letter; the R keeps its fan at 76.5-79.8 and
114 mm; R counter 4.06 of 6.63 mm2; M's top-right changes; not sewn on cloth. The pro match is a second job:
`docs/block-butt-2026-11-18.md` section 7 (per-letter gaps, builder functions, what was dropped).
Tests that call `letter_columns` / `lettering_columns_shape` directly never see the config default (ContextVar False).
