# Low-resolution outline recovery: what is left to try — 2026-10-10

**Question.** `docs/tracer-head-to-head-2026-10-10.md` measured that on
1.8–3 px/mm sources no binary tracer beats stage 4. What, if anything,
recovers better outlines from such sources?

Not repeated here: vtracer 0.6 packaging and hole handling
(`docs/vtracer-evaluation-2026-08-17.md`); potrace/pypotrace GPL trap
(`docs/tooling-research-2026-09-12.md`, "three traps"). Research only —
**nothing below was run.** Every item is marked VERIFIED (primary source read
today) or UNVERIFIED.

## Answer

1. **0.18 px is not the physics floor for a clean, isolated edge** — the
   literature and our own `subpixel.py` both say 0.02–0.05 px. It *is* roughly
   the floor of a hard mask. The gap is real, but only where the edge model
   holds.
2. **The one untried thing that uses information we already have** is an
   iso-contour of the native-resolution coverage field (alpha, or soft label
   membership). No new dependency.
3. **One correction to the head-to-head doc:** vtracer 1.0.0-alpha *is* on
   PyPI, and its watershed mode claims to place boundaries on the anti-alias
   ramp.
4. Learned vectorizers and super-resolution add a *prior*, not information.
   None publishes evidence on flat-colour logos; all can redraw lettering.

## 1. The physics limit

| Source | Claim | Status |
|---|---|---|
| Lyvers, Purdue PhD abstract (moment-based operator; basis of the 1989 PAMI paper) — [link](https://docs.lib.purdue.edu/dissertations/AAI8911949) | "can locate correctly modeled edges to hundredths of a pixel"; not severely degraded by moderate noise | VERIFIED (abstract) |
| Akey, Purdue PhD abstract — [link](https://docs.lib.purdue.edu/dissertations/AAI8519972) | accuracy "limited only by the signal-to-noise ratio and not by the pixel size"; max error 0.06–0.10 px, average near 0.02 px | VERIFIED (abstract) |
| Trujillo-Pino et al. 2013, partial-area-effect edge model (the same coverage model `subpixel.py` uses) — [handle](https://accedacris.ulpgc.es/handle/10553/43474) | exact for ideal straight/circular edges | UNVERIFIED — PDF returned 403 / a login page; search summary only, no numbers read |
| Rockett, BMVC 1999 — [pdf](https://bmva-archive.org.uk/bmvc/1999/papers/39.pdf); Hagara 2013 — [pdf](https://www.measurement.sk/M2013/doc/proceedings/311_Hagara-1.pdf) | — | UNVERIFIED — could not extract text / certificate error |
| `digitizer/digitizer_core/subpixel.py` docstring | area-conservation estimate: −0.05 to +0.01 px on a straight edge; 0.037 px scatter on a disc | repo's own measurement, 2026-09-09 |

**My arithmetic, not a citation.** A hard mask puts the edge within ±0.5 px,
uniformly: median error 0.25 px. The head-to-head's mask outline (arm M)
converts to 0.19, 0.17, 0.17, 0.18, 0.17 source pixels at 1.8, 3, 5, 8,
12 px/mm — a constant. Error that is a fixed fraction of the *source* pixel
at every rung is quantisation behaviour, not a noise floor. A working
sub-pixel estimator would sit at 0.02–0.05 px: about 0.01–0.03 mm at
1.8 px/mm.

**Why we are not there.** Every claim above says "correctly modeled edges":
one straight edge, a flat plateau each side. `subpixel.py` states its own
limit — a stroke under about three pixels has no plateau and is rejected. At
1.8 px/mm that is anything under ~1.7 mm, i.e. most lettering. And detail
finer than two pixels (~1.1 mm) is aliased; no method recovers it without
inventing it. So: wide shapes have 3–5× headroom; thin strokes do not have a
quotable floor.

## 2. Vectorizers

| Tool | Reads the ramp? | Finding | Status |
|---|---|---|---|
| **potrace** | No | "Potrace can only handle 2-valued images" ([FAQ](https://potrace.sourceforge.net/faq.html)). Own greymap conversion is "very crude" ([man](https://potrace.sourceforge.net/potrace.1.html)). `alphamax` default 1 (0 = polygon, >4/3 = no corners), `opttolerance` 0.2; turdsize default not stated on the man page. GPL v2+. | VERIFIED |
| **mkbitmap** (potrace's preprocessor) | Yes, indirectly | Interpolate **then** threshold: "one can recover some of this detail by scaling the image to a higher resolution … before applying the thresholding step" ([doc](https://potrace.sourceforge.net/mkbitmap.html)). Default 2× cubic; at 1× "too much detail is lost"; 3×+ "tends to 'invent' detail" ([man](https://potrace.sourceforge.net/mkbitmap.1.html)). GPL — take the principle, not the code. | VERIFIED |
| **autotrace** | Not stated | Outline + centerline, colour reduction. Program GPL v2+, library LGPL v2.1+ ([README](https://github.com/autotrace/autotrace/blob/master/README.md)); last release 0.31.10, 2024-01-29. | VERIFIED |
| **Kopf-Lischinski** | No — wrong problem | Paper targets "pixel art images" ([project page](https://johanneskopf.de/publications/pixelart/)). libdepixelize: "non-blended non-anti-aliased pixel art", GPL/LGPL ([Launchpad](https://launchpad.net/libdepixelize)). `jerith/depixel` MIT but self-described "very much a work in progress", last push 2021 ([repo](https://github.com/jerith/depixel)). | VERIFIED |
| **vtracer 1.0.0a4** | Claimed, watershed mode only | On PyPI since 2026-07-24 (a1); a4 uploaded 2026-08-29, `cp38-abi3-win_amd64` wheel, `MIT OR Apache-2.0` ([PyPI JSON](https://pypi.org/pypi/vtracer/json)). Changelog: "antialiased pixels snap to the color-midpoint iso-line instead of meandering with the noise inside the ramp"; `bw` mode is still a threshold ([CHANGELOG](https://github.com/visioncortex/vtracer/blob/master/CHANGELOG.md)). npm `latest` = 1.0.0-alpha.4, Node target per 08-17 doc ([registry](https://registry.npmjs.org/@visioncortex/vtracer)). Alpha handling in watershed: not documented. | VERIFIED (claims); accuracy unmeasured |
| **Marching squares** | Yes | `skimage.measure.find_contours`: "Array values are linearly interpolated to provide better precision" ([docs](https://scikit-image.org/docs/stable/api/skimage.measure.html)). scikit-image 0.26.0 is already pinned in `digitizer/requirements.txt`. BSD-3. | VERIFIED |
| **OpenCV** | No | `findContours` is binary. | UNVERIFIED today (docs.opencv.org 403); from memory |
| **DiffVG / LIVE / Im2Vec** | Optimise a render loss | Apache-2.0 LICENSE files read ([diffvg](https://github.com/BachiLi/diffvg/blob/master/LICENSE), [LIVE](https://github.com/Picsart-AI-Research/LIVE-Layerwise-Image-Vectorization/blob/main/LICENSE), [Im2Vec](https://github.com/preddy5/Im2Vec/blob/master/LICENSE.md)). No releases; Im2Vec archived. No first-party low-res accuracy claims found. Runtime/GPU needs: UNVERIFIED. | licence VERIFIED |
| **StarVector** | Generates SVG code | Code Apache-2.0 ([LICENSE](https://github.com/joanrod/star-vector/blob/main/LICENSE)). Weights repo `starvector/starvector-1b-im2svg` carries an `apache-2.0` tag and **no LICENSE file** (16 files listed) — the BiRefNet pattern. Card: "ability to perfectly vectorize all types of images … may have limitations" ([card](https://huggingface.co/starvector/starvector-1b-im2svg)). | VERIFIED |
| **Vectorizer.ai** | Claimed | "place boundaries according to the anti-aliasing pixel values" ([site](https://vectorizer.ai/)). Hosted only; $0.05–$0.20 per API image, test mode free ([pricing](https://vectorizer.ai/pricing)). Customer art leaves the machine. | VERIFIED (claims) |
| **Adobe Image Trace** | Not stated | helpx direct fetch 403. Search excerpts of helpx: Noise 1–10 for low-res; leave anti-aliasing on edges for smoother curves. | UNVERIFIED |

## 3. Super-resolution before tracing

| Tool | Code | Weights | Last release | Windows / CPU | Logo evidence |
|---|---|---|---|---|---|
| Real-ESRGAN | BSD-3 ([LICENSE](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE)) | **No separate grant found** in README, FAQ, model zoo or anime doc; weights are release assets. Trained on DIV2K + Flickr2K + OST ([Training.md](https://github.com/xinntao/Real-ESRGAN/blob/master/docs/Training.md)) | v0.3.0, 2022-09-20; last push 2024-08 | ncnn-vulkan exe; CPU needs `--fp32` ([FAQ](https://github.com/xinntao/Real-ESRGAN/blob/master/docs/FAQ.md)) | None. Anime model "optimized for anime images" only |
| waifu2x (ncnn-vulkan) | MIT ([LICENSE](https://github.com/nihui/waifu2x-ncnn-vulkan/blob/master/LICENSE)) | In-repo `models/` (cunet, upconv_7 anime-art, photo) under the same MIT file | 2025-09-15 | Portable exe, `-g -1` = CPU ([README](https://github.com/nihui/waifu2x-ncnn-vulkan/blob/master/README.md)) | None. "Anime-Style Art" |
| waifu2x (nunif) | MIT | downloaded by script; own note: binary builds "possible that it will be GPL" via PyAV/ffmpeg ([README](https://github.com/nagadomi/nunif/blob/master/README.md)) | active (pushed 2026-10-10) | Windows package | None |
| SwinIR | Apache-2.0 ([LICENSE](https://github.com/JingyunLiang/SwinIR/blob/main/LICENSE)) | Release assets, no separate grant found; trained on DIV2K/Flickr2K and more ([README](https://github.com/JingyunLiang/SwinIR/blob/main/README.md)) | v0.0, 2021-08-26 | CPU speed UNVERIFIED | None |

No logo- or lettering-specific upscaler with a first-party accuracy claim was
found. **Hallucination:** none of these projects documents behaviour on
text. A GAN upscaler outputs a plausible edge, not the measured one; on a
2-px-wide letter stroke that can change the letter. Treat as a real risk, not
a nitpick — and one our edge-distance yardstick would only catch with truth.

## Licence table

| Tool | Code | Weights | Can ship | Source |
|---|---|---|---|---|
| scikit-image `find_contours` | BSD-3 | — | **yes** (already a dependency) | [LICENSE.txt](https://github.com/scikit-image/scikit-image/blob/main/LICENSE.txt) |
| vtracer 1.0.0a4 | MIT OR Apache-2.0 | — | **yes** (alpha quality) | [PyPI](https://pypi.org/pypi/vtracer/json) |
| waifu2x-ncnn-vulkan | MIT | MIT (in repo) | **yes**, on the LICENSE text; training-data provenance not checked | [LICENSE](https://github.com/nihui/waifu2x-ncnn-vulkan/blob/master/LICENSE) |
| jerith/depixel | MIT | — | yes, unfinished | [LICENSE](https://github.com/jerith/depixel/blob/master/LICENSE) |
| Real-ESRGAN | BSD-3 | no explicit grant | **no, not as it stands** | above |
| SwinIR | Apache-2.0 | no explicit grant | **no, not as it stands** | above |
| StarVector | Apache-2.0 | tag only, no LICENSE file | **no, not as it stands** | above |
| DiffVG / LIVE / Im2Vec | Apache-2.0 | — / — / none shipped | yes (code) | above |
| potrace, mkbitmap, pypotrace, potracer | GPL | — | **no** | [man](https://potrace.sourceforge.net/potrace.1.html) |
| autotrace | GPL v2+ / lib LGPL v2.1+ | — | no (program); library only with LGPL care | [README](https://github.com/autotrace/autotrace/blob/master/README.md) |
| libdepixelize | GPL/LGPL | — | no | [Launchpad](https://launchpad.net/libdepixelize) |
| Vectorizer.ai | hosted, proprietary | — | API only, per-image cost | [pricing](https://vectorizer.ai/pricing) |

Not legal advice.

## Ranked shortlist — at most three spikes

1. **Iso-contour on the native coverage field.** New arm in the head-to-head
   harness: `find_contours(alpha/255, 0.5)` on the *source-grid* alpha for the
   alpha-only cases (and on a per-layer soft membership for colour), plus the
   same after a 2× cubic enlarge (mkbitmap's recipe). Score with the existing
   `analyze.py`. *Why it might win:* it needs no plateau, so it works on the
   sub-3-px strokes `subpixel.py` rejects, and it never sees the NEAREST
   stairs stage 1 creates for Becker's class. Zero new dependencies. Half a
   day.
2. **vtracer 1.0.0a4, `clustering="watershed"`, on the source grid.** Arm B4,
   in the existing Python 3.12 venv. *Why:* it is the B3 configuration — the
   smooth one that was 2–3× off — with the one defect B3 had (thresholding
   the ramp) claimed fixed. Composite alpha onto white first; alpha handling
   is undocumented. Alpha software: measure, do not adopt.
3. **waifu2x 2× (cunet) before stage 1** — only if 1 and 2 leave lettering
   unsolved. *Why:* the only shippable option that adds a prior for thin
   strokes. Score against truth and read every letter by eye.

Optional yardstick, not a candidate: Vectorizer.ai in free test mode on the
synthetic rungs, to learn how far a commercial ramp-aware tracer gets. Kent's
call — it uploads artwork.

## Not worth trying

- **potrace / autotrace / pypotrace** — binary, and GPL. Same class as vtracer
  0.6, already measured.
- **Kopf-Lischinski** — built for hand-placed pixel art without anti-aliasing;
  our sources are the opposite.
- **vtracer `bw` mode, any version** — still a threshold.
- **DiffVG / LIVE / Im2Vec** — optimise against the same low-res pixels; no new
  information, heavy runtime, research code without releases.
- **StarVector** — generates SVG tokens, so geometry is not tied to pixels;
  weights have no licence file.
- **Real-ESRGAN, SwinIR** — no explicit weights grant, stale releases, no logo
  evidence. waifu2x covers the same experiment cleanly.
- **Enlarging more than 2× before thresholding** — potrace's own docs say it
  invents detail.
