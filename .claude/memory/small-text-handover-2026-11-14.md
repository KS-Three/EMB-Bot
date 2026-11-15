---
name: small-text-handover-2026-11-14
description: ProSeal's tagline at 109.6 mm (4.01 mm cap) fell between the first restore (< 3.0) and the re-set (< 3.6) and sewed its raw trace; `small_text_handover` retraces 0.9-1.25 caps at true size (#1561); Kent 11-15 "Flip both ON", flip pending
metadata:
  type: project
---

Small-text hand-over, 2026-11-14 (#1561). ProSeal's tagline at 109.6 mm
(4.01 mm cap) fell between the first restore (< 3.0) and the re-set (< 3.6)
and sewed its raw trace: an A without its crossbar, a broken T, a teal
anti-aliased sliver.

`cfg.extra["small_text_handover"]` (built OFF) retraces lines from 0.9 to
1.25 caps at true size, after the re-set, and drops thin other-thread slivers
the retraced line covers. With it on, the line reads at 109.6 mm. A
growth-based near-cap re-set failed on room (bottom edge).

**Kent 2026-11-15:** "Flip both ON" (this flag and `fine_bar_survive`).
Ruled ON 11-15, flip pending. Related: [[proseal-size-2026-11-14]],
[[fine-bar-survive-2026-11-14]], [[reset-one-baseline-2026-11-13]].
