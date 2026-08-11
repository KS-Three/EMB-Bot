# Photo palette floor-aware overflow — design

**Date:** 2026-08-11 · **Scope:** fix #6.1 from `docs/photo-quality-root-cause-
2026-08-11.md` — `drone_render.png` scoring F/0 on
`digitizer/tools/corpus_scorecard.py` because `select_palette`'s hard
`max_colors` cap binds before its own excess-ΔE target is satisfied.

## Problem

`select_palette` (`digitizer_core/palette.py:140-225`) runs a weighted
k-medoids BUILD loop that is supposed to keep adding chart threads until
every region is within `PALETTE_EXCESS_DELTAE` (4.5 ΔE00, `palette.py:93`)
of its own best possible match (`floor`). On `drone_render.png` the loop
instead hits `cap = min(max_k, len(chart))` — `max_k` is `cfg.max_colors`,
default 12 (`config.py:32`) — before that condition holds
(`max_excess_de00=7.599`). Two regions have excellent chart matches
available (`floor=1.98`/`1.51` ΔE00, e.g. Isacord "Silver") but the
area-weighted objective doesn't spend one of the 12 medoid slots on them,
so they force-merge onto "Armour" at ΔE 9.10-9.18.

`max_colors` is a single global `PipelineConfig` field consumed by every
digitized design, flat art included — raising it outright would change
thread-color-change count (real machine setup/trim cost) for every design,
not just the handful of gradient-heavy photo fixtures that hit this
pattern. That's the approach explicitly rejected here.

## Design

Let the BUILD loop overflow past `max_colors` — bounded — specifically when
a low-floor region is the reason it would otherwise stop short.

- New constant in `palette.py`, next to `PALETTE_EXCESS_DELTAE`:
  `PALETTE_OVERFLOW_K = 3`.
- `select_palette` computes two caps instead of one:
  - `soft_cap = max(1, min(int(max_k), len(chart)))` — today's `cap`.
  - `hard_cap = max(1, min(int(max_k) + PALETTE_OVERFLOW_K, len(chart)))`
    — the new absolute ceiling (15 for the default `max_colors=12`).
- BUILD loop condition changes from `while len(selected) < cap` to:
  ```python
  while len(selected) < hard_cap:
      if selected and ((res - floor) <= excess_deltae).all():
          break
      if len(selected) >= soft_cap:
          # Only keep growing past max_colors for a region whose own
          # floor is low enough that a genuinely good match exists —
          # never to pad the palette for a region that's just hard to
          # match (no thread is close, more medoids won't help it).
          worst = int(np.argmax(res - floor))
          if not (floor[worst] <= excess_deltae * 0.5):
              break
      ... # rest of the loop body (cost computation, candidate pick,
          # no-improvement break) unchanged
  ```
  `excess_deltae * 0.5` (≈2.25 ΔE00 at the default 4.5) ties the "low
  floor" threshold to the existing named constant instead of introducing an
  unexplained magic number — it comfortably covers the 1.98/1.51 floors
  actually measured on `drone_render`'s two bad regions.
- SWAP phase, `PaletteSelection`, `region_spools`, and every caller
  signature are unchanged — this only touches how many medoids BUILD
  settles on and why.

## Effect on other designs

Any design that already satisfies the excess bound within `max_colors`
never reaches the new `len(selected) >= soft_cap` branch — the loop breaks
on the existing `((res - floor) <= excess_deltae).all()` check first,
exactly as today. The overflow path is reachable only for designs where
the classical stop condition would otherwise force a low-floor region onto
a bad spool. Zero behavior change outside that pattern.

## Testing

- `drone_render.png` via `corpus_scorecard.py`: `max_excess_de00` should
  drop from 7.599 toward ≤4.5 (or as close as the chart allows), grade
  should move off F/0 at both configs.
- Existing photo-lane byte-identity goldens
  (`tests/test_photo_lane_byte_identical.py`) must stay green for every
  fixture that doesn't hit the overflow path — the fix is additive to the
  BUILD loop, not a change to `kept_masks_to_quant` or anything downstream.
- New unit test directly on `select_palette`: a synthetic region set sized
  to hit `max_colors` with every region already inside the excess bound —
  pins that `len(medoids) == max_colors` (soft cap respected, no
  unnecessary overflow).
- New unit test: a synthetic region set with one deliberately low-floor,
  high-excess region past the soft cap — pins that `select_palette`
  overflows to resolve it, and that `len(medoids) <= max_k +
  PALETTE_OVERFLOW_K` even when more than `PALETTE_OVERFLOW_K` regions
  would benefit (the hard cap actually caps).

## Non-goals

Does not touch `summit_badge.png` (fix #6.2 — segmentation-merge chaining,
a different mechanism in `stage2_photo_segment.py`) or
`repro_gradient_white_icon.png` (fix #6.3 — post-vectorization
color/geometry desync, a new mechanism not yet designed). Both are tracked
separately; see `docs/photo-quality-root-cause-2026-08-11.md`.
