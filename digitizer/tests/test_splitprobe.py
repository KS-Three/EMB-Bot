import numpy as np

from tools.pro_parity.splitprobe import classify_straddle

# Cell grids: 1 = pro satin, 2 = pro fill, -1 = outside the shape.


def _grid(rows):
    return np.array(rows, dtype=int)


def test_ring_of_satin_around_fill_core_reads_ring():
    g = _grid([[1, 1, 1, 1, 1],
               [1, 2, 2, 2, 1],
               [1, 2, 2, 2, 1],
               [1, 2, 2, 2, 1],
               [1, 1, 1, 1, 1]])
    assert classify_straddle(g) == "ring"


def test_side_by_side_partition_reads_split():
    g = _grid([[1, 1, 2, 2, 2],
               [1, 1, 2, 2, 2],
               [1, 1, 2, 2, 2],
               [1, 1, 2, 2, 2]])
    assert classify_straddle(g) == "split"


def test_checkerboard_reads_speckle():
    g = _grid([[1, 2, 1, 2],
               [2, 1, 2, 1],
               [1, 2, 1, 2],
               [2, 1, 2, 1]])
    assert classify_straddle(g) == "speckle"


def test_pure_shape_reads_pure():
    g = _grid([[2, 2], [2, 2]])
    assert classify_straddle(g) == "pure"


def test_outside_cells_are_ignored():
    g = _grid([[-1, 1, 1, -1],
               [1, 2, 2, 1],
               [-1, 1, 1, -1]])
    assert classify_straddle(g) == "ring"
