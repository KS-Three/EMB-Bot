"""`tools/delivery_jpeg.py`'s pure helpers: the delivery a customer's file
goes through, and the cone diff. No digitize here — the sweep itself is a
measurement, not a test."""
import cv2
import numpy as np

from tools import delivery_jpeg as dj


def test_alpha_is_flattened_onto_white_as_a_jpeg_export_does():
    raw = np.zeros((4, 4, 4), np.uint8)
    raw[..., :3] = (0, 0, 255)            # BGR red
    raw[:2, :, 3] = 255                    # top half opaque, bottom transparent
    out = dj.flatten_on_white(raw)
    assert out.shape == (4, 4, 3)
    assert (out[:2] == (0, 0, 255)).all()
    assert (out[2:] == 255).all()


def test_flat_white_is_lossless_and_jpeg_is_not():
    rng = np.random.default_rng(0)
    raw = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
    assert (dj.deliver(raw, dj.DELIVERIES["flat_white"]) == raw).all()
    assert not (dj.deliver(raw, dj.DELIVERIES["q30"]) == raw).all()


def test_double_save_compounds_and_thumb_shrinks():
    raw = np.full((50, 100, 3), 200, np.uint8)
    cv2.circle(raw, (50, 25), 15, (20, 40, 160), -1)
    assert dj.deliver(raw, dj.DELIVERIES["thumb"]).shape == (30, 60, 3)
    assert dj.deliver(raw, dj.DELIVERIES["q75x2"]).shape == raw.shape


def test_cone_diff_counts_threads_outside_the_same_colour_tolerance():
    black, white, red = [0, 0, 0], [255, 255, 255], [200, 0, 0]
    assert dj.cone_diff([black, white], [black, white]) == (0, 0)
    assert dj.cone_diff([black, white], [[10, 10, 10], white]) == (0, 0)
    assert dj.cone_diff([black, white], [black, white, red]) == (1, 0)
    assert dj.cone_diff([black, white, red], [black]) == (0, 2)
