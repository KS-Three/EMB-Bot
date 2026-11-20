"""SAM2.1 tiny: PyTorch CPU vs ONNX Runtime, same AMG settings as sam2_worker.py.

A PROBE, not part of the pipeline: nothing imports it. Evidence and numbers:
docs/sam2-onnx-directml-probe-2026-11-20.md.

Only the two network forwards are swapped (image encoder, prompt-encoder+mask-decoder);
SAM2's own automatic-mask-generator post-processing runs unchanged on both paths,
so any mask difference comes from the networks alone.

Run it in a SCRATCH venv (torch CPU + Meta's SAM2 + onnx + onnxscript +
onnxruntime or onnxruntime-directml), never the shared digitizer/.venv:

    OUT=<scratch dir> PROV=DmlExecutionProvider REPS=2 python onnx_probe.py img1.png img2.jpg ...

OUT (default: cwd) receives enc.onnx (~110 MB), dec.onnx (~17 MB) and
results.json. PROV is a comma list of ONNX Runtime providers (default CPU).
Needs the checkpoint `sam2_worker.py --prewarm tiny` caches.
"""
import sys, time, json, os
import numpy as np, torch, cv2
from PIL import Image
import onnxruntime as ort
from sam2.build_sam import build_sam2
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

HERE = os.path.abspath(os.environ.get("OUT", "."))
CKPT = os.path.expanduser("~/.cache/sam2/sam2.1_hiera_tiny.pt")
CFG = "configs/sam2.1/sam2.1_hiera_t.yaml"
PPS, MIN_AREA, MAX_SIDE = 12, 36, 1024  # production defaults (config.py)
torch.set_grad_enabled(False)
model = build_sam2(CFG, CKPT, device="cpu").eval()


class Enc(torch.nn.Module):
    def __init__(s, m):
        super().__init__(); s.m = m
    def forward(s, img):
        bo = s.m.forward_image(img)
        _, vf, _, _ = s.m._prepare_backbone_features(bo)
        if s.m.directly_add_no_mem_embed:
            vf[-1] = vf[-1] + s.m.no_mem_embed
        sizes = [(256, 256), (128, 128), (64, 64)]
        f = [x.permute(1, 2, 0).reshape(1, -1, *sz) for x, sz in zip(vf, sizes)]
        return f[2], f[0], f[1]


class Dec(torch.nn.Module):
    def __init__(s, m):
        super().__init__(); s.m = m
    def forward(s, emb, f0, f1, coords, labels):
        sp, de = s.m.sam_prompt_encoder(points=(coords, labels), boxes=None, masks=None)
        lr, iou, _, _ = s.m.sam_mask_decoder(
            image_embeddings=emb, image_pe=s.m.sam_prompt_encoder.get_dense_pe(),
            sparse_prompt_embeddings=sp, dense_prompt_embeddings=de,
            multimask_output=True, repeat_image=True, high_res_features=[f0, f1])
        return lr, iou


def export():
    enc_p, dec_p = os.path.join(HERE, "enc.onnx"), os.path.join(HERE, "dec.onnx")
    if os.path.exists(enc_p) and os.path.exists(dec_p):
        return enc_p, dec_p
    img = torch.randn(1, 3, 1024, 1024)
    e, f0, f1 = Enc(model)(img)
    t = time.time()
    torch.onnx.export(Enc(model), (img,), enc_p, input_names=["img"],
                      output_names=["emb", "f0", "f1"], opset_version=17, dynamo=False)
    c = torch.rand(64, 1, 2) * 1024; l = torch.ones(64, 1, dtype=torch.int32)
    torch.onnx.export(Dec(model), (e, f0, f1, c, l), dec_p,
                      input_names=["emb", "f0", "f1", "coords", "labels"],
                      output_names=["lr", "iou"], opset_version=17, dynamo=False,
                      dynamic_axes={"coords": {0: "B"}, "labels": {0: "B"},
                                    "lr": {0: "B"}, "iou": {0: "B"}})
    print(f"export {time.time()-t:.1f}s  enc {os.path.getsize(enc_p)/1e6:.1f}MB  dec {os.path.getsize(dec_p)/1e6:.1f}MB")
    return enc_p, dec_p


def make_gen():
    return SAM2AutomaticMaskGenerator(model, points_per_side=PPS, points_per_batch=64,
                                      min_mask_region_area=MIN_AREA, output_mode="binary_mask",
                                      multimask_output=True)


def patch_ort(gen, enc_s, dec_s, timers):
    pred = gen.predictor

    def set_image(image):
        pred.reset_predictor()
        pred._orig_hw = [image.shape[:2]]
        x = pred._transforms(image)[None].numpy()
        t = time.perf_counter()
        emb, f0, f1 = enc_s.run(None, {"img": x})
        timers["enc"] += time.perf_counter() - t
        pred._features = {"image_embed": torch.from_numpy(emb),
                          "high_res_feats": [torch.from_numpy(f0), torch.from_numpy(f1)]}
        pred._is_image_set = True

    def _predict(point_coords, point_labels, boxes=None, mask_input=None,
                 multimask_output=True, return_logits=False, img_idx=-1):
        assert boxes is None and mask_input is None and multimask_output
        F = pred._features
        t = time.perf_counter()
        lr, iou = dec_s.run(None, {"emb": F["image_embed"].numpy(),
                                   "f0": F["high_res_feats"][0].numpy(),
                                   "f1": F["high_res_feats"][1].numpy(),
                                   "coords": point_coords.float().numpy(),
                                   "labels": point_labels.int().numpy()})
        timers["dec"] += time.perf_counter() - t
        lr, iou = torch.from_numpy(lr), torch.from_numpy(iou)
        masks = pred._transforms.postprocess_masks(lr, pred._orig_hw[img_idx])
        lr = torch.clamp(lr, -32.0, 32.0)
        if not return_logits:
            masks = masks > pred.mask_threshold
        return masks, iou, lr

    pred.set_image = set_image
    pred._predict = _predict


def patch_torch_timers(gen, timers):
    pred = gen.predictor
    o_set, o_pred = pred.set_image, pred._predict
    def set_image(image):
        t = time.perf_counter(); o_set(image); timers["enc"] += time.perf_counter() - t
    def _predict(*a, **k):
        t = time.perf_counter(); r = o_pred(*a, **k); timers["dec"] += time.perf_counter() - t; return r
    pred.set_image, pred._predict = set_image, _predict


def labels_of(records, hw):
    lab = np.full(hw, -1, np.int32)
    for i, r in enumerate(sorted(records, key=lambda r: -r["area"])):
        lab[r["segmentation"]] = i
    return lab


def load(path):
    rgb = np.array(Image.open(path).convert("RGB"))
    h, w = rgb.shape[:2]
    if max(h, w) > MAX_SIDE:
        s = MAX_SIDE / max(h, w)
        rgb = cv2.resize(rgb, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    return rgb


def match_iou(ra, rb):
    """Mean best-match IoU of A's masks against B's (area-weighted)."""
    if not ra or not rb:
        return float("nan")
    B = np.stack([r["segmentation"].ravel() for r in rb]).astype(np.float32)
    bs = B.sum(1)
    tot = wsum = 0.0
    for r in ra:
        a = r["segmentation"].ravel().astype(np.float32)
        inter = B @ a
        iou = inter / (bs + a.sum() - inter + 1e-9)
        tot += iou.max() * a.sum(); wsum += a.sum()
    return float(tot / wsum)


def run(path, gen, timers, reps):
    img = load(path)
    out, walls = None, []
    for _ in range(reps):
        for k in timers: timers[k] = 0.0
        t = time.perf_counter()
        with torch.inference_mode():
            out = gen.generate(img)
        walls.append(time.perf_counter() - t)
    return img, out, min(walls), dict(timers)


if __name__ == "__main__":
    images = sys.argv[1:]
    reps = int(os.environ.get("REPS", "2"))
    enc_p, dec_p = export()
    PROV = os.environ.get("PROV", "CPUExecutionProvider").split(",")
    so = ort.SessionOptions(); so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    enc_s = ort.InferenceSession(enc_p, so, providers=PROV)
    dec_s = ort.InferenceSession(dec_p, so, providers=PROV)
    tt, to = {"enc": 0.0, "dec": 0.0}, {"enc": 0.0, "dec": 0.0}
    g_t, g_o = make_gen(), make_gen()
    patch_torch_timers(g_t, tt); patch_ort(g_o, enc_s, dec_s, to)
    print(f"torch threads {torch.get_num_threads()}  ort {ort.__version__}  torch {torch.__version__}")
    rows = []
    for p in images:
        img, rt, wt, tm_t = run(p, g_t, tt, reps)
        _, ro, wo, tm_o = run(p, g_o, to, reps)
        lt, lo = labels_of(rt, img.shape[:2]), labels_of(ro, img.shape[:2])
        row = dict(image=os.path.basename(p), hw=list(img.shape[:2]),
                   torch_s=round(wt, 2), onnx_s=round(wo, 2), speedup=round(wt / wo, 2),
                   torch_enc=round(tm_t["enc"], 2), torch_dec=round(tm_t["dec"], 2),
                   onnx_enc=round(tm_o["enc"], 2), onnx_dec=round(tm_o["dec"], 2),
                   n_torch=len(rt), n_onnx=len(ro),
                   mask_iou_t2o=round(match_iou(rt, ro), 4), mask_iou_o2t=round(match_iou(ro, rt), 4),
                   coverage_t=round(float((lt >= 0).mean()), 3), coverage_o=round(float((lo >= 0).mean()), 3))
        rows.append(row); print(json.dumps(row), flush=True)
    json.dump(rows, open(os.path.join(HERE, "results.json"), "w"), indent=1)
