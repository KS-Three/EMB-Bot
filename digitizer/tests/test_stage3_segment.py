"""Stage 3 — `RegionMask`'s cropped storage and its coordinate algebra.

The class carries a bbox-tight crop plus an origin instead of a frame-sized
bool, which is what took the pipeline's peak from 8.5 GB to ~1.0 GB at
2800x2100. Everything here pins the arithmetic that makes a crop equivalent
to the frame mask it replaced: an off-by-one in `window`, `frame_slice` or
`union_from` would move geometry silently rather than raise.
"""
from __future__ import annotations

import numpy as np

from digitizer_core.config import PipelineConfig

# --- RegionMask crop storage (2026-08-24) ------------------------------------
#
# Full-frame per-region masks were the pipeline's memory ceiling: a 2800x2100
# frame produces 1,455 components before the small-region policy culls them to
# ~102, and holding a frame-sized bool for each cost 8.56 GB — the entire
# measured peak. Cropped, the same 1,455 come to 26.8 MB. These pin the
# coordinate algebra that makes the crop equivalent to the frame it replaced,
# because a silent off-by-one here would move geometry, not crash.

def _rm(frame_shape, box, layer=0):
    """A RegionMask covering `box` = (y0, x0, y1, x1) of a `frame_shape` frame."""
    from digitizer_core.stage3_segment import RegionMask
    m = np.zeros(frame_shape, bool)
    y0, x0, y1, x1 = box
    m[y0:y1, x0:x1] = True
    return RegionMask.from_full(m, layer=layer), m


def test_crop_round_trips_through_full_mask_and_reports_frame_geometry():
    """`from_full` -> `full_mask` is the identity, and `area`/`bbox` describe
    the footprint in FRAME coordinates, not crop-local ones."""
    rm, m = _rm((40, 50), (7, 11, 19, 23))

    assert rm.crop.shape == (12, 12)
    assert rm.origin == (7, 11)
    assert rm.frame_shape == (40, 50)
    assert rm.bbox == (7, 11, 19, 23)
    assert rm.area == int(m.sum()) == 144
    assert np.array_equal(rm.full_mask(), m)


def test_window_reads_frame_coordinates_and_clips_outside_the_crop():
    """`window` is what let the halo/neighbour tests keep frame coordinates
    without materializing a frame, so it has to agree with the old
    `mask[wy0:wy1, wx0:wx1]` for every window — overlapping, containing,
    partial, and fully disjoint."""
    rm, m = _rm((40, 50), (7, 11, 19, 23))

    for win in [(0, 0, 40, 50),        # whole frame
                (7, 11, 19, 23),       # exactly the bbox
                (0, 0, 10, 15),        # clips the top-left corner
                (15, 20, 30, 40),      # clips the bottom-right corner
                (10, 14, 14, 18),      # strictly inside
                (0, 0, 5, 5),          # disjoint, before
                (30, 40, 40, 50)]:     # disjoint, after
        wy0, wx0, wy1, wx1 = win
        assert np.array_equal(rm.window(wy0, wx0, wy1, wx1),
                              m[wy0:wy1, wx0:wx1]), f"window {win}"


def test_frame_slice_indexes_a_frame_array_like_the_old_boolean_mask():
    """`frame[rm.frame_slice()][rm.crop]` replaced `frame[rm.mask]` at every
    fancy-indexing site in stage 2 — including a WRITE, which only works
    because basic slicing yields a view."""
    rm, m = _rm((12, 14), (3, 4, 8, 10))
    frame = np.arange(12 * 14, dtype=np.int32).reshape(12, 14)

    assert np.array_equal(frame[rm.frame_slice()][rm.crop], frame[m])

    a, b = np.zeros((12, 14), np.int32), np.zeros((12, 14), np.int32)
    a[rm.frame_slice()][rm.crop] = 7      # the view write the port relies on
    b[m] = 7
    assert np.array_equal(a, b)


def test_union_from_merges_in_place_and_grows_the_crop():
    """Absorption is the one post-construction mutation, and it MUST land in
    place: `resolve_small_regions` keeps index-parallel `areas`/`boxes` and
    re-reads the absorbing region through them. A property returning a fresh
    array here would have dropped every absorb silently, which is why
    `.mask` was removed outright rather than reimplemented."""
    a, ma = _rm((30, 30), (2, 2, 6, 6))
    b, mb = _rm((30, 30), (20, 21, 26, 28))
    before = id(a)

    a.union_from(b)

    assert id(a) == before, "must mutate in place, not rebind"
    assert np.array_equal(a.full_mask(), ma | mb)
    assert a.bbox == (2, 2, 26, 28)
    assert a.area == int((ma | mb).sum())


def test_union_from_a_contained_region_leaves_the_crop_alone():
    """The fast path: absorbing something already inside the bbox must not
    reallocate, and must still OR the pixels in."""
    a, ma = _rm((30, 30), (5, 5, 25, 25))
    b, mb = _rm((30, 30), (10, 10, 12, 12))
    a.crop[:] = False                      # so the union is observable
    a.crop[5, 5] = True

    a.union_from(b)

    assert a.origin == (5, 5) and a.crop.shape == (20, 20)
    assert np.array_equal(a.full_mask()[10:12, 10:12], mb[10:12, 10:12])


def test_an_empty_mask_keeps_total_geometry_rather_than_a_zero_length_crop():
    """`resolve_small_regions` asks every region for area and bbox, including
    ones quantization left empty. A 0x0 crop would make the window arithmetic
    partial; a 1x1 at the origin keeps it total and area still reads 0."""
    from digitizer_core.stage3_segment import RegionMask
    rm = RegionMask.from_full(np.zeros((16, 18), bool), layer=0)

    assert rm.area == 0
    assert rm.crop.shape == (1, 1)
    assert rm.bbox == (0, 0, 1, 1)
    assert not rm.full_mask().any()
    assert not rm.window(0, 0, 16, 18).any()


def test_classical_segmenter_crops_every_component_it_emits():
    """The producer's own contract: components come back cropped, carrying the
    frame they belong to, and reconstructing them reproduces the layer."""
    from digitizer_core.stage2_quantize import Quant
    from digitizer_core.stage3_segment import ClassicalSegmenter

    labels = np.zeros((20, 24), np.int32)
    labels[2:6, 3:9] = 1          # one component on layer 1
    labels[14:18, 15:22] = 1      # a second, disjoint
    quant = Quant(labels=labels, thread_indices=[0, 1],
                  cluster_rgb=np.zeros((2, 3), np.float64))

    out = ClassicalSegmenter().segment(quant, None, PipelineConfig())
    layer1 = [rm for rm in out if rm.layer == 1]

    assert len(layer1) == 2
    for rm in layer1:
        assert rm.frame_shape == (20, 24)
        # bbox-tight: every border row and column of the crop carries a pixel
        assert rm.crop.any(axis=1)[0] and rm.crop.any(axis=1)[-1]
        assert rm.crop.any(axis=0)[0] and rm.crop.any(axis=0)[-1]
    union = np.zeros((20, 24), bool)
    for rm in layer1:
        union |= rm.full_mask()
    assert np.array_equal(union, labels == 1)
