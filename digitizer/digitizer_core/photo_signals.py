"""Is this artwork a PHOTOGRAPH? — the two signals the repo already owns.

Quality review 2026-09-08 item 13. `config.is_photographic` decides whether
the photographic machinery applies (the palette resnap bind, the shade bind,
preflight's photo yardstick), and it is DECLARED today because **stage 0's
colour signals cannot answer it**: measured 2026-08-25, a real photograph
reads LESS photographic than several gradient logos on `unique_color_mass`,
stage 0's primary photo gate (owl_kent 0.1107 against summit_badge 0.1152
and drone_render 0.1592). Re-tuning that gate is both futile and stage-0
recalibration, which ROADMAP gate 2 refuses without real tonal artwork.

**Two signals that are not colour statistics do separate them** (DOCTRINE
2026-08-25, PR #245): EXIF camera Make/Model (4/4 photos, 0/9 logos) and the
YuNet detector already shipped at `stage1_photo_prep.detect_faces_seam`
(4/4 portraits, 0/9 logos). Each has a blind spot — EXIF dies on re-save
(`owl_kent.jpg` carries none), faces miss pets and landscapes — so the route
is **EXIF-or-face, with the declaration as the fallback**, never a checkbox
as the primary mechanism.

## What this module promises, and what it deliberately does not

`detect(...)` returns **True or None. Never False.** A signal that fires
says "photograph"; silence says "no opinion", because the corpus contains a
real photograph neither signal catches (`owl_kent.jpg`: re-saved, so no
EXIF, and an owl, so no face). Returning False there would be a claim the
evidence does not support, and it would suppress machinery on exactly the
designs that need it. So detection can only ever ADD photographs, which is
also why turning it on cannot change a design no signal fires on.

Precedence, implemented by `config.is_photographic`: an explicit
declaration wins (the person uploading knows, and an explicit False must
stay a suppression), then detection, then the class.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

# EXIF tag ids, from the TIFF spec — `PIL.ExifTags.TAGS` maps these names,
# but the ids are stable and reading them directly costs no import.
_EXIF_MAKE = 0x010F
_EXIF_MODEL = 0x0110


@dataclass(frozen=True)
class PhotoSignals:
    """What each signal said, so a caller can report WHY, not just what."""

    exif_camera: str | None = None      # "Make Model", or None
    faces: int | None = None            # None = the detector could not run
    face_reason: str | None = None      # why not, when `faces` is None

    @property
    def is_photograph(self) -> bool | None:
        """True when a signal fired; None when none did — never False.
        See the module docstring: silence is no opinion, not a denial."""
        if self.exif_camera:
            return True
        if self.faces:
            return True
        return None

    @property
    def signal(self) -> str | None:
        """Which one fired: "exif", "face", or None. The warning's `signal`
        key — a UI switches on this, never on `why`'s prose."""
        if self.exif_camera:
            return "exif"
        if self.faces:
            return "face"
        return None

    @property
    def why(self) -> str:
        if self.exif_camera:
            return f"EXIF camera {self.exif_camera!r}"
        if self.faces:
            return f"{self.faces} face(s) detected"
        if self.faces is None and self.face_reason:
            return f"no EXIF camera; face detection unavailable ({self.face_reason})"
        return "no EXIF camera, no face detected"


def exif_camera(image: str | Path | bytes | np.ndarray) -> str | None:
    """The camera that took it: "Make Model" from EXIF, or None.

    An ndarray never has EXIF — it is already decoded — and neither does a
    file a designer exported. **A re-save strips it**, which is why this is
    half a route and not the route: `owl_kent.jpg` is a real photograph with
    no EXIF at all.

    Never raises: a corrupt header, a format PIL cannot open, or a missing
    Pillow all read as "no camera", because a detection signal that can take
    the pipeline down is worse than one that stays quiet.
    """
    if isinstance(image, np.ndarray):
        return None
    try:
        from PIL import Image
        src = io.BytesIO(image) if isinstance(image, (bytes, bytearray)) else str(image)
        with Image.open(src) as im:
            tags = im.getexif()
        make = (tags.get(_EXIF_MAKE) or "").strip() if tags else ""
        model = (tags.get(_EXIF_MODEL) or "").strip() if tags else ""
    except Exception:                    # noqa: BLE001 — see the docstring
        return None
    name = " ".join(p for p in (make, model) if p)
    return name or None


def detect(image: str | Path | bytes | np.ndarray,
           rgb: np.ndarray | None = None,
           cfg=None) -> PhotoSignals:
    """Both signals, cheapest first.

    `rgb` is the prep raster the face detector runs on; without it only EXIF
    is read (the caller has no pixels yet, or does not want to pay for the
    detector). **EXIF short-circuits**: once it says photograph, running
    YuNet cannot change the answer and is pure cost.
    """
    cam = exif_camera(image)
    if cam:
        return PhotoSignals(exif_camera=cam)
    if rgb is None:
        return PhotoSignals()
    from .stage1_photo_prep import detect_faces_seam, face_detector_unavailable_reason
    faces = detect_faces_seam(rgb, cfg)
    if faces is None:
        return PhotoSignals(faces=None, face_reason=face_detector_unavailable_reason())
    return PhotoSignals(faces=len(faces))


def apply_detection(cfg, detected: bool):
    """Fold a detection verdict into a config — the one-line seam.

    `build_generation` resolves the signals once and carries the verdict on
    the `Generation` (and then the `PipelineResult`) the way stage 0's class
    and stage 1.5's `faces_present` are already carried: they are runtime
    facts only that pass can answer, and `finish_generation`, `plan_stitches`
    and preflight each arrive later holding the CALLER's config. Each folds
    the verdict in here, so all nine `config.is_photographic()` call sites
    keep reading one field and none of them learns that detection exists.

    Only ever writes True, and only into a config that declared nothing —
    "the caller said no" outranks every signal (see `config.is_photographic`).
    """
    if not detected or cfg.is_photographic is not None:
        return cfg
    return replace(cfg, is_photographic=True)


def resolve(cfg, *, image=None, rgb=None):
    """Run the signals if asked to, and hand back (config, signals).

    Returns `(cfg, None)` — the same config object, untouched — whenever
    detection did not run: the flag is off, or the caller already declared an
    answer and a declaration wins either way, so paying for the signals could
    only produce a verdict nothing may act on.

    `image` is the UNDECODED artwork, the only thing EXIF survives in: an
    ndarray has no header left, which is why the service hands its upload
    bytes down past its own decode. `rgb` is the prep raster the face pass
    runs on, RGB per stage 1's contract (`detect_faces_seam` converts to the
    BGR its detector was trained on itself). Without either, the answer is
    simply no opinion.

    Cost, measured 2026-09-11 across the 15-fixture corpus: EXIF alone
    0.4-50.8 ms; EXIF plus the face pass 0.03-0.14 s, against preps of
    0.04-1.10 s. EXIF short-circuits, so a photo that kept its header never
    pays for the detector.
    """
    if not cfg.detect_photographic or cfg.is_photographic is not None:
        return cfg, None
    signals = detect(image, rgb=rgb, cfg=cfg) if image is not None or rgb is not None \
        else PhotoSignals()
    return apply_detection(cfg, bool(signals.is_photograph)), signals
