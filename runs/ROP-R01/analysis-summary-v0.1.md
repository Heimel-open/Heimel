# ROP-R01 Calibration Run — Analysis Summary

**Date:** 2026-09-12T06:37:07.508538+00:00
**Protocol:** ROP-R01 (v0.1)
**Tasks Analyzed:** 48
**Overall Decision:** `NO_GO / STOP`

---

## Condition Results

| Condition | N | Correct | Accuracy | ESC (Mean ± Std) | Mean Steps | Mean Time (s) | Dep. Pres. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C0 (Unconstrained)** | 16 | 15 | 93.8% | -0.276 ± 0.810 | 3.00 | 25.66s | 87.5% |
| **C2 (Decomposition)** | 16 | 15 | 93.8% | -0.256 ± 0.751 | 2.94 | 31.24s | 75.0% |
| **C3 (Reduction Op)** | 16 | 13 | 81.2% | +0.532 ± 2.154 | 2.69 | 105.17s | 37.5% |

---

## Pre-registered Hypotheses

- **H1 (ESC Reduction):** `NOT_SUPPORTED`
  - $\Delta \text{ESC}(C3 - C0) = +0.808$
  - $\Delta \text{ESC}(C3 - C2) = +0.788$
- **H2 (Correctness Preservation $\ge -5\%$):** `FAIL`
  - C3 Accuracy: `81.2%` vs Best Control: `93.8%` (diff: `-12.5pp`)

---

## Kill / Stop Rules

- **Violations:** 2
- ⚠️ C3 correctness is 12.5pp below best control (exceeds 5pp tolerance)
- ⚠️ C3 dependency preservation rate (37.5%) is below 95%
- **Gate Recommendation:** **`NO_GO / STOP`**
