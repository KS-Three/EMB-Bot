"""`cfg.seam_hold_skips_outline_bodies` (ON, 2026-11-19): an outline's body sews as a
FILL, so `satin_seam_hold`'s cut tongue (#1641, which counts on satin rails carrying
the pull under the later colour) does not reach it.

The regression it repairs: Ahora (`testdata/art/commons_lettering/logo_ahora.png`)
at 80 mm left chest. #1594 (2026-11-15) made its white gear crisp; #1641 (2026-11-17)
cut the gold O's tongue under the gear from 22 mm^2 to none, the fill stopped round a
gear-shaped hole and its travel crossed it, bare yellow bars between the teeth. Kent:
"it was previously stitching out a nice gear just a day or two ago".
"""
import pytest

from digitizer_core.config import PipelineConfig
from tests.conftest import PRE_FLIP, TESTDATA

AHORA = TESTDATA / "art" / "commons_lettering" / "logo_ahora.png"


def test_default_is_on_and_false_is_the_1641_engine():
    assert PipelineConfig().seam_hold_skips_outline_bodies is True
    assert PRE_FLIP["seam_hold_skips_outline_bodies"] is False


@pytest.fixture(scope="module")
def ahora():
    from tools.eye_pairs.features import base_cfg, digitize_once

    def sew(**kw):
        return digitize_once(AHORA, base_cfg(80.0, "left_chest", **kw))[3]
    return sew


def test_ahora_gear_sews_as_it_did_before_the_hold(ahora):
    # The guard: with the repair ON, the hold leaves Ahora exactly as the hold OFF
    # sews it -- the gear #1594 made. Not a pinned md5: any later change that moves
    # both arms together keeps passing; one that brings the gap back fails here.
    assert ahora() == ahora(satin_seam_hold=False)


def test_without_the_repair_the_gold_o_moves(ahora):
    # the repair is what holds it: OFF, the hold still moves Ahora
    assert ahora(seam_hold_skips_outline_bodies=False) != ahora(satin_seam_hold=False)
