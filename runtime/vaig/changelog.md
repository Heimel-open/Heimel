# VALO Changelog

## 2026-08-05
### Production-hardening recovery (`hermes/recover-vaig-commits`)
- Recovered orphaned RACS adapter, core helpers and tests
- Wired canonical AARM verdict engine into the API and orchestrator
- Fail-closed external instruments, WORM ChaCha20-Poly1305 AEAD encryption
- CORS, rate-limit and SQLite-WORM thread-safety fixes
- Removed experimental modules (`vaig/swarm`, `vaig/vaig_embedded`) from the
  live package — retained only in git history

## 2026-06-13
### Consolidation Release
- Unified DistrustEngine (merges 3 implementations)
- Unified WORMLog (standardized hash-chained audit)
- Rebuilt vaig_embedded (on-device runtime, 13 files)
- Rebuilt Swarm Authority (anti-coercion, 8 files)
- 69 tests passing (29 core + 15 integration + 25 red team)
- EU AI Act compliance mapper
- Master Colab (P1 + P5 + P6)
- Universal equation: γ + 4ρ = δ·ρ

## Earlier
- valo-v5-core: Rust deterministic gate, TLA+ verified
- vaig: 8-instrument ensemble
- Sidecar: Dockerized VAIG
- Φ-law: P1/P5/P6 empirical validation
