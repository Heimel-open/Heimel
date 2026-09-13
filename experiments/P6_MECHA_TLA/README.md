# P6 — MECHA Formal Verification

Python bounded model checker for:

> Rupp & Solland (2026). *MECHA: Formal Verification of Conjunctive Human-AI Execution Governance*

## Files

| File | Purpose |
|------|---------|
| `mecha_checker.py` | Python BFS model checker — standalone |
| `visualize_mecha.py` | Generate verification report charts |
| `P6_MECHA_Colab.ipynb` | Colab notebook — Python BFS reproduction + visualization |
| `P6_MECHA_TLC_Colab.ipynb` | Colab notebook — **real TLC run** (Java + tla2tools.jar), v1.1 + v1.0 bug comparison |

## Run locally

```bash
# Correct spec (v1.1) — should show 0 violations
python mecha_checker.py

# Bug simulation (v1.0 — missing ~vetoed guard) — shows 524 violations
python mecha_checker.py --bug

# Generate comparison charts
python visualize_mecha.py
```

## Results

| Version | States | ConjunctiveIntegrity | SeparationOfDuties | NoDoubleFinalize |
|---------|--------|---------------------|-------------------|-----------------|
| v1.1 (correct) | 16,900 | HOLDS | HOLDS | HOLDS |
| v1.0 (bug) | 17,424 | HOLDS | HOLDS | **VIOLATED (524×)** |

**Bug:** `AllowAction` in v1.0 was missing the `~vetoed[op]` guard, allowing states where `executed[op] ∧ vetoed[op]` — a double-finalize violation.

## Colab

Two notebooks:

- `P6_MECHA_Colab.ipynb` — Python BFS reproduction. No external dependencies beyond `tqdm` and `matplotlib`.
- `P6_MECHA_TLC_Colab.ipynb` — the **actual TLC model checker** (official `tla2tools.jar`, Java). Verifies v1.1 (expect 16,900 distinct states, 0 violations — confirmed against a real TLC run: 146,836 states generated, depth 16) and re-runs the v1.0 bug variant so TLC itself produces the `NoDoubleFinalize` counterexample trace. Runtime ~1–2 min on a free Colab CPU.
