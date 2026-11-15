"""The outline-body vote's guard (`cfg.group_consistent_outline_body`, held OFF
by Kent 2026-11-14, "G4 alone looks the best").

With `outline_redraw_k` 0.75 beside it, MFab hat's small line (113.5 mm, the
Studio hat config) turned into thick white keyline loops over its black
letters. Each flag alone read clean. Traced: the vote is taken at stage 7 over
a line of like candidates. Without the redraw its ink read 2.54x to the
ladder side, so ink decided "not bodies". The re-fit moved two letters' own
readings, the ink fell to 1.46x (inside `MARGIN`), and the width tie-break
decided "bodies" on a 3.4% difference. Then 5 of 8 and 3 of 4 small letters
were keyline bodies, their words stopped riding the white panel
(`silhouette_underfill.find_riders`: 12 riders -> 0), and the colour order
lost its last black block.

The guard: the width tie-break needs one side wider by more than `MARGIN`,
the module's own bar for evidence; else no verdict and each member keeps its
own call. AHORA, the case the flag is for, is decided by ink (3.42x) and
never reaches it.
"""
from __future__ import annotations

import cv2
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import group_consistency as gc
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches

from .conftest import TESTDATA
from .test_group_consistency import _word


def test_a_near_tie_in_width_is_no_verdict():
    word = _word([3, 3, 3, 3])                       # 42 mm^2 each: ink 84 vs 84
    own = {"L0": True, "L1": True, "L2": False, "L3": False}
    # MFab's plan-stage reading under the redraw: 1.336 against 1.292 mm
    stroke = {"L0": 1.336, "L1": 1.336, "L2": 1.292, "L3": 1.292}
    assert gc.outline_side(word, own, stroke) is None
    # exactly MARGIN apart is still not MORE than it
    stroke = {"L0": 3.0, "L1": 3.0, "L2": 2.0, "L3": 2.0}
    assert gc.outline_side(word, own, stroke) is None


def test_ink_past_the_margin_still_decides_whatever_the_widths():
    word = _word([3, 3, 3, 3])
    own = {"L0": True, "L1": False, "L2": False, "L3": False}       # 42 vs 126
    stroke = {"L0": 1.0, "L1": 1.0, "L2": 1.0, "L3": 1.0}
    assert gc.outline_side(word, own, stroke) is False


def _mfab_113(**kw):
    cfg = PipelineConfig(photo_prep=False, target_width_mm=113.5, max_colors=6, satin=True,
                         detail_layer=False, edge_cap="none", sew_enclosed_white=True,
                         sew_enclosed_rgb=(255, 255, 255), faces_route_flat=True,
                         garment_id="hat_front", garment_rgb=(235, 232, 223), **kw)
    pix = cv2.imread(str(TESTDATA / "art" / "logo_mfab_hat.png"), cv2.IMREAD_UNCHANGED)
    plan = plan_stitches(finish_generation(build_generation(pix, cfg), cfg), cfg)
    return [c["name"] for c in plan_to_design(plan, name="t")["colors"]]


@pytest.mark.parametrize("redraw", [None, 0.75], ids=["no-redraw", "redraw-0.75"])
def test_mfab_hat_small_line_still_rides_with_the_body_vote_on(redraw):
    assert _mfab_113(group_consistent_outline_body=True, outline_redraw_k=redraw) == \
        ["0020 Black", "0015 White", "0020 Black"]
