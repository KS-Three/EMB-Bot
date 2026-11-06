---
name: external-repo-sourcing-2026-11-06
description: Kent 11-06 "any repos that would benefit this project?" — tesserocr measured 45-50x per OCR read (ADOPT, catch: Tesseract 5.5.3 moves OCR goldens); clipper2-ts on trigger; five new GPL digitizers since 11-04, bench filum's DST only
metadata:
  type: project
---

**The ask (Kent, 2026-11-06):** after NVIDIA/auto-ontology (text-to-SQL over
warehouses, irrelevant) — "look on GitHub or other open source code sites to see
if there are any repos that would benefit this project." Full doc:
`docs/external-repo-sourcing-2026-11-06.md`. Scoped to what changed since the
09-12 sweep (86 candidates) and the 11-04 free-digitizer survey; neither repeated.

**The one adopt, measured:** `tesserocr` 2.12.0 (MIT, wheels bundle Tesseract
5.5.3 for cp39–cp315 incl. Windows cp314). Becker chest jpg, 48 tiles, same
tessdata: psm 10 **251 → 5 ms per read**, psm 7 185 → 4 ms. pytesseract spawns
`tesseract.exe` + a PNG per call at 8 sites (textcluster 5, legibility 2,
calibration/reader 1); the 10-26 "batch 4 at a time" was a workaround for that.
**Catch:** a THIRD engine version (box 5.4.0, CI apt 5.3.4) — every OCR-derived
number (lettering cc, legibility conf) moves once, box and CI together. Adopt =
one helper holding a per-thread `PyTessBaseAPI` (GIL released in Recognize, fits
`_one_tesseract_thread`), pytesseract fallback, lettering board before/after,
re-pin OCR goldens.

**On trigger, not now:** `clipper2-ts` 2.0.1-18 (BSL-1.0, 0 deps, 194/195 ref
tests) for the browser's home-rolled `offsetRing` (`src/digitize.js:581`,
defects 54/55 wedge class; 55's offset half still open). Costs a vendored bundle
in `ENGINE_FILES`; trigger = the next offsetRing artefact.

**Field since 11-04:** every 2026 entrant copies the same width table (run <1–1.5,
satin ≤7, fill above) and none compares to a pro. filum (GPL-3, Rust/WASM port of
Ink/Stitch's WHOLE engine incl. knockdown + order optimisation, created 11-04) is
the one DST worth a Tier-1 row when it ships a release — clean-room, never read.
Lilo (GPL-3, stalled after 2 days, straight-skeleton satin), Roidery (MIT/Apache —
the only permissive engine, 12 commits, nothing ahead of ours), tatami.ninja and
kaanyaren/Pantone thread charts (no licence) — skip.

**Watch:** skan (BSD-3; plumbing not discrimination), RapidOCR (Apache code,
Baidu-owned models; text LOCATION for the tagger's MFab misses), BiRefNet (MIT;
already a seam in `photo_prep_background_removal_model`, flip the knob).
**Empty:** PyPI Wu quantizers (patolette pre-release + patent note), permissive
straight-skeleton libs. Related: [[free-digitizer-survey-2026-11-04]],
[[digitize-speed-2026-10-26]], [[text-cluster-part-touching-2026-10-25]].
