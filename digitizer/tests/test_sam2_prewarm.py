"""`sam2_worker._ensure_checkpoint` must not cache a truncated download.

The failure this pins happened for real (2026-08-22, cloud container): a
proxy ended the checkpoint stream early WITHOUT an error — `read()`
returned b"" exactly as on genuine EOF — so `--prewarm` wrote 136.9 MB of
a 156.0 MB file, printed "checkpoint cached", and every later SAM2 job
died with torch's "failed finding central directory". The docstring's own
promise ("an interrupted or truncated download is never left behind
wearing the real filename") was violated by the one truncation mode
urllib does not surface as an exception. The fix enforces the server's
Content-Length.

`sam2_worker` is standalone by design (torch imports are lazy), so these
tests import it under the shared venv and fake the HTTP layer — no
network, no torch.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from digitizer_core import sam2_worker


class _FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, content_length: int | None):
        super().__init__(body)
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _prime(monkeypatch, tmp_path: Path, body: bytes, content_length: int | None):
    monkeypatch.setattr(sam2_worker, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        sam2_worker.urllib.request, "urlopen",
        lambda url, timeout: _FakeResponse(body, content_length),
    )


def test_truncated_stream_raises_and_caches_nothing(tmp_path, monkeypatch):
    _prime(monkeypatch, tmp_path, b"x" * 50, content_length=100)
    with pytest.raises(OSError, match="truncated: got 50 of 100"):
        sam2_worker._ensure_checkpoint("tiny")
    # Nothing wearing the real filename, and no orphaned .part either.
    assert list(tmp_path.iterdir()) == []


def test_complete_stream_is_cached(tmp_path, monkeypatch):
    _prime(monkeypatch, tmp_path, b"x" * 100, content_length=100)
    dest = sam2_worker._ensure_checkpoint("tiny")
    assert dest.parent == tmp_path and dest.stat().st_size == 100
    assert not list(tmp_path.glob("*.part"))


def test_no_content_length_keeps_the_old_nonempty_check(tmp_path, monkeypatch):
    """A server that sends no Content-Length gets the pre-fix behavior —
    the guard cannot enforce a number it was never given."""
    _prime(monkeypatch, tmp_path, b"x" * 60, content_length=None)
    dest = sam2_worker._ensure_checkpoint("tiny")
    assert dest.stat().st_size == 60
