# Claude findings — 2026-06-14

Task: analyse current codebase as input to extracting `packages/vaig-core`.

Files read: `proxy/README.md`, `proxy/proxy.py`, `proxy/gate.py`, `vaig/ensemble.py`, `vaig/orchestrator.py`, `vaig/worm.py`, `vaig/instruments/` (12 files), `spaces/app.py`.

Missing files (not in repo): `context.md`, `docs/PRODUCT_MODES.md`, `docs/ARCHITECTURE.md`, `docs/analysis/valo_research_group_complete_analysis.md`, `mcp_server.py`, `Sidecar/README.md`.

---

## Current structure

```
vaig/                    ← Python package — already IS the core
  ensemble.py            ← DistrustLevel + VAIGEnsemble (L1–L4)
  orchestrator.py        ← VAIGOrchestrator (L5): Scout + Dirigent + Ensemble
  worm.py                ← WORMLog — SHA-256 hash-chained, encrypted
  instruments/           ← 12 instruments (hedge, logprob, semantic_entropy, …)
  scout/                 ← terrain.py, dirigent.py
  integrations/          ← external adapters

proxy/                   ← HTTP Proxy deployment mode
  proxy.py               ← Flask transparent proxy (Scout → forward → Gate → WORM)
  gate.py                ← C₀ coherence gate (PASS/DEGRADE/HALT)
  scout.py               ← ingress filter (injection + L-scalar)
  worm.py                ← WORMLog duplicate (simpler version)
  defer.py               ← DeferQueue: DEGRADE → human review queue
  worm_backends.py       ← S3 Object Lock / TPM2 backends

spaces/                  ← Gradio UI (HF Spaces / demo deployment)
  app.py

tests/
pyproject.toml
```

---

## What belongs in `packages/vaig-core`

### 1. Levels (DistrustLevel)

Defined in `vaig/ensemble.py`:

```python
class DistrustLevel(Enum):
    TRUSTED  = "L0"
    MONITOR  = "L1"
    WARN     = "L2"
    DEGRADE  = "L3"
    HALT     = "L4"
```

Gate decision (in `proxy/gate.py`) maps to three states: `PASS / DEGRADE / HALT`.
These are two overlapping vocabularies. Core should define both and document the mapping:
- `TRUSTED/MONITOR → PASS`
- `WARN/DEGRADE → DEGRADE`
- `HALT → HALT`

### 2. Decisions (ValidationResult + GateResult)

`vaig/ensemble.py` — `ValidationResult`:
```python
@dataclass
class ValidationResult:
    entry_id: str
    level: DistrustLevel
    combined_score: float
    scores: Dict[str, float]
    worm_hash: str
    latency_ms: float
```

`proxy/gate.py` — inline dict:
```python
{"status": "PASS", "tav_regime": ..., "combined_status": ..., "coherence": ..., "metrics_logged": True}
```

For `vaig-core`: a `GateDecision` dataclass unifying both, used by all three deployment modes.

### 3. Policy mapping

Two separate policy tables today:

`vaig/ensemble.py` (distrust thresholds, 0–1 score):
```python
_THRESHOLDS_DEFAULT = {
    "HALT": 0.75, "DEGRADE": 0.55, "WARN": 0.35, "MONITOR": 0.15,
}
```

`proxy/gate.py` (coherence threshold, 0–10000 scale):
```python
coherence = confidence_score * 10000
if coherence >= C₀: PASS
elif coherence > 0: DEGRADE
else: HALT
```

For `vaig-core`: single `PolicyConfig` with both tables, loaded from env vars once at startup.

### 4. Audit receipt schema

Defined in `vaig/worm.py` — canonical schema per entry:

```json
{
  "id": "<uuid8>",
  "ts": 1718364000.123,
  "prev": "<sha256 of previous entry or 'genesis'>",
  "prompt_sha256": "<sha256>",       // Level 1 — always present
  "response_sha256": "<sha256>",     // Level 1 — always present
  "prompt_enc": "<base64 XOR>",      // Level 2 — if encryption_key set
  "response_enc": "<base64 XOR>",    // Level 2 — if encryption_key set
  "<instrument scores>": ...,
  "hash": "<sha256 of this entry>"   // chain link
}
```

This schema is the EU AI Act Article 12/13 audit receipt. It is the canonical output of `vaig-core`. Deployment modes (proxy, sidecar, MCP) all write to it — they never define their own schema.

### 5. WORM interface

Canonical interface from `vaig/worm.py`:

```python
class WORMLog:
    def append(entry_id: str, data: dict, prompt=None, response=None) -> str
    def verify() -> bool
    def decrypt_entry(entry: dict) -> dict
    def read_all() -> list[dict]
```

Backends (file, S3 Object Lock, TPM2) live in `proxy/worm_backends.py` today — they belong in `vaig-core` as optional extras.

---

## Divergence: two WORMLog implementations

`vaig/worm.py` and `proxy/worm.py` are separate. The proxy uses `from proxy.worm import WORMLog` — meaning it does NOT use the canonical implementation.

This is the primary structural problem `packages/vaig-core` solves.

Fix: proxy imports `from vaig_core.worm import WORMLog`.

---

## Divergence: module-level RuntimeError in proxy/gate.py

```python
_raw = os.environ.get("VALO_COHERENCE_THRESHOLD")
if not _raw:
    raise RuntimeError("VALO_COHERENCE_THRESHOLD environment variable is required")
```

This crashes any process that imports `proxy.gate` without the env var set — including tests. Same pattern fixed in `website/api/v5/playground/chat.py` today. Recommend moving the check inside `evaluate()` and raising `ValueError` there.

---

## Deployment modes — confirmed distinct

All three modes share the same gate logic and WORM schema. They differ in transport and trigger:

| Mode | Transport | Trigger | File |
|------|-----------|---------|------|
| HTTP Proxy | Flask, transparent | Any HTTP client | `proxy/proxy.py` |
| Sidecar / Gradio | Gradio UI | Human demo / researcher | `spaces/app.py` |
| MCP Server | MCP protocol | Claude Code, Cursor, agentic tools | does not exist yet |

Do NOT merge them. The right move is to let all three import from `packages/vaig-core`.

---

## Proposed `packages/vaig-core` surface

```python
# vaig_core/__init__.py — public API
from vaig_core.levels import DistrustLevel, GateStatus
from vaig_core.decisions import ValidationResult, GateDecision
from vaig_core.policy import PolicyConfig, default_policy
from vaig_core.worm import WORMLog
from vaig_core.receipt import AuditReceipt   # typed schema for the JSONL entry
```

What stays OUT of core:
- Instruments (stay in `vaig/`)
- Scout / Dirigent (stay in `vaig/`)
- Flask / Gradio / MCP transport (stay in their mode packages)
- `l1-guardian/` Rust code — not touched
- `formal-verification/` TLA+ — not touched

---

## Safe next step

Create `vaig_core/` directory with:
1. `levels.py` — `DistrustLevel` enum + `GateStatus` literal
2. `decisions.py` — `ValidationResult` + `GateDecision` dataclasses (copied from `vaig/ensemble.py`, not moved yet)
3. `worm.py` — copy of `vaig/worm.py` (canonical)
4. `receipt.py` — typed `AuditReceipt` dataclass matching the JSONL schema
5. `policy.py` — `PolicyConfig` with both threshold tables

Then update imports in `proxy/` to use `vaig_core.worm` instead of `proxy.worm`.

Do NOT delete `vaig/worm.py` until proxy is confirmed working with the core version.
