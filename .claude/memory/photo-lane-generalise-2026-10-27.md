---
name: photo-lane-generalise-2026-10-27
description: Kent 10-27 after the 18-genre photo census — the digitizer must improve ALL photos, not the few fixtures on hand; a photo build with no cross-genre corpus is the pattern he rejected
metadata:
  type: feedback
---

Kent, 2026-10-27, on seeing the photo-style census montage (18 untested
genres, `docs/photo-style-census-2026-10-27.md`): "it's as if this digitize
was only building tools to improve the photos we had on hand. This digitizer
needs to be building tools that help and improve ALL photos."

**Why:** the photo lane's rulings were measured on four acceptance portraits
and `owl_kent.jpg` (cutout-skip rule, width floor, faces-flat). All assume a
subject on a quiet ground. The census broke exactly outside that: scenes
(cutout hunts a subject, `GROUND_SEWN` blocks the picture), crowds/action
(faces drag the scene flat at 40-60k stitches), pale/line-art (cutout removes
100%, preflight grades the empty design A). Subject-on-ground rows passed.

**How to apply:** a photo-lane build needs a cross-genre reading before and
after, not one fixture. The census fetch script (Commons API, licence
filter) plus the logo census give 39 licence-clean inputs; use them as a
scorecard, never a golden. Prefer a content decision (subject / scene /
line-art / high-key) over another global rule. Check the phase-4 tonal
techniques (`scanline_tonal`, `sketch`, `detail_layer`) before writing new
fill code — the census ran the Studio's tatami request, not them. Related:
[[lane-census-2026-10-25]], [[build-what-was-priced]].
