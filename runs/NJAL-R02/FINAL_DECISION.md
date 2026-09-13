# NJAL-R02 — Final Decision and Research Conclusion

**Protocol:** NJAL-R02 (v0.1)  
**Run Date:** 2026-09-12  
**Final Decision:** **`CONFIRMED / GO`**  
**Preregistration Impact:** PREREGISTERED HYPOTHESES CORROBORATED  

---

## 1. Outcome Summary & Hypothesis Corroboration

The preregistered governed reactivation benchmark NJAL-R02 executed all 72 tasks (24 C2, 24 C3-R-M, 24 C3-R-G) under two-process physical isolation, condition-neutral blinded scoring, and consequence-gated harness verification.

The empirical outcomes evaluated against frozen preregistered hypotheses and kill rules are:

* **H1 (Governed Restore Elevation) Corroborated:** C3-R-G achieved a material restore rate of **100.0%** (16/16) prior to consequence execution, compared to **37.5%** (6/16) in C3-R-M ($\Delta = +62.5\text{ pp}$). This easily clears the required threshold of $\ge 90\%$ and $\ge +25\text{ pp}$ improvement over C3-R-M.
* **H2 (Dependency Preservation Restoration) Corroborated:** C3-R-G achieved a dependency preservation rate of **100.0%** (24/24), compared to **58.3%** (14/24) in C3-R-M ($\Delta = +41.7\text{ pp}$). This exceeds the required threshold of $\ge 90\%$ and $\ge +25\text{ pp}$.
* **H3 (Active Workspace Preservation) Corroborated:** C3-R-G maintained a mean active workspace size of **2.67** components compared to **8.67** in C2, achieving a **69.2% reduction** in active cognitive/context load while maintaining perfect correctness and dependency preservation.
* **H4 (Correctness Non-Inferiority) Corroborated:** C3-R-G maintained an accuracy of **100.0%** (24/24) with zero drop compared to C2 ($\Delta = 0.0\text{ pp}$), satisfying the non-inferiority tolerance ($\le 5\text{ pp}$ drop).

---

## 2. Condition Comparison

| Condition | N | Correctness | Dependency Preservation | Mean Active Workspace | H1 Restore Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C2 (Decomposition Only)** | 24 | 100.0% (24/24) | 100.0% (24/24) | 8.67 | N/A |
| **C3-R-M (Model-Directed Restore)** | 24 | 100.0% (24/24) | 58.3% (14/24) | 2.25 | 37.5% (6/16) |
| **C3-R-G (Governed Reactivation)** | 24 | 100.0% (24/24) | 100.0% (24/24) | 2.67 | 100.0% (16/16) |

---

## 3. Scientific Conclusion

> **NJAL-R02 definitively corroborates the core thesis of the Njål Method: when consequence authority is decoupled from the model and held by an execution harness with deterministic consequence triggers (`C3-R-G`), material latent components are 100% reliably restored before consequence-bearing steps. This completely resolves the self-directed restoration failure observed in NJAL-R01 (H4 failure), restoring dependency preservation from 58.3% back to 100.0% while achieving a 69.2% reduction in active context/workspace load.**

---

## 4. Protocol Gate Resolution

All kill rules pass without exception:
- Max correctness drop vs C2 <= 5 pp: **PASS (0.0 pp)**
- Min C3-R-G dependency preservation >= 90%: **PASS (100.0%)**
- Min C3-R-G restore rate >= 90%: **PASS (100.0%)**
- C3-R-G improves over C3-R-M: **PASS (+41.7 pp)**
- Min workspace reduction vs C2 >= 20%: **PASS (69.2%)**

The execution gate is unlocked, artifacts are sealed, and the benchmark is marked **`CONFIRMED`**.
