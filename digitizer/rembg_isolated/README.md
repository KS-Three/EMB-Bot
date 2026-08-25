# Isolated rembg venv (photo plan §2 row 1 — background removal)

`rembg` cannot be imported inside the shared `digitizer/.venv`: it depends on
`pymatting`, which depends on `numba`, and `numba` refuses to import next to
numpy 2.5 (`ImportError: Numba needs NumPy 2.4 or less`) — the shared venv
pins `numpy==2.5.1` for the k-means goldens and that pin is not negotiable
for a background-removal dependency (docs/photo-prep-deps-probe-2026-08-04.md
§2 has the full probe record).

The fix shipped here is option 2 from that probe doc: run rembg in its OWN
venv, with its own numpy, and talk to it as a subprocess. Nothing in
`digitizer/.venv` changes.

`digitizer_core/stage1_photo_prep.remove_background_seam` shells out to
`digitizer_core/rembg_worker.py` (a standalone script — no `digitizer_core`
imports, so it needs nothing installed here but `rembg` and its own deps),
running it under THIS directory's venv's python interpreter, never the
shared one.

## Build it

From the repo's `digitizer/` directory:

```
python3.12 -m venv rembg_isolated/venv
rembg_isolated/venv/bin/pip install -r rembg_isolated/requirements.txt        # POSIX
rembg_isolated\venv\Scripts\pip install -r rembg_isolated\requirements.txt    # Windows
```

That's it — no digitizer_core install needed in this venv (the worker script
is standalone by design). `stage1_photo_prep.py` looks for the interpreter at
`rembg_isolated/venv/bin/python` (POSIX) or `rembg_isolated/venv/Scripts/python.exe`
(Windows) by default; nothing else to configure.

**This venv is NOT committed** (`.venv/`-style — see `digitizer/.gitignore`)
and is a **required** deploy-time setup step, the same shape as building
`digitizer/.venv` itself — Kent's ruling 2026-08-24, the day
`photo_prep_background_removal` became a shipped default rather than an
opt-in.

Without it built, `photo_prep_background_removal` degrades to
`PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE` and the job completes on the plain
classical route. **Note what changed there**: this file used to say "the
rest of the pipeline, including every other `photo_prep` feature, is
unaffected", and that is no longer true. Tone prep, texture kill and the
YuNet face priors are now skipped WITH the cutout, deliberately — prep
without the cutout is the worst arm the acceptance harness measures, worse
than doing nothing on all four portraits (`baby_deck_laugh`: 110 -> 175
regions and 17,167 -> 32,663 stitches against no prep at all), so failing
onto it was failing in the expensive direction. See
`pipeline.build_generation`'s `cutout_requested` / `cutout_failed`.

An explicit `photo_prep=True` with `photo_prep_background_removal=False` is
untouched by any of this: that asks for prep alone and still gets exactly
prep alone.

CI does NOT build this venv, so CI exercises the fallback path rather than
the cutout. That is intentional — the fallback is the shipped behaviour on
a box without the venv, and it deserves the coverage — but it means a green
CI run is not evidence about the cutout itself. The tests that do cover it
carry `requires_rembg`-style skips (`tests/test_background_removal.py`).

## The model

`isnet-general-use.onnx` (178 MB, the plan's default background-removal
tier) is **not committed either** — at 178 MB it is well past the "couple
hundred KB" line `digitizer_core/model_data/README.md` draws for committed
inference models. rembg downloads it itself, on first real use, from
`github.com/danielgatis/rembg/releases/...` into its own cache dir
(`~/.u2net/` by default, or wherever the `U2NET_HOME` env var points — the
SAME cache location any rembg install on the machine uses, not something
this repo manages). That download worked cleanly through this sandbox's
proxy when probed (2026-08-04) and again while building this slice: ~10s for
the file itself. Every call after the first reuses the cached model, no
network needed (measured: sub-2s inference on a 512x512 image once cached).

If the machine building this venv has no route to GitHub release assets, the
first real job pays for it as a slow/failed subprocess call — which the
`photo_prep_background_removal_timeout_s` config knob bounds, and which
still degrades to the no-op fallback rather than failing the job outright.
Pre-warming the cache ahead of time (running the worker once by hand against
any image) is the fix, not something this repo needs to script.

## Sanity-check it by hand

```
rembg_isolated/venv/bin/python digitizer_core/rembg_worker.py \
    testdata/photo/enthusiast_logo.png /tmp/mask.png
```

Exit code 0 and a grayscale PNG at `/tmp/mask.png` (255 = subject, 0 =
background) means the venv and model cache are both working.
