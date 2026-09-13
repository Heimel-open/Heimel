# NJAL-R02 Analysis Summary: Governed Reactivation Benchmark

Protocol: NJAL-R02 v0.1
Total Tasks: 72
Final Decision: **CONFIRMED**

## Conditions Overview

| Condition | N | Correctness | Dependency Preservation | Mean Active Workspace | H1 Restore Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **C2 (Decomposition Only)** | 24 | 100.0% | 100.0% | 8.67 | N/A |
| **C3-R-M (Model-Directed Restore)** | 24 | 100.0% | 58.3% | 2.25 | 37.5% |
| **C3-R-G (Governed Reactivation)** | 24 | 100.0% | 100.0% | 2.67 | 100.0% |

## Frozen Hypotheses Evaluation

- **H1 (Governed Restore Elevation)**: C3-R-G restore rate: **100.0%** vs C3-R-M: **37.5%** (+62.5 pp, threshold: >=90% & >=+25 pp) -> **PASS**
- **H2 (Dependency Preservation Restoration)**: C3-R-G dep preservation: **100.0%** vs C3-R-M: **58.3%** (+41.7 pp, threshold: >=90% & >=+25 pp) -> **PASS**
- **H3 (Active Workspace Preservation)**: C3-R-G active load: **2.67** vs C2: **8.67** (69.2% reduction, threshold: >=50%) -> **PASS**
- **H4 (Correctness Non-Inferiority)**: C3-R-G accuracy drop vs C2: **0.0 pp** (threshold: <= 5 pp) -> **PASS**

## Kill Rules Status

- Max correctness drop vs C2 <= 5 pp: **PASS**
- Min C3-R-G dependency preservation >= 90%: **PASS**
- Min C3-R-G restore rate >= 90%: **PASS**
- C3-R-G improves over C3-R-M: **PASS**
- Min workspace reduction vs C2 >= 20%: **PASS**
