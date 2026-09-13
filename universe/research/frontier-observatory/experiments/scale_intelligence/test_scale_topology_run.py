from scale_sweep import NODES, evolve
from scale_topology_run import (
    DENSE_SCALES,
    FIXED_SUBSTRATE_INVARIANTS,
    REPLICATE_SEEDS,
    TASK_BLOCKS,
    evolve_reflected,
    reflected_index,
)


def test_reflection_rule_at_boundaries():
    assert reflected_index(-1) == 1
    assert reflected_index(-30) == 30
    assert reflected_index(NODES) == NODES - 2
    assert reflected_index(NODES + 29) == NODES - 31


def test_reflected_line_is_not_periodic_ring():
    values = [float(i) for i in range(NODES)]
    assert evolve_reflected(values, 4) != evolve(values, 4)


def test_dense_grid_and_fresh_replicates_are_frozen():
    assert TASK_BLOCKS == (5, 9, 13)
    assert DENSE_SCALES == tuple(range(4, 16))
    assert REPLICATE_SEEDS == (37037, 38038, 39039, 40040, 41041)


def test_topology_is_part_of_fixed_substrate_fingerprint():
    assert "topology" in FIXED_SUBSTRATE_INVARIANTS
    assert FIXED_SUBSTRATE_INVARIANTS["topology"].startswith("sha256:")
