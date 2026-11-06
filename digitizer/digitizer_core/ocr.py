"""One Tesseract for the digitizer.

Every OCR read in `digitizer_core` and `tools/` goes through this module. It
runs Tesseract IN PROCESS through `tesserocr` when that wheel and a tessdata
directory are present, and falls back to the `tesseract` child process through
`pytesseract` otherwise. Same model (`eng.traineddata`), same page-segmentation
modes, same `{"text": [...], "conf": [...]}` shape as
`pytesseract.image_to_data(..., output_type=DICT)` for the two keys the
callers read.

Why (2026-11-06, `docs/external-repo-sourcing-2026-11-06.md`): `pytesseract`
spawns `tesseract.exe`, writes a PNG and parses a TSV per call. Measured on
Becker's chest logo cut into 48 crops, same tessdata, laptop idle:
psm 10 **251 ms -> 5 ms per read**, psm 7 185 -> 4 ms. Eight call sites paid
that (the glyph tagger, the legibility gate, the calibration reader), and the
2026-10-26 "batch four tesseract processes at a time" was a workaround for the
process start, not a fix. In-process the start is paid once per thread, for
the life of the process.

What moves: the wheel bundles its own Tesseract (5.5.3 for tesserocr 2.12.0)
where Kent's box runs 5.4.0 and CI's apt gives 5.3.4 — so every OCR-derived
number (lettering-board cc, legibility confidence, `ocr_char`) can shift once,
on the box and in CI together. `version()` says which engine read, and the
boards record it in their meta.

Threads: `tesserocr` releases the GIL inside `Recognize`, and one
`PyTessBaseAPI` must not be shared across threads — so each thread gets its
own, created on first use and kept (`threading.local`). The bundled Tesseract
is built without OpenMP (its `--version` names no OpenMP), so the one-thread
guard the subprocess path needed (`textcluster._one_tesseract_thread`) is
inert here and harmless.

Override: `EMB_OCR_ENGINE=pytesseract` forces the child-process path (the
before/after lever for a board comparison); `EMB_OCR_ENGINE=tesserocr` refuses
to fall back (so a CI job cannot go quietly slow).
"""
from __future__ import annotations

import os
import shutil
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np

ENGINE_ENV = "EMB_OCR_ENGINE"
LANG = "eng"

_TESSDATA_CANDIDATES = (
    "/usr/share/tesseract-ocr/5/tessdata",      # apt tesseract-ocr on Ubuntu 22.04+ (CI)
    "/usr/share/tesseract-ocr/4.00/tessdata",   # older apt
    "/usr/share/tessdata",
    "/usr/local/share/tessdata",
    "/opt/homebrew/share/tessdata",             # brew on Apple silicon
    "/usr/local/share/tesseract-ocr/tessdata",
)


def _has_lang(d: str | os.PathLike | None) -> bool:
    return bool(d) and (Path(d) / f"{LANG}.traineddata").is_file()


@lru_cache(maxsize=1)
def tessdata_dir() -> str | None:
    """The directory holding `eng.traineddata`, or None. `TESSDATA_PREFIX`
    first (the directory itself or its `tessdata/` child), then the installed
    `tesseract` binary's own `tessdata/` (the Windows installer's layout),
    then the usual apt / brew places."""
    env = os.environ.get("TESSDATA_PREFIX")
    if env:
        for d in (env, os.path.join(env, "tessdata")):
            if _has_lang(d):
                return d
    exe = shutil.which("tesseract")
    if exe:
        beside = Path(exe).resolve().parent
        for d in (beside / "tessdata", beside.parent / "share" / "tessdata",
                  beside.parent / "share" / "tesseract-ocr" / "tessdata"):
            if _has_lang(d):
                return str(d)
    for d in _TESSDATA_CANDIDATES:
        if _has_lang(d):
            return d
    return None


@lru_cache(maxsize=1)
def _tesserocr():
    try:
        import tesserocr  # noqa: F401
    except Exception:  # ImportError, or a wheel whose bundled DLLs failed to load
        return None
    return tesserocr


@lru_cache(maxsize=1)
def engine() -> str | None:
    """`"tesserocr"`, `"pytesseract"` or None (no OCR possible)."""
    want = os.environ.get(ENGINE_ENV, "").strip().lower()
    if want == "tesserocr":
        return "tesserocr" if _tesserocr() is not None and tessdata_dir() else None
    if want == "pytesseract":
        return "pytesseract" if shutil.which("tesseract") else None
    if _tesserocr() is not None and tessdata_dir():
        return "tesserocr"
    if shutil.which("tesseract"):
        return "pytesseract"
    return None


def available() -> bool:
    return engine() is not None


def reset() -> None:
    """Forget the cached engine choice (tests that flip `EMB_OCR_ENGINE`)."""
    engine.cache_clear()
    version.cache_clear()
    tessdata_dir.cache_clear()
    _tesserocr.cache_clear()
    _local.__dict__.clear()


@lru_cache(maxsize=1)
def version() -> str | None:
    """A line naming the engine AND the Tesseract it carries, e.g.
    `tesseract v5.5.3 (tesserocr 2.12.0, in-process)` or
    `tesseract v5.4.0.20240606 (pytesseract, subprocess)`. The boards put
    this in their meta, so a cc that moved can be read against the engine
    that read it."""
    e = engine()
    if e == "tesserocr":
        t = _tesserocr()
        tv = t.tesseract_version().splitlines()[0].strip().replace("tesseract ", "tesseract v", 1)
        return f"{tv} ({'tesserocr'} {t.__version__}, in-process)"
    if e == "pytesseract":
        import subprocess
        try:
            r = subprocess.run(["tesseract", "--version"], capture_output=True, text=True)
            line = (r.stdout or r.stderr).splitlines()[0].strip()
        except (OSError, IndexError):
            line = "tesseract"
        return f"{line} (pytesseract, subprocess)"
    return None


# --- the in-process API, one per thread ---------------------------------------

_local = threading.local()


def _api():
    api = getattr(_local, "api", None)
    if api is None:
        t = _tesserocr()
        api = t.PyTessBaseAPI(path=tessdata_dir(), lang=LANG)
        _local.api = api
    return api


def _pil(img):
    from PIL import Image
    if isinstance(img, Image.Image):
        return img
    a = np.asarray(img)
    if a.ndim == 3 and a.shape[2] == 3:
        return Image.fromarray(a[:, :, ::-1])      # OpenCV hands BGR
    return Image.fromarray(a)


def _read_words(img, psm: int) -> tuple[list[str], list[float]]:
    t = _tesserocr()
    api = _api()
    api.SetPageSegMode(int(psm))
    api.SetImage(_pil(img))
    api.Recognize()
    texts: list[str] = []
    confs: list[float] = []
    it = api.GetIterator()
    if it is None:
        return texts, confs
    level = t.RIL.WORD
    for r in t.iterate_level(it, level):
        try:
            word = r.GetUTF8Text(level)
        except RuntimeError:  # an empty cell at this level
            word = ""
        texts.append((word or "").strip())
        confs.append(float(r.Confidence(level)))
    return texts, confs


# --- the two reads every caller uses --------------------------------------------

def image_to_data(img, psm: int) -> dict:
    """Word-level read -> `{"text": [...], "conf": [...]}`: one entry per
    word Tesseract found, `conf` 0..100. Through pytesseract the dict is
    pytesseract's own (it also carries `-1` rows for the non-word levels and
    the box columns); callers filter `conf >= 0`, so both shapes read the
    same. Raises on an engine failure — every caller already catches and
    fails open, that contract is theirs."""
    e = engine()
    if e == "tesserocr":
        texts, confs = _read_words(img, psm)
        return {"text": texts, "conf": confs}
    if e == "pytesseract":
        import pytesseract
        return pytesseract.image_to_data(_pil(img), config=f"--psm {int(psm)}",
                                         output_type=pytesseract.Output.DICT)
    raise RuntimeError("no OCR engine: neither tesserocr+tessdata nor a tesseract binary")


def image_to_string(img, psm: int) -> str:
    e = engine()
    if e == "tesserocr":
        api = _api()
        api.SetPageSegMode(int(psm))
        api.SetImage(_pil(img))
        return api.GetUTF8Text()
    if e == "pytesseract":
        import pytesseract
        return pytesseract.image_to_string(_pil(img), config=f"--psm {int(psm)}")
    raise RuntimeError("no OCR engine: neither tesserocr+tessdata nor a tesseract binary")


def words(img, psm: int) -> tuple[str, float]:
    """`image_to_data` folded the way `legibility.ocr` and
    `word_legibility._tsv_reads` fold it: the words joined by one space and
    the mean confidence over them; a read with no word is `("", 0.0)`."""
    data = image_to_data(img, psm)
    got = [(w.strip(), float(c)) for w, c in zip(data["text"], data["conf"])
           if w and w.strip() and float(c) >= 0]
    if not got:
        return "", 0.0
    return " ".join(w for w, _c in got), sum(c for _w, c in got) / len(got)
