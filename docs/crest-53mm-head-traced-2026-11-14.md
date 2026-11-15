# The crest's top eagle at 53 mm: head and neck traced (2026-11-14)

Fault 7 of the evening's eye sweep (`eye_pairs_out/eye-sweep-1114/REPORT.md`):
at the Studio's hat auto-fit, 53.3 mm, the heraldic crest's top eagle reads
with no head and no neck. It belongs to the shape-detail family
(`docs/shape-detail-traced-2026-11-14.md`). Fault 6 (Bridge's anchor at 48 mm)
was left alone: it is the anchor-and-waves weld Kent ruled a manual edit on
11-10, and the cause is the same.

Traced on main `d9699832` with the corpus request at 53.3 mm on `hat_front`
(hat pull 0.4 mm). The source is 585 px, the work grid 9.85 px/mm. Pictures
(gitignored, primary checkout):
- `eye_pairs_out/detail-1114/sheets/sweep7_crest53_head.png` (art | OFF | ON);
- `trace/C53_*`.

n = 1; counts, not a quality claim (gate 4).

## Where the head goes

| what the art draws | stage | number |
|---|---|---|
| black lines, about 1 px (0.1 mm), draw the head, the neck feathers and the eye's ring | 2: they snap into the blue (`stage2_snapped`) | sub-thread width; nothing sews them |
| the neck's feathered silhouette, with grey bays between it and the wings | 4 keeps it: one blue region, `Sbf854741`, 437.5 mm², 464 vertices | its bays near the neck are 0.48-0.59 mm across (inlets closed at 0.3 mm), up to 1.19 at 0.6 |
| the same bays in our needles | 5 closes them: a fill grown 0.4 mm from both walls shuts a bay under 0.8 mm | the bays are gone from the render |

So the neck dies at stage 5, the same cause as dot_music's notch. The flag
`cfg.extra["outline_inlets_kept"]` (#1528, OFF) already keeps a fill's growth
out of its own inlets. ON at 53.3 mm:
- the neck's feathered edge comes back, with the bays open on both sides;
- the beak sews open, with its tongue (the satin guard re-plans 7 shapes
  here, the beak among them);
- the head's top still runs into the crown above it, and the eye and the
  black feather lines are still gone.

**No new flag:** the cause that geometry settles here is one already built.

## What is left, and whose

- **The eye and the crown:** `missing-1114` traced the crest's eyes and crown
  (#1540).
- **The black feather and outline lines:** a 0.1 mm line is under any
  thread. A pro adds a dark run along such lines. `cfg.hairline` (OFF) sews
  lines it is given, but these never reach it: stage 2 has merged them into
  the blue first. Not built.
- **Speed, before any flip of `outline_inlets_kept`:** this run took 1,199 s
  ON against 169 s OFF on the shared laptop. The ON path re-plans stages
  5-7 when the satin guard fires and runs stage 5 a second time for the
  pinned fill angles. Contention on the laptop was not separated from the
  flag's own cost. Time one design on a quiet machine first.
