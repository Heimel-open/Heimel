# CLAUDE.md — Personal AI Operating System (PAIOS)

## State: CO-WORKER

PAIOS is the software foundation for relAIon: a co-worker that **discovers + proposes + remembers**.  
It NEVER decides, never executes.  
**REHT is the sole admissibility authority.**  
Execution is owned by REHT / VALO Harness — out of scope here.

## Naming and lineage

- Current canonical product/architecture name: **relAIon**.
- **Relygon** is the former name and is not a separate product or development track.
- Historical Relygon source is retained only for provenance/compatibility under `docs/relaion/legacy/relygon/` or in its original infrastructure owner.
- All interpretation and new work follows `docs/relaion/relygon-migration.md`.
- Do not introduce new current-facing `Relygon` names except explicit compatibility/provenance handling.

## Core identity

| Property | Value |
|----------|-------|
| Role | Co-worker (discovers + proposes + remembers) |
| Opportunity | Finds needs, latent capabilities, unrealized assets and possible paths |
| Execution | OUT OF SCOPE — REHT/Harness own that |
| Authority | Zero execution authority |
| Memory | Canonical Memory (#139): structured, queryable, NOT chat-history |
| Execution autonomy | Governed by AutonomyModel (#144); separate from developmental state |
| Proposals | RACS-style action envelopes (#143), routed to REHT/VAIG |

## Canonical architecture references

- **relAIon canonical home**: `docs/relaion/README.md`.
- **Relygon → relAIon migration**: `docs/relaion/relygon-migration.md`.
- **relAIon Opportunity Engine**: Need → latent capability → unrealized asset → opportunity graph → possible paths → governed proposal → evidence → learning.
- **relAIon embodiment**: Continuity-bearing Core with replaceable models, devices, sensors, providers and capabilities.
- **REHT** (#15-18): SOLE admissibility authority. OS proposes → REHT decides.
- **VAIG** (#23-28): Integrity signals. Evaluates proposals before REHT.
- **BARO** (#57-58): Observation/evidence only. Not referenced directly.
- **RACS** (#29-30): Action envelope standard. Schema reused here.
- **VALO Harness** (#105-115): Orchestration, NO authority.
- **Governed Autonomy** (#143): Graduated freedom within explicit authority/policy/admissibility bounds.
- **Canonical Memory** (#139): Authoritative structured memory, NOT random chat history.
- **Maturity Model** (#144): L0 none → L1 assist → L2 steered recs → L3 governed execution → L4 autonomous.

## Non-negotiable rules

1. REHT sole admissibility authority — OS proposes, never decides/executes.
2. An inferred need is not consent.
3. A known asset is not permission to use it.
4. A relationship is not an entitlement or capability grant.
5. A technical capability is not authority.
6. A valuable path is not automatically admissible.
7. Opportunity reasoning preserves provenance, uncertainty, conflicts, affected parties and time validity.
8. Personal context is disclosed to capabilities only when necessary and within purpose/mandate.
9. Canonical types reused where they exist (RACS action envelope, MemoryRecord shapes).
10. C0/α/τ = ENV VARS only, never hardcoded.
11. Deterministic, synchronous where possible, no hidden state.
12. Python 3.11+ conventions; pyproject.toml + pytest.
13. No execution-autonomy advance without governance signal (AutonomyModel).
14. Execution boundary asserted in code + tests.

## Directory structure

```
PersonalAI-OS/
├── src/paios/
│   ├── __init__.py     # Package root
│   ├── seed.py         # Minimal identity-bearing developmental seed
│   ├── memory.py       # CanonicalMemory + MemoryRecord (#139)
│   ├── maturity.py     # MaturityModel + levels (#144)
│   ├── proposal.py     # Action envelope builder + governed proposal (#143)
│   ├── reht_client.py  # REHT client — in-process + HTTP modes (#257 follow-up)
│   └── boundaries.py   # Assert-no-execution guard
├── tests/
│   └── test_paios.py   # Unit tests
├── config/
│   └── paios.yaml      # Default configuration
├── docs/
│   └── relaion/
│       ├── README.md
│       ├── relygon-migration.md
│       └── legacy/relygon/   # Historical source only
├── pyproject.toml      # Build + test config
├── CLAUDE.md           # This file
└── README.md           # Project overview
```

## Development commands

```bash
# Install
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=src/paios

# Type check (optional)
mypy src/paios/
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAIOS_MEMORY_PATH` | `~/.paios/memory.jsonl` | Canonical memory store path |
| `PAIOS_C0_LOW` | `0.3` | Lower coherence threshold |
| `PAIOS_C0_HIGH` | `0.7` | Upper coherence threshold |
| `PAIOS_ALPHA` | `0.1` | Learning rate |
| `PAIOS_TAU` | `3600` | Time constant |
| `PAIOS_ADVANCE_C0` | `0.65` | Min coherence for L2→L3 advance |
| `PAIOS_REHT_ADMISSIBILITY_PROVEN` | `0` | Set to `1` to enable L2→L3 |
| `PAIOS_CONTINUOUS_INTEGRITY` | `0` | Set to `1` to enable L3→L4 |

## Key architectural boundaries

```
need / observation / personal state
              ↓
relAIon opportunity discovery and possible paths
              ↓
         ActionEnvelope
              ↓
         VAIG (integrity eval)
              ↓
         REHT (admissibility)
              ↓
         GovernanceClearance
              ↓
         VALO Harness / Core (EXECUTION — out of PAIOS scope)
              ↓
         Effect evidence → governed learning
```
