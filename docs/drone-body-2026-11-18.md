# Precision Drone: the drone body is not a fusing or area-floor fault (2026-11-18)

Scorecard faults: `L_precision_drone` "drone body, camera and arms are disconnected grey and black patches", "thermal lens lost", "long jumps across the whole design". Reproduced on main `ea4257d` with `tools.pro_pair.digitize` on the `precision_drone` job (hat_front, 62.6 mm, Studio request). Nothing in code was changed; no flag built. Pictures (our render and the original art only): `docs/renders/drone-body-2026-11-18/`.

## The count

- **112 stage-2 regions**, **9 threads** (black 0020, silvery grey 1972, black chrome 2776, silver 3971, fox fire 1305, flag blue 3335), 20 regions under 1 mm2. Sewn: **94 objects** in 9 colour blocks (grey 173, 119, 225 each come back twice), 14,211 stitches, 102 trims.
- **Drone zone** (plan x -22..22, y -26..3, everything not the black base): **50 regions, 10 under 1 mm2**, by thread 225:25, 308:10, 173:9, 119:4, 254:2. The black base (`S00c2fb94`, thread 4) is ONE 800 mm2 region: the navy sky, the drone's black body and the dark glass all went black at stage 2, so the drone is only what stands out of it as grey, and the dark lens is black on black.

## (a) Fusing touching fragments of one tone: nothing to fuse

`color_cap_fuse_split_tones` (ON) fuses cap-moved halves from two original threads. Among the 50 drone-zone regions only **3 same-thread pairs touch (gap <= 0.15 mm)**: 2 in thread 119, 1 in thread 225. The fragments are separate because black sits between them, not because one tone was cut in two. A looser fuse would join pieces the art keeps apart. Not built.

## (b) The thermal lens is not dropped by an area floor

The lens area holds **six sewn regions**: orange 2.36 mm2 (layer 8), three dark pieces 0.6-1.75 mm2 and a light 2.09 mm2 (all `rescued_small_shape`, so they already passed the small-shape rescue), and a 10 mm2 light piece. `light_thin_stroke_keep` acts on sub-floor strokes absorbed into a neighbour; nothing here is absorbed. What is lost is the lens's structure: a ~7 x 5 mm housing with an orange window, a dark glass ring and a highlight, which at 63 mm leaves 1-2 mm of thread per feature. `lens_closeup.png`: the orange is sewn, the round glass is not. That is a thread-width limit (0.4 mm stitches, 1.5-2 mm of art per feature), not a floor, and the black-on-black glass is the sky/black merge (`merge_chroma_guard`, OFF, not a flip candidate: `docs/renders/merge-chroma-guard-2026-11-17/README.md`).

## (c) Object order: a real but small saving, in lettering-ordered blocks

Needle-up travel: **134 jumps, 1,557 mm; 54 over 10 mm; 15 over 30 mm; longest 49 mm**. Inside the nine colour blocks the shape-to-shape travel is 1,095 mm. Reordering each block with nearest-neighbour plus or-opt, entries and exits held as planned, gives **841 mm (-23%)**, and 70% of that is two blocks: the dark-grey block 7 (232 -> 152 mm) and the final silver block 8, the PRECISION letters (162 -> 79 mm). The rest of the 1,557 mm is colour changes (the layering needs 9 blocks) and in-shape travel; neither moves. Caveats that keep it unbuilt: it is an estimate with fixed entries (the real planner re-picks entries), it reorders lettering, which the pro sews in reading order, and it lives in `stage7_sequence` chaining territory (ROADMAP gate 3: no chaining flag flips until its instrument is rebuilt). It does not touch either `ruins` fault.

## Verdict

The two `ruins` faults are the sky/black merge plus a 9-thread cap at 63 mm, which is what the OFF `merge_chroma_guard` already addresses and which fails three tests with it ON. Neither (a) nor (b) is a cheap gain; (c) is a modest saving worth building only if lettering order may change. Gate 1 constants (pull compensation, satin floors) untouched.
