"""Stage 0's texture route and two-ink veto (`cfg.stage0_texture_gate`).

Spec: `docs/superpowers/specs/2026-10-28-stage0-photo-texture-gate-design.md`.
Every fixture reading pinned here is an instrument reading on a real file,
not a quality claim (ROADMAP gate 4); the arrays built in-line check
arithmetic only and calibrate nothing (gate 2).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from digitizer_core.config import PipelineConfig

from .conftest import ENGINE_2026_10_27

HERE = Path(__file__).resolve().parent
TESTDATA = HERE.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"


def cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- Task 1: the flag ----------------------------------------------------------

def test_the_flag_defaults_on():
    assert PipelineConfig().stage0_texture_gate is True


def test_the_frozen_snapshot_holds_the_pre_flip_value():
    """A pin built on the dated engine must not ride this flip
    (`tests/test_pins_are_frozen.py`, rule 2)."""
    assert ENGINE_2026_10_27["stage0_texture_gate"] is False
