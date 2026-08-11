# Smaller/faster SAM for the photo lane — what's actually available

**Date:** 2026-08-11 · **Scope:** answer Kent's two questions — (a) is there a
"mobile" SAM that keeps the photo-segmentation quality at lower cost, and (b) is
there a photos-only SAM that avoids paying for SAM2's video machinery — plus the
two adjacent angles (drop PyTorch via ONNX Runtime; what the existing config
knobs already buy). Decision doc for the `photo_segment_sam2` lane. **No product
code was changed.**

**Method.** Every license, checkpoint size, and capability claim below was
checked against the live primary source today (the repo's own `LICENSE` file via
`raw.githubusercontent.com`, the GitHub trees/contents API, HuggingFace model
cards, PyPI JSON, or an HTTP `HEAD` for byte-exact file sizes) — not from
training-data memory and not from blog summaries. Fetch date for every URL in
this document is **2026-08-11**.

**Verification legend**, same convention as `docs/inkstitch-research-2026-08-10.md`:
- **[V]** verified this session against the cited primary source.
- **[M]** measured this session on Kent's own machine (see §1 for the rig).
- **[U]** could not be verified from a primary source; flagged, not asserted.

**The single most important finding is in §1**, and it is not about any of the
candidate models: **the image encoder is only ~8% of SAM2's per-image cost in
automatic-mask-generation mode.** Every lightweight SAM variant in existence
optimizes the image encoder. That means essentially none of them can fix the
~45s penalty, and the two config fields that already exist (`points_per_side`,
`max_side_px`) can. Read §1 before §3.

---

## 0. Answers, in one paragraph each

**(a) Is there a smaller "mobile" SAM?** Several, and three of them are
license-clean and support unprompted whole-image mask generation: **EdgeTAM**
(Meta, Apache-2.0, 56.1 MB), **MobileSAM** (Apache-2.0, 40.7 MB), and
**EfficientViT-SAM-L0** (Apache-2.0, 139 MB). But **swapping the model will not
solve the speed problem** — they all shrink the image encoder, which §1 measures
at 8% of the cost. They shrink the checkpoint (156 MB → 40-56 MB), which is
worth ~100 MB against a ~1.03 GB footprint whose real bulk is PyTorch, not
weights. **Two candidates are disqualified on license: FastSAM (AGPL-3.0) and
EdgeSAM (NTU S-Lab 1.0, non-commercial).**

**(b) Is there a photos-only SAM?** SAM 1 is the image-only predecessor, and it
is **heavier, not lighter** — its smallest checkpoint (ViT-B) is 375.0 MB vs SAM
2.1 tiny's 156.0 MB [V]. And the premise is mostly wrong anyway: §4 measures the
SAM 2.1 tiny checkpoint tensor-by-tensor and finds the video machinery is
**30.1 MB of 156.0 MB (19.3%)** — it costs disk and RAM but **zero runtime**,
because the image path provably never executes it. Dropping to a hypothetical
image-only SAM 2.1 tiny would save ~30 MB of a ~1.03 GB footprint and 0 seconds.

**Cheapest real wins**, in order: lower `points_per_side` from 16 to 12 (**-41%
SAM2 time, measured**) or 8 (**-69%**); lower `max_side_px` from 1024 to 512
(**-21%**); drop `opencv-python-headless` from the isolated venv (**-113 MB** for
~0.8s of function). Then, if a bigger project is warranted, ONNX Runtime instead
of PyTorch (**~-600 MB**).

---

## 1. [M] The measurement that reframes the whole question

**Rig.** AMD Ryzen 7 4700U (8 cores / 8 logical, 2.0 GHz base — a 15W mobile
part), Windows 11 Pro 26100, Python 3.14.6, `torch 2.13.0+cpu`,
`torch.get_num_threads() == 8`, no GPU. Model `sam2.1_hiera_tiny.pt` from
`~/.cache/sam2/`. `SAM2AutomaticMaskGenerator` with the worker's own settings
(`points_per_batch=64`, `output_mode="binary_mask"`, `multimask_output=True`,
`crop_n_layers=0` by default). Test image: scikit-image's `astronaut.png` (a
real photograph), resampled to the stated size. Both runs are read-only scripts
against the existing isolated venv.

### Run A — how cost scales with the two config knobs

| configuration | wall time | masks returned |
|---|---|---|
| `build_sam2` (model construct + load) | 0.57s | — |
| **image encoder only** (`set_image`) @1024px | **4.22s** | — |
| image encoder only @512px | 3.62s | — |
| image encoder only @256px | 3.52s | — |
| AMG `points_per_side=16` @1024px (**today's default**) | **53.96s** | 16 |
| AMG `points_per_side=12` @1024px | 32.10s | 16 |
| AMG `points_per_side=8` @1024px | 16.91s | 11 |
| AMG `points_per_side=4` @1024px | 8.70s | 5 |
| AMG `points_per_side=16` @512px | 42.55s | 16 |
| AMG `points_per_side=16` @256px | 37.63s | 13 |

### Run B — where the time actually goes

| configuration | wall time | masks |
|---|---|---|
| image encoder only (`set_image`) @1024px | 3.21s | — |
| **decoder only**, 256 prompts in batches of 64 | **37.92s** (148.1 ms/prompt) | — |
| AMG `points_per_side=16`, `min_mask_region_area=0` | 40.09s | 16 |
| AMG `points_per_side=16`, `min_mask_region_area=100` | 40.93s | 16 |

**Run-to-run variance is real and must be stated:** the same configuration
measured 53.96s in Run A and 40.93s in Run B — a 27% spread, entirely plausible
on a 15W mobile CPU that thermally throttles under a multi-minute all-core load.
**Ratios within a single run are stable and internally consistent; absolute
seconds are not.** Every conclusion below rests on within-run ratios.

### What this proves

1. **The image encoder is ~8% of the cost.** 4.22s of 53.96s (Run A), 3.21s of
   40.93s (Run B). The remaining 92% is the prompt loop.
2. **The prompt loop is the whole story, and it is linear in the number of
   points.** Least-squares over Run A's four `points_per_side` values
   (`N = points_per_side²`; 256, 144, 64, 16) gives
   `T ≈ 5.2s + 0.189s × N_points`, with a worst-case residual of 5.6% (at
   `points_per_side=4`) and under 2.5% at the other three. Run B independently measures the
   decoder path at 148.1 ms/prompt and confirms
   `AMG total ≈ encoder + decoder-loop` (3.21 + 37.92 = 41.1 vs 40.09 measured).
3. **`points_per_side` is quadratic leverage.** 16 → 12 is 41% off; 16 → 8 is
   69% off; 16 → 4 is 84% off.
4. **`max_side_px` gives a smaller, real win.** 1024 → 512 costs 21% less with
   the same 16 masks returned. It does **not** touch the encoder (see §1.1) — it
   reduces the per-prompt mask upscale, since `_predict` returns masks already
   resized to the original resolution (verified: output tensor shape
   `(64, 3, 1024, 1024)`). Halving the side quarters that pixel work.
   1024 → 256 buys only another 5 percentage points and starts losing masks
   (13 vs 16) — diminishing, then negative.
5. **The cv2 small-region cleanup is nearly free in time.** `min_mask_region_area`
   0 vs 100 is 40.09s vs 40.93s — under 1s, ~2%. That matters for §3.6.
6. **Every subprocess pays ~4.8s of fixed import cost.** Measured warm, twice:
   `import torch` 2.32-2.50s, `import sam2` 2.36s, total 4.68-4.86s. This is
   paid once per image because the worker is a fresh subprocess, and **no config
   knob or model swap reduces it** — only leaving PyTorch behind does (§3).

### 1.1 [V] Why `max_side_px` cannot speed up the encoder

`sam2/utils/transforms.py`, `SAM2Transforms.__init__`, verified in the installed
package:

```python
self.transforms = torch.jit.script(
    nn.Sequential(
        Resize((self.resolution, self.resolution)),
        Normalize(self.mean, self.std),
    )
)
```

`resolution` is `self.model.image_size`, which `sam2.1_hiera_t.yaml` sets to
`1024`. **The encoder always sees a 1024×1024 square, whatever you feed it.**
Confirmed empirically: 4.22s / 3.62s / 3.52s for 1024 / 512 / 256 px inputs —
the small residual difference is the `ToTensor` + resize of the source array,
not the network. Anyone reasoning "shrink the input, shrink the encoder cost"
about this pipeline is wrong.

### 1.2 The consequence for every candidate in §3

MobileSAM, EdgeSAM, EfficientSAM, EfficientViT-SAM, SlimSAM, NanoSAM and EdgeTAM
are all, without exception, **image-encoder** optimizations. That is the right
target for their intended use case — interactive click-to-segment, where you
encode once and then decode many prompts *in real time as the user clicks*, so
the encoder is the latency the user feels. It is the wrong target for automatic
mask generation, where the decoder runs `points_per_side²` times per image with
no human in the loop.

This is not an inference — it is checkable in their source. EfficientViT-SAM's
`efficientvit/models/efficientvit/sam.py` imports SAM 1's decoder wholesale [V]:

```python
from segment_anything import SamAutomaticMaskGenerator
from segment_anything.modeling import MaskDecoder, PromptEncoder, TwoWayTransformer
```

`class EfficientViTSamAutomaticMaskGenerator(SamAutomaticMaskGenerator)` at line
504 [V]. MobileSAM and SlimSAM likewise keep SAM 1's `MaskDecoder` unchanged and
replace only the encoder. SAM 1's mask decoder is ~4.06M parameters; SAM 2.1
tiny's is 4,215,109 [M, §4]. **Per-prompt cost is therefore roughly a wash
across the entire field.** A model swap buys you the 8%, not the 92%.

---

## 2. License triage — the gate, before anything else

| candidate | code license | weights license | commercial-safe? |
|---|---|---|---|
| **SAM 2.1** (incumbent) | Apache-2.0 [V] | Apache-2.0 [V] | ✅ yes |
| **EdgeTAM** (Meta) | Apache-2.0 [V] | Apache-2.0 [V] | ✅ yes |
| **MobileSAM** (v1 only) | Apache-2.0 [V] | Apache-2.0 [V] | ✅ yes — **but see the v2 landmine** |
| **EfficientSAM** | Apache-2.0 [V] | Apache-2.0 (weights in-tree) [V] | ✅ yes |
| **EfficientViT-SAM** | Apache-2.0 [V] | Apache-2.0 [V] | ✅ yes, one residual question |
| **SlimSAM** | Apache-2.0 [V] | Apache-2.0 [V] | ✅ yes |
| **SAM 1** | Apache-2.0 [V] | Apache-2.0 [V] | ✅ yes |
| **NanoSAM** | Apache-2.0 [V] | (no separate terms found) | ✅ yes |
| **FastSAM** | **AGPL-3.0** [V] | AGPL-3.0 (Ultralytics) [V] | ❌ **DISQUALIFIED** |
| **EdgeSAM** | **NTU S-Lab 1.0, non-commercial** [V] | same (no split) [V] | ❌ **DISQUALIFIED** |
| **SAM 3 / SAM 3.1** | custom "SAM License", gated download [V] | same | ⚠️ permits commercial use, but not OSI, unilaterally amendable, and gated |

### 2.1 ❌ FastSAM — AGPL-3.0. Hard no.

The brief flagged this one specifically, and the flag was right. Fetched
`https://raw.githubusercontent.com/CASIA-IVA-Lab/FastSAM/main/LICENSE` twice,
independently, and it opens:

```
                    GNU AFFERO GENERAL PUBLIC LICENSE
                       Version 3, 19 November 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
```

GitHub's own detection agrees (`api.github.com/repos/CASIA-IVA-Lab/FastSAM`
reports `spdx_id: "AGPL-3.0"`).

**The README contradicts its own LICENSE file, and the README is the one that's
wrong.** It says "The model is licensed under the [Apache 2.0 license](LICENSE)"
— and that markdown link points at the AGPL-3.0 file quoted above. There is no
Apache-2.0 text anywhere in the repo. **A broken cross-reference is not a
license grant.**

It gets worse, not better, on inspection:
- **`ultralytics` is AGPL-3.0 too** [V] —
  `raw.githubusercontent.com/ultralytics/ultralytics/main/LICENSE` is the AGPL-3.0
  text, and the PyPI metadata classifier reads "OSI Approved :: GNU Affero
  General Public License v3 or later (AGPLv3+)".
- **Ultralytics' own license page names EMB-Bot's exact situation as requiring a
  paid Enterprise license** [V] — the trigger list at `ultralytics.com/license`
  includes "Any commercial product or service", "Proprietary / closed-source
  software", and "Internal business tools or private company applications", and
  AGPL otherwise requires "publicly releasing the complete corresponding source
  code for the entire derivative work, including the larger application".
- **Ultralytics claims AGPL covers the weights, not just the code** — their terms
  cover "Ultralytics YOLO code, models, architectures, training pipelines, or
  trained/fine-tuned models". FastSAM's weights are YOLOv8-derived and are
  distributed from `ultralytics/assets`.
- **You cannot avoid it by not pip-installing `ultralytics`.** FastSAM's
  `requirements.txt` comments the dependency out — because the repo **vendors the
  whole `ultralytics/` tree in-tree**, and `fastsam/model.py` imports from it
  (`from ultralytics.yolo.engine.model import YOLO`) [V]. Shipping vendored AGPL
  code is strictly worse than depending on it.

Same posture as `docs/inkstitch-research-2026-08-10.md` §0 takes on GPL-3.0:
concepts are fine, code and weights are not. **Do not use FastSAM. Do not use
`ultralytics`.**

### 2.2 ❌ EdgeSAM — NTU S-Lab License 1.0. Non-commercial. Hard no.

`https://raw.githubusercontent.com/chongzhou96/EdgeSAM/master/LICENSE`, fetched
directly, verbatim:

```
S-Lab License 1.0

Copyright 2022 S-Lab

Redistribution and use for non-commercial purpose in source and
binary forms, with or without modification, are permitted provided
that the following conditions are met:
```

and its closing clause: "In the event that redistribution and/or use for
commercial purpose in source or binary forms, with or without modification is
required, please contact the contributor(s) of the work."

GitHub reports `spdx_id: NOASSERTION`, `name: "Other"` — it is not an OSI
license. There is no code/weights split; the whole project is covered, and its
`edge_sam/automatic_mask_generator.py` is Meta's Apache-2.0 code **re-covered by
the restrictive license**. This is the same category as the `bria-rmbg`
rejection: an absolute no, not a risk to weigh. (Technically it would also have
failed on capability — see §3.9.)

### 2.3 ⚠️ MobileSAM's AGPL landmine — real, and avoidable

MobileSAM's root license is genuine Apache-2.0 [V] (the `LICENSE` file is
byte-identical to canonical Apache 2.0, 11,357 bytes, with no non-commercial or
weights carve-out anywhere in the text), and `app/README.md` states it of the
model specifically, fetched verbatim: **"The model is licensed under the
[Apache 2.0 license](LICENSE)."** The single checkpoint is committed in-tree at
`weights/mobile_sam.pt`, so the root license covers it.

**But the same repository contains a `MobileSAMv2/` subdirectory that vendors
Ultralytics YOLO, with `# Ultralytics YOLO 🚀, AGPL-3.0 license` headers on every
file** [V]. AGPL-3.0 inside an Apache-2.0 repo. If MobileSAM is ever adopted:
vendor `mobile_sam/` only, never `MobileSAMv2/`, and make that a written rule in
the vendoring script — a `git clone` of the whole repo pulls AGPL code into the
tree.

### 2.4 ⚠️ EfficientViT-SAM — one unresolved provenance question

Repo license is Apache-2.0 [V], the HuggingFace weights repo
`mit-han-lab/efficientvit-sam` is tagged `apache-2.0` and its `LICENSE.txt` is
standard Apache 2.0 [V], and a full tree enumeration found exactly one license
file (no per-directory or weights-specific override) [V]. So on its face it is
clean.

The open question: the weights were trained on Meta's **SA-1B**, whose dataset
page lists intended use as "Research purposes only" [V]. **[U]** — the verbatim
SA-1B Dataset Research License text could not be retrieved (Meta's download page
returns 403). Two mitigating facts: Meta itself ships SAM/SAM2 weights trained on
the same data under Apache-2.0, and MIT Han Lab has unilaterally released the
derived weights under Apache-2.0. **This is a residual question for counsel, not
a license bar** — and it applies equally to MobileSAM, SlimSAM and EfficientSAM,
all of which are distilled from SAM. Note it once; do not treat it as
distinguishing between candidates.

### 2.5 ⚠️ SAM 3 / SAM 3.1 exist, and are a licensing regression

Meta shipped **SAM 3** on 2025-11-19 and **SAM 3.1** on 2026-03-27 [V]. Neither
is a candidate here, for four independent reasons — but Kent should know they
exist so nobody re-opens this later:

- **Custom "SAM License", not Apache-2.0** [V]. GitHub reports `spdx_id:
  NOASSERTION`; HuggingFace tags it `license: other`. It *does* permit commercial
  use — no non-commercial clause, no MAU threshold — but it is not OSI-approved,
  it requires passing the agreement through on redistribution, §8 lets Meta amend
  it unilaterally with immediate effect, and §1.b.iv prohibits use that would
  "reverse engineer, decompile or discover the underlying components" — which is
  worth legal review before anyone quantizes, prunes or distills those weights.
- **The HuggingFace repo is gated (`gated: "manual"`)** [V] — manual Meta
  approval per account. That is real friction for a build pipeline.
- **3.45 GB / 3.50 GB checkpoints, 0.9B params** [V] — ~22x SAM 2.1 tiny.
- **No automatic mask generation at all.** A full git-tree enumeration of
  `facebookresearch/sam3` for `automatic|amg|mask_gen` returns **zero matches**
  [V], where `sam2` and `EdgeTAM` both ship `automatic_mask_generator.py`. SAM 3
  is prompt-required by design (text or visual exemplar). **It cannot do what
  this pipeline needs.**

There is no SAM 2.2 [V]. `facebookresearch/sam2` has published no GitHub
releases at all; last push 2026-05-30, still Apache-2.0.

---

## 3. The candidates, one by one

Format per candidate, in the order the brief asked for: license → checkpoint
size → runtime deps → **automatic mask generation** → speed → quality.

### 3.0 SAM 2.1 Hiera-Tiny — the incumbent, for comparison

1. **License:** Apache-2.0, code *and* checkpoints [V]. Meta's README states
   "The SAM 2 model checkpoints, SAM 2 demo code (front-end and back-end), and
   SAM 2 training code are licensed under Apache 2.0." The installed package's
   own `LICENSE` (in `sam_2-1.0.dist-info/licenses/`) is standard Apache 2.0 [V].
2. **Checkpoint:** 156,008,466 bytes = **156.0 MB** [V, byte-exact `HEAD` against
   `dl.fbaipublicfiles.com`], 38,962,754 params, all fp32 [M]. Siblings: small
   184.4 MB, base_plus 323.6 MB, large 898.1 MB [V].
3. **Runtime deps:** PyTorch required (`torch>=2.5.1`, `torchvision>=0.20.1`,
   `hydra-core`, `iopath`, `numpy`, `pillow`, `tqdm`) [V, from the installed
   `METADATA`]. **No ONNX path officially — see §5.**
4. **Automatic mask generation:** yes, `SAM2AutomaticMaskGenerator` — this is what
   the pipeline uses today.
5. **Speed:** see §1. ~41-54s per image at today's settings on this box [M].
6. **Quality:** established good by Kent's own real-photo test. That is the bar
   every candidate below has to clear, and none of their published numbers
   measure against it directly.

### 3.1 EdgeTAM — the strongest model-swap candidate

`facebookresearch/EdgeTAM`, Meta's own on-device SAM 2 variant, CVPR 2025.

1. **License:** **Apache-2.0 for code AND checkpoints** [V]. `LICENSE` is
   canonical Apache 2.0 (11,357 bytes); README states verbatim: **"The EdgeTAM
   model checkpoints and code are licensed under Apache 2.0."** No gating, no
   custom terms. Cleanest license of anything Meta has shipped post-SAM-2.
2. **Checkpoint:** `checkpoints/edgetam.pt` = 56,116,523 bytes = **56.1 MB**
   [V, byte-exact `HEAD`]. **2.8x smaller than SAM 2.1 tiny.** CoreML exports
   (iOS only) are ~9.6 MB encoder / ~2 MB prompt encoder / ~8 MB decoder [V].
3. **Runtime deps:** PyTorch ≥2.3.1, torchvision ≥0.18.1, Python ≥3.10 [V]. It
   is a fork of the `sam2` package, so the dependency shape is identical to what
   the isolated venv already has. **No pure-ONNX path documented** — the export
   story is CoreML.
4. **Automatic mask generation: YES** [V]. Ships `sam2/automatic_mask_generator.py`
   and `notebooks/automatic_mask_generator_example.ipynb`; README states "EdgeTAM
   also supports automatic mask generation on images just like SAM." Because it
   keeps the `sam2` package layout, this is close to a drop-in for
   `sam2_worker.py` — a different checkpoint, config, and package, same API.
5. **Speed:** 16 FPS on iPhone 15 Pro Max (real on-device measurement, unusually
   honest for this field), 150.9 FPS video-object-segmentation on A100, "22x
   faster than SAM 2" [V]. **No x86 CPU numbers published** [U]. And per §1.2,
   its speedup is concentrated in the encoder and the *video* memory path — for
   image AMG expect to save a fraction of the 8%, not the 92%.
6. **Quality:** authors report SA-V val **72.3 J&F vs SAM 2.1's 76.8**, DAVIS 2017
   **87.7 vs 90.2** [V]. Both are **video** metrics — **[U] no image-mode
   segmentation quality comparison against SAM 2.1 was found**, which is exactly
   the number this decision needs.

**Verdict:** worth an A/B specifically because the swap is cheap (same package
shape, same API) and the checkpoint saving is real (-100 MB). Do not expect it to
fix the speed. Its image-mode quality vs SAM 2.1 tiny is unmeasured and would have
to be established on Kent's own photos.

### 3.2 MobileSAM

1. **License:** Apache-2.0, code and weights [V] — see §2.3 for the `MobileSAMv2/`
   AGPL caveat.
2. **Checkpoint:** `weights/mobile_sam.pt` = 40,728,226 bytes = **40.73 MB** [V],
   9.66M params (5M TinyViT encoder + 3.876M SAM-1 decoder). Single checkpoint,
   no variants.
3. **Runtime deps:** PyTorch ≥1.7, torchvision ≥0.8 [V]. `setup.py` declares
   `install_requires=[]`, which is Meta's stock file and misleading. An ONNX
   *export script* exists (`scripts/export_onnx_model.py`); **no pre-exported
   `.onnx` is shipped** [V]. Not on PyPI under any obvious name [V].
4. **Automatic mask generation: YES, first-class** [V].
   `mobile_sam/automatic_mask_generator.py` + `scripts/amg.py` CLI, exported from
   `mobile_sam/__init__.py`, documented in the README as
   `from mobile_sam import SamAutomaticMaskGenerator`. The project's explicit
   design goal is drop-in compatibility: "MobileSAM keeps exactly the same
   pipeline as the original SAM."
5. **Speed:** ~12 ms total on "a single GPU" (model unnamed) [V]. **The only
   published CPU datapoint in this entire field:** "On our own Mac i5 CPU, it
   takes around 3s" — informal, single prompt, encoder-dominated [V].
6. **Quality:** the weakest of the viable candidates. Third-party measurement
   (EdgeSAM paper Table 4): **COCO AP 39.4 vs SAM's 46.1** [V]. SlimSAM's Table 1
   puts its prompted mIoU at **62.73%** vs SAM-B's 73.37% [V]. Against SAM 2.1 —
   which is a generation newer than the SAM-1 it was distilled from — the gap
   would be wider still.
7. **Maintenance:** the most active of the lightweight variants; last commit
   2026-05-05 [V].

**Verdict:** the easiest drop-in and the smallest checkpoint, but it trades away
the quality Kent already validated, to buy 8% of the runtime. Poor exchange rate.

### 3.3 EfficientViT-SAM (MIT Han Lab)

1. **License:** Apache-2.0, code and weights [V] — see §2.4 for the SA-1B
   provenance note.
2. **Checkpoints:** L0 **139 MB**, L1 191 MB, L2 246 MB, XL0 468 MB, XL1 814 MB
   [V, HF file listing]. Params 34.8M / 47.7M / 61.3M / 117.0M / 203.3M.
3. **Runtime deps:** PyTorch for the reference path — **but it has the best ONNX
   story of any candidate**: `applications/efficientvit_sam/deployment/onnx/`
   contains `export_encoder.py` **and** `export_decoder.py` [V, contents API], and
   the decoder export declares dynamic axes
   `{"point_coords": {0: "batch_size", 1: "num_points"}, ...}` [V] — i.e. it can
   take a whole batch of grid prompts in one call, which is exactly what an
   AMG driver needs. **Caveat [V]:** the folder contains only
   `__init__.py, export_decoder.py, export_encoder.py` — **there is no shipped
   unprompted ONNX runner**; the README's `run_efficientvit_sam_onnx.py` 404s at
   that path. The export is there; the everything-mode driver would be new code.
   ⚠️ **Do not `pip install efficientsam`** — that PyPI name resolves to
   EfficientViT-SAM, not `yformer/EfficientSAM`, with no author or license
   metadata [V].
4. **Automatic mask generation: YES** [V] —
   `class EfficientViTSamAutomaticMaskGenerator(SamAutomaticMaskGenerator)`,
   `efficientvit/models/efficientvit/sam.py:504`, in the PyTorch path.
5. **Speed:** vendor numbers are GPU-only (Jetson Orin 8.2 ms, A100 762 img/s for
   L0) [V]. **But there is one genuinely useful independent CPU benchmark** — the
   peer-reviewed survey *On Efficient Variants of Segment Anything Model* (arXiv
   2410.04960, v6 revised 2026-06-04) [V], Table 4, hardware stated verbatim as
   "a 14 vCPU Intel(R) Xeon(R) Gold 6330 Processor @ 2.00GHz", **SegAny latency
   for a single box prompt**:

   | model | CPU | RTX 3090 |
   |---|---|---|
   | SAM-H | 9470 ms | 461 ms |
   | SAM-B | 3294 ms | 116 ms |
   | SAM2-B+ | 1221 ms | 85 ms |
   | **EfficientViT-SAM-L0** | **194 ms** | 16 ms |
   | EfficientViT-SAM-XL1 | 1334 ms | 52 ms |

   Read that carefully: "SegAny, one box prompt" is **encoder-dominated**. It
   says L0's encoder is dramatically faster than SAM's. It does **not** say its
   `points_per_side²` decoder loop is faster — and per §1.2 its decoder *is* SAM
   1's, unchanged.
6. **Quality:** the best in the field, and the only one that matches or beats full
   SAM. Survey Table 6, COCO box-prompt mIoU: SAM-H 77.4, **L0 78.5**, XL1 79.9
   [V]. Instance-seg AP: SAM-H 46.5, L0 45.7, XL1 47.8 [V].
7. **Maintenance:** last push 2025-09-05, 3,346 stars, not archived [V].

**Verdict:** the strongest candidate *if and only if* the ONNX migration in §5 is
happening anyway — it is the only model with a first-class encoder+decoder ONNX
export and independently-measured best-in-class CPU encoder latency. As a
PyTorch-path swap it is worse than the incumbent (139 MB vs 156 MB checkpoint,
same torch tail, same decoder cost).

### 3.4 EfficientSAM (Meta Research / yformer)

1. **License:** Apache-2.0 [V] — `LICENSE` is byte-identical to MobileSAM's
   canonical Apache 2.0. Weights are **committed in-tree** under `weights/`, so
   the root license covers them. Note the README has no license section at all,
   so the in-tree argument is what you'd rely on [V].
2. **Checkpoints:** `efficient_sam_vitt.pt` **40.98 MB**;
   `efficient_sam_vits.pt.zip` 98.30 MB zipped; pre-exported ONNX
   `efficient_sam_vitt_encoder.onnx` **24.80 MB** + `_decoder.onnx` **16.57 MB**
   [V, byte sizes from the repo]. Params: Ti 10M, S 25M.
3. **Runtime deps:** **pre-exported ONNX shipped, and a working torch-free
   example** [V] — `EfficientSAM_onnx_example.py` runs encoder and decoder through
   `onnxruntime.InferenceSession` directly, encoding once and reusing the
   embedding across prompts. Also ships TorchScript CPU builds
   (`efficientsam_ti_cpu.jit` 41.2 MB).
4. **Automatic mask generation: NO packaged API — DIY, but demonstrated** [V]. A
   full tree enumeration finds **no `automatic_mask_generator.py` and no
   `amg.py`**. What exists is
   `notebooks/EfficientSAM_segment_everything_example.ipynb`, which hand-rolls a
   32×32 grid, feeds **all 1,024 points in one batched forward pass**, filters on
   IoU > 0.7 then stability > 0.9, then NMS — and does it on `model.cpu()`. It
   imports `segment_anything.utils.amg` from Meta's SAM 1 (Apache-2.0, so no
   license problem) for the RLE/NMS helpers, because the repo ships none [V].
   **You would write and own the wrapper.**
5. **Speed:** "benchmarking the speed (throughput) on a single NVIDIA A100" —
   EfficientSAM-Ti 54 img/s, -S 47 img/s, SAM 2 img/s [V]. **GPU only; no CPU
   numbers despite shipping CPU JIT builds** [U].
6. **Quality:** second only to EfficientViT-SAM. Zero-shot instance seg AP:
   **-S COCO 44.4 / LVIS 42.3** vs SAM 46.5/44.7, MobileSAM 38.7/34.4 [V]. **The
   relevant column is 1-click mIoU**, since grid AMG is point-prompted, and that
   is where the gap widens: SAM 55.6, -S 50.0, **-Ti 45.5** on COCO [V].
7. **Maintenance:** dormant. Last commit 2024-12-24, and that commit redirects
   users to the successor project `yformer/EfficientTAM` [V].

**Verdict:** good license, good ONNX artifacts, real quality — but no AMG API, a
dormant repo, and the batched-all-points design is the one thing here genuinely
worth stealing as a *technique* (see §7).

### 3.5 SlimSAM

1. **License:** Apache-2.0, code and weights [V] — weights independently
   confirmed `license: apache-2.0` on the HF cards `Zigeng/SlimSAM-uniform-50`
   and `-77`. (It vendors `torch_pruning/`; check that separately before
   shipping.)
2. **Checkpoints:** uniform-50 **112 MB** (26M params), uniform-77 **38.9 MB**
   (9.1M params) [V, HF file listings, fp32 safetensors].
3. **Runtime deps:** PyTorch. No `requirements.txt`, no ONNX export script, no
   pre-exported `.onnx` [V]. There is an HF `transformers` integration
   (`SamModel.from_pretrained("Zigeng/SlimSAM-uniform-50")`), which would give an
   Optimum export route, but **official ONNX is [U]**.
4. **Automatic mask generation: YES** [V] —
   `segment_anything/automatic_mask_generator.py` present, and `inference.py`
   demonstrates `SamAutomaticMaskGenerator(model=SlimSAM_model,
   points_per_side=32, ...)` alongside point and box prompting.
5. **Speed: [U] — the weakest evidence of any candidate.** Neither README nor
   paper publishes wall-clock latency on named hardware; the README's tables are
   embedded images, and the paper reports MACs only (SlimSAM-50 98G, -77 23G, vs
   SAM-B 372G, SAM-H 2736G).
6. **Quality:** best quality-per-MAC in its own comparison table (arXiv
   2312.05284v3 Table 1, mIoU): SAM-H 78.30, SAM-B 73.37, **SlimSAM-50 72.33**,
   SlimSAM-77 67.40, EfficientSAM-s 71.19, EdgeSAM 65.96, MobileSAM 62.73,
   FastSAM-x 35.41 [V]. Self-reported, and note it is measuring against SAM 1.
7. **Maintenance:** last commit 2025-09-27, 361 stars [V].

**Verdict:** legitimate and well-licensed, but it is a *pruned SAM 1* — a
generation behind the incumbent — with no ONNX path and no published latency. No
axis on which it beats staying put.

### 3.6 SAM 1 — the direct answer to Kent's question (b)

1. **License:** Apache-2.0, code and weights [V]. README line 160 verbatim: "The
   model is licensed under the [Apache 2.0 license](LICENSE)." (The *dataset* is
   separately restricted — the SA-1B Dataset Research License binds SA-1B, not the
   checkpoints.)
2. **Checkpoints — byte-exact `Content-Length` from `dl.fbaipublicfiles.com`,
   fetched today** [V]:

   | file | bytes | MB |
   |---|---|---|
   | `sam_vit_b_01ec64.pth` | 375,042,383 | **375.0** |
   | `sam_vit_l_0b3195.pth` | 1,249,524,607 | 1,249.5 |
   | `sam_vit_h_4b8939.pth` | 2,564,550,879 | 2,564.6 |

   **The smallest SAM 1 checkpoint is 2.4x larger than SAM 2.1 tiny's 156.0 MB.**
   That is the headline answer: the image-only predecessor is heavier, not
   lighter.
3. **Runtime deps:** PyTorch ≥1.7, torchvision ≥0.8 [V]. **The ONNX export is
   decoder-only, and this is a trap worth naming.** `scripts/export_onnx_model.py`
   describes itself verbatim as "Export the SAM prompt encoder and mask decoder
   to an ONNX model", and the exported `SamOnnxModel` takes *pre-computed*
   `image_embeddings` as an input [V]. **The ViT image encoder — the expensive
   part — still runs in PyTorch.** Anyone who reads "SAM has an official ONNX
   export" and concludes torch can be dropped has been misled by the headline.
4. **Automatic mask generation: YES** — `segment_anything/automatic_mask_generator.py`,
   `SamAutomaticMaskGenerator`, `points_per_side=32` default [V]. This is the
   original that SAM2's is "adapted from" (stated in SAM2's own file header, [V]
   in the installed source).
5. **Speed:** 3294 ms CPU for SAM-B, single box prompt (survey Table 4, §3.3) —
   ~2.7x slower than SAM2-B+ [V].
6. **Quality:** the reference point everything else is measured against, but SAM
   2.1 improved on it. No reason to move backwards.
7. **Maintenance:** last push 2024-09-18 — ~23 months dormant, README redirects to
   SAM 2 [V]. Effectively frozen.

### 3.7 NanoSAM — not applicable

1. **License:** Apache-2.0 [V] (the file is `LICENSE.md`, not `LICENSE`, which is
   why a naive fetch 404s). Clean, no NVIDIA-specific restrictions.
2. **Checkpoints: [U]** — the README links `resnet18_image_encoder.onnx` and
   `mobile_sam_mask_decoder.onnx` on Google Drive with no stated sizes, and there
   are no GitHub releases.
3. **Runtime deps: TensorRT and a CUDA GPU. This is the blocker.**
   `nanosam/utils/predictor.py` hard-imports `from torch2trt import TRTModule` and
   `import tensorrt as trt`, and its constructor takes **engine files only**,
   loaded via `runtime.deserialize_cuda_engine` [V]. The `.onnx` files are inputs
   to `trtexec`, not runnable artifacts. **There is no ONNX Runtime path and no
   CPU path in the predictor.**
4. **Automatic mask generation: NO** on the fast path [V]. There *is* an
   `automatic_mask_generator.py` under `nanosam/mobile_sam/` — but that belongs to
   the vendored PyTorch MobileSAM used as the distillation *teacher*, not to the
   TensorRT predictor, whose decoder engine is bound to prompt inputs.
5. **Speed:** Jetson-only (Orin Nano 27 ms full pipeline) [V].
6. **Quality:** COCO box-prompted mIoU 0.706 vs MobileSAM's 0.728 [V].
7. **Maintenance:** last commit 2023-09-20 — ~3 years untouched [V].

**Verdict:** license-clean but structurally wrong for a CPU-only Windows box.
Rule it out.

### 3.8 ❌ FastSAM — see §2.1. AGPL-3.0.

For completeness on the non-license axes, since they are sometimes cited:
checkpoints FastSAM-s **22.75 MB** / FastSAM-x **138.21 MB** [V]; yes it does
everything-mode; 40 ms flat on an RTX 3090 regardless of prompt count [V, GPU
only]; COCO AP **.379 vs SAM's .465** [V], and its *prompted mask quality* is far
worse than the AP suggests — SlimSAM's independent table scores FastSAM-s at
30.72% mIoU and FastSAM-x at 35.41% against SAM-B's 73.37% [V]. **None of this
matters. The license disqualifies it.**

### 3.9 ❌ EdgeSAM — see §2.2. Non-commercial.

Worth recording that it would also have failed on capability, because it is the
clearest illustration of §1.2's point. Its `edge_sam/automatic_mask_generator.py`
exists and will run — but:
- **The paper explicitly disclaims it** [V], verbatim: "As EdgeSAM is built for
  inference-speed-sensitive devices, we do not advocate using everything mode of
  EdgeSAM in practice" — precisely because "in everything mode, points in a 32×32
  grid are fed to the decoder, which results in 1,024 times decoder inference."
  **That is the same arithmetic §1 measured.**
- **Its IoU token was never distilled**, so AMG's primary quality filter is
  broken. README verbatim: "Since EdgeSAM doesn't perform knowledge distillation
  on the IoU token of the original SAM, its IoU predictions might not be
  reliable" — and AMG's default `pred_iou_thresh=0.88` filters on exactly that
  signal [V].
- **Nothing wires it up**; the ONNX predictor exposes only single-prompt
  `predict()`, with no batched grid path [V].

---

## 4. [M] Angle B — does SAM2's video capability actually cost anything?

**Short answer: 30.1 MB of disk and RAM, and zero runtime.**

### 4.1 The checkpoint, tensor by tensor

Loaded `~/.cache/sam2/sam2.1_hiera_tiny.pt` with `torch.load(weights_only=True)`
and summed parameters by top-level module. 471 tensors, **all fp32**, 38,962,754
params total, 155.9 MB of tensor bytes in a 156.0 MB file — i.e. the file is
essentially all weights, no slack.

| module | params | share | fp32 MB | needed for images? |
|---|---|---|---|---|
| `image_encoder` | 27,219,136 | 69.9% | 108.88 | **yes** |
| `memory_attention` | 5,922,304 | 15.2% | 23.69 | **no — video only** |
| `sam_mask_decoder` | 4,215,109 | 10.8% | 16.86 | **yes** |
| `memory_encoder` | 1,384,608 | 3.6% | 5.54 | **no — video only** |
| `obj_ptr_proj` | 197,376 | 0.5% | 0.79 | **no** (see §4.2) |
| `obj_ptr_tpos_proj` | 16,448 | <0.1% | 0.07 | **no** |
| `sam_prompt_encoder` | 6,476 | <0.1% | 0.03 | **yes** |
| `maskmem_tpos_enc` + `no_mem_pos_enc` + `no_obj_ptr` + `no_obj_embed_spatial` | 1,024 | <0.1% | ~0.00 | **no** |
| `no_mem_embed` | 256 | <0.1% | ~0.00 | **yes** (see §4.2) |
| `mask_downsample` | 17 | <0.1% | ~0.00 | no |

Within the encoder: `image_encoder.trunk` (the Hiera backbone) is 26,849,472 and
`image_encoder.neck` (FpnNeck) is 369,664.

**Video-only total: 7,521,760 params = 30.09 MB = 19.3% of the checkpoint.** So a
hypothetical image-only SAM 2.1 tiny would be a ~126 MB checkpoint instead of
156 MB. Against the ~1.03 GB total footprint that is **2.9%** — real, but not the
lever anyone is looking for.

### 4.2 [V] The image path provably never executes the video machinery

`sam2/modeling/sam2_base.py`, in the installed package: `self.memory_attention` is
called at exactly one site (line 667, inside `_prepare_memory_conditioned_features`)
and `self.memory_encoder` at exactly one site (line 711, inside
`_encode_new_memory`). **Both of those are reached only from `track_step` (line
814) — the video path.**

`sam2/sam2_image_predictor.py`, the path `SAM2AutomaticMaskGenerator` actually
uses, calls in full:

- `self.model.forward_image` → `_prepare_backbone_features` (line 117-118)
- `vision_feats[-1] + self.model.no_mem_embed` (line 121) — a 256-parameter
  learned "there is no memory" token, the one piece of video scaffolding the
  image path *does* use
- `self.model.sam_prompt_encoder(...)` (line 406)
- `self.model.sam_mask_decoder(...)` (line 422)

It never calls `_forward_sam_heads`, which is where `obj_ptr_proj` is applied
(line 393 of `sam2_base.py`) — so even the object-pointer projection is dead
weight in image mode.

**Conclusion: SAM2's video capability costs 30.1 MB of checkpoint and the RAM to
hold it. It costs no time.** Kent's intuition that "a photos-only model would be
cheaper" is correct in principle and immaterial in magnitude. And per §3.6, the
actual photos-only model that exists — SAM 1 — is 2.4x *heavier* per checkpoint
and slower per prompt. **Question (b) resolves to: no, there is nothing to gain
here.**

### 4.3 [M] Where the footprint really is

Byte-exact walk of the isolated venv's `site-packages` (note: these are true MB;
`du -sm` reports MiB with per-file cluster slack, which is where Kent's "875 MB"
and "torch 534 MB" figures come from — both sets of numbers are right, they're
just different units and rounding):

| package | MB (10⁶ bytes) | MiB |
|---|---|---|
| **site-packages total** | **854.2** | 815 |
| `torch` | 520.8 | 497 |
| `cv2` (opencv-python-headless) | 117.4 | 112 |
| `sympy` | 72.6 | 69 |
| `numpy` + `numpy.libs` | 52.8 | 50 |
| `PIL` | 16.2 | 15 |
| `networkx` | 15.7 | 15 |
| `torchvision` | 15.0 | 14 |
| `pip` | 11.4 | 11 |
| `setuptools` | 8.9 | 8 |
| `mpmath` | 4.7 | 4 |
| `torchgen` | 3.4 | 3 |
| `fsspec` + `jinja2` + `filelock` | 3.3 | 3 |
| `hydra` + `omegaconf` + `antlr4` + `sam2` + `training` | 4.3 | 5 |

**PyTorch and its exclusive tail** (`torch`, `sympy`, `mpmath`, `networkx`,
`torchvision`, `fsspec`, `jinja2`, `filelock`, `torchgen`) = **~635.5 MB**, i.e.
74% of site-packages. Inside `torch` itself: `torch/lib/` is 352 MiB — of which
`torch_cpu.dll` alone is 291 MiB — plus `torch/include/` 64 MiB of C++ headers,
`_inductor` 24 MiB, `distributed` 14 MiB, `testing` 12 MiB, `_dynamo` 12 MiB.

**The checkpoint is 156 MB of a 1.03 GB problem. Torch is 635 MB of it.** Any
plan that shrinks the checkpoint and keeps torch is optimizing the wrong term.

---

## 5. Angle A — dropping PyTorch for ONNX Runtime

### 5.1 The size prize, with real numbers

| | wheel (Windows amd64) | installed |
|---|---|---|
| `torch` 2.13.0 (cp312) | 122.1 MB [V] | 520.8 MB + 114.7 MB tail [M] |
| `onnxruntime` 1.28.0 (cp314) | **14.1 MB** [V] | **45 MiB** [M, measured against an existing local install] |

`onnxruntime` 1.28.0's `requires_dist` is `flatbuffers`, `numpy>=1.21.6`,
`packaging`, `protobuf>=4.25.8` — with **`sympy` demoted to an optional
`symbolic` extra** and `coloredlogs`/`humanfriendly` gone entirely [V]. `torch`
2.13.0's is `filelock`, `typing-extensions`, `setuptools`, `sympy>=1.13.3`,
`networkx>=2.5.1`, `jinja2`, `fsspec` [V].

**Net saving on the order of 600 MB** — the isolated venv would drop from ~854 MB
of site-packages to roughly 220-250 MB (numpy + cv2 + PIL + onnxruntime),
or ~135 MB if cv2 also goes (§6.4). **This is by far the largest available
footprint win, and it is ~6x bigger than any checkpoint change.**

Two constraints, both already satisfied here: onnxruntime 1.28.0 requires Python
≥3.11 and ships a cp314 win_amd64 wheel [V] — **both EMB-Bot venvs are already on
Python 3.14.6** [M], so there is no version bind. (Had they been on 3.10, the cap
would be onnxruntime ≤1.22, which makes `sympy` mandatory again and gives back
~75 MB of the win [V].)

**Weights are roughly a wash at fp32, a win at int8.** The `onnx-community` SAM
2.1 tiny export is 134.08 MB vision encoder + 20.96 MB prompt-encoder/decoder =
155 MB fp32; the int8 variants are 52.57 + 8.66 = **61.2 MB**, q4f16 33.1 MB [V].

### 5.2 Is there an official SAM2 ONNX export? **No.**

`facebookresearch/sam2`'s `tools/` directory contains exactly two files —
`README.md` and `vos_inference.py` [V, contents API]. `README.md` and
`INSTALL.md` contain **zero** mentions of ONNX, ONNX Runtime, TorchScript, or any
export path [V]. HuggingFace `transformers` does have official SAM2 support
including a `mask-generation` pipeline — but it is pure torch — and
`optimum-onnx`'s supported-architecture list includes `SAM` and `Hiera` but
**not `SAM2`** [V]. **Every ONNX path for SAM2 is community-maintained.** Weigh
that accordingly.

### 5.3 The crux: can automatic mask generation survive the port? **Yes — and someone has already done it.**

`SAM2AutomaticMaskGenerator` is not a graph and cannot be exported; it is a Python
class that calls the model `points_per_side²` times and post-processes. So the
real question is how much torch-bound post-processing would have to be
rewritten. From the installed `sam2/utils/amg.py` [V], the split is:

- **torch-bound, would need reimplementing:** `mask_to_rle_pytorch`,
  `calculate_stability_score`, `batched_mask_to_box`, `uncrop_masks`,
  `is_box_near_crop_edge`, plus `torchvision.ops.boxes.batched_nms` (imported at
  the top of `automatic_mask_generator.py`). Five or six functions, all simple
  array arithmetic.
- **already numpy:** `build_all_layer_point_grids`, `generate_crop_boxes`,
  `rle_to_mask`.
- **already cv2:** `remove_small_regions`.

**`axinc-ai/ailia-models` has already written all of it** [V]. Directory
`image_segmentation/segment-anything-2/` ships `sam2_automatic_mask_generator.py`
(5,949 B) whose imports are `numpy`, `cv2`, and its own
`sam2_image_predictor` — **no torch, no torchvision**. NMS is a local greedy numpy
implementation; `calculate_stability_score`, `build_point_grid` and `mask_to_box`
are local numpy. Its `sam2_image_predictor.py` exposes `predict_batch()` taking
`point_coords_batch`, which is exactly the batched-grid driver AMG needs. The
`onnxruntime` branch is real and does not touch the paid ailia SDK (`import
ailia` happens conditionally inside `main()` only when `--onnx` is false). It
tracks SAM 2.1 via a `--version` flag, and the repo was pushed **today**.

Licensing caveat [V]: the model directory carries Apache 2.0, but the repo root
is `NOASSERTION`, and the ONNX weights are hosted on axinc's own storage. **Treat
axinc-ai as a reference implementation to learn from, not as a weights source.**

For producing weights, **`vietanhdev/samexporter` is the better artifact**: MIT
licensed, on PyPI, actively maintained (last push 2026-02-22), supports SAM 2,
2.1 and 3, and — critically — its decoder export declares the dynamic axes you
need to batch a whole prompt grid [V]:

```
{"point_coords": {0: "num_labels", 1: "num_points"},
 "point_labels": {0: "num_labels", 1: "num_points"},
 "mask_input":   {0: "num_labels"},
 "has_mask_input": {0: "num_labels"}}
```

Self-exporting from Meta's Apache-2.0 checkpoints with an MIT tool is the cleanest
provenance story available.

**What to avoid** [V]: `ibaiGorordo/ONNX-SAM2-Segment-Anything` — last push
2024-08-29, predating the SAM 2.1 release, with an open unanswered issue asking
for 2.1 support and a broken conversion notebook; the README self-describes as
"still in development, use it at your own risk". `onnx-community/sam2.1-hiera-tiny-ONNX`
— convenient prebuilt fp32/fp16/int8/q4 graphs, but **no model card and no
declared license**, which is a hard stop for shipping. `lucasgelfond/webgpu-sam2`
— **no license file at all**.

### 5.4 Does ONNX Runtime CPU actually run it? Yes — but no Windows CPU number exists

Evidence it executes [V]: a user ran the ibaiGorordo pipeline with
`['CPUExecutionProvider']` on Windows 10 (the complaint in that issue was output
mismatch, not a load failure); RectLabel's C++ ORT wrapper reports encoder times
on **macOS CPU** of Tiny 1s / Small 2s / BasePlus 4s / Large 10s; axinc-ai ships
and exercises ORT-consumable SAM 2.1 graphs. **No unsupported-op reports were
found for the ORT CPU execution provider on the SAM2 image path** — the two
near-misses in search are an `onnxsim` simplifier assertion and a tinygrad
compile failure, neither an ORT kernel problem.

**[U] There is no published Windows-CPU latency figure for SAM2 on ONNX Runtime.
None.** This would have to be measured before committing.

**And there is one specific red flag that lands directly on this pipeline** [V]:
a user who actually attempted AMG over ONNX reported the ONNX decoder running
*slower* than PyTorch, attributed to the export losing flash-attention, "which
compounds when running a few hundred times / image to get all masks." Given §1
measures the decoder loop at 92% of the cost, **a port that regresses per-prompt
decode time makes the pipeline worse, not better.** The mitigation is to push the
whole grid through the dynamic `num_labels` axis in one call rather than looping
per prompt — which is exactly what EfficientSAM's notebook does (§3.4) and what
samexporter's dynamic axes enable.

### 5.5 int8 quantization — supported, with a caveat that cuts against Hiera

ONNX Runtime's official quantization docs state, verbatim [V]:

> "It is recommended to use dynamic quantization for RNNs and transformer-based
> models, and static quantization for CNN models."

**SAM2's encoder is a hybrid** — Hiera is transformer blocks over a convolutional
patch-embed and downsampling stem — so neither recommendation cleanly applies.
ORT's dynamic quantization also only quantizes "MatMul with const B" by default,
leaving conv-heavy portions in fp32. Expect less than the headline speedup unless
static quantization with a calibration set is used. The docs also warn that
"S8S8 with QOperator will be slow on x86-64 CPUs and should be avoided", and that
the big int8 wins need VNNI — **[U] whether this Ryzen 7 4700U (Zen 2) has usable
int8 dot-product acceleration was not verified**; Zen 2 predates AMD's VNNI
support, so the realistic expectation here is modest.

Best corroborating datapoint [V]: OpenVINO/NNCF int8 on **SAM 1** reports "on the
CPU, the INT8 model achieves approximately a 30% improvement compared to the FP16
model", model size 350 MB → under 100 MB, and "in both prompt and auto modes, the
INT8 model shows almost no change in accuracy". Directionally encouraging;
different toolchain, different model generation, not a substitute for measuring.

**Tooling risk worth knowing** [V]: ORT issue #24459 reports dynamic quantization
silently becoming a no-op for transformer nodes after a 1.20→1.21 upgrade
(204.6 MB → 204.7 MB instead of 120.2 MB), **closed as `not_planned`**. Verify the
quantized artifact actually shrank; do not trust the call to have worked.

---

## 6. Cheapest things to try first — zero new dependencies

Everything in this section uses config fields that **already exist** in
`digitizer/digitizer_core/config.py` and are already plumbed through
`stage2_sam2_segment.py` into `sam2_worker.py`. No new package, no new license
question, no new code.

### 6.1 Lower `photo_segment_sam2_points_per_side` from 16 — the single biggest lever

Measured, Run A, same image, same everything else:

| `points_per_side` | prompts | time | vs 16 | masks |
|---|---|---|---|---|
| 16 (today) | 256 | 53.96s | — | 16 |
| **12** | 144 | **32.10s** | **-41%** | **16** |
| **8** | 64 | **16.91s** | **-69%** | 11 |
| 4 | 16 | 8.70s | -84% | 5 |

**Expected tradeoff.** The grid is a *sampling* of the image; each point is a
seed that may or may not land on a distinct object. Halving `points_per_side`
quarters the number of seeds, so the risk is not blurrier masks — SAM's mask
quality per prompt is unchanged — it is **missed regions**: small or thin objects
that no grid point happens to land on. That is visible in the mask counts above
(16 → 16 → 11 → 5) and it is exactly the failure mode embroidery cares about,
since a missed region becomes a missing color area in the stitch plan.

**The specific recommendation: try 12 first.** It returned the identical 16 masks
as 16 on this image while costing 41% less. The step from 12 to 8 is where mask
loss began. Kent should re-run his own real-photo test at 12 and compare region
counts and the visual result — that is a 10-minute experiment against a config
field, and if quality holds it removes ~18 of the ~45 seconds with no other
change.

**Caution on generalizing.** The measurement image is one photo. Grid sampling
adequacy depends on how many distinct small regions a given image contains, so a
busy photo may lose more at 12 than this one did. The *timing* law
(`T ≈ a + b·points_per_side²`) is robust — it held to within 3% across four
settings. The *quality* curve is image-dependent and must be checked on real
inputs.

### 6.2 Lower `photo_segment_sam2_max_side_px` from 1024 — a smaller, safer win

| `max_side_px` | time at `points_per_side=16` | vs 1024 | masks |
|---|---|---|---|
| 1024 (today) | 53.96s | — | 16 |
| **512** | **42.55s** | **-21%** | **16** |
| 256 | 37.63s | -30% | 13 |

**Why this works is not what you'd expect**, and §1.1 has the detail: it does not
touch the encoder, which always runs at a hard 1024×1024 regardless. It reduces
the per-prompt mask upscale — `_predict` returns masks already resized to the
source resolution, so quartering the source pixels quarters that work.

**Expected tradeoff:** genuine loss of fine boundary precision, since the mask
outline is resolved at the smaller resolution before `_upsample_labels` scales it
back up in the seam. For embroidery this is less alarming than it sounds — the
stitch plan already goes through `simplify_tol_mm=0.2mm` vectorization — but
`docs/photo-quality-root-cause-2026-08-11.md` §`repro_gradient_white_icon` is a
live example of geometry drift on thin shapes causing real damage, so **do not
combine an aggressive `max_side_px` cut with thin-detail artwork without
looking at the result.**

Also note the seam already compensates the min-area floor for the downscale
factor (`min_mask_region_area = (min_detail_mm * px_per_mm * scale)²`), so
lowering `max_side_px` does not silently over-filter. That was handled.

### 6.3 Combining them

The cost model from §1 fits both runs. Solving it per-prompt at each measured
source resolution (Run A: 0.1905 s/prompt at 1024², 0.1459 at 512², 0.1267 at
256²) and extrapolating: `points_per_side=12` at `max_side_px=512` predicts
**~26s**, and `points_per_side=8` at 512 predicts **~15s** — versus today's
~40-54s. **[U] these two are extrapolations, not measurements** — the
four measured combinations are in §6.1 and §6.2. But even the measured
single-knob numbers get most of the way: 12 alone is -41%.

### 6.4 Drop `opencv-python-headless` from the isolated venv — 113 MiB

**[M]** `cv2` is 117.4 MB (112 MiB) — the second largest package in the isolated
venv after torch — and **[V]** `sam2` imports it **lazily**, from inside exactly
two functions: `amg.remove_small_regions` (line 276) and `sam2_utils` line 267,
which is a *training-time* point-sampling helper never reached at inference. So
cv2 exists in this venv for one function.

**[M]** That function costs **~0.8s of 41s (2%)**: `min_mask_region_area=0` ran
40.09s vs 40.93s at 100, same 16 masks.

**The honest caveat:** `remove_small_regions` fills small holes and removes small
islands *within* each individual mask. The seam's downstream floor drops *whole*
small regions. Those are not the same operation, so this is not a free swap —
it would mean reimplementing per-mask hole/island cleanup on the main-venv side
(which already has cv2, scipy and skimage) after the labels come back. Worth
doing if footprint matters; not free.

### 6.5 What no knob can fix

The **~4.8s of fixed per-image subprocess import cost** (`import torch` 2.3-2.5s
+ `import sam2` 2.4s, measured warm, twice). At `points_per_side=8` that becomes
~30% of the remaining SAM2 time. Only leaving PyTorch behind (§5) removes it —
or keeping a warm worker process alive across jobs, which is a different design
change with its own failure modes and is out of scope for this document.

Also worth recording [M]: the worker currently emits a `UserWarning` on every
call — "cannot import name `_C` from `sam2`... Skipping the post-processing step"
— because SAM2's optional CUDA extension was never built. The consequence is that
`max_hole_area`/`max_sprinkle_area` post-processing silently does nothing. That
is benign here (the code path is a CUDA connected-components kernel), but it means
one of SAM2's mask-cleanup features is not actually running, and nobody should
count on it.

---

## 7. Ranked recommendation

Ranked by the brief's own criteria, in order: **license safety → automatic mask
generation works → footprint → speed.**

### 1. Tune `points_per_side` to 12, then evaluate 8. Do this first, today.

License risk zero, new dependencies zero, new code zero. Measured **-41%** at 12
with identical mask output on the test image, **-69%** at 8. It is a config field
that already exists. **Nothing else in this document has a better
effort-to-payoff ratio, and no model swap in §3 comes close** — the best of them
buys 8%.

Validation needed: re-run Kent's real-photo test at 12 and compare region count
and visual result. That is the whole experiment.

### 2. Add `max_side_px=512` if step 1's quality holds. Measured -21% more.

Same zero-risk category. Combined with step 1, extrapolates to ~25s vs today's
~40-54s. Watch thin-detail artwork specifically
(`docs/photo-quality-root-cause-2026-08-11.md`).

### 3. Stay on SAM 2.1 tiny for the model. Do not swap for speed.

Apache-2.0 on code and weights, best-in-class AMG support, and quality Kent has
already validated on a real photo. §1.2 is the argument: every alternative
optimizes the image encoder, which is 8% of the cost. **A model swap cannot fix
the speed problem, and every swap risks the quality that is currently working.**

### 4. If footprint is the priority: drop cv2 from the isolated venv. -113 MiB.

Measured cost: ~2% of runtime and a reimplementation of per-mask hole/island
cleanup on the main-venv side. §6.4.

### 5. If a bigger project is warranted: ONNX Runtime instead of PyTorch. ~-600 MB.

The only change that meaningfully attacks the 1 GB footprint —
**~6x larger than any checkpoint change** — and it also removes the 4.8s
per-image torch import. Both venvs are already on Python 3.14.6, so onnxruntime
1.28.0 fits with no version bind.

Build it as: **`samexporter` (MIT) to self-export from Meta's Apache-2.0
checkpoints**, plus a numpy AMG driver modelled on **`axinc-ai/ailia-models`'s
torch-free `sam2_automatic_mask_generator.py`** (Apache-2.0, reference only —
export your own weights rather than depending on their hosting).

**Verify three things before committing**, in this order:
1. **Measure Windows CPU latency yourself.** No published number exists, and one
   credible report has the ONNX decoder running *slower* than PyTorch under
   exactly this AMG workload. Given the decoder is 92% of the cost, a regression
   here makes things worse. Push the whole prompt grid through the dynamic
   `num_labels` axis in one call rather than looping.
2. **Verify int8 actually shrinks and actually speeds up** — ORT has a known
   silent-no-op failure mode, and this Zen 2 CPU predates AMD's VNNI, so the
   headline int8 gains may not be available.
3. **Confirm mask parity against the torch path** on the existing fixtures before
   switching the default.

This is a multi-day project with real maintenance risk (nothing here is
officially supported by Meta). Do steps 1-2 first and re-measure whether it is
still worth it.

### 6. EdgeTAM — the only model swap worth an experiment, and only for footprint.

Apache-2.0 code *and* checkpoints (Meta's own, cleanest license post-SAM-2),
**56.1 MB vs 156.0 MB**, real `automatic_mask_generator.py`, and it is a fork of
the `sam2` package so `sam2_worker.py` would need a checkpoint/config/package
change, not a rewrite. Saves ~100 MB and a slice of the 8% encoder time.

**Blocked on an unknown:** its published quality numbers are all *video* metrics
(SA-V J&F 72.3 vs SAM 2.1's 76.8). **No image-mode comparison against SAM 2.1 was
found.** Since image quality is the thing Kent validated and cares about, that
would have to be measured before adopting.

### 7. EfficientViT-SAM-L0 — revisit only if step 5 happens.

Apache-2.0, real `EfficientViTSamAutomaticMaskGenerator`, best published quality
in the field (COCO box mIoU 78.5, beating SAM-H's 77.4), and the only candidate
with first-class encoder **and** decoder ONNX export with dynamic prompt-batch
axes. Independently benchmarked at 194 ms CPU SegAny vs SAM2-B+'s 1221 ms. But:
139 MB checkpoint (only 17 MB under the incumbent), decoder is SAM 1's unchanged
so per-prompt cost is a wash, and no everything-mode ONNX runner ships — that
would be new code. **Only competitive inside an ONNX-first design.**

### 8-10. MobileSAM / EfficientSAM / SlimSAM — viable licenses, no winning axis.

All Apache-2.0 with usable weights terms. MobileSAM has the best drop-in story
(40.7 MB, real `SamAutomaticMaskGenerator`, most actively maintained) but the
worst quality (COCO AP 39.4 vs SAM's 46.1) and requires quarantining its own
AGPL-licensed `MobileSAMv2/` subdirectory. EfficientSAM has better quality and
pre-built ONNX but **no AMG API at all** (DIY from a notebook) and a dormant
repo. SlimSAM has good quality-per-MAC and real AMG but no ONNX path and **no
published latency of any kind**. All three are SAM-1-generation.

### Not viable

- **SAM 1** — heavier (375 MB smallest checkpoint), slower, dormant, and its
  ONNX export is **decoder-only** so torch stays. Answers question (b) in the
  negative.
- **NanoSAM** — TensorRT/CUDA only, no CPU path, prompt-only, untouched since
  2023.
- **SAM 3 / SAM 3.1** — 3.45/3.50 GB, gated download, GPU-required, custom
  non-OSI license, and **no automatic mask generation at all**. A regression on
  every axis that matters here.

### ❌ Disqualified on license

- **FastSAM — AGPL-3.0** (§2.1). The repo's LICENSE file is AGPL-3.0, the README's
  "Apache 2.0" claim links to that same AGPL file, `ultralytics` is AGPL-3.0, the
  weights are covered too, and FastSAM vendors the AGPL code in-tree so you cannot
  route around it. Using it means open-sourcing EMB-Bot or buying an Ultralytics
  Enterprise license.
- **EdgeSAM — NTU S-Lab License 1.0, non-commercial** (§2.2). "Redistribution and
  use for non-commercial purpose... are permitted." Same category as the
  `bria-rmbg` rejection.

---

## 8. What could not be verified

Recorded honestly, so nobody mistakes a gap for a finding.

- **[U] EdgeTAM's image-mode segmentation quality vs SAM 2.1 tiny.** Only video
  metrics (SA-V, DAVIS) are published. This is the number recommendation 6 hinges
  on.
- **[U] Any Windows-CPU latency figure for SAM2 on ONNX Runtime.** Nothing exists.
  The nearest datapoint is a macOS-CPU encoder time (Tiny ≈1s) from a third-party
  C++ wrapper.
- **[U] CPU benchmarks for EdgeSAM, EfficientSAM, EdgeTAM, or SlimSAM.** Every
  headline number in this field is A100, RTX 3090, Jetson, or iPhone NPU. The
  only published CPU figures anywhere are MobileSAM's informal "around 3s" on a
  Mac i5 and the survey's Xeon Gold 6330 table (§3.3).
- **[U] SlimSAM's wall-clock latency, on any hardware.** README tables are images;
  the paper reports MACs only.
- **[U] NanoSAM's checkpoint sizes.** Google Drive links, no sizes in the README,
  no GitHub releases.
- **[U] The verbatim SA-1B Dataset Research License text.** Meta's download page
  returns 403. §2.4 — affects every distilled variant equally, and Meta's own
  Apache-2.0 release of SAM/SAM2 weights is the working precedent.
- **[U] Whether this Ryzen 7 4700U has usable int8 acceleration.** Zen 2 predates
  AMD's VNNI support, so §5.5's int8 speedup expectations should be treated as
  optimistic until measured.
- **[U] §6.3's combined `points_per_side` + `max_side_px` figures** are
  extrapolations from the fitted cost model, not measurements. The measured
  single-knob numbers are in §6.1 and §6.2.
- **Method caveat on §5.2:** GitHub's code-search API returns 401 unauthenticated,
  so the "no official ONNX export" finding rests on the repo file tree plus
  `README.md` and `INSTALL.md` — strong, but not an exhaustive repo-wide grep.
