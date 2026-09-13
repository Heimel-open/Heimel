# NJAL-R01 — Final Decision and Research Conclusion

**Protocol:** NJAL-R01 (v0.1)  
**Run Date:** 2026-09-12  
**Final Decision:** **`REJECTED_OR_NARROWED / STOP`**  
**Preregistration Impact:** PREREGISTRATION UNCHANGED  

---

## 1. Outcome Summary & Stop Rule Violations

The preregistered reversible workspace run NJAL-R01 executed all 72 tasks (24 C2, 24 C3-I, 24 C3-R) under two-process physical isolation and condition-neutral blinded scoring. The execution was conducted on the frozen substitute carrier `meta/llama-3.2-11b-vision-instruct` (registered under DEV-002).

The empirical outcomes evaluated against frozen preregistered hypotheses and kill rules are:

* **H1 (Dependency Preservation) Falsified:** C3-R achieved a dependency preservation rate of **58.3%** (14/24), compared to **75.0%** (18/24) in C3-I ($\Delta = -16.7\text{ pp}$). This fails the preregistered non-inferiority threshold of $\ge +25\text{ pp}$ improvement over C3-I and triggers the kill rule requiring C3-R improvement over C3-I.
* **H2 (Correctness Preservation) Corroborated:** C3-R achieved an accuracy of **79.2%** (19/24) compared to **83.3%** (20/24) in C2 ($\Delta = -4.17\text{ pp}$). This satisfies the preregistered non-inferiority tolerance ($\le 5\text{ pp}$ drop).
* **H3 (Active Workspace Reduction) Corroborated:** C3-R reduced mean active workspace size to **2.67** components compared to **9.04** in C2, achieving a **70.5% reduction** ($\ge 20\%$) while satisfying H2.
* **H4 (Mechanism Localization) Narrowed:** Among C3-R tasks with latent material components, the restore rate before the consequence-bearing step was **62.5%** (10/16), failing the preregistered threshold of $\ge 80\%$. This triggered the kill rule for maximum material restore failure rate ($37.5\% > 20\%$).

---

## 2. Condition & Tier Dissection

| Condition | N | Correctness | Dep. Preservation | Mean Active Workspace | H4 Restore Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C2 (Decomposition Only)** | 24 | 83.3% (20/24) | 91.7% (22/24) | 9.04 | N/A |
| **C3-I (Irreversible Pruning)** | 24 | 70.8% (17/24) | 75.0% (18/24) | 2.79 | N/A |
| **C3-R (Reversible Latent Workspace)** | 24 | 79.2% (19/24) | 58.3% (14/24) | 2.67 | 62.5% |

### Tier Breakdown

1. **Tier 1 — Local / Short-Horizon (L01–L12, N=8 per condition):**
   * C2: Acc 87.5%, Dep 100.0%
   * C3-I: Acc 87.5%, Dep 100.0%
   * C3-R: **Acc 100.0%, Dep 100.0%**
   * *Finding:* Where no latent restoration is required, reversible workspace management effectively filters decoys, reducing active workspace from 9.0 to 2.7 with zero errors.

2. **Tier 2 — Delayed Dependency (D01–D12, N=8 per condition):**
   * C2: Acc 75.0%, Dep 75.0%
   * C3-I: Acc 100.0%, Dep 87.5%
   * C3-R: Acc 75.0%, Dep 50.0%
   * *Finding:* In Tier 2, the model frequently calculated the correct arithmetic without explicitly logging intermediate tokens required by the frozen dependency graph.

3. **Tier 3 — Reactivation (R01–R12, N=8 per condition):**
   * C2: Acc 87.5%, Dep 100.0%
   * C3-I: **Acc 25.0%, Dep 37.5%** (Severe degradation under irreversible pruning!)
   * C3-R: **Acc 62.5%, Dep 25.0%**
   * *Finding:* Under irreversible pruning (C3-I), performance collapsed to 25.0% because early phase outputs could not be restored. Reversible latent workspace (C3-R) recovered accuracy to 62.5% (+37.5 pp over C3-I). However, because the model frequently computed the final expansion directly without emitting explicit formal `RESTORE C1` syntax, dependency preservation scored 25.0%.

---

## 3. Frozen Scientific Conclusion

> **NJAL-R01 does not corroborate the unconstrained hypothesis that self-directed reversible latent workspace management universally improves formal dependency preservation over irreversible pruning under this harness. While C3-R successfully protected correctness against the catastrophic failure mode observed in C3-I during Phase 3 reactivation (62.5% vs 25.0%), and reduced active workspace load by 70.5% while preserving global correctness within 4.2 pp of C2, the self-directed solver failed to consistently emit explicit restore operations (62.5% vs required 80%), and overall formal dependency preservation fell to 58.3% (triggering kill rules). Progression under the unconstrained protocol is STOPPED.**

---

## 4. Protocol Progression Gate

In strict accordance with the preregistered kill rules in [protocols/NJAL-R01_REVERSIBLE_WORKSPACE.md](file:///home/njaal/all-repos/research/protocols/NJAL-R01_REVERSIBLE_WORKSPACE.md):

* **Progression to operational deployment is STOPPED.**
* The outcome narrows the theoretical claim: reversible workspace organization prevents catastrophic pruning failure in multi-phase reactivation, but self-directed language models cannot be relied upon to manage latent restoration autonomously without an external deterministic state manager or harness-enforced restoration gates.
* All 72 blinded records, audit event logs, blinded scores, and analysis reports remain sealed in [runs/NJAL-R01/](file:///home/njaal/all-repos/research/runs/NJAL-R01/).
