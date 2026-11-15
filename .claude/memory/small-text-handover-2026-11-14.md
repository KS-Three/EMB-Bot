---
name: small-text-handover-2026-11-14
description: ProSeal's tagline at 109.6 mm (4.01 mm cap) fell between the first restore (< 3.0) and the re-set (< 3.6) and sewed its raw trace; `small_text_handover` retraces 0.9-1.15 caps at true size (#1561); Kent 11-15 "Flip both ON", flipped ON 11-15
metadata:
  type: project
---

Small-text hand-over, 2026-11-14 (#1561). ProSeal's tagline at 109.6 mm
(4.01 mm cap) fell between the first restore (< 3.0) and the re-set (< 3.6)
and sewed its raw trace: an A without its crossbar, a broken T, a teal
anti-aliased sliver.

`small_text_handover` (built OFF as `cfg.extra`) retraces lines from 0.9 to
1.15 caps at true size (`HANDOVER_RATIO`; a first 1.25 band broke ProSeal at
5.0 mm), after the re-set, and drops thin other-thread slivers (under 0.2 mm)
the retraced line covers. With it on, the line reads at 109.6 mm. A
growth-based near-cap re-set failed on room (bottom edge).

**Kent 2026-11-15:** "Flip both ON" (this flag and `fine_bar_survive`).
**Flipped ON 11-15** (flip PR 2): a `PipelineConfig` field, PRE_FLIP pins it OFF. Related: [[proseal-size-2026-11-14]],
[[fine-bar-survive-2026-11-14]], [[reset-one-baseline-2026-11-13]].
