---
name: hotel-fremont-pro-parity-findings
description: logo_hotel_fremont.webp at 92.5mm/patch — tiny-lettering and satin-border-fragmentation are real and already instrumented by LETTERING_TOO_SMALL/STITCHES_TOO_SHORT/TRIM_HEAVY; forced_class=flat makes it worse, not better; "missing backfill" was a render-fidelity misread, underlay is really there
metadata:
  type: reference
---

Kent flagged five things off a rendered EMB-Bot-vs-Wilcom comparison chart
for `logo_hotel_fremont.webp` (92.5mm, patch garment): "THE" incomplete,
fine details lacking, satin border not clean, EAT|STAY|PLAY missing,
missing backfill stitching. Investigated each against `digitize()` +
`plan.iter_runs()` directly (not the render) — full detail and numbers in
`docs/scope/1-auto-digitizing-quality.md`'s 2026-08-20 Hotel Fremont entry.

**Two real, two refuted, none of them [[satin-extremity-drop-and-coverage-check]]'s
mechanism** — `ARTWORK_UNCOVERED` correctly stayed silent here (`worst_mm2:
0.2`), first real-world confirmation it doesn't false-positive on a design
with five other genuine problems.

- **Tiny lettering** ("THE", EAT|STAY|PLAY, fine details): shapes exist and
  `stitched: true`, just 0.53-0.98mm column width. Already caught by
  `LETTERING_TOO_SMALL` + `STITCHES_TOO_SHORT` — no new instrumentation
  needed, the existing preflight checks are doing their job. Not dropped,
  illegible — a physical-scale ceiling, not a bug.
- **Satin border fragmentation** — NEW finding, not previously known. A
  continuous rope-twist stroke sews as ~21 disconnected satin islands
  instead of one, driving `TRIM_HEAVY` (13.0/1000 here vs. the pro file's
  ~1.3/1000 by direct pystitch count). Root cause (why the segmenter
  fragments a thin continuous motif) not found — filed with reproduction
  only, same standard as the enthusiast_logo bracket entry.
- **`CLASSIFIED_GRADIENT` misclassification confirmed, but `forced_class=
  "flat"` is WORSE, not the fix** — 2 colors instead of 5, no letter
  counters, solid crushed mass. Tested directly so nobody re-tries this as
  a quick fix. The rope's diagonal banding is the likely classifier trigger
  on artwork that's genuinely flat vector art by the chart's own caption.
- **"Missing backfill stitching" refuted** — underlay is present, 78 runs
  across the plan, confirmed under 5 of 6 sampled small letter shapes via
  `kind == "underlay"` on the StitchPlan runs (not visible in the exported
  design JSON — had to go through `digitizer_core` directly for run kind).
  Same render-fidelity class as the `render-dst.mjs` white-gaps misread in
  [[satin-extremity-drop-and-coverage-check]] — thin zigzag underlay doesn't
  read as "backing" in a stitch-path line render even when it's really
  there.

Professional reference: `HOTEL_FREMONT_.DST` (Wilcom), decoded with pystitch
— 15,589 stitches, matches the chart's 15,569 closely. Uploaded alongside
`.PES`/`.EMB`/`.pdf` versions; not committed to the repo (customer file,
per CLAUDE.md's no-new-client-artwork-without-asking rule) — this was a
one-session comparison, source stays in the upload, not `testdata/`.

**UPDATE 2026-08-22 — this fixture is UNREPRESENTATIVE of client work.** Its
46-hole perforated white field drove a session of fill-side trim work that
turned out to be **byte-identical on all six real client logos**. Real logos
carry 1–3 fill shapes that essentially never cut; this one is the exception, not
the type. Use it to reproduce a defect, never to size how much a fix is worth.
Detail: [[real-artwork-trim-truth]].

See also [[satin-extremity-drop-and-coverage-check]] and
[[real-artwork-parity]].
