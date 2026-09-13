# PR #6 — Conflict Resolution Plan
**Date:** 2026-06-14  
**PR:** feat(proxy): DistrustEngine Instrument 4 — semantic drift detection  
**Branch:** `claude/calo-core-review-FXR3n` → `main`  
**Status:** DRAFT — requires Njål review before rebase

---

## Current conflict state

Git reports 4 files as conflicting. Analysis below covers each in detail.
Conclusion: 3 of 4 files have substantive diffs; 1 (`ONBOARDING.md`) is a new
file on the branch and will resolve automatically on rebase.

No WORM migration is included in this PR. `proxy/proxy.py` still uses the
old `worm.append(data)` signature — that migration is deferred to a separate PR.

---

## File 1: `proxy/gate.py`

### What changed on main
Module-level env-var check and RuntimeError at import time:

```python
# main — lines 6–10
_raw = os.environ.get("VALO_COHERENCE_THRESHOLD")
if not _raw:
    raise RuntimeError("VALO_COHERENCE_THRESHOLD environment variable is required")
_COHERENCE_THRESHOLD = float(_raw)
```

`evaluate()` references the module-level constant `_COHERENCE_THRESHOLD`.

### What changed on branch
Module-level check removed entirely. Env-var read moved inside `evaluate()`:

```python
# branch — inside evaluate()
raw = os.environ.get("VALO_COHERENCE_THRESHOLD")
if not raw:
    raise RuntimeError("VALO_COHERENCE_THRESHOLD environment variable is required")
coherence_threshold = float(raw)
```

`evaluate()` uses the local variable `coherence_threshold`.

### Why branch version should win

The module-level `raise RuntimeError` fires at **import time**, not at call
time. This breaks:

1. **Railway cold start**: the dyno imports `proxy/gate.py` to register routes;
   the process dies before the health-check handler even runs.
2. **Test imports**: `from proxy.gate import evaluate` in any test without the
   env var set raises immediately, making unit tests impossible.
3. **Any serverless or lazy-init deployment**: same crash-on-import problem as
   Railway cold start.

Moving the check inside `evaluate()` preserves the same runtime invariant
(call fails without env var) while allowing the module to be imported cleanly.
This is the standard pattern for env-var-gated singletons in Python.

### Behavior preserved

- `evaluate(confidence_score, tav_l_scalar)` signature: unchanged.
- Return format `{status, tav_regime, combined_status, coherence, metrics_logged}`: unchanged.
- RuntimeError still raised if env var missing — just at call time, not import time.
- `_tav_regime()` and `_combined_status()` helpers: unchanged.
- TAV threshold constants `_TAV_THRESHOLDS`: unchanged.

### Tests that must pass after resolution

```python
# 1. Clean import without env var — must NOT raise
import importlib, sys
sys.modules.pop("proxy.gate", None)
import proxy.gate  # no RuntimeError

# 2. evaluate() without env var — must raise RuntimeError
import pytest
with pytest.raises(RuntimeError, match="VALO_COHERENCE_THRESHOLD"):
    proxy.gate.evaluate(0.9)

# 3. evaluate() with env var — must return correct status
import os
os.environ["VALO_COHERENCE_THRESHOLD"] = "4495"
result = proxy.gate.evaluate(0.9)
assert result["status"] == "PASS"
assert result["combined_status"] == "PASS"
assert result["coherence"] == 9000.0

# 4. TAV override
result = proxy.gate.evaluate(0.9, tav_l_scalar=0.4)  # PLASMA
assert result["combined_status"] == "HALT"
```

---

## File 2: `vaig/__init__.py`

### What changed on main
v0.2.0, 6 public exports:
```python
from vaig.ensemble import VAIGEnsemble, ValidationResult, DistrustLevel
from vaig.orchestrator import VAIGOrchestrator, OrchestratorResult
from vaig.worm import WORMLog

__version__ = "0.2.0"
```

### What changed on branch
v0.3.0, 16 exports — main's 6 preserved exactly, plus 10 new:
```python
from vaig.recovery import RecoveryManager, RecoveryAction      # L5.5
from vaig.cakm import CAKM, AlertLevel                         # L7
from vaig.council import CouncilQueue, CouncilItem              # L6
from vaig.skjaersilden import Skjaersilden                      # L6.5
from vaig.delta_sandbox import DeltaBoxSandbox, CheckpointNotFoundError  # L8

__version__ = "0.3.0"
```

Docstring updated with full-stack usage example.

### Why branch version should win

Branch is **strictly additive**. Every symbol exported by main continues to be
exported with the identical import path. No existing import is removed, renamed,
or changed. New exports correspond to modules (`recovery.py`, `cakm.py`,
`council/`, `skjaersilden.py`, `delta_sandbox.py`) that are added on the branch
and do not exist on main. Version bump 0.2.0 → 0.3.0 correctly reflects the
addition of four new architectural layers.

### Behavior preserved

All existing `from vaig import X` calls continue to work without modification.
New imports become available but are not required.

### Tests that must pass after resolution

```python
# Existing public API — all must still import cleanly
from vaig import VAIGEnsemble, ValidationResult, DistrustLevel
from vaig import VAIGOrchestrator, OrchestratorResult
from vaig import WORMLog

# New L5.5–L8 exports — must all be importable
from vaig import RecoveryManager, RecoveryAction
from vaig import CAKM, AlertLevel
from vaig import CouncilQueue, CouncilItem
from vaig import Skjaersilden
from vaig import DeltaBoxSandbox, CheckpointNotFoundError

import vaig
assert vaig.__version__ == "0.3.0"
```

---

## File 3: `vaig/orchestrator.py`

### What changed on main
- No CAKM import
- `OrchestratorResult`: no `cakm_alert` field
- `VAIGOrchestrator.__init__`: no `with_cakm` parameter
- `evaluate()`: no `session_id` parameter; returns `OrchestratorResult` directly
- `__str__()`: no CAKM display line

### What changed on branch
Four additive changes — no existing signatures altered:

**1. Import added (top of file):**
```python
from vaig.cakm import CAKM, AlertLevel
```

**2. OrchestratorResult — one field added with default:**
```python
cakm_alert: Optional[str] = None  # AlertLevel.value, or None if CAKM not active
```
`__str__()` displays it only when non-None and non-GREEN.

**3. `__init__` — one optional param + one attribute:**
```python
def __init__(self, ..., with_cakm: bool = True):
    ...
    self.cakm: Optional[CAKM] = CAKM() if with_cakm else None
```

**4. `evaluate()` — one optional param + CAKM.observe() at end:**
```python
def evaluate(self, prompt, response, ..., session_id: str = ""):
    ...
    orch_result = OrchestratorResult(...)  # renamed from result for clarity

    if self.cakm and session_id:           # guard: both must be truthy
        alert = self.cakm.observe(session_id, orch_result)
        orch_result.cakm_alert = alert.value

    return orch_result
```

### Why branch version should win

All new parameters have defaults (`with_cakm=True`, `session_id=""`). All
existing call sites continue to work without modification. The `if self.cakm
and session_id:` guard means CAKM is entirely bypassed when `session_id` is not
provided — no behavioral change for existing callers. `with_cakm=False` allows
callers to opt out of CAKM entirely if needed.

CAKM (L7) is the session-level distrust pattern tracker: the only way to wire
it into the Orchestrator result is exactly this pattern.

The cosmetic rename `result` → `orch_result` avoids shadowing the inner
`result` from `self.ensemble.evaluate()`. No semantic change.

### Behavior preserved

- `VAIGOrchestrator()` with no args: same behavior, CAKM instance created but
  unused unless session_id provided.
- `orch.evaluate(prompt, response)` without session_id: returns same
  OrchestratorResult with `cakm_alert=None`.
- `result.should_halt`, `result.level`, `result.combined_score`: all unchanged.
- `result.validation`, `result.terrain`, `result.activated_*`, `result.skipped`:
  all unchanged.

### Tests that must pass after resolution

```python
from vaig.orchestrator import VAIGOrchestrator, OrchestratorResult

orch = VAIGOrchestrator()

# Existing call signature — must work unchanged
result = orch.evaluate("prompt", "response")
assert hasattr(result, "should_halt")
assert result.cakm_alert is None  # not set without session_id

# With session_id — CAKM fires
result2 = orch.evaluate("prompt", "response", session_id="test-session")
assert result2.cakm_alert in ("GREEN", "YELLOW", "ORANGE", "RED")

# Opt-out
orch_no_cakm = VAIGOrchestrator(with_cakm=False)
result3 = orch_no_cakm.evaluate("prompt", "response", session_id="test-session")
assert result3.cakm_alert is None  # CAKM disabled
```

---

## File 4: `ONBOARDING.md`

### What changed on main
**File does not exist on main.** (`get_file_contents` returns 404.)

### What changed on branch
New file added. Comprehensive Norwegian-language onboarding guide covering:
installation, quick start, distrust levels, the 8 instruments, LLM integration,
WORM audit log, production setup, demo mode, and what VAIG does not do.

Section "Ressurser" includes:
> EU AI Act Article 12: WORM-loggen støtter kravene til automatisk,
> manipulasjonssikker logging. Articles 9–11, 13–17 krever separate tiltak.

### Why branch version should win

There is no conflict. A file that exists only on the branch is added cleanly by
git rebase — no merge decision required. The Article 12 scope qualifier is
correct: VAIG's WORM log directly addresses Article 12 (automatic logging of
high-risk AI systems). Articles 9–11 (risk management, data governance, technical
documentation) and 13–17 (transparency, human oversight, accuracy, robustness,
cybersecurity) require separate organisational and technical measures beyond what
VAIG provides.

### Tests that must pass after resolution

No code test. Verify file is present at `ONBOARDING.md` in the merged tree.

---

## Summary

| File | Conflict type | Resolution | Risk |
|------|--------------|-----------|------|
| `proxy/gate.py` | RuntimeError placement | Take branch | Low — same runtime invariant, safer for imports |
| `vaig/__init__.py` | Additive exports + version bump | Take branch | Low — strictly additive |
| `vaig/orchestrator.py` | CAKM wiring, new optional params | Take branch | Low — all defaults backward-compatible |
| `ONBOARDING.md` | New file on branch, absent on main | Auto-resolves | None — git adds it cleanly |

**No WORM migration** in this PR (`proxy/proxy.py` worm calls deferred).  
**No private IP disclosure** — no constants, thresholds, or calibration values in any file above.  
**Prerequisite for rebase:** Njål reviews this document and gives explicit go.
