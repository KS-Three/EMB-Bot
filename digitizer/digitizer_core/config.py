"""Pipeline configuration. One dataclass, everything explicit, everything
serializable — this is the parameter set the stateless service round-trips,
so no hidden module-level tunables anywhere else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    # Physical target: the artwork's finished embroidered width. The px->mm
    # factor derives from this against the non-background artwork bbox.
    target_width_mm: float = 80.0

    # Stage 0
    # Skip signal computation, force this classification instead — the UI
    # override the plan calls for, and the escape hatch every test that
    # needs a specific class without depending on threshold tuning uses.
    # One of "flat" | "gradient" | "photo_subject" | "photo_scene", or None
    # to classify normally.
    forced_class: str | None = None

    # Stage 2
    # Which manufacturer's chart the design is snapped to. Ids match the
    # browser's (app/src/lib/threadBrandsIndex.js) because Studio sends its
    # stored preference straight through; None = Isacord, the shop default and
    # what every golden here is pinned to. The operator buys the cone this
    # names, so an unknown id raises rather than silently substituting.
    thread_brand: str | None = None
    max_colors: int = 12
    seed: int = 0                      # k-means RNG seed — fixed for determinism
    # Cluster centers within this CIE76 distance are the SAME flat color that
    # k-means split; merged before spool snapping. Also the perpendicular
    # tolerance for the phantom-blend collinearity test.
    merge_delta_e: float = 6.0
    aa_iterations: int = 2             # AA-halo majority-filter passes
    aa_phantom_edge_frac: float = 0.9  # cluster >90% edge pixels = phantom blend color

    # Stage 1
    bg_tolerance_lab: float = 6.0      # Delta-E-ish flood tolerance
    # Fraction of the border ring the modal border color must actually
    # describe before stage 1 believes a background exists at all. Measured
    # over every committed fixture (re-measured 2026-08-11 under the
    # enclosed-regions semantics): real backgrounds score 92.5-100%,
    # full-bleed art 35.5% and below. Below this, nothing floods and
    # BACKGROUND_ABSENT says so. Originally derived on the pre-c1b9e35
    # branch fix/bg-existence-guard (73e0665); the numbers reproduce.
    bg_border_agreement_min: float = 0.75
    # The subject-dominated-border guard (the snowy-owl failure): a pale
    # subject filling a tight portrait crop dominates the border ring, so the
    # ring's modal color IS the subject and the flood deletes the subject's
    # body while the real wall survives as "foreground". The tell is a second
    # COHERENT border color — the wall showing through at the crop's margins.
    # This is the largest coarse color bin among ring pixels the modal-color
    # mask does NOT claim, as a fraction of the whole ring. Measured
    # 2026-08-11: every real-background fixture scores 0.000-0.021 (the
    # remainder is anti-alias scatter), the owl-repro fixture 0.173. When the
    # rival is at or above this AND the modal color fails to hold the frame's
    # corners (a real background owns its corners; a tight crop's wall peeks
    # through them), stage 1 refuses to flood and reports BACKGROUND_UNCERTAIN
    # (reason "subject_dominated_border") instead of silently deleting the
    # subject. Zero or negative disables the guard.
    bg_border_rival_min: float = 0.10
    bg_margin_mm: float = 3.0          # intrusion past this inside a shape's hull = uncertain
    bg_intrusion_min_mm: float = 2.0   # intrusion below (this mm)^2 is boundary noise, not art loss
    min_px_per_mm: float = 4.0         # resolution floor at target size
    upscale_cap: float = 4.0           # max Lanczos upscale factor
    denoise: bool = True

    # Stage 1.5 — photo prep (photo plan §2 rows 3-4; build step 3, first
    # slice — stage1_photo_prep.py). CLAHE tone rescue + texture kill on the
    # prepped raster BEFORE the photo region former sees it. DOUBLE-gated:
    # this flag must be True AND stage 0 must classify the design
    # photo_subject/photo_scene (forced_class counts). Default False, and
    # with it off — or on for any non-photo class — the pipeline is
    # byte-identical to before this module existed (pinned in
    # tests/test_photo_prep.py; the flat lane additionally by the
    # byte-identical suites). The YuNet face priors (plan §2 row 2, wired
    # 2026-08-04 — detection, face-local merge threshold, eyes/skin palette
    # weights, the preflight face-size guard) ride this SAME double gate:
    # no separate flag, no face machinery on any lane this flag doesn't
    # open. See stage1_photo_prep.detect_faces_seam.
    photo_prep: bool = False
    # Texture-kill technique: "bilateral" (default, zero-dep) | "meanshift"
    # (zero-dep) | "rolling_guidance" (real path since the 2026-08-04
    # opencv-contrib-headless swap in requirements.txt; falls back to
    # bilateral with a warning when cv2.ximgproc is absent, e.g. a pre-swap
    # env — see stage1_photo_prep's module docstring) | "none" (tone prep
    # only).
    photo_prep_texture_kill: str = "bilateral"
    # CLAHE knobs — plan row 3's own numbers ("clip 2-3, tiles 8x8").
    photo_prep_clahe_clip: float = 2.5
    photo_prep_clahe_tiles: int = 8

    # rembg subject cutout (photo plan §2 row 1 — build step 3's second
    # slice, stage1_photo_prep.remove_background_seam). A SEPARATE opt-in
    # flag ON TOP of the photo_prep double gate above (this flag AND
    # photo_prep AND a photo classification must all hold) — the isolated
    # venv subprocess this shells out to (digitizer/rembg_isolated/, see its
    # README.md) is heavier than the zero-dep tone/texture/face-priors work
    # above it, so turning photo_prep on does not, by itself, spend a
    # subprocess and a neural net on every photo job. Default False; with it
    # off the pipeline is exactly what it was before this slice existed,
    # including for every design that has photo_prep=True. When on and the
    # isolated venv is missing/broken/times out, the documented no-op
    # fallback applies (PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE): stage 1's
    # border-flood bg_mask is kept unchanged and the job still completes.
    photo_prep_background_removal: bool = False
    # Which rembg model the worker loads. "isnet-general-use" is the plan's
    # default tier (§2 row 1); "birefnet-general-lite" (quality) and
    # "u2net_human_seg" (portrait fast tier) are documented seams — the
    # worker script accepts any rembg model name, but only the default has
    # been measured end-to-end (docs/photo-prep-deps-probe-2026-08-04.md).
    photo_prep_background_removal_model: str = "isnet-general-use"
    # Subprocess timeout, seconds. Generous because the FIRST call in a
    # fresh isolated venv also downloads the model (~178 MB; measured ~10s
    # through this sandbox's proxy) — every call after that is cached and
    # takes ~1-2s. A slow/blocked download degrades to the no-op fallback
    # exactly like any other subprocess failure, never hangs the job.
    photo_prep_background_removal_timeout_s: float = 60.0
    # Stage 2 (photo path) — SAM2 region former (digitizer/sam2_isolated/,
    # see its README.md). A SEPARATE opt-in flag, gated on the PHOTO classes
    # only: this flag must be True AND stage 0 must classify the design
    # photo_subject/photo_scene (forced_class counts). "gradient" designs
    # route through stage2_photo_segment for an unrelated reason (avoiding
    # k-means dithering on a smooth ramp) and deliberately do NOT get SAM2 —
    # a gradient has no "distinct objects" for an instance segmenter to find,
    # and SLIC+RAG is already tuned against two real gradient fixtures. "flat"
    # never reaches this code path at all. Default False; with it off the
    # pipeline is exactly what it was before this lane existed. When on and
    # the isolated venv is missing/broken/times out, the documented fallback
    # applies (PHOTO_SAM2_SEGMENTATION_UNAVAILABLE): the classical SLIC+RAG
    # region former runs instead and the job still completes.
    photo_segment_sam2: bool = False
    # Which SAM 2.1 checkpoint tier the worker loads — a key of
    # sam2_worker.CHECKPOINTS ("tiny" | "small" | "base_plus" | "large").
    # "tiny" is the default and the only tier this lane was built around:
    # inference here is CPU-only, so the larger tiers get slow enough to be
    # self-defeating against the timeout below, and embroidery-scale regions
    # (floored at min_detail_mm) do not need fine-grained natural-scene
    # accuracy. An unknown name is rejected by the worker (exit 2) and
    # degrades to the classical fallback like any other worker failure.
    photo_segment_sam2_checkpoint: str = "tiny"
    # SAM2's own automatic-mask-generator prompt-grid density. SAM2's library
    # default is 32 (1024 prompts); 16 (256 prompts) quarters the mask-decoder
    # work, which is the dominant CPU cost here. MEASURED AND CONFIRMED,
    # Task 6, 2026-08-10 (this machine: Windows, CPU-only, no GPU, tiny
    # checkpoint, torch 2.13.0+cpu). Swept 16/32/48 against
    # testdata/photo/photo_scene_stub.png (target_width_mm=80,
    # garment_id=left_chest) — the corpus fixture that came back sparse
    # (1 raw mask) at 16: 32 barely moved it (2 raw masks, 125s vs 40s —
    # ~3x the wall-clock for +1 mask), and 48 (2304 prompts) blew past the
    # THEN-180s subprocess timeout entirely (190s wall before the timeout
    # fired) and fell back to the classical segmenter, exactly as designed.
    # Conclusion: this fixture's low mask count is a CONTENT property (a
    # smooth, nearly textureless "scene" raster with no salient objects for
    # an instance segmenter to find — SAM2 is behaving correctly, not
    # grid-starved), not a grid-density problem, so raising this constant
    # buys a worse cost/mask ratio here and real timeout risk against the
    # new (also Task-6-measured) 90s timeout below, with no corresponding
    # region-count benefit. See docs/sam2-segmentation-live-
    # acceptance-2026-08-10.md for the full sweep and the other two corpus
    # fixtures' raw mask counts at 16 (1 and 14).
    #
    # LOWERED 16 -> 12, 2026-08-11, measured on the same machine (see
    # docs/sam-alternatives-research-2026-08-11.md). That research set out to
    # find a smaller/faster SAM and found instead that the model is the wrong
    # thing to change: in automatic-mask-generation mode SAM2's image ENCODER
    # is only ~8% of per-image cost, and the other ~92% is this constant's own
    # points_per_side**2 prompt-decode loop (~148 ms per prompt, 256 prompts
    # at 16). Every lightweight SAM variant on the market optimizes the
    # encoder — they target interactive click-to-segment — so none of them can
    # touch the 92%. This knob can. Measured, same image, all else equal:
    # 16 -> 53.96s / 16 masks; 12 -> 32.10s / 16 masks (IDENTICAL output for
    # 41% less time); 8 -> 16.91s / 11 masks (loses 5 — too far). 12 is the
    # last step down that costs nothing in output.
    photo_segment_sam2_points_per_side: int = 12
    # Longest side, in px, of the raster handed to the worker. SAM2's image
    # encoder resizes its input to 1024x1024 internally, so sending more than
    # this costs I/O and post-processing without giving the encoder more to
    # work with; the returned label map is nearest-neighbour upsampled back
    # to full resolution, which preserves region identity exactly and costs
    # at most a pixel of boundary precision — well inside the tolerance
    # stage 4 already applies via simplify_tol_mm. 0 or negative disables the
    # downscale entirely.
    #
    # STAYS 1024 — a 512 default was tried and REJECTED on measurement,
    # 2026-08-11. `docs/sam-alternatives-research-2026-08-11.md` proposed
    # 1024 -> 512 as "~-21% wall-clock, same masks"; measured end-to-end
    # through the real service on photo_scene_stub.png it is NOT the same
    # masks — region count drops 25 -> 20 (a fifth of the segmentation),
    # reproducibly, at BOTH points_per_side 16 and 12. Time saved was ~11%,
    # and this box's run-to-run timing noise is wider than that (the SAME
    # config measured 51.3s and 59.7s in two runs), so the trade is a real,
    # deterministic quality loss bought with a saving smaller than the
    # noise. Region counts are the trustworthy signal here, not seconds.
    #
    # That research DID correct the mechanism this comment asserts above, and
    # the correction stands even though its recommendation didn't: the claim
    # that sending more than the encoder's own 1024 costs "I/O and
    # post-processing" has the encoder half backwards. `SAM2Transforms`
    # hard-resizes every input to 1024x1024 regardless, so this knob never
    # feeds the encoder more OR less work; what it really changes is the
    # per-prompt mask upscale and how much real detail survives to be
    # segmented at all — which is why lowering it loses regions. The
    # boundary-precision half of the original claim remains reasoned, not
    # measured — and would matter more below 1024, so it is the thing to
    # revisit first if this is ever lowered again and thin features start
    # coming back soft on real photos.
    photo_segment_sam2_max_side_px: int = 1024
    # Subprocess timeout, seconds. This is the ONLY bound this architecture
    # has on a hung SAM2 call: digitizer_service/jobs.py's JobRegistry is a
    # single-worker ThreadPoolExecutor with no per-job timeout and no
    # cancellation of a running job, so a call that never returns starves
    # every queued job behind it. Read this number as a starvation bound, not
    # a performance target.
    #
    # MEASURED, Task 6, 2026-08-10 (this machine: Windows, CPU-only, no GPU,
    # Python 3.14.6, torch 2.13.0+cpu, sam2_isolated venv built fresh —
    # this measurement's own venv had no 3.12 interpreter installed, so it
    # used Python 3.14, which has a real cp314 CPU wheel on PyTorch's own
    # index as of this date; digitizer/sam2_isolated/README.md's build
    # command already documents `python3.14` for this reason, see the
    # measurement note for the detail). `sam2_worker.py
    # testdata/photo/drone_render.png ... tiny 16
    # 36`, run twice: COLD (pays the one-time ~150 MB checkpoint download
    # from dl.fbaipublicfiles.com plus torch's own cold import) = 155.98s;
    # WARM (cache hit, the number that matters) = 39.96s. A second warm
    # sample through the full seam (photo_scene_stub.png, target_width_mm=80,
    # garment_id=left_chest) landed within a second of that (40.8s),
    # so treated as a stable p50, not a fluke.
    #
    # Originally set to roughly 2x the observed warm run (2 * 39.96 = 79.9s,
    # rounded up to 90s), on the theory that `sam2_isolated/README.md`'s
    # required pre-warm step (populate the checkpoint cache by hand before
    # this lane is ever used for a real job) keeps every real job off the
    # 155.98s cold path entirely, so sizing the timeout off the cold number
    # instead would only be buying safety a mandatory setup step already
    # provides — see this field's git history for that reasoning in full,
    # including why the alternative was rejected at the time.
    #
    # Task 5 (2026-08-18/19, this worktree's own isolated-venv rebuild) found
    # that trade-off did not hold up: 90s did not reliably cover a real job
    # even with the checkpoint cache warm. Re-sized off the measured COLD
    # path instead — 240s is ~1.54x the 155.98s cold-start baseline (Task 6,
    # 2026-08-10, see the MEASURED paragraph above), not a multiple of the
    # warm one — so this bound now holds regardless of which path a given
    # job actually takes. Still short enough that one hung call cannot
    # starve the single-worker job queue (see this field's own opening
    # paragraph) for more than a few minutes.
    #
    # measured 156 s cold start 2026-08-11; 90 s guaranteed a first-job timeout
    photo_segment_sam2_timeout_s: float = 240.0

    # Stage 3
    min_detail_mm: float = 1.5         # blueprint hard constraint
    # Absorbed regions below this fraction of the min-detail area are
    # anti-alias cleanup, not lost artwork — absorbed silently so the review
    # screen's warning stays meaningful ("30 details merged" from AA slivers
    # is noise that trains the user to ignore warnings).
    report_absorb_frac: float = 0.25
    # The run-tier rescue (stages 3, 4 and 7 together). A shape below the
    # sewable floor that would otherwise be dropped is kept and sewn as a
    # light bean run on its outline: on the benchmark logo at 90 mm the whole
    # "ENTERPRISES INC." subline sits under the floor, and dropping it means
    # a line of the customer's text silently vanishing. Shapes below the
    # thread's own visual weight (machine.RUN_MIN_LOOP_MM / RUN_MIN_AREA_MM2)
    # still drop. False restores the old drop-everything behaviour.
    small_shape_rescue: bool = True

    # Stage 4
    # Polygon simplification tolerance. Both call sites (`stage4_vectorize.
    # vectorize`'s `eps_px = simplify_tol_mm * px_per_mm`, then divided back
    # by `px_per_mm` on the way to mm-space output; `pipeline.py`'s
    # background-outline simplify, which runs on already-mm coordinates
    # directly) apply it so the REALIZED deviation is a genuine, constant
    # `simplify_tol_mm` millimetres regardless of `target_width_mm` — by
    # construction, not by accident, because `px_per_mm` is exactly what
    # converts one to the other and cancels out of the round trip.
    #
    # Ember Design's competitor tool scales an equivalent tolerance linearly
    # with design size, clamped [0.32, 2.5] (`docs/emberdesign-competitive-
    # research-2026-08-07.md`), which reads at first glance like something
    # EMB-Bot should copy. Checked directly, not assumed, 2026-08-07: their
    # `/api/vectorize` traces a raw uploaded image with NO physical-size
    # input at that layer at all (sizing happens later, in their editor) —
    # their "size" is the traced raster SHAPE's pixel dimensions, a proxy
    # for "how much raw contour noise is probably in this image," not a
    # physical output measurement. EMB-Bot already has an explicit mm scale
    # at this point (`px_per_mm`, derived from `target_width_mm` in stage 1)
    # and applies this tolerance AFTER that conversion specifically so it
    # measures real millimetres independent of source resolution — a more
    # direct solve to the problem their size-proportional heuristic
    # approximates without one. Copying their formula/clamp would be
    # applying pixel-domain calibration to a constant that is already
    # mm-domain, not a calibration match, and their own floor (0.32 mm) is
    # already coarser than today's whole 0.2 mm default.
    #
    # Measured this directly on real fixtures rather than reasoning it
    # through: held one synthetic wavy contour fixed and swept `px_per_mm`
    # 3.0-40.0 (the range this app's real 40-180 mm `target_width_mm` bound
    # produces across the fixture corpus — measured 4.0-34.1 px/mm running
    # `run_stages` on every flat- and photo-lane testdata fixture at 40, 60,
    # 80, 90, 120, 150, 180 mm). The Hausdorff deviation between the
    # simplified and unsimplified contour stayed 0.185-0.200 mm across the
    # ENTIRE swept range — i.e. already scale-invariant in the metric that
    # matters — while vertex count varied 26-226 exactly as it should (a
    # design built from the same source pixels genuinely has less raw detail
    # to preserve at a smaller physical size, not more error at a bigger
    # one). Full pipeline runs on the flat-lane fixtures (`logo_whitebg.png`,
    # `logo_alpha.png`, `ribbon_curve.png`, immune to the photo lane's own
    # segmenter-resolution confounds) showed the same thing end to end:
    # smooth, sub-linear vertex growth with `target_width_mm`, no blocky
    # under-detail at 40 mm and no runaway vertex blowup at 150 mm. The one
    # fixture that DID show a dramatic vertex swing at small sizes
    # (`photo/summit_badge.png`, 1654 vertices at 40 mm collapsing to 627 at
    # 80 mm) traced entirely to a DIFFERENT mechanism — the sub-detail
    # rescue path's own fixed 0.5 px floor a few lines below this one in
    # `stage4_vectorize.py`, not this constant — confirmed by a per-region
    # breakdown: 1263 of 1654 vertices at 40 mm came from `rescued_
    # small_shape=True` regions, which bypass this tolerance entirely.
    # See `tests/test_run_tier.py::
    # test_simplify_tol_mm_realized_deviation_is_px_per_mm_invariant` and
    # `tests/test_pipeline.py::
    # test_simplify_tol_mm_stays_fine_across_the_real_target_width_range`
    # for the pinned regressions, and MASTER_SCOPE.md's Ember research entry
    # for the full writeup. Conclusion: no change justified by evidence —
    # left at 0.2 deliberately, not by default.
    simplify_tol_mm: float = 0.2

    # Stage 5 — sew order, underlap, pull compensation
    # Which garment/fabric the design is going on. The fabric preset supplies
    # pull compensation, underlay style, density adjustment and trim distance;
    # naming a garment picks its usual fabric. An explicit fabric_id wins.
    garment_id: str | None = None
    fabric_id: str | None = None
    # How far a color extends underneath the color that sews after it. Enough
    # to survive fabric pull, small enough never to read as a color error.
    overlap_mm: float = 0.25
    # Directional pull/push compensation (Laws 22-24). False is the shipped
    # behaviour: one isotropic `buffer(pull)` outward in every direction, which
    # is right on average and wrong everywhere specific — no major package does
    # it, because pull acts ALONG the stitch direction and push acts across it.
    #
    # True compensates each tier the way its stitches actually run:
    #   fill  – growth only along the fill angle, on the edges its rows
    #           penetrate; the edges the rows run parallel to keep artwork size.
    #   satin – growth stays isotropic, which is already exact on the rails (a
    #           column's stitch direction IS its boundary normal there), and
    #           each open END is cut back by `machine.PUSH_CUTBACK_MM` plus the
    #           pull the isotropic step wrongly added there.
    #
    # Default False because the cutback is sew-out-gated (playbook Part 4 test
    # 4) and because every committed golden is pinned to the isotropic result.
    directional_comp: bool = False

    # Stage 6 — fill. None means "use the machine default", so a caller can
    # override density without knowing the whole table.
    fill_row_mm: float | None = None
    fill_stitch_mm: float | None = None
    # None = per-region principal axis (what the browser engine does, and what
    # beat a fixed angle in practice). A number forces every region to it.
    fill_angle_deg: float | None = None
    # None = the fabric preset's fill underlay style. One of "none" |
    # "edge_run" | "center_run" | "edge_zigzag" | "edge_lattice" |
    # "double_lattice" | "zigzag" (fabrics.py's own vocabulary). Feeds the
    # fill and contour tiers only — satin underlay is a separate, narrower
    # knob (fabric.satin_underlay, gated by `underlay` below, not this field);
    # see the shape_overrides block for why that stays engine-internal for
    # now. Per-shape intent overrides this the same way border's mode is
    # overridden: `Region.meta["underlay_style"]` beats it in both
    # directions, and rides the same carry-forward as border/tier/fill_angle
    # (deterministic ids from `assign_shape_ids` — see `regions.py`'s docstring;
    # NOT `match_shape_ids`, which has no production caller).
    underlay_style: str | None = None
    underlay: bool = True

    # Which fill technique a fill-classified shape sews with.
    #
    # "tatami"  – straight rows at one angle. THE DEFAULT, and every golden in
    #             the suite is pinned to it.
    # "scanline_tonal" – the scan-line mono tonal tier (photo plan, technique
    #             row 8, stage6_scanline): parallel rows across one grain,
    #             local source-image darkness driving row spacing, penetration
    #             pitch and zigzag amplitude — the PhotoFlash halftone look.
    #             Strictly opt-in: setting this is ALSO what makes
    #             pipeline.run_stages carry source pixels forward for
    #             non-gradient classes, so the flat lane grows no raster
    #             payload while the flag is off. A shape the tier sews nothing
    #             for (all highlight) falls back to tatami, the same
    #             never-drop-artwork contract contour has.
    # "meander_tonal" – the meander mono tonal tier (photo plan, technique
    #             row 9, stage6_meander): ONE continuous non-crossing
    #             wandering line — an adaptive Hilbert traversal, Velho &
    #             Gomes 1991 — whose local spacing, penetration pitch and
    #             zigzag amplitude all follow source-image darkness; the
    #             Reef/Sfumato look, fabric left bare as the highlight
    #             value. Same opt-in plumbing, source-pixel gate and
    #             tatami-on-empty fallback as "scanline_tonal".
    # "streamline" – the streamline thread-paint tier, first (mono) slice
    #             (photo plan, technique row 10, stage6_streamline):
    #             Jobard–Lefer evenly-spaced streamlines traced in the ETF
    #             direction field (directionfield.py), separation modulated
    #             by local source-image darkness (highlight sews nothing —
    #             fabric shows), resampled to 2.5–4 mm run stitches. Regions
    #             whose field coherence is too low fall back to parallel
    #             lines at the house angle, per the field's own contract.
    #             Strictly opt-in: setting this is ALSO what makes
    #             pipeline.run_stages carry source pixels forward for
    #             non-gradient classes, so the flat lane grows no raster
    #             payload while the flag is off. A shape the tier sews
    #             nothing for (all highlight) falls back to tatami — the
    #             same never-drop-artwork contract contour has. Multi-color
    #             dark→light layering is `streamline_mode` below, built as
    #             the seam documented in stage6_streamline's module
    #             docstring. Also available per-shape, on ANY design
    #             (including a design that never sets this field —
    #             `fill_technique` can stay "tatami" for the rest of the
    #             shapes), as the review screen's `tier: "streamline"`
    #             override (contract v1.6, mirrors `tier: "sketch"`'s
    #             per-shape form immediately below — see the
    #             shape_overrides block). This is how a manually-classified
    #             ("flat") design reaches streamline fill without opting
    #             the whole design into the photo-plan preset.
    # "sketch" – the sketch tier (photo plan, technique row 12,
    #             stage6_sketch): the row-12 PRESET over rows 10+11, not a
    #             new engine — sparse mono streamline line work (row 10's
    #             tracer with the darkness field read at half strength, so
    #             strokes seed ~2.6x sparser at full black and give up to
    #             bare fabric at twice the highlight cutoff) PLUS the FDoG
    #             detail block (row 11) appended last, implied by this
    #             technique whether or not `detail_layer` is set — law 10's
    #             corpus fingerprint (layered run passes + detail lines,
    #             fabric as the tone value). Same opt-in plumbing,
    #             source-pixel gate and tatami-on-empty fallback as the
    #             three tonal tiers above; `streamline_mode` is ignored
    #             (a sketch is mono by definition). Also available
    #             per-shape as the review screen's `tier: "sketch"`
    #             override (contract v1.3, see the shape_overrides block).
    # "contour" – uniform inward offsets of the outline, sewn inner to outer
    #             (stage6_contour). Rows follow the silhouette instead of
    #             cutting across it, which is the one thing tatami structurally
    #             cannot do: even needle distribution in a shape whose width
    #             varies along its length. Rings, letterforms, crescents.
    #             Falls back to tatami on any shape contour produces nothing
    #             for, so turning it on can never drop artwork.
    #
    # Satin classification runs first either way — a ribbon is still a ribbon.
    #
    # READ THIS BEFORE TURNING "contour" ON. An adversarial pass on 2026-08-02
    # confirmed three defects no shipped test could see. As of 2026-08-04,
    # later the same day, the instrument that pass mandated exists and all
    # three are fixed; the tier still ships off because "tatami" is
    # byte-identical to the engine that has always shipped and this whole
    # class of claim is un-sew-out-gated regardless of how good the geometry
    # measures — flipping the default is Kent's call, not a geometry
    # question this file can settle on its own.
    #
    # THE INSTRUMENT (built first, as mandated): `barecircle.py` measures the
    # widest circle of bare fabric inscribable in a shape further than half a
    # thread width from any emitted stitch — rasterized exact-EDT, trusting
    # only the polygon and the runs, never this tier's own bookkeeping.
    # Validated against the pass's own figures (tests/test_barecircle.py):
    # Sb253ebba contour 0.640 cited / 0.644 measured, tatami 0.090 / 0.094;
    # the 10-point star's mitred-offset annihilation (offsets dead at
    # ~5.6 mm of inset against an inradius of 10.00, ledger charging ~0.2)
    # reproduces. ONE figure did not survive re-measurement as written: the
    # star's "2.94 mm bare disc" is a DIAMETER — every reconstruction
    # measures 1.28-1.43 mm bare RADIUS, and defect 2's own "silent on that
    # 1.47 mm bare radius" (= 2.94/2) only coheres under that reading.
    #
    #  1. A BARE CORE INSIDE ORDINARY SHAPES — FIXED 2026-08-04 (the shrink,
    #     later than the measurement above). `_rings` used to stop the
    #     moment the mitred `_offset` returned nothing, leaving every healthy
    #     shape a 0.86 mm structural centre dot (~10x tatami's 0.090); a
    #     notched interior could be annihilated wholesale (the star's
    #     1.33 mm core). Two fixes close most of it: `_refine_terminal_
    #     generation` (stage6_contour.py) bisects the LAST ring's own inset
    #     onto the true sewability floor instead of wherever the fixed
    #     spacing grid happened to land, and a finishing pass patches
    #     whatever `barecircle.widest_bare_circle` still calls the widest
    #     bare spot with an ordinary tatami patch, iterating on the
    #     instrument itself rather than a vector reconstruction (tried
    #     first, measured worse — see the finishing-pass comment in
    #     stage6_contour.py). Re-measured: discs and the dumbbell now read
    #     0.067-0.13 mm (was 0.86 mm uniformly); `machine.CONTOUR_BARE_CORE_MM`
    #     recalibrated 0.87 -> 0.13 to match, with `starved_threshold_mm`
    #     re-derived off it (see item 2 below — the formula didn't change,
    #     what it evaluates to did). The star's annihilated core — a
    #     different failure mode than a healthy shape's structural dot —
    #     shrinks too (1.33 -> 0.441 mm) but stays correctly `starved`.
    #  2. `starved` MISCALIBRATION — FIXED 2026-08-04, both directions.
    #     The area-fraction gate is gone; `starved` IS the instrument's
    #     measurement, fired when the widest bare spot beats
    #     `barecircle.starved_threshold_mm` (the measured structural dot plus
    #     half a ring spacing — 0.33 mm at shipped density post-shrink, was
    #     1.07 mm pre-shrink; derivation at the function). The old gate's
    #     silence on the star's 1.47 mm class now fires; its false alarms —
    #     whitebg's Sf5200f3f at 0.499 mm bare (the cited "firing on 0.51")
    #     and Sb253ebba at 0.644, both under a healthy disc's OLD, pre-shrink
    #     dot — are now silent against either threshold. Proven in both
    #     directions in tests/test_barecircle.py and tests/test_contour.py.
    #  3. TRANSITION-CHORD CONTAINMENT — FIXED 2026-08-04. `_link` now
    #     containment-tests the ring-to-ring crossing chord and banks the
    #     path (travel, not an escaping stitch) when it fails. The cited
    #     15 mm disc with a 0.3 mm hole reproduced (one transition 0.255 mm
    #     outside pre-fix) and is the regression pin; the cited 0.45 mm neck
    #     could not be reconstructed from its description — four neck
    #     geometries tried, none escapes even pre-fix.
    #
    # "crosshatch" – two overlapping tatami passes on the same shape, one at
    #             the shape's own fill angle and one at angle+90
    #             (stage6_fill._crosshatch_fill_paths), each pass
    #             individually spaced `machine.CROSSHATCH_ROW_SCALE_FACTOR`
    #             times wider than a normal single-pass row so the two passes
    #             TOGETHER land at a combined density near a single-pass
    #             fill's, not roughly double it. Reuses the exact mechanism
    #             `_underlay_paths`'s "double_lattice" style already relies
    #             on for its own +-45deg underlay passes — travel between the
    #             two passes is stitch_shape's ordinary emit() bridging,
    #             nothing new. Falls back to plain tatami on any shape it
    #             produces nothing for, the same never-drop-artwork contract
    #             contour has. Also available per-shape, on ANY design
    #             (`fill_technique` can stay "tatami" for the rest of the
    #             shapes), as the review screen's `tier: "crosshatch"`
    #             override — mirrors `tier: "streamline"`'s per-shape form
    #             above (see the shape_overrides block). Unlike every tonal
    #             tier above, crosshatch needs no source pixels: it is a
    #             purely geometric variant of the plain tatami fill, so its
    #             per-shape override works on any design, photo-classified or
    #             not, with no raster-plumbing opt-in cost. Lower-stakes than
    #             "contour" too: it ships OPT-IN per-shape or per-design
    #             only, never a default, so turning it on cannot move any
    #             existing golden.
    # "wave" – tatami rows with a subtle perpendicular sine wobble on every
    #             INTERIOR row point (stage6_fill._wave_row_points):
    #             y + machine.WAVE_AMPLITUDE_MM * sin(2*pi*x /
    #             machine.WAVE_LENGTH_MM + phase), phase alternating by row
    #             parity (0 / pi) so neighbouring rows' waves move opposite
    #             ways instead of stacking into a corrugated-cardboard look.
    #             Both row ends still land exactly on the boundary — the
    #             same edge-crispness contract `_row_points` itself
    #             documents — and the interior grid's own stagger
    #             (`_stagger_phase`) is untouched, so the wave rides on top
    #             of it rather than replacing it. Same opt-in / per-shape /
    #             no-source-pixels / never-drop-artwork contract as
    #             "crosshatch" immediately above, including the
    #             `tier: "wave"` per-shape override.
    # "chevron" – a simplified, TEXTURAL herringbone impression, not a full
    #             multi-angle banded herringbone (that needs new column/
    #             travel logic, deliberately out of scope for this family):
    #             interior row points alternate
    #             +-machine.CHEVRON_AMPLITUDE_MM every stitch
    #             (stage6_fill._chevron_row_points), on the same staggered
    #             grid tatami already builds. Same contract as "wave" above,
    #             including the `tier: "chevron"` override.
    # "brick" – swaps `_row_points`' van-der-Corput anti-moire stagger for a
    #             strict 2-phase "running bond": even rows' interior grid
    #             starts at phase 0, odd rows at phase `stitch_mm / 2`
    #             (stage6_fill._brick_row_points). No new machine.py
    #             constant — the phase IS `stitch_mm / 2`, already a known
    #             quantity. Same contract as "wave"/"chevron" above,
    #             including the `tier: "brick"` override.
    fill_technique: str = "tatami"

    # Task A2 (2026-08-14, tools/pro_parity): the corpus's professional
    # SOLID fill elements sew at roughly double a single ordinary pass's
    # density — see machine.FILL_DENSITY_BOOST_MIN_WIDTH_MM's own comment
    # for the measurement and the two-pass "cross + top" mechanism. It only
    # ever fires where `fill_technique` is still plain "tatami" (any other
    # technique — crosshatch, wave, sketch, streamline, contour, ... — is an
    # explicit choice and is left alone) AND the shape itself is solid
    # (stage6_fill.is_solid_fill) — a thin strip or lattice arm stays
    # single-pass regardless of this flag.
    #
    # SEW-OUT GATED, same standing as `directional_comp` above and
    # `PUSH_CUTBACK_MM` in machine.py: False is the shipped default because
    # every golden in the suite is pinned to plain single-pass tatami
    # (stage6_fill.stitch_shape's own docstring) and turning this on by
    # default moved a real, measured set of them — not a bug in the
    # technique, but a shipped-default change that belongs behind Kent's
    # physical sew-out, exactly the bar `directional_comp` and
    # `PUSH_CUTBACK_MM` are held to. `tools/pro_parity/prep_all.py` sets
    # this True explicitly — that harness's whole job is measuring a
    # candidate engine change against the corpus before it ships, which is
    # exactly what this flag needs measured.
    fill_density_boost: bool = False
    # streamline's own sub-mode — irrelevant (and unread) unless
    # fill_technique == "streamline".
    #
    # "mono"    – THE DEFAULT: one thread, `stage6_streamline`'s first slice,
    #             d_sep driven by raw source darkness.
    # "layered" – the multi-color seam: a 3-5 chart-shade decomposition of
    #             the region's own pixels (`stage6_blend`'s shade-selection
    #             machinery, reused rather than reinvented — see
    #             `stage6_streamline._shade_layers`), one J-L streamline set
    #             traced per shade against that shade's own coverage-share
    #             map (not raw darkness), stacked dark shade first. Every
    #             shade boundary is an unconditional colour change (forced
    #             jump+trim, never travel-bridged) — a spool change always
    #             cuts thread regardless of geometry. "mono" is
    #             byte-identical to the tier as it shipped before this mode
    #             existed.
    streamline_mode: str = "mono"
    # The detail layer (photo plan, technique row 11, first slice —
    # stage6_detail): FDoG coherent line extraction (Kang 2007, the same
    # paper and ETF machinery as directionfield.py) over the source raster,
    # emitted as BEAN runs in one extra color block sewn LAST, on top of
    # every fill — photo details (edges, whiskers, panel lines) as discrete
    # top objects instead of merging into fill quantization. ORTHOGONAL to
    # fill_technique on purpose: it composes with any fill tier (that is
    # the row's whole point — details ride on top of whatever renders the
    # tone). Strictly opt-in: False is byte-identical to the engine before
    # the layer existed (the byte-identity suites pin that), and setting it
    # is ALSO what makes pipeline.run_stages carry source pixels forward —
    # the flat lane grows no raster payload while the flag is off. A design
    # the extractor finds no coherent lines for (flat color, noise) emits
    # NOTHING extra — no block, no warning — rather than failing. The
    # row's other half (the eye recipe) is a documented seam, not built:
    # see stage6_detail's module docstring.
    detail_layer: bool = False
    # Split a photo region whose own pixels span more light-to-dark range than
    # one thread can express into several regions, each getting its own mean
    # colour, palette weight and spool (stage2_photo_segment.
    # split_tonal_regions). Exists because a region IS the unit that owns a
    # thread: Kent's owl body is one 4200 mm2 region spanning 81 points of L*,
    # so it sews as a flat pale mass however good the fill tier is. The blend
    # tier was meant to rescue this and, at the time this flag was written,
    # could not — its per-shade threads were computed and then never read by
    # stage 7 (measured on gradient_ramp_linear.png: 4 shades chosen, 1
    # colour change emitted). FIXED 2026-08-19 — stage7_sequence._shade_
    # blocks now reads shade_thread_index and sews the shades it chooses;
    # kept here as the motivating history, since splitting upstream is still
    # the one route to a region's own thread getting more than one spool
    # without any source-reading fill tier being in play at all.
    # Splitting upstream needs no new machinery downstream. It does NOT stay
    # inside the palette's existing budget, though (F3, 2026-08-19
    # correction of this comment's old claim): the shade path (stage6_blend's
    # per-shade snap, read by stage7_sequence._shade_blocks) picks its own
    # per-shade thread independent of `select_palette`'s own choice, and the
    # two can and do disagree — measured 9 emitted threads outside the
    # selected palette, 28 spools sewn vs 14 pre-branch, on Kent's owl.
    # Palette binding for the shade path is not something this flag solves;
    # `shade_palette_bind` below (2026-08-23) is its default-OFF measuring
    # instrument — shipped behaviour is still unbound, pending Kent's call.
    # Opt-in pending a corpus run; see MASTER_SCOPE.md's blend-tier entry.
    # Spec 2026-08-18 decision 2: photo_subject and photo_scene split by
    # default (cfg false still means yes for those classes); gradient and flat
    # do not (cfg true is the only way to split them).
    split_tonal_regions: bool = False
    # EXPERIMENT, default OFF, pending Kent's quality call — option (a) of
    # docs/superpowers/plans/2026-08-23-shade-palette-binding.md, the decision
    # doc this flag exists to put live evidence in front of. The shade path is
    # the palette cap's REMAINING escape hatch now that the region-level
    # resnap is bound (stage4_vectorize.revalidate_threads, 2026-08-23): on
    # the photo route every tonally-split region decomposes into 3-5 shades
    # and each shade snaps to the FULL ~400-spool chart independently of
    # `select_palette`'s choice (stage6_streamline._shade_layers ->
    # stage7_sequence._shade_blocks) — measured on the four acceptance
    # portraits, post-region-fix: 43/45/50/14 block-level threads against
    # palettes of 15/12/12/7, i.e. 28/33/38/8 spools the operator's cone list
    # never names (and a listed cone can sew ZERO stitches when every shade of
    # its regions snaps elsewhere — face_closeup_blur's 1565). True masks the
    # shade snap to the spools this plan's own regions sew (photo classes
    # only, the same strict class gate the region fix uses) and merges
    # ADJACENT same-spool shades into one honest fewer-shade layer — the
    # block level already buckets same-spool shades at sew time
    # (stage7_sequence._shade_blocks), so the merge makes the DECOMPOSITION
    # say what actually sews rather than listing shades that only look
    # distinct. The cost, and why this is not simply on: each bound shade
    # moves onto its nearest palette spool (plan-doc estimate median 8-11.2
    # dE00, worst ~20) and the merges re-collapse shade distinctions — the
    # owl-body flat-mass defect's ghost in palette-sized steps
    # (`split_tonal_regions` above: a region IS the unit that owns a thread).
    # Trading shade fidelity for a loadable cone list is Kent's call, made
    # from the acceptance A/B's bound_shade arm (tools_acceptance.
    # variant_matrix), not an engineering default. False is byte-identical
    # shipped behaviour, pinned by tests/test_shade_palette_bind.py.
    shade_palette_bind: bool = False
    # The acceptance A/B's speckle-gate knob, funded by Kent 2026-08-23 after
    # the tonal-eng measurement (docs/tonal-eng-measurements-2026-08-22.md §1)
    # showed RAMP_SPECKLE_MAX — not the r² floor — blocks 41 of the 42 real
    # regions whose tonal structure the ramp model explains at r² 0.5-0.99:
    # real-photo texture reads as speckle even when a ramp explains 92% of
    # the region. None (the default) is byte-identical shipped behaviour.
    # Set to an r² bar (the harness's relaxed arm uses RAMP_R2_MIN itself,
    # 0.5) and a region fitting AT OR ABOVE the bar passes the speckle gate
    # regardless — the fit quality vouches for the region, the texture no
    # longer vetoes it. Exists so Kent's eyes can judge stock vs relaxed on
    # one contact sheet; NOT a shipped default, and flipping it into one is
    # an eyeball-loop verdict, not an optimisation.
    blend_speckle_r2_override: float | None = None
    # None = fill_row_mm (or the machine default). Contour rings are the same
    # 0.40 mm apart as tatami rows; this exists so the ring tier can be opened
    # up independently, which is what "best used for open fills with low stitch
    # counts" means in Wilcom's own positioning of Offset Fill.
    contour_spacing_mm: float | None = None
    # How far a chord may bow off the ring it approximates (Ink/Stitch calls it
    # running stitch tolerance). None = machine.CONTOUR_TOLERANCE_MM.
    contour_tolerance_mm: float | None = None

    # Satin classification. Ribbons up to this wide sew as satin columns;
    # None = the machine default (3.0 mm, matching the browser engine).
    # satin=False forces everything to fill — the pre-step-4 behaviour,
    # kept as an escape hatch for comparison sew-outs.
    satin: bool = True
    satin_max_width_mm: float | None = None

    # Split satin. A satin cross longer than the threshold carries
    # intermediate penetrations, staggered station to station so the holes
    # never line up (machine.SPLIT_* carry the corpus measurements: the
    # majority of professional crosses split from ~5 mm, ~100% by 7.5).
    # True is the corpus-majority default; False sews raw crosses however
    # long — a real house style (jolly-af and sweet-heart ship 6.5-7 mm raw
    # crosses), not a safety toggle. None = machine.SPLIT_SATIN_ABOVE_MM.
    # Wiring: stage 7's satin_shape call maps these to its `split_above_mm`
    # kwarg (False -> math.inf). Until that one-line wiring lands, the
    # machine default applies — identical behaviour for this default config.
    split_satin: bool = True
    split_satin_above_mm: float | None = None

    # Stage 6 — the border tier (an outline sewn as one closed circuit).
    #
    # "off"  – no borders. THE DEFAULT, and it is a measured choice, not
    #          timidity: our tatami fill has no ragged edge to cover (measured
    #          starvation 0.00 mm with zero variance on 13 real letterforms at
    #          three sizes, because `_row_points` puts both row ends on the
    #          shape's edge by construction), and the corpus shows a plain
    #          majority of fills going unbordered — 18 borders against 21 fill
    #          elements and 150 satin elements in the same 19 files. An
    #          unearned border is ~400 stitches per ring and a heavier logo for
    #          nothing, and Kent pays for machine time.
    # "auto" – satin border on every fill-classified shape wide enough to host
    #          a column, bean run where it is not. A shape classified as satin
    #          never gets one; see stage 7.
    # "bean" – the light tier wherever a centreline fits.
    #
    # Per-shape intent overrides the mode: `Region.meta["border"] = True/False`
    # rides the existing id-stability carry-forward (`assign_shape_ids` re-derives
    # the same id from the same content — see `regions.py`'s docstring), so a
    # review-screen decision survives a re-digitize with no new contract.
    border: str = "off"
    border_width_mm: float | None = None

    # Stage 6 — the appliqué tier (docs/specialty-techniques-2026-08-01.md §2).
    #
    # OFF by default, and that default is load-bearing: with `applique` False
    # nothing in this block is read, no step metadata is attached, and a design
    # sews byte-for-byte what it sewed before the tier existed. `tests/
    # test_applique.py::test_applique_off_is_byte_identical` pins that.
    #
    # Per-shape intent overrides the mode in both directions, exactly as
    # `border` does: `Region.meta["applique"] = True/False` rides the existing
    # id-stability carry-forward, so a review-screen decision survives a
    # re-digitize with no new contract.
    applique: bool = False
    # "trim_in_place" (4 layers, 2 stops) | "pre_cut" (3 layers, 1 stop).
    # Wilcom's guide-run panel makes this an explicit switch and §2.1 calls it
    # "the single biggest branch in the feature".
    applique_mode: str = "trim_in_place"
    # Shop-level trim discipline: tight | normal | loose. §2.3's implementation
    # corollary is emphatic — expose THIS and derive the cover width from the
    # tolerance stack. Do not expose cover width as a free number the user
    # guesses at.
    applique_trim_discipline: str = "normal"
    # Pre-cut only: how accurately the piece lands. "hand" (0.75 mm) or
    # "heat_tacked" (0.40 mm). Laser cutting adds no geometry, it removes
    # tolerance — the whole benefit shows up here (§2.9).
    applique_placement: str = "hand"
    # Which material floor the solved width may not go under: twill | felt |
    # woven | knit | loose_weave (§2.13 W_floor_material).
    applique_material: str = "woven"
    # Tackdown stitch type: run | double_run | zigzag | e_stitch | none.
    # Trim-in-place wants run/double_run — a zigzag tack gets clipped by the
    # scissors and leaves fabric whiskers (§2.7). None = pick from the mode.
    applique_tackdown: str | None = None
    # Cover stitch type: satin | zigzag | e_stitch. Zigzag at 1.69 mm is the
    # tackle-twill look and a genuinely different aesthetic, not a cheap satin.
    applique_cover: str = "satin"
    # Override the solved cover width, in mm. None = solve from the tolerance
    # stack, which is what you want; a number here is an escape hatch for a
    # sew-out comparison and is still clamped to [2.5, 5.0].
    applique_cover_width_mm: float | None = None

    # --- Review-screen shape edits (the shape-layers contract v1) ----------
    #
    # Both fields are keyed by the content-derived shape_id the review payload
    # reports (`regions.assign_shape_ids`): the same artwork re-digitized with
    # the same stage 1-4 parameters produces the same ids, which is what makes
    # a stateless edit round-trip possible at all. Applied by
    # `regions.apply_shape_edits` / `apply_layer_overrides`, called from
    # `pipeline.run_stages` so both `digitize()` and a service re-digitize
    # pass through them. Empty (the defaults) is byte-identical to the engine
    # before the contract existed.
    #
    # Shapes the user removed on the review screen. Dropped AFTER stage 4 —
    # ids are assigned against the full generation first, so the survivors'
    # ids cannot churn — and reported via SHAPES_DELETED_BY_USER so the panel
    # can say "2 shapes hidden by you" rather than losing them silently. An id
    # that matches nothing is a SHAPE_EDIT_UNKNOWN_ID warning, never an error:
    # the art may have changed under the edit.
    deleted_shape_ids: list = field(default_factory=list)
    # Per-shape decisions, keyed by shape_id. Each value is a dict that may
    # hold any of:
    #   thread_index: int     – recolor: index into the job's chart. Applied
    #                           to the Region itself before stage-5 grouping,
    #                           so the shape moves to that thread's color
    #                           block; the palette gains the thread if nothing
    #                           else sews it.
    #   fill_angle_deg: float – this shape's fill angle. Beats the global
    #                           fill_angle_deg and the per-region PCA; the
    #                           full precedence is stated where stage 7
    #                           decides it.
    #   tier: str             – "auto" (default) | "satin" | "fill" | "run"
    #                           | "sketch" (contract v1.3, photo plan row
    #                           12: sparse mono sketch rendering for this
    #                           one shape — requesting it is also an
    #                           explicit source-pixel opt-in, and it does
    #                           NOT imply the design-wide detail block the
    #                           fill_technique="sketch" preset appends)
    #                           | "streamline" (contract v1.6, photo plan row
    #                           10's evenly-spaced thread-paint tier for this
    #                           one shape — same explicit source-pixel opt-in
    #                           as "sketch"; this is what lets a manually-
    #                           classified/flat-lane shape reach streamline
    #                           fill without the whole design setting
    #                           fill_technique="streamline"; direction field
    #                           is always this design's own prepped raster
    #                           read through directionfield.py, never a
    #                           shape-geometry-derived field, so a genuinely
    #                           textureless shape falls back to parallel
    #                           lines at fill_angle_deg/the house angle
    #                           rather than following anything invented).
    #                           Forces the stitch tier. Geometry the forced
    #                           tier cannot sew falls through the same rescue
    #                           ladder the auto path uses, so artwork never
    #                           silently vanishes.
    #   border: str           – "off" | "auto" | "bean". Per-shape border
    #                           intent; beats the global `border` mode in both
    #                           directions. (The pre-contract True/False meta
    #                           form is still honoured.)
    #   layer: int            – explicit sew-order layer; stage 5 already
    #                           orders color blocks by meta["layer"]. Applied
    #                           AFTER the palette is compacted, so moving a
    #                           shape never drops its thread from the color
    #                           list.
    #   sew_order: int         – explicit position (0-based) in this shape's
    #                           color layer's OWN sew sequence (contract
    #                           v1.2) — distinct from `layer`, which picks
    #                           which layer a shape sews in; this picks where
    #                           within it. Stage 7 forces a pinned shape into
    #                           its slot once the running pick count reaches
    #                           it, and fills every unpinned slot with
    #                           nearest-neighbour exactly as before, so a
    #                           layer with no override sews byte-identical.
    #   underlay_style: str    – this shape's fill/contour underlay style
    #                           (the `underlay_style` field's own vocabulary,
    #                           "none" included). Beats the global
    #                           `underlay_style` AND `underlay` in both
    #                           directions — an explicit per-shape style wins
    #                           even with underlay off design-wide, and an
    #                           explicit "none" wins even with it on — the
    #                           same "beats the mode both ways" contract
    #                           `border` already has. Does not reach satin:
    #                           satin's own underlay is `fabric.satin_underlay`,
    #                           gated only by `underlay`, and stays engine-
    #                           internal — its vocabulary is effectively binary
    #                           (a spine run, plus zigzag above
    #                           machine.SATIN_ZIGZAG_ABOVE_MM) where fill's is
    #                           seven styles, so it was a materially different,
    #                           lower-value knob to expose and is deferred, not
    #                           forgotten.
    #   boundary_override: list – (contract v1.4) hand-edited exterior ring
    #                           replacing this shape's outline: a list of
    #                           [x, y] mm points in the same design-center,
    #                           y-down coordinate system as the review
    #                           payload's `outline_mm` (which is exactly
    #                           where a client reads the starting points
    #                           from). Holes are NOT touched by this key —
    #                           they ride forward unchanged from the shape's
    #                           own current geometry; boundary editing is
    #                           exterior-only in this slice. Applied directly
    #                           to `Region.polygon` (not read again later the
    #                           way tier/fill_angle/underlay_style are), so
    #                           every downstream stage sees an ordinary
    #                           polygon and needs no boundary-override-
    #                           specific handling. Defensively validated in
    #                           both `digitizer_service.app` (point count,
    #                           finite numbers — a fast 400) and
    #                           `regions.apply_shape_edits` (the same, plus
    #                           the geometry checks that need the shape's
    #                           actual polygon: must build a valid, simple
    #                           polygon — no self-intersection, no hole
    #                           poking outside the new outline — with area
    #                           and perimeter at least `machine.
    #                           RUN_MIN_AREA_MM2` / `RUN_MIN_LOOP_MM`, the
    #                           same sewability floor stage 4's own run-tier
    #                           rescue already holds auto-digitized regions
    #                           to). A rejected edit is a ValueError at the
    #                           core layer (a 400 at the service layer,
    #                           before the job ever runs) — never a silent
    #                           repair and never a crash downstream.
    # Values ride Region.meta so stages 5 and 7 pick them up where each
    # decision is made (boundary_override is the one exception: it rides
    # Region.polygon itself, plus a Region.meta record of the edit — the record
    # is what `match_shape_ids` would carry, though that function is not wired;
    # see `regions.py`'s docstring). Unknown shape_ids warn
    # (SHAPE_EDIT_UNKNOWN_ID).
    shape_overrides: dict = field(default_factory=dict)

    # Shape identity edits (contract v1.5, `regions.apply_shape_merges` /
    # `apply_shape_splits`) — the other half of the shape-recognition gap
    # `boundary_override` above did not touch: those two change ONE shape's
    # geometry/attributes, these change the SET of shapes. Applied BEFORE
    # `shape_overrides`/`deleted_shape_ids` (right after stage 4 assigns ids
    # against the full generation, same ordering reasoning `apply_shape_edits`
    # already documents) so a request MAY layer a `shape_overrides` entry onto
    # a shape these mint this same call, if the caller independently computes
    # the same deterministic id `_merge_shape_id`/`_split_shape_id` would — not
    # required; the reference Studio UI does not do this in v1, it always
    # waits for the resulting review payload before adding further overrides.
    #
    #   merge_shape_ids: [[shape_id, shape_id, ...], ...] — each inner list at
    #     least 2 distinct ids to union into ONE new shape. v1 restrictions
    #     (see `regions.py`'s own comment above `apply_shape_merges` for the
    #     full reasoning): every source shape must share one thread_number
    #     (no cross-color merge) and have no holes; the union must reduce to
    #     one Polygon (the sources must already touch or overlap — two
    #     disjoint shapes are rejected, not bridged). The new shape's id is a
    #     hash of the (sorted) source ids, never geometry-derived, so it is
    #     stable across an identical resubmit. Per-shape styling
    #     (border/tier/fill_angle_deg/sew_order/underlay_style) is seeded from
    #     the LARGEST source shape; `boundary_override` is never carried
    #     forward (it describes a hand-edited shell for a specific OLD
    #     polygon that no longer exists after the merge).
    #   split_shapes: {shape_id: [[x0, y0], [x1, y1]]} — a straight cut line
    #     (mm, the same design-center/y-down space `outline_mm` reports) that
    #     divides ONE shape into exactly two new shapes. Not an arbitrary
    #     polyline — a single straight line, extended internally past the
    #     shape's own bounding box so the caller need only send the two
    #     dragged endpoints. A line crossing one of the shape's own holes is
    #     rejected rather than silently turning the hole into a notch on both
    #     halves. Each new piece's id hashes the source id, the line's
    #     endpoints, and which piece (0/1, assigned by centroid order — never
    #     shapely's internal split() ordering, so it cannot flip between
    #     otherwise-identical runs); styling is seeded from the source shape
    #     onto BOTH new pieces, `boundary_override` dropped for the same
    #     reason as merge.
    #
    # A group/line naming an id the artwork no longer has is a warning
    # (SHAPE_EDIT_UNKNOWN_ID) and that one merge/split is skipped — the same
    # "the art may have changed under the edit" posture every other key here
    # already takes. A GEOMETRICALLY bad request (mixed threads, a present
    # hole, a non-adjacent merge, a line that does not cross cleanly, a piece
    # under the sewability floor) is a `ValueError` — a real, checkable
    # mistake in the request, not staleness.
    merge_shape_ids: list = field(default_factory=list)
    split_shapes: dict = field(default_factory=dict)

    # Debug artifacts: written per stage when set
    debug_dir: Path | None = None

    # Forward-compat scratch. Known keys:
    #   shapefield: bool — DT-first migration M1
    #               (docs/dt-first-architecture-2026-08-01.md §2). Off by
    #               default (absent or falsy = today's path, byte-identical
    #               by construction). On routes stage6_satin's skeleton/DT
    #               extraction through digitizer_core/shapefield.py's
    #               ShapeField instead of stage6_satin's own inline
    #               rasterize+medial_axis call — same numbers, hoisted for
    #               a later stage (M2/M3, not this one) to eventually share.
    #   photo_sequencing: bool — explicit opt-in to photo depth sequencing
    #               (plan §2 row 14) for a design stage 0 did NOT classify
    #               photo: depth-sorted color layers (background first, then
    #               dark→light, explicit detail tiers last —
    #               stage7_sequence.depth_sort_layers) plus the photo
    #               underlay split (light-mesh fill underlay, spine-run
    #               satin underlay). Photo-classified designs get both
    #               automatically; absent or falsy changes nothing, so the
    #               flat and gradient lanes stay byte-identical.
    extra: dict = field(default_factory=dict)

    # Step 9 — preflight scoring. Whether the service attaches a preflight
    # report to a finished job. On by default because the report is the point
    # of digitizing through the service at all; off is for callers that score
    # separately (or benchmark the pipeline without the extra stage-1 pass
    # the thread-match check costs). Thresholds live in preflight.py with
    # their citations, deliberately not here: they are measurements, not
    # preferences.
    preflight: bool = True

    # Stage 7 — chaining. Whether a needle-up move that would be trimmed may
    # instead be sewn as a needle-down link, when its path is buried under a
    # colour that sews later or rides over work this colour has already laid
    # (chaining laws 59-62; docs/chaining-laws-2026-08-01.md). Distance stops
    # being the decision variable — coverage is — and `fabric.trim_at_mm` is
    # left governing only the moves that cannot be covered.
    #
    # OFF BY DEFAULT AS OF 2026-08-02, and it shipped on for less than a day.
    # The laws are right and the win is real — benchmark trims/1k 8.42 -> 2.63,
    # inside the professional band for the first time — but the COVERAGE TEST
    # that makes a link safe is measured against polygons, and a polygon is not
    # thread.
    #
    # `_link_cover` quotes `p.polygon` for every shape the block has sewn. A
    # fill does not stitch its whole polygon (its first row sits half a row
    # inside the boundary, and `_columns` drops non-monotone spans), and a
    # satin column does not either (it stops short at the tips and fans on
    # curves). So the router is told it may travel over ground its own colour
    # never reaches, and it does.
    #
    # Measured on the benchmark at 90 mm, against the union of every emitted
    # non-travel stitch in the design, over each link's REAL sewn path
    # (previous run's last point -> link -> next run's first point), bare being
    # further than half a thread width from any thread of any colour:
    #
    #     left_chest  chain off:  0 links,  0 exposed,  0.00 mm bare
    #     left_chest  chain ON:  23 links, 17 exposed, 12.38 mm, worst 0.673 mm
    #     full_back   chain off:  1 link,   0 exposed,  0.00 mm bare
    #     full_back   chain ON:  31 links, 26 exposed, 29.11 mm, worst 1.055 mm
    #
    # full_back is fleece_sweatshirt, a stock preset. The control is exactly
    # zero, so every millimetre of that is chaining's.
    #
    # Neither shipped instrument can see it, and that is structural, not an
    # oversight: `tests/test_chaining.py::_uncovered_links` and
    # `tools/chain_probe.py::uncovered_travel` both rebuild the cover from the
    # same polygons the router trusted, both skip one-point links (37% of the
    # benchmark's), and both test `LineString(run.points)` when `_link_stitches`
    # returns only the route's INTERIOR — so up to RUN_STITCH_MM at each end is
    # never examined by anything.
    #
    # Turning this off costs a needle-up move, not a thread cut: refusing a
    # link makes it a jump, and the measured trims/1k does not move. That is
    # the cheap direction to be wrong in, and a float on fleece is not.
    #
    # UPDATE 2026-08-03: the first of the three preconditions is done.
    # `_link_cover` now builds the already-laid half of its cover from `runs`
    # — the block's real emitted stitch centrelines, buffered to their real
    # thread width — instead of from `p.polygon`. Measured on the committed
    # `logo_alpha` fixture (the benchmark file the numbers above were measured
    # on lives outside the repo and could not be re-measured): chaining's
    # extra links (10 -> 14) now add ZERO bare exposure — `exp`/`bare`/`worst`
    # land on exactly the same figures chaining OFF does — while still
    # cutting trims (13 -> 9) and total stitch count (3012 -> 2992). See
    # `tests/test_chaining.py::test_chaining_adds_no_bare_fabric_exposure_on_
    # the_committed_fixture`.
    #
    # UPDATE 2026-08-04: the second is done too. `covered_by` — the half of
    # the cover whose stitches do not exist yet at routing time — is now
    # eroded by LINK_COVER_INSET_MM (0.75 mm, machine.py has the full
    # derivation table) before it may bury a link. Derived from measurement
    # on both committed fixtures, real emitted runs vs the artwork polygon
    # `covered_by` quotes: fill's nearest centreline stops up to 0.223 mm
    # inside the boundary (thread edge 0.023 mm shy), satin's up to 0.501 mm
    # (edge 0.301 mm shy — tips stop short, columns fan), and a run-tier
    # shape covers no interior at all, honest only once eroded away at its
    # inradius (0.527/0.539 mm measured). Worst measured 0.539 +
    # LINK_COVER_TOL_MM the cover buffers back on = 0.739, rounded up to
    # 0.75. Re-measured with chaining ON after the inset (chain_probe, both
    # committed fixtures): every link the inset disqualifies becomes a jump,
    # never an exposure, and on these fixtures none needed it — logo_alpha
    # still links 13 -> 17 and trims 14 -> 10 (st 3312 -> 3292), logo_whitebg
    # unchanged (chaining adds nothing there, with or without the inset),
    # chaining's ADDED bare exposure 0.00 mm on both (exp/bare/worst land on
    # exactly the chain-off floor: 0.7 mm/0.2057 and 0.8 mm/0.2045, stage 6's
    # own pre-existing in-shape travel). The inset is live, not idle: it
    # removes 20-32% of each block's future-colour cover area on logo_alpha
    # and erodes the run-tier sliver out of the cover entirely; the fixtures'
    # links just never rode the dishonest margin. Pinned by
    # `tests/test_chaining.py::test_a_sliver_of_a_future_colour_no_longer_
    # counts_as_cover` (a 1.2 mm band that linked pre-inset must now cut).
    # What no inset can fix, measured so nobody re-derives it: hairline gaps
    # between fanned satin crosses persist at any inset (<= 0.127 mm
    # inscribed radius, <= 0.121 mm beyond the thread edge) — under one
    # thread width, left to the sew-out below.
    #
    # UPDATE 2026-08-11: the third structural hole is closed — TIER
    # blindness. `covered_by` unions later layers' artwork with no idea what
    # tier each shape will sew as, and a shape pinned `tier: "run"` sews
    # only its outline: its polygon promised areal cover no thread will ever
    # provide, at ANY size — the inset bounds a fill/satin tier's
    # sub-millimetre boundary shortfall, not a whole interior. Stage 7 now
    # predicts run-tier shapes with the same predicate `stitch_one` routes
    # on (explicit tier "run", or the small-shape rescue's area floor) and
    # subtracts their artwork from every later-colour cover before the
    # inset (`_link_cover`'s `run_tier_art`; pinned by
    # tests/test_chaining.py::test_a_later_run_tier_shape_buries_nothing —
    # a 10 mm-tall run-tier bridge that linked pre-fix must now cut). The
    # verification instruments stopped sharing the router's blind spots in
    # the same pass: `_uncovered_links` now tests one-point links (37% of
    # the benchmark's — export sews a plain STITCH record through them) and
    # the REAL sewn path including the two endpoint segments
    # `_link_stitches` never stores. Acceptance, measured with
    # `_thread_bare_mm` on all four fixtures (benchmark = the committed
    # enthusiast_logo @ 82 mm/left_chest, full_back = same art on the stock
    # fleece preset, left_chest = logo_whitebg, ribbon = ribbon_curve):
    # chaining-added bare thread is 0.00 mm on every one, and 0.0 ABSOLUTE
    # where the chain-off floor is zero (benchmark, full_back, ribbon —
    # left_chest keeps stage 6's own pre-existing ~0.10 mm in-shape-travel
    # floor, chain-on == chain-off to the digit). The corrected cover
    # refused no link the fixtures actually used: benchmark still links
    # 1 -> 18 and lands 4.06 trims/1k chain-on (9.82 off); full_back
    # 1 -> 14, 7.35 -> 4.73. Pinned by
    # tests/test_chaining.py::
    # test_chaining_adds_zero_bare_thread_on_every_acceptance_fixture.
    #
    # Still outstanding, and still why this stays off by default:
    #   - A sew-out that says at what clearance a needle-down float actually
    #     shows — LINK_COVER_TOL_MM is still a thread spec, not a measurement.
    chain_links: bool = False
