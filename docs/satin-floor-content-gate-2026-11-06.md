# Defect 2: the width floor by content, not by class (2026-11-06)

`cfg.satin_floor_content_gate` — **built OFF; flipping it is Kent's call.**

## What it does

Law 31's 1.0 mm satin floor (`stage6_satin.PHOTO_MIN_SATIN_WIDTH_MM`, never
tuned, ROADMAP gate 1) reroutes a satin the classifier *earned* but that sews
narrower than 1.0 mm to the outline run. It applied only when stage 0 classed
the design `photo_subject` / `photo_scene`. A photograph stage 0 sends
**gradient** (Kent's 2026-08-25 "a photo sews filled") never got it.

ON, `floor_applies` is also true when `config.is_photographic(cfg, class_)` is:
the Studio's "It's a photo" declaration, or a `detect_photographic` hit (folded
in by `apply_detection` before stages 5-7 read it). It is threaded to
`classify_ribbon` / `_floor_or`, the per-stroke branch (`_stroke_rows`), and the
four callers that must agree (stage 7 routing, stage 7's `_sews_satin`, stage 5's
`_comp_axis`, `_fill_inside_satin_border`). No new content signal, no stage-0
threshold (gate 2), the constant untouched. OFF is byte-identical.

## Measured (laptop, main 5777f91c + this change, 2026-11-06)

`python -m tools.floor_content_gate --photo --logos`. One `run_stages` per arm,
planned twice (flag OFF / ON) on that one result. *verdicts* = regions
`classify_ribbon` sends to `photo_width_floor`; *reroutes* = shapes that sewed
satin OFF and sew none ON.

| fixture | default route | `detect_photographic` fired | declared photo: verdicts OFF -> ON | declared: reroutes |
|---|---|---|---|---|
| drone_render | gradient | no | 0 -> 51 | 21 |
| logo_drone_thermal_badge | gradient | no | 0 -> 51 | 21 |
| summit_badge | gradient | no | 0 -> 26 | 0 (2 shapes' travel moved) |
| owl_kent | photo_scene | no | 14 -> 14 (class floor already applies) | 0 |

Reference, forced `photo_subject` (the Aug-22 route, class floor): drone 24,
summit 36, thermal 24, owl 14 verdicts. Aug-22 recorded 29 / 24 / – / 5 verdicts
and 18 / 9 / – / 2 reroutes. **These do not reproduce** — the engine moved in
2.5 months, and a declaration re-routes stages 1-4 (drone 127 regions declared vs
88 forced) — so the old reroute counts are not a baseline for the ON arm; compare
rows within this table only.

**What fired.** Only the declaration reaches drone and summit. Detection (EXIF
Make/Model + YuNet face) fired on **none** of the four photo fixtures — the two
renders (as expected) and the owl (the documented blind spot: re-saved, no face).
So the *automatic* drone/summit case stays blocked on a content signal that does
not exist; building one is stage-0 work (gate 2) and was not attempted.

## Guardrail: nothing floors on flat/gradient customer logos

Committed customer logos at default routing, flag ON, both `default` and
`detect_photographic=True` arms: bridge bar, golden tee, hotel fremont, gaulke
roofing (all gradient), enthusiast (flat). **0 detection hits, 0 floor verdicts,
plans byte-identical OFF vs ON in all 10 arms.** (Detection false positives: 0/5.)
The floor can only reach a logo someone declares a photo, or a future detector
mislabels. Not run: the gitignored pro-DST logos (the 61/64 population) — the
ON arm is inert there by the same mechanism (no declaration, no detection hit).

## Flip question (Kent)

ON changes nothing until a request carries `is_photographic: true` (the "It's a
photo" declaration) or `detect_photographic` fires. The flip is the engine
default; the Studio half (whether it sends the declaration for a gradient-routed
photo) was not checked here. Catch: the 1.0 mm constant is still an unsewn
physical constant (gate 1), and drone-type hairlines become bean runs, not satin.
