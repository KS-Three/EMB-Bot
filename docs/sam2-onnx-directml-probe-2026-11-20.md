# SAM2 through ONNX Runtime: CPU and DirectML probe (2026-11-20)

**Question (Kent, 2026-11-20):** would a local inference framework help EMB-Bot?
The one concrete candidate was the ONNX port of SAM2 that
`docs/sam-alternatives-research-2026-08-11.md` §5 and §7 step 5 left unmeasured.
This doc records that measurement. It changes no runtime code.

## Result

| | vs PyTorch CPU (today's worker) | Masks |
|---|---|---|
| ONNX Runtime, CPU | **1.0–1.6×**: no material gain | identical on 6/6 |
| ONNX Runtime, **DirectML** (GPU) | **3.2–15×**: 1.4–5.8 s against 6–21 s | identical on 6/6 |

- **The CPU port is not a speed lever.** The research doc's warning was that
  the ONNX decoder can run slower than PyTorch. It did not run slower here, but
  it was not meaningfully faster either.
- **The win is the GPU, through DirectML.** DirectML runs on any DirectX 12
  GPU (NVIDIA, AMD or Intel integrated) with one ~20 MB wheel
  (`onnxruntime-directml`), with no CUDA toolkit and no vendor lock.
- **The size win counts whether or not there is a GPU.** The exported tiny model
  is `enc.onnx` 109.4 MB + `dec.onnx` 16.6 MB. Today's lane needs a 2–3 GB
  PyTorch venv (`digitizer/sam2_isolated/README.md`), and the post-v1
  "enhanced photo mode" is planned as an ~1 GB download
  (`PRODUCT.md`, launch posture). ONNX Runtime would replace PyTorch at run
  time, which makes about 150 MB in all.

## What was run

`digitizer/sam2_isolated/onnx_probe.py`, in a scratch Python 3.12.15 venv
(torch 2.15.0+cpu, Meta's SAM-2 from GitHub, onnx 1.23.2, onnxruntime 1.32.0
then onnxruntime-directml 1.24.4). Export: `torch.onnx.export`
(TorchScript path, opset 17) of two wrappers. The first is the image encoder
including `no_mem_embed`. The second is the prompt encoder plus the mask decoder,
with the batch axis dynamic. The export took 6.7 s.

**Production settings, from `config.py`:** `sam2.1_hiera_tiny`,
`points_per_side=12`, `points_per_batch=64`, `multimask_output=True`, long side
capped at 1024 px, and `min_mask_region_area=36`.

**What makes the parity reading fair:** only the two network forwards are
swapped. `SAM2AutomaticMaskGenerator`'s own filtering, NMS and small-region
removal run unchanged on both paths, so a mask difference could only come from
the networks. Parity is measured as the area-weighted best-match IoU in both
directions, plus mask count and coverage.

**Machine:** Kent's desktop: an i7-14700KF (20 torch threads), 32 GB of RAM and
an **RTX 4070 (12 GB)** on driver 565.90. `sam2_worker.py` and the SAM2 README
say "this machine has no GPU". That was true of the machine they were written
on, and it is not true of this one.

## Numbers

Wall time for `generate()` (best of 2), PyTorch CPU against ONNX:

| fixture (`testdata/photo/`) | size | torch CPU | ONNX CPU | torch CPU (DML run) | ONNX DirectML | masks t/o | IoU t→o / o→t |
|---|---|---|---|---|---|---|---|
| `drone_render.png` | 683×1024 | 17.05 | 10.90 | 13.69 | **1.99** | 5/5 | 1.0 / 1.0 |
| `owl_kent.jpg` | 554×554 | 16.78 | 17.68 | 20.58 | **5.77** | 3/3 | 1.0 / 1.0 |
| `photo_dof_meadow.png` | 520×780 | 17.53 | 15.77 | 20.88 | **1.37** | 2/2 | 1.0 / 1.0 |
| `logo_golden_tee.jpg` | 1024×1024 | 19.13 | 16.80 | 9.10 | **1.75** | 1/1 | 1.0 / 1.0 |
| `photo_sunset_backlit.png` | 600×800 | 21.18 | 20.36 | 7.30 | **1.51** | 2/2 | 1.0 / 1.0 |
| `summit_badge.png` | 900×900 | 23.15 | 23.09 | 6.16 | **1.93** | 4/4 | 1.0 / 1.0 |

PyTorch was re-measured beside each ONNX run, so every ratio compares two runs
taken together.

## Caveats: what this does NOT show

1. **The parity check is thin.** These fixtures produce only 1–5 surviving
   masks each, which is far fewer than the "tens to low hundreds" of raw masks
   the README expects. Identical output on 17 masks is real evidence, but it
   is not a corpus. Before any adoption, re-check on fixtures that produce
   many masks, and compare the label maps through
   `stage2_sam2_segment`.
2. **The PyTorch CPU baseline is noisy.** `summit_badge` measured 6.2 s in
   one run and 23.2 s in another. A later single-image check of `owl_kent`
   read 4.45 s, where the table has 16.8 and 20.6, against 1.05 s on
   DirectML (4.3×). The cause is probably other load on a shared desktop.
   DirectML stayed fast in every run (1.0–5.8 s). The ratios are a range, not
   a constant.
3. **Only one GPU, an NVIDIA desktop card, was measured.** The integrated Intel
   or AMD graphics a typical customer laptop has is the case that matters most,
   and it has not been run. DirectML on such a GPU may land between the CPU
   and 4070 numbers.
4. **Cold start was not measured.** These timings are with warm sessions.
   The worker is a fresh subprocess per job, so the cost of loading the model
   and creating the ORT sessions belongs in the comparison. Today's lane pays
   a measured 156 s cold torch import plus download
   (`docs/sam2-segmentation-live-acceptance-2026-08-10.md`).
5. **Where the models come from:** the models were self-exported from Meta's
   Apache-2.0 checkpoint, which is the clean route
   `docs/scope-digest/licence-and-deps.md` names. No community ONNX weights
   were used.
6. **Int8 quantization was not tried**, and it is not needed for the GPU path.

## If this is pursued (post-v1: SAM2 ships after launch)

1. Measure DirectML on an integrated-GPU laptop, and measure the CPU fallback
   on that same laptop.
2. Add an opt-in ONNX backend to `sam2_worker.py` that keeps the PyTorch path
   as a fallback, with the ORT provider chosen at run time: DirectML, then CPU.
3. Run a parity sweep through `stage2_sam2_segment` on the photo corpus, and
   measure cold start.
4. Then the packaging question: should the enhanced-photo download become
   about 150 MB of ONNX instead of about 1 GB of PyTorch? That one is Kent's.
