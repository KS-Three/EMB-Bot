---
name: trim-economy-2026-10-21
description: Why we cut ~1.7x the pro's trims, read per trim from both DSTs (tools/trim_classes.py) — only the under-later class is a trim POLICY (pro 9, ours 43); most of the gap is white left as fabric (R11), fragmentation and the edge cap; `trim_bury_under_later` built OFF
metadata:
  type: project
---

Ten jobs that have both art and the pro's DST, each trim classified by what its
straight hop lies on (`digitizer/tools/trim_classes.py`, DST only — PES reports
a TRIM per jump). Full record: `docs/trim-economy-2026-10-21.md`.

- Pro 234, ours 449 (median ratio 1.73). Excess: bare +124, on_work +57,
  under_later +34.
- **The pro almost never cuts a hop that later thread covers (9 vs our 43)**:
  he travels under the work. That is the one class that is a trim POLICY, and
  `cfg.trim_bury_under_later` (built OFF) copies only it — real later stitches,
  whole thread width, never on top of finished thread (`chain_links`' other
  half, which the pro does not do: he cuts 141 on-work hops).
- **Bare excess is mostly design, not policy**: Machine / To a T / MFab have
  ZERO pro bare trims against our 91, because he sews the white (R11). No trim
  rule recovers that.
- The edge cap is cut stretch by stretch: 39 of our 478 plan trims — the next
  trim lever.

**Why:** a session handed "trims are 1.7x" would reach for a distance or
chaining knob; per-trim classes show only a quarter of the gap is a cut-vs-travel
choice. **How to apply:** classify before tuning; a flip of the new flag is gate
3 (chaining tier) and its show-through under light satin is a sew-out question.
Related: [[pro-trim-threshold]], [[real-artwork-trim-truth]],
[[exposed-travel-is-the-fill-tier-2026-09-19]].
