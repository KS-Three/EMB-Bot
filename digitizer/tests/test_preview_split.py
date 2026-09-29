"""`tools/pro_parity/preview_split.py` — recovering artwork from vendor previews.

The two tests that matter here run WITHOUT `scratch_kent/`, so CI sees them:
the refusal, and the slug invariant. The ones that need real vendor files skip
on a machine that does not carry them, the same way the OCR tests skip without
tesseract.
"""
import numpy as np
import pytest
from PIL import Image

from tools.pro_parity import prep_all, preview_split as ps

BECKER = "Becker Marine/Becker Hat & Polo Large/beckers logo hat.JPG"


def _have(rel: str) -> bool:
    return (ps.SCRATCH / rel).exists()


# ---- these two run everywhere, including CI ---------------------------------

def test_unlisted_source_is_refused_not_guessed():
    """The whole point of the manifest.

    `beckers logo hat.JPG` is two stitch simulations with no artwork in it.
    Both measured heuristics would have picked a panel anyway — flatness
    scores it 1.51, above a genuine artwork file at 1.84 — and handing a
    simulation to the pipeline as artwork is the provenance bug blockcensus
    guards (+11.3 points of flattery). So an unlisted source must raise, not
    return an array.
    """
    with pytest.raises(ps.NotInManifest):
        ps.extract(BECKER)
    assert BECKER not in ps.MANIFEST


def test_every_manifest_entry_names_a_real_pro_design():
    """A typo in a slug would silently produce an artwork file that pairs with
    nothing, and blockcensus would report it as "pro file missing" long after
    the fact. Catch it here instead."""
    slugs = {slug for slug, _path in prep_all.DESIGNS}
    for rel, (which, stem, slug) in ps.MANIFEST.items():
        assert slug in slugs, f"{rel} names unknown pro slug {slug!r}"
        assert which in ("first", "second"), f"{rel} has bad panel {which!r}"
        assert stem and not stem.endswith(".png"), f"{rel} stem should be bare: {stem!r}"
    stems = [stem for _w, stem, _s in ps.MANIFEST.values()]
    assert len(stems) == len(set(stems)), "two entries would write the same file"
    slugs_used = [slug for _w, _st, slug in ps.MANIFEST.values()]
    assert len(slugs_used) == len(set(slugs_used)), (
        "one pro file paired to two artworks would double-count in aggregates"
    )


# ---- these need the vendor files ---------------------------------------------

@pytest.mark.skipif(not _have("MFAB/Mfab Hat & Polo/mf4b logo hat.JPG"),
                    reason="scratch_kent vendor previews not present")
def test_stacked_preview_splits_horizontally():
    rel = "MFAB/Mfab Hat & Polo/mf4b logo hat.JPG"
    a = np.asarray(Image.open(ps.SCRATCH / rel).convert("RGB")).astype(int)
    axis, s, e = ps.find_gutter(a)
    assert axis == "H"
    assert 0 < s < e < a.shape[0]


@pytest.mark.skipif(not _have("To a T Machine/Machine beanie E.JPG"),
                    reason="scratch_kent vendor previews not present")
def test_side_by_side_preview_splits_vertically():
    """To a T Machine is the vendor that breaks the 'artwork is on top' rule —
    its panels sit side by side and the artwork is the RIGHT one. If this ever
    starts reporting "H", the manifest's "second" no longer means what it did."""
    rel = "To a T Machine/Machine beanie E.JPG"
    a = np.asarray(Image.open(ps.SCRATCH / rel).convert("RGB")).astype(int)
    axis, s, e = ps.find_gutter(a)
    assert axis == "V"
    assert 0 < s < e < a.shape[1]


@pytest.mark.skipif(not _have("MFAB/Mfab Hat & Polo/mf4b logo hat.JPG"),
                    reason="scratch_kent vendor previews not present")
def test_extracted_panel_is_a_strict_part_of_the_source():
    rel = "MFAB/Mfab Hat & Polo/mf4b logo hat.JPG"
    src = np.asarray(Image.open(ps.SCRATCH / rel).convert("RGB")).astype(int)
    art = ps.extract(rel)
    assert art.size > 0
    assert art.shape[0] < src.shape[0], "a panel must be shorter than the whole image"
    assert art.shape[1] == src.shape[1], "a horizontal split keeps full width"
    # Not blank: a gutter-only crop would be uniform background.
    assert len(np.unique(art.reshape(-1, 3), axis=0)) > 2
