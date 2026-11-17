"""`cfg.extra["dark_ink_refuse_ground_gaps"]` (built OFF 2026-11-17).

The flat lane's dark-ink read keeps a thin dark component ringed by one
lighter ground. Light lettering on a dark field is that picture inside out:
the strip of field between two letters is thin, dark and ringed by one lighter
colour, and the US Forest Service shield at 80 mm sewed 13 of them as bean
lines in a second green. `thin_ink.refuse_ground_gaps` reads the quantiser's
labels: a component whose own label is the larger body the light shapes round
it sit on is the ground, not a stroke.
"""
import numpy as np

from digitizer_core.thin_ink import ThinInk, refuse_ground_gaps

FIELD, INK = 0, 1


def _thin(mask):
    labels = np.where(mask, 0, -1).astype(np.int32)
    return ThinInk(mask=mask, labels=labels, spools=[7], components=1, length_mm=1.0, dark=1)


def _light_letters_on_dark_field():
    """Two light bars on a dark field; the dark read is the strip between them."""
    labels = np.full((80, 120), FIELD, np.int32)
    labels[20:60, 30:50] = INK
    labels[20:60, 56:76] = INK
    gap = np.zeros(labels.shape, bool)
    gap[20:60, 50:56] = True
    return labels, gap


def _dark_letter_on_light_field():
    """A dark bar on a light field that fills the picture."""
    labels = np.full((80, 120), INK, np.int32)      # the light ground
    stroke = np.zeros(labels.shape, bool)
    stroke[20:60, 50:56] = True
    labels[stroke] = FIELD                           # the dark stroke's own cluster
    return labels, stroke


def test_field_between_light_letters_is_not_a_stroke():
    labels, gap = _light_letters_on_dark_field()
    assert refuse_ground_gaps(_thin(gap), labels, np.ones(labels.shape, bool)) is None


def test_counter_inside_a_light_letter_is_not_a_stroke():
    labels = np.full((80, 120), FIELD, np.int32)
    labels[20:60, 40:80] = INK
    counter = np.zeros(labels.shape, bool)
    counter[34:46, 56:62] = True
    labels[counter] = FIELD
    assert refuse_ground_gaps(_thin(counter), labels, np.ones(labels.shape, bool)) is None


def test_dark_letter_on_a_light_ground_is_kept():
    labels, stroke = _dark_letter_on_light_field()
    dark = _thin(stroke)
    assert refuse_ground_gaps(dark, labels, np.ones(labels.shape, bool)) is dark


def test_dark_letter_sharing_a_cluster_with_a_small_shape_is_kept():
    """Fremont's tagline shares its cluster with the rope: a dark body exists
    elsewhere, but the light ground round the letter is the larger one."""
    labels, stroke = _dark_letter_on_light_field()
    labels[2:8, 2:40] = FIELD                        # another dark shape, smaller than the ground
    dark = _thin(stroke)
    assert refuse_ground_gaps(dark, labels, np.ones(labels.shape, bool)) is dark


def test_stroke_lost_into_its_ground_is_kept():
    """The cartoon's letters: the quantiser gave the stroke its ground's label."""
    labels = np.full((80, 120), INK, np.int32)
    stroke = np.zeros(labels.shape, bool)
    stroke[20:60, 50:56] = True
    dark = _thin(stroke)
    assert refuse_ground_gaps(dark, labels, np.ones(labels.shape, bool)) is dark


def test_only_the_gaps_go_when_both_kinds_are_read():
    labels, gap = _light_letters_on_dark_field()
    # a light plate, larger than the field's remainder is not needed: a dark
    # stroke on a light shape that touches the page, not the field
    labels[:, 100:] = INK
    stroke = np.zeros(labels.shape, bool)
    stroke[10:70, 108:112] = True
    labels[stroke] = 2                               # its own dark cluster
    out = refuse_ground_gaps(_thin(gap | stroke), labels, np.ones(labels.shape, bool))
    assert out is not None
    assert out.mask[stroke].all() and not out.mask[gap].any()


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("dark_ink_refuse_ground_gaps")
