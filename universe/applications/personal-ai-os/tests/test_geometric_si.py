from statistics import mean

from paios.geometric_si import Ablation, GeometricState, Relation, evaluate, nursery_state, run_experiment


def test_geometry_digest_is_deterministic():
    a = nursery_state().geometry.digest()
    b = nursery_state().geometry.digest()
    assert a == b


def test_geo_ablation_removes_symbolic_history_but_preserves_geometry():
    state = nursery_state().ablate(Ablation.GEO, seed=1)
    assert state.geometry.edges
    assert state.symbolic.records == []
    assert state.strongest_target("signal-a", "means") == "safe"
    assert "delta" in state.reachable("alpha", "path")


def test_symbolic_control_gets_same_compositional_opportunity():
    state = nursery_state().ablate(Ablation.SYMBOLIC, seed=1)
    assert not state.geometry.edges
    assert state.symbolic.records
    assert "delta" in state.reachable("alpha", "path")


def test_reset_loses_acquired_capabilities():
    metrics = evaluate(Ablation.RESET, seed=1)
    assert metrics.acquired_score == 0.0


def test_rewire_preserves_relation_inventory_not_arrangement():
    original = nursery_state().geometry
    rewired = original.rewire(seed=7)
    assert len(rewired.edges) <= len(original.edges)
    assert sorted(r.kind for r in rewired.edges.values()) == sorted(r.kind for r in original.edges.values())
    assert sorted(r.weight for r in rewired.edges.values()) == sorted(r.weight for r in original.edges.values())
    assert rewired.digest() != original.digest()


def test_geo_beats_reset_across_preregistered_acquired_metrics():
    runs = run_experiment(range(20))
    geo = mean(r.acquired_score for r in runs[Ablation.GEO])
    reset = mean(r.acquired_score for r in runs[Ablation.RESET])
    assert geo > reset
    assert geo == 1.0
    assert reset == 0.0


def test_symbolic_control_is_not_artificially_crippled():
    runs = run_experiment(range(20))
    geo = mean(r.acquired_score for r in runs[Ablation.GEO])
    symbolic = mean(r.acquired_score for r in runs[Ablation.SYMBOLIC])
    assert symbolic == geo


def test_rewired_control_is_not_equivalent_to_learned_geometry():
    runs = run_experiment(range(20))
    geo = mean(r.acquired_score for r in runs[Ablation.GEO])
    rewired = mean(r.acquired_score for r in runs[Ablation.REWIRED])
    assert rewired < geo


def test_geometry_has_no_authority_surface():
    state = GeometricState()
    state.learn(Relation("a", "rel", "b", provenance="event:x"))
    assert not hasattr(state, "authority")
    assert not hasattr(state, "execute")
