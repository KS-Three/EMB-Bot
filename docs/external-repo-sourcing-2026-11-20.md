# External sourcing sweep — four tracks, 2026-11-20

Kent asked for a project dependency and sourcing review. A first attempt
(Remote Control session "Project dependency research") went offline before its
four researchers saved anything, so this is the re-run of the same four-track
brief. It does NOT repeat
[`external-repo-sourcing-2026-09-12.md`](external-repo-sourcing-2026-09-12.md),
[`tooling-research-2026-09-12.md`](tooling-research-2026-09-12.md),
[`free-digitizer-survey-2026-11-04.md`](free-digitizer-survey-2026-11-04.md) or
[`external-repo-sourcing-2026-11-06.md`](external-repo-sourcing-2026-11-06.md);
it reports what changed since them.

Tracks: (1) the earlier watch / reject / on-trigger lists, re-checked against
today's defects and the installer; (2) new embroidery projects since September;
(3) image models that run on CPU and allow commercial use; (4) engineering tools
— test-suite speed first, then geometry libraries, then signing and update
facts.

Method: desk research only. Nothing was installed, run, or downloaded except
the DIS5K terms PDF. **[V]** = read from the primary source (LICENSE file,
package metadata, vendor page, repo file) on 2026-11-20. **[V2]** = also
re-checked by the session that wrote this doc. **[U]** = not verified.

## 1. The verdict

**No code to adopt.** Same shape as the last three sweeps: the engine's gaps are
discrimination problems and no library ships a discriminator. But this sweep
found two **real problems** in what we already ship, and two benchmark rows
worth running.

| # | What | Kind | Whose call |
|---|---|---|---|
| A | The background-removal model we ship may carry non-commercial training-data terms | Licence risk | Kent (possibly a lawyer) |
| B | The frozen Windows app does not bundle rembg, but background removal defaults ON and DOCTRINE makes rembg a deploy requirement | Product gap + a wrong doc line | Kent |
| C | filum has shipped releases — its 11-06 benchmark trigger fired | Benchmark row | Kent (queued 11-06, §8 item 2) |
| D | ZigZag: new, Apache-2.0 lettering engine with real traction | Benchmark row + readable reference | Kent |

Everything else is a refreshed watch row or a well-evidenced negative (§3–§6).

## 2. The two real problems

### A. `isnet-general-use` and the DIS5K terms

- We ship `photo_prep_background_removal_model = "isnet-general-use"`
  (`digitizer/digitizer_core/config.py:989`) through rembg 2.0.77
  (`digitizer/rembg_isolated/requirements.txt:10`). [V2]
- The DIS5K Terms of Use PDF (linked from the
  [DIS README](https://github.com/xuebinqin/DIS)), §2 "Intended use", limits
  the dataset to non-commercial research or education, and says commercial use
  is "prohibited even after copying, editing, processing" without the authors'
  permission. [V2 — text extracted from the PDF]
- The DIS README gives Apache-2.0 for "code and evaluation metric" only. It
  states **no licence for the weights**, and does not say what
  `isnet-general-use` was trained on ("this is NOT DIS V2.0"). The academic
  model "was trained with DIS V1.0". [V2]
- **BiRefNet is not the clean way out the 09-12 and 11-06 docs assumed.** Its
  code is MIT [V], but its weight repos still have no LICENSE file (only a card
  tag), and its model-zoo rows list DIS5K-TR, P3M-10k and Distinctions-646 as
  training data [V]. BEN2's card says "trained on the DIS5k and our 22K
  proprietary segmentation dataset" [V].
- Fallback if the terms are ruled to bind: `u2netp` (Apache, DUTS-TR, 4.7 MB;
  DUTS terms not found [U]), visibly weaker than isnet.
- Whether dataset terms bind weights trained on the dataset is unsettled law.
  This is a question for Kent, possibly a lawyer — not a tooling decision, and
  not legal advice. It does not need answering before launch is near (Kent
  11-12), but it should be on the launch list.

**rembg upgrade trap (not biting yet).** From v2.0.80 rembg's default model is
`bria-rmbg` (non-commercial) and its model cache moved to
`~/.rembg/models/<model>/`; later releases added cloud sessions. We pin 2.0.77
and `digitizer_core/rembg_worker.py:47` passes the model name explicitly, so
nothing breaks today. **Never bump rembg without re-checking both.** [V]

### B. The installed app has no subject cutout

- `photo_prep_background_removal: bool = True`
  (`digitizer/digitizer_core/config.py:983`). [V2]
- DOCTRINE line 660: "The photo subject cutout ships ON, and rembg is a DEPLOY
  REQUIREMENT" (Kent 08-24, re-affirmed 11-13). [V2]
- `docs/packaging-freeze-spike-2026-11-10.md:68` says background removal and
  SAM2 are "Both … default OFF … the intended v1 shape". **That is wrong for
  background removal** (true for SAM2, post-v1 by the 08-11 ruling). [V2]
- `digitizer/packaging/build_freeze.py` bundles neither isolated venv. So the
  installed app runs the no-cutout lane on every photo, unlike the venv product
  the scorecard measures.
- Cost of fixing: isnet alone is ~170–178 MB against a 109 MB installer, plus
  the onnxruntime wheel (~16.7 MB on Windows, 1.32.0). Item A decides whether
  isnet is the model to bundle at all, so **A and B are one decision.**

**Kent's ruling, 2026-11-20: "Park both till launch."** The packaging doc's
wrong line is corrected in the same PR; A and B are on the launch list in
`.claude/memory/launch-not-near-rulings-2026-11-12.md`. Until launch, the
installed app's photo results differ from the venv's and the scorecard's.

## 3. Track 1 — earlier lists re-checked

| Item | Was | Now | Verdict |
|---|---|---|---|
| clipper2-ts | 11-06, on trigger (next offsetRing artefact) | Trigger fired: #1290 pinned 5 offsetRing failures; in-house `offsetBevel` (#1304, built OFF, not wired into `app/src`) passes 4 of 5. Upstream 2.0.1-19 (11-07), BSL-1.0 [V] | Keep watching — fallback if the bevel flip is refused |
| skia-pathops | 09-12, on trigger (outline-font import reopened) | Fired 11-06 (#1268) and answered in-house by NONZERO winding (`outline_fonts.py`) | Keep watching (re-trigger: a glyph the filter gets wrong) |
| filum | 11-06, bench when released | Fired — see §4 | Benchmark (item C) |
| RapidOCR | 11-06, watch (tagger misses = text location) | Partly fired, on seal ring text (logo batches 3, 4, 7, 9) rather than MFab IN/AND. **New trap:** Requires-Dist `opencv-python-headless`, which clashes with our pinned contrib cv2 ("never co-install them"). MODEL_LICENSES.md it cites returns 404 [V] | Keep watching; the opencv_zoo detector in §5 covers the same need without the clash |
| BiRefNet | 11-06, "flip the existing knob" | See item A — same data problem as isnet; cost up because rembg is not in the freeze | Keep watching |
| skan | 11-06, watch | Not fired; recent branch faults are Column-lane walk order, not the skeleton graph. Hard deps numba, pandas, matplotlib, openpyxl | Drop as a dependency |
| FLIP | 09-12, adopt pending ranking | Measured 11-08: kappa +0.042 [−0.09, +0.17], fails the blank oracle | Drop (settled) |
| embroidery-streamlines | 09-12, not evaluated | MPL-2.0 [V], dormant since 2024-11; Kent 11-05 "PARK ALL" literature lanes | Parked (ruling) |
| tesserocr (adopted 11-06) | pin `==2.12.0` | 2.13.0 (11-12) bundles Tesseract 5.5.4 | Do not bump casually — moves every OCR-derived number |

**Nothing moved** (settled or dormant): TSP/ordering tools (Kent 11-05 "SKIP.
Order is not the gap"), tracers (DOCTRINE: "Do not evaluate one again"), vpype,
Ink/Stitch (description-only), SAM-HQ 2, SAM 3 (gated), RMBG-2.0 (gated),
patolette (not on PyPI), bezier-js, Lilo, tatami.ninja, Roidery (no release),
openstitch (lb2002, AGPL, benched), heatstitch, Nuizu, libembroidery.
habon-el/needler is gone (404). pyclipper and mapbox-earcut have no consumer.

## 4. Track 2 — new embroidery projects

**Still true:** every new engine picks run / satin / fill by width, and none
compares its output to a human professional's file. No paired pro-digitized
dataset appeared anywhere (GitHub, PyPI name index, npm, Hugging Face, GitLab,
arXiv).

| Project | Licence | What | Verdict |
|---|---|---|---|
| **[ZigZag](https://github.com/simpsoka/zigzag)** | Apache-2.0 [V2]; NOTICE lists ports from Respira (Apache), pyembroidery (MIT), VectorCraft — no Ink/Stitch [V2] | Rust editor + CLI + MCP server, created 10-30, v0.1.6 11-19, 987 stars [V2]. `zigzag convert logo.png -o logo.pes`; letters as satin columns via chordal axis, cut/mitred corners, lean. Ships a ~50-font "letter census" counting fans, off-square stitches, bare cloth, piles, extra cuts | **Benchmark row** in `bench_free_digitizers.py` via its CLI, and readable as a lettering reference for the Column lane (MARINE, counter fan, thin arm, wedge cap). Chordal axis itself is not new to us (09-12: `classify_ribbon` fills that slot) |
| **[filum](https://github.com/benkl/filum)** (update) | GPL-3.0 [V2] | Rust/WASM Ink/Stitch port. v0.1.0 11-04 and v0.2.0 11-05 — so the 11-06 doc's "when it ships a release" was already met when written. Now v0.2.2 (11-14) [V2]; Windows exe/msi ~140 MB, unsigned, GUI only (CLI needs a cargo build) | **Benchmark only, clean-room** — judge the DST, never read the code. ~2 h in the GUI, same route as openstitch |
| [OpenStitch (cristianonescu)](https://github.com/cristianonescu/OpenStitch) — not lb2002's AGPL one | MIT/Apache files [V]; API reports Apache-2.0 [V2] | Rust PE-DESIGN 11 work-alike. `compat/reference/` holds ~565 files made with a licensed PE-DESIGN 11.50, with a MANIFEST of exact settings + sha256; ~240 are text letters (e.g. Lato Bold, OFL, 20 mm) | **Benchmark only** — a commercial engine's satin letters on OFL outlines we can also set. Commercial-software output, not a human pro; **do not vendor into this public repo** (Brother EULA terms unchecked [U]) |
| StitchFoundry | MIT/Apache | Wilcom-style suite; its 39 fonts are auto-converted OFL with an unlicensed fonts repo, the rest the Ink/Stitch pool | Watch — no new font supply |
| tarz-text | MIT; 25 TTFs each with OFL | Arabic / Latin / Tifinagh shaping laid out as satin | Watch — only if Arabic becomes scope (MASTER_SCOPE #36) |
| fontstitch (npm) | MIT in package.json; repo 404 | TTF → satin by triangulation + skeleton | Watch — same idea as our outline-font lane |
| stitch_generator 1.0.0 (10-14) | MIT | Only change since the 08-01 teardown | Watch |
| embroidery-ksy, EmbroideryLab | MIT | Format stubs; small Rust tool | Skip |

Skipped for no LICENSE file (15 repos), source-available-no-redistribution
(needleworks), GPL/AGPL (4), or being a ZigZag copy (pichimail/hooop). Codeberg
search was rate-limited (429) twice [U].

## 5. Track 3 — image models (CPU, commercial use)

| Category | Finding | Verdict |
|---|---|---|
| Text location | **PP-OCRv3 en detector from opencv_zoo**: Apache-2.0 LICENSE in its folder [V], 2.4 MB fp32, zoo benchmark 18.6 ms at 640×480 on an i7-12700K. Runs in the `cv2` we already ship (`TextDetectionModel_DB` present; model not loaded [U]). Training-data terms not stated [U] | **Trial candidate** — aimed at ring text lost in logo batches 3/4/7/9 and the MFab IN/AND misses; ships like YuNet in `digitizer_core/model_data/` with a sha256 |
| Text location, others | PP-OCRv5 det (Paddle format only), docTR/OnnxTR (document-tuned, 9 deps) — watch. EAST (GPL), DB (no licence), CRAFT (no weights grant) — reject | — |
| Segmentation (post-v1) | Nothing new from Meta since SAM 3.1 (03-27). EfficientSAM-Ti ONNX in opencv_zoo (Apache, 20–48 MB, cv2.dnn, **no torch**) — but prompt-only, no automatic masks; DOCTRINE 1611 refutes SAM on logos. EdgeTAM/MobileSAM: DOCTRINE 1315 still applies (encoder ~8% of cost) | Watch EfficientSAM-Ti (would drop the ~1 GB torch download) |
| Raster → vector | vtracer: no release since 1.0.0-alpha.4. StarVector / OmniSVG: 1.4–8B params, Apache tag but no LICENSE file, output not tied to pixels | No change / reject |
| Upscaling (we use Lanczos) | FSRCNN is clean (Apache, T91/General100, 39 KB) but adds a prior, not information (DOCTRINE 10-10: the limit is the hard mask). EDSR / ESPCN / Swin2SR / Real-ESRGAN are DIV2K-trained, "academic research purpose only" [V]. APISR GPL. waifu2x MIT, still spike #3 in the 10-10 doc | Reject / no change |
| Background removal | See §2 A. RMBG-3.0 (new, 11-17): gated, non-commercial — reject. rembg's new ViTMatte models: research-dataset trained — reject | — |

## 6. Track 4 — engineering

### Test-suite speed

Slowest digitizer test files by recorded seconds (`tests/.shard_durations.json`,
last refreshed 2026-11-06 in #1292 [V2]): `test_preflight` 709.5,
`test_column_ends` 708.5, `test_duplicate_cone_layers` 538.0, `test_service`
422.1, `test_underfill_small_size` 344.2, `test_lowercase_angle` 342.6,
`test_stitch_width` 321.4, `test_bind_resnap_all_classes` 293.8,
`test_pro_silhouette` 292.6, `test_crop_inert` 273.4. Most are whole-pipeline
digitizes of the same real logos (`enthusiast_logo` in 44 files,
`becker_marine_logo` in 32). CI setup is negligible (install 0.2–0.3 min); the
"Digitizer tests" step per shard ranged 9.8–26.1 min over three green main runs.

Ranked:

1. **Refresh the shard map, then automate it.** 184 of 671 test files are
   unmeasured (27.4%) and each weighs the p75 default; the staleness warning
   fires on every shard. Balancing should save ~3–10 min of wall time per full
   digitizer run; risk nil (balance only). It went stale in two weeks and was
   flagged on 10-28 and 11-19, so a one-off refresh will rot: a scheduled
   workflow that regenerates it from the last green main's JUnit artifacts and
   opens a PR is the durable fix.
2. **Parallel e2e digitizer-service specs, one service per worker.** The serial
   step is 7.9–12.7 min of each `studio-e2e` shard, serial only because 28 specs
   share 127.0.0.1:8721. The Studio already honours the
   `embstudio:digitizerUrl` localStorage override (`app/src/lib/digitizer.js:38`
   [V2]), so a worker-scoped Playwright fixture on port 8721+workerIndex needs
   no app change. ~3–6 min; risk: four services plus four Chromiums on four
   cores, and `retries: 1` could hide flakes.
3. **Refresh `SPEC_SECONDS`** in `app/playwright.config.js` (13 of 79 specs on
   the 30 s default). ~1–3 min.
4. **shapely 2.2.0 (10-07)** claims scalar calls drop from 2–3 µs to 50–100 ns;
   the core makes ~2,400 scalar property reads. Saving unknown, and the bundled
   GEOS moves 3.13.1 → 3.14.1, which may break md5 goldens. Speed work is
   parked (Kent 11-16), so measure only if he un-parks it.

Rejected with evidence: a cross-run digitize cache (242 of the last 300
digitizer commits touch the engine/testdata/conftest; 82 test files monkeypatch
the engine), pytest-testmon / path selection (every flag PR edits
PipelineConfig), uv (nothing to win), xdist worksteal (may not honour
`xdist_group` [U]), pytest-split (duplicates `_ci_shard`), numba (refuses
numpy ≥ 2.5).

### Geometry libraries

Straight skeleton is still empty: shapely-polyskel is LGPL-3,
py_straight_skeleton's licence is contradictory, CGAL is GPL. pyclipr
(Clipper2, BSL-1.0) has no manylinux wheels. JS boolean libraries
(polygon-clipping, martinez, flatten-js) have no consumer — `src/` does no
boolean ops besides `offsetRing`. shapely 2.2's `minimum_width()` could replace
the `minimum_rotated_rectangle` width reads in `columns.py`, `fine_bar.py` and
`group_consistency.py`, behind the same golden-drift caveat as item 4.

### Signing and auto-update — facts only

Kent ruled 2026-11-12 not to raise signing or update decisions until launch is
near. These are facts for that day, read from vendor pages on 2026-11-20, with
no recommendation:

| Option | As stated |
|---|---|
| Azure Artifact Signing (renamed Trusted Signing) | Basic US$9.99/mo (5,000 signatures); no EV; SmartScreen reputation builds with downloads |
| SignPath Foundation | Free, but every component must be OSI-licensed — EMB-Bot is "Proprietary" in pyproject, so it does not qualify |
| Certum Open Source Code Signing | €69, card + reader, issued to a natural person |
| SSL.com OV / EV | $129/yr / $349/yr; EV no longer bypasses SmartScreen (since March 2024) |
| Velopack (MIT) | Builds its own installer — would replace Inno Setup |
| WinSparkle (MIT) | DLL + appcast; sits beside Inno Setup |
| Squirrel.Windows | Dormant since 2020 |

## 7. Doc gaps found

1. `docs/packaging-freeze-spike-2026-11-10.md:68` — background removal is
   default ON, not OFF (§2 B).
2. MASTER_SCOPE defect 55 says the offset cure is "not built"; it was built OFF
   in #1304.
3. The 11-06 sweep says filum had not released; v0.1.0 and v0.2.0 predate it.

Gap 1 is corrected in this PR. Gaps 2 and 3 are left for a scope-refresh lane.

## 8. Not checked

DUTS / SA-1B / PP-OCRv3-detector training-data terms; PP-OCRv3 speed on Kent's
laptop or on logo art; fresh per-test durations (JUnit zips not downloaded);
shapely 2.2 speed or golden drift; whether ZigZag's Windows zip includes the
CLI; filum's and ZigZag's output quality (nothing installed); Brother's EULA
terms for the PE-DESIGN reference files; Codeberg.
