"""Reproducibility tests for Phi validation experiments."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
P1_DIR = ROOT / "experiments" / "P1_LLM_LIM_Test"
P5_DIR = ROOT / "experiments" / "P5_Swarm_Coherence"

sys.path.insert(0, str(P1_DIR))
sys.path.insert(0, str(P5_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


p1 = _load_module("p1_experiment", P1_DIR / "experiment.py")
p5 = _load_module("p5_swarm", P5_DIR / "swarm_sim.py")


def test_p1_stable_seed_is_reproducible():
    assert p1.stable_seed("Tofoo") == p1.stable_seed("Tofoo")
    assert p1.stable_seed("Tofoo") != p1.stable_seed("Different prompt")


def test_p1_simulation_is_reproducible():
    left = p1.simulate_with_filter("repro prompt", max_steps=5, use_ccl=True, vocab_size=128)
    right = p1.simulate_with_filter("repro prompt", max_steps=5, use_ccl=True, vocab_size=128)

    assert left["status_history"] == right["status_history"]
    assert np.allclose(left["tau_history"], right["tau_history"])


def test_p5_swarm_is_reproducible():
    left = p5.run_swarm_simulation(n_agents=8, n_steps=12, with_phi_law=True, seed=123)
    right = p5.run_swarm_simulation(n_agents=8, n_steps=12, with_phi_law=True, seed=123)

    assert np.allclose(left["tau_matrix"], right["tau_matrix"])
    assert np.allclose(left["coherence_count"], right["coherence_count"])
    assert left["resonance_events"] == right["resonance_events"]
