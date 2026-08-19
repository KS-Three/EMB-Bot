# Photo/Tonal v1 — Decision Record (Spec)

Decisions made by Kent 2026-08-18 under /grill-me, un-tabling ROADMAP phase 4
(tonal work) as a parallel track. Evidence base: the two-agent investigation of
2026-08-18 — docs map (photo plan rows 0–15 all built, dead on the automatic
path) and live probe (`digitizer/debug_out/probe_photo_20260818/`, stage-0
sweep in the session scratchpad).

## The problem, measured

A photo digitized with default config comes out as N flat posterized patches:

1. Real photos never reach the photo lanes — owl + both becker garment photos
   classify `gradient` at every resolution (ucm 0.088–0.123 vs the 0.28 gate);
   `photo_subject` is reachable by 2 of 30 corpus images; routing flips with
   export resolution on 13/30.
2. No lane renders tone. The blend tier decomposed 0/27 real regions (r² floor
   0.5; best real region 0.481). The photo_* lanes have no blend tier at all
   (grass macro: 713 superpixels → 2 flat fills).
3. Even decomposed shades sew one thread — stage 7 never reads
   `shade_thread_idx` (computed at `stage6_blend.py:586`, dropped); a block's
   thread is `group[0].region.thread_index` (`stage7_sequence.py:~1357`).
   Verified: 4-shade ramp at r²=1.0 sews 2 blocks / 1 color change.
4. SAM2: checkpoint cached (156 MB) but `sam2_isolated/venv` is a 1.2 MB husk;
   the availability check only tests `python.exe` existence, so jobs eat
   "SAM2 worker exited 106" at runtime and fall back. Off by default anyway,
   and its 90 s timeout sits under the measured 156 s cold start.

## Decisions

| # | Decision | Ruling |
|---|---|---|
| 1 | Acceptance target | Portrait/pet single subject, 5×7 in hoop or larger, judged by **Kent's eyes** on 3–5 real photos he supplies. The scorecard is explicitly non-authoritative for tonal work (it scored `split_tonal_regions` −2.7 while the change visibly did the right thing). |
| 2 | Tone mechanism | **Both.** Un-table `split_tonal_regions` for the photo lanes (immediate tone under the existing one-thread-per-region model), AND fix stage-7 to read the per-shade thread snap (unblocks multi-color tier emission — the portrait renderer needs it). |
| 3 | Automatic tier map | `photo_subject` → layered streamline thread-paint + detail layer when faces are detected; `photo_scene` → split + tatami; `gradient` → blend tier (unchanged). The existing per-element panel override survives. |
| 4 | Lane entry v1 | Studio gets a "This is a photo" toggle that sends `forced_class: "photo_subject"` (the service field the probe used). Stage-0 recalibration is phase 2 work and stays there. |
| 5 | SAM2 | Rebuild the isolated venv on Kent's machine; fix the lying availability check and the 90 s timeout; keep default OFF; A/B classical vs SAM2 on the acceptance photos — Kent's eyeball decides if it graduates. The opt-in-download ship ruling stands. |
| 6 | Acceptance fixtures | `digitizer/testdata/photo/acceptance/` — **gitignored, local-only, never published** (public repo; CLAUDE.md bars new personal artwork). |
| 7 | ROADMAP | Phase 4 marked active **in parallel** with phase 1, un-tabled by Kent 2026-08-18. Phases 2–3 stay honestly incomplete. |

## Standing constraints (unchanged by this spec)

- **No sew-out, no physical constants** (ROADMAP hard gate 1): nothing here may
  tune fill spacing, satin floors, or lock lengths, and no photo tier is
  marketed before thread meets cloth.
- **Flat-lane byte identity**: every change must leave the flat lane
  byte-for-byte identical (the repo's own `flat_lane_byte_identical` test).
- Real fixtures only for routing decisions (hard gate 2); synthetics barred.
- Engineering items inside the build, evidence-driven, not separately ruled:
  blend r² floor retune, palette-drift resnap, gating the `2·p90<1.0mm→run`
  satin rule to photo classes only (it is DISPROVED for flat art), sequencing
  trim thrash.

## Out of scope for v1

Stage-0 recalibration (phase 2). Scenery quality. SAM2 as a shipped default.
Any Studio review-screen UI beyond the one toggle. `MASTER_SCOPE.md`
line-budget refactors beyond the corrections named in the plan.
