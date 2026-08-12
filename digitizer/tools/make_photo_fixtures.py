#!/usr/bin/env python
"""Generate the committed photo-REALISTIC classifier/pipeline fixtures
(testdata/photo/photo_*.png, excluding the older *_stub.png pair).

Why these exist (2026-08-11): the photo class had only two synthetic stubs
(full-frame RGB noise / gradient+grain), which are too easy — SAM2's
measured real-photo benefit is invisible on them and nothing in the corpus
regression-tests the photo lane against the failure modes that actually
distinguish photo pipelines. Kent's motivating real case: a snowy owl
(pale subject) on a beige wall in a tight crop.

Every fixture is procedurally generated — pure numpy/cv2 drawing plus
seeded value-noise, no downloads, no external assets, licensing-clean —
and deterministic (fixed per-fixture seeds; `--check` twice yields
byte-identical arrays). All of them MUST classify into photo territory
(stage0_classify: unique_color_mass >= 0.28), which in practice means the
fine per-pixel grain layers below are load-bearing, not decoration: they
are what breaks the throwaway 16-color quantize locally the way real
sensor noise does. Amplitudes were tuned against the real classifier —
re-run `--check` and re-read the printed signals before touching any of
them.

Fixtures (intended stage-0 class in parens):

  photo_owl_pale.png       (photo_subject) Pale owl portrait on a pale
                           wall — the snowy-owl failure shape, harder than
                           tight_crop_pale_subject.png: multi-octave
                           feather streaks + barring, soft wall shadow,
                           sensor grain, and the subject touches THREE
                           image corners (wall survives only near the
                           top-right), so border-based background logic
                           gets no easy ring.
  photo_dof_meadow.png     (photo_scene) Two sharp foreground mushrooms
                           against a heavily blurred meadow with bokeh
                           discs — depth-of-field: sharp subject pixels
                           are a minority, smooth blur dominates.
  photo_grass_macro.png    (photo_subject) Full-frame macro grass —
                           anisotropic high-frequency blade texture at
                           native resolution, the SLIC-over-segments /
                           SAM2-should-win case.
  photo_sunset_backlit.png (photo_scene) Low-contrast backlit sunset:
                           smooth global sky ramp + sun glow, silhouetted
                           ridge/tree/bird — tests gradient handling and
                           subject extraction together.
  photo_chrome_specular.png (photo_subject) Brushed-metal kettle with hard
                           specular highlights that quantize as separate
                           regions, on a dark studio sweep.

Usage (from `digitizer/`):

    .venv/Scripts/python tools/make_photo_fixtures.py           # write PNGs
    .venv/Scripts/python tools/make_photo_fixtures.py --check   # classify only

Committed output is canonical — regenerate only if a fixture's shape of
failure itself needs to change, then re-verify the classifier verdicts
printed by `--check` still match tests/test_stage0_classify.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "testdata" / "photo"
sys.path.insert(0, str(ROOT))


# --- shared procedural helpers ----------------------------------------------

def _value_noise(rng: np.random.Generator, h: int, w: int,
                 lo_h: int, lo_w: int, amplitude: float) -> np.ndarray:
    """Seeded low-res grid upscaled to (h, w): smooth blobby value noise.
    Anisotropic grids (lo_h != lo_w proportionally) give directional
    streaks — tall grids stretch into vertical strands, flat grids into
    horizontal bands."""
    lo = rng.uniform(-1.0, 1.0, size=(lo_h, lo_w))
    return cv2.resize(lo, (w, h), interpolation=cv2.INTER_CUBIC) * amplitude


def _grain(rng: np.random.Generator, h: int, w: int,
           lum_sigma: float, chroma_sigma: float) -> np.ndarray:
    """Sensor-grain layer: correlated luminance noise plus smaller
    independent per-channel chroma noise. This is what carries the
    unique_color_mass signal — see module docstring before reducing it."""
    lum = rng.normal(0.0, lum_sigma, size=(h, w, 1))
    chroma = rng.normal(0.0, chroma_sigma, size=(h, w, 3))
    return lum + chroma


def _streak_noise(rng: np.random.Generator, h: int, w: int,
                  kernel: np.ndarray, amplitude: float) -> np.ndarray:
    """Native-resolution white noise smeared along `kernel` — anisotropic
    high-frequency texture (feather strands, grass blades, brushed metal).
    Unlike upscaled value noise this KEEPS pixel-scale frequency across the
    smear direction, which is what drives gradient_smoothness up."""
    noise = rng.uniform(-1.0, 1.0, size=(h, w)).astype(np.float32)
    smeared = cv2.filter2D(noise, -1, kernel / kernel.sum())
    smeared /= max(1e-9, float(np.abs(smeared).std()) * 3.0)
    return np.clip(smeared, -1.0, 1.0) * amplitude


def _v_kernel(length: int) -> np.ndarray:
    return np.ones((length, 1), np.float32)


def _h_kernel(length: int) -> np.ndarray:
    return np.ones((1, length), np.float32)


def _soft_mask(mask: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)


def _finish(img: np.ndarray) -> np.ndarray:
    return np.clip(img, 0, 255).round().astype(np.uint8)


# --- 1. pale owl on pale wall, tight crop ------------------------------------

def make_owl_pale() -> np.ndarray:
    """Snowy-owl-class portrait, RGB. Subject touches the top-left,
    bottom-left, and bottom-right corners; the wall survives only around
    the top-right corner. Wall/body separation is ~9 gray levels of base
    color — the texture, shadow, and eyes are what a photo pipeline gets."""
    H, W = 640, 500
    rng = np.random.default_rng(20260811)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    # wall: pale beige with low-frequency mottle and a corner vignette
    img = np.empty((H, W, 3), np.float64)
    img[:] = (221.0, 212.0, 195.0)
    mottle = _value_noise(rng, H, W, 7, 5, 4.5) + _value_noise(rng, H, W, 19, 15, 2.5)
    img += mottle[:, :, None]
    r = np.hypot((xx - W / 2) / W, (yy - H / 2) / H)
    img -= (r ** 2 * 34.0)[:, :, None]

    # subject mask: body ellipse + head circle; touches 3 corners
    mask = np.zeros((H, W), np.uint8)
    cv2.ellipse(mask, (int(W * 0.44), int(H * 0.74)),
                (int(W * 0.62), int(H * 0.52)), 6, 0, 360, 1, -1)
    cv2.circle(mask, (int(W * 0.40), int(H * 0.22)), int(W * 0.44), 1, -1)

    # soft wall shadow cast up-right of the subject
    shadow = np.roll(mask, (14, 26), axis=(0, 1)).astype(np.float32)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 22.0)
    img -= (shadow * (1 - _soft_mask(mask, 2.0)) * 20.0)[:, :, None]

    # owl body: near-white with vertical feather streaks + barring. The
    # feather layer is smeared noise re-blurred to MID frequency: pixel-scale
    # iid noise here just fires Canny and gets excluded from the classifier's
    # smoothness measurement, while few-px structure survives in the valid
    # windows the way real feather detail does.
    body = np.empty((H, W, 3), np.float64)
    body[:] = (230.0, 224.0, 212.0)
    shading = _value_noise(rng, H, W, 6, 5, 6.0)           # soft form shading
    streaks = cv2.GaussianBlur(
        _streak_noise(rng, H, W, _v_kernel(9), 30.0), (0, 0), 1.0)
    barring = _value_noise(rng, H, W, 46, 10, 7.0)          # owl barring rows
    body += (shading + streaks + barring)[:, :, None]
    # feathers are slightly warm where barred, cool where lit
    body[:, :, 2] -= barring * 0.5

    alpha = _soft_mask(mask, 1.6)[:, :, None]
    img = img * (1 - alpha) + body * alpha

    # face: yellow iris, black pupil, tiny specular; dark beak
    for ex in (0.28, 0.52):
        c = (int(W * ex), int(H * 0.20))
        cv2.circle(img, c, 26, (168, 138, 42), -1)
        cv2.circle(img, c, 12, (28, 24, 20), -1)
        cv2.circle(img, (c[0] + 4, c[1] - 4), 3, (240, 238, 232), -1)
    cv2.ellipse(img, (int(W * 0.40), int(H * 0.30)), (10, 17), 0, 0, 360,
                (52, 42, 34), -1)

    img = cv2.GaussianBlur(img, (0, 0), 0.6)  # optics: nothing is pixel-sharp
    # feather micro-detail on the SUBJECT only — the wall stays smoother
    img += (rng.normal(0.0, 5.0, size=(H, W)) * alpha[:, :, 0])[:, :, None]
    img += _grain(rng, H, W, 6.0, 2.5)
    return _finish(img)


# --- 2. depth-of-field meadow with two sharp subjects -------------------------

def make_dof_meadow() -> np.ndarray:
    """Two sharp foreground mushrooms; everything behind them is a heavily
    blurred meadow with bokeh discs. RGB."""
    H, W = 520, 780
    rng = np.random.default_rng(20260812)
    yy = np.mgrid[0:H, 0:W][0].astype(np.float64) / H

    # blurred meadow: vertical green ramp + big soft mottle
    top = np.array([64.0, 92.0, 48.0])
    bot = np.array([138.0, 128.0, 74.0])
    bg = top[None, None, :] * (1 - yy[:, :, None]) + bot[None, None, :] * yy[:, :, None]
    bg += _value_noise(rng, H, W, 9, 13, 14.0)[:, :, None]

    # bokeh discs: warm out-of-focus highlights, soft-edged
    bokeh = np.zeros((H, W), np.float32)
    for _ in range(46):
        cx = int(rng.uniform(0, W))
        cy = int(rng.uniform(0, H * 0.72))
        rad = int(rng.uniform(9, 34))
        disc = np.zeros((H, W), np.float32)
        cv2.circle(disc, (cx, cy), rad, float(rng.uniform(0.25, 0.8)), -1)
        bokeh += cv2.GaussianBlur(disc, (0, 0), rad * 0.22)
    bg += bokeh[:, :, None] * np.array([52.0, 48.0, 22.0])[None, None, :]
    bg = cv2.GaussianBlur(bg, (0, 0), 5.0)  # the depth-of-field wash

    img = bg
    # dark blurred ground band the subjects sit on
    ground = np.zeros((H, W), np.uint8)
    cv2.rectangle(ground, (0, int(H * 0.86)), (W, H), 1, -1)
    g = _soft_mask(ground, 9.0)[:, :, None]
    img = img * (1 - g * 0.55) + np.array([46.0, 40.0, 26.0])[None, None, :] * g * 0.55

    # two sharp mushrooms (the in-focus subjects)
    for cx, cy, s, cap_rgb in (
        (int(W * 0.36), int(H * 0.78), 1.00, (176.0, 84.0, 52.0)),
        (int(W * 0.58), int(H * 0.83), 0.72, (198.0, 122.0, 64.0)),
    ):
        m = np.zeros((H, W), np.uint8)
        cv2.rectangle(m, (cx - int(16 * s), cy - int(52 * s)),
                      (cx + int(16 * s), cy), 1, -1)                 # stem
        cv2.ellipse(m, (cx, cy - int(52 * s)), (int(58 * s), int(34 * s)),
                    0, 180, 360, 1, -1)                              # cap
        cap = np.zeros((H, W), np.uint8)
        cv2.ellipse(cap, (cx, cy - int(52 * s)), (int(58 * s), int(34 * s)),
                    0, 180, 360, 1, -1)

        subj = np.empty((H, W, 3), np.float64)
        subj[:] = (214.0, 198.0, 172.0)                              # stem tone
        capf = cap.astype(np.float64)[:, :, None]
        subj = subj * (1 - capf) + np.array(cap_rgb)[None, None, :] * capf
        subj += _streak_noise(rng, H, W, _v_kernel(4), 7.0)[:, :, None]
        for _ in range(int(26 * s)):                                 # cap speckles
            px = cx + int(rng.uniform(-52 * s, 52 * s))
            py = cy - int(52 * s) - int(rng.uniform(2, 30 * s))
            cv2.circle(subj, (px, py), int(rng.uniform(1, 3)), (232, 222, 200), -1)

        a = _soft_mask(m, 0.7)[:, :, None]
        img = img * (1 - a) + subj * a

    img += _grain(rng, H, W, 6.5, 2.4)
    return _finish(img)


# --- 3. macro grass / fur-class high-frequency texture ------------------------

def make_grass_macro() -> np.ndarray:
    """Full-frame macro grass: anisotropic pixel-scale blade texture, clump
    lighting, dew highlights. RGB. The over-segmentation stress case."""
    H, W = 560, 760
    rng = np.random.default_rng(20260813)

    base = np.empty((H, W, 3), np.float64)
    base[:] = (58.0, 104.0, 44.0)
    # clump lighting and yellowing patches (low frequency)
    clumps = _value_noise(rng, H, W, 8, 11, 16.0)
    yellowing = np.clip(_value_noise(rng, H, W, 5, 7, 1.0), 0, 1)
    base += clumps[:, :, None]
    base[:, :, 0] += yellowing * 34.0
    base[:, :, 1] += yellowing * 22.0

    # blades: two near-vertical smear directions so strands cross
    k1 = cv2.getRotationMatrix2D((10, 10), 8, 1.0)
    k2 = cv2.getRotationMatrix2D((10, 10), -11, 1.0)
    kern1 = cv2.warpAffine(_v_kernel(17).repeat(21, axis=1) *
                           (np.arange(21) == 10)[None, :], k1, (21, 21))
    kern2 = cv2.warpAffine(_v_kernel(17).repeat(21, axis=1) *
                           (np.arange(21) == 10)[None, :], k2, (21, 21))
    blades = (_streak_noise(rng, H, W, kern1 + 1e-6, 36.0)
              + _streak_noise(rng, H, W, kern2 + 1e-6, 28.0))
    base[:, :, 1] += blades
    base[:, :, 0] += blades * 0.55
    base[:, :, 2] += blades * 0.30

    # dew highlights: tiny bright points
    for _ in range(70):
        p = (int(rng.uniform(0, W)), int(rng.uniform(0, H)))
        cv2.circle(base, p, int(rng.uniform(1, 2)), (228, 240, 214), -1)

    # blade micro-edges: unsmeared pixel-scale detail on top of the streaks —
    # this is what pushes gradient_smoothness into photo_subject territory
    # (full-frame texture leaves no smooth interior, unlike the owl portrait)
    base += rng.normal(0.0, 16.0, size=(H, W))[:, :, None]
    base += _grain(rng, H, W, 9.0, 3.0)
    return _finish(base)


# --- 4. low-contrast backlit sunset -------------------------------------------

def make_sunset_backlit() -> np.ndarray:
    """Smooth global sky ramp + sun glow, silhouetted ridge and tree, one
    bird. RGB. Gradient handling and subject extraction in one frame."""
    H, W = 600, 800
    rng = np.random.default_rng(20260814)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    t = yy / H

    # sky: three-stop vertical ramp, purple -> dusty rose -> orange
    stops = np.array([[52.0, 36.0, 88.0], [142.0, 78.0, 96.0], [238.0, 146.0, 74.0]])
    pos = np.array([0.0, 0.55, 1.0])
    img = np.empty((H, W, 3), np.float64)
    for c in range(3):
        img[:, :, c] = np.interp(t, pos, stops[:, c])

    # sun glow low on the frame, plus a hot core
    sun = (0.60 * W, 0.74 * H)
    d2 = ((xx - sun[0]) ** 2 + (yy - sun[1]) ** 2)
    img += np.exp(-d2 / (2 * (0.16 * W) ** 2))[:, :, None] * np.array([54.0, 34.0, 6.0])
    img += np.exp(-d2 / (2 * (0.045 * W) ** 2))[:, :, None] * np.array([46.0, 40.0, 22.0])

    # horizontal cloud shelves in the mid-sky
    clouds = _value_noise(rng, H, W, 26, 5, 9.0) * np.exp(-((t - 0.42) / 0.22) ** 2)
    img += clouds[:, :, None] * np.array([1.0, 0.55, 0.75])[None, None, :]

    # silhouetted ridge with a lone tree; edges softened like real backlight
    ridge = np.zeros((H, W), np.uint8)
    ridge_y = (H * 0.82 + _value_noise(rng, 1, W, 1, 7, 22.0)[0]).astype(np.int32)
    for x in range(W):
        ridge[ridge_y[x]:, x] = 1
    tx = int(W * 0.24)
    ty = int(ridge_y[tx])
    cv2.rectangle(ridge, (tx - 4, ty - 78), (tx + 4, ty), 1, -1)          # trunk
    cv2.ellipse(ridge, (tx, ty - 96), (34, 30), 0, 0, 360, 1, -1)         # crown
    cv2.ellipse(ridge, (tx - 22, ty - 66), (18, 14), 0, 0, 360, 1, -1)
    cv2.ellipse(ridge, (tx + 24, ty - 70), (20, 15), 0, 0, 360, 1, -1)
    sil = _soft_mask(ridge, 1.1)[:, :, None]
    dark = np.array([26.0, 18.0, 30.0])[None, None, :] + (
        _value_noise(rng, H, W, 6, 8, 4.0)[:, :, None])
    img = img * (1 - sil) + dark * sil

    # one bird silhouette: two wing arcs
    bx, by = int(W * 0.42), int(H * 0.30)
    cv2.ellipse(img, (bx - 9, by), (11, 4), 24, 180, 300, (30, 22, 34), 3)
    cv2.ellipse(img, (bx + 9, by), (11, 4), -24, 240, 360, (30, 22, 34), 3)

    img += _grain(rng, H, W, 9.5, 4.5)
    return _finish(img)


# --- 5. specular chrome kettle -------------------------------------------------

def make_chrome_specular() -> np.ndarray:
    """Brushed-metal kettle on a dark studio sweep: vertical reflection
    bands, horizontal brushing, hard specular highlights that quantize as
    separate regions. RGB."""
    H, W = 620, 520
    rng = np.random.default_rng(20260815)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # studio sweep: dark radial falloff, slightly blue
    r2 = ((xx - W * 0.5) / W) ** 2 + ((yy - H * 0.38) / H) ** 2
    img = np.empty((H, W, 3), np.float64)
    img[:] = (64.0, 66.0, 74.0)
    img -= (r2 * 90.0)[:, :, None]
    img += _value_noise(rng, H, W, 6, 5, 3.5)[:, :, None]

    # kettle silhouette: dome body + lid knob + spout stub
    mask = np.zeros((H, W), np.uint8)
    body_c = (int(W * 0.52), int(H * 0.62))
    cv2.ellipse(mask, body_c, (int(W * 0.40), int(H * 0.34)), 0, 0, 360, 1, -1)
    cv2.ellipse(mask, (body_c[0], int(H * 0.34)), (int(W * 0.16), int(H * 0.07)),
                0, 0, 360, 1, -1)                                        # lid
    cv2.circle(mask, (body_c[0], int(H * 0.28)), 14, 1, -1)              # knob
    cv2.ellipse(mask, (int(W * 0.16), int(H * 0.52)), (46, 20), -35, 0, 360, 1, -1)

    # metal: mid gray + vertical environment reflections + horizontal brushing
    metal = np.empty((H, W, 3), np.float64)
    metal[:] = (150.0, 152.0, 156.0)
    bands = _value_noise(rng, H, W, 3, 22, 34.0)      # vertical reflection bands
    brush = cv2.GaussianBlur(
        _streak_noise(rng, H, W, _h_kernel(9), 26.0), (0, 0), 0.8)
    metal += (bands + brush)[:, :, None]
    # dark "room" reflection block on the right shoulder
    room = np.zeros((H, W), np.uint8)
    cv2.rectangle(room, (int(W * 0.60), int(H * 0.42)), (int(W * 0.78), int(H * 0.78)), 1, -1)
    metal -= _soft_mask(room, 5.0)[:, :, None] * 46.0
    # form shading: darker toward the silhouette edge
    edge = mask - cv2.erode(mask, np.ones((25, 25), np.uint8))
    metal -= _soft_mask(edge, 7.0)[:, :, None] * 40.0

    a = _soft_mask(mask, 0.9)[:, :, None]
    img = img * (1 - a) + metal * a

    # hard speculars: near-white, minimal blur, deliberately quantize apart
    spec = np.zeros((H, W), np.float32)
    cv2.ellipse(spec, (int(W * 0.38), int(H * 0.46)), (13, 42), 12, 0, 360, 1.0, -1)
    cv2.ellipse(spec, (int(W * 0.44), int(H * 0.33)), (22, 7), -8, 0, 360, 1.0, -1)
    cv2.circle(spec, (body_c[0] + 3, int(H * 0.275)), 4, 1.0, -1)
    cv2.ellipse(spec, (int(W * 0.63), int(H * 0.58)), (5, 26), 6, 0, 360, 0.8, -1)
    spec = cv2.GaussianBlur(spec, (0, 0), 1.2)[:, :, None]
    img = img * (1 - spec) + np.array([250.0, 250.0, 252.0])[None, None, :] * spec

    # contact shadow on the sweep
    contact = np.zeros((H, W), np.uint8)
    cv2.ellipse(contact, (body_c[0], int(H * 0.93)), (int(W * 0.30), 16), 0, 0, 360, 1, -1)
    img -= (_soft_mask(contact, 8.0) * (1 - a[:, :, 0]) * 30.0)[:, :, None]

    # metal micro-grain on the kettle only; the sweep stays smooth
    img += (rng.normal(0.0, 7.0, size=(H, W)) * a[:, :, 0])[:, :, None]
    img += _grain(rng, H, W, 7.0, 2.5)
    return _finish(img)


# --- entry points --------------------------------------------------------------

FIXTURES = {
    "photo_owl_pale.png": make_owl_pale,
    "photo_dof_meadow.png": make_dof_meadow,
    "photo_grass_macro.png": make_grass_macro,
    "photo_sunset_backlit.png": make_sunset_backlit,
    "photo_chrome_specular.png": make_chrome_specular,
}


def _classify_all(images: dict[str, np.ndarray]) -> None:
    from digitizer_core.config import PipelineConfig
    from digitizer_core.stage0_classify import classify

    cfg = PipelineConfig(target_width_mm=80.0)
    for name, rgb in images.items():
        # classify()'s ndarray path expects BGR (it mirrors cv2.imread), so
        # convert first — this makes --check byte-equivalent to classifying
        # the committed PNG by path.
        r = classify(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), cfg)
        sig = {k: round(v, 4) for k, v in r.signals.items()}
        print(f"{name}: {r.class_} conf={r.confidence:.3f} {sig}")


def main() -> None:
    check_only = "--check" in sys.argv[1:]
    images = {name: fn() for name, fn in FIXTURES.items()}
    _classify_all(images)
    if check_only:
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rgb in images.items():
        cv2.imwrite(str(OUT / name), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    for name in FIXTURES:
        f = OUT / name
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
