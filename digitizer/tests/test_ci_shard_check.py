"""tools/ci_shard_check.py, the `digitizer` aggregator's coverage proof,
including the wire scope a non-digitizer PR runs under."""

from tools.ci_shard_check import check

ALL = ["a::1", "a::2", "b::1"]


def _full(k, sel):
    return {"shard": k, "of": 2, "scope": "full", "collected": ALL, "selected": sel}


def _marker(k):
    return {"shard": k, "of": 3, "scope": "wire", "skipped": True}


def _wire_ran(collected, selected=None):
    return {"shard": 1, "of": 1, "scope": "wire", "collected": collected,
            "selected": collected if selected is None else selected}


def test_full_scope_passes_when_the_shards_add_up():
    assert check([_full(1, ["a::1", "b::1"]), _full(2, ["a::2"])]) == []


def test_full_scope_catches_a_dropped_test():
    assert check([_full(1, ["a::1"]), _full(2, ["a::2"])])


def test_wire_scope_passes_with_shard_one_run_and_the_rest_marked():
    assert check([_wire_ran(["w::1", "w::2"]), _marker(2), _marker(3)]) == []


def test_wire_scope_fails_on_an_empty_subset():
    assert check([_wire_ran([]), _marker(2), _marker(3)])


def test_wire_scope_fails_when_a_shard_is_missing():
    assert check([_wire_ran(["w::1"]), _marker(3)])


def test_wire_scope_fails_when_shard_one_ran_only_part_of_it():
    assert check([_wire_ran(["w::1", "w::2"], ["w::1"]), _marker(2), _marker(3)])


def test_shards_that_disagree_on_scope_fail():
    assert check([_wire_ran(["w::1"]), _full(2, ["a::2"]), _marker(3)])
