# ROP-R01 — Final Decision and Research Conclusion

**Protocol:** ROP-R01 (v0.1)  
**Run Date:** 2026-09-12  
**Final Decision:** **`NO_GO / STOP`**  
**Preregistration Impact:** PREREGISTRATION UNCHANGED  

---

## 1. Outcome Summary & Stop Rule Violations

The preregistered calibration run ROP-R01 executed all 48 tasks under two-process physical isolation and structural blinding. The preregistered hypotheses were not corroborated:

* **H1 (ESC Reduction) Falsified:** Explicit reduction (C3) did not reduce effective search cost. Relative to controls, $\Delta \text{ESC}(C3 - C0) = +0.808$ and $\Delta \text{ESC}(C3 - C2) = +0.788$. While C3 exhibited fewer reported steps (2.69 vs 3.00), this was heavily outweighed by severe latency penalties (mean time 105.17s vs 25.66s in C0).
* **H2 (Correctness Preservation) Failed:** C3 accuracy was 81.2% (13/16) compared to 93.8% (15/16) in both controls (C0 and C2). The difference of −12.5 percentage points violates the preregistered non-inferiority tolerance of $\ge -5\text{pp}$.
* **Material Degradation of Dependency Preservation:** C3 preserved required mathematical dependencies at only 37.5% (6/16), compared to 87.5% in C0 and 75.0% in C2. The explicit reduction scaffolding caused premature removal or skipping of required intermediate structure, directly violating the preregistered threshold ($\ge 95\%$).

---

## 2. Frozen Scientific Conclusion

> **ROP-R01 does not corroborate the current Reduction Operator Protocol. Under the tested harness, explicit reduction increased effective search cost, reduced correctness beyond the preregistered tolerance, and materially degraded dependency preservation. Progression is stopped. The result narrows the hypothesis from “explicit reduction improves reasoning efficiency” to a weaker question: whether reduction can help when removal decisions are externally constrained or independently validated rather than delegated to the solving model itself.**

---

## 3. Protocol Progression Gate

In strict accordance with the preregistered kill rules in [protocols/ROP-R01_CALIBRATION.md](file:///home/njaal/all-repos/research/protocols/ROP-R01_CALIBRATION.md):

* **Progression to ROP-R02 / R07 is STOPPED** under this operator.
* No post-hoc modification or repair of ROP-R01 is permitted.
* Any future investigation or testing of externally constrained reduction must be designed as a distinct protocol / version.
